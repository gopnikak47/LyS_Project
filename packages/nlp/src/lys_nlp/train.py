"""Fine-tune PhoBERT từ CSV riêng train/validation; hiệu chỉnh trên validation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from lys_nlp.pipeline import LABELS
from lys_nlp.preprocess import normalize, words


def main() -> None:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base", default="vinai/phobert-base-v2")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    torch.manual_seed(42)

    def read(path: str) -> list[dict[str, str]]:
        with Path(path).open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        if not rows or any(
            row.get("label") not in LABELS or not row.get("text", "").strip() for row in rows
        ):
            raise ValueError("CSV cần text,label hợp lệ và không rỗng.")
        return rows

    train, validation = read(args.train), read(args.validation)
    if {normalize(row["text"]) for row in train} & {normalize(row["text"]) for row in validation}:
        raise ValueError("Train và validation chứa nội dung trùng, gây rò dữ liệu.")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base,
        num_labels=3,
        id2label=dict(enumerate(LABELS)),
        label2id={label: index for index, label in enumerate(LABELS)},
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)

    def encode(rows: list[dict[str, str]]) -> Any:
        return tokenizer(
            [" ".join(words(normalize(row["text"]))) for row in rows],
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        ).to(device)

    for _ in range(args.epochs):
        model.train()
        for start in range(0, len(train), args.batch_size):
            batch = train[start : start + args.batch_size]
            labels = torch.tensor([LABELS.index(row["label"]) for row in batch], device=device)
            optimizer.zero_grad()
            model(**encode(batch), labels=labels).loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
    model.eval()
    logits = []
    with torch.no_grad():
        for start in range(0, len(validation), args.batch_size):
            logits.append(model(**encode(validation[start : start + args.batch_size])).logits)
    fixed_logits = torch.cat(logits).detach()
    targets = torch.tensor([LABELS.index(row["label"]) for row in validation], device=device)
    log_temperature = torch.zeros(1, device=device, requires_grad=True)
    calibrator = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=50)

    def closure() -> Any:
        calibrator.zero_grad()
        loss = torch.nn.functional.cross_entropy(fixed_logits / log_temperature.exp(), targets)
        loss.backward()
        return loss

    calibrator.step(closure)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    (output / "metadata.json").write_text(
        json.dumps(
            {
                "version": args.version,
                "labels": list(LABELS),
                "temperature": float(log_temperature.exp().item()),
                "train_samples": len(train),
                "validation_samples": len(validation),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
