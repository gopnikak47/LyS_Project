"""Kiểm tra sức khỏe các thành phần phụ thuộc (DB, Redis…)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import text

from app import __version__
from app.core.logging import get_logger
from app.core.resources import Resources
from app.schemas.health import ComponentHealth, ReadinessResponse

logger = get_logger(__name__)

HealthCheck = Callable[[], Awaitable[object]]


class HealthService:
    def __init__(self, checks: Mapping[str, HealthCheck], *, timeout: float) -> None:
        self._checks = dict(checks)
        self._timeout = timeout

    @classmethod
    def from_resources(cls, resources: Resources, *, timeout: float) -> HealthService:
        async def check_database() -> None:
            async with resources.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        async def check_redis() -> None:
            await resources.redis.ping()

        return cls({"database": check_database, "redis": check_redis}, timeout=timeout)

    async def _run(self, name: str, check: HealthCheck) -> tuple[str, ComponentHealth]:
        started = time.perf_counter()
        error: str | None = None
        try:
            await asyncio.wait_for(check(), timeout=self._timeout)
        except Exception as exc:  # health-check phải nuốt mọi lỗi để báo cáo
            error = type(exc).__name__
            logger.warning("health_check_failed", component=name, error=error)
        latency = round((time.perf_counter() - started) * 1000, 2)
        return name, ComponentHealth(
            status="error" if error else "ok", latency_ms=latency, error=error
        )

    async def readiness(self) -> ReadinessResponse:
        results = await asyncio.gather(*(self._run(n, c) for n, c in self._checks.items()))
        components = dict(results)
        healthy = all(c.status == "ok" for c in components.values())
        return ReadinessResponse(
            status="ok" if healthy else "degraded",
            version=__version__,
            components=components,
        )
