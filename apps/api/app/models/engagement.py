from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamps, UUIDPrimaryKey, str_enum
from app.models.enums import JobStatus


class EmailDelivery(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dedupe_key", name="uq_email_deliveries_dedupe"),
        Index("ix_email_deliveries_status_due", "status", "next_attempt_at"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    survey_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE")
    )
    recipient: Mapped[str] = mapped_column(String(320))
    kind: Mapped[str] = mapped_column(String(32))
    dedupe_key: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus, "job_status"), default=JobStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None]
    sent_at: Mapped[datetime | None]
    opened_at: Mapped[datetime | None]
    clicked_at: Mapped[datetime | None]
    last_error: Mapped[str | None] = mapped_column(String(200))


class ReportSchedule(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "report_schedules"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    recipients: Mapped[list[str]] = mapped_column(ARRAY(String(320)))
    cadence: Mapped[str] = mapped_column(String(16))
    filters: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    next_run_at: Mapped[datetime]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
