from __future__ import annotations

import json
from pathlib import Path

from lys_nlp import SENTIMENT_LABELS, Sentiment

SHARED_CONSTANTS = Path(__file__).parents[2] / "shared" / "src" / "sentiments.json"


def test_three_sentiment_classes() -> None:
    assert [s.value for s in SENTIMENT_LABELS] == ["positive", "negative", "neutral"]


def test_labels_match_frontend_shared_constants() -> None:
    # Đảm bảo nhãn phía Python và phía giao diện không lệch nhau.
    shared = json.loads(SHARED_CONSTANTS.read_text(encoding="utf-8"))
    assert [item["value"] for item in shared] == [s.value for s in Sentiment]
