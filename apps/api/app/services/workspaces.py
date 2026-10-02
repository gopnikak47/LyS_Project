"""Không gian khảo sát (FR-02): CRUD, xóa mềm có xác nhận, bộ chủ đề theo ngành."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError
from app.core.permissions import Permission
from app.domain.topic_templates import INDUSTRY_TEMPLATES
from app.models import Survey, Topic, TopicSet, Workspace, WorkspaceMember
from app.repositories.base import TenantRepository
from app.services.audit import audit


class WorkspaceRepository(TenantRepository[Workspace]):
    model = Workspace
    not_found_message = "Không tìm thấy không gian khảo sát."


async def create_workspace(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    industry: str | None,
    created_by: uuid.UUID | None,
    description: str | None = None,
    color: str | None = None,
) -> Workspace:
    """Tạo workspace kèm bộ chủ đề (rỗng hoặc theo mẫu ngành)."""
    workspace = Workspace(
        tenant_id=tenant_id,
        name=name,
        industry=industry,
        description=description,
        created_by=created_by,
    )
    if color:
        workspace.color = color
    db.add(workspace)
    await db.flush()

    template = INDUSTRY_TEMPLATES.get(industry or "")
    topic_set = TopicSet(
        tenant_id=tenant_id,
        workspace_id=workspace.id,
        name=f"Chủ đề {template.name}" if template else "Chủ đề",
        template_code=template.code if template else None,
    )
    db.add(topic_set)
    await db.flush()
    if template:
        for pos, tt in enumerate(template.topics):
            db.add(
                Topic(
                    tenant_id=tenant_id,
                    workspace_id=workspace.id,
                    topic_set_id=topic_set.id,
                    name=tt.name,
                    description=tt.description,
                    keywords=list(tt.keywords),
                    color=tt.color,
                    sort_order=pos,
                )
            )
        await db.flush()
    return workspace


class WorkspaceService:
    def __init__(self, db: AsyncSession, principal: Principal) -> None:
        self.db = db
        self.principal = principal
        self.repo = WorkspaceRepository(db, principal.tenant_id)

    async def list_accessible(self) -> Sequence[tuple[Workspace, int]]:
        stmt = (
            select(Workspace, func.count(Survey.id))
            .outerjoin(Survey, (Survey.workspace_id == Workspace.id) & Survey.deleted_at.is_(None))
            .where(Workspace.tenant_id == self.principal.tenant_id, Workspace.deleted_at.is_(None))
            .group_by(Workspace.id)
            .order_by(Workspace.created_at)
        )
        if not self.principal.sees_all_workspaces:
            stmt = stmt.where(Workspace.id.in_(self.principal.workspace_ids))
        rows = await self.db.execute(stmt)
        return [(ws, int(count)) for ws, count in rows.all()]

    async def get(self, workspace_id: uuid.UUID) -> Workspace:
        self.principal.require_workspace(workspace_id)
        return await self.repo.get_or_404(workspace_id)

    async def create(
        self,
        *,
        name: str,
        industry: str | None,
        description: str | None,
        color: str | None,
    ) -> Workspace:
        self.principal.require(Permission.WORKSPACE_MANAGE)
        from app.services.billing import enforce_limit
        await enforce_limit(self.db, self.principal.tenant_id, "workspaces")
        workspace = await create_workspace(
            self.db,
            tenant_id=self.principal.tenant_id,
            name=name,
            industry=industry,
            created_by=self.principal.user_id,
            description=description,
            color=color,
        )
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="workspace.create",
            entity_type="workspace",
            entity_id=workspace.id,
            data={"name": name},
        )
        return workspace

    async def update(self, workspace_id: uuid.UUID, **fields: object) -> Workspace:
        self.principal.require(Permission.WORKSPACE_MANAGE)
        workspace = await self.get(workspace_id)
        for key, value in fields.items():
            if value is not None:
                setattr(workspace, key, value)
        await self.db.flush()
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="workspace.update",
            entity_type="workspace",
            entity_id=workspace.id,
            data={k: v for k, v in fields.items() if v is not None and k != "settings"},
        )
        return workspace

    async def delete(self, workspace_id: uuid.UUID, confirm_name: str) -> None:
        """Xóa mềm: phải gõ đúng tên workspace để xác nhận (tránh xóa nhầm)."""
        self.principal.require(Permission.WORKSPACE_MANAGE)
        workspace = await self.get(workspace_id)
        if confirm_name.strip() != workspace.name:
            raise AppError(
                "Tên xác nhận không khớp với tên không gian khảo sát.", code="CONFIRMATION_MISMATCH"
            )
        workspace.deleted_at = datetime.now(UTC)
        await self.db.flush()
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="workspace.delete",
            entity_type="workspace",
            entity_id=workspace.id,
            data={"name": workspace.name},
        )

    async def set_members(self, workspace_id: uuid.UUID, user_ids: Sequence[uuid.UUID]) -> None:
        """Ghi đè danh sách thành viên được phân quyền vào workspace."""
        existing = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.tenant_id == self.principal.tenant_id,
            )
        )
        for member in existing.scalars():
            await self.db.delete(member)
        for user_id in set(user_ids):
            self.db.add(
                WorkspaceMember(
                    tenant_id=self.principal.tenant_id, workspace_id=workspace_id, user_id=user_id
                )
            )
        await self.db.flush()
