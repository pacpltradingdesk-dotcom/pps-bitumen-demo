"""Tests for the pure JSON-extraction helper in circular_extract.
(The network/vision call itself is not unit-tested — it needs a live API key;
all logic it depends on is the parser, which is tested separately.)
"""
from __future__ import annotations

import circular_extract as ce


def test_parse_rows_json_plain_array():
    txt = '[{"location":"Mathura","grade":"60/70-VG30","price":76382}]'
    rows = ce.parse_rows_json(txt)
    assert rows == [{"location": "Mathura", "grade": "60/70-VG30", "price": 76382}]


def test_parse_rows_json_markdown_fenced():
    txt = "```json\n[{\"location\":\"Koyali\",\"grade\":\"VG30\",\"price\":78260}]\n```"
    rows = ce.parse_rows_json(txt)
    assert len(rows) == 1 and rows[0]["price"] == 78260


def test_parse_rows_json_with_prose_around():
    txt = 'Here is the table:\n[{"location":"Mumbai","grade":"VG30","price":76870}]\nHope that helps!'
    rows = ce.parse_rows_json(txt)
    assert rows[0]["location"] == "Mumbai"


def test_parse_rows_json_drops_non_dicts():
    txt = '[{"location":"X","grade":"VG30","price":70000}, "junk", 5]'
    rows = ce.parse_rows_json(txt)
    assert rows == [{"location": "X", "grade": "VG30", "price": 70000}]


def test_parse_rows_json_garbage_returns_empty():
    assert ce.parse_rows_json("no json here") == []
    assert ce.parse_rows_json("") == []
    assert ce.parse_rows_json("{not a list}") == []
