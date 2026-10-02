"""Chạy migration Alembic bằng code (dùng trong CLI, container `migrate` và test)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Đối tượng tạo bằng SQL thủ công trong migration (không có trong model): autogenerate bỏ qua.
MANUAL_OBJECTS = frozenset({"ix_text_analyses_text_trgm"})


def alembic_config(database_url: str | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    if database_url:
        # Dấu % phải được thoát vì Config dùng ConfigParser.
        cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return cfg


def upgrade(revision: str = "head", database_url: str | None = None) -> None:
    command.upgrade(alembic_config(database_url), revision)


def downgrade(revision: str, database_url: str | None = None) -> None:
    command.downgrade(alembic_config(database_url), revision)


async def upgrade_async(revision: str = "head", database_url: str | None = None) -> None:
    # env.py tự gọi asyncio.run(): chạy trong thread riêng để không đụng event loop hiện tại.
    await asyncio.to_thread(upgrade, revision, database_url)


async def downgrade_async(revision: str, database_url: str | None = None) -> None:
    await asyncio.to_thread(downgrade, revision, database_url)
