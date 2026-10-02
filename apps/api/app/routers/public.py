"""Endpoint công khai không cần đăng nhập: /api/v1/public/* (lời mời; khảo sát ở GĐ 4–5)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.auth import ResourcesDep, SettingsDep, SystemDB, client_ip_hash
from app.core.ratelimit import enforce
from app.routers.auth import auth_service, start_session
from app.schemas.auth import SessionOut
from app.schemas.members import InvitationAccept, PublicInvitationOut
from app.services.members import accept_invitation, describe_invitation

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/invitations/{token}", response_model=PublicInvitationOut)
async def get_invitation(
    token: str, request: Request, db: SystemDB, settings: SettingsDep, resources: ResourcesDep
) -> PublicInvitationOut:
    await enforce(resources.limiter, f"invite:ip:{client_ip_hash(request, settings)}", 60, 3600)
    return await describe_invitation(db, token)


@router.post("/invitations/{token}/accept", response_model=SessionOut)
async def accept(
    token: str,
    data: InvitationAccept,
    request: Request,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> SessionOut:
    await enforce(resources.limiter, f"invite:ip:{client_ip_hash(request, settings)}", 60, 3600)
    user, membership = await accept_invitation(
        db, token, full_name=data.full_name, password=data.password, settings=settings
    )
    service = auth_service(db, settings, resources)
    return await start_session(request, response, settings, resources, service, user, membership)
