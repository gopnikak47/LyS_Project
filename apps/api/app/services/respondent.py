"""Phân giải slug bằng phiên hệ thống, mọi ghi dữ liệu dùng RLS đúng tenant."""
from __future__ import annotations

import secrets
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, found
from app.core.security import hash_identifier
from app.db.tenant import apply_tenant_context
from app.domain.question_types import validate_answers
from app.models import Answer, Response, Survey, SurveyVersion, Tenant, TextAnalysis, Workspace
from app.models.enums import AnalysisStatus, SurveyStatus, TenantStatus
from app.schemas.respondent import Submission, SubmissionResult


async def resolve(db: AsyncSession, slug: str) -> Survey:
    survey = (await db.execute(select(Survey).join(Workspace, Workspace.id == Survey.workspace_id).join(Tenant, Tenant.id == Survey.tenant_id).where(Survey.slug == slug, Survey.deleted_at.is_(None), Workspace.deleted_at.is_(None), Tenant.deleted_at.is_(None), Tenant.status == TenantStatus.ACTIVE))).scalar_one_or_none()
    if survey is None or survey.current_version_id is None:
        raise NotFoundError("Không tìm thấy khảo sát.")
    return survey


def require_open(survey: Survey) -> None:
    now = datetime.now(UTC)
    if survey.status != SurveyStatus.PUBLISHED or (survey.opens_at and survey.opens_at > now) or (survey.closes_at and survey.closes_at <= now):
        raise AppError("Khảo sát hiện không nhận phản hồi. Cảm ơn bạn đã quan tâm!", code="SURVEY_CLOSED", status_code=410)
    limit = survey.settings.get("max_responses")
    if isinstance(limit, int) and limit > 0 and survey.response_count >= limit:
        raise AppError("Khảo sát đã nhận đủ phản hồi.", code="SURVEY_FULL", status_code=410)


async def snapshot(db: AsyncSession, survey: Survey) -> dict[str, Any]:
    version = found((await db.execute(select(SurveyVersion).where(SurveyVersion.id == survey.current_version_id, SurveyVersion.tenant_id == survey.tenant_id, SurveyVersion.survey_id == survey.id))).scalar_one_or_none())
    return version.snapshot


def public_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    # Tách cấu hình nội bộ và đáp án đúng khỏi bản gửi cho khách.
    import copy
    result = copy.deepcopy(snapshot)
    settings = result.get("settings", {})
    result["settings"] = {key: settings[key] for key in ("thank_you", "quiz_duration_seconds", "quiz_show_result", "randomize_questions", "randomize_options") if key in settings}
    for question in result["questions"]:
        question.get("config", {}).pop("correct_answer", None)
    return result


def issue_token(survey: Survey, settings: Settings, ip_hash: str | None) -> str:
    now = int(time.time())
    return jwt.encode({"aud": "survey-submit", "sub": str(survey.id), "version": str(survey.current_version_id), "jti": secrets.token_urlsafe(24), "iat": now, "exp": now + 7200, "ip": ip_hash}, settings.secret_key.get_secret_value(), algorithm="HS256")


