from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.auth import Ctx
from app.core.errors import AppError
from app.core.storage import LocalStorage
from app.models.enums import ExportKind, JobStatus
from app.schemas.feedback import FeedbackFilter
from app.services.exports import ExportService, describe

router = APIRouter(prefix="/exports", tags=["exports"])


class ExportRequest(BaseModel):
    filters: FeedbackFilter
    kind: ExportKind


@router.post("", status_code=202)
async def create(data: ExportRequest, ctx: Ctx) -> dict[str, Any]:
    return describe(await ExportService(ctx).create(data.filters, data.kind))


@router.get("/{job_id}")
async def detail(job_id: uuid.UUID, ctx: Ctx) -> dict[str, Any]:
    return describe(await ExportService(ctx).get(job_id))


@router.get("/{job_id}/download")
async def download(job_id: uuid.UUID, ctx: Ctx) -> FileResponse:
    job = await ExportService(ctx).get(job_id)
    if job.status != JobStatus.DONE or not job.file_key:
        raise AppError("Báo cáo chưa sẵn sàng.", status_code=409)
    return FileResponse(LocalStorage(ctx.settings.storage_local_root).path(job.file_key), filename=job.filename, media_type="application/pdf" if job.kind == ExportKind.PDF else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
