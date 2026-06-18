"""Single-source-of-truth guard.

Asserts that the canonical bitumen prices in price_master are exactly what the
calculation engine, the feasibility engine, and the price_board ticker all show.
If anyone ever hardcodes a divergent price, this test fails — drift becomes
impossible, not just discouraged.
"""
from __future__ import annotations

import price_master
import calculation_engine
import feasibility_engine
import price_board


SAMPLE_LOCATIONS = ["IOCL Koyali", "MRPL Mangalore", "CPCL Chennai", "Kandla Port Import"]


def test_calculation_engine_uses_canonical_prices():
    canon = price_master.default_prices()
    for loc in SAMPLE_LOCATIONS:
        assert calculation_engine._DEFAULT_LIVE_PRICES[loc] == canon[loc]


def test_feasibility_engine_uses_canonical_prices():
    canon = price_master.default_prices()
    feas = feasibility_engine.get_live_prices()
    for loc in SAMPLE_LOCATIONS:
        assert feas[loc] == canon[loc]


def test_price_board_ticker_matches_canonical_at_base():
    canon = price_master.default_prices()
    board = price_board.build_price_board(price_master.VG30_BASE)
    ref = {n: p for n, g, p in board["refinery"]}
    # At base == VG30_BASE the scale factor is 1.0, so the ticker shows the
    # exact canonical price.
    assert ref["IOCL Koyali"] == canon["IOCL Koyali"]
    assert ref["MRPL Mangalore"] == canon["MRPL Mangalore"]


def test_market_data_base_is_canonical():
    # The headline VG30 default must be the canonical base, not a stray constant.
    assert price_master.VG30_BASE == 76870
