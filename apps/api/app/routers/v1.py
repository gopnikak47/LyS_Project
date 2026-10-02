"""Gom các router của API phiên bản 1 (tiền tố `/api/v1`)."""

from __future__ import annotations

from fastapi import APIRouter

from app.routers import analytics, auth, exports, feedback, health, imports, members, nlp, public, surveys, templates, topics, workspaces
from app.schemas.health import ReadinessResponse
from app.routers import engagement, tickets, tracking
from app.routers import billing

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(workspaces.router)
api_v1.include_router(members.router)
api_v1.include_router(public.router)
api_v1.include_router(topics.router)
api_v1.include_router(surveys.router)
api_v1.include_router(nlp.router)
api_v1.include_router(imports.router)
api_v1.include_router(feedback.router)
api_v1.include_router(analytics.router)
api_v1.include_router(exports.router)
api_v1.include_router(templates.router)
api_v1.include_router(tickets.router)
api_v1.include_router(engagement.router)
api_v1.include_router(tracking.router)
api_v1.include_router(billing.router)

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
