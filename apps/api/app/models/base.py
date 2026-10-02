"""Lớp nền cho model ORM: quy ước đặt tên ràng buộc, kiểu mặc định, mixin dùng chung."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, MetaData, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Quy ước tên ràng buộc để migration ổn định giữa các môi trường.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {  # noqa: RUF012 — thuộc tính đặc biệt của SQLAlchemy
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
        datetime: DateTime(timezone=True),
        uuid.UUID: UUID(as_uuid=True),
    }


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Enum lưu dạng VARCHAR + CHECK (dễ thêm giá trị hơn enum native của PostgreSQL)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class UUIDPrimaryKey:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CreatedAt:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class SoftDelete:
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class TenantScoped:
    """Bảng thuộc về một doanh nghiệp: luôn có tenant_id và chịu chính sách RLS."""

    __tenant_scoped__ = True

    @declared_attr
    @classmethod
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
        )
