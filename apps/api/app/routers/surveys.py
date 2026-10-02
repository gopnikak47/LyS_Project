from __future__ import annotations

import io
import uuid
from html import escape
from typing import Annotated, Literal
from urllib.parse import urlencode

import segno
from fastapi import APIRouter, Query, Response

from app.core.auth import Ctx
from app.models.enums import SurveyStatus
from app.schemas.common import OkResponse, Page
from app.schemas.surveys import ShareOut, SurveyCreate, SurveyInput, SurveyOut
from app.services.surveys import SurveyService

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.get("", response_model=Page[SurveyOut])
async def list_surveys(ctx: Ctx, workspace_id: uuid.UUID, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str = Query("", max_length=300), status: SurveyStatus | None = None) -> Page[SurveyOut]:
    return await SurveyService(ctx.db, ctx.principal).list(workspace_id, page, page_size, search, status)


@router.post("", response_model=SurveyOut, status_code=201)
async def create(data: SurveyCreate, ctx: Ctx) -> SurveyOut:
    return await SurveyService(ctx.db, ctx.principal).create(data)


@router.get("/{survey_id}", response_model=SurveyOut)
async def detail(survey_id: uuid.UUID, ctx: Ctx) -> SurveyOut:
    service = SurveyService(ctx.db, ctx.principal)
    return await service.describe(await service.get(survey_id))


@router.put("/{survey_id}", response_model=SurveyOut)
async def save(survey_id: uuid.UUID, data: SurveyInput, ctx: Ctx) -> SurveyOut:
    return await SurveyService(ctx.db, ctx.principal).save(survey_id, data)


@router.post("/{survey_id}/publish", response_model=SurveyOut)
async def publish(survey_id: uuid.UUID, ctx: Ctx) -> SurveyOut:
    return await SurveyService(ctx.db, ctx.principal).publish(survey_id)


@router.post("/{survey_id}/close", response_model=SurveyOut)
async def close(survey_id: uuid.UUID, ctx: Ctx) -> SurveyOut:
    return await SurveyService(ctx.db, ctx.principal).close(survey_id)


@router.post("/{survey_id}/duplicate", response_model=SurveyOut, status_code=201)
async def duplicate(survey_id: uuid.UUID, ctx: Ctx) -> SurveyOut:
    return await SurveyService(ctx.db, ctx.principal).duplicate(survey_id)


@router.delete("/{survey_id}", response_model=OkResponse)
async def remove(survey_id: uuid.UUID, ctx: Ctx, confirm_title: str) -> OkResponse:
    from app.core.errors import AppError
    from app.core.permissions import Permission

    ctx.principal.require(Permission.SURVEY_EDIT)
    service = SurveyService(ctx.db, ctx.principal)
    survey = await service.get(survey_id, lock=True)
    if confirm_title != survey.title:
        raise AppError("Tên xác nhận không khớp.")
    await service.repo.soft_delete(survey)
    return OkResponse()


@router.get("/{survey_id}/share", response_model=ShareOut)
async def share(survey_id: uuid.UUID, ctx: Ctx, channel: Literal["link", "qr", "embed", "kiosk", "email"] = "link", branch: str = Query("", max_length=100), table: str = Query("", max_length=100)) -> ShareOut:
    survey = await SurveyService(ctx.db, ctx.principal).get(survey_id)
    url = f"{ctx.settings.public_base_url.rstrip('/')}/s/{survey.slug}?{urlencode({'channel': channel, 'branch': branch, 'table': table})}"
    return ShareOut(url=url, embed=f'<iframe src="{escape(url, quote=True)}" title="Khảo sát" width="100%" height="700" loading="lazy"></iframe>')


@router.get("/{survey_id}/qr")
async def qr(survey_id: uuid.UUID, ctx: Ctx, format: Literal["png", "svg"] = "png", scale: int = Query(8, ge=2, le=30), color: Annotated[str, Query(pattern=r"^#[0-9a-fA-F]{6}$")] = "#000000", branch: str = Query("", max_length=100), table: str = Query("", max_length=100)) -> Response:
    link = await share(survey_id, ctx, "qr", branch, table)
    output = io.BytesIO()
    segno.make(link.url, micro=False, error="h").save(output, kind=format, scale=scale, dark=color)
    return Response(output.getvalue(), media_type="image/svg+xml" if format == "svg" else "image/png", headers={"Content-Disposition": f'attachment; filename="survey-qr.{format}"'})
