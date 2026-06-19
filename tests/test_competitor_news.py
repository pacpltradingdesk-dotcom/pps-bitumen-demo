"""
Regression tests for the Competitor-Intel "Latest MEE Industry News" block,
which used to show frozen Feb-2026 sample headlines.

Two guarantees:
  1. Fresh bitumen news is sorted newest-first by *parsed* datetime, robust
     to mixed ISO / DD-MM-YYYY date formats (not raw-string sort).
  2. When no fresh news is available the picker returns an empty list — it
     must NOT fall back to stale, hard-dated sample content.
"""

import competitor_intelligence as ci


def test_pick_fresh_bitumen_sorts_newest_first_mixed_formats():
    rows = [
        {"headline": "OLD crude note", "date_time": "28-02-2026 14:00 IST"},
        {"headline": "FRESH bitumen road project today", "date_time": "2026-06-18 15:00 IST"},
        {"headline": "MID brent refinery update", "date_time": "2026-06-10 09:00 IST"},
    ]
    out = ci._pick_fresh_bitumen(rows, 4)
    assert out, "expected picked items"
    assert out[0]["headline"].startswith("FRESH"), (
        f"newest should be first, got {out[0]['headline']!r}"
    )
    assert out[-1]["headline"].startswith("OLD")


def test_pick_fresh_bitumen_empty_when_no_rows():
    """No data must yield an empty list — never stale sample content."""
    assert ci._pick_fresh_bitumen([], 4) == []
