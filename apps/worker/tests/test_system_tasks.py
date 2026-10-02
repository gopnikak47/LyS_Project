from __future__ import annotations

from collections.abc import Iterator

import pytest

from worker.celery_app import celery_app
from worker.tasks.system import heartbeat, ping


@pytest.fixture(autouse=True)
def eager_mode() -> Iterator[None]:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_store_eager_result = False
    yield
    celery_app.conf.task_always_eager = False


def test_ping_task_returns_pong() -> None:
    assert ping.delay().get(timeout=1) == "pong"


def test_heartbeat_returns_iso_timestamp() -> None:
    value = heartbeat.apply().get(timeout=1)
    assert "T" in value


def test_queue_durability_settings() -> None:
    conf = celery_app.conf
    assert conf.task_acks_late is True
    assert conf.task_reject_on_worker_lost is True
    assert conf.worker_prefetch_multiplier == 1
    assert conf.accept_content == ["json"]


def test_beat_schedule_registered_tasks_exist() -> None:
    celery_app.loader.import_default_modules()
    for entry in celery_app.conf.beat_schedule.values():
        assert entry["task"] in celery_app.tasks
