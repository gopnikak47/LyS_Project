"""Nhật ký thao tác nhạy cảm (đăng nhập, phân quyền, xóa dữ liệu, xuất dữ liệu…)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.request_context import get_request_id
from app.models import AuditLog

logger = get_logger("app.audit")


async def audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    action: str,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | str | None = None,
    data: dict[str, Any] | None = None,
    ip_hash: str | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            data=data or {},
            ip_hash=ip_hash,
            request_id=get_request_id(),
        )
    )
    logger.info(
        "audit",
        action=action,
        tenant_id=str(tenant_id),
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
    )
