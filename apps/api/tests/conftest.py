from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from urllib.parse import urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.migrate import upgrade
from app.db.session import create_engine, create_session_factory
from app.main import create_app

# Bảng không bị xóa giữa các test (dữ liệu tham chiếu do migration tạo).
_KEEP_TABLES = {"alembic_version", "plans"}


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        log_level="WARNING",
        cors_origins="http://localhost:3000",
        postgres_host="127.0.0.1",
        redis_url="redis://127.0.0.1:6399/0",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


# --------------------------------------------------------------------------- CSDL thật
@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """PostgreSQL cho test tích hợp.

    - Có `TEST_DATABASE_URL` (CI dùng service container) → dùng luôn.
    - Không có → khởi động container `postgres:16-alpine` qua testcontainers.
    Tên CSDL bắt buộc chứa "test" để không bao giờ xóa nhầm dữ liệu dev.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        db_name = urlparse(url).path.lstrip("/")
        if "test" not in db_name:
            pytest.exit(f"TEST_DATABASE_URL phải trỏ tới CSDL có chữ 'test' (đang là {db_name!r})")
        upgrade("head", url)
        yield url
        return

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", dbname="lys_test", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        upgrade("head", url)
        yield url


@pytest.fixture(scope="session")
async def db_engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(
        Settings(_env_file=None, app_env="test", database_url=database_url, db_pool_size=5)
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(db_engine)


@pytest.fixture
async def clean_db(db_engine: AsyncEngine) -> None:
    """Làm sạch dữ liệu trước mỗi test cần CSDL (giữ bảng tham chiếu)."""
    async with db_engine.begin() as conn:
        rows = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = [r[0] for r in rows if r[0] not in _KEEP_TABLES]
        if tables:
            await conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
