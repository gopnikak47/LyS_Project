"""Khởi tạo Celery.

Chạy worker: `celery -A worker.celery_app worker -Q default,nlp -l INFO`
Chạy beat:   `celery -A worker.celery_app beat -l INFO`
"""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.signals import setup_logging

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()

celery_app = Celery(
    "lys",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks.system"],
)

celery_app.conf.update(
    # --- Độ bền hàng đợi: chỉ xác nhận khi task chạy xong; worker chết -> task quay lại hàng đợi.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # --- Tuần tự hóa an toàn
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # --- Thời gian
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    result_expires=60 * 60 * 24,
    # --- Định tuyến: NLP tách hàng đợi riêng để mở rộng ngang độc lập.
    task_default_queue="default",
    task_routes={"worker.tasks.nlp.*": {"queue": "nlp"}},
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 60 * 60},
    worker_hijack_root_logger=False,
    worker_send_task_events=True,
    task_send_sent_event=True,
    # --- Lịch chạy định kỳ (beat). Các job bù NLP / sao lưu bổ sung ở giai đoạn sau.
    beat_schedule={
        "system-heartbeat": {
            "task": "worker.tasks.system.heartbeat",
            "schedule": 60.0,
        },
    },
)


@setup_logging.connect
def _configure_celery_logging(**_: Any) -> None:
    # Dùng chung định dạng log JSON với API.
    configure_logging(settings.log_level, json=settings.log_json)
