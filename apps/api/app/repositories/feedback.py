from __future__ import annotations

from sqlalchemy import Select, func

from app.models import LabelCorrection, Survey, TextAnalysis, Workspace
from app.repositories.base import TenantRepository
from app.schemas.feedback import FeedbackFilter


class FeedbackRepository(TenantRepository[TextAnalysis]):
    model = TextAnalysis

    def filtered(self, filters: FeedbackFilter) -> Select[TextAnalysis]:
        stmt = (
            self._scoped()
            .join(Survey, Survey.id == TextAnalysis.survey_id)
            .join(Workspace, Workspace.id == TextAnalysis.workspace_id)
            .where(
                TextAnalysis.workspace_id == filters.workspace_id,
                Survey.deleted_at.is_(None),
                Workspace.deleted_at.is_(None),
            )
        )
        if filters.survey_id:
            stmt = stmt.where(TextAnalysis.survey_id == filters.survey_id)
        if filters.sentiment:
            stmt = stmt.where(TextAnalysis.sentiment == filters.sentiment)
        if filters.topic_id:
            stmt = stmt.where(TextAnalysis.topic_ids.contains([filters.topic_id]))
        if filters.urgent is not None:
            stmt = stmt.where(TextAnalysis.is_urgent == filters.urgent)
        if filters.channel:
            stmt = stmt.where(TextAnalysis.channel == filters.channel)
        if filters.search:
            stmt = stmt.where(
                func.f_unaccent(func.lower(TextAnalysis.text)).ilike(
                    func.f_unaccent(func.lower(f"%{filters.search}%"))
                )
            )
        if filters.start:
            stmt = stmt.where(TextAnalysis.responded_at >= filters.start)
        if filters.end:
            stmt = stmt.where(TextAnalysis.responded_at < filters.end)
        return stmt


class CorrectionRepository(TenantRepository[LabelCorrection]):
    model = LabelCorrection
