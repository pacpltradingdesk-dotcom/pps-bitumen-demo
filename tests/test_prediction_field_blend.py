"""Prediction batch (live audit 09-07-2026, sales-reported):

1. Field entries must influence the next-revision prediction — the desk saw a
   ~Rs 6,000 drop coming from rate cards while the model showed INCREASE +5.5%
   because it only looks at Brent/FX.
2. The waterfall's "=> Next Predicted" showed the already-Published 01-07 row
   (df.iloc[0]) while "Next Revision at a Glance" showed the pending 16-07 row
   — two different numbers for "next" on the same page.
3. The refresh bar said "Data stale · 31610 min" because it watched
   ai_learned_weights.json, a file the prediction page never reads.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime

import manual_entry_engine as mee


def _entry(basic, *, days_old=0, grade="VG30", ptype="bulk"):
    ist = datetime.datetime(2026, 7, 9, 10, 0) - datetime.timedelta(days=days_old)
    return {
        "entry_ist": ist.strftime("%d-%m-%Y %H:%M IST"),
        "location": "Mumbai", "grade": grade, "price_type": ptype,
        "basic_price": basic, "user": "janki",
    }


# ── field signal aggregation ────────────────────────────────────────────────

def test_field_signal_averages_recent_bulk_entries(tmp_path):
    log = tmp_path / "entries.json"
    import json
    json.dump([
        _entry(71_600, days_old=1),
        _entry(71_800, days_old=2),
        _entry(90_000, days_old=30),          # too old — ignored
        _entry(69_000, days_old=1, ptype="drum"),   # drum — ignored
        _entry(75_000, days_old=1, grade="VG10"),   # other grade — ignored
    ], open(log, "w"))

    now = datetime.datetime(2026, 7, 9, 12, 0)
    sig = mee.field_price_signal(grade="VG30", price_type="bulk",
                                 max_age_days=14, path=log, now=now)

    assert sig["count"] == 2
    assert sig["avg_basic"] == 71_700


def test_field_signal_empty_when_no_entries(tmp_path):
    sig = mee.field_price_signal(path=tmp_path / "missing.json")
    assert sig["count"] == 0
    assert sig["avg_basic"] is None


# ── blend math ───────────────────────────────────────────────────────────────

def test_blend_no_signal_returns_model_price():
    from command_intel.price_prediction import blend_field_signal
    blended, weight = blend_field_signal(81_877, None, 0)
    assert blended == 81_877
    assert weight == 0.0


def test_blend_single_entry_gets_15pct_weight():
    from command_intel.price_prediction import blend_field_signal
    blended, weight = blend_field_signal(80_000, 72_000, 1)
    assert weight == 0.15
    assert blended == round(80_000 * 0.85 + 72_000 * 0.15)


def test_blend_weight_caps_at_50pct():
    from command_intel.price_prediction import blend_field_signal
    blended, weight = blend_field_signal(80_000, 72_000, 10)
    assert weight == 0.5
    assert blended == 76_000


def test_blend_output_clamped_to_realistic_band():
    # A fat-fingered field entry (7,187 instead of 71,877) must not drag the
    # customer-facing prediction below the model path's own 25k-90k guard.
    from command_intel.price_prediction import blend_field_signal
    blended, _ = blend_field_signal(80_000, 7_187, 10)     # naive blend = 43,594
    assert blended >= 25_000
    blended_hi, _ = blend_field_signal(80_000, 500_000, 10)
    assert blended_hi <= 90_000


def test_field_signal_rejects_implausible_prices(tmp_path):
    # Outlier entries (outside the 25k-90k bitumen band) are excluded from the
    # average so one typo can't poison the signal for 14 days.
    import json
    log = tmp_path / "entries.json"
    json.dump([
        _entry(71_600, days_old=1),
        _entry(7_187, days_old=1),        # typo — must be ignored
    ], open(log, "w"))
    now = datetime.datetime(2026, 7, 9, 12, 0)
    sig = mee.field_price_signal(path=log, now=now)
    assert sig["count"] == 1
    assert sig["avg_basic"] == 71_600


def test_next_pending_row_returns_none_on_empty():
    import pandas as pd
    from command_intel.price_prediction import next_pending_row
    assert next_pending_row(pd.DataFrame()) is None


# ── waterfall must anchor on the next PENDING revision ──────────────────────

def test_next_pending_row_skips_published():
    import pandas as pd
    from command_intel.price_prediction import next_pending_row
    df = pd.DataFrame([
        {"Revision Date": "01-07-2026", "Predicted (₹/MT)": 82_286, "Status": "Published"},
        {"Revision Date": "16-07-2026", "Predicted (₹/MT)": 81_877, "Status": "Pending"},
    ])
    row = next_pending_row(df)
    assert row["Revision Date"] == "16-07-2026"
    assert row["Predicted (₹/MT)"] == 81_877


def test_next_pending_row_falls_back_to_first():
    import pandas as pd
    from command_intel.price_prediction import next_pending_row
    df = pd.DataFrame([
        {"Revision Date": "01-07-2026", "Predicted (₹/MT)": 82_286, "Status": "Published"},
    ])
    assert next_pending_row(df)["Predicted (₹/MT)"] == 82_286


# ── freshness mapping watches what the page actually reads ──────────────────

def test_prediction_freshness_watches_real_sources():
    import freshness_guard as fg
    watched = [p.name for p in fg.PAGE_CACHES["price_prediction"]]
    assert "ai_learned_weights.json" not in watched, (
        "prediction page never reads learned weights — watching it caused the "
        "bogus 'Data stale · 31610 min' badge"
    )
    assert "tbl_crude_prices.json" in watched  # the ML forecast's actual input
