from __future__ import annotations

from pathlib import Path

from app.db.erd import render

ERD_DOC = Path(__file__).parents[3] / "docs" / "erd.md"


def test_erd_doc_is_up_to_date() -> None:
    assert ERD_DOC.read_text(encoding="utf-8") == render(), (
        "docs/erd.md đã cũ — chạy: uv run python -m app.db.erd > docs/erd.md"
    )
