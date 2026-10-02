"""JWT access token (ngắn hạn). Refresh token là chuỗi ngẫu nhiên lưu băm trong CSDL."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings
from app.models.enums import Role

ALGORITHM = "HS256"
ISSUER = "lys-api"


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: Role
    token_version: int
    expires_at: datetime


def create_access_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: Role,
    token_version: int,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    issued = now or datetime.now(UTC)
    expires = issued + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "role": role.value,
        "tv": token_version,
        "typ": "access",
        "iss": ISSUER,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)
    return token, expires


def decode_access_token(settings: Settings, token: str) -> AccessClaims | None:
    """Trả None nếu token hết hạn/sai chữ ký/sai cấu trúc — không phân biệt lý do ra ngoài."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "tid", "role", "tv"]},
        )
        if payload.get("typ") != "access":
            return None
        return AccessClaims(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tid"]),
            role=Role(payload["role"]),
            token_version=int(payload["tv"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
