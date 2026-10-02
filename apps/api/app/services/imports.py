from __future__ import annotations

import asyncio
import uuid
from itertools import islice
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.auth import RequestContext
from app.core.errors import AppError
from app.core.permissions import Permission
from app.core.storage import LocalStorage
from app.domain.tabular import rows
from app.models import ImportJob
from app.models.enums import ImportKind
from app.repositories.jobs import ImportRepository
from app.services.surveys import SurveyService
from app.services.workspaces import WorkspaceService


class ImportService:
    def __init__(self, ctx: RequestContext) -> None:
        self.ctx = ctx
        self.repo = ImportRepository(ctx.db, ctx.principal.tenant_id)
        self.storage = LocalStorage(ctx.settings.storage_local_root)

    async def get(self, job_id: uuid.UUID) -> ImportJob:
        job = await self.repo.get_or_404(job_id)
        await WorkspaceService(self.ctx.db, self.ctx.principal).get(job.workspace_id)
        return job

    async def upload(self, survey_id: uuid.UUID, file: UploadFile) -> dict[str, Any]:
        self.ctx.principal.require(Permission.SURVEY_EDIT)
        survey = await SurveyService(self.ctx.db, self.ctx.principal).get(survey_id)
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".csv", ".xlsx"}:
            raise AppError("Chỉ nhận tệp CSV UTF-8 hoặc XLSX.")
        content = await file.read(20 * 1024 * 1024 + 1)
        if len(content) > 20 * 1024 * 1024:
            raise AppError("Dung lượng tối đa 20MB.", status_code=413)
        if suffix == ".xlsx" and not content.startswith(b"PK\x03\x04"):
            raise AppError("Tệp không phải XLSX hợp lệ.")
        job_id = uuid.uuid4()
        key = f"{survey.tenant_id}/imports/{job_id}/input{suffix}"
        await asyncio.to_thread(self.storage.put, key, content)
        try:
            preview = await asyncio.to_thread(
                lambda: list(islice(rows(self.storage.path(key)), 20))
            )
        except (ValueError, OSError, UnicodeError) as exc:
            raise AppError("Không đọc được tệp CSV/XLSX.") from exc
        if not preview:
            raise AppError("Tệp không có dữ liệu.")
        job = self.repo.add(
            ImportJob(
                id=job_id,
                workspace_id=survey.workspace_id,
                survey_id=survey.id,
                kind=ImportKind.RESPONSES,
                original_filename=(file.filename or "import")[:300],
                file_key=key,
                created_by=self.ctx.principal.user_id,
            )
        )
        await self.ctx.db.flush()
        return {"id": str(job.id), "columns": list(preview[0]), "preview": preview}

    async def start(self, job_id: uuid.UUID, mapping: dict[str, str]) -> ImportJob:
        self.ctx.principal.require(Permission.SURVEY_EDIT)
        await self.get(job_id)
        job: ImportJob = (
            await self.ctx.db.execute(
                self.repo._scoped().where(ImportJob.id == job_id).with_for_update()
            )
        ).scalar_one()
        if job.mapping:
            raise AppError("Tác vụ đã được bắt đầu.", status_code=409)
        if job.survey_id is None:
            raise AppError("Tác vụ thiếu khảo sát.")
        if job.survey_id is None:
            raise AppError("Tác vụ thiếu khảo sát.")
        survey = await SurveyService(self.ctx.db, self.ctx.principal).describe(
            await SurveyService(self.ctx.db, self.ctx.principal).get(job.survey_id)
        )
        allowed = {q.code for q in survey.questions}
        columns = set(next(rows(self.storage.path(job.file_key))))
        if not mapping or set(mapping) - allowed or set(mapping.values()) - columns:
            raise AppError("Ánh xạ cột không hợp lệ.")
        if any(q.required and q.code not in mapping for q in survey.questions):
            raise AppError("Cần ánh xạ tất cả câu hỏi bắt buộc.")
        job.mapping = {
            "columns": mapping,
            "questions": [q.model_dump(mode="json") for q in survey.questions],
            "version_id": str(survey.current_version_id) if survey.current_version_id else None,
        }
        await self.ctx.db.flush()
        # Commit ở dependency trước dispatch: quét bù cũng tìm job pending đã có mapping.
        return job
