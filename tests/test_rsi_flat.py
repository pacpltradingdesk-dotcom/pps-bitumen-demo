"""Regression: _rsi returned 100 (false OVERBOUGHT) for a flat series."""

import market_pulse_engine as mpe


def test_rsi_flat_series_is_neutral():
    assert mpe._rsi([100.0] * 20) == 50.0


def test_rsi_pure_uptrend_is_overbought():
    assert mpe._rsi([float(i) for i in range(20)]) == 100.0


def test_rsi_short_series_neutral_default():
    assert mpe._rsi([1.0, 2.0]) == 50.0
