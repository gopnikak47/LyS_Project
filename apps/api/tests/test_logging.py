from __future__ import annotations

import json
import logging

import pytest
import structlog

from app.core.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    structlog.reset_defaults()


def _json_lines(output: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in output.splitlines() if line.startswith("{")]


def test_structlog_and_stdlib_logs_are_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json=True, force=True)
    structlog.contextvars.bind_contextvars(request_id="req-test-0001")
    try:
        get_logger("app.test").info("khao_sat_da_tao", survey_id=42)
        logging.getLogger("uvicorn.error").info(
            "Shutting down", extra={"color_message": "\x1b[1mShutting down\x1b[0m"}
        )
    finally:
        structlog.contextvars.clear_contextvars()

    lines = _json_lines(capsys.readouterr().out)
    events = {line["event"]: line for line in lines}
    assert events["khao_sat_da_tao"]["survey_id"] == 42
    assert events["khao_sat_da_tao"]["request_id"] == "req-test-0001"
    # Log của thư viện (uvicorn) cũng phải ra JSON, cùng request-id.
    assert events["Shutting down"]["logger"] == "uvicorn.error"
    assert events["Shutting down"]["request_id"] == "req-test-0001"
    assert "color_message" not in events["Shutting down"]


def test_vietnamese_text_is_not_escaped(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json=True, force=True)
    get_logger("app.test").info("phan_hoi", noi_dung="Món ăn ngon")
    assert "Món ăn ngon" in capsys.readouterr().out
