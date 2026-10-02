"""Endpoint xác thực: /api/v1/auth/* (FR-01)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select

from app.core.auth import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    Ctx,
    ResourcesDep,
    SettingsDep,
    SystemDB,
    client_ip_hash,
    load_principal,
    verify_csrf,
)
from app.core.config import Settings
from app.core.errors import UnauthorizedError, found
from app.core.security import new_token, verify_password
from app.core.tokens import create_access_token
from app.db.tenant import system_session, tenant_session
from app.models import Membership, Tenant, User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    SwitchTenantRequest,
    TenantOut,
    UpdateProfileRequest,
    UserOut,
)
from app.schemas.common import OkResponse
from app.services.auth import AuthService, InvalidCredentialsError, IssuedRefresh

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_PATH = "/api/v1/auth"


def _set_session_cookies(
    response: Response,
    settings: Settings,
    *,
    access: str,
    access_expires: datetime,
    refresh: IssuedRefresh,
) -> str:
    secure = settings.secure_cookies
    access_age = int(settings.access_token_ttl_minutes * 60)
    refresh_age = int(settings.refresh_token_ttl_days * 86400)
    csrf = new_token(24)
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=access_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh.token,
        max_age=refresh_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=REFRESH_PATH,
    )
    # Cookie CSRF đọc được bằng JS để gửi lại qua header X-CSRF-Token.
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=refresh_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return csrf


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


async def _session_payload(
    resources: ResourcesDep,
    service: AuthService,
    user: User,
    membership: Membership,
    *,
    csrf: str | None,
    access_expires: datetime | None,
) -> SessionOut:
    async with tenant_session(resources.session_factory, membership.tenant_id, user.id) as db:
        principal = await load_principal(db, user.id, membership.tenant_id, None)
        tenant = found(await db.get(Tenant, membership.tenant_id))
    return SessionOut(
        user=UserOut.model_validate(user),
        tenant=TenantOut.model_validate(tenant),
        role=principal.role,
        permissions=sorted(p.value for p in principal.permissions),
        all_workspaces=principal.sees_all_workspaces,
        workspace_ids=sorted(principal.workspace_ids),
        memberships=await service.memberships(user.id),
        csrf_token=csrf,
        access_expires_at=access_expires,
    )


async def start_session(
    request: Request,
    response: Response,
    settings: Settings,
    resources: ResourcesDep,
    service: AuthService,
    user: User,
    membership: Membership,
) -> SessionOut:
    ip_hash = client_ip_hash(request, settings)
    _, refresh = await service.issue_refresh(
        user_id=user.id,
        tenant_id=membership.tenant_id,
        user_agent=request.headers.get("user-agent"),
        ip_hash=ip_hash,
    )
    access, access_exp = create_access_token(
        settings,
        user_id=user.id,
        tenant_id=membership.tenant_id,
        role=membership.role,
        token_version=user.token_version,
    )
    csrf = _set_session_cookies(
        response, settings, access=access, access_expires=access_exp, refresh=refresh
    )
    # Commit trước khi đọc lại bằng phiên tenant (khác kết nối).
    await service.db.commit()
    return await _session_payload(
        resources, service, user, membership, csrf=csrf, access_expires=access_exp
    )


def auth_service(db: SystemDB, settings: Settings, resources: ResourcesDep) -> AuthService:
    return AuthService(db, settings, resources.limiter, resources.queue)


@router.post(
    "/register",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký doanh nghiệp + tài khoản quản trị đầu tiên",
)
async def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> SessionOut:
    service = auth_service(db, settings, resources)
    user, membership = await service.register(data, ip_hash=client_ip_hash(request, settings))
    return await start_session(request, response, settings, resources, service, user, membership)


@router.post("/login", response_model=SessionOut, summary="Đăng nhập bằng email/mật khẩu")
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> SessionOut:
    service = auth_service(db, settings, resources)
    try:
        user, membership = await service.authenticate(
            data, ip_hash=client_ip_hash(request, settings)
        )
    except InvalidCredentialsError:
        # Lưu bộ đếm đăng nhập sai trước khi trả lỗi.
        await db.commit()
        raise
    return await start_session(request, response, settings, resources, service, user, membership)


@router.post("/refresh", response_model=SessionOut, summary="Làm mới phiên (xoay vòng refresh)")
async def refresh(
    request: Request,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> SessionOut:
    verify_csrf(request)
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise UnauthorizedError()
    service = auth_service(db, settings, resources)
    try:
        user, membership, issued = await service.rotate_refresh(
            raw,
            user_agent=request.headers.get("user-agent"),
            ip_hash=client_ip_hash(request, settings),
        )
    except UnauthorizedError:
        await db.commit()  # lưu việc thu hồi "họ" token nếu phát hiện tái sử dụng
        _clear_session_cookies(response)
        raise
    access, access_exp = create_access_token(
        settings,
        user_id=user.id,
        tenant_id=membership.tenant_id,
        role=membership.role,
        token_version=user.token_version,
    )
    csrf = _set_session_cookies(
        response, settings, access=access, access_expires=access_exp, refresh=issued
    )
    await db.commit()
    return await _session_payload(
        resources, service, user, membership, csrf=csrf, access_expires=access_exp
    )


@router.post("/logout", response_model=OkResponse, summary="Đăng xuất (thu hồi refresh token)")
async def logout(
    request: Request,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> OkResponse:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        verify_csrf(request)
        await auth_service(db, settings, resources).revoke(raw)
    _clear_session_cookies(response)
    return OkResponse()


@router.post(
    "/switch-tenant", response_model=SessionOut, summary="Chuyển doanh nghiệp đang làm việc"
)
async def switch_tenant(
    data: SwitchTenantRequest,
    ctx: Ctx,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> SessionOut:
    service = auth_service(db, settings, resources)
    membership = await service.membership_for(ctx.principal.user_id, data.tenant_id)
    user = found(await db.get(User, ctx.principal.user_id))
    return await start_session(
        ctx.request, response, settings, resources, service, user, membership
    )


@router.get("/me", response_model=SessionOut, summary="Thông tin phiên hiện tại")
async def me(ctx: Ctx, resources: ResourcesDep, settings: SettingsDep) -> SessionOut:
    async with system_session(resources.session_factory) as db:
        service = auth_service(db, settings, resources)
        user = found(await db.get(User, ctx.principal.user_id))
        membership = (
            await db.execute(
                select(Membership).where(
                    Membership.user_id == ctx.principal.user_id,
                    Membership.tenant_id == ctx.principal.tenant_id,
                )
            )
        ).scalar_one()
        return await _session_payload(
            resources,
            service,
            user,
            membership,
            csrf=ctx.request.cookies.get(CSRF_COOKIE),
            access_expires=None,
        )


@router.patch("/me", response_model=UserOut, summary="Cập nhật hồ sơ cá nhân")
async def update_profile(data: UpdateProfileRequest, ctx: Ctx) -> UserOut:
    user = found(await ctx.db.get(User, ctx.principal.user_id))
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.locale is not None:
        user.locale = data.locale
    await ctx.db.flush()
    return UserOut.model_validate(user)


@router.post("/change-password", response_model=SessionOut, summary="Đổi mật khẩu")
async def change_password(
    data: ChangePasswordRequest,
    ctx: Ctx,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> SessionOut:
    service = auth_service(db, settings, resources)
    user = found(await db.get(User, ctx.principal.user_id))
    if not verify_password(data.current_password, user.password_hash):
        raise InvalidCredentialsError("Mật khẩu hiện tại không đúng.")
    await service.set_password(user, data.new_password)
    membership = await service.membership_for(user.id, ctx.principal.tenant_id)
    # Đăng nhập lại ngay trên thiết bị hiện tại; các thiết bị khác bị đăng xuất.
    return await start_session(
        ctx.request, response, settings, resources, service, user, membership
    )


@router.post(
    "/forgot-password",
    response_model=OkResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Gửi email đặt lại mật khẩu",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> OkResponse:
    await auth_service(db, settings, resources).forgot_password(
        data.email, ip_hash=client_ip_hash(request, settings)
    )
    return OkResponse()


@router.post("/reset-password", response_model=OkResponse, summary="Đặt lại mật khẩu bằng token")
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> OkResponse:
    from app.core.ratelimit import enforce

    await enforce(resources.limiter, f"reset:ip:{client_ip_hash(request, settings)}", 20, 3600)
    await auth_service(db, settings, resources).reset_password(data.token, data.password)
    return OkResponse()
