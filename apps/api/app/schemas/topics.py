from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from app.schemas.common import ApiModel, HexColor
from app.schemas.workspaces import Industry

TopicName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Keyword = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def _dedupe_keywords(values: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen[key] = value.strip()
    return list(seen.values())


class TopicBase(ApiModel):
    description: str | None = Field(default=None, max_length=500)
    keywords: list[Keyword] = Field(default_factory=list, max_length=50)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, value: list[str]) -> list[str]:
        return _dedupe_keywords(value)


class TopicCreate(TopicBase):
    name: TopicName
    color: HexColor = "#6366f1"


class TopicUpdate(ApiModel):
    name: TopicName | None = None
    description: str | None = Field(default=None, max_length=500)
    keywords: list[Keyword] | None = Field(default=None, max_length=50)
    color: HexColor | None = None
    is_active: bool | None = None

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, value: list[str] | None) -> list[str] | None:
        return _dedupe_keywords(value) if value is not None else None


class TopicOut(ApiModel):
    id: uuid.UUID
    name: str
    description: str | None
    keywords: list[str]
    color: str
    sort_order: int
    is_active: bool
    usage_count: int = 0


class TopicSetOut(ApiModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    template_code: str | None
    version: int
    topics: list[TopicOut]


class TopicMerge(ApiModel):
    source_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    target_id: uuid.UUID


class TopicOrder(ApiModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class ApplyTemplate(ApiModel):
    template_code: Industry
    # True: thay toàn bộ chủ đề hiện có; False: chỉ thêm chủ đề chưa có.
    replace: bool = False


class TemplateTopicOut(ApiModel):
    name: str
    description: str
    keywords: list[str]
    color: str


class TemplateOut(ApiModel):
    code: str
    name: str
    topics: list[TemplateTopicOut]


class ReanalyzeOut(ApiModel):
    queued: bool
    pending: int
