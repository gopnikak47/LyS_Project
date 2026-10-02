from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.auth import RequestContext
from app.core.errors import AppError
from app.core.permissions import Permission
from app.models import ExportJob
from app.models.enums import ExportKind, JobStatus
from app.repositories.jobs import ExportRepository
from app.schemas.feedback import FeedbackFilter
from app.services.workspaces import WorkspaceService


class ExportService:
    def __init__(self, ctx: RequestContext) -> None:
        self.ctx = ctx
        self.repo = ExportRepository(ctx.db, ctx.principal.tenant_id)

    async def create(self, filters: FeedbackFilter, kind: ExportKind) -> ExportJob:
        self.ctx.principal.require(Permission.DATA_EXPORT)
        await WorkspaceService(self.ctx.db, self.ctx.principal).get(filters.workspace_id)
        if kind not in {ExportKind.XLSX, ExportKind.PDF}:
            raise AppError("Định dạng xuất chưa được hỗ trợ.")
        job = self.repo.add(ExportJob(workspace_id=filters.workspace_id, kind=kind, params={"filters": filters.model_dump(mode="json"), "anonymous": True}, created_by=self.ctx.principal.user_id, expires_at=datetime.now(UTC) + timedelta(days=7)))
        await self.ctx.db.flush()
        return job

    async def get(self, job_id: uuid.UUID) -> ExportJob:
        self.ctx.principal.require(Permission.DATA_EXPORT)
        job = await self.repo.get_or_404(job_id)
        if job.workspace_id is None:
            raise AppError("Tác vụ thiếu không gian khảo sát.")
        await WorkspaceService(self.ctx.db, self.ctx.principal).get(job.workspace_id)
        if job.expires_at and job.expires_at <= datetime.now(UTC):
            raise AppError("Báo cáo đã hết hạn.", status_code=410)
        return job


def describe(job: ExportJob) -> dict[str, Any]:
    return {"id": str(job.id), "kind": job.kind, "status": job.status, "filename": job.filename, "error_message": job.error_message, "expires_at": job.expires_at, "ready": job.status == JobStatus.DONE}
