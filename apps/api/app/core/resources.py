"""Tài nguyên dùng chung trong vòng đời ứng dụng (engine DB, Redis, rate limiter, hàng đợi).

Tạo khi khởi động, đóng gọn gàng khi tắt (graceful shutdown). Test có thể thay
`limiter`/`queue` bằng bản in-memory.
"""

from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.queue import CeleryQueue, TaskQueue
from app.core.ratelimit import RateLimiter, RedisRateLimiter
from app.db.session import create_engine, create_session_factory


@dataclass(slots=True)
class Resources:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis: Redis
    limiter: RateLimiter
    queue: TaskQueue

    @classmethod
    def from_settings(cls, settings: Settings) -> Resources:
        engine = create_engine(settings)
        redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.health_check_timeout_seconds,
            socket_timeout=settings.health_check_timeout_seconds,
        )
        return cls(
            engine=engine,
            session_factory=create_session_factory(engine),
            redis=redis,
            limiter=RedisRateLimiter(redis),
            queue=CeleryQueue(settings),
        )

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()
