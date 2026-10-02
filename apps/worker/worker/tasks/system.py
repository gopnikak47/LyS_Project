"""Task hệ thống: kiểm tra worker còn sống, nhịp tim định kỳ."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.logging import get_logger
from worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="worker.tasks.system.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="worker.tasks.system.heartbeat", ignore_result=True)
def heartbeat() -> str:
    now = datetime.now(UTC).isoformat()
    logger.info("worker_heartbeat", at=now)
    return now
