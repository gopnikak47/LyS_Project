from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.enums import Role
from app.schemas.common import ApiModel, Email, Name, Password


class RegisterRequest(ApiModel):
    company_name: Name
    full_name: Name
    email: Email
    password: Password
    industry: Literal["restaurant", "it", "hotel", "retail", "education", "healthcare"] | None = (
        None
    )


class LoginRequest(ApiModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)
    tenant_slug: str | None = Field(default=None, max_length=80)


class ForgotPasswordRequest(ApiModel):
    email: Email


class ResetPasswordRequest(ApiModel):
    token: str = Field(min_length=10, max_length=200)
    password: Password


class ChangePasswordRequest(ApiModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password


class SwitchTenantRequest(ApiModel):
    tenant_id: uuid.UUID


class UpdateProfileRequest(ApiModel):
    full_name: Name | None = None
    locale: Literal["vi", "en"] | None = None


class UserOut(ApiModel):
    id: uuid.UUID
    email: str
    full_name: str
    locale: str


class TenantOut(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    industry: str | None
    plan_code: str


class MembershipSummary(ApiModel):
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    role: Role


class SessionOut(ApiModel):
    user: UserOut
    tenant: TenantOut
    role: Role
    permissions: list[str]
    all_workspaces: bool
    workspace_ids: list[uuid.UUID]
    memberships: list[MembershipSummary]
    csrf_token: str | None = None
    access_expires_at: datetime | None = None
