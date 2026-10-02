from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.deps import HealthServiceDep
from app.schemas.health import LivenessResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=LivenessResponse, summary="Liveness: tiến trình còn sống")
async def liveness() -> LivenessResponse:
    return LivenessResponse()


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness: DB và Redis sẵn sàng",
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(service: HealthServiceDep, response: Response) -> ReadinessResponse:
    report = await service.readiness()
    if report.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report
