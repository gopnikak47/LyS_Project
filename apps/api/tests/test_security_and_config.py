from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings


def test_security_headers_on_api_responses(client: TestClient) -> None:
    res = client.get("/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert "Strict-Transport-Security" not in res.headers


def test_docs_are_served_without_strict_csp_outside_production(client: TestClient) -> None:
    res = client.get("/api/docs")
    assert res.status_code == 200
    assert "Content-Security-Policy" not in res.headers


def test_cors_allows_only_configured_origins(client: TestClient) -> None:
    allowed = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    denied = client.options(
        "/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_cors_origins_accepts_comma_separated_string() -> None:
    s = Settings(_env_file=None, cors_origins="http://a.vn, http://b.vn,")
    assert s.cors_origins == ["http://a.vn", "http://b.vn"]


def test_database_url_built_from_parts() -> None:
    s = Settings(
        _env_file=None,
        postgres_user="u",
        postgres_password="p",
        postgres_host="db",
        postgres_port=5433,
        postgres_db="x",
    )
    assert s.database_url == "postgresql+asyncpg://u:p@db:5433/x"


def test_production_rejects_default_secrets() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, app_env="production")


def test_production_accepts_strong_secrets() -> None:
    s = Settings(
        _env_file=None,
        app_env="production",
        secret_key="k" * 40,
        hash_salt="s" * 40,
    )
    assert s.is_production


def test_bcrypt_cost_must_be_at_least_12() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, bcrypt_rounds=10)
