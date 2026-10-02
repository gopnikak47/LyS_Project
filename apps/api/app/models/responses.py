"""Phản hồi, câu trả lời, kết quả phân tích NLP, lịch sử sửa nhãn, ticket."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    CreatedAt,
    TenantScoped,
    Timestamps,
    UUIDPrimaryKey,
    str_enum,
)
from app.models.enums import (
    AnalysisStatus,
    Channel,
    CorrectionField,
    ResponseStatus,
    ReviewStatus,
    Sentiment,
    TicketPriority,
    TicketStatus,
)


class Response(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    __tablename__ = "responses"
    __table_args__ = (
        Index("ix_responses_tenant_survey_created", "tenant_id", "survey_id", "created_at"),
        Index("ix_responses_tenant_workspace_created", "tenant_id", "workspace_id", "created_at"),
    )

    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    survey_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("survey_versions.id", ondelete="SET NULL")
    )
    channel: Mapped[Channel] = mapped_column(str_enum(Channel, "channel"), default=Channel.LINK)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("survey_channels.id", ondelete="SET NULL")
    )
    # Tham số nguồn (chi nhánh, bàn, mã hóa đơn…)
    source_params: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    # Thông tin định danh tùy chọn (họ tên/SĐT/email) — có thể ẩn danh khi xuất.
    respondent: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    language: Mapped[str] = mapped_column(String(8), default="vi", server_default="vi")
    status: Mapped[ResponseStatus] = mapped_column(
        str_enum(ResponseStatus, "response_status"), default=ResponseStatus.COMPLETED
    )
    started_at: Mapped[datetime | None]
    submitted_at: Mapped[datetime | None]
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    # Băm có muối — không lưu IP/fingerprint thô (bảo vệ dữ liệu cá nhân).
    fingerprint_hash: Mapped[str | None] = mapped_column(String(128))
    ip_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    # Chỉ số tổng hợp để lọc/thống kê nhanh, tính khi lưu phản hồi.
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    csat: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    nps: Mapped[int | None] = mapped_column(SmallInteger)
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    external_id: Mapped[str | None] = mapped_column(String(128))


class Answer(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    __tablename__ = "answers"

    response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("responses.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"), index=True
    )
    question_code: Mapped[str] = mapped_column(String(64))
    question_type: Mapped[str] = mapped_column(String(32))
    value: Mapped[Any] = mapped_column(JSONB)
    text_value: Mapped[str | None] = mapped_column(Text)


class TextAnalysis(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    """Kết quả NLP cho một câu trả lời dạng văn bản.

    Luôn lưu văn bản thô trước với `status=pending`; worker phân tích sau
    (dự phòng khi mô hình lỗi).
    Các cột workspace/survey/channel/rating được sao chép từ phản hồi để lọc nhanh không cần JOIN.
    """

    __tablename__ = "text_analyses"
    __table_args__ = (
        Index("ix_text_analyses_tenant_survey_created", "tenant_id", "survey_id", "created_at"),
        Index("ix_text_analyses_tenant_sentiment", "tenant_id", "sentiment"),
        Index("ix_text_analyses_tenant_urgent", "tenant_id", "is_urgent"),
        Index("ix_text_analyses_status", "status"),
        Index("ix_text_analyses_topic_ids", "topic_ids", postgresql_using="gin"),
    )

    response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("responses.id", ondelete="CASCADE"), index=True
    )
    answer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"), unique=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"))
    channel: Mapped[Channel] = mapped_column(str_enum(Channel, "channel"), default=Channel.LINK)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    responded_at: Mapped[datetime] = mapped_column(server_default=func.now())

    text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[Sentiment | None] = mapped_column(str_enum(Sentiment, "sentiment"))
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    # Xác suất từng lớp + kết quả theo câu: {"probs": {...}, "sentences": [...]}
    sentiment_detail: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    topic_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, server_default="{}"
    )
    topic_scores: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    urgent_reasons: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)), default=list, server_default="{}"
    )

    model_version: Mapped[str | None] = mapped_column(String(64))
    topic_set_version: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[AnalysisStatus] = mapped_column(
        str_enum(AnalysisStatus, "analysis_status"), default=AnalysisStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(500))
    analyzed_at: Mapped[datetime | None]
    # Đã được người kiểm tra xác nhận/hiệu chỉnh (human-in-the-loop).
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    verified_at: Mapped[datetime | None]
    note: Mapped[str | None] = mapped_column(Text)


class LabelCorrection(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    """Lịch sử hiệu chỉnh nhãn (FR-20) — nguồn dữ liệu cho đánh giá và huấn luyện lại."""

    __tablename__ = "label_corrections"
    __table_args__ = (Index("ix_label_corrections_tenant_created", "tenant_id", "created_at"),)

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("text_analyses.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    field: Mapped[CorrectionField] = mapped_column(str_enum(CorrectionField, "correction_field"))
    old_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500))
    model_version: Mapped[str | None] = mapped_column(String(64))
    # Đã hoàn tác (undo) — không dùng để huấn luyện.
    reverted_at: Mapped[datetime | None]
    used_for_training: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    review_status: Mapped[ReviewStatus] = mapped_column(
        str_enum(ReviewStatus, "review_status"), default=ReviewStatus.APPROVED
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None]


class Ticket(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "tickets"
    __table_args__ = (Index("ix_tickets_tenant_status", "tenant_id", "status"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    response_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("responses.id", ondelete="SET NULL")
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("text_analyses.id", ondelete="SET NULL"), unique=True
    )
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[TicketStatus] = mapped_column(
        str_enum(TicketStatus, "ticket_status"), default=TicketStatus.NEW
    )
    priority: Mapped[TicketPriority] = mapped_column(
        str_enum(TicketPriority, "ticket_priority"), default=TicketPriority.NORMAL
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    due_at: Mapped[datetime | None]
    resolved_at: Mapped[datetime | None]
    notes: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
