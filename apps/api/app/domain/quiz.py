from __future__ import annotations

import copy
import random
from typing import Any


def questions_for_attempt(snapshot: dict[str, Any], nonce: str) -> list[dict[str, Any]]:
    questions = copy.deepcopy(snapshot["questions"])
    rng = random.Random(nonce)  # noqa: S311 — chỉ xáo thứ tự, nonce được sinh bằng secrets.
    settings = snapshot.get("settings", {})
    count = settings.get("quiz_draw_count")
    if snapshot.get("is_quiz") and count:
        questions = rng.sample(questions, min(count, len(questions)))
    if settings.get("randomize_questions"):
        rng.shuffle(questions)
    if settings.get("randomize_options"):
        for question in questions:
            rng.shuffle(question["options"])
    return questions


def grade(questions: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    score = maximum = 0.0
    detail = []
    for question in questions:
        points = float(question.get("points") or 0)
        expected = question.get("config", {}).get("correct_answer")
        if not points or expected is None:
            continue
        actual = answers.get(question["code"])
        correct = set(actual) == set(expected) if question["type"] == "multi_choice" and isinstance(actual, list) and isinstance(expected, list) else actual == expected
        maximum += points
        if correct:
            score += points
        detail.append({"code": question["code"], "correct": correct, "expected": expected, "points": points if correct else 0})
    percent = score / maximum * 100 if maximum else 0
    return {"score": score, "maximum": maximum, "percent": percent, "classification": "Xuất sắc" if percent >= 90 else "Đạt" if percent >= 50 else "Chưa đạt", "detail": detail}
