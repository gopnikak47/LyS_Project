from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.auth import Ctx
from app.core.errors import AppError
from app.models import ImportJob
from app.services.imports import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])


def describe(job: ImportJob) -> dict[str, Any]:
    return {"id": str(job.id), "status": job.status, "total_rows": job.total_rows, "processed_rows": job.processed_rows, "success_rows": job.success_rows, "error_rows": job.error_rows, "error_message": job.error_message, "has_error_report": bool(job.error_report_key)}


class Mapping(BaseModel):
    columns: dict[str, str]


@router.post("", status_code=201)
async def upload(survey_id: uuid.UUID, file: UploadFile, ctx: Ctx) -> dict[str, Any]:
    return await ImportService(ctx).upload(survey_id, file)


@router.post("/{job_id}/start", status_code=202)
async def start(job_id: uuid.UUID, data: Mapping, ctx: Ctx) -> dict[str, Any]:
    return describe(await ImportService(ctx).start(job_id, data.columns))


@router.get("/{job_id}")
async def detail(job_id: uuid.UUID, ctx: Ctx) -> dict[str, Any]:
    return describe(await ImportService(ctx).get(job_id))


@router.get("/{job_id}/errors")
async def errors(job_id: uuid.UUID, ctx: Ctx) -> FileResponse:
    service = ImportService(ctx)
    job = await service.get(job_id)
    if not job.error_report_key:
        raise AppError("Báo cáo lỗi chưa sẵn sàng.", status_code=409)
    return FileResponse(service.storage.path(job.error_report_key), media_type="text/csv", filename="import-errors.csv")
