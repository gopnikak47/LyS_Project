"""Migration chạy sạch: lên → xuống → lên lại trên CSDL trống, và khớp với model."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from urllib.parse import urlparse, urlunparse

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.migrate import MANUAL_OBJECTS, downgrade_async, upgrade_async
from app.models import Base

pytestmark = pytest.mark.db


@pytest.fixture
async def fresh_database_url(database_url: str) -> AsyncIterator[str]:
    name = f"lys_test_mig_{uuid.uuid4().hex[:8]}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    parsed = urlparse(database_url)
    yield urlunparse(parsed._replace(path=f"/{name}"))
    async with admin.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    await admin.dispose()


async def test_upgrade_downgrade_upgrade(fresh_database_url: str) -> None:
    await upgrade_async("head", fresh_database_url)
    await downgrade_async("base", fresh_database_url)
    await upgrade_async("head", fresh_database_url)

    engine = create_async_engine(fresh_database_url)
    async with engine.connect() as conn:
        plans = (await conn.execute(text("SELECT code FROM plans ORDER BY sort_order"))).all()
    await engine.dispose()
    assert [p[0] for p in plans] == ["free", "pro", "business"]


async def test_models_match_migrations(database_url: str) -> None:
    def _diff(conn: Connection) -> list[object]:
        ctx = MigrationContext.configure(
            conn,
            opts={
                "compare_type": True,
                "include_object": lambda _o, name, *_: name not in MANUAL_OBJECTS,
            },
        )
        return list(compare_metadata(ctx, Base.metadata))

    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        diff = await conn.run_sync(_diff)
    await engine.dispose()
    assert diff == [], f"Model và migration lệch nhau, cần tạo migration mới: {diff}"
