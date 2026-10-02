from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.auth import Ctx
from app.core.permissions import Permission
from app.models import EmailDelivery, ReportSchedule
from app.schemas.feedback import FeedbackFilter
from app.services.engagement import CampaignInput, ScheduleInput, ScheduleRepository, campaign, create_schedule
from app.services.surveys import SurveyService
from app.services.workspaces import WorkspaceService

router=APIRouter(tags=["engagement"])


@router.post("/surveys/{survey_id}/email-invitations",status_code=202)
async def send_campaign(survey_id:uuid.UUID,data:CampaignInput,ctx:Ctx)->dict:
    return await campaign(ctx,survey_id,data)


@router.get("/surveys/{survey_id}/email-invitations")
async def campaign_metrics(survey_id:uuid.UUID,ctx:Ctx)->dict:
    await SurveyService(ctx.db,ctx.principal).get(survey_id)
    row=(await ctx.db.execute(select(func.count(),func.count().filter(EmailDelivery.sent_at.is_not(None)),func.count().filter(EmailDelivery.opened_at.is_not(None)),func.count().filter(EmailDelivery.clicked_at.is_not(None))).where(EmailDelivery.tenant_id==ctx.principal.tenant_id,EmailDelivery.survey_id==survey_id,EmailDelivery.kind=="invitation"))).one()
    return dict(zip(["queued","sent","opened","clicked"],row,strict=True))


@router.post("/report-schedules",status_code=201)
async def schedule(data:ScheduleInput,ctx:Ctx)->dict:
    job=await create_schedule(ctx,data);return {"id":str(job.id)}


@router.get("/report-schedules")
async def schedules(workspace_id:uuid.UUID,ctx:Ctx)->list[dict]:
    ctx.principal.require(Permission.DATA_EXPORT)
    await WorkspaceService(ctx.db,ctx.principal).get(workspace_id)
    rows=await ScheduleRepository(ctx.db,ctx.principal.tenant_id).list(ReportSchedule.workspace_id==workspace_id)
    return [{key:getattr(row,key) for key in ("id","recipients","cadence","next_run_at","enabled")} for row in rows]


@router.delete("/report-schedules/{schedule_id}")
async def delete_schedule(schedule_id:uuid.UUID,ctx:Ctx)->dict:
    ctx.principal.require(Permission.DATA_EXPORT)
    row=await ScheduleRepository(ctx.db,ctx.principal.tenant_id).get_or_404(schedule_id)
    await WorkspaceService(ctx.db,ctx.principal).get(row.workspace_id)
    row.enabled=False;return {"ok":True}
