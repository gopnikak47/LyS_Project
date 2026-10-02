"""Logic chỉ tham chiếu câu trước và jump tiến: cấu trúc không có vòng lặp."""
from __future__ import annotations

from typing import Any

from app.core.errors import AppError

OPERATORS = frozenset({"eq", "ne", "contains", "gt", "lt"})


def condition(rule: dict[str, Any] | None, answers: dict[str, Any]) -> bool:
    if not rule:
        return True
    if "all" in rule:
        return all(condition(item, answers) for item in rule["all"])
    if "any" in rule:
        return any(condition(item, answers) for item in rule["any"])
    actual = answers.get(rule["question"])
    expected = rule.get("value")
    op = rule["operator"]
    if actual is None:
        return False
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "contains":
        return isinstance(actual, (list, str)) and expected in actual
    if op in {"gt", "lt"}:
        return type(actual) in (int, float) and type(expected) in (int, float) and (actual > expected if op == "gt" else actual < expected)
    return False


def check_rule(rule: Any, previous: set[str], depth: int = 0) -> None:
    if not rule:
        return
    if depth > 8 or not isinstance(rule, dict):
        raise AppError("Điều kiện không hợp lệ hoặc lồng quá sâu.")
    if "all" in rule or "any" in rule:
        group = rule.get("all", rule.get("any"))
        if not isinstance(group, list) or not 1 <= len(group) <= 20:
            raise AppError("Nhóm điều kiện cần 1–20 điều kiện con.")
        for item in group:
            check_rule(item, previous, depth + 1)
    elif rule.get("question") not in previous or rule.get("operator") not in OPERATORS:
        raise AppError("Điều kiện phải tham chiếu câu trước với toán tử hợp lệ.")


def validate_logic(questions: list[dict[str, Any]]) -> None:
    positions = {q["code"]: index for index, q in enumerate(questions)}
    for index, question in enumerate(questions):
        previous = set(list(positions)[:index])
        logic = question.get("logic", {})
        check_rule(logic.get("display_if"), previous)
        carry = logic.get("carry_from")
        if carry and carry not in previous:
            raise AppError("Carry forward chỉ lấy từ câu trước.")
        jumps = logic.get("jumps", [])
        if not isinstance(jumps, list) or len(jumps) > 20:
            raise AppError("Tối đa 20 quy tắc rẽ nhánh mỗi câu.")
        for jump in jumps:
            check_rule(jump.get("if"), previous | {question["code"]})
            target = jump.get("target")
            if target != "end" and (target not in positions or positions[target] <= index):
                raise AppError("Điểm rẽ nhánh phải là câu phía sau hoặc kết thúc.")
        for option in question.get("options", []):
            check_rule(option.get("display_if"), previous)


def path(questions: list[dict[str, Any]], answers: dict[str, Any]) -> list[dict[str, Any]]:
    visible = []
    index = 0
    positions = {q["code"]: i for i, q in enumerate(questions)}
    previous_answers: dict[str, Any] = {}
    while index < len(questions):
        question = dict(questions[index]); logic = question.get("logic", {})
        if not condition(logic.get("display_if"), previous_answers):
            index += 1
            continue
        question["options"] = [option for option in question.get("options", []) if condition(option.get("display_if"), previous_answers)]
        carry = logic.get("carry_from")
        if carry:
            source = next(q for q in questions if q["code"] == carry)
            selected = previous_answers.get(carry, [])
            selected = selected if isinstance(selected, list) else [selected]
            question["options"] = [option for option in source.get("options", []) if option["value"] in selected]
        visible.append(question)
        if question["code"] in answers:
            previous_answers[question["code"]] = answers[question["code"]]
        next_index = index + 1
        for jump in logic.get("jumps", []):
            if question["code"] in answers and condition(jump.get("if"), previous_answers):
                next_index = len(questions) if jump["target"] == "end" else positions[jump["target"]]
                break
        index = next_index
    return visible
