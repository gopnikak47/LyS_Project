"""Gửi job sang Celery worker theo tên task (API không import code worker).

Trong test, thay `TaskQueue` bằng `RecordingQueue` để kiểm tra job đã được đẩy đúng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from celery import Celery

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskQueue(Protocol):
    def send(self, task_name: str, *, kwargs: dict[str, Any], queue: str = "default") -> None: ...


class CeleryQueue:
    def __init__(self, settings: Settings) -> None:
        self._celery = Celery("lys-api", broker=settings.celery_broker_url)
        self._celery.conf.update(task_serializer="json", accept_content=["json"])

    def send(self, task_name: str, *, kwargs: dict[str, Any], queue: str = "default") -> None:
        self._celery.send_task(task_name, kwargs=kwargs, queue=queue)
        logger.info("task_enqueued", task=task_name, queue=queue)


@dataclass
class RecordingQueue:
    sent: list[tuple[str, dict[str, Any], str]] = field(default_factory=list)

    def send(self, task_name: str, *, kwargs: dict[str, Any], queue: str = "default") -> None:
        self.sent.append((task_name, kwargs, queue))

    def of(self, task_name: str) -> list[dict[str, Any]]:
        return [kw for name, kw, _ in self.sent if name == task_name]
