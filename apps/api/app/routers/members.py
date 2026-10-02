"""/api/v1/members, /api/v1/invitations, /api/v1/tenants/me (FR-03)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.auth import Ctx, ResourcesDep, SettingsDep
from app.core.errors import found
from app.core.permissions import Permission
from app.db.tenant import system_session
from app.models import Tenant
from app.schemas.auth import TenantOut
from app.schemas.common import ApiModel, Name, OkResponse
from app.schemas.members import (
    InvitationCreate,
    InvitationCreated,
    InvitationOut,
    MemberOut,
    MemberUpdate,
)
from app.services.auth import AuthService
from app.services.members import InvitationService, MemberService

router = APIRouter(tags=["members"])


@router.get("/members", response_model=list[MemberOut], summary="Danh sách thành viên")
async def list_members(ctx: Ctx) -> list[MemberOut]:
    ctx.principal.require(Permission.MEMBER_MANAGE)
    return await MemberService(ctx.db, ctx.principal).list_members()


@router.patch("/members/{membership_id}", response_model=MemberOut)
async def update_member(membership_id: uuid.UUID, data: MemberUpdate, ctx: Ctx) -> MemberOut:
    service = MemberService(ctx.db, ctx.principal)
    await service.update(membership_id, data)
    return next(m for m in await service.list_members() if m.id == membership_id)


@router.delete("/members/{membership_id}", response_model=OkResponse)
async def remove_member(
    membership_id: uuid.UUID, ctx: Ctx, resources: ResourcesDep, settings: SettingsDep
) -> OkResponse:
    user_id = await MemberService(ctx.db, ctx.principal).remove(membership_id)
    # Đăng xuất người bị xóa khỏi doanh nghiệp này trên mọi thiết bị.
    async with system_session(resources.session_factory) as db:
        await AuthService(db, settings, resources.limiter, resources.queue).revoke_all_for_user(
            user_id, tenant_id=ctx.principal.tenant_id
        )
    return OkResponse()


@router.get("/invitations", response_model=list[InvitationOut], summary="Lời mời đang chờ")
async def list_invitations(
    ctx: Ctx, settings: SettingsDep, resources: ResourcesDep
) -> list[InvitationOut]:
    ctx.principal.require(Permission.MEMBER_MANAGE)
    service = InvitationService(ctx.db, ctx.principal, settings, resources.queue)
    return [InvitationOut.model_validate(i) for i in await service.list_pending()]


@router.post("/invitations", response_model=InvitationCreated, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    data: InvitationCreate, ctx: Ctx, settings: SettingsDep, resources: ResourcesDep
) -> InvitationCreated:
    service = InvitationService(ctx.db, ctx.principal, settings, resources.queue)
    invitation, link = await service.create(data)
    return InvitationCreated(
        **InvitationOut.model_validate(invitation).model_dump(), invite_url=link
    )


@router.delete("/invitations/{invitation_id}", response_model=OkResponse)
async def revoke_invitation(
    invitation_id: uuid.UUID, ctx: Ctx, settings: SettingsDep, resources: ResourcesDep
) -> OkResponse:
    await InvitationService(ctx.db, ctx.principal, settings, resources.queue).revoke(invitation_id)
    return OkResponse()


class TenantUpdate(ApiModel):
    name: Name


@router.get("/tenants/me", response_model=TenantOut, tags=["tenants"])
async def get_tenant(ctx: Ctx) -> TenantOut:
    tenant = await ctx.db.get(Tenant, ctx.principal.tenant_id)
    return TenantOut.model_validate(tenant)


@router.patch("/tenants/me", response_model=TenantOut, tags=["tenants"])
async def update_tenant(data: TenantUpdate, ctx: Ctx) -> TenantOut:
    ctx.principal.require(Permission.TENANT_MANAGE)
    tenant = found(await ctx.db.get(Tenant, ctx.principal.tenant_id))
    tenant.name = data.name
    await ctx.db.flush()
    return TenantOut.model_validate(tenant)
