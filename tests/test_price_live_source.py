"""Regression guards for the price-source bugs fixed 2026-06-29:
  1. USD/INR must come from the LIVE spot row, never the stale monthly-average
     proxy (which was stamped with a fresh timestamp and used to win).
  2. VG30 must equal the published/set base — the intra-fortnight auto-drift is
     disabled, so a VG30_ANCHOR must NOT move the displayed price.
If either regresses, these tests fail in CI before it can reach the board.
"""
import datetime
import json


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _setup(tmp_path, monkeypatch, fx_rows, live_prices=None):
    import market_data as m
    (tmp_path / "tbl_fx_rates.json").write_text(json.dumps(fx_rows), encoding="utf-8")
    if live_prices is not None:
        (tmp_path / "live_prices.json").write_text(json.dumps(live_prices), encoding="utf-8")
    # Point the module at the temp dir; keep it offline + deterministic.
    monkeypatch.setattr(m, "_HUB_CACHE_PATH", tmp_path / "hub_cache.json", raising=False)
    monkeypatch.setattr(m, "_LIVE_PRICES_PATH", tmp_path / "live_prices.json", raising=False)
    monkeypatch.setattr(m, "fetch_api_data", lambda *a, **k: None, raising=False)
    return m


def test_unified_usdinr_picks_live_spot_not_monthly(tmp_path, monkeypatch):
    ts = _now()
    # The real-world bug shape: a stale monthly row appended AFTER the live spot,
    # both with a FRESH timestamp. Without the period_label skip, reversed() would
    # hit the monthly row first and surface 85.60 instead of the live 94.30.
    fx = [
        {"date_time": ts, "pair": "USD/INR", "rate": 94.30,
         "source": "yfinance INR=X (live spot)"},
        {"date_time": ts, "pair": "USD/INR", "rate": 85.60,
         "source": "RBI Reference Rate (ECB/Frankfurter proxy) — monthly avg",
         "period_label": "2025-06"},
    ]
    m = _setup(tmp_path, monkeypatch, fx)
    u = m.get_unified_prices()
    assert u["usdinr"] == 94.30, f"must use live spot, not monthly avg; got {u['usdinr']}"


def test_unified_vg30_ignores_anchor_no_drift(tmp_path, monkeypatch):
    ts = _now()
    fx = [{"date_time": ts, "pair": "USD/INR", "rate": 94.30,
           "source": "yfinance INR=X (live spot)"}]
    # An anchor that, under the old drift logic, would have pulled VG30 down ~₹1,845.
    live = {"VG30_BASE": 77000,
            "VG30_ANCHOR": {"base": 77000, "brent": 77.37, "usdinr": 85.99}}
    m = _setup(tmp_path, monkeypatch, fx, live)
    u = m.get_unified_prices()
    assert u["vg30"] == 77000.0, f"VG30 must equal the set base (no drift); got {u['vg30']}"
