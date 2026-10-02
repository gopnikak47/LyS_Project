"""Gom các router của API phiên bản 1 (tiền tố `/api/v1`)."""

from __future__ import annotations

from fastapi import APIRouter

from app.routers import health
from app.schemas.health import ReadinessResponse

api_v1 = APIRouter(prefix="/api/v1")

# Readiness công khai qua nginx: GET /api/v1/health
api_v1.add_api_route(
    "/health",
    health.readiness,
    methods=["GET"],
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
    tags=["health"],
    summary="Tình trạng hệ thống (DB, Redis)",
)
