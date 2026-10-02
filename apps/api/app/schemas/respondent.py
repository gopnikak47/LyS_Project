from __future__ import annotations

from typing import Any

from pydantic import Field

from app.models.enums import Channel
from app.schemas.common import ApiModel


class Submission(ApiModel):
    token: str = Field(max_length=2000)
    answers: dict[str, Any]
    honeypot: str = Field(default="", max_length=500)
    fingerprint: str = Field(default="", max_length=200)
    language: str = Field(default="vi", max_length=8)
    channel: Channel = Channel.LINK
    invitation: str | None = Field(default=None, max_length=2000)
    source_params: dict[str, str] = Field(default_factory=dict)


class SubmissionResult(ApiModel):
    response_id: str
    voucher: str | None = None
    voucher_expires_at: str | None = None
    message: str = "Cảm ơn bạn đã chia sẻ phản hồi!"
    quiz: dict[str, Any] | None = None
