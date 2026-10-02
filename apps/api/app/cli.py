"""Lệnh quản trị: `python -m app.cli <lệnh>`.

migrate [--revision head]     Chạy migration
downgrade <revision>          Quay lui migration
seed [--reset] [--scale 1.0]  Sinh dữ liệu minh họa tiếng Việt
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db import migrate
from app.db.session import create_engine, create_session_factory
from app.db.tenant import system_session

logger = get_logger("app.cli")


async def _seed(reset: bool, scale: float) -> None:
    from app.seed.generator import DEMO_PASSWORD, SEED_TENANTS, reset_seed_data, seed

    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with system_session(factory) as session:
            if reset:
                await reset_seed_data(session)
            stats = await seed(session, scale=scale)
    finally:
        await engine.dispose()
    logger.info("seed_done", **stats)
    print("\nĐã sinh dữ liệu minh họa:", ", ".join(f"{k}={v}" for k, v in stats.items()))
    print(f"Tài khoản đăng nhập (mật khẩu chung: {DEMO_PASSWORD}):")
    for tenant in SEED_TENANTS:
        for email, name, role in tenant.users:
            print(f"  - {email:<24} {role.value:<8} {name} · {tenant.name}")


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.log_json)

    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p_mig = sub.add_parser("migrate", help="Chạy migration tới revision (mặc định head)")
    p_mig.add_argument("--revision", default="head")
    p_down = sub.add_parser("downgrade", help="Quay lui migration")
    p_down.add_argument("revision")
    p_seed = sub.add_parser("seed", help="Sinh dữ liệu minh họa tiếng Việt")
    p_seed.add_argument("--reset", action="store_true", help="Xóa dữ liệu minh họa cũ trước")
    p_seed.add_argument("--scale", type=float, default=1.0, help="Hệ số số lượng phản hồi")

    args = parser.parse_args(argv)
    if args.command == "migrate":
        migrate.upgrade(args.revision)
        logger.info("migrate_done", revision=args.revision)
    elif args.command == "downgrade":
        migrate.downgrade(args.revision)
        logger.info("downgrade_done", revision=args.revision)
    elif args.command == "seed":
        asyncio.run(_seed(args.reset, args.scale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
