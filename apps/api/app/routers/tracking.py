from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from app.core.auth import ResourcesDep, SettingsDep, load_principal
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.permissions import Permission
from app.core.resources import Resources
from app.core.storage import LocalStorage
from app.db.tenant import tenant_session
from app.models import EmailDelivery, ExportJob, Survey
from app.models.enums import JobStatus
from app.services.workspaces import WorkspaceService

router = APIRouter(prefix="/public", tags=["public"])


def decode(token: str, audience: str, settings: Settings) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, settings.secret_key.get_secret_value(), algorithms=["HS256"], audience=audience
        )
    except jwt.PyJWTError as exc:
        raise NotFoundError("Liên kết không hợp lệ hoặc đã hết hạn.") from exc


async def track(token: str, kind: str, settings: Settings, resources: Resources) -> str:
    claims = decode(token, "survey-invitation", settings)
    async with tenant_session(resources.session_factory, uuid.UUID(claims["tenant"])) as db:
        row = (
            await db.execute(
                select(EmailDelivery)
                .where(
                    EmailDelivery.id == uuid.UUID(claims["sub"]),
                    EmailDelivery.tenant_id == uuid.UUID(claims["tenant"]),
                    EmailDelivery.kind == "invitation",
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundError()
        survey = (
            await db.execute(
                select(Survey).where(
                    Survey.id == row.survey_id,
                    Survey.tenant_id == row.tenant_id,
                    Survey.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if survey is None:
            raise NotFoundError()
        setattr(row, kind, getattr(row, kind) or datetime.now(UTC))
        return survey.slug


@router.get("/email/{token}/open")
async def opened(token: str, settings: SettingsDep, resources: ResourcesDep) -> Response:
    await track(token, "opened_at", settings, resources)
    return Response(
        bytes.fromhex(
            "47494638396101000100800000ffffff00000021f90401000000002c00000000010001000002024401003b"
        ),
        media_type="image/gif",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/email/{token}/click")
async def clicked(token: str, settings: SettingsDep, resources: ResourcesDep) -> RedirectResponse:
    slug = await track(token, "clicked_at", settings, resources)
    return RedirectResponse(f"/s/{slug}?channel=email&invitation={token}", status_code=303)


@router.get("/reports/{token}")
async def shared_report(token: str, settings: SettingsDep, resources: ResourcesDep) -> FileResponse:
    claims = decode(token, "report-share", settings)
    async with tenant_session(resources.session_factory, uuid.UUID(claims["tenant"])) as db:
        job = (
            await db.execute(
                select(ExportJob).where(
                    ExportJob.id == uuid.UUID(claims["sub"]),
                    ExportJob.tenant_id == uuid.UUID(claims["tenant"]),
                )
            )
        ).scalar_one_or_none()
        if (
            job is None
            or job.status != JobStatus.DONE
            or not job.file_key
            or not job.created_by
            or not job.workspace_id
            or (job.expires_at and job.expires_at <= datetime.now(UTC))
        ):
            raise NotFoundError()
        principal = await load_principal(db, job.created_by, job.tenant_id, None)
        principal.require(Permission.DATA_EXPORT)
        await WorkspaceService(db, principal).get(job.workspace_id)
        path = LocalStorage(settings.storage_local_root).path(job.file_key)
        return FileResponse(path, filename=job.filename, headers={"Cache-Control": "no-store"})
