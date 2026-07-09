"""Sidebar LIVE MARKET strip must show the unified VG30, never a raw drum key.

Live audit 09-07-2026: sidebar showed VG30 Rs 66,200 (raw DRUM_KANDLA_VG30 —
a stale/wrong manual drum entry) while the top bar, ticker and KPIs all showed
the unified Rs 77,640 on the same screen. Render-layer guard: the sidebar
builds its rows from get_unified_prices() only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import subtab_bar  # noqa: E402


def test_ticker_items_use_unified_vg30():
    unified = {"brent": 78.85, "wti": 74.31, "usdinr": 95.55, "vg30": 77640.0}

    items = subtab_bar._market_ticker_items(unified)

    by_label = {label: value for label, value, _color in items}
    assert by_label["VG30"] == "₹77,640"
    assert by_label["Brent"] == "$78.85"
    assert by_label["USD/INR"] == "95.55"


def test_ticker_skips_missing_values_without_crashing():
    items = subtab_bar._market_ticker_items({"vg30": None, "brent": 0})
    assert items == []


def test_sidebar_never_reads_raw_drum_key():
    # Drift guard: the sidebar module must not bypass the single source of
    # truth by reading live_prices keys directly.
    src = (Path(__file__).parent.parent / "subtab_bar.py").read_text(encoding="utf-8")
    assert "DRUM_KANDLA_VG30" not in src
    assert "DRUM_MUMBAI_VG30" not in src
