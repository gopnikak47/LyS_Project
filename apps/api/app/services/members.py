"""Thành viên & lời mời (FR-03)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.config import Settings
from app.core.errors import AppError, ConflictError, NotFoundError, UnauthorizedError
from app.core.permissions import Permission
from app.core.queue import TaskQueue
from app.core.security import hash_password, hash_token, new_token, verify_password
from app.models import Invitation, Membership, Tenant, User, Workspace, WorkspaceMember
from app.models.enums import MembershipStatus, Role
from app.schemas.members import InvitationCreate, MemberOut, MemberUpdate, PublicInvitationOut
from app.services.audit import audit
from app.services.auth import TokenInvalidError
from app.services.email import ROLE_LABELS, enqueue_email, invitation_email


class LastAdminError(AppError):
    status_code = 409
    code = "LAST_ADMIN"


class MemberService:
    def __init__(self, db: AsyncSession, principal: Principal) -> None:
        self.db = db
        self.principal = principal

    async def list_members(self) -> list[MemberOut]:
        rows = (
            await self.db.execute(
                select(Membership, User)
                .join(User, User.id == Membership.user_id)
                .where(Membership.tenant_id == self.principal.tenant_id)
                .order_by(Membership.created_at)
            )
        ).all()
        scopes: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        for user_id, workspace_id in (
            await self.db.execute(
                select(WorkspaceMember.user_id, WorkspaceMember.workspace_id).where(
                    WorkspaceMember.tenant_id == self.principal.tenant_id
                )
            )
        ).all():
            scopes[user_id].append(workspace_id)
        return [
            MemberOut(
                id=m.id,
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=m.role,
                status=m.status,
                all_workspaces=m.role == Role.ADMIN or m.all_workspaces,
                workspace_ids=sorted(scopes.get(u.id, [])),
                last_login_at=u.last_login_at,
                created_at=m.created_at,
            )
            for m, u in rows
        ]

    async def _get(self, membership_id: uuid.UUID) -> Membership:
        membership = (
            await self.db.execute(
                select(Membership).where(
                    Membership.id == membership_id,
                    Membership.tenant_id == self.principal.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if membership is None:
            raise NotFoundError("Không tìm thấy thành viên.")
        return membership

    async def _active_admin_count(self) -> int:
        return int(
            (
                await self.db.execute(
                    select(func.count()).where(
                        Membership.tenant_id == self.principal.tenant_id,
                        Membership.role == Role.ADMIN,
                        Membership.status == MembershipStatus.ACTIVE,
                    )
                )
            ).scalar_one()
        )

    async def _validate_workspaces(self, workspace_ids: list[uuid.UUID]) -> None:
        if not workspace_ids:
            return
        found = (
            await self.db.execute(
                select(func.count()).where(
                    Workspace.id.in_(workspace_ids),
                    Workspace.tenant_id == self.principal.tenant_id,
                    Workspace.deleted_at.is_(None),
                )
            )
        ).scalar_one()
        if found != len(set(workspace_ids)):
            raise NotFoundError("Không tìm thấy không gian khảo sát.")

    async def update(self, membership_id: uuid.UUID, data: MemberUpdate) -> Membership:
        self.principal.require(Permission.MEMBER_MANAGE)
        membership = await self._get(membership_id)
        was_active_admin = (
            membership.role == Role.ADMIN and membership.status == MembershipStatus.ACTIVE
        )
        losing_admin = (data.role is not None and data.role != Role.ADMIN) or (
            data.status is not None and data.status != MembershipStatus.ACTIVE
        )
        if was_active_admin and losing_admin and await self._active_admin_count() <= 1:
            raise LastAdminError()

        if data.role is not None:
            membership.role = data.role
        if data.status is not None:
            membership.status = data.status
        if data.all_workspaces is not None:
            membership.all_workspaces = data.all_workspaces
        if data.workspace_ids is not None:
            await self._validate_workspaces(data.workspace_ids)
            existing = await self.db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.user_id == membership.user_id,
                    WorkspaceMember.tenant_id == self.principal.tenant_id,
                )
            )
            for row in existing.scalars():
                await self.db.delete(row)
            for ws_id in set(data.workspace_ids):
                self.db.add(
                    WorkspaceMember(
                        tenant_id=self.principal.tenant_id,
                        workspace_id=ws_id,
                        user_id=membership.user_id,
                    )
                )
        await self.db.flush()
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="member.update",
            entity_type="membership",
            entity_id=membership.id,
            data=data.model_dump(mode="json", exclude_none=True),
        )
        return membership

    async def remove(self, membership_id: uuid.UUID) -> uuid.UUID:
        self.principal.require(Permission.MEMBER_MANAGE)
        membership = await self._get(membership_id)
        if (
            membership.role == Role.ADMIN
            and membership.status == MembershipStatus.ACTIVE
            and await self._active_admin_count() <= 1
        ):
            raise LastAdminError()
        user_id = membership.user_id
        existing = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.tenant_id == self.principal.tenant_id,
            )
        )
        for row in existing.scalars():
            await self.db.delete(row)
        await self.db.delete(membership)
        await self.db.flush()
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="member.remove",
            entity_type="membership",
            entity_id=membership_id,
            data={"user_id": str(user_id)},
        )
        return user_id


class InvitationService:
    def __init__(
        self, db: AsyncSession, principal: Principal, settings: Settings, queue: TaskQueue
    ) -> None:
        self.db = db
        self.principal = principal
        self.settings = settings
        self.queue = queue

    async def list_pending(self) -> list[Invitation]:
        rows = await self.db.execute(
            select(Invitation)
            .where(
                Invitation.tenant_id == self.principal.tenant_id,
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
            )
            .order_by(Invitation.created_at.desc())
        )
        return list(rows.scalars())

    async def create(self, data: InvitationCreate) -> tuple[Invitation, str]:
        self.principal.require(Permission.MEMBER_MANAGE)
        already = await self.db.execute(
            select(Membership.id)
            .join(User, User.id == Membership.user_id)
            .where(User.email == data.email, Membership.tenant_id == self.principal.tenant_id)
        )
        if already.first():
            raise ConflictError("Người này đã là thành viên.", code="ALREADY_MEMBER")
        await MemberService(self.db, self.principal)._validate_workspaces(data.workspace_ids)

        now = datetime.now(UTC)
        for old in await self.list_pending():
            if old.email == data.email:
                old.revoked_at = now
        raw = new_token()
        invitation = Invitation(
            tenant_id=self.principal.tenant_id,
            email=data.email,
            role=data.role,
            workspace_ids=list(dict.fromkeys(data.workspace_ids)),
            token_hash=hash_token(raw),
            invited_by=self.principal.user_id,
            expires_at=now + timedelta(days=self.settings.invite_ttl_days),
        )
        self.db.add(invitation)
        await self.db.flush()

        tenant = await self.db.get(Tenant, self.principal.tenant_id)
        link = f"{self.settings.public_base_url.rstrip('/')}/invite/{raw}"
        enqueue_email(
            self.queue,
            invitation_email(
                app_name=self.settings.app_name,
                to=data.email,
                tenant_name=tenant.name if tenant else "",
                inviter_name=self.principal.full_name,
                role_label=ROLE_LABELS[data.role.value],
                link=link,
            ),
        )
        await audit(
            self.db,
            tenant_id=self.principal.tenant_id,
            user_id=self.principal.user_id,
            action="invitation.create",
            entity_type="invitation",
            entity_id=invitation.id,
            data={"email": data.email, "role": data.role.value},
        )
        return invitation, link

    async def revoke(self, invitation_id: uuid.UUID) -> None:
        self.principal.require(Permission.MEMBER_MANAGE)
        invitation = (
            await self.db.execute(
                select(Invitation).where(
                    Invitation.id == invitation_id,
                    Invitation.tenant_id == self.principal.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if invitation is None:
            raise NotFoundError("Không tìm thấy lời mời.")
        invitation.revoked_at = datetime.now(UTC)
        await self.db.flush()


# ---------------------------------------------------------------------- công khai (phiên hệ thống)
async def _valid_invitation(db: AsyncSession, raw: str) -> Invitation:
    invitation = (
        await db.execute(
            select(Invitation).where(
                Invitation.token_hash == hash_token(raw),
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
                Invitation.expires_at > datetime.now(UTC),
            )
        )
    ).scalar_one_or_none()
    if invitation is None:
        raise TokenInvalidError("Lời mời không hợp lệ hoặc đã hết hạn.")
    return invitation


async def describe_invitation(db: AsyncSession, raw: str) -> PublicInvitationOut:
    invitation = await _valid_invitation(db, raw)
    tenant = await db.get(Tenant, invitation.tenant_id)
    inviter = await db.get(User, invitation.invited_by) if invitation.invited_by else None
    user_exists = (
        await db.execute(select(User.id).where(User.email == invitation.email))
    ).first() is not None
    return PublicInvitationOut(
        tenant_name=tenant.name if tenant else "",
        email=invitation.email,
        role=invitation.role,
        inviter_name=inviter.full_name if inviter else None,
        user_exists=user_exists,
        expires_at=invitation.expires_at,
    )


async def accept_invitation(
    db: AsyncSession,
    raw: str,
    *,
    full_name: str | None,
    password: str,
    settings: Settings,
) -> tuple[User, Membership]:
    """Nhận lời mời: người đã có tài khoản xác nhận bằng mật khẩu; người mới tạo tài khoản."""
    from app.schemas.members import InvitationAcceptNew

    invitation = await _valid_invitation(db, raw)
    user = (
        await db.execute(select(User).where(User.email == invitation.email))
    ).scalar_one_or_none()
    if user is not None:
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Mật khẩu không đúng.", code="INVALID_CREDENTIALS")
    else:
        new_user = InvitationAcceptNew(full_name=full_name or "", password=password)
        user = User(
            email=invitation.email,
            full_name=new_user.full_name,
            password_hash=hash_password(new_user.password, settings.bcrypt_rounds),
            email_verified_at=datetime.now(UTC),
        )
        db.add(user)
        await db.flush()

    existing = (
        await db.execute(
            select(Membership).where(
                Membership.tenant_id == invitation.tenant_id, Membership.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Bạn đã là thành viên của doanh nghiệp này.", code="ALREADY_MEMBER")
    membership = Membership(
        tenant_id=invitation.tenant_id,
        user_id=user.id,
        role=invitation.role,
        all_workspaces=not invitation.workspace_ids,
    )
    db.add(membership)
    for ws_id in invitation.workspace_ids:
        db.add(WorkspaceMember(tenant_id=invitation.tenant_id, workspace_id=ws_id, user_id=user.id))
    invitation.accepted_at = datetime.now(UTC)
    await db.flush()
    await audit(
        db,
        tenant_id=invitation.tenant_id,
        user_id=user.id,
        action="invitation.accept",
        entity_type="invitation",
        entity_id=invitation.id,
    )
    return user, membership
