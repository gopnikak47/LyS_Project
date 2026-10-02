from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import NotFoundError
from app.db.tenant import system_session, tenant_session
from app.models import Response, Tenant, TextAnalysis, Workspace
from app.repositories.base import TenantRepository
from app.seed.generator import seed

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("clean_db")]


class WorkspaceRepo(TenantRepository[Workspace]):
    model = Workspace
    not_found_message = "Không tìm thấy không gian khảo sát."


async def test_seed_meets_demo_requirements(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with system_session(session_factory) as s:
        stats = await seed(s)
    assert stats["tenants"] >= 2
    assert stats["workspaces"] >= 3
    assert stats["responses"] >= 1500

    async with system_session(session_factory) as s:
        texts = (await s.execute(select(TextAnalysis.text))).scalars().all()
        responses = (await s.execute(select(func.count()).select_from(Response))).scalar_one()
    assert responses == stats["responses"]
    joined = " ".join(texts).lower()
    # Có teencode và ca khẩn cấp để thử pipeline NLP.
    assert any(token in joined for token in (" ko ", " dc ", " đc ", " k "))
    assert any(token in joined for token in ("đau bụng", "gián", "ngộ độc", "lừa đảo"))


async def test_seed_refuses_to_duplicate(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with system_session(session_factory) as s:
        await seed(s, scale=0.01)

    async def seed_again() -> None:
        async with system_session(session_factory) as s:
            await seed(s, scale=0.01)

    with pytest.raises(RuntimeError, match="--reset"):
        await seed_again()


async def test_repository_is_tenant_scoped_and_hides_soft_deleted(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with system_session(session_factory) as s:
        a, b = Tenant(name="A", slug="ta"), Tenant(name="B", slug="tb")
        s.add_all([a, b])
        await s.flush()
        wa = Workspace(tenant_id=a.id, name="WA")
        wb = Workspace(tenant_id=b.id, name="WB")
        s.add_all([wa, wb])
        await s.flush()

    async with tenant_session(session_factory, a.id) as s:
        repo = WorkspaceRepo(s, a.id)
        assert [w.name for w in await repo.list()] == ["WA"]
        with pytest.raises(NotFoundError, match="không gian"):
            await repo.get_or_404(wb.id)
        # add() luôn ép tenant_id của repository, kể cả khi truyền sai.
        created = repo.add(Workspace(tenant_id=b.id, name="WA2"))
        await s.flush()
        assert created.tenant_id == a.id
        await repo.soft_delete(await repo.get_or_404(wa.id))
        assert [w.name for w in await repo.list()] == ["WA2"]
        assert await repo.count() == 1
