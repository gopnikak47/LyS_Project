"""Lỗi chuẩn hóa của API.

Mọi lỗi trả về theo một định dạng duy nhất để frontend xử lý thống nhất:

    {"error": {"code": "NOT_FOUND", "message": "…", "details": …, "request_id": "…"}}

`code` là mã ổn định (frontend có thể dịch theo mã), `message` mặc định tiếng Việt.
Không bao giờ trả stack trace ra ngoài.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, TypeVar, cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.core.request_context import get_request_id

logger = get_logger(__name__)

# Thông điệp mặc định theo mã lỗi.
ERROR_MESSAGES: dict[str, str] = {
    "BAD_REQUEST": "Yêu cầu không hợp lệ.",
    "UNAUTHORIZED": "Bạn cần đăng nhập để tiếp tục.",
    "FORBIDDEN": "Bạn không có quyền thực hiện thao tác này.",
    "NOT_FOUND": "Không tìm thấy tài nguyên.",
    "METHOD_NOT_ALLOWED": "Phương thức không được hỗ trợ.",
    "CONFLICT": "Dữ liệu bị xung đột, vui lòng tải lại và thử lại.",
    "PAYLOAD_TOO_LARGE": "Dữ liệu gửi lên quá lớn.",
    "VALIDATION_ERROR": "Dữ liệu không hợp lệ.",
    "RATE_LIMITED": "Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút.",
    "SERVICE_UNAVAILABLE": "Dịch vụ tạm thời không khả dụng.",
    "INTERNAL_ERROR": "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.",
    "INVALID_CREDENTIALS": "Email hoặc mật khẩu không đúng.",
    "ACCOUNT_LOCKED": "Tài khoản tạm khóa do đăng nhập sai nhiều lần. Vui lòng thử lại sau.",
    "CSRF_FAILED": "Phiên làm việc không hợp lệ, vui lòng tải lại trang.",
    "TOKEN_INVALID": "Liên kết không hợp lệ hoặc đã hết hạn.",
    "LAST_ADMIN": "Doanh nghiệp phải còn ít nhất một quản trị viên.",
    "NO_TENANT": "Tài khoản chưa thuộc doanh nghiệp nào.",
}

_STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}


class AppError(Exception):
    """Lỗi nghiệp vụ có chủ đích; ném ra từ service/repository."""

    status_code: int = HTTPStatus.BAD_REQUEST
    code: str = "BAD_REQUEST"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.message = message or ERROR_MESSAGES.get(self.code, ERROR_MESSAGES["BAD_REQUEST"])
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"


class UnauthorizedError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "CONFLICT"


T = TypeVar("T")


def found(value: T | None, message: str | None = None) -> T:
    """Trả về giá trị hoặc ném NotFoundError (thay cho assert trong code chạy thật)."""
    if value is None:
        raise NotFoundError(message)
    return value


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message, "request_id": get_request_id()}
    if details is not None:
        body["details"] = jsonable_encoder(details)
    return {"error": body}


def _response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, details),
        headers=headers,
    )


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    exc = cast(AppError, exc)
    return _response(exc.status_code, exc.code, exc.message, exc.details)


async def _http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    exc = cast(StarletteHTTPException, exc)
    fallback = "BAD_REQUEST" if exc.status_code < 500 else "INTERNAL_ERROR"
    code = _STATUS_TO_CODE.get(exc.status_code, fallback)
    try:
        default_phrase = HTTPStatus(exc.status_code).phrase
    except ValueError:
        default_phrase = ""
    # Chỉ dùng `detail` nếu là chuỗi do ta chủ động đặt; mặc định dùng thông điệp tiếng Việt.
    message = (
        exc.detail
        if isinstance(exc.detail, str) and exc.detail and exc.detail != default_phrase
        else ERROR_MESSAGES[code]
    )
    return _response(exc.status_code, code, message, headers=getattr(exc, "headers", None))


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    exc = cast(RequestValidationError, exc)
    details = [
        {
            "field": ".".join(str(part) for part in err.get("loc", ()) if part != "body"),
            "type": err.get("type"),
            "message": err.get("msg"),
        }
        for err in exc.errors()
    ]
    return _response(422, "VALIDATION_ERROR", ERROR_MESSAGES["VALIDATION_ERROR"], details)


async def _pydantic_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # ValidationError phát sinh trong service (không phải ở biên request) — vẫn trả 422 chuẩn.
    exc = cast(ValidationError, exc)
    details = [
        {
            "field": ".".join(str(part) for part in err.get("loc", ())),
            "type": err.get("type"),
            "message": err.get("msg"),
        }
        for err in exc.errors()
    ]
    return _response(422, "VALIDATION_ERROR", ERROR_MESSAGES["VALIDATION_ERROR"], details)


async def _integrity_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Vi phạm ràng buộc CSDL (thường do 2 request ghi đồng thời): 409, không lộ chi tiết SQL.
    logger.warning("integrity_error", error=str(getattr(exc, "orig", exc))[:300])
    return _response(409, "CONFLICT", ERROR_MESSAGES["CONFLICT"])


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_error",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
    )
    return _response(500, "INTERNAL_ERROR", ERROR_MESSAGES["INTERNAL_ERROR"])


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(ValidationError, _pydantic_error_handler)
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
