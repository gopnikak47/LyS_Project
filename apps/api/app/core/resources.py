"""Tài nguyên dùng chung trong vòng đời ứng dụng (engine DB, Redis).

Tạo khi khởi động, đóng gọn gàng khi tắt (graceful shutdown).
"""

from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.session import create_engine, create_session_factory


@dataclass(slots=True)
class Resources:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis: Redis

    @classmethod
    def from_settings(cls, settings: Settings) -> Resources:
        engine = create_engine(settings)
        return cls(
            engine=engine,
            session_factory=create_session_factory(engine),
            redis=Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=settings.health_check_timeout_seconds,
                socket_timeout=settings.health_check_timeout_seconds,
            ),
        )

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()
