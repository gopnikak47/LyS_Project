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
    logo_url: str | None = Field(
        default=None, max_length=2000, pattern=r"^/api/v1/public/assets/[\w.-]+$"
    )
    background_image: str | None = Field(
        default=None, max_length=2000, pattern=r"^/api/v1/public/assets/[\w.-]+$"
    )


class Choice(ApiModel):
    value: str = Field(min_length=1, max_length=64, pattern=r"^[\w-]+$")
    label: dict[str, str]
    image_url: str | None = Field(
        default=None, max_length=2000, pattern=r"^/api/v1/public/assets/[\w.-]+$"
    )
    display_if: dict[str, Any] = Field(default_factory=dict)


class Voucher(ApiModel):
    enabled: bool = False
    code: str | None = Field(default=None, max_length=100)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def timezone_required(self) -> Voucher:
        if self.expires_at and self.expires_at.tzinfo is None:
            raise ValueError("Hạn voucher cần múi giờ.")
        return self


class QuestionInput(ApiModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    code: str = Field(min_length=1, max_length=64, pattern=r"^[\w-]+$")
    type: Literal[
        "rating",
        "csat",
        "text",
        "single_choice",
        "multi_choice",
        "nps",
        "picture_choice",
        "slider",
        "ranking",
        "contact",
        "upload",
        "matrix",
        "datetime",
    ]
    title: dict[str, str]
    description: dict[str, str] = Field(default_factory=dict)
    required: bool = False
    options: list[Choice] = Field(default_factory=list, max_length=100)
    config: dict[str, Any] = Field(default_factory=dict)
    logic: dict[str, Any] = Field(default_factory=dict)
    points: float | None = Field(default=None, ge=0, le=1000)

    @model_validator(mode="after")
    def validate_question(self) -> QuestionInput:
        if not self.title.get("vi", "").strip() or any(len(v) > 2000 for v in self.title.values()):
            raise ValueError("Câu hỏi cần tiêu đề tiếng Việt, tối đa 2.000 ký tự.")
        if self.type in {"single_choice", "multi_choice", "picture_choice", "ranking"}:
            if len(self.options) < 2 or any(
                not c.label.get("vi", "").strip() for c in self.options
            ):
                raise ValueError("Câu hỏi lựa chọn cần ít nhất hai đáp án có nội dung.")
            if len({c.value for c in self.options}) != len(self.options):
                raise ValueError("Mã đáp án không được trùng.")
        if self.type == "text":
            maximum = self.config.get("max_length", 5000)
            if type(maximum) is not int or not 1 <= maximum <= 10000:
                raise ValueError("Giới hạn nhận xét phải nằm trong 1–10.000 ký tự.")
        if self.type == "slider":
            low, high, step = (
                self.config.get("min", 0),
                self.config.get("max", 100),
                self.config.get("step", 1),
            )
            if (
                any(type(n) is not int for n in (low, high, step))
                or not -10000 <= low < high <= 10000
                or not 1 <= step <= high - low
            ):
                raise ValueError("Thanh trượt cần min < max và step hợp lệ.")
        if self.type == "matrix":
            rows = self.config.get("rows", [])
            columns = self.config.get("columns", [])
            if (
                not rows
                or not columns
                or len(rows) > 20
                or len(columns) > 20
                or any(
                    not isinstance(v, str) or not v.strip() or len(v) > 200 for v in rows + columns
                )
                or len(set(rows)) != len(rows)
                or len(set(columns)) != len(columns)
            ):
                raise ValueError("Ma trận cần 1–20 hàng/cột có tên không trùng.")
        return self


class SurveyInput(ApiModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    theme: Theme = Field(default_factory=Theme)
    settings: dict[str, Any] = Field(default_factory=dict)
    questions: list[QuestionInput] = Field(default_factory=list, max_length=100)
    expected_updated_at: datetime | None = None
    languages: list[Literal["vi", "en"]] = Field(default=["vi"], min_length=1, max_length=2)
    default_language: Literal["vi", "en"] = "vi"
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    is_quiz: bool = False

    @model_validator(mode="after")
    def unique_questions(self) -> SurveyInput:
        from app.core.errors import AppError
        from app.domain.question_types import VALIDATORS
        from app.domain.survey_logic import validate_logic

        if self.is_quiz:
            for question in self.questions:
                if question.points:
                    if "correct_answer" not in question.config:
                        raise ValueError("Câu có điểm cần đáp án đúng.")
                    try:
                        VALIDATORS[question.type](
                            question.model_dump(mode="json"), question.config["correct_answer"]
                        )
                    except AppError as exc:
                        raise ValueError("Đáp án đúng không hợp lệ.") from exc
        duration = self.settings.get("quiz_duration_seconds")
        if duration is not None and (type(duration) is not int or not 30 <= duration <= 86400):
            raise ValueError("Thời gian quiz cần 30–86.400 giây.")
        draw = self.settings.get("quiz_draw_count")
        if draw is not None and (type(draw) is not int or not 1 <= draw <= len(self.questions)):
            raise ValueError("Số câu rút ngẫu nhiên phải từ 1 đến số câu trong ngân hàng.")
        if (draw or self.settings.get("randomize_questions")) and any(
            q.logic for q in self.questions
        ):
            raise ValueError("Không xáo/rút câu khi khảo sát có logic phụ thuộc thứ tự.")
        try:
            validate_logic([q.model_dump(mode="json") for q in self.questions])
        except AppError as exc:
            raise ValueError(str(exc)) from exc
        if self.default_language not in self.languages:
            raise ValueError("Ngôn ngữ mặc định phải nằm trong danh sách ngôn ngữ.")
        if any(d is not None and d.tzinfo is None for d in (self.opens_at, self.closes_at)):
            raise ValueError("Lịch khảo sát cần múi giờ.")
        if self.opens_at and self.closes_at and self.opens_at >= self.closes_at:
            raise ValueError("Thời điểm mở phải trước thời điểm đóng.")
        limit = self.settings.get("max_responses")
        if limit is not None and (type(limit) is not int or not 1 <= limit <= 10000000):
            raise ValueError("Giới hạn phản hồi phải từ 1 đến 10.000.000.")
        quotas = self.settings.get("quotas", [])
        if not isinstance(quotas, list) or len(quotas) > 20:
            raise ValueError("Tối đa 20 quota mỗi khảo sát.")
        for quota in quotas:
            if (
                not isinstance(quota, dict)
                or quota.get("question") not in {q.code for q in self.questions}
                or type(quota.get("limit")) is not int
                or quota["limit"] <= 0
                or type(quota.get("value")) not in (str, int)
            ):
                raise ValueError("Quota cần mã câu hỏi, giá trị và giới hạn dương.")
        if "voucher" in self.settings:
            self.settings["voucher"] = Voucher.model_validate(self.settings["voucher"]).model_dump(
                mode="json"
            )
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
    languages: list[str]
    default_language: str
    opens_at: datetime | None
    closes_at: datetime | None
    is_quiz: bool


class ShareOut(ApiModel):
    url: str
    embed: str
