"""Chứng minh lớp RLS ở PostgreSQL cô lập dữ liệu giữa các tenant (FR-04, lớp 3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.tenant import system_session, tenant_session
from app.models import (
    TENANT_SCOPED_TABLES,
    Membership,
    Survey,
    Tenant,
    TextAnalysis,
    User,
    Workspace,
)
from app.models.enums import Role

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("clean_db")]


@dataclass
class TenantData:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    survey_id: uuid.UUID


async def _make_tenant(factory: async_sessionmaker[AsyncSession], slug: str) -> TenantData:
    async with system_session(factory) as s:
        tenant = Tenant(name=f"DN {slug}", slug=slug)
        s.add(tenant)
        await s.flush()
        user = User(email=f"admin@{slug}.vn", full_name="Admin", password_hash="x")
        s.add(user)
        await s.flush()
        s.add(Membership(tenant_id=tenant.id, user_id=user.id, role=Role.ADMIN))
        ws = Workspace(tenant_id=tenant.id, name=f"WS {slug}")
        s.add(ws)
        await s.flush()
        survey = Survey(tenant_id=tenant.id, workspace_id=ws.id, title="KS", slug=f"ks-{slug}")
        s.add(survey)
        await s.flush()
        return TenantData(tenant.id, user.id, ws.id, survey.id)


@pytest.fixture
async def two_tenants(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[TenantData, TenantData]:
    return await _make_tenant(session_factory, "a"), await _make_tenant(session_factory, "b")


async def test_tenant_sees_only_own_rows(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, _b = two_tenants
    async with tenant_session(session_factory, a.tenant_id, a.user_id) as s:
        # Truy vấn KHÔNG có điều kiện tenant vẫn chỉ trả dữ liệu của A.
        workspaces = (await s.execute(select(Workspace))).scalars().all()
        surveys = (await s.execute(select(Survey))).scalars().all()
        tenants = (await s.execute(select(Tenant))).scalars().all()
    assert [w.id for w in workspaces] == [a.workspace_id]
    assert [x.id for x in surveys] == [a.survey_id]
    assert [t.id for t in tenants] == [a.tenant_id]


async def test_guessing_other_tenant_id_returns_nothing(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, b = two_tenants
    async with tenant_session(session_factory, a.tenant_id) as s:
        found = await s.get(Survey, b.survey_id)
    assert found is None


async def test_cannot_insert_rows_for_other_tenant(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, b = two_tenants

    async def insert_for_b() -> None:
        async with tenant_session(session_factory, a.tenant_id) as s:
            s.add(Workspace(tenant_id=b.tenant_id, name="chen ngang"))
            await s.flush()

    with pytest.raises((ProgrammingError, DBAPIError), match="row-level security"):
        await insert_for_b()


async def test_cannot_update_or_delete_other_tenant_rows(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, b = two_tenants
    async with tenant_session(session_factory, a.tenant_id) as s:
        res = await s.execute(update(Survey).where(Survey.id == b.survey_id).values(title="bi sua"))
        assert res.rowcount == 0  # type: ignore[attr-defined]
        res = await s.execute(text("DELETE FROM surveys WHERE id = :id"), {"id": b.survey_id})
        assert res.rowcount == 0  # type: ignore[attr-defined]
    async with system_session(session_factory) as s:
        survey = await s.get(Survey, b.survey_id)
    assert survey is not None
    assert survey.title == "KS"


async def test_cannot_move_row_to_other_tenant(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, b = two_tenants

    async def move_to_b() -> None:
        async with tenant_session(session_factory, a.tenant_id) as s:
            await s.execute(
                update(Workspace)
                .where(Workspace.id == a.workspace_id)
                .values(tenant_id=b.tenant_id)
            )

    with pytest.raises((ProgrammingError, DBAPIError), match="row-level security"):
        await move_to_b()


async def test_missing_tenant_context_sees_nothing(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    async with session_factory() as s, s.begin():
        await s.execute(text("SET LOCAL ROLE lys_rls"))
        count = (await s.execute(select(func.count()).select_from(Survey))).scalar_one()
    assert count == 0


async def test_users_visible_only_within_tenant(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, _b = two_tenants
    async with tenant_session(session_factory, a.tenant_id, a.user_id) as s:
        emails = (await s.execute(select(User.email))).scalars().all()
    assert emails == ["admin@a.vn"]


async def test_rls_role_cannot_read_auth_tables(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, _ = two_tenants

    async def read_tokens() -> None:
        async with tenant_session(session_factory, a.tenant_id) as s:
            await s.execute(text("SELECT * FROM refresh_tokens"))

    with pytest.raises((ProgrammingError, DBAPIError), match="permission denied"):
        await read_tokens()


async def test_tenant_context_does_not_leak_between_transactions(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, _ = two_tenants
    async with tenant_session(session_factory, a.tenant_id):
        pass
    # Kết nối trả về pool phải sạch: không còn vai trò RLS hay tenant cũ.
    async with session_factory() as s:
        role = (await s.execute(text("SELECT current_user"))).scalar_one()
        tenant = (
            await s.execute(text("SELECT current_setting('app.tenant_id', true)"))
        ).scalar_one()
    assert role != "lys_rls"
    assert tenant in (None, "")


async def test_rls_enabled_on_every_tenant_table(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Bảng có tenant_id mà quên bật RLS sẽ làm test này đỏ (kể cả bảng thêm ở migration sau)."""
    async with system_session(session_factory) as s:
        rows = await s.execute(
            text(
                "SELECT c.relname, c.relrowsecurity, "
                "EXISTS (SELECT 1 FROM pg_policies p WHERE p.tablename = c.relname) "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind = 'r'"
            )
        )
        info = {name: (rls, has_policy) for name, rls, has_policy in rows}
        cols = await s.execute(
            text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND column_name = 'tenant_id'"
            )
        )
        with_tenant_column = {r[0] for r in cols} - {"refresh_tokens"}
    assert set(TENANT_SCOPED_TABLES) <= with_tenant_column
    missing = [
        t for t in sorted(with_tenant_column | {"tenants", "users"}) if info[t] != (True, True)
    ]
    assert missing == []


async def test_unaccent_search_matches_without_diacritics(
    session_factory: async_sessionmaker[AsyncSession], two_tenants: tuple[TenantData, TenantData]
) -> None:
    a, _ = two_tenants
    async with system_session(session_factory) as s:
        s.add(
            TextAnalysis(
                tenant_id=a.tenant_id,
                response_id=await _make_response(s, a),
                workspace_id=a.workspace_id,
                survey_id=a.survey_id,
                text="Ăn xong bị ĐAU BỤNG cả đêm",
            )
        )
    async with tenant_session(session_factory, a.tenant_id) as s:
        hits = (
            (
                await s.execute(
                    select(TextAnalysis.text).where(
                        func.f_unaccent(func.lower(TextAnalysis.text)).like("%dau bung%")
                    )
                )
            )
            .scalars()
            .all()
        )
    assert hits == ["Ăn xong bị ĐAU BỤNG cả đêm"]


async def _make_response(s: AsyncSession, data: TenantData) -> uuid.UUID:
    from app.models import Response

    response = Response(
        tenant_id=data.tenant_id, survey_id=data.survey_id, workspace_id=data.workspace_id
    )
    s.add(response)
    await s.flush()
    return response.id
