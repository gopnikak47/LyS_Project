"""Tiện ích chuỗi tiếng Việt."""

from __future__ import annotations

import re
import secrets
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def strip_diacritics(value: str) -> str:
    """Bỏ dấu tiếng Việt: "Đặng Thị Ánh" → "Dang Thi Anh"."""
    value = value.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def slugify(value: str, *, max_length: int = 60) -> str:
    slug = _NON_SLUG.sub("-", strip_diacritics(value).lower()).strip("-")
    return slug[:max_length].strip("-") or "khong-ten"


def random_suffix(length: int = 6) -> str:
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
