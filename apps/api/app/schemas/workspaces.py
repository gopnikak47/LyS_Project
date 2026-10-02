from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import ApiModel, HexColor, Name

Industry = Literal["restaurant", "it", "hotel", "retail", "education", "healthcare"]


class WorkspaceSettings(ApiModel):
    # Cụm từ khẩn cấp bổ sung riêng cho workspace (FR-17).
    urgent_keywords: list[str] = Field(default_factory=list, max_length=200)
    # Ngưỡng tin cậy gán chủ đề (FR-16); dưới ngưỡng → "Chưa phân loại".
    topic_threshold: float = Field(default=0.35, ge=0.05, le=0.95)
    # Email nhận cảnh báo khẩn cấp ngay lập tức.
    alert_emails: list[str] = Field(default_factory=list, max_length=20)


class WorkspaceCreate(ApiModel):
    name: Name
    description: str | None = Field(default=None, max_length=1000)
    industry: Industry | None = None
    color: HexColor | None = None


class WorkspaceUpdate(ApiModel):
    name: Name | None = None
    description: str | None = Field(default=None, max_length=1000)
    industry: Industry | None = None
    color: HexColor | None = None
    settings: WorkspaceSettings | None = None


class WorkspaceDelete(ApiModel):
    confirm_name: str = Field(min_length=1, max_length=200)


class WorkspaceOut(ApiModel):
    id: uuid.UUID
    name: str
    description: str | None
    industry: str | None
    color: str
    settings: dict[str, Any]
    survey_count: int = 0
    created_at: datetime
