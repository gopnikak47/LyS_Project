"""Harness test API với PostgreSQL thật, rate limiter & hàng đợi in-memory."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx2 as httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core.queue import RecordingQueue
from app.core.ratelimit import MemoryRateLimiter
from app.main import create_app

PASSWORD = "MatKhau@2026"


@dataclass
class Harness:
    app: FastAPI
    queue: RecordingQueue
    _clients: list[httpx.AsyncClient] = field(default_factory=list)

    def client(self) -> httpx.AsyncClient:
        """Mỗi client có cookie jar riêng = một trình duyệt/người dùng riêng."""
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://testserver"
        )
        self._clients.append(client)
        return client

    async def register(
        self,
        company: str,
        email: str,
        *,
        industry: str | None = "restaurant",
        full_name: str = "Quản Trị Viên",
    ) -> tuple[httpx.AsyncClient, dict[str, Any]]:
        client = self.client()
        res = await client.post(
            "/api/v1/auth/register",
            json={
                "company_name": company,
                "full_name": full_name,
                "email": email,
                "password": PASSWORD,
                "industry": industry,
            },
        )
        assert res.status_code == 201, res.text
        body = res.json()
        client.headers["X-CSRF-Token"] = body["csrf_token"]
        return client, body

    async def login(
        self, email: str, password: str = PASSWORD, client: httpx.AsyncClient | None = None
    ) -> tuple[httpx.AsyncClient, httpx.Response]:
        client = client or self.client()
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        if res.status_code == 200:
            client.headers["X-CSRF-Token"] = res.json()["csrf_token"]
        return client, res

    async def invite_and_accept(
        self,
        admin: httpx.AsyncClient,
        email: str,
        role: str = "ANALYST",
        workspace_ids: list[str] | None = None,
        full_name: str = "Thành Viên Mới",
        password: str = PASSWORD,
    ) -> tuple[httpx.AsyncClient, dict[str, Any]]:
        res = await admin.post(
            "/api/v1/invitations",
            json={"email": email, "role": role, "workspace_ids": workspace_ids or []},
        )
        assert res.status_code == 201, res.text
        token = res.json()["invite_url"].rsplit("/", 1)[-1]
        client = self.client()
        res = await client.post(
            f"/api/v1/public/invitations/{token}/accept",
            json={"full_name": full_name, "password": password},
        )
        assert res.status_code == 200, res.text
        client.headers["X-CSRF-Token"] = res.json()["csrf_token"]
        return client, res.json()

    async def aclose(self) -> None:
        for client in self._clients:
            await client.aclose()


@asynccontextmanager
async def make_harness(database_url: str, **overrides: Any) -> AsyncIterator[Harness]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        secret_key="test-secret-key-0123456789-abcdefghijklmnop",
        database_url=database_url,
        log_level="WARNING",
        public_base_url="http://testserver",
        redis_url="redis://127.0.0.1:6399/0",
        **overrides,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        queue = RecordingQueue()
        app.state.resources.limiter = MemoryRateLimiter()
        app.state.resources.queue = queue
        harness = Harness(app=app, queue=queue)
        try:
            yield harness
        finally:
            await harness.aclose()


@pytest.fixture
async def api(database_url: str, clean_db: None) -> AsyncIterator[Harness]:
    async with make_harness(database_url) as harness:
        yield harness


@pytest.fixture
def harness_factory(database_url: str, clean_db: None) -> Callable[..., Any]:
    def factory(**overrides: Any) -> Any:
        return make_harness(database_url, **overrides)

    return factory
