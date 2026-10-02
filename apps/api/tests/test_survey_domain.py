from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core.errors import AppError
from app.core.storage import LocalStorage
from app.domain.question_types import validate_answers
from app.domain.quiz import grade, questions_for_attempt
from app.domain.survey_logic import condition, validate_logic
from app.domain.tabular import csv_bytes, rows, safe_cell
from app.schemas.surveys import QuestionInput


def question(code: str = "score", kind: str = "rating", **extra: Any) -> dict[str, Any]:
    return {
        "code": code,
        "type": kind,
        "required": True,
        "options": [],
        "logic": {},
        "config": {},
        **extra,
    }


@pytest.mark.parametrize("value", [True, False, 0, 6, "5", [], {}, None])
def test_rating_rejects_invalid_values(value: Any) -> None:
    with pytest.raises(AppError):
        validate_answers([question()], {"score": value})


def test_skip_logic_and_hidden_options() -> None:
    questions = [
        question(),
        question(
            "comment",
            "text",
            logic={
                "display_if": {
                    "question": "score",
                    "operator": "lt",
                    "value": 3,
                }
            },
        ),
    ]
    validate_logic(questions)
    assert validate_answers(questions, {"score": 5}) == {"score": 5}
    with pytest.raises(AppError):
        validate_answers(questions, {"score": 1})
    questions[0]["logic"] = {"jumps": [{"if": {}, "target": "score"}]}
    with pytest.raises(AppError):
        validate_logic(questions)
    assert not condition({"question": "x", "operator": "contains", "value": {}}, {"x": "abc"})


def test_quiz_snapshot_is_not_mutated_and_grading_is_exact() -> None:
    questions = [
        question(
            "pick",
            "multi_choice",
            options=[{"value": "a"}, {"value": "b"}],
            points=2,
            config={"correct_answer": ["a", "b"]},
        )
    ]
    snapshot = {
        "questions": questions,
        "is_quiz": True,
        "settings": {"randomize_options": True, "quiz_draw_count": 1},
    }
    assert questions_for_attempt(snapshot, "nonce") == questions_for_attempt(snapshot, "nonce")
    assert questions[0]["options"] == [{"value": "a"}, {"value": "b"}]
    assert grade(questions, {"pick": ["b", "a"]})["score"] == 2
    assert grade(questions, {"pick": ["a"]})["score"] == 0


def test_image_schema_accepts_signed_asset_and_blocks_external_urls() -> None:
    data: dict[str, Any] = {
        "code": "pick",
        "type": "picture_choice",
        "title": {"vi": "Chọn"},
        "options": [
            {"value": "a", "label": {"vi": "A"}, "image_url": "/api/v1/public/assets/a.b-c"},
            {"value": "b", "label": {"vi": "B"}},
        ],
    }
    assert QuestionInput.model_validate(data).options[0].image_url
    data["options"][0]["image_url"] = "//evil.example/image.png"
    with pytest.raises(ValueError, match="image_url"):
        QuestionInput.model_validate(data)


def test_storage_and_csv_formula_injection(tmp_path: Path) -> None:
    storage = LocalStorage(str(tmp_path))
    for key in ("../escape", str(tmp_path.parent / "escape"), "."):
        with pytest.raises(ValueError, match="Khóa lưu trữ"):
            storage.path(key)
    storage.put("input.csv", csv_bytes(["comment"], [["=HYPERLINK(1)"]]))
    assert list(rows(storage.path("input.csv"))) == [{"comment": "'=HYPERLINK(1)"}]
    assert safe_cell("  @SUM(1)") == "'  @SUM(1)"
    storage.delete("input.csv")
    assert not storage.path("input.csv").exists()
