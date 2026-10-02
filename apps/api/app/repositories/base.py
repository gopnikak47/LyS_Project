"""Repository nền có tenant scope bắt buộc.

Lớp phòng thủ thứ 2 (sau dependency gắn tenant từ token, trước RLS PostgreSQL):
mọi truy vấn đi qua `_scoped()` luôn có điều kiện `tenant_id = :tenant` và bỏ bản ghi đã xóa mềm.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar, Generic, TypeVar, cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantRepository(Generic[ModelT]):
    model: ClassVar[type[Any]]
    not_found_message: ClassVar[str] = "Không tìm thấy dữ liệu."

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    @property
    def _soft_delete(self) -> bool:
        return hasattr(self.model, "deleted_at")

    def _scoped(self, *, include_deleted: bool = False) -> Select[Any]:
        stmt: Select[Any] = select(self.model).where(self.model.tenant_id == self.tenant_id)
        if self._soft_delete and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    async def get(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> ModelT | None:
        stmt = self._scoped(include_deleted=include_deleted).where(self.model.id == entity_id)
        return cast(ModelT | None, (await self.session.execute(stmt)).scalar_one_or_none())

    async def get_or_404(self, entity_id: uuid.UUID) -> ModelT:
        entity = await self.get(entity_id)
        if entity is None:
            raise NotFoundError(self.not_found_message)
        return entity

    async def list(
        self,
        *filters: Any,
        order_by: Any = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[ModelT]:
        stmt = self._scoped().where(*filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return cast(Sequence[ModelT], (await self.session.execute(stmt)).scalars().all())

    async def count(self, *filters: Any) -> int:
        stmt = select(func.count()).select_from(self._scoped().where(*filters).subquery())
        return int((await self.session.execute(stmt)).scalar_one())

    def add(self, entity: ModelT) -> ModelT:
        # Không tin tenant_id do tầng trên truyền vào: luôn ghi đè bằng tenant của repository.
        entity.tenant_id = self.tenant_id  # type: ignore[attr-defined]
        self.session.add(entity)
        return entity

    async def soft_delete(self, entity: ModelT) -> None:
        entity.deleted_at = func.now()  # type: ignore[attr-defined]
        await self.session.flush()
