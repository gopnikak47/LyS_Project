from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import get_health_service
from app.services.health import HealthService


async def _ok() -> None:
    return None


async def _boom() -> None:
    raise ConnectionRefusedError("db down")


async def _slow() -> None:
    await asyncio.sleep(5)


def test_liveness_returns_ok_with_request_id(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    assert len(res.headers["X-Request-ID"]) >= 8


@pytest.mark.parametrize("path", ["/health/ready", "/api/v1/health"])
def test_readiness_ok(app: FastAPI, client: TestClient, path: str) -> None:
    app.dependency_overrides[get_health_service] = lambda: HealthService(
        {"database": _ok, "redis": _ok}, timeout=1
    )
    res = client.get(path)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert set(body["components"]) == {"database", "redis"}


def test_readiness_degraded_returns_503_without_leaking_details(
    app: FastAPI, client: TestClient
) -> None:
    app.dependency_overrides[get_health_service] = lambda: HealthService(
        {"database": _boom, "redis": _ok}, timeout=1
    )
    res = client.get("/api/v1/health")
    assert res.status_code == 503
    body = res.json()
    assert body["status"] == "degraded"
    assert body["components"]["database"] == {
        "status": "error",
        "latency_ms": body["components"]["database"]["latency_ms"],
        "error": "ConnectionRefusedError",
    }
    assert "db down" not in res.text


async def test_health_check_times_out() -> None:
    service = HealthService({"redis": _slow}, timeout=0.05)
    report = await service.readiness()
    assert report.status == "degraded"
    assert report.components["redis"].error == "TimeoutError"
