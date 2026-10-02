"""Endpoint công khai không cần đăng nhập: /api/v1/public/* (lời mời; khảo sát ở GĐ 4–5)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, UploadFile, Form

from app.core.auth import ResourcesDep, SettingsDep, SystemDB, client_ip_hash
from app.core.ratelimit import enforce
from app.routers.auth import auth_service, start_session
from app.schemas.auth import SessionOut
from app.schemas.members import InvitationAccept, PublicInvitationOut
from app.services.members import accept_invitation, describe_invitation
from app.schemas.respondent import Submission, SubmissionResult
from app.services import respondent

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/assets/{token}")
async def public_asset(token: str, settings: SettingsDep):
    import jwt
    from fastapi.responses import FileResponse
    from app.core.errors import NotFoundError
    from app.core.storage import LocalStorage
    try:
        claims = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=["HS256"], audience="public-asset")
        path = LocalStorage(settings.storage_local_root).path(claims["key"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise NotFoundError() from exc
    if not path.is_file():
        raise NotFoundError()
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/surveys/{slug}")
async def public_survey(slug: str, db: SystemDB) -> dict:
    survey = await respondent.resolve(db, slug)
    respondent.require_open(survey)
    snapshot = await respondent.snapshot(db, survey)
    return respondent.public_snapshot(snapshot)


@router.post("/surveys/{slug}/uploads", status_code=201)
async def upload_response_file(slug: str, request: Request, file: UploadFile, db: SystemDB, settings: SettingsDep, resources: ResourcesDep, token: str = Form(...)) -> dict:
    import asyncio
    import secrets
    import time
    import jwt
    from pathlib import Path
    from app.core.errors import AppError
    from app.core.storage import LocalStorage
    from app.core.uploads import scan_file

    ip = client_ip_hash(request, settings)
    await enforce(resources.limiter, f"survey-upload:{ip}", 20, 3600)
    survey = await respondent.resolve(db, slug)
    respondent.require_open(survey)
    try:
        claims = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=["HS256"], audience="survey-submit")
    except jwt.PyJWTError as exc:
        raise AppError("Phiên tải tệp không hợp lệ.") from exc
    if claims.get("sub") != str(survey.id) or claims.get("ip") != ip:
        raise AppError("Phiên tải tệp không hợp lệ.")
    config = await respondent.snapshot(db, survey)
    if not any(q["type"] == "upload" for q in config["questions"]):
        raise AppError("Khảo sát không nhận tệp.")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise AppError("Tệp vượt giới hạn 5MB.", status_code=413)
    suffix = ".png" if content.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if content.startswith(b"\xff\xd8\xff") else ".pdf" if content.startswith(b"%PDF-") else None
    if suffix is None:
        raise AppError("Chỉ nhận PNG, JPEG, PDF hợp lệ.")
    await asyncio.to_thread(scan_file, content, settings.upload_scanner_host, settings.upload_scanner_port)
    key = f"{survey.tenant_id}/uploads/{survey.id}/{claims['jti']}/{secrets.token_hex(16)}{suffix}"
    await asyncio.to_thread(LocalStorage(settings.storage_local_root).put, key, content)
    proof = jwt.encode({"aud": "survey-upload", "sub": str(survey.id), "jti": claims["jti"], "key": key, "exp": int(time.time()) + 7200}, settings.secret_key.get_secret_value(), algorithm="HS256")
    return {"key": key, "filename": Path(file.filename or "file").name[:200], "size": len(content), "scanned": True, "proof": proof}


@router.post("/surveys/{slug}/session")
async def survey_session(slug: str, request: Request, db: SystemDB, settings: SettingsDep, resources: ResourcesDep) -> dict[str, str]:
    ip = client_ip_hash(request, settings)
    await enforce(resources.limiter, f"survey-session:{ip}", 60, 3600)
    survey = await respondent.resolve(db, slug)
    respondent.require_open(survey)
    import jwt
    from app.domain.quiz import questions_for_attempt
    token = respondent.issue_token(survey, settings, ip)
    claims = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=["HS256"], audience="survey-submit")
    config = await respondent.snapshot(db, survey)
    return {"token": token, "survey": respondent.public_snapshot({**config, "questions": questions_for_attempt(config, claims["jti"])}), "started_at": claims["iat"]}


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
