"""Sinh sơ đồ ERD (Mermaid) trực tiếp từ metadata SQLAlchemy.

Chạy: `uv run python -m app.db.erd > docs/erd.md` — test sẽ báo nếu tài liệu lệch với model.
"""

from __future__ import annotations

from sqlalchemy import Table

from app.models import TENANT_SCOPED_TABLES, Base

HEADER = """# Sơ đồ quan hệ dữ liệu (ERD)

> Tự sinh từ model SQLAlchemy bằng `uv run python -m app.db.erd > docs/erd.md`. Không sửa tay.

- Mọi bảng có `tenant_id` đều bật **Row-Level Security** (chính sách `tenant_isolation`).
- `tenants` lọc theo `id`; `users` chỉ thấy chính mình hoặc thành viên cùng tenant.
- Bảng toàn cục (không RLS, chỉ truy cập qua phiên hệ thống): `plans`, `nlp_models`,
  `refresh_tokens`, `password_reset_tokens`.
"""


def _type_name(col_type: object) -> str:
    name = type(col_type).__name__.lower()
    return {"varchar": "string", "enum": "enum", "uuid": "uuid", "jsonb": "jsonb"}.get(name, name)


def _entity(table: Table) -> str:
    lines = [f"  {table.name} {{"]
    for col in table.columns:
        markers = []
        if col.primary_key:
            markers.append("PK")
        if col.foreign_keys:
            markers.append("FK")
        if col.unique:
            markers.append("UK")
        suffix = f" {','.join(markers)}" if markers else ""
        lines.append(f"    {_type_name(col.type)} {col.name}{suffix}")
    lines.append("  }")
    return "\n".join(lines)


def render() -> str:
    tables = sorted(Base.metadata.tables.values(), key=lambda t: t.name)
    parts = [HEADER, "```mermaid", "erDiagram"]
    for table in tables:
        for fk in sorted(table.foreign_keys, key=lambda f: (f.parent.name, f.column.table.name)):
            target = fk.column.table.name
            if fk.parent.name == "tenant_id" and target == "tenants" and table.name != "tenants":
                continue  # Bỏ cạnh tenant_id để sơ đồ dễ đọc (bảng nào cũng có).
            card = "|o--o{" if fk.parent.nullable else "||--o{"
            parts.append(f"  {target} {card} {table.name} : {fk.parent.name}")
    parts.extend(_entity(t) for t in tables)
    parts.append("```")
    parts.append("")
    parts.append("## Bảng chịu RLS theo tenant")
    parts.append("")
    parts.append(", ".join(f"`{name}`" for name in TENANT_SCOPED_TABLES))
    parts.append("")
    return "\n".join(parts)


if __name__ == "__main__":
    print(render(), end="")
