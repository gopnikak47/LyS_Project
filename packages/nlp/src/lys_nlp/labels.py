"""Nhãn dùng chung giữa NLP, API và giao diện (khớp `packages/shared/src/constants.ts`)."""

from __future__ import annotations

from enum import StrEnum


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


SENTIMENT_LABELS: tuple[Sentiment, ...] = tuple(Sentiment)
