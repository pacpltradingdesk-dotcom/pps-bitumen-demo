"""Top-bar alert count must match the Command Center's definition.

Live audit 09-07-2026: top bar said "⚠️ 1855 alerts" while Quick Stats said
"32 OPEN ALERTS" on the same screen. The ribbon counted every SRE row whose
status wasn't literally "dismissed" (so thousands of Resolved rows counted);
the Command Center counts status == "Open", deduped by message. One
definition, one number.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from components.power_stats_ribbon import _count_active_alerts  # noqa: E402

NOW = datetime.datetime(2026, 7, 9, 11, 0)


def test_resolved_sre_alerts_do_not_count():
    sre = [
        {"status": "Open", "message": "API brent degraded"},
        {"status": "Resolved", "message": "old issue"},
        {"status": "resolved", "message": "older issue"},
        {"status": "Auto-Resolved", "message": "ancient issue"},
    ]
    assert _count_active_alerts(sre, None, NOW) == 1


def test_open_sre_alerts_dedup_by_message_like_command_center():
    sre = [
        {"status": "Open", "message": "price_anomalies WARN"},
        {"status": "Open", "message": "price_anomalies WARN"},
        {"status": "Open", "what_happened": "scheduler late"},
    ]
    assert _count_active_alerts(sre, None, NOW) == 2


def test_market_alerts_still_counted_when_active():
    market = [{"expires_at": "2099-01-01 00:00:00"}]
    assert _count_active_alerts([], market, NOW) == 1


def test_none_sources_return_none():
    assert _count_active_alerts(None, None, NOW) is None
