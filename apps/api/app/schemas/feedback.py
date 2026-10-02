from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.enums import Sentiment
from app.schemas.common import ApiModel


class FeedbackFilter(ApiModel):
    workspace_id: uuid.UUID
    survey_id: uuid.UUID | None = None
    sentiment: Sentiment | None = None
    topic_id: uuid.UUID | None = None
    urgent: bool | None = None
    channel: str | None = Field(default=None, max_length=32)
    search: str = Field(default="", max_length=300)
    start: datetime | None = None
    end: datetime | None = None
    sort: Literal["newest", "oldest", "confidence", "urgent"] = "urgent"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CorrectionInput(ApiModel):
    sentiment: Sentiment | None = None
    topic_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    is_urgent: bool | None = None
    note: str | None = Field(default=None, max_length=5000)
    reason: str = Field(default="", max_length=500)
    expected_updated_at: datetime | None = None


class BulkCorrection(ApiModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    correction: CorrectionInput
