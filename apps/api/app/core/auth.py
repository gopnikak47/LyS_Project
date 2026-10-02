"""Xác thực & ngữ cảnh request (FR-01, FR-04 lớp 1).

Mỗi request đã xác thực nhận `RequestContext` gồm:
  - `principal`: người dùng, tenant, vai trò, quyền, phạm vi workspace — lấy từ CSDL (không tin
    vai trò ghi trong token, đổi vai trò có hiệu lực ngay);
  - `db`: phiên CSDL đã gắn ngữ cảnh tenant (RLS) trong một transaction.
"""

from __future__ import annotations

import hmac
import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.permissions import Permission, permissions_for
from app.core.resources import Resources
from app.core.security import hash_identifier
from app.core.tokens import decode_access_token
from app.db.tenant import tenant_session
from app.models import Membership, Tenant, User, WorkspaceMember
from app.models.enums import MembershipStatus, Role, TenantStatus

ACCESS_COOKIE = "lys_access"
REFRESH_COOKIE = "lys_refresh"
CSRF_COOKIE = "lys_csrf"
CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CsrfError(AppError):
    status_code = 403
    code = "CSRF_FAILED"


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: Role
    email: str
    full_name: str
    all_workspaces: bool
    workspace_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)

    @property
    def permissions(self) -> frozenset[Permission]:
        return permissions_for(self.role)

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions

    def require(self, permission: Permission) -> None:
        if not self.can(permission):
            raise ForbiddenError()

    @property
    def sees_all_workspaces(self) -> bool:
        return self.role == Role.ADMIN or self.all_workspaces

    def can_access_workspace(self, workspace_id: uuid.UUID) -> bool:
        return self.sees_all_workspaces or workspace_id in self.workspace_ids

    def require_workspace(self, workspace_id: uuid.UUID) -> None:
        # Trả 404 thay vì 403 để không tiết lộ workspace có tồn tại hay không.
        if not self.can_access_workspace(workspace_id):
            raise NotFoundError("Không tìm thấy không gian khảo sát.")


@dataclass(slots=True)
class RequestContext:
    principal: Principal
    db: AsyncSession
    request: Request
    settings: Settings
    resources: Resources

    @property
    def ip_hash(self) -> str | None:
        return client_ip_hash(self.request, self.settings)

    @property
    def request_id(self) -> str | None:
        from app.core.request_context import get_request_id

        return get_request_id()


def get_resources(request: Request) -> Resources:
    resources: Resources = request.app.state.resources
    return resources


def get_app_settings(request: Request) -> Settings:
    """Cấu hình của chính app đang chạy (create_app(settings)) — không dùng bản cache toàn cục."""
    settings: Settings = request.app.state.settings
    return settings


def client_ip_hash(request: Request, settings: Settings) -> str | None:
    host = request.client.host if request.client else None
    return hash_identifier(host, settings.hash_salt.get_secret_value()) if host else None


def _extract_token(request: Request) -> tuple[str | None, bool]:
    """Trả (token, dùng_cookie). Ưu tiên header Authorization cho client API."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None, False
    return request.cookies.get(ACCESS_COOKIE), True


def verify_csrf(request: Request) -> None:
    """Double-submit cookie: header X-CSRF-Token phải trùng cookie lys_csrf (so sánh an toàn)."""
    if request.method not in UNSAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise CsrfError("Phiên làm việc không hợp lệ, vui lòng tải lại trang.")


async def load_principal(
    session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, token_version: int | None
) -> Principal:
    row = (
        await session.execute(
            select(Membership, User, Tenant)
            .join(User, User.id == Membership.user_id)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .where(Membership.user_id == user_id, Membership.tenant_id == tenant_id)
        )
    ).first()
    if row is None:
        raise UnauthorizedError()
    membership, user, tenant = row
    if (
        membership.status != MembershipStatus.ACTIVE
        or user.deleted_at is not None
        or tenant.deleted_at is not None
        or tenant.status != TenantStatus.ACTIVE
        or (token_version is not None and user.token_version != token_version)
    ):
        raise UnauthorizedError()
    workspace_ids: frozenset[uuid.UUID] = frozenset()
    if membership.role != Role.ADMIN and not membership.all_workspaces:
        ids = await session.execute(
            select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
        )
        workspace_ids = frozenset(ids.scalars().all())
    return Principal(
        user_id=user.id,
        tenant_id=tenant_id,
        role=membership.role,
        email=user.email,
        full_name=user.full_name,
        all_workspaces=membership.all_workspaces,
        workspace_ids=workspace_ids,
    )


async def get_context(
    request: Request,
    resources: Annotated[Resources, Depends(get_resources)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AsyncIterator[RequestContext]:
    token, via_cookie = _extract_token(request)
    claims = decode_access_token(settings, token) if token else None
    if claims is None:
        raise UnauthorizedError()
    if via_cookie:
        verify_csrf(request)
    async with tenant_session(resources.session_factory, claims.tenant_id, claims.user_id) as db:
        principal = await load_principal(db, claims.user_id, claims.tenant_id, claims.token_version)
        yield RequestContext(principal, db, request, settings, resources)


async def get_system_db(
    resources: Annotated[Resources, Depends(get_resources)],
) -> AsyncIterator[AsyncSession]:
    """Phiên hệ thống cho endpoint chưa có ngữ cảnh tenant (đăng ký, đăng nhập, công khai).

    Không dùng `session.begin()` để handler có thể `commit()` giữa chừng (vd. lưu bộ đếm
    đăng nhập sai trước khi trả lỗi); phần còn lại được commit khi handler kết thúc.
    """
    async with resources.session_factory() as db:
        try:
            yield db
            await db.commit()
        except BaseException:
            await db.rollback()
            raise


Ctx = Annotated[RequestContext, Depends(get_context)]
SystemDB = Annotated[AsyncSession, Depends(get_system_db)]
ResourcesDep = Annotated[Resources, Depends(get_resources)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def require(
    permission: Permission,
) -> Callable[[RequestContext], Coroutine[Any, Any, RequestContext]]:
    """Dependency kiểm tra quyền: `ctx: Annotated[RequestContext, Depends(require(...))]`."""

    async def checker(ctx: Ctx) -> RequestContext:
        ctx.principal.require(permission)
        return ctx

    return checker
