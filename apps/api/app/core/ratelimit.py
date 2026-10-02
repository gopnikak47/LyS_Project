"""Giới hạn tần suất (fixed window) dùng Redis; bản in-memory cho test/dev không Redis."""

from __future__ import annotations

import time
from typing import Protocol

from redis.asyncio import Redis

from app.core.errors import AppError


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Ghi nhận một lượt; trả False nếu đã vượt giới hạn trong cửa sổ hiện tại."""

    async def reset(self, key: str) -> None: ...


class RedisRateLimiter:
    def __init__(self, redis: Redis, prefix: str = "rl") -> None:
        self.redis = redis
        self.prefix = prefix

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        bucket = int(time.time() // window_seconds)
        full_key = f"{self.prefix}:{key}:{bucket}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(full_key)
            pipe.expire(full_key, window_seconds + 1)
            count, _ = await pipe.execute()
        return int(count) <= limit

    async def reset(self, key: str) -> None:
        async for k in self.redis.scan_iter(match=f"{self.prefix}:{key}:*"):
            await self.redis.delete(k)


class MemoryRateLimiter:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        bucket = int(time.time() // window_seconds)
        full_key = f"{key}:{bucket}"
        self._counts[full_key] = self._counts.get(full_key, 0) + 1
        return self._counts[full_key] <= limit

    async def reset(self, key: str) -> None:
        for k in [k for k in self._counts if k.startswith(f"{key}:")]:
            del self._counts[k]


async def enforce(limiter: RateLimiter, key: str, limit: int, window_seconds: int) -> None:
    if not await limiter.hit(key, limit, window_seconds):
        raise RateLimitedError()
