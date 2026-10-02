"""Hạn mức serialize bằng khóa tenant; không loại bỏ phản hồi khách đã gửi."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Invitation, Membership, Plan, Survey, Tenant, TextAnalysis, Workspace
from app.models.enums import AnalysisStatus, MembershipStatus


async def plan_for(db: AsyncSession, tenant_id: uuid.UUID, lock: bool = False) -> Plan:
    query = select(Tenant).where(Tenant.id == tenant_id)
    if lock:
        query = query.with_for_update()
    tenant = (await db.execute(query)).scalar_one()
    return (
        await db.execute(
            select(Plan).where(Plan.code == tenant.plan_code, Plan.is_active.is_(True))
        )
    ).scalar_one()


async def usage(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, int]:
    month = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    workspaces = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Workspace)
                .where(Workspace.tenant_id == tenant_id, Workspace.deleted_at.is_(None))
            )
        ).scalar_one()
    )
    members = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Membership)
                .where(
                    Membership.tenant_id == tenant_id, Membership.status == MembershipStatus.ACTIVE
                )
            )
        ).scalar_one()
    )
    pending_invites = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Invitation)
                .where(
                    Invitation.tenant_id == tenant_id,
                    Invitation.accepted_at.is_(None),
                    Invitation.revoked_at.is_(None),
                    Invitation.expires_at > datetime.now(UTC),
                )
            )
        ).scalar_one()
    )
    nlp = int(
        (
            await db.execute(
                select(func.count(func.distinct(TextAnalysis.response_id))).where(
                    TextAnalysis.tenant_id == tenant_id,
                    TextAnalysis.created_at >= month,
                    TextAnalysis.status != AnalysisStatus.SKIPPED,
                )
            )
        ).scalar_one()
    )
    surveys = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Survey)
                .where(Survey.tenant_id == tenant_id, Survey.deleted_at.is_(None))
            )
        ).scalar_one()
    )
    return {
        "workspaces": workspaces,
        "members": members,
        "surveys": surveys,
        "pending_invitations": pending_invites,
        "nlp_responses_per_month": nlp,
    }


async def enforce_limit(
    db: AsyncSession, tenant_id: uuid.UUID, resource: str, *, reserve_invites: bool = False
) -> None:
    plan = await plan_for(db, tenant_id, lock=True)
    current = await usage(db, tenant_id)
    count = current[resource] + (
        current["pending_invitations"] if reserve_invites and resource == "members" else 0
    )
    maximum = plan.limits.get(resource)
    if maximum is not None and count >= maximum:
        raise AppError(
            "Gói dịch vụ đã đạt hạn mức. Vui lòng xem Gói & mức sử dụng.",
            code="PLAN_LIMIT",
            status_code=409,
            details={"resource": resource, "limit": maximum},
        )


async def nlp_capacity(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    try:
        await enforce_limit(db, tenant_id, "nlp_responses_per_month")
    except AppError as exc:
        if exc.code == "PLAN_LIMIT":
            return False
        raise
    return True
