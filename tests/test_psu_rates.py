"""Live PSU Bitumen Rates must come from the unified price board.

User report 09-07-2026: the Competitor Intel section always showed "PSU rate
auto-fetch not available. Using static data from MEE bulletins." Root cause:
BOTH fetch paths imported feasibility_engine.get_psu_prices — a function that
has never existed — and swallowed the ImportError silently; the secondary
fallback stored a {"snapshot": ...} dict the UI read as records. The system
already has live PSU refinery rates (price_board — the same numbers as the
Command Center REFINERY ticker), so the section now reads those.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import competitor_intelligence as ci  # noqa: E402


def test_board_rows_map_to_psu_records():
    board = {"refinery": [("IOCL Koyali", "VG30", 79_152),
                          ("BPCL Mumbai", "VG30", 77_640)]}
    recs = ci._psu_records_from_board(board, circular_date="19-06-2026")

    assert recs == [
        {"refinery": "IOCL Koyali", "grade": "VG30", "price_inr_mt": 79_152,
         "effective_date": "19-06-2026", "source": "Unified price board (live)"},
        {"refinery": "BPCL Mumbai", "grade": "VG30", "price_inr_mt": 77_640,
         "effective_date": "19-06-2026", "source": "Unified price board (live)"},
    ]


def test_fetch_live_psu_rates_returns_real_rates():
    # Integration: the board always derives from the unified VG30 base, so
    # this must never be empty again (the "auto-fetch not available" state).
    recs = ci._fetch_live_psu_rates()
    assert len(recs) >= 6
    assert all(r.get("price_inr_mt") for r in recs)
    names = {r["refinery"] for r in recs}
    assert "IOCL Koyali" in names


def test_phantom_get_psu_prices_import_is_gone():
    for fname in ("competitor_intelligence.py", "api_hub_engine.py"):
        src = (Path(__file__).parent.parent / fname).read_text(encoding="utf-8")
        assert "import get_psu_prices" not in src, f"phantom import still in {fname}"
