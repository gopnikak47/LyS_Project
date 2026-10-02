"""Middleware ASGI thuần (không dùng BaseHTTPMiddleware để không phá luồng SSE)."""

from __future__ import annotations

import time
from typing import ClassVar

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ERROR_MESSAGES, error_payload
from app.core.logging import get_logger
from app.core.request_context import sanitize_request_id, set_request_id

logger = get_logger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"
_QUIET_PATHS = frozenset({"/health", "/health/ready"})
_DOCS_PATHS = ("/api/docs", "/api/openapi.json")


class RequestContextMiddleware:
    """Gắn request-id, ghi access log JSON, và là "lưới an toàn" cuối cho lỗi chưa xử lý.

    - Nhận `X-Request-ID` từ client/nginx nếu hợp lệ, ngược lại tự sinh.
    - Gắn request-id vào mọi log trong request (structlog contextvars) và header phản hồi.
    - Lỗi không bắt được -> log kèm stack trace phía server, trả JSON 500 chuẩn, không lộ chi tiết.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = sanitize_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        set_request_id(request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("unhandled_error", path=scope.get("path"), method=scope.get("method"))
            if not response_started:
                response = JSONResponse(
                    status_code=500,
                    content=error_payload("INTERNAL_ERROR", ERROR_MESSAGES["INTERNAL_ERROR"]),
                )
                await response(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            from app.core.metrics import LATENCY, REQUESTS
            route = getattr(scope.get("route"), "path", "unmatched")
            REQUESTS.labels(scope.get("method", ""), route, str(status_code)).inc()
            LATENCY.labels(scope.get("method", ""), route).observe(duration_ms / 1000)
            path = scope.get("path", "")
            log = logger.debug if path in _QUIET_PATHS and status_code < 400 else logger.info
            log(
                "http_request",
                method=scope.get("method"),
                path=path,
                status=status_code,
                duration_ms=duration_ms,
            )
            structlog.contextvars.unbind_contextvars("request_id")
            set_request_id(None)


class SecurityHeadersMiddleware:
    """Header bảo mật mặc định cho mọi phản hồi của API."""

    _HEADERS: ClassVar[dict[str, str]] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }
    # API chỉ trả JSON nên CSP có thể rất chặt (trừ trang tài liệu OpenAPI).
    _API_CSP = "default-src 'none'; frame-ancestors 'none'"

    def __init__(self, app: ASGIApp, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_docs = str(scope.get("path", "")).startswith(_DOCS_PATHS)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in self._HEADERS.items():
                    headers.setdefault(key, value)
                if not is_docs:
                    headers.setdefault("Content-Security-Policy", self._API_CSP)
                if self.hsts:
                    headers.setdefault(
                        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)
