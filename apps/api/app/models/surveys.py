"""Khảo sát, phiên bản xuất bản, câu hỏi, kênh phát hành."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    CreatedAt,
    SoftDelete,
    TenantScoped,
    Timestamps,
    UUIDPrimaryKey,
    str_enum,
)
from app.models.enums import Channel, SurveyStatus


class Survey(UUIDPrimaryKey, TenantScoped, Timestamps, SoftDelete, Base):
    __tablename__ = "surveys"
    __table_args__ = (
        Index("ix_surveys_tenant_workspace_status", "tenant_id", "workspace_id", "status"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SurveyStatus] = mapped_column(
        str_enum(SurveyStatus, "survey_status"), default=SurveyStatus.DRAFT
    )
    # Slug công khai, duy nhất toàn hệ thống: /s/{slug}
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    theme: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    languages: Mapped[list[str]] = mapped_column(
        ARRAY(String(8)), default=lambda: ["vi"], server_default="{vi}"
    )
    default_language: Mapped[str] = mapped_column(String(8), default="vi", server_default="vi")
    is_quiz: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("survey_versions.id", ondelete="SET NULL", use_alter=True)
    )
    published_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    opens_at: Mapped[datetime | None]
    closes_at: Mapped[datetime | None]
    response_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class SurveyVersion(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    """Ảnh chụp cấu hình khi xuất bản — dữ liệu phản hồi cũ luôn đối chiếu đúng phiên bản."""

    __tablename__ = "survey_versions"
    __table_args__ = (UniqueConstraint("survey_id", "version", name="uq_survey_versions_version"),)

    survey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]]
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Question(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_survey_position", "survey_id", "position"),)

    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"))
    # Loại câu hỏi theo registry plugin: rating, csat, text, single_choice, multi_choice, nps…
    type: Mapped[str] = mapped_column(String(32))
    # Mã ổn định để đối chiếu qua các phiên bản và khi import.
    code: Mapped[str] = mapped_column(String(64))
    # Nội dung đa ngôn ngữ: {"vi": "...", "en": "..."}
    title: Mapped[dict[str, Any]] = mapped_column(default=dict)
    description: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    options: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    config: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    logic: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    position: Mapped[int] = mapped_column(Integer, default=0)
    required: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    points: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))


class SurveyChannel(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    """Kênh/điểm phát hành (QR theo chi nhánh, bàn, hóa đơn…) để thống kê nguồn (FR-06)."""

    __tablename__ = "survey_channels"
    __table_args__ = (UniqueConstraint("survey_id", "code", name="uq_survey_channels_code"),)

    survey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[Channel] = mapped_column(str_enum(Channel, "channel"), default=Channel.QR)
    code: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
