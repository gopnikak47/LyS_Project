"""Đăng ký doanh nghiệp, đăng nhập, refresh token xoay vòng, quên/đặt lại mật khẩu (FR-01).

Chạy trên phiên hệ thống (chưa có/không chỉ một tenant) nhưng mọi truy vấn đều lọc rõ ràng
theo user/tenant tương ứng.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError, ConflictError, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.queue import TaskQueue
from app.core.ratelimit import RateLimiter, enforce
from app.core.security import hash_password, hash_token, new_token, verify_password
from app.core.text import random_suffix, slugify
from app.models import (
    Membership,
    PasswordResetToken,
    RefreshToken,
    Tenant,
    User,
)
from app.models.enums import MembershipStatus, Role, TenantStatus
from app.schemas.auth import LoginRequest, MembershipSummary, RegisterRequest
from app.services.audit import audit
from app.services.email import enqueue_email, password_reset_email
from app.services.workspaces import create_workspace

logger = get_logger(__name__)

# Băm giả để thời gian phản hồi như nhau dù email có tồn tại hay không (chống dò tài khoản).
_DUMMY_HASH = hash_password("khong-ton-tai-0", rounds=12)


class AccountLockedError(AppError):
    status_code = 423
    code = "ACCOUNT_LOCKED"


class InvalidCredentialsError(UnauthorizedError):
    code = "INVALID_CREDENTIALS"


class TokenInvalidError(AppError):
    status_code = 400
    code = "TOKEN_INVALID"


@dataclass(frozen=True, slots=True)
class IssuedRefresh:
    token: str
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        limiter: RateLimiter,
        queue: TaskQueue,
    ) -> None:
        self.db = db
        self.settings = settings
        self.limiter = limiter
        self.queue = queue

    # ------------------------------------------------------------------ đăng ký
    async def register(
        self, data: RegisterRequest, *, ip_hash: str | None
    ) -> tuple[User, Membership]:
        await enforce(
            self.limiter, f"register:ip:{ip_hash}", self.settings.register_rate_per_hour, 3600
        )
        existing = await self.db.execute(select(User.id).where(User.email == data.email))
        if existing.first():
            raise ConflictError("Email này đã được đăng ký.", code="EMAIL_TAKEN")

        user = User(
            email=data.email,
            full_name=data.full_name,
            password_hash=hash_password(data.password, self.settings.bcrypt_rounds),
        )
        try:
            async with self.db.begin_nested():
                self.db.add(user)
                await self.db.flush()
        except IntegrityError:
            # Hai request đăng ký cùng email chạy song song: request đến sau nhận 409.
            raise ConflictError("Email này đã được đăng ký.", code="EMAIL_TAKEN") from None
        tenant = await self._create_tenant(data.company_name, data.industry)
        membership = Membership(tenant_id=tenant.id, user_id=user.id, role=Role.ADMIN)
        self.db.add(membership)
        await create_workspace(
            self.db,
            tenant_id=tenant.id,
            name="Không gian chung",
            industry=data.industry,
            created_by=user.id,
        )
        await audit(
            self.db,
            tenant_id=tenant.id,
            user_id=user.id,
            action="tenant.register",
            entity_type="tenant",
            entity_id=tenant.id,
            ip_hash=ip_hash,
        )
        await self.db.flush()
        return user, membership

    async def _create_tenant(self, name: str, industry: str | None) -> Tenant:
        """Tạo tenant với slug duy nhất.

        Kiểm tra trước rồi mới chèn vẫn có thể trùng khi nhiều request chạy song song, nên chèn
        trong SAVEPOINT và thử lại với hậu tố ngẫu nhiên nếu vi phạm unique.
        """
        base = slugify(name, max_length=50)
        taken = (await self.db.execute(select(Tenant.id).where(Tenant.slug == base))).first()
        for attempt in range(6):
            slug = base if attempt == 0 and not taken else f"{base}-{random_suffix(4)}"
            tenant = Tenant(name=name, slug=slug, industry=industry)
            try:
                async with self.db.begin_nested():
                    self.db.add(tenant)
                    await self.db.flush()
                return tenant
            except IntegrityError:
                continue
        raise ConflictError("Không tạo được mã doanh nghiệp, vui lòng thử lại.")

    # ------------------------------------------------------------------ đăng nhập
    async def authenticate(
        self, data: LoginRequest, *, ip_hash: str | None
    ) -> tuple[User, Membership]:
        per_minute = self.settings.login_rate_per_minute
        await enforce(self.limiter, f"login:ip:{ip_hash}", per_minute * 3, 60)
        await enforce(self.limiter, f"login:email:{data.email}", per_minute, 60)

        user = (
            await self.db.execute(
                select(User).where(User.email == data.email, User.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if user is None:
            verify_password(data.password, _DUMMY_HASH)
            raise InvalidCredentialsError()

        now = datetime.now(UTC)
        if user.locked_until and user.locked_until > now:
            minutes = max(1, int((user.locked_until - now).total_seconds() // 60) + 1)
            raise AccountLockedError(
                "Tài khoản tạm khóa do đăng nhập sai nhiều lần. "
                f"Vui lòng thử lại sau {minutes} phút."
            )

        if not verify_password(data.password, user.password_hash):
            user.failed_login_count += 1
            locked = user.failed_login_count >= self.settings.login_max_attempts
            if locked:
                user.locked_until = now + timedelta(minutes=self.settings.login_lock_minutes)
                user.failed_login_count = 0
            membership = await self._pick_membership(user.id, None, strict=False)
            if membership is not None:
                await audit(
                    self.db,
                    tenant_id=membership.tenant_id,
                    user_id=user.id,
                    action="auth.login_locked" if locked else "auth.login_failed",
                    ip_hash=ip_hash,
                )
            await self.db.flush()
            raise InvalidCredentialsError()

        membership = await self._pick_membership(user.id, data.tenant_slug, strict=True)
        if membership is None:  # strict=True đã ném lỗi; giữ để mypy hiểu kiểu
            raise ForbiddenError(code="NO_TENANT")
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        await audit(
            self.db,
            tenant_id=membership.tenant_id,
            user_id=user.id,
            action="auth.login",
            ip_hash=ip_hash,
        )
        await self.db.flush()
        return user, membership

    async def _pick_membership(
        self, user_id: uuid.UUID, tenant_slug: str | None, *, strict: bool
    ) -> Membership | None:
        stmt = (
            select(Membership)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .where(
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE,
                Tenant.deleted_at.is_(None),
                Tenant.status == TenantStatus.ACTIVE,
            )
            .order_by(Membership.created_at)
        )
        if tenant_slug:
            stmt = stmt.where(Tenant.slug == tenant_slug)
        membership = (await self.db.execute(stmt)).scalars().first()
        if membership is None and strict:
            raise ForbiddenError(code="NO_TENANT")
        return membership

    async def membership_for(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Membership:
        membership = (
            await self.db.execute(
                select(Membership)
                .join(Tenant, Tenant.id == Membership.tenant_id)
                .where(
                    Membership.user_id == user_id,
                    Membership.tenant_id == tenant_id,
                    Membership.status == MembershipStatus.ACTIVE,
                    Tenant.deleted_at.is_(None),
                    Tenant.status == TenantStatus.ACTIVE,
                )
            )
        ).scalar_one_or_none()
        if membership is None:
            raise ForbiddenError()
        return membership

    async def memberships(self, user_id: uuid.UUID) -> list[MembershipSummary]:
        rows = await self.db.execute(
            select(Membership, Tenant)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .where(
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE,
                Tenant.deleted_at.is_(None),
            )
            .order_by(Tenant.name)
        )
        return [
            MembershipSummary(tenant_id=t.id, tenant_name=t.name, tenant_slug=t.slug, role=m.role)
            for m, t in rows.all()
        ]

    # ------------------------------------------------------------------ refresh token
    async def issue_refresh(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_agent: str | None,
        ip_hash: str | None,
        family_id: uuid.UUID | None = None,
    ) -> tuple[RefreshToken, IssuedRefresh]:
        raw = new_token()
        expires = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_ttl_days)
        row = RefreshToken(
            user_id=user_id,
            tenant_id=tenant_id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_token(raw),
            expires_at=expires,
            user_agent=(user_agent or "")[:300] or None,
            ip_hash=ip_hash,
        )
        self.db.add(row)
        await self.db.flush()
        return row, IssuedRefresh(raw, expires)

    async def rotate_refresh(
        self, raw: str, *, user_agent: str | None, ip_hash: str | None
    ) -> tuple[User, Membership, IssuedRefresh]:
        """Xoay vòng refresh token. Dùng lại token đã thu hồi → thu hồi cả "họ" token (bị lộ)."""
        current = (
            await self.db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
            )
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        if current is None:
            raise UnauthorizedError()
        if current.revoked_at is not None:
            logger.warning("refresh_token_reuse", family_id=str(current.family_id))
            await self._revoke_family(current.family_id, now)
            raise UnauthorizedError()
        if current.expires_at <= now:
            raise UnauthorizedError()

        user = await self.db.get(User, current.user_id)
        if user is None or user.deleted_at is not None:
            raise UnauthorizedError()
        membership = await self.membership_for(user.id, current.tenant_id)
        new_row, issued = await self.issue_refresh(
            user_id=user.id,
            tenant_id=current.tenant_id,
            user_agent=user_agent,
            ip_hash=ip_hash,
            family_id=current.family_id,
        )
        current.revoked_at = now
        current.replaced_by_id = new_row.id
        await self.db.flush()
        return user, membership, issued

    async def revoke(self, raw: str) -> None:
        current = (
            await self.db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
            )
        ).scalar_one_or_none()
        if current is not None:
            await self._revoke_family(current.family_id, datetime.now(UTC))

    async def _revoke_family(self, family_id: uuid.UUID, now: datetime) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def revoke_all_for_user(
        self, user_id: uuid.UUID, *, tenant_id: uuid.UUID | None = None
    ) -> None:
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
        if tenant_id is not None:
            stmt = stmt.where(RefreshToken.tenant_id == tenant_id)
        await self.db.execute(stmt.values(revoked_at=datetime.now(UTC)))

    # ------------------------------------------------------------------ mật khẩu
    async def forgot_password(self, email: str, *, ip_hash: str | None) -> None:
        """Luôn trả thành công (không tiết lộ email có tồn tại hay không)."""
        await enforce(self.limiter, f"forgot:ip:{ip_hash}", 10, 3600)
        if not await self.limiter.hit(f"forgot:email:{email}", 3, 3600):
            return
        user = (
            await self.db.execute(
                select(User).where(User.email == email, User.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if user is None:
            return
        raw = new_token()
        self.db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=self.settings.reset_token_ttl_minutes),
            )
        )
        await self.db.flush()
        link = f"{self.settings.public_base_url.rstrip('/')}/reset-password?token={raw}"
        enqueue_email(
            self.queue,
            password_reset_email(
                app_name=self.settings.app_name,
                to=user.email,
                full_name=user.full_name,
                link=link,
                ttl_minutes=self.settings.reset_token_ttl_minutes,
            ),
        )

    async def reset_password(self, raw: str, password: str) -> User:
        now = datetime.now(UTC)
        token = (
            await self.db.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.token_hash == hash_token(raw),
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > now,
                )
            )
        ).scalar_one_or_none()
        if token is None:
            raise TokenInvalidError()
        user = await self.db.get(User, token.user_id)
        if user is None or user.deleted_at is not None:
            raise TokenInvalidError()
        token.used_at = now
        await self.set_password(user, password)
        user.failed_login_count = 0
        user.locked_until = None
        await self.db.flush()
        return user

    async def set_password(self, user: User, password: str) -> None:
        """Đổi mật khẩu: tăng token_version (vô hiệu access token cũ), thu hồi mọi refresh token."""
        user.password_hash = hash_password(password, self.settings.bcrypt_rounds)
        user.token_version += 1
        await self.revoke_all_for_user(user.id)
        await self.db.flush()
