"""Quản lý bộ chủ đề theo workspace (FR-12) và nạp danh mục chủ đề cho NLP (FR-13)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, any_, case, func, literal, select, text, update
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.permissions import Permission
from app.core.queue import TaskQueue
from app.domain.topic_templates import INDUSTRY_TEMPLATES
from app.models import TextAnalysis, Topic, TopicSet, Workspace
from app.models.enums import AnalysisStatus
from app.schemas.topics import TopicCreate, TopicOut, TopicSetOut, TopicUpdate
from app.services.audit import audit

REANALYZE_TASK = "worker.tasks.nlp.reanalyze_workspace"
DEFAULT_TOPIC_THRESHOLD = 0.35


class TopicService:
    def __init__(self, db: AsyncSession, principal: Principal) -> None:
        self.db = db
        self.principal = principal

    # ------------------------------------------------------------------ đọc
    async def _workspace(self, workspace_id: uuid.UUID) -> Workspace:
        self.principal.require_workspace(workspace_id)
        workspace = (
            await self.db.execute(
                select(Workspace).where(
                    Workspace.id == workspace_id,
                    Workspace.tenant_id == self.principal.tenant_id,
                    Workspace.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if workspace is None:
            raise NotFoundError("Không tìm thấy không gian khảo sát.")
        return workspace

    async def _topic_set(self, workspace_id: uuid.UUID) -> TopicSet:
        await self._workspace(workspace_id)
        topic_set = (
            await self.db.execute(
                select(TopicSet).where(
                    TopicSet.workspace_id == workspace_id,
                    TopicSet.tenant_id == self.principal.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if topic_set is None:
            topic_set = TopicSet(
                tenant_id=self.principal.tenant_id, workspace_id=workspace_id, name="Chủ đề"
            )
            self.db.add(topic_set)
            await self.db.flush()
        return topic_set

    async def _topic(self, topic_id: uuid.UUID) -> Topic:
        topic = (
            await self.db.execute(
                select(Topic).where(
                    Topic.id == topic_id, Topic.tenant_id == self.principal.tenant_id
                )
            )
        ).scalar_one_or_none()
        if topic is None or not self.principal.can_access_workspace(topic.workspace_id):
            raise NotFoundError("Không tìm thấy chủ đề.")
        return topic

    async def _topics(self, topic_set_id: uuid.UUID) -> list[Topic]:
        rows = await self.db.execute(
            select(Topic)
            .where(Topic.topic_set_id == topic_set_id, Topic.tenant_id == self.principal.tenant_id)
            .order_by(Topic.sort_order, Topic.created_at)
        )
        return list(rows.scalars())

    async def get_set(self, workspace_id: uuid.UUID) -> TopicSetOut:
        topic_set = await self._topic_set(workspace_id)
        topics = await self._topics(topic_set.id)
        usage: dict[uuid.UUID, int] = {
            tid: int(count)
            for tid, count in (
                await self.db.execute(
                    select(func.unnest(TextAnalysis.topic_ids).label("tid"), func.count())
                    .where(
                        TextAnalysis.tenant_id == self.principal.tenant_id,
                        TextAnalysis.workspace_id == workspace_id,
                    )
                    .group_by(text("tid"))
                )
            ).all()
        }
        return TopicSetOut(
            id=topic_set.id,
            workspace_id=workspace_id,
            name=topic_set.name,
            template_code=topic_set.template_code,
            version=topic_set.version,
            topics=[
                TopicOut.model_validate(t).model_copy(
                    update={"usage_count": int(usage.get(t.id, 0))}
                )
                for t in topics
            ],
        )

    # ------------------------------------------------------------------ ghi
    async def _bump(self, topic_set: TopicSet, action: str, data: dict[str, object]) -> None:
        """Mỗi thay đổi tăng version: phân tích dùng version cũ được coi là cần phân tích lại."""
        topic_set.version += 1
        await self.db.flush()
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action=action,
            entity_type="topic_set",
            entity_id=topic_set.id,
            data={**data, "version": topic_set.version},
        )

    async def _ensure_unique_name(
        self, topic_set_id: uuid.UUID, name: str, exclude: uuid.UUID | None = None
    ) -> None:
        stmt = select(Topic.id).where(
            Topic.topic_set_id == topic_set_id, func.lower(Topic.name) == name.lower()
        )
        if exclude:
            stmt = stmt.where(Topic.id != exclude)
        if (await self.db.execute(stmt)).first():
            raise ConflictError(f"Chủ đề “{name}” đã tồn tại.", code="TOPIC_EXISTS")

    async def create(self, workspace_id: uuid.UUID, data: TopicCreate) -> Topic:
        self.principal.require(Permission.TOPIC_MANAGE)
        topic_set = await self._topic_set(workspace_id)
        await self._ensure_unique_name(topic_set.id, data.name)
        max_order = (
            await self.db.execute(
                select(func.coalesce(func.max(Topic.sort_order), -1)).where(
                    Topic.topic_set_id == topic_set.id
                )
            )
        ).scalar_one()
        topic = Topic(
            tenant_id=self.principal.tenant_id,
            workspace_id=workspace_id,
            topic_set_id=topic_set.id,
            name=data.name,
            description=data.description,
            keywords=data.keywords,
            color=data.color,
            sort_order=int(max_order) + 1,
        )
        self.db.add(topic)
        await self.db.flush()
        await self._bump(topic_set, "topic.create", {"name": data.name})
        return topic

    async def update(self, topic_id: uuid.UUID, data: TopicUpdate) -> Topic:
        self.principal.require(Permission.TOPIC_MANAGE)
        topic = await self._topic(topic_id)
        if data.name is not None and data.name != topic.name:
            await self._ensure_unique_name(topic.topic_set_id, data.name, exclude=topic.id)
        for field in ("name", "description", "keywords", "color", "is_active"):
            value = getattr(data, field)
            if value is not None:
                setattr(topic, field, value)
        topic_set = await self.db.get(TopicSet, topic.topic_set_id)
        if topic_set is not None:
            await self._bump(topic_set, "topic.update", {"topic_id": str(topic.id)})
        return topic

    async def delete(self, topic_id: uuid.UUID) -> None:
        self.principal.require(Permission.TOPIC_MANAGE)
        topic = await self._topic(topic_id)
        await self._detach_from_analyses(topic.workspace_id, topic.id, replacement=None)
        topic_set = await self.db.get(TopicSet, topic.topic_set_id)
        await self.db.delete(topic)
        await self.db.flush()
        if topic_set is not None:
            await self._bump(topic_set, "topic.delete", {"name": topic.name})

    async def merge(
        self, workspace_id: uuid.UUID, source_ids: Sequence[uuid.UUID], target_id: uuid.UUID
    ) -> Topic:
        """Gộp nhiều chủ đề vào một: chuyển nhãn trên phản hồi, hợp nhất từ khóa, xóa nguồn."""
        self.principal.require(Permission.TOPIC_MANAGE)
        self.principal.require_workspace(workspace_id)
        if target_id in source_ids:
            raise AppError("Chủ đề đích không được nằm trong danh sách gộp.", code="BAD_MERGE")
        target = await self._topic(target_id)
        if target.workspace_id != workspace_id:
            raise NotFoundError("Không tìm thấy chủ đề.")
        keywords = list(target.keywords)
        for source_id in dict.fromkeys(source_ids):
            source = await self._topic(source_id)
            if source.topic_set_id != target.topic_set_id:
                raise NotFoundError("Không tìm thấy chủ đề.")
            await self._detach_from_analyses(target.workspace_id, source.id, replacement=target.id)
            keywords.extend([source.name, *source.keywords])
            await self.db.delete(source)
        target.keywords = list(
            dict.fromkeys(k for k in keywords if k.lower() != target.name.lower())
        )[:50]
        await self.db.flush()
        topic_set = await self.db.get(TopicSet, target.topic_set_id)
        if topic_set is not None:
            await self._bump(
                topic_set,
                "topic.merge",
                {"target": str(target.id), "sources": [str(s) for s in source_ids]},
            )
        return target

    async def _detach_from_analyses(
        self, workspace_id: uuid.UUID, topic_id: uuid.UUID, replacement: uuid.UUID | None
    ) -> None:
        """Gỡ chủ đề khỏi mọi phản hồi; nếu gộp thì thay bằng chủ đề đích (không trùng lặp)."""
        array_type = ARRAY(UUID(as_uuid=True))
        removed = func.array_remove(TextAnalysis.topic_ids, topic_id, type_=array_type)
        new_ids: ColumnElement[Any] = removed
        if replacement is not None:
            new_ids = case(
                (literal(replacement, UUID(as_uuid=True)) == any_(removed), removed),
                else_=func.array_append(removed, replacement, type_=array_type),
            )
        await self.db.execute(
            update(TextAnalysis)
            .where(
                TextAnalysis.tenant_id == self.principal.tenant_id,
                TextAnalysis.workspace_id == workspace_id,
                literal(topic_id, UUID(as_uuid=True)) == any_(TextAnalysis.topic_ids),
            )
            .values(
                topic_ids=new_ids,
                topic_scores=TextAnalysis.topic_scores.op("-")(str(topic_id)),
            )
            .execution_options(synchronize_session=False)
        )

    async def reorder(self, workspace_id: uuid.UUID, ids: Sequence[uuid.UUID]) -> None:
        self.principal.require(Permission.TOPIC_MANAGE)
        topic_set = await self._topic_set(workspace_id)
        topics = {t.id: t for t in await self._topics(topic_set.id)}
        if set(ids) != set(topics):
            raise AppError("Danh sách sắp xếp phải gồm đủ các chủ đề hiện có.", code="BAD_ORDER")
        for position, topic_id in enumerate(ids):
            topics[topic_id].sort_order = position
        await self.db.flush()

    async def apply_template(self, workspace_id: uuid.UUID, code: str, replace: bool) -> None:
        self.principal.require(Permission.TOPIC_MANAGE)
        template = INDUSTRY_TEMPLATES.get(code)
        if template is None:
            raise NotFoundError("Không tìm thấy bộ chủ đề mẫu.")
        topic_set = await self._topic_set(workspace_id)
        existing = await self._topics(topic_set.id)
        if replace:
            for topic in existing:
                await self._detach_from_analyses(workspace_id, topic.id, replacement=None)
                await self.db.delete(topic)
            await self.db.flush()
            existing = []
        names = {t.name.lower() for t in existing}
        position = max((t.sort_order for t in existing), default=-1) + 1
        for tt in template.topics:
            if tt.name.lower() in names:
                continue
            self.db.add(
                Topic(
                    tenant_id=self.principal.tenant_id,
                    workspace_id=workspace_id,
                    topic_set_id=topic_set.id,
                    name=tt.name,
                    description=tt.description,
                    keywords=list(tt.keywords),
                    color=tt.color,
                    sort_order=position,
                )
            )
            position += 1
        topic_set.template_code = template.code
        await self.db.flush()
        await self._bump(topic_set, "topic.apply_template", {"template": code, "replace": replace})

    async def request_reanalysis(self, workspace_id: uuid.UUID, queue: TaskQueue) -> int:
        """Đánh dấu toàn bộ phân tích của workspace là cần làm lại và xếp job nền."""
        self.principal.require(Permission.TOPIC_MANAGE)
        await self._workspace(workspace_id)
        result = await self.db.execute(
            update(TextAnalysis)
            .where(
                TextAnalysis.tenant_id == self.principal.tenant_id,
                TextAnalysis.workspace_id == workspace_id,
                TextAnalysis.status != AnalysisStatus.PROCESSING,
            )
            .values(status=AnalysisStatus.PENDING)
            .execution_options(synchronize_session=False)
        )
        queue.send(
            REANALYZE_TASK,
            kwargs={"tenant_id": str(self.principal.tenant_id), "workspace_id": str(workspace_id)},
            queue="nlp",
        )
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="topic.reanalyze",
            entity_type="workspace",
            entity_id=workspace_id,
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------- danh mục cho NLP (FR-13)
@dataclass(frozen=True, slots=True)
class TopicSpec:
    id: uuid.UUID
    name: str
    description: str
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopicCatalog:
    """Ảnh chụp bộ chủ đề của MỘT workspace dùng cho phân loại."""

    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    version: int
    threshold: float
    topics: tuple[TopicSpec, ...]


async def load_topic_catalog(
    db: AsyncSession, tenant_id: uuid.UUID, workspace_id: uuid.UUID
) -> TopicCatalog:
    """Chỉ nạp chủ đề đang bật của đúng workspace + tenant (không bao giờ lẫn ngành khác)."""
    workspace = (
        await db.execute(
            select(Workspace).where(Workspace.id == workspace_id, Workspace.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if workspace is None:
        raise NotFoundError("Không tìm thấy không gian khảo sát.")
    topic_set = (
        await db.execute(
            select(TopicSet).where(
                TopicSet.workspace_id == workspace_id, TopicSet.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    topics: list[TopicSpec] = []
    if topic_set is not None:
        rows = await db.execute(
            select(Topic)
            .where(
                Topic.topic_set_id == topic_set.id,
                Topic.tenant_id == tenant_id,
                Topic.workspace_id == workspace_id,
                Topic.is_active.is_(True),
            )
            .order_by(Topic.sort_order)
        )
        topics = [
            TopicSpec(t.id, t.name, t.description or "", tuple(t.keywords)) for t in rows.scalars()
        ]
    threshold = float((workspace.settings or {}).get("topic_threshold", DEFAULT_TOPIC_THRESHOLD))
    return TopicCatalog(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        version=topic_set.version if topic_set else 0,
        threshold=threshold,
        topics=tuple(topics),
    )
