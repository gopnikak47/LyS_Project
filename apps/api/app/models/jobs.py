"""Job nền: import, export; registry phiên bản mô hình NLP."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAt, TenantScoped, Timestamps, UUIDPrimaryKey, str_enum
from app.models.enums import ExportKind, ImportKind, JobStatus


class ImportJob(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "import_jobs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    survey_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE")
    )
    kind: Mapped[ImportKind] = mapped_column(str_enum(ImportKind, "import_kind"))
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus, "job_status"), default=JobStatus.PENDING
    )
    original_filename: Mapped[str] = mapped_column(String(300))
    file_key: Mapped[str] = mapped_column(String(500))
    mapping: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    total_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    success_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_report_key: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class ExportJob(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "export_jobs"

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    kind: Mapped[ExportKind] = mapped_column(str_enum(ExportKind, "export_kind"))
    status: Mapped[JobStatus] = mapped_column(
        str_enum(JobStatus, "job_status"), default=JobStatus.PENDING
    )
    params: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    file_key: Mapped[str | None] = mapped_column(String(500))
    filename: Mapped[str | None] = mapped_column(String(300))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    finished_at: Mapped[datetime | None]
    expires_at: Mapped[datetime | None]


class NlpModel(UUIDPrimaryKey, CreatedAt, Base):
    """Registry phiên bản mô hình (toàn cục). `metrics` lấy từ evaluate.py — số liệu thật."""

    __tablename__ = "nlp_models"
    __table_args__ = (UniqueConstraint("task", "version", name="uq_nlp_models_task_version"),)

    task: Mapped[str] = mapped_column(String(32))  # sentiment | topics
    version: Mapped[str] = mapped_column(String(64))
    backend: Mapped[str] = mapped_column(String(32))
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    artifact_path: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text)
