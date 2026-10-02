"""Băm mật khẩu, token và định danh cá nhân."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

import bcrypt


def _prehash(password: str) -> bytes:
    # bcrypt chỉ dùng 72 byte đầu: băm SHA-256 trước để mật khẩu dài vẫn được tính trọn vẹn.
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str, rounds: int = 12) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("ascii"))
    except ValueError:
        return False


def new_token(nbytes: int = 32) -> str:
    """Token ngẫu nhiên an toàn cho URL (refresh, đặt lại mật khẩu, lời mời…)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Chỉ lưu băm của token trong CSDL — lộ CSDL cũng không dùng lại được token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_identifier(value: str, salt: str) -> str:
    """Băm có muối cho IP/fingerprint (bảo vệ dữ liệu cá nhân, vẫn đếm trùng được)."""
    return hmac.new(salt.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
