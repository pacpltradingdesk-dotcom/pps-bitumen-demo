"""Tests for price_drift — bounded intra-fortnight VG30 estimate.

Between fortnightly circular updates the VG30 base nudges with crude + FX moves
since the circular ('anchor'), capped to ±5% so the published number stays
authoritative. No anchor / missing inputs -> no drift (returns the base).
"""
from __future__ import annotations

import price_drift as pd


A_BASE, A_BRENT, A_FX = 76870, 77.7, 86.19


def test_no_market_move_returns_anchor_base():
    assert pd.drift_vg30(A_BASE, A_BRENT, A_FX, A_BRENT, A_FX) == 76870


def test_crude_up_raises_base():
    # +$2 Brent * ₹450/MT/$ = +₹900
    assert pd.drift_vg30(A_BASE, A_BRENT, A_FX, A_BRENT + 2, A_FX) == 77770


def test_crude_down_lowers_base():
    assert pd.drift_vg30(A_BASE, A_BRENT, A_FX, A_BRENT - 2, A_FX) == 75970


def test_fx_up_raises_base():
    # +₹1 USD/INR * ₹120/MT = +₹120
    assert pd.drift_vg30(A_BASE, A_BRENT, A_FX, A_BRENT, A_FX + 1) == 76990


def test_drift_is_capped_at_5pct():
    # A massive +$130 move would be +₹58,500, but cap = 5% of 76,870 = ₹3,843.5
    r = pd.drift_vg30(A_BASE, A_BRENT, A_FX, 200.0, A_FX)
    assert r == int(round(A_BASE + A_BASE * 0.05))
    assert A_BASE < r <= A_BASE * 1.0501


def test_missing_inputs_no_drift():
    assert pd.drift_vg30(A_BASE, None, A_FX, A_BRENT, A_FX) == 76870
    assert pd.drift_vg30(A_BASE, A_BRENT, A_FX, None, A_FX) == 76870


def test_bad_anchor_base_is_safe():
    assert pd.drift_vg30(0, A_BRENT, A_FX, A_BRENT, A_FX) == 0
    assert isinstance(pd.drift_vg30("x", A_BRENT, A_FX, A_BRENT, A_FX), int)
