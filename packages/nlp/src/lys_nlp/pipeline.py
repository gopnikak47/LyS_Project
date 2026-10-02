"""Inference PhoBERT có temperature scaling; rules chỉ là baseline demo công khai."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lys_nlp.preprocess import keywords, normalize, sentences

LABELS = ("negative", "neutral", "positive")
URGENT_PHRASES = (
    "ngộ độc",
    "đau bụng",
    "tiêu chảy",
    "dị vật",
    "côn trùng",
    "kiện",
    "công an",
    "lừa đảo",
    "báo đài",
    "đe dọa",
    "tử vong",
)
POSITIVE = ("tốt", "ngon", "hài lòng", "thân thiện", "nhanh", "sạch", "yêu thích", "tuyệt", "ổn")
NEGATIVE = (
    "tệ",
    "dở",
    "chậm",
    "bẩn",
    "thất vọng",
    "không hài lòng",
    "lỗi",
    "đắt",
    "tức giận",
    "kém",
)


@dataclass
class Prediction:
    normalized_text: str
    sentiment: str
    sentiment_score: float
    sentiment_detail: dict[str, Any]
    topic_ids: list[str]
    topic_scores: dict[str, float]
    is_urgent: bool
    urgent_reasons: list[str]
    keywords: list[str]
    model_version: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class Pipeline:
    def __init__(
        self, backend: str = "phobert", model_path: str = "", topic_model: str = ""
    ) -> None:
        self.backend = backend
        self.version = "rules-demo-v1"
        self.temperature = 1.0
        self.tokenizer: Any = None
        self.model: Any = None
        self.embedding: Any = None
        if backend == "phobert":
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            artifact = Path(model_path)
            if not model_path or not (artifact / "metadata.json").is_file():
                raise RuntimeError("Chưa có artifact PhoBERT đã huấn luyện.")
            metadata = json.loads((artifact / "metadata.json").read_text(encoding="utf-8"))
            if metadata.get("labels") != list(LABELS):
                raise RuntimeError("Artifact có thứ tự nhãn không tương thích.")
            self.temperature = float(metadata.get("temperature", 1.0))
            if not math.isfinite(self.temperature) or self.temperature <= 0:
                raise RuntimeError("Temperature không hợp lệ.")
            self.version = str(metadata["version"])
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_path, local_files_only=True
            )
            self.model.eval()
        elif backend != "rules":
            raise ValueError("NLP_BACKEND không hợp lệ.")
        if topic_model:
            from sentence_transformers import SentenceTransformer

            self.embedding = SentenceTransformer(topic_model)

    def sentiment(self, lines: list[str]) -> list[dict[str, float]]:
        if not lines:
            return [{"negative": 0.0, "neutral": 1.0, "positive": 0.0}]
        if self.backend == "rules":
            results = []
            for line in lines:
                pos = sum(phrase in line and f"không {phrase}" not in line for phrase in POSITIVE)
                neg = sum(phrase in line for phrase in NEGATIVE) + sum(
                    f"không {phrase}" in line for phrase in POSITIVE
                )
                label = "positive" if pos > neg else "negative" if neg > pos else "neutral"
                results.append({name: 0.6 if name == label else 0.2 for name in LABELS})
            return results
        import torch

        from lys_nlp.preprocess import words

        encoded = self.tokenizer(
            [" ".join(words(line)) for line in lines],
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        with torch.inference_mode():
            values = torch.softmax(self.model(**encoded).logits / self.temperature, dim=-1).tolist()
        return [dict(zip(LABELS, row, strict=True)) for row in values]

    def analyze(
        self,
        text: str,
        *,
        topics: list[dict[str, Any]],
        threshold: float = 0.35,
        dictionary: dict[str, str] | None = None,
        urgent_phrases: list[str] | None = None,
    ) -> Prediction:
        normalized = normalize(text, dictionary)
        lines = sentences(normalized)
        probabilities = self.sentiment(lines)
        aggregate = {
            name: sum(row[name] for row in probabilities) / len(probabilities) for name in LABELS
        }
        label = max(aggregate, key=lambda key: aggregate[key])
        topic_scores: dict[str, float] = {}
        if self.embedding is not None and topics:
            vectors = self.embedding.encode(
                [
                    normalized,
                    *[
                        f"{t['name']}. {t.get('description', '')}. "
                        f"{' '.join(t.get('keywords', []))}"
                        for t in topics
                    ],
                ],
                normalize_embeddings=True,
            )
            topic_scores = {
                str(topic["id"]): float(vectors[0] @ vector)
                for topic, vector in zip(topics, vectors[1:], strict=True)
            }
        else:
            for topic in topics:
                signals = [normalize(k) for k in topic.get("keywords", []) if k.strip()]
                matches = sum(signal in normalized for signal in signals)
                topic_scores[str(topic["id"])] = min(1.0, matches * 0.5)
        reasons = [
            phrase
            for phrase in (urgent_phrases if urgent_phrases is not None else URGENT_PHRASES)
            if normalize(phrase) in normalized
        ]
        if aggregate["negative"] >= 0.9:
            reasons.append("Điểm tiêu cực rất cao")
        return Prediction(
            normalized,
            label,
            aggregate[label],
            {
                "probs": aggregate,
                "sentences": [
                    {"text": line, "probs": probs}
                    for line, probs in zip(lines, probabilities, strict=False)
                ],
                "calibrated": self.backend == "phobert",
                "topic_backend": "embedding" if self.embedding else "keywords-demo",
            },
            [key for key, score in topic_scores.items() if score >= threshold],
            topic_scores,
            bool(reasons),
            reasons,
            keywords(normalized),
            self.version,
        )
