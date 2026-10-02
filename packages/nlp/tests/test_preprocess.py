from __future__ import annotations

import unicodedata

import pytest

from lys_nlp.preprocess import EMOJI, TEENCODE, keywords, normalize, sentences


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        *TEENCODE.items(),
        *[(key, value.strip()) for key, value in EMOJI.items()],
        ("NV ko dc", "nhân viên không được"),
        ("SP GOOD", "sản phẩm tốt"),
        ("tks nv", "cảm ơn nhân viên"),
        ("hok vs sp", "không với sản phẩm"),
        ("  món   ăn  ngon  ", "món ăn ngon"),
        ("<b>Rất tốt</b>", "rất tốt"),
        ("ngon https://example.com/x?q=1", "ngon"),
        ("www.example.com tệ", "tệ"),
        ("NGOOOON", "ngon"),
        ("ĐẸPPPP", "đẹp"),
        ("!!!", "!!!"),
        ("", ""),
        ("&#78;V", "nhân viên"),
        ("a &amp; b", "a b"),
        ("x\ny\tz", "x y z"),
        ("không tốt", "không tốt"),
        ("không tệ", "không tệ"),
        ("0 10 100", "0 10 100"),
        ("😊👍", "hài lòng tốt"),
        ("😡👎", "tức giận tệ"),
        ("món ăn! phục vụ?", "món ăn! phục vụ?"),
        ("<script>x</script>", "x"),
        ("a_b", "a_b"),
        ("a@b", "a b"),
        ("koooo", "không"),
    ],
)
def test_normalization_golden(source: str, expected: str) -> None:
    assert normalize(source) == expected
    assert normalize(normalize(source)) == expected


def test_unicode_and_workspace_dictionary() -> None:
    assert normalize(unicodedata.normalize("NFD", "Đánh giá tốt")) == "đánh giá tốt"
    assert normalize("nv", {"nv": "nhân sự"}) == "nhân sự"
    assert sentences("ngon! chậm? sạch.") == ["ngon", "chậm", "sạch"]
    assert "không" in keywords("tôi không hài lòng và không quay lại")
