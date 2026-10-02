from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ComponentHealth(BaseModel):
    status: Literal["ok", "error"]
    latency_ms: float
    # Chỉ tên loại lỗi, không lộ chi tiết hạ tầng ra ngoài.
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    components: dict[str, ComponentHealth]
