from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.errors import ForbiddenError, NotFoundError
from app.main import create_app


class _Payload(BaseModel):
    name: str = Field(min_length=2)
    rating: int = Field(ge=1, le=5)


def _build_app(settings: Settings) -> FastAPI:
    app = create_app(settings)
    router = APIRouter(prefix="/test")

    @router.post("/validate")
    async def validate(payload: _Payload) -> _Payload:
        return payload

    @router.get("/not-found")
    async def not_found() -> None:
        raise NotFoundError("Không tìm thấy khảo sát.")

    @router.get("/forbidden")
    async def forbidden() -> None:
        raise ForbiddenError()

    @router.get("/crash")
    async def crash() -> None:
        raise RuntimeError("secret internal detail")

    app.include_router(router)
    return app


@pytest.fixture
def err_client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(_build_app(settings)) as client:
        yield client


def test_unknown_route_returns_standard_error(err_client: TestClient) -> None:
    res = err_client.get("/khong-ton-tai")
    assert res.status_code == 404
    error = res.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["message"] == "Không tìm thấy tài nguyên."
    assert error["request_id"] == res.headers["X-Request-ID"]


def test_app_error_uses_custom_message(err_client: TestClient) -> None:
    res = err_client.get("/test/not-found")
    assert res.status_code == 404
    assert res.json()["error"]["message"] == "Không tìm thấy khảo sát."


def test_app_error_default_message(err_client: TestClient) -> None:
    res = err_client.get("/test/forbidden")
    assert res.status_code == 403
    assert res.json()["error"] == {
        "code": "FORBIDDEN",
        "message": "Bạn không có quyền thực hiện thao tác này.",
        "request_id": res.headers["X-Request-ID"],
    }


def test_validation_error_lists_fields(err_client: TestClient) -> None:
    res = err_client.post("/test/validate", json={"name": "a", "rating": 9})
    assert res.status_code == 422
    error = res.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {d["field"] for d in error["details"]} == {"name", "rating"}


def test_unhandled_error_hides_internals(err_client: TestClient) -> None:
    res = err_client.get("/test/crash")
    assert res.status_code == 500
    assert res.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "secret internal detail" not in res.text
    assert "Traceback" not in res.text
    assert res.headers["X-Request-ID"] == res.json()["error"]["request_id"]


def test_valid_request_id_is_propagated(err_client: TestClient) -> None:
    res = err_client.get("/health", headers={"X-Request-ID": "req-abc-12345"})
    assert res.headers["X-Request-ID"] == "req-abc-12345"


@pytest.mark.parametrize("bad", ["short", "x" * 100, "abc def ghi jkl", "abc<script>xyz"])
def test_unsafe_request_id_is_replaced(err_client: TestClient, bad: str) -> None:
    res = err_client.get("/health", headers={"X-Request-ID": bad})
    assert res.headers["X-Request-ID"] != bad
