from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import select

from app.core.auth import Ctx
from app.core.errors import AppError
from app.core.permissions import Permission
from app.models import AuditLog, Plan, Tenant
from app.repositories.base import TenantRepository
from app.services.audit import audit
from app.services.billing import plan_for, usage

router=APIRouter(tags=["billing"])


@router.get("/billing/usage")
async def get_usage(ctx:Ctx)->dict:
    ctx.principal.require(Permission.TENANT_MANAGE)
    plan=await plan_for(ctx.db,ctx.principal.tenant_id)
    plans=(await ctx.db.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order))).scalars().all()
    return {"plan":plan.code,"usage":await usage(ctx.db,ctx.principal.tenant_id),"limits":plan.limits,"plans":[{"code":p.code,"name":p.name,"price_vnd":p.price_vnd,"limits":p.limits} for p in plans],"mock":True,"can_change":not ctx.settings.is_production}


class MockChange(BaseModel):
    plan_code:str=Field(pattern="^(free|pro|business)$")


@router.post("/billing/mock-subscription")
async def mock_change(data:MockChange,ctx:Ctx)->dict:
    ctx.principal.require(Permission.TENANT_MANAGE)
    if ctx.settings.is_production:
        raise AppError("Thanh toán giả lập chỉ dùng môi trường phát triển.",status_code=403)
    plan=(await ctx.db.execute(select(Plan).where(Plan.code==data.plan_code,Plan.is_active.is_(True)))).scalar_one()
    tenant=(await ctx.db.execute(select(Tenant).where(Tenant.id==ctx.principal.tenant_id).with_for_update())).scalar_one()
    current=await usage(ctx.db,tenant.id)
    if any(current.get(key,0)>limit for key,limit in plan.limits.items() if isinstance(limit,int)):
        raise AppError("Mức sử dụng hiện tại vượt giới hạn gói đã chọn.",status_code=409)
    tenant.plan_code=plan.code
    await audit(ctx.db,tenant_id=tenant.id,user_id=ctx.principal.user_id,action="billing.mock_change",data={"plan":plan.code})
    return {"mock":True,"charged":False,"plan":plan.code}


class AuditRepository(TenantRepository[AuditLog]):
    model=AuditLog


@router.get("/audit-logs")
async def logs(ctx:Ctx,page:int=Query(1,ge=1))->dict:
    ctx.principal.require(Permission.TENANT_MANAGE)
    repo=AuditRepository(ctx.db,ctx.principal.tenant_id)
    rows=await repo.list(order_by=AuditLog.created_at.desc(),limit=50,offset=(page-1)*50)
    return {"items":[{key:getattr(row,key) for key in ("id","user_id","action","entity_type","entity_id","created_at","request_id")} for row in rows],"total":await repo.count()}


@router.get("/metrics")
async def metrics(ctx:Ctx)->Response:
    ctx.principal.require(Permission.TENANT_MANAGE)
    return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)


@router.get("/observability")
async def observability(ctx:Ctx)->dict:
    ctx.principal.require(Permission.TENANT_MANAGE)
    from sqlalchemy import func
    from app.models import TextAnalysis
    counts=(await ctx.db.execute(select(TextAnalysis.status,func.count()).where(TextAnalysis.tenant_id==ctx.principal.tenant_id).group_by(TextAnalysis.status))).all()
    return {"analysis_statuses":dict(counts),"broker_default":await ctx.resources.redis.llen("default"),"broker_nlp":await ctx.resources.redis.llen("nlp")}
