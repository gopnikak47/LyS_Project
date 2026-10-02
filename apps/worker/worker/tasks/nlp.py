"""Khóa skip-locked, RLS mỗi batch, backoff và quét bù khi broker/model lỗi."""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.resources import Resources
from app.db.tenant import system_session, tenant_session
from app.models import Tenant, TextAnalysis, Workspace
from app.models.enums import AnalysisStatus, Sentiment
from app.services.topics import load_topic_catalog
from lys_nlp.pipeline import Pipeline
from worker.celery_app import celery_app

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def pipeline() -> Pipeline:
    settings = get_settings()
    return Pipeline(settings.nlp_backend, settings.nlp_model_path, settings.nlp_topic_model)


async def process(tenant_id: str, response_id: str | None = None, workspace_id: str | None = None) -> int:
    settings = get_settings()
    resources = Resources.from_settings(settings)
    completed = 0
    failed = False
    try:
        while True:
            count = 0
            async with tenant_session(resources.session_factory, uuid.UUID(tenant_id)) as db:
                query = select(TextAnalysis).where(TextAnalysis.tenant_id == uuid.UUID(tenant_id), TextAnalysis.status.in_([AnalysisStatus.PENDING, AnalysisStatus.FAILED]), TextAnalysis.is_verified.is_(False)).order_by(TextAnalysis.created_at).limit(settings.nlp_batch_size).with_for_update(skip_locked=True)
                if response_id:
                    query = query.where(TextAnalysis.response_id == uuid.UUID(response_id))
                if workspace_id:
                    query = query.where(TextAnalysis.workspace_id == uuid.UUID(workspace_id))
                rows = (await db.execute(query)).scalars().all()
                if not rows:
                    break
                catalogs = {}
                for row in rows:
                    count += 1
                    row.attempts += 1
                    try:
                        if row.workspace_id not in catalogs:
                            catalogs[row.workspace_id] = await load_topic_catalog(db, row.tenant_id, row.workspace_id)
                        catalog = catalogs[row.workspace_id]
                        workspace = (await db.execute(select(Workspace).where(Workspace.id == row.workspace_id, Workspace.tenant_id == row.tenant_id))).scalar_one()
                        result = await asyncio.to_thread(pipeline().analyze, row.text, topics=[{"id": str(t.id), "name": t.name, "description": t.description, "keywords": list(t.keywords)} for t in catalog.topics], threshold=catalog.threshold, dictionary=workspace.settings.get("teencode"), urgent_phrases=workspace.settings.get("urgent_phrases"))
                        row.normalized_text = result.normalized_text
                        row.sentiment = Sentiment(result.sentiment)
                        row.sentiment_score = result.sentiment_score
                        row.sentiment_detail = result.sentiment_detail
                        row.topic_ids = [uuid.UUID(value) for value in result.topic_ids]
                        row.topic_scores = result.topic_scores
                        row.is_urgent = result.is_urgent
                        row.urgent_reasons = result.urgent_reasons
                        row.keywords = result.keywords
                        row.model_version = result.model_version
                        row.topic_set_version = catalog.version
                        row.status = AnalysisStatus.DONE
                        row.analyzed_at = datetime.now(UTC)
                        row.last_error = None
                        completed += 1
                    except Exception as exc:
                        row.status = AnalysisStatus.FAILED
                        row.last_error = type(exc).__name__
                        failed = True
                        logger.exception("nlp_analysis_failed", analysis_id=str(row.id), attempt=row.attempts)
            if failed or count < settings.nlp_batch_size:
                break
        if failed:
            raise RuntimeError("NLP chưa sẵn sàng; giữ văn bản thô để thử lại.")
        return completed
    finally:
        await resources.close()


@celery_app.task(name="worker.tasks.nlp.analyze_response", autoretry_for=(RuntimeError,), retry_backoff=10, retry_backoff_max=3600, retry_jitter=True, max_retries=6)
def analyze_response(tenant_id: str, response_id: str) -> int:
    return asyncio.run(process(tenant_id, response_id=response_id))


@celery_app.task(name="worker.tasks.nlp.reanalyze_workspace", autoretry_for=(RuntimeError,), retry_backoff=10, retry_backoff_max=3600, max_retries=6)
def reanalyze_workspace(tenant_id: str, workspace_id: str) -> int:
    return asyncio.run(process(tenant_id, workspace_id=workspace_id))


async def scan() -> int:
    resources = Resources.from_settings(get_settings())
    queued = 0
    try:
        async with system_session(resources.session_factory) as db:
            tenants = list((await db.execute(select(Tenant.id).where(Tenant.deleted_at.is_(None)))).scalars())
        for tenant_id in tenants:
            async with tenant_session(resources.session_factory, tenant_id) as db:
                pairs = (await db.execute(select(TextAnalysis.workspace_id).where(TextAnalysis.tenant_id == tenant_id, TextAnalysis.is_verified.is_(False), TextAnalysis.status.in_([AnalysisStatus.PENDING, AnalysisStatus.FAILED]), TextAnalysis.updated_at < datetime.now(UTC) - timedelta(minutes=5)).distinct())).scalars().all()
            for workspace_id in pairs:
                resources.queue.send("worker.tasks.nlp.reanalyze_workspace", kwargs={"tenant_id": str(tenant_id), "workspace_id": str(workspace_id)}, queue="nlp")
                queued += 1
        return queued
    finally:
        await resources.close()


@celery_app.task(name="worker.tasks.nlp.scan_pending")
def scan_pending() -> int:
    return asyncio.run(scan())
