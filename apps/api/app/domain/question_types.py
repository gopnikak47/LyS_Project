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
    if not isinstance(value, str) or len(value) > question.get("config", {}).get(
        "max_length", 5000
    ):
        raise AppError("Nhận xét vượt giới hạn ký tự hoặc sai định dạng.", code="INVALID_ANSWER")
    return value.strip()


@register("single_choice", "multi_choice", "picture_choice")
def choice(question: dict[str, Any], value: Any) -> Any:
    options = {option["value"] for option in question["options"]}
    if question["type"] in {"single_choice", "picture_choice"}:
        valid = isinstance(value, str) and value in options
    else:
        valid = (
            isinstance(value, list)
            and all(isinstance(v, str) and v in options for v in value)
            and len(set(value)) == len(value)
        )
    if not valid:
        raise AppError("Lựa chọn không hợp lệ.", code="INVALID_ANSWER")
    return value


@register("nps", "slider")
def scale(question: dict[str, Any], value: Any) -> int:
    config = question.get("config", {})
    low, high, step = (
        (0, 10, 1)
        if question["type"] == "nps"
        else (config.get("min", 0), config.get("max", 100), config.get("step", 1))
    )
    if type(value) is not int or not low <= value <= high or (value - low) % step:
        raise AppError("Giá trị thang đo không hợp lệ.", code="INVALID_ANSWER")
    return value


@register("ranking")
def ranking(question: dict[str, Any], value: Any) -> list[str]:
    allowed = {o["value"] for o in question["options"]}
    if (
        not isinstance(value, list)
        or any(not isinstance(v, str) for v in value)
        or set(value) != allowed
        or len(value) != len(allowed)
    ):
        raise AppError("Vui lòng xếp hạng đầy đủ, không trùng đáp án.")
    return value


@register("contact")
def contact(question: dict[str, Any], value: Any) -> dict[str, str]:
    import re

    from pydantic import EmailStr, TypeAdapter, ValidationError

    if (
        not isinstance(value, dict)
        or set(value) - {"name", "email", "phone"}
        or any(not isinstance(v, str) or len(v) > 200 for v in value.values())
    ):
        raise AppError("Thông tin liên hệ không hợp lệ.")
    try:
        if value.get("email"):
            TypeAdapter(EmailStr).validate_python(value["email"])
    except ValidationError as exc:
        raise AppError("Email không hợp lệ.") from exc
    if value.get("phone") and not re.fullmatch(r"\+?[0-9 ()-]{8,20}", value["phone"]):
        raise AppError("Số điện thoại không hợp lệ.")
    return value


@register("datetime")
def date_time(question: dict[str, Any], value: Any) -> str:
    from datetime import datetime

    if not isinstance(value, str) or len(value) > 40:
        raise AppError("Ngày giờ không hợp lệ.")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise AppError("Ngày giờ không hợp lệ.") from exc
    return value


@register("matrix")
def matrix(question: dict[str, Any], value: Any) -> dict[str, str]:
    config = question.get("config", {})
    if (
        not isinstance(value, dict)
        or set(value) != set(config["rows"])
        or any(v not in config["columns"] for v in value.values())
    ):
        raise AppError("Vui lòng chọn một giá trị cho mỗi hàng ma trận.")
    return value


@register("upload")
def upload(question: dict[str, Any], value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("key"), str)
        or value.get("scanned") is not True
    ):
        raise AppError("Tệp cần được tải lên và quét trước khi gửi.")
    return value


def validate_answers(questions: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, Any]:
    from app.domain.survey_logic import path

    if set(answers) - {q["code"] for q in questions}:
        raise AppError("Câu trả lời chứa mã câu hỏi không thuộc khảo sát.", code="INVALID_ANSWER")
    questions = path(questions, answers)
    result: dict[str, Any] = {}
    for question in questions:
        code = question["code"]
        value = answers.get(code)
        missing = (
            value is None
            or value == ""
            or value == []
            or (isinstance(value, str) and not value.strip())
        )
        if missing:
            if question["required"]:
                raise AppError(
                    "Vui lòng trả lời câu hỏi bắt buộc.",
                    code="REQUIRED_ANSWER",
                    details={"question": code},
                )
            continue
        validator = VALIDATORS.get(question["type"])
        if validator is None:
            raise AppError("Loại câu hỏi chưa được hỗ trợ.")
        result[code] = validator(question, value)
    return result
