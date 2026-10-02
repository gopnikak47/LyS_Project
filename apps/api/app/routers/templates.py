from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.auth import Ctx
from app.core.errors import NotFoundError
from app.domain.survey_templates import TEMPLATES
from app.schemas.surveys import QuestionInput, SurveyCreate, SurveyOut
from app.services.surveys import SurveyService

router = APIRouter(prefix="/templates", tags=["templates"])


class UseTemplate(BaseModel):
    workspace_id: uuid.UUID


@router.get("")
async def templates(ctx: Ctx) -> list[dict[str, str]]:
    return [{"code": code, "title": template["title"], "industry": template["industry"]} for code, template in TEMPLATES.items()]


@router.post("/{code}/use", response_model=SurveyOut, status_code=201)
async def use_template(code: str, data: UseTemplate, ctx: Ctx) -> SurveyOut:
    template = TEMPLATES.get(code)
    if template is None:
        raise NotFoundError()
    return await SurveyService(ctx.db, ctx.principal).create(SurveyCreate(workspace_id=data.workspace_id, title=template["title"], questions=[QuestionInput(code="rating", type="nps" if code == "nps" else "csat", title={"vi": template["rating"]}, required=True), QuestionInput(code="comment", type="text", title={"vi": template["comment"]}, config={"max_length": 5000})]))
