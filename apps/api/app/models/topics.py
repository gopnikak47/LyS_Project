"""Bộ chủ đề theo workspace (FR-12/13)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamps, UUIDPrimaryKey


class TopicSet(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    """Mỗi workspace có đúng một bộ chủ đề; `version` tăng mỗi khi chủ đề thay đổi."""

    __tablename__ = "topic_sets"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(200))
    template_code: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class Topic(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("topic_set_id", "name", name="uq_topics_set_name"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    topic_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topic_sets.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    # Mô tả ngắn + từ khóa gợi ý dùng làm "prototype" cho phân loại zero-shot (FR-16).
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), default=list, server_default="{}"
    )
    color: Mapped[str] = mapped_column(String(16), default="#6366f1", server_default="#6366f1")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
