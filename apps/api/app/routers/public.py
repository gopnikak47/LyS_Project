"""Endpoint công khai không cần đăng nhập: /api/v1/public/* (lời mời; khảo sát ở GĐ 4–5)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.auth import ResourcesDep, SettingsDep, SystemDB, client_ip_hash
from app.core.ratelimit import enforce
from app.routers.auth import auth_service, start_session
from app.schemas.auth import SessionOut
from app.schemas.members import InvitationAccept, PublicInvitationOut
from app.services.members import accept_invitation, describe_invitation
from app.schemas.respondent import Submission, SubmissionResult
from app.services import respondent

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/surveys/{slug}")
async def public_survey(slug: str, db: SystemDB) -> dict:
    survey = await respondent.resolve(db, slug)
    respondent.require_open(survey)
    return await respondent.snapshot(db, survey)


@router.post("/surveys/{slug}/session")
async def survey_session(slug: str, request: Request, db: SystemDB, settings: SettingsDep, resources: ResourcesDep) -> dict[str, str]:
    ip = client_ip_hash(request, settings)
    await enforce(resources.limiter, f"survey-session:{ip}", 60, 3600)
    survey = await respondent.resolve(db, slug)
    respondent.require_open(survey)
    return {"token": respondent.issue_token(survey, settings, ip)}


@router.post("/surveys/{slug}/responses", response_model=SubmissionResult, status_code=201)
async def survey_response(slug: str, data: Submission, request: Request, db: SystemDB, settings: SettingsDep, resources: ResourcesDep) -> SubmissionResult:
    ip = client_ip_hash(request, settings)
    await enforce(resources.limiter, f"survey-submit:{ip}", 30, 3600)
    survey = await respondent.resolve(db, slug)
    tenant_id = str(survey.tenant_id)
    result = await respondent.submit(db, survey, data, settings, ip)
    await db.commit()
    try:
        resources.queue.send("worker.tasks.nlp.analyze_response", kwargs={"tenant_id": tenant_id, "response_id": result.response_id}, queue="nlp")
    except Exception:
        from app.core.logging import get_logger
        get_logger(__name__).exception("nlp_dispatch_failed", response_id=result.response_id)
    return result


@router.get("/invitations/{token}", response_model=PublicInvitationOut)
async def get_invitation(
    token: str, request: Request, db: SystemDB, settings: SettingsDep, resources: ResourcesDep
) -> PublicInvitationOut:
    await enforce(resources.limiter, f"invite:ip:{client_ip_hash(request, settings)}", 60, 3600)
    return await describe_invitation(db, token)


@router.post("/invitations/{token}/accept", response_model=SessionOut)
async def accept(
    token: str,
    data: InvitationAccept,
    request: Request,
    response: Response,
    db: SystemDB,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> SessionOut:
    await enforce(resources.limiter, f"invite:ip:{client_ip_hash(request, settings)}", 60, 3600)
    user, membership = await accept_invitation(
        db, token, full_name=data.full_name, password=data.password, settings=settings
    )
    service = auth_service(db, settings, resources)
    return await start_session(request, response, settings, resources, service, user, membership)
