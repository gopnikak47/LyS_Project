from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from itertools import islice

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.resources import Resources
from app.core.storage import LocalStorage
from app.db.tenant import system_session, tenant_session
from app.domain.question_types import validate_answers
from app.domain.tabular import csv_bytes, rows
from app.models import Answer, ImportJob, Question, Response, Survey, Tenant, TextAnalysis
from app.models.enums import AnalysisStatus, Channel, JobStatus
from worker.celery_app import celery_app


async def run_import(tenant_id: str, job_id: str) -> int:
    tid, jid = uuid.UUID(tenant_id), uuid.UUID(job_id)
    settings = get_settings(); resources = Resources.from_settings(settings)
    storage = LocalStorage(settings.storage_local_root)
    try:
        while True:
            async with tenant_session(resources.session_factory, tid) as db:
                job = (await db.execute(select(ImportJob).where(ImportJob.id == jid, ImportJob.tenant_id == tid).with_for_update(skip_locked=True))).scalar_one_or_none()
                if job is None or job.status == JobStatus.DONE or not job.mapping:
                    return 0
                job.status = JobStatus.RUNNING
                job.started_at = job.started_at or datetime.now(UTC)
                start = job.processed_rows
                try:
                    batch = await asyncio.to_thread(lambda: list(islice(rows(storage.path(job.file_key)), start, start + 200)))
                    if not batch:
                        job.total_rows = job.processed_rows; job.status = JobStatus.DONE; job.finished_at = datetime.now(UTC)
                        error_key = f"{tid}/imports/{jid}/errors.csv"
                        chunks = sorted(storage.path(f"{tid}/imports/{jid}").glob("errors-*.csv"))
                        # Ghi đè từng báo cáo lô theo offset để retry không nhân đôi lỗi.
                        content = csv_bytes(["Dòng", "Lỗi"], [])
                        for path in chunks:
                            lines = path.read_bytes().splitlines(keepends=True)
                            content += b"".join(lines[1:])
                        storage.put(error_key, content); job.error_report_key = error_key
                        return job.success_rows
                    survey = (await db.execute(select(Survey).where(Survey.id == job.survey_id, Survey.tenant_id == tid, Survey.deleted_at.is_(None)).with_for_update())).scalar_one()
                    qids = set((await db.execute(select(Question.id).where(Question.survey_id == survey.id, Question.tenant_id == tid))).scalars())
                    errors = []
                    for offset, row in enumerate(batch):
                        number = start + offset + 2
                        try:
                            raw = {}
                            for q in job.mapping["questions"]:
                                column = job.mapping["columns"].get(q["code"])
                                value = row.get(column, "") if column else ""
                                if value:
                                    if q["type"] in {"rating", "csat"}:
                                        value = int(value)
                                    elif q["type"] == "multi_choice":
                                        value = [part.strip() for part in value.split("|")]
                                    raw[q["code"]] = value
                            validated = validate_answers(job.mapping["questions"], raw)
                        except (ValueError, AppError) as exc:
                            errors.append([number, str(exc)]); job.error_rows += 1
                            continue
                        from app.services.billing import nlp_capacity
                        allow_nlp = await nlp_capacity(db, tid)
                        response = Response(tenant_id=tid, workspace_id=survey.workspace_id, survey_id=survey.id, survey_version_id=uuid.UUID(job.mapping["version_id"]) if job.mapping.get("version_id") else None, channel=Channel.IMPORT, external_id=f"{jid}:{number}", submitted_at=datetime.now(UTC))
                        for field in ("rating", "csat"):
                            values = [validated[q["code"]] for q in job.mapping["questions"] if q["type"] == field and q["code"] in validated]
                            if values:
                                setattr(response, field, Decimal(sum(values)) / len(values))
                        db.add(response); await db.flush()
                        for q in job.mapping["questions"]:
                            if q["code"] not in validated:
                                continue
                            value = validated[q["code"]]; qid = uuid.UUID(q["id"])
                            answer = Answer(tenant_id=tid, response_id=response.id, question_id=qid if qid in qids else None, question_code=q["code"], question_type=q["type"], value=value, text_value=value if q["type"] == "text" else None)
                            db.add(answer); await db.flush()
                            if answer.text_value:
                                db.add(TextAnalysis(tenant_id=tid, response_id=response.id, answer_id=answer.id, workspace_id=survey.workspace_id, survey_id=survey.id, channel=Channel.IMPORT, rating=response.rating, text=answer.text_value, status=AnalysisStatus.PENDING if allow_nlp else AnalysisStatus.SKIPPED, last_error=None if allow_nlp else "PLAN_LIMIT"))
                        job.success_rows += 1; survey.response_count += 1
                    storage.put(f"{tid}/imports/{jid}/errors-{start:08d}.csv", csv_bytes(["Dòng", "Lỗi"], errors))
                    job.processed_rows += len(batch)
                except Exception as exc:
                    job.status = JobStatus.FAILED; job.error_message = type(exc).__name__
                    await db.flush()
                    return job.success_rows
    finally:
        await resources.close()


@celery_app.task(name="worker.tasks.imports.run", autoretry_for=(OSError,), retry_backoff=True, max_retries=6)
def import_file(tenant_id: str, job_id: str) -> int:
    return asyncio.run(run_import(tenant_id, job_id))


async def scan() -> int:
    resources = Resources.from_settings(get_settings()); count = 0
    try:
        async with system_session(resources.session_factory) as db:
            tenants = list((await db.execute(select(Tenant.id).where(Tenant.deleted_at.is_(None)))).scalars())
        for tid in tenants:
            async with tenant_session(resources.session_factory, tid) as db:
                jobs = (await db.execute(select(ImportJob.id).where(ImportJob.tenant_id == tid, ImportJob.status.in_([JobStatus.PENDING, JobStatus.RUNNING]), ImportJob.mapping != {}))).scalars().all()
            for jid in jobs:
                resources.queue.send("worker.tasks.imports.run", kwargs={"tenant_id": str(tid), "job_id": str(jid)})
                count += 1
        return count
    finally:
        await resources.close()


@celery_app.task(name="worker.tasks.imports.scan")
def scan_imports() -> int:
    return asyncio.run(scan())
