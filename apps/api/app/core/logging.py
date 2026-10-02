"""Cấu hình log có cấu trúc (JSON) dùng chung cho API và worker.

Mọi log — kể cả của uvicorn, sqlalchemy, celery — đi qua `structlog.ProcessorFormatter`
để ra cùng một định dạng, kèm `request_id` nếu đang trong một request.
"""

from __future__ import annotations

import logging
import logging.config
from typing import Any

import structlog

_configured = False


def _drop_color_message(
    _: Any, __: str, event_dict: structlog.typing.EventDict
) -> structlog.typing.EventDict:
    # uvicorn gắn thêm bản có mã màu ANSI của thông điệp — vô ích trong log JSON.
    event_dict.pop("color_message", None)
    return event_dict


def _shared_processors() -> list[structlog.typing.Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.ExtraAdder(),
        _drop_color_message,
    ]


def configure_logging(level: str = "INFO", *, json: bool = True, force: bool = False) -> None:
    """Thiết lập logging toàn cục. Gọi nhiều lần là an toàn (idempotent)."""
    global _configured
    if _configured and not force:
        return

    shared = _shared_processors()
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer(ensure_ascii=False)
        if json
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=[
            *shared,
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter_config: dict[str, Any] = {
        "()": structlog.stdlib.ProcessorFormatter,
        "foreign_pre_chain": shared,
        "processors": [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"structured": formatter_config},
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "structured",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["default"], "level": level.upper()},
            "loggers": {
                # uvicorn tự gắn handler dạng chữ thường; bỏ đi để log đi qua root (JSON).
                "uvicorn": {"handlers": [], "propagate": True, "level": level.upper()},
                "uvicorn.error": {"handlers": [], "propagate": True, "level": level.upper()},
                # Access log của uvicorn được thay bằng log của RequestContextMiddleware.
                "uvicorn.access": {"handlers": [], "propagate": False},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
