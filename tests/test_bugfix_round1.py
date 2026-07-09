"""Round-1 bug-fix guards (09-07-2026 full bug sweep).

Covers the pure-logic fixes from the multi-agent bug review:
  #1 news signal was directionally dead in the master composite
  #5 load_articles handed out the shared DEMO_ARTICLES dicts (mutation leak)
  #7 compute_basic_price divided by zero at gst_pct == -100
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest  # noqa: E402


# ── #1 news signal direction ─────────────────────────────────────────────────

def test_news_direction_high_supply_risk_is_up():
    import market_intelligence_engine as mie
    # HIGH supply risk (refinery/geopolitics/ports) dominates -> upward pressure
    assert mie._news_direction("NEUTRAL", "HIGH") == "UP"
    assert mie._news_direction("NEGATIVE", "HIGH") == "UP"


def test_news_direction_sentiment_when_risk_not_high():
    import market_intelligence_engine as mie
    assert mie._news_direction("POSITIVE", "LOW") == "UP"
    assert mie._news_direction("NEGATIVE", "LOW") == "DOWN"
    assert mie._news_direction("NEUTRAL", "LOW") == "STABLE"


def test_news_direction_feeds_direction_score():
    import market_intelligence_engine as mie
    # A news-shaped signal now yields a non-zero composite direction (was always 0.0)
    up = {"direction": mie._news_direction("POSITIVE", "LOW")}
    down = {"direction": mie._news_direction("NEGATIVE", "LOW")}
    assert mie._direction_of(up) == 1.0
    assert mie._direction_of(down) == -1.0


# ── #7 compute_basic_price divide-by-zero guard ──────────────────────────────

def test_compute_basic_price_rejects_gst_at_minus_100():
    from manual_entry_engine import compute_basic_price
    with pytest.raises(ValueError):
        compute_basic_price(1000.0, 0.0, -100.0, gst_inclusive=True)


def test_compute_basic_price_normal_inclusive_math():
    from manual_entry_engine import compute_basic_price
    # 1180 incl 18% GST -> 1000 ex-GST, minus 0 freight
    assert compute_basic_price(1180.0, 0.0, 18.0, gst_inclusive=True) == 1000


def test_compute_basic_price_exclusive_passthrough_minus_freight():
    from manual_entry_engine import compute_basic_price
    assert compute_basic_price(1000.0, 200.0, 18.0, gst_inclusive=False) == 800


# ── #5 load_articles copy independence ───────────────────────────────────────

def test_load_articles_returns_independent_demo_copies(monkeypatch):
    import news_engine as ne
    monkeypatch.setattr(ne, "_load_json", lambda *a, **k: [])  # force demo branch
    before = dict(ne.DEMO_ARTICLES[0])
    got = ne.load_articles()
    assert got and got[0] is not ne.DEMO_ARTICLES[0]  # not the same object
    got[0]["status"] = "read-by-one-user"
    # Mutating the returned copy must NOT bleed into the module constant
    assert ne.DEMO_ARTICLES[0] == before
