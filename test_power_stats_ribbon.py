"""Tests for the power-stats ribbon alert counting.

Regression: the ribbon was counting the *entire* market_alerts.json rolling
log (500 capped entries, mostly expired) as "active alerts" → showed
"503 alerts" while the Command Center showed only 3. The ribbon must count
only genuinely-active alerts: SRE alerts that aren't dismissed + market
alerts that haven't expired yet.
"""
import datetime

from components.power_stats_ribbon import (
    _parse_alert_ts,
    _market_alert_active,
    _count_active_alerts,
)

NOW = datetime.datetime(2026, 6, 18, 17, 0)


def test_parse_ist_timestamp():
    # Arrange / Act
    got = _parse_alert_ts("2026-06-10 06:14 IST")
    # Assert
    assert got == datetime.datetime(2026, 6, 10, 6, 14)


def test_parse_returns_none_for_empty():
    assert _parse_alert_ts(None) is None
    assert _parse_alert_ts("") is None
    assert _parse_alert_ts("garbage") is None


def test_market_alert_active_when_expiry_in_future():
    alert = {"expires_at": "2026-06-20 00:00 IST"}
    assert _market_alert_active(alert, NOW) is True


def test_market_alert_inactive_when_expired():
    alert = {"expires_at": "2026-06-10 06:14 IST"}
    assert _market_alert_active(alert, NOW) is False


def test_market_alert_dismissed_is_inactive():
    alert = {"expires_at": "2026-06-20 00:00 IST", "status": "dismissed"}
    assert _market_alert_active(alert, NOW) is False


def test_market_alert_without_expiry_counts_as_active():
    # Defensive: if a feed ever omits expires_at, don't silently hide it.
    alert = {"message": "no expiry field"}
    assert _market_alert_active(alert, NOW) is True


def test_count_active_alerts_combines_sre_open_and_live_market():
    # Arrange: 2 open SRE + 1 dismissed SRE; 1 live market + 2 expired market
    sre = [
        {"status": "Open", "message": "a"},
        {"status": "Open", "message": "b"},
        {"status": "dismissed", "message": "c"},
    ]
    market = [
        {"expires_at": "2026-06-20 00:00 IST"},       # live
        {"expires_at": "2026-06-10 00:00 IST"},       # expired
        {"expires_at": "2026-06-09 00:00 IST"},       # expired
    ]
    # Act
    total = _count_active_alerts(sre, market, NOW)
    # Assert: 2 SRE open + 1 live market = 3 (not 6)
    assert total == 3


def test_count_active_alerts_handles_none_inputs():
    assert _count_active_alerts(None, None, NOW) is None
    assert _count_active_alerts([], None, NOW) == 0
