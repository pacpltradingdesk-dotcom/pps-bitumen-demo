"""RBI/Frankfurter monthly-average FX rows must UPSERT, not append.

Root cause of the fx-history pollution (live audit 09-07-2026):
connect_rbi_fx_historical() re-appended all ~13 monthly-average rows on every
run with a fresh date_time stamp. _append_tbl's same-minute dedup never
matched, so tbl_fx_rates.json filled with hundreds of stale-month duplicates
(42 copies of 2025-06 locally) and the max_records trim evicted real live-spot
rows. One month must map to exactly one row, refreshed in place.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from govt_connectors import upsert_period_records  # noqa: E402


def _monthly(period: str, rate: float, ts: str = "2026-07-09 10:00:00 IST") -> dict:
    return {
        "date_time": ts,
        "period_label": period,
        "pair": "USD/INR",
        "rate": rate,
        "source": "RBI Reference Rate (ECB/Frankfurter proxy) — monthly avg",
    }


def _spot(rate: float, ts: str) -> dict:
    return {"date_time": ts, "rate": rate, "source": "yfinance INR=X (live spot)"}


def test_upsert_replaces_existing_month_row():
    existing = [
        _monthly("2026-05", 87.1, ts="2026-06-01 06:00:00 IST"),
        _monthly("2026-06", 90.2, ts="2026-07-01 06:00:00 IST"),
    ]
    fresh = [_monthly("2026-06", 91.0), _monthly("2026-07", 95.4)]

    out = upsert_period_records(existing, fresh)

    monthly = {r["period_label"]: r for r in out if r.get("period_label")}
    assert set(monthly) == {"2026-05", "2026-06", "2026-07"}
    assert monthly["2026-06"]["rate"] == 91.0  # refreshed in place, not duplicated
    assert sum(1 for r in out if r.get("period_label") == "2026-06") == 1


def test_upsert_preserves_live_spot_rows():
    existing = [
        _spot(94.53, "2026-06-29 17:53:22 IST"),
        _monthly("2026-06", 90.2),
        _spot(95.55, "2026-07-09 09:45:00 IST"),
    ]
    fresh = [_monthly("2026-06", 91.0)]

    out = upsert_period_records(existing, fresh)

    spots = [r for r in out if not r.get("period_label")]
    assert [r["rate"] for r in spots] == [94.53, 95.55]


def test_upsert_is_idempotent():
    existing = [_spot(95.55, "2026-07-09 09:45:00 IST")]
    fresh = [_monthly("2026-06", 91.0), _monthly("2026-07", 95.4)]

    once = upsert_period_records(existing, fresh)
    twice = upsert_period_records(once, fresh)

    assert len(once) == 3
    assert len(twice) == 3


def test_upsert_does_not_mutate_inputs():
    existing = [_monthly("2026-06", 90.2)]
    snapshot = [dict(r) for r in existing]

    upsert_period_records(existing, [_monthly("2026-06", 91.0)])

    assert existing == snapshot
