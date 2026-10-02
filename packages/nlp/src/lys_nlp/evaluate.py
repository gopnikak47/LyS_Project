"""Đánh giá thật CSV text,label; không suy diễn số liệu khi không có nhãn."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from lys_nlp.pipeline import LABELS, Pipeline


def metrics(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    if not expected or len(expected) != len(predicted):
        raise ValueError("Cần tập nhãn không rỗng và số dự đoán tương ứng.")
    if any(label not in LABELS for label in [*expected, *predicted]):
        raise ValueError("Nhãn phải là negative/neutral/positive.")
    matrix = [
        [
            sum(a == row and b == col for a, b in zip(expected, predicted, strict=True))
            for col in LABELS
        ]
        for row in LABELS
    ]
    per_class = {}
    for index, label in enumerate(LABELS):
        tp = matrix[index][index]
        precision = tp / max(1, sum(row[index] for row in matrix))
        recall = tp / max(1, sum(matrix[index]))
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "support": sum(matrix[index]),
        }
    return {
        "samples": len(expected),
        "accuracy": sum(a == b for a, b in zip(expected, predicted, strict=True)) / len(expected),
        "macro_f1": sum(item["f1"] for item in per_class.values()) / 3,
        "per_class": per_class,
        "labels": list(LABELS),
        "confusion_matrix": matrix,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--backend", choices=["rules", "phobert"], default="phobert")
    parser.add_argument("--model", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with Path(args.data).open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    pipeline = Pipeline(args.backend, args.model)
    predicted = [pipeline.analyze(row["text"], topics=[]).sentiment for row in rows]
    report = {
        **metrics([row["label"] for row in rows], predicted),
        "model_version": pipeline.version,
        "dataset": str(args.data),
        "scope": "Kết quả chỉ áp dụng cho tập nhãn đầu vào; dữ liệu seed là minh họa.",
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
