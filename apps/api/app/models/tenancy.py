"""Doanh nghiệp, người dùng, thành viên, lời mời, không gian khảo sát, token, gói dịch vụ."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
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
from app.models.enums import MembershipStatus, Role, TenantStatus


class Plan(Timestamps, Base):
    """Gói dịch vụ (Free/Pro/Business) — bảng toàn cục, không theo tenant."""

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price_vnd: Mapped[int] = mapped_column(Integer, default=0)
    # Ví dụ: {"workspaces": 1, "members": 3, "nlp_responses_per_month": 500, "features": [...]}
    limits: Mapped[dict[str, Any]] = mapped_column(default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Tenant(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    industry: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[TenantStatus] = mapped_column(
        str_enum(TenantStatus, "tenant_status"), default=TenantStatus.ACTIVE
    )
    plan_code: Mapped[str] = mapped_column(
        ForeignKey("plans.code"), default="free", server_default="free"
    )
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")


class User(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    """Người dùng toàn cục: một người có thể thuộc nhiều doanh nghiệp qua `memberships`."""

    __tablename__ = "users"

    # Luôn lưu dạng chữ thường (chuẩn hóa ở tầng service) để unique không phân biệt hoa thường.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(8), default="vi", server_default="vi")
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    email_verified_at: Mapped[datetime | None]
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    # Tăng khi đổi mật khẩu để vô hiệu toàn bộ phiên cũ.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Membership(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"))
    status: Mapped[MembershipStatus] = mapped_column(
        str_enum(MembershipStatus, "membership_status"), default=MembershipStatus.ACTIVE
    )
    # True = được truy cập mọi workspace; False = chỉ các workspace trong workspace_members.
    all_workspaces: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Invitation(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    __tablename__ = "invitations"

    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"))
    workspace_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, server_default="{}"
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


class Workspace(UUIDPrimaryKey, TenantScoped, Timestamps, SoftDelete, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(32))
    color: Mapped[str] = mapped_column(String(16), default="#4f46e5", server_default="#4f46e5")
    # Cấu hình riêng: từ khóa khẩn cấp, ngưỡng chủ đề, người nhận cảnh báo…
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class WorkspaceMember(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class RefreshToken(UUIDPrimaryKey, CreatedAt, Base):
    """Refresh token xoay vòng; `family_id` để phát hiện token bị đánh cắp và tái sử dụng."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    replaced_by_id: Mapped[uuid.UUID | None]
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip_hash: Mapped[str | None] = mapped_column(String(128))


class PasswordResetToken(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class Subscription(UUIDPrimaryKey, TenantScoped, Timestamps, Base):
    __tablename__ = "subscriptions"

    plan_code: Mapped[str] = mapped_column(ForeignKey("plans.code"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    current_period_start: Mapped[datetime]
    current_period_end: Mapped[datetime]
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    provider_ref: Mapped[str | None] = mapped_column(String(200))


class AuditLog(UUIDPrimaryKey, TenantScoped, CreatedAt, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    data: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default="{}")
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[str | None] = mapped_column(String(64))
