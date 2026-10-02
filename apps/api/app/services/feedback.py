from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError, ConflictError
from app.core.permissions import Permission
from app.models import LabelCorrection, TextAnalysis, Topic
from app.models.enums import AnalysisStatus, CorrectionField, ReviewStatus, Role, Sentiment
from app.repositories.feedback import CorrectionRepository, FeedbackRepository
from app.schemas.feedback import CorrectionInput, FeedbackFilter
from app.services.audit import audit
from app.services.workspaces import WorkspaceService


def describe(row: TextAnalysis) -> dict[str, Any]:
    return {key: getattr(row, key) for key in ("id", "response_id", "survey_id", "workspace_id", "text", "rating", "sentiment", "sentiment_score", "sentiment_detail", "topic_ids", "topic_scores", "is_urgent", "urgent_reasons", "channel", "responded_at", "status", "model_version", "is_verified", "note", "updated_at")}


def describe_correction(row: LabelCorrection) -> dict[str, Any]:
    return {key: getattr(row, key) for key in ("id", "analysis_id", "user_id", "field", "old_value", "new_value", "reason", "created_at", "reverted_at", "review_status", "reviewed_by")}


class FeedbackService:
    def __init__(self, db: AsyncSession, principal: Principal) -> None:
        self.db, self.principal = db, principal
        self.repo = FeedbackRepository(db, principal.tenant_id)
        self.corrections = CorrectionRepository(db, principal.tenant_id)

    async def get(self, analysis_id: uuid.UUID, lock: bool = False) -> TextAnalysis:
        row = await self.repo.get_or_404(analysis_id)
        await WorkspaceService(self.db, self.principal).get(row.workspace_id)
        if lock:
            row = (await self.db.execute(self.repo._scoped().where(TextAnalysis.id == analysis_id).with_for_update())).scalar_one()
        return row

    async def list(self, filters: FeedbackFilter) -> dict[str, Any]:
        await WorkspaceService(self.db, self.principal).get(filters.workspace_id)
        stmt = self.repo.filtered(filters)
        total = int((await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
        order = {"newest": [TextAnalysis.responded_at.desc()], "oldest": [TextAnalysis.responded_at], "confidence": [TextAnalysis.sentiment_score.asc().nullsfirst()], "urgent": [TextAnalysis.is_urgent.desc(), TextAnalysis.responded_at.desc()]}[filters.sort]
        rows = (await self.db.execute(stmt.order_by(*order, TextAnalysis.id).limit(filters.page_size).offset((filters.page - 1) * filters.page_size))).scalars()
        return {"items": [describe(row) for row in rows], "total": total, "page": filters.page, "page_size": filters.page_size}

    async def correct(self, analysis_id: uuid.UUID, data: CorrectionInput) -> TextAnalysis:
        self.principal.require(Permission.LABEL_EDIT)
        row = await self.get(analysis_id, lock=True)
        if data.expected_updated_at is not None and row.updated_at != data.expected_updated_at:
            raise ConflictError("Phản hồi đã được sửa. Vui lòng tải lại.")
        if data.topic_ids is not None:
            topics = (await self.db.execute(select(Topic.id).where(Topic.tenant_id == self.principal.tenant_id, Topic.workspace_id == row.workspace_id, Topic.id.in_(data.topic_ids), Topic.is_active.is_(True)))).scalars().all()
            if set(topics) != set(data.topic_ids):
                raise AppError("Chủ đề không thuộc không gian hiện tại.")
        changes = [("sentiment", CorrectionField.SENTIMENT), ("topic_ids", CorrectionField.TOPICS), ("is_urgent", CorrectionField.URGENT)]
        for attribute, field in changes:
            value = getattr(data, attribute)
            old = getattr(row, attribute)
            if value is None or old == value:
                continue
            def serialized(v: Any) -> Any:
                return [str(item) for item in v] if isinstance(v, list) else str(v) if isinstance(v, Sentiment) else v
            self.corrections.add(LabelCorrection(analysis_id=row.id, user_id=self.principal.user_id, field=field, old_value=serialized(old), new_value=serialized(value), reason=data.reason or None, model_version=row.model_version, review_status=ReviewStatus.APPROVED if self.principal.role == Role.ADMIN else ReviewStatus.PENDING))
            setattr(row, attribute, list(dict.fromkeys(value)) if isinstance(value, list) else value)
        if data.note is not None:
            row.note = data.note
        row.is_verified = True; row.verified_by = self.principal.user_id; row.verified_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        if row.sentiment is not None:
            row.status = AnalysisStatus.DONE
        await audit(self.db, tenant_id=self.principal.tenant_id, user_id=self.principal.user_id, action="analysis.correct", entity_type="analysis", entity_id=row.id, data={"reason": data.reason})
        await self.db.flush()
        return row

    async def history(self, analysis_id: uuid.UUID) -> list[dict[str, Any]]:
        await self.get(analysis_id)
        return [describe_correction(row) for row in await self.corrections.list(LabelCorrection.analysis_id == analysis_id, order_by=LabelCorrection.created_at.desc())]

    async def undo(self, correction_id: uuid.UUID) -> TextAnalysis:
        self.principal.require(Permission.LABEL_EDIT)
        correction = await self.corrections.get_or_404(correction_id)
        row = await self.get(correction.analysis_id, lock=True)
        latest = await self.corrections.list(LabelCorrection.analysis_id == row.id, LabelCorrection.field == correction.field, LabelCorrection.reverted_at.is_(None), order_by=LabelCorrection.created_at.desc(), limit=1)
        if correction.reverted_at or not latest or latest[0].id != correction.id:
            raise ConflictError("Chỉ có thể hoàn tác chỉnh sửa mới nhất của trường này.")
        attribute = {CorrectionField.SENTIMENT: "sentiment", CorrectionField.TOPICS: "topic_ids", CorrectionField.URGENT: "is_urgent"}[correction.field]
        value = correction.old_value
        if correction.field == CorrectionField.TOPICS:
            value = [uuid.UUID(item) for item in (value or [])]
        elif correction.field == CorrectionField.SENTIMENT:
            value = Sentiment(value) if value else None
        setattr(row, attribute, value)
        correction.reverted_at = datetime.now(UTC); row.updated_at = datetime.now(UTC)
        row.is_verified = False; row.verified_by = None; row.verified_at = None
        await self.db.flush()
        return row

    async def review(self, correction_id: uuid.UUID, approved: bool) -> None:
        self.principal.require(Permission.LABEL_APPROVE)
        correction = await self.corrections.get_or_404(correction_id)
        await self.get(correction.analysis_id, lock=True)
        if correction.reverted_at:
            raise ConflictError("Không duyệt nhãn đã hoàn tác.")
        correction.review_status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
        correction.reviewed_by = self.principal.user_id; correction.reviewed_at = datetime.now(UTC)
        await self.db.flush()

    async def quality(self, workspace_id: uuid.UUID) -> dict[str, Any]:
        await WorkspaceService(self.db, self.principal).get(workspace_id)
        scope = self.repo._scoped().where(TextAnalysis.workspace_id == workspace_id)
        total = int((await self.db.execute(select(func.count()).select_from(scope.subquery()))).scalar_one())
        verified = int((await self.db.execute(select(func.count()).select_from(scope.where(TextAnalysis.is_verified.is_(True)).subquery()))).scalar_one())
        corrected = int((await self.db.execute(select(func.count(func.distinct(LabelCorrection.analysis_id))).join(TextAnalysis, TextAnalysis.id == LabelCorrection.analysis_id).where(LabelCorrection.tenant_id == self.principal.tenant_id, TextAnalysis.workspace_id == workspace_id, LabelCorrection.reverted_at.is_(None)))).scalar_one())
        return {"total": total, "verified": verified, "corrected": corrected, "correction_rate": corrected / total if total else None, "accuracy": None, "accuracy_note": "Đánh giá accuracy/F1 bằng evaluate.py trên tập nhãn giữ lại; tỷ lệ sửa không phải accuracy."}
