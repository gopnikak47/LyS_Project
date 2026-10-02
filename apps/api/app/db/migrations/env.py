"""Môi trường Alembic (async, asyncpg).

URL lấy theo thứ tự: tham số `sqlalchemy.url` của Config → `DATABASE_URL` trong cấu hình ứng dụng.
"""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.migrate import MANUAL_OBJECTS
from app.models import Base

config = context.config
target_metadata = Base.metadata


def _include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    return name not in MANUAL_OBJECTS


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def _configure(connection: Connection | None = None) -> None:
    context.configure(
        connection=connection,
        url=None if connection is not None else _url(),
        target_metadata=target_metadata,
        compare_type=True,
        include_object=_include_object,
        literal_binds=connection is None,
    )


def run_migrations_offline() -> None:
    _configure()
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