async def submit(db: AsyncSession, survey: Survey, data: Submission, settings: Settings, ip_hash: str | None) -> SubmissionResult:
    try:
        token = jwt.decode(data.token, settings.secret_key.get_secret_value(), algorithms=["HS256"], audience="survey-submit", options={"require": ["exp", "iat", "sub", "jti", "version"]})
    except jwt.PyJWTError as exc:
        raise AppError("Phiên khảo sát đã hết hạn. Vui lòng tải lại trang.", code="TOKEN_INVALID") from exc
    if token["sub"] != str(survey.id) or token.get("ip") != ip_hash or data.honeypot:
        raise AppError("Phiên khảo sát không hợp lệ.", code="TOKEN_INVALID")
    await apply_tenant_context(db, survey.tenant_id)
    # Khóa khảo sát tuần tự hóa kiểm tra quota và chống gửi trùng khi hai request đồng thời.
    survey = found((await db.execute(select(Survey).where(Survey.id == survey.id, Survey.tenant_id == survey.tenant_id).with_for_update())).scalar_one_or_none())
    existing = (await db.execute(select(Response).where(Response.tenant_id == survey.tenant_id, Response.survey_id == survey.id, Response.external_id == token["jti"]))).scalar_one_or_none()
    if existing:
        return SubmissionResult(response_id=str(existing.id), voucher=existing.source_params.get("_voucher"), voucher_expires_at=existing.source_params.get("_voucher_expires_at"))
    require_open(survey)
    if str(survey.current_version_id) != token["version"]:
        raise AppError("Khảo sát vừa được cập nhật. Vui lòng tải lại trang.", code="VERSION_CHANGED", status_code=409)
    duration = int(time.time()) - token["iat"]
    if duration < 2:
        raise AppError("Vui lòng đọc kỹ khảo sát trước khi gửi.", code="TOO_FAST")
    config = await snapshot(db, survey)
    answers = validate_answers(config["questions"], data.answers)
    if survey.settings.get("one_per_ip") and ip_hash:
        previous = (await db.execute(select(Response.id).where(Response.tenant_id == survey.tenant_id, Response.survey_id == survey.id, Response.ip_hash == ip_hash).limit(1))).scalar_one_or_none()
        if previous:
            raise AppError("Bạn đã gửi phản hồi cho khảo sát này.", code="ALREADY_RESPONDED", status_code=409)
    fingerprint_hash = hash_identifier(data.fingerprint, settings.hash_salt.get_secret_value()) if data.fingerprint else None
    if survey.settings.get("one_per_browser") and fingerprint_hash:
        previous = (await db.execute(select(Response.id).where(Response.tenant_id == survey.tenant_id, Response.survey_id == survey.id, Response.fingerprint_hash == fingerprint_hash).limit(1))).scalar_one_or_none()
        if previous:
            raise AppError("Trình duyệt đã gửi phản hồi.", code="ALREADY_RESPONDED", status_code=409)
    for q in config["questions"]:
        if q["type"] == "upload" and q["code"] in answers:
            value = answers[q["code"]]
            try:
                proof = jwt.decode(value.get("proof", ""), settings.secret_key.get_secret_value(), algorithms=["HS256"], audience="survey-upload")
            except jwt.PyJWTError as exc:
                raise AppError("Tệp không có xác nhận quét hợp lệ.") from exc
            if proof.get("sub") != str(survey.id) or proof.get("jti") != token["jti"] or proof.get("key") != value.get("key"):
                raise AppError("Tệp không thuộc lượt trả lời này.")
    from app.models import Answer as StoredAnswer
    from sqlalchemy import func
    for quota in survey.settings.get("quotas", []):
        if answers.get(quota["question"]) != quota["value"]:
            continue
        count = int((await db.execute(select(func.count()).select_from(StoredAnswer).join(Response, Response.id == StoredAnswer.response_id).where(StoredAnswer.tenant_id == survey.tenant_id, Response.survey_id == survey.id, StoredAnswer.question_code == quota["question"], StoredAnswer.value == quota["value"]))).scalar_one())
        if count >= quota["limit"]:
            raise AppError("Nhóm đối tượng này đã đủ số lượng phản hồi.", code="QUOTA_FULL", status_code=409)
    if data.language not in survey.languages:
        raise AppError("Ngôn ngữ không được hỗ trợ.")
    if len(data.source_params) > 10 or any(len(k) > 64 or len(v) > 200 for k, v in data.source_params.items()):
        raise AppError("Tham số nguồn không hợp lệ.")
    sources = {k: v for k, v in data.source_params.items() if not k.startswith("_")}
    voucher_config = config.get("settings", {}).get("voucher", {})
    voucher = None
    expires = voucher_config.get("expires_at")
    if voucher_config.get("enabled") and (not expires or datetime.fromisoformat(expires) > datetime.now(UTC)):
        voucher = voucher_config.get("code") or f"LYS-{secrets.token_hex(4).upper()}"
        sources.update({"_voucher": voucher, "_voucher_expires_at": expires})
    now = datetime.now(UTC)
    response = Response(tenant_id=survey.tenant_id, workspace_id=survey.workspace_id, survey_id=survey.id, survey_version_id=survey.current_version_id, channel=data.channel, source_params=sources, language=data.language, external_id=token["jti"], ip_hash=ip_hash, fingerprint_hash=hash_identifier(data.fingerprint, settings.hash_salt.get_secret_value()) if data.fingerprint else None, submitted_at=now, started_at=datetime.fromtimestamp(token["iat"], UTC), duration_seconds=duration)
    numeric: dict[str, list[int]] = {"rating": [], "csat": []}
    for q in config["questions"]:
        if q["type"] in numeric and q["code"] in answers:
            numeric[q["type"]].append(answers[q["code"]])
    for key, values in numeric.items():
        if values:
            setattr(response, key, Decimal(sum(values)) / Decimal(len(values)))
    nps = next((answers[q["code"]] for q in config["questions"] if q["type"] == "nps" and q["code"] in answers), None)
    response.nps = nps
    db.add(response)
    await db.flush()
    # Câu hỏi đã bị xóa ở bản nháp vẫn có snapshot; question_id lúc đó để NULL.
    from app.models import Question
    current_ids = set((await db.execute(select(Question.id).where(Question.survey_id == survey.id, Question.tenant_id == survey.tenant_id))).scalars())
    for q in config["questions"]:
        if q["code"] not in answers:
            continue
        value = answers[q["code"]]
        qid = uuid.UUID(q["id"])
        answer = Answer(tenant_id=survey.tenant_id, response_id=response.id, question_id=qid if qid in current_ids else None, question_code=q["code"], question_type=q["type"], value=value, text_value=value if q["type"] == "text" else None)
        db.add(answer)
        await db.flush()
        if answer.text_value:
            db.add(TextAnalysis(tenant_id=survey.tenant_id, response_id=response.id, answer_id=answer.id, workspace_id=survey.workspace_id, survey_id=survey.id, channel=response.channel, rating=response.rating, responded_at=now, text=answer.text_value, status=AnalysisStatus.PENDING))
    survey.response_count += 1
    await db.flush()
    return SubmissionResult(response_id=str(response.id), voucher=voucher, voucher_expires_at=expires if voucher else None)
