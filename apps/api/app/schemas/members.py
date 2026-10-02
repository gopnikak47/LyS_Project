from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import MembershipStatus, Role
from app.schemas.common import ApiModel, Email, Name, Password


class MemberOut(ApiModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: Role
    status: MembershipStatus
    all_workspaces: bool
    workspace_ids: list[uuid.UUID]
    last_login_at: datetime | None
    created_at: datetime


class MemberUpdate(ApiModel):
    role: Role | None = None
    status: MembershipStatus | None = None
    all_workspaces: bool | None = None
    workspace_ids: list[uuid.UUID] | None = Field(default=None, max_length=500)


class InvitationCreate(ApiModel):
    email: Email
    role: Role = Role.ANALYST
    # Rỗng = được truy cập mọi workspace.
    workspace_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)


class InvitationOut(ApiModel):
    id: uuid.UUID
    email: str
    role: Role
    workspace_ids: list[uuid.UUID]
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class InvitationCreated(InvitationOut):
    # Trả link một lần để admin có thể tự gửi (trường hợp email bị chặn).
    invite_url: str


class PublicInvitationOut(ApiModel):
    tenant_name: str
    email: str
    role: Role
    inviter_name: str | None
    user_exists: bool
    expires_at: datetime


class InvitationAccept(ApiModel):
    # Người dùng mới: bắt buộc họ tên + mật khẩu mới. Người đã có tài khoản: mật khẩu hiện tại.
    full_name: Name | None = None
    password: str = Field(min_length=1, max_length=128)


class InvitationAcceptNew(ApiModel):
    full_name: Name
    password: Password
