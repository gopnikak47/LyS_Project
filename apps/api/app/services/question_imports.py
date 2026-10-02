from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.auth import RequestContext
from app.core.errors import AppError
from app.core.permissions import Permission
from app.core.storage import LocalStorage
from app.domain.tabular import rows
from app.schemas.surveys import Choice, QuestionInput, SurveyInput, SurveyOut
from app.services.surveys import SurveyService


async def import_questions(
    ctx: RequestContext, survey_id: uuid.UUID, file: UploadFile
) -> SurveyOut:
    ctx.principal.require(Permission.SURVEY_EDIT)
    service = SurveyService(ctx.db, ctx.principal)
    survey = await service.describe(await service.get(survey_id))
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise AppError("Chỉ nhận CSV/XLSX.")
    content = await file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise AppError("Bảng câu hỏi tối đa 2MB.", status_code=413)
    storage = LocalStorage(ctx.settings.storage_local_root)
    key = f"{ctx.principal.tenant_id}/question-imports/{uuid.uuid4()}{suffix}"
    await asyncio.to_thread(storage.put, key, content)
    values = await asyncio.to_thread(lambda: list(rows(storage.path(key))))
    if not 1 <= len(values) <= 100:
        raise AppError("Bảng cần 1–100 câu hỏi.")
    questions = []
    for number, value in enumerate(values, 2):
        try:
            choices = [
                Choice(value=f"option-{index + 1}", label={"vi": label})
                for index, label in enumerate(value.get("options_vi", "").split("|"))
                if label
            ]
            config = json.loads(value.get("config_json") or "{}")
            questions.append(
                QuestionInput.model_validate(
                    {
                        "code": value["code"],
                        "type": value["type"],
                        "title": {"vi": value["title_vi"], "en": value.get("title_en", "")},
                        "required": value.get("required", "").lower() in {"true", "1", "yes"},
                        "options": choices,
                        "config": config,
                        "points": float(value["points"]) if value.get("points") else None,
                    }
                )
            )
        except (KeyError, ValueError) as exc:
            raise AppError(f"Câu hỏi tại dòng {number} không hợp lệ.") from exc
    data = SurveyInput.model_validate(
        {
            **survey.model_dump(mode="json"),
            "questions": questions,
            "expected_updated_at": survey.updated_at,
        }
    )
    return await service.save(survey_id, data)
