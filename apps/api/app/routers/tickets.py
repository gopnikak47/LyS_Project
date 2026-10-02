from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, AwareDatetime

from app.core.auth import Ctx
from app.models.enums import TicketPriority, TicketStatus
from app.services.tickets import TicketService, describe

router=APIRouter(prefix="/tickets",tags=["tickets"])


class TicketUpdate(BaseModel):
    status:TicketStatus|None=None
    priority:TicketPriority|None=None
    assignee_id:uuid.UUID|None=None
    due_at:AwareDatetime|None=None
    note:str|None=Field(default=None,max_length=2000)


@router.get("")
async def list_tickets(workspace_id:uuid.UUID,ctx:Ctx,status:TicketStatus|None=None,page:int=Query(1,ge=1))->dict[str,Any]:
    return await TicketService(ctx.db,ctx.principal).list(workspace_id,status,page)


@router.get("/metrics")
async def metrics(workspace_id:uuid.UUID,ctx:Ctx)->dict[str,Any]:
    return await TicketService(ctx.db,ctx.principal).metrics(workspace_id)


@router.get("/assignees")
async def assignees(workspace_id:uuid.UUID,ctx:Ctx)->list[dict]:
    from sqlalchemy import exists, or_, select
    from app.models import Membership, User, WorkspaceMember
    from app.models.enums import MembershipStatus, Role
    from app.services.workspaces import WorkspaceService
    await WorkspaceService(ctx.db,ctx.principal).get(workspace_id)
    scope=exists(select(WorkspaceMember.id).where(WorkspaceMember.workspace_id==workspace_id,WorkspaceMember.user_id==User.id,WorkspaceMember.tenant_id==ctx.principal.tenant_id))
    rows=(await ctx.db.execute(select(User.id,User.full_name).join(Membership,Membership.user_id==User.id).where(Membership.tenant_id==ctx.principal.tenant_id,Membership.status==MembershipStatus.ACTIVE,Membership.role.in_([Role.ADMIN,Role.ANALYST]),User.deleted_at.is_(None),or_(Membership.role==Role.ADMIN,Membership.all_workspaces.is_(True),scope)))).all()
    return [{"id":str(user_id),"name":name} for user_id,name in rows]


@router.get("/{ticket_id}")
async def detail(ticket_id:uuid.UUID,ctx:Ctx)->dict[str,Any]:
    return describe(await TicketService(ctx.db,ctx.principal).get(ticket_id))


@router.patch("/{ticket_id}")
async def update(ticket_id:uuid.UUID,data:TicketUpdate,ctx:Ctx)->dict[str,Any]:
    return describe(await TicketService(ctx.db,ctx.principal).update(ticket_id,data.model_dump(exclude_unset=True)))
