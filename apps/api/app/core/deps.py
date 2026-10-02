"""Dependency FastAPI dùng chung (ngoài xác thực — xem `app.core.auth`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.auth import ResourcesDep, SettingsDep
from app.services.health import HealthService


def get_health_service(resources: ResourcesDep, settings: SettingsDep) -> HealthService:
    return HealthService.from_resources(resources, timeout=settings.health_check_timeout_seconds)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
