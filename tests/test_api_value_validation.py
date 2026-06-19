"""
Regression: api_manager accepted any non-None numeric (incl. 0.0) as a live
price, never consulting resilience_config.VALIDATION_RULES. A broken upstream
returning 0 poisoned every Brent/VG-30/FX calc. _value_in_range now gates it.
"""

import api_manager as am


def test_rejects_zero_and_out_of_range_brent():
    assert am._value_in_range("brent", 0.0) is False
    assert am._value_in_range("brent", -5) is False
    assert am._value_in_range("brent", 500) is False
    assert am._value_in_range("brent", 78.0) is True


def test_usdinr_bounds():
    assert am._value_in_range("usdinr", 0.0) is False
    assert am._value_in_range("usdinr", 500) is False
    assert am._value_in_range("usdinr", 93.89) is True   # high but in 50–120 band


def test_unknown_widget_passes_through():
    # No rule for this widget → don't block (avoid breaking unrelated widgets)
    assert am._value_in_range("news_count_widget", 12345) is True
