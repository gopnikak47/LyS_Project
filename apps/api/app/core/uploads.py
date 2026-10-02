"""Quét ClamAV INSTREAM; không chấp nhận tệp khi scanner chưa cấu hình."""

from __future__ import annotations

import socket
import struct

from app.core.errors import AppError


def scan_file(content: bytes, host: str, port: int) -> None:
    if not host:
        raise AppError("Chức năng tải tệp chưa có dịch vụ quét virus.", status_code=503)
    try:
        with socket.create_connection((host, port), timeout=20) as connection:
            connection.sendall(b"zINSTREAM\0")
            for start in range(0, len(content), 65536):
                chunk = content[start : start + 65536]
                connection.sendall(struct.pack("!I", len(chunk)) + chunk)
            connection.sendall(struct.pack("!I", 0))
            result = b""
            while b"\0" not in result and len(result) < 4096:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                result += chunk
        if not result.rstrip(b"\0\n").endswith(b": OK"):
            raise AppError("Tệp không vượt qua kiểm tra an toàn.", code="UNSAFE_FILE")
    except OSError as exc:
        raise AppError("Dịch vụ quét tệp tạm thời không khả dụng.", status_code=503) from exc
