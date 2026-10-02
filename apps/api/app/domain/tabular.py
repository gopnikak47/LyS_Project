"""Đọc dữ liệu CSV/XLSX có giới hạn, bảo vệ archive bomb và công thức xuất."""
from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from app.core.errors import AppError

MAX_ROWS = 100000


def rows(path: Path) -> Iterator[dict[str, str]]:
    if path.suffix == ".xlsx":
        import openpyxl
        with zipfile.ZipFile(path) as archive:
            if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
                raise AppError("Tệp Excel giải nén vượt giới hạn 100MB.")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            values = workbook.active.iter_rows(values_only=True)
            header = [str(v).strip() if v is not None else "" for v in next(values, ())]
            validate_header(header)
            for index, row in enumerate(values):
                if index >= MAX_ROWS:
                    raise AppError("Tệp vượt giới hạn 100.000 dòng.")
                yield {key: str(value) if value is not None else "" for key, value in zip(header, row, strict=False)}
        finally:
            workbook.close()
    else:
        with path.open(encoding="utf-8-sig", newline="") as source:
            sample = source.read(4096); source.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(source, dialect=dialect)
            validate_header(reader.fieldnames or [])
            for index, row in enumerate(reader):
                if index >= MAX_ROWS:
                    raise AppError("Tệp vượt giới hạn 100.000 dòng.")
                if None in row:
                    raise AppError("Dòng CSV có nhiều cột hơn tiêu đề.")
                yield {key: value or "" for key, value in row.items()}


def validate_header(header: list[str]) -> None:
    if not header or len(header) > 100 or any(not value or len(value) > 200 for value in header) or len(set(header)) != len(header):
        raise AppError("Tiêu đề cột rỗng, trùng hoặc vượt giới hạn 100 cột.")


def safe_cell(value: Any) -> Any:
    # Chặn CSV/Excel formula injection khi xuất nhận xét người dùng.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def csv_bytes(header: list[str], values: list[list[Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output); writer.writerow(header)
    writer.writerows([[safe_cell(cell) for cell in row] for row in values])
    return output.getvalue().encode("utf-8-sig")
