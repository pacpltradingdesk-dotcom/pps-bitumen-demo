"""
Regression tests: the AI data layer must feed LIVE prices/FX to the model,
not frozen Feb-2026 literals (VG30=48302, USD/INR=86.87, revision 01-03-2026).
Single source of truth = market_data.get_unified_prices() / price_master.
"""

import ai_data_layer as adl
from market_data import get_unified_prices


def test_prediction_context_uses_live_vg30_not_48302():
    ctx = adl.get_prediction_context()
    live_vg30 = int(float(get_unified_prices().get("vg30") or 0))
    assert ctx.get("current_base_VG30_per_MT") == live_vg30
    assert ctx.get("current_base_VG30_per_MT") != 48302


def test_prediction_context_revision_date_not_frozen_feb():
    ctx = adl.get_prediction_context()
    assert "01-03-2026" not in str(ctx.get("next_revision_date", ""))


def test_price_snapshot_fx_tracks_live():
    snap = adl.get_price_snapshot()
    live_fx = float(get_unified_prices().get("usdinr") or 0)
    assert abs(float(snap["USD_INR_rate"]) - live_fx) < 0.05


def test_next_revision_date_is_1st_or_16th_future():
    import datetime
    d = adl._next_revision_date()
    assert d.day in (1, 16)
    assert d >= datetime.date.today()
