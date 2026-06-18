"""Tests for price_board — the derive-from-base + manual-override price engine.

These test the MECHANISM (scaling, override-wins, sanity-guard) with explicit
controlled inputs, so they are independent of the seed reference rate table
(which is business data confirmed separately).
"""
from __future__ import annotations

import price_board as pb


# ── scale_price: derive a location price proportionally from the live base ──

def test_scale_price_equal_base_returns_reference():
    # At the reference base, the reference price is unchanged.
    assert pb.scale_price(42000, base_vg30=50500, ref_base=50500) == 42000


def test_scale_price_scales_up_with_base():
    # Base +10% -> every derived price +10% (stays consistent with the headline).
    assert pb.scale_price(42000, base_vg30=55550, ref_base=50500) == 46200


def test_scale_price_scales_down_with_base():
    assert pb.scale_price(42000, base_vg30=45450, ref_base=50500) == 37800


def test_scale_price_missing_base_falls_back_to_reference():
    # No / zero base must never blow up or zero the board — show the reference.
    assert pb.scale_price(42000, base_vg30=0, ref_base=50500) == 42000
    assert pb.scale_price(42000, base_vg30=None, ref_base=50500) == 42000


# ── resolve_price: manual override wins, but only if sane ──

def test_resolve_price_uses_derived_when_no_override():
    assert pb.resolve_price(36500, base_vg30=50500, override=None, ref_base=50500) == 36500


def test_resolve_price_uses_override_when_within_band():
    # A real entered price near the derived value wins verbatim.
    assert pb.resolve_price(36500, base_vg30=50500, override=37000, ref_base=50500) == 37000


def test_resolve_price_rejects_absurd_override():
    # The live bug: Drum Kandla VG10 fat-fingered to 67350 (+84% over derived).
    # Sanity guard must ignore it and show the derived value instead.
    assert pb.resolve_price(36500, base_vg30=50500, override=67350, ref_base=50500) == 36500


def test_resolve_price_rejects_zero_and_negative_override():
    assert pb.resolve_price(36500, base_vg30=50500, override=0, ref_base=50500) == 36500
    assert pb.resolve_price(36500, base_vg30=50500, override=-5, ref_base=50500) == 36500


# ── build_price_board: full board shape, scaling and overrides applied ──

def test_build_price_board_shapes():
    board = pb.build_price_board(base_vg30=76870)
    assert set(board) >= {"refinery", "imports"}
    # refinery rows: (name, grade, price); import rows: (name, price)
    for name, grade, price in board["refinery"]:
        assert isinstance(name, str) and isinstance(grade, str)
        assert isinstance(price, (int, float)) and price > 0
    for name, price in board["imports"]:
        assert isinstance(name, str)
        assert isinstance(price, (int, float)) and price > 0


def test_build_price_board_scales_every_row_with_base():
    base_board = pb.build_price_board(base_vg30=76870)
    up_board = pb.build_price_board(base_vg30=84557)  # +10%
    base_ref = {n: p for n, g, p in base_board["refinery"]}
    up_ref = {n: p for n, g, p in up_board["refinery"]}
    assert base_ref, "expected at least one refinery row"
    for name, base_price in base_ref.items():
        assert up_ref[name] == int(round(base_price * 1.1))


def test_build_price_board_applies_valid_override():
    # An override key present in live_prices wins for that one location.
    key = pb.REFINERY_ITEMS[0].override_key
    name = pb.REFINERY_ITEMS[0].name
    board = pb.build_price_board(base_vg30=76870, overrides={key: 79000})
    prices = {n: p for n, g, p in board["refinery"]}
    assert prices[name] == 79000


def test_build_price_board_ignores_absurd_override():
    key = pb.REFINERY_ITEMS[0].override_key
    name = pb.REFINERY_ITEMS[0].name
    board = pb.build_price_board(base_vg30=76870, overrides={key: 999999})
    prices = {n: p for n, g, p in board["refinery"]}
    assert prices[name] != 999999  # absurd -> derived shown instead
    assert prices[name] > 0
