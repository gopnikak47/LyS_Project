"""Tổng hợp tại PostgreSQL; không tải 100k phản hồi vào tiến trình API."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.models import Response, Survey, TextAnalysis, Workspace
from app.models.enums import ResponseStatus, Sentiment
from app.schemas.feedback import FeedbackFilter
from app.services.workspaces import WorkspaceService


class AnalyticsService:
    def __init__(self, db: AsyncSession, principal: Principal) -> None:
        self.db, self.principal = db, principal

    async def response_scope(self, filters: FeedbackFilter):
        await WorkspaceService(self.db, self.principal).get(filters.workspace_id)
        query = select(Response).join(Survey, Survey.id == Response.survey_id).join(Workspace, Workspace.id == Response.workspace_id).where(Response.tenant_id == self.principal.tenant_id, Response.workspace_id == filters.workspace_id, Survey.deleted_at.is_(None), Workspace.deleted_at.is_(None), Response.status != ResponseStatus.SPAM)
        if filters.survey_id:
            query = query.where(Response.survey_id == filters.survey_id)
        if filters.start:
            query = query.where(Response.created_at >= filters.start)
        if filters.end:
            query = query.where(Response.created_at < filters.end)
        if filters.channel:
            query = query.where(Response.channel == filters.channel)
        return query

    async def analysis_scope(self, filters: FeedbackFilter):
        from app.repositories.feedback import FeedbackRepository
        await WorkspaceService(self.db, self.principal).get(filters.workspace_id)
        return FeedbackRepository(self.db, self.principal.tenant_id).filtered(filters)

    async def overview(self, filters: FeedbackFilter) -> dict[str, Any]:
        responses = (await self.response_scope(filters)).subquery()
        row = (await self.db.execute(select(func.count().label("total"), func.avg(responses.c.csat).label("csat"), func.count().filter(responses.c.status == ResponseStatus.COMPLETED).label("completed")).select_from(responses))).one()
        analyses = (await self.analysis_scope(filters)).subquery()
        counts = {str(label): count for label, count in (await self.db.execute(select(analyses.c.sentiment, func.count()).where(analyses.c.sentiment.is_not(None)).group_by(analyses.c.sentiment))).all()}
        analyzed = sum(counts.values())
        urgent = int((await self.db.execute(select(func.count(func.distinct(analyses.c.response_id))).where(analyses.c.is_urgent.is_(True)))).scalar_one())
        return {"total_responses": row.total, "csat": float(row.csat) if row.csat is not None else None, "completed": row.completed, "completion_rate": row.completed / row.total if row.total else None, "analyzed_texts": analyzed, "sentiments": {label.value: {"count": counts.get(label.value, 0), "percent": counts.get(label.value, 0) / analyzed if analyzed else None} for label in Sentiment}, "urgent_responses": urgent}

    async def trends(self, filters: FeedbackFilter, period: str = "day") -> list[dict[str, Any]]:
        responses = (await self.response_scope(filters)).subquery()
        bucket = func.date_trunc(period, responses.c.created_at)
        rows = (await self.db.execute(select(bucket, func.count(), func.avg(responses.c.csat)).group_by(bucket).order_by(bucket))).all()
        return [{"date": date.isoformat(), "responses": count, "csat": float(csat) if csat is not None else None} for date, count, csat in rows]

    async def topics(self, filters: FeedbackFilter, period: str = "week") -> list[dict[str, Any]]:
        analyses = (await self.analysis_scope(filters)).subquery()
        expanded = select(func.date_trunc(period, analyses.c.responded_at).label("bucket"), func.unnest(analyses.c.topic_ids).label("topic_id")).subquery()
        rows = (await self.db.execute(select(expanded.c.bucket, expanded.c.topic_id, func.count()).group_by(expanded.c.bucket, expanded.c.topic_id).order_by(expanded.c.bucket, expanded.c.topic_id))).all()
        return [{"date": date.isoformat(), "topic_id": str(topic), "count": count} for date, topic, count in rows]

    async def wordcloud(self, filters: FeedbackFilter) -> list[dict[str, Any]]:
        analyses = (await self.analysis_scope(filters)).subquery()
        expanded = select(analyses.c.sentiment, func.unnest(analyses.c.keywords).label("word")).where(analyses.c.sentiment.in_([Sentiment.POSITIVE, Sentiment.NEGATIVE])).subquery()
        rows = (await self.db.execute(select(expanded.c.sentiment, expanded.c.word, func.count()).group_by(expanded.c.sentiment, expanded.c.word).order_by(func.count().desc(), expanded.c.word).limit(100))).all()
        return [{"sentiment": sentiment, "word": word, "count": count} for sentiment, word, count in rows]
