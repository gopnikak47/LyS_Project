"""Dependency FastAPI dùng chung."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.resources import Resources
from app.services.health import HealthService


def get_resources(request: Request) -> Resources:
    resources: Resources = request.app.state.resources
    return resources


SettingsDep = Annotated[Settings, Depends(get_settings)]
ResourcesDep = Annotated[Resources, Depends(get_resources)]


def get_health_service(resources: ResourcesDep, settings: SettingsDep) -> HealthService:
    return HealthService.from_resources(resources, timeout=settings.health_check_timeout_seconds)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
