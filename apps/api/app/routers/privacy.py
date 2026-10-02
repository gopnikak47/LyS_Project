"""Tenant administrator erasure by response ID; no public identity lookup."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi import Response as HttpResponse
from pydantic import BaseModel
from sqlalchemy import delete, select, update

from app.core.auth import Ctx
from app.core.errors import AppError, found
from app.core.logging import get_logger
from app.core.permissions import Permission
from app.core.storage import LocalStorage
from app.models import (
    Answer,
    EmailDelivery,
    ExportJob,
    ImportJob,
    Response,
    Survey,
    TextAnalysis,
    Ticket,
)
from app.models.enums import JobStatus
from app.services.audit import audit
from app.services.workspaces import WorkspaceService

router = APIRouter(prefix="/privacy", tags=["privacy"])


class Erasure(BaseModel):
    confirm_response_id: uuid.UUID


@router.delete("/responses/{response_id}", status_code=204)
async def erase(response_id: uuid.UUID, data: Erasure, ctx: Ctx) -> HttpResponse:
    ctx.principal.require(Permission.TENANT_MANAGE)
    if data.confirm_response_id != response_id:
        raise AppError("Xác nhận mã phản hồi không khớp.")
    # Serialize with submissions, imports and exports on the same workspace.
    row = found(
        (
            await ctx.db.execute(
                select(Response).where(
                    Response.id == response_id,
                    Response.tenant_id == ctx.principal.tenant_id,
                )
            )
        ).scalar_one_or_none()
    )
    await WorkspaceService(ctx.db, ctx.principal).get(row.workspace_id)
    export_jobs = (
        (
            await ctx.db.execute(
                select(ExportJob)
                .where(
                    ExportJob.tenant_id == ctx.principal.tenant_id,
                    ExportJob.workspace_id == row.workspace_id,
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    import_jobs = (
        (
            await ctx.db.execute(
                select(ImportJob)
                .where(
                    ImportJob.tenant_id == ctx.principal.tenant_id,
                    ImportJob.workspace_id == row.workspace_id,
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    files = {job.file_key for job in export_jobs if job.file_key}
    files.update(job.file_key for job in import_jobs)
    files.update(job.error_report_key for job in import_jobs if job.error_report_key)
    uploads = (
        await ctx.db.execute(
            select(Answer.value).where(
                Answer.tenant_id == ctx.principal.tenant_id,
                Answer.response_id == response_id,
                Answer.question_type == "upload",
            )
        )
    ).scalars()
    for value in uploads:
        if isinstance(value, dict) and isinstance(value.get("key"), str):
            files.add(value["key"])
    analysis_ids = (
        (
            await ctx.db.execute(
                select(TextAnalysis.id)
                .where(
                    TextAnalysis.tenant_id == ctx.principal.tenant_id,
                    TextAnalysis.response_id == response_id,
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    # Wait for analysis workers before taking the response lock, matching their FK writes.
    row = found(
        (
            await ctx.db.execute(
                select(Response)
                .where(
                    Response.tenant_id == ctx.principal.tenant_id,
                    Response.id == response_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
    )
    await ctx.db.execute(
        delete(EmailDelivery).where(
            EmailDelivery.tenant_id == ctx.principal.tenant_id,
            EmailDelivery.payload["analysis_id"].astext.in_([str(value) for value in analysis_ids]),
        )
    )
    survey = (
        await ctx.db.execute(
            select(Survey)
            .where(
                Survey.id == row.survey_id,
                Survey.tenant_id == ctx.principal.tenant_id,
            )
            .with_for_update()
        )
    ).scalar_one()
    # Cascades remove answers, analyses and correction history. Tickets retain free text,
    # so remove them explicitly instead of leaving SET NULL references.
    await ctx.db.execute(
        delete(Ticket).where(
            Ticket.tenant_id == ctx.principal.tenant_id,
            Ticket.response_id == response_id,
        )
    )
    await ctx.db.execute(
        delete(Response).where(
            Response.tenant_id == ctx.principal.tenant_id,
            Response.id == response_id,
        )
    )
    survey.response_count = max(0, survey.response_count - 1)
    # Invalidate derived files, including signed report links. Source imports may contain
    # the original record; revoke them so retry cannot resurrect erased data.
    await ctx.db.execute(
        update(ExportJob)
        .where(
            ExportJob.tenant_id == ctx.principal.tenant_id,
            ExportJob.workspace_id == row.workspace_id,
        )
        .values(
            status=JobStatus.FAILED,
            file_key=None,
            expires_at=datetime.now(UTC),
            error_message="DATA_ERASED",
        )
    )
    await ctx.db.execute(
        update(ImportJob)
        .where(
            ImportJob.tenant_id == ctx.principal.tenant_id,
            ImportJob.workspace_id == row.workspace_id,
        )
        .values(status=JobStatus.FAILED, error_report_key=None, error_message="DATA_ERASED")
    )
    await audit(
        ctx.db,
        tenant_id=ctx.principal.tenant_id,
        user_id=ctx.principal.user_id,
        action="privacy.erase",
        entity_type="response",
        entity_id=response_id,
    )
    await ctx.db.commit()
    storage = LocalStorage(ctx.settings.storage_local_root)
    for key in files:
        if key.startswith(f"{ctx.principal.tenant_id}/"):
            try:
                await asyncio.to_thread(storage.delete, key)
            except OSError:
                get_logger(__name__).exception("erasure_file_cleanup_failed", key=key)
    return HttpResponse(status_code=204)
