"""Registry validator câu trả lời, mở rộng mà không đổi lõi lưu phản hồi."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.errors import AppError

Validator = Callable[[dict[str, Any], Any], Any]
VALIDATORS: dict[str, Validator] = {}


def register(*names: str) -> Callable[[Validator], Validator]:
    def decorator(validator: Validator) -> Validator:
        for name in names:
            VALIDATORS[name] = validator
        return validator
    return decorator


@register("rating", "csat")
def rating(question: dict[str, Any], value: Any) -> int:
    if type(value) is not int or not 1 <= value <= 5:
        raise AppError("Đánh giá phải là số nguyên từ 1 đến 5.", code="INVALID_ANSWER")
    return value


@register("text")
def text(question: dict[str, Any], value: Any) -> str:
    if not isinstance(value, str) or len(value) > question.get("config", {}).get("max_length", 5000):
        raise AppError("Nhận xét vượt giới hạn ký tự hoặc sai định dạng.", code="INVALID_ANSWER")
    return value.strip()


@register("single_choice", "multi_choice")
def choice(question: dict[str, Any], value: Any) -> Any:
    options = {option["value"] for option in question["options"]}
    if question["type"] == "single_choice":
        valid = isinstance(value, str) and value in options
    else:
        valid = isinstance(value, list) and all(isinstance(v, str) and v in options for v in value) and len(set(value)) == len(value)
    if not valid:
        raise AppError("Lựa chọn không hợp lệ.", code="INVALID_ANSWER")
    return value


def validate_answers(questions: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    if set(answers) - {q["code"] for q in questions}:
        raise AppError("Câu trả lời chứa mã câu hỏi không thuộc khảo sát.", code="INVALID_ANSWER")
    result: dict[str, Any] = {}
    for question in questions:
        code = question["code"]
        value = answers.get(code)
        missing = value is None or value == "" or value == [] or (isinstance(value, str) and not value.strip())
        if missing:
            if question["required"]:
                raise AppError("Vui lòng trả lời câu hỏi bắt buộc.", code="REQUIRED_ANSWER", details={"question": code})
            continue
        validator = VALIDATORS.get(question["type"])
        if validator is None:
            raise AppError("Loại câu hỏi chưa được hỗ trợ.")
        result[code] = validator(question, value)
    return result
