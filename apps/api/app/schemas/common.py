"""Kiểu dữ liệu dùng chung cho schema API."""

from __future__ import annotations

import re
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


def _normalize_email(value: str) -> str:
    return value.strip().lower()


Email = Annotated[EmailStr, AfterValidator(_normalize_email)]

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]

_HAS_LETTER = re.compile(r"[^\W\d_]")
_HAS_DIGIT = re.compile(r"\d")


def _password_policy(value: str) -> str:
    if not _HAS_LETTER.search(value) or not _HAS_DIGIT.search(value):
        raise ValueError("Mật khẩu cần có cả chữ và số.")
    return value


Password = Annotated[str, Field(min_length=8, max_length=128), AfterValidator(_password_policy)]


class Page(ApiModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class OkResponse(ApiModel):
    ok: bool = True
