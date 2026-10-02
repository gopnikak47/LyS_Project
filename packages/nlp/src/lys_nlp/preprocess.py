"""Chuẩn hóa tiếng Việt, giữ tín hiệu emoji; từ điển có thể ghi đè theo workspace."""
from __future__ import annotations

import html
import re
import unicodedata

TEENCODE = {"ko": "không", "kh": "không", "k": "không", "hok": "không", "dc": "được", "đc": "được", "vs": "với", "nv": "nhân viên", "sp": "sản phẩm", "tks": "cảm ơn", "thx": "cảm ơn", "ok": "ổn", "oke": "ổn", "good": "tốt", "bad": "tệ", "bt": "bình thường", "bth": "bình thường"}
EMOJI = {"😍": " yêu thích ", "❤️": " yêu thích ", "👍": " tốt ", "😊": " hài lòng ", "😄": " hài lòng ", "😡": " tức giận ", "👎": " tệ ", "😭": " thất vọng ", "😞": " thất vọng "}
STOPWORDS = frozenset("và là của có cho với những các thì một tôi mình bạn này đó được đã cũng rất quá nhưng ở về trong khi đến từ sẽ mà nhé nha".split())


def normalize(text: str, dictionary: dict[str, str] | None = None) -> str:
    text = unicodedata.normalize("NFC", html.unescape(text)).lower()
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    for emoji, token in EMOJI.items():
        text = text.replace(emoji, token)
    # Tiếng Việt không có phụ âm/âm tiết cần lặp >=3 lần liên tiếp.
    text = re.sub(r"([^\W\d_])\1{2,}", r"\1", text)
    text = re.sub(r"[^\w\s.,!?;:à-ỹ]", " ", text)
    aliases = {**TEENCODE, **(dictionary or {})}
    text = re.sub(r"\b\w+\b", lambda m: aliases.get(m.group(), m.group()), text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.!?;]+", text) if part.strip()]


def words(text: str) -> list[str]:
    try:
        from underthesea import word_tokenize
    except ImportError:
        return re.findall(r"\b[^\W\d_]+\b", text)
    return str(word_tokenize(text, format="text")).split()


def keywords(text: str) -> list[str]:
    return list(dict.fromkeys(word for word in words(text) if len(word) > 1 and len(word) <= 64 and word not in STOPWORDS))[:100]
