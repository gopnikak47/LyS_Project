"""Hợp đồng trình tạo khảo sát; snapshot dùng chung với trang khách."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import ApiModel, HexColor


class Theme(ApiModel):
    primary: HexColor = "#4f46e5"
    background: HexColor = "#f8fafc"
    text: HexColor = "#0f172a"
    font: Literal["sans-serif", "serif"] = "sans-serif"
    font_size: int = Field(default=16, ge=14, le=24)
    layout: Literal["scroll", "one_per_page"] = "scroll"


class Choice(ApiModel):
    value: str = Field(min_length=1, max_length=64, pattern=r"^[\w-]+$")
    label: dict[str, str]


class QuestionInput(ApiModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    code: str = Field(min_length=1, max_length=64, pattern=r"^[\w-]+$")
    type: Literal["rating", "csat", "text", "single_choice", "multi_choice"]
    title: dict[str, str]
    description: dict[str, str] = Field(default_factory=dict)
    required: bool = False
    options: list[Choice] = Field(default_factory=list, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    logic: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_question(self) -> QuestionInput:
        if not self.title.get("vi", "").strip() or any(len(v) > 2000 for v in self.title.values()):
            raise ValueError("Câu hỏi cần tiêu đề tiếng Việt, tối đa 2.000 ký tự.")
        if self.type in {"single_choice", "multi_choice"}:
            if len(self.options) < 2 or any(not c.label.get("vi", "").strip() for c in self.options):
                raise ValueError("Câu hỏi lựa chọn cần ít nhất hai đáp án có nội dung.")
            if len({c.value for c in self.options}) != len(self.options):
                raise ValueError("Mã đáp án không được trùng.")
        if self.type == "text":
            maximum = self.config.get("max_length", 5000)
            if type(maximum) is not int or not 1 <= maximum <= 10000:
                raise ValueError("Giới hạn nhận xét phải nằm trong 1–10.000 ký tự.")
        return self


class SurveyInput(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    theme: Theme = Field(default_factory=Theme)
    settings: dict[str, Any] = Field(default_factory=dict)
    questions: list[QuestionInput] = Field(default_factory=list, max_length=100)
    expected_updated_at: datetime | None = None

    @model_validator(mode="after")
    def unique_questions(self) -> SurveyInput:
        if len({q.code for q in self.questions}) != len(self.questions):
            raise ValueError("Mã câu hỏi không được trùng.")
        if len({q.id for q in self.questions}) != len(self.questions):
            raise ValueError("ID câu hỏi không được trùng.")
        if not self.title.strip():
            raise ValueError("Vui lòng nhập tên khảo sát.")
        return self


class SurveyCreate(SurveyInput):
    workspace_id: uuid.UUID


class SurveyOut(ApiModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str | None
    status: str
    slug: str
    theme: dict[str, Any]
    settings: dict[str, Any]
    response_count: int
    updated_at: datetime
    current_version_id: uuid.UUID | None
    questions: list[QuestionInput] = Field(default_factory=list)


class ShareOut(ApiModel):
    url: str
    embed: str
