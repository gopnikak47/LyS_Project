"""StorageBackend; khóa tương đối kiểm tra traversal, ghi thay thế nguyên tử."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def path(self, key: str) -> Path: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root) or candidate == self.root:
            raise ValueError("Khóa lưu trữ không hợp lệ.")
        return candidate

    def put(self, key: str, content: bytes) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def read(self, key: str) -> bytes:
        return self.path(key).read_bytes()
