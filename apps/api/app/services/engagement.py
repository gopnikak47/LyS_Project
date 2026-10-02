from __future__ import annotations

import uuid
from typing import Any, Protocol

from pydantic import AwareDatetime, BaseModel, EmailStr, Field

from app.core.auth import RequestContext
from app.core.permissions import Permission
from app.models import EmailDelivery, ReportSchedule
from app.repositories.base import TenantRepository
from app.schemas.feedback import FeedbackFilter
from app.services.surveys import SurveyService
from app.services.workspaces import WorkspaceService


class ZaloZnsProvider(Protocol):
    def send(self, phone: str, template_id: str, params: dict[str, str]) -> str: ...


class MockZaloZnsProvider:
    def send(self, phone: str, template_id: str, params: dict[str, str]) -> str:
        return f"mock:{uuid.uuid4()}"


class ScheduleRepository(TenantRepository[ReportSchedule]):
    model = ReportSchedule


class CampaignInput(BaseModel):
    recipients: list[EmailStr] = Field(min_length=1, max_length=500)


class ScheduleInput(BaseModel):
    workspace_id: uuid.UUID
    recipients: list[EmailStr] = Field(min_length=1, max_length=20)
    cadence: str = Field(pattern="^(day|week|month)$")
    next_run_at: AwareDatetime
    filters: dict[str, Any] = Field(default_factory=dict)


async def campaign(
    ctx: RequestContext, survey_id: uuid.UUID, data: CampaignInput
) -> dict[str, Any]:
    ctx.principal.require(Permission.SURVEY_EDIT)
    survey = await SurveyService(ctx.db, ctx.principal).get(survey_id)
    batch = uuid.uuid4()
    for email in set(data.recipients):
        ctx.db.add(
            EmailDelivery(
                tenant_id=survey.tenant_id,
                workspace_id=survey.workspace_id,
                survey_id=survey.id,
                recipient=str(email),
                kind="invitation",
                dedupe_key=f"invite:{batch}:{email}",
                payload={
                    "title": survey.title,
                    "slug": survey.slug,
                    "created_by": str(ctx.principal.user_id),
                },
            )
        )
    await ctx.db.flush()
    return {"campaign_id": str(batch), "queued": len(set(data.recipients))}


async def create_schedule(ctx: RequestContext, data: ScheduleInput) -> ReportSchedule:
    ctx.principal.require(Permission.DATA_EXPORT)
    await WorkspaceService(ctx.db, ctx.principal).get(data.workspace_id)
    filters = FeedbackFilter.model_validate({**data.filters, "workspace_id": data.workspace_id})
    schedule = ScheduleRepository(ctx.db, ctx.principal.tenant_id).add(
        ReportSchedule(
            workspace_id=data.workspace_id,
            created_by=ctx.principal.user_id,
            recipients=[str(e) for e in data.recipients],
            cadence=data.cadence,
            next_run_at=data.next_run_at,
            filters=filters.model_dump(mode="json"),
        )
    )
    await ctx.db.flush()
    return schedule
