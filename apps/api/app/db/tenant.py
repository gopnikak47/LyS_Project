"""Phiên làm việc có ngữ cảnh tenant — lớp phòng thủ RLS ở PostgreSQL (FR-04).

Mỗi request đã xác thực chạy trong một transaction với:
  - `SET LOCAL ROLE lys_rls`  → vai trò không phải chủ sở hữu bảng nên bị RLS ràng buộc;
  - `app.tenant_id`, `app.user_id` → chính sách RLS chỉ cho thấy/ghi dữ liệu của tenant hiện tại.
`LOCAL` nghĩa là chỉ có hiệu lực trong transaction; kết nối trả về pool đã sạch ngữ cảnh.

Phiên hệ thống (`system_session`) không đổi vai trò → bỏ qua RLS. Chỉ dùng cho các thao tác
bắt buộc xuyên tenant: đăng ký/đăng nhập, phân giải slug công khai, job nền trước khi biết tenant.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

RLS_ROLE = "lys_rls"


async def apply_tenant_context(
    session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    await session.execute(text(f"SET LOCAL ROLE {RLS_ROLE}"))
    await session.execute(
        text(
            "SELECT set_config('app.tenant_id', :tenant, true),"
            " set_config('app.user_id', :user, true)"
        ),
        {"tenant": str(tenant_id), "user": str(user_id) if user_id else ""},
    )


@asynccontextmanager
async def tenant_session(
    factory: async_sessionmaker[AsyncSession],
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> AsyncIterator[AsyncSession]:
    async with factory() as session, session.begin():
        await apply_tenant_context(session, tenant_id, user_id)
        yield session


@asynccontextmanager
async def system_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session, session.begin():
        yield session
