"""Command Center alert panel: honest severity dots + role-scoped visibility.

Live audit 09-07-2026 leftovers:
- Open P2/P3 alerts rendered with a GREEN dot (green = all-good next to
  "Data quality WARN" text) because the dot mapping only knew P0/P1.
- Internal system-health alerts (API degraded, cache freshness, scheduler
  late) were shown to SALES users on the Command Center — ops noise that
  belongs to admin/director only; sales should see business alerts.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sre_engine import alert_dot, is_system_alert  # noqa: E402


# ── severity dots ────────────────────────────────────────────────────────────

def test_p0_red_p1_orange_p2_yellow():
    assert alert_dot("P0") == "🔴"
    assert alert_dot("critical") == "🔴"
    assert alert_dot("P1") == "🟠"
    assert alert_dot("warning") == "🟠"
    assert alert_dot("P2") == "🟡"


def test_open_alert_never_gets_green_dot():
    # Green next to an OPEN warning reads as "all good" — never allowed.
    for sev in ("P0", "P1", "P2", "P3", "info", "", None):
        assert alert_dot(sev) != "🟢"


# ── system vs business classification ───────────────────────────────────────

def test_system_health_alerts_detected():
    assert is_system_alert({"entity": "api_cache_freshness",
                            "message": "Data quality FAIL: api_cache_freshness"})
    assert is_system_alert({"entity": "usdinr",
                            "message": "API usdinr degraded performance"})
    assert is_system_alert({"entity": "scheduler",
                            "message": "Health check scheduler running late"})
    assert is_system_alert({"entity": "live_prices",
                            "message": "Data quality WARN: live_prices"})
    # Leaked on first live check (janki login): API-down feed alerts
    assert is_system_alert({"entity": "world_bank_cpi_india",
                            "message": "API world_bank_cpi_india is DOWN (non-critical feed)"})


def test_business_alerts_not_flagged_system():
    assert not is_system_alert({"entity": "brent_price",
                                "message": "Brent moved -4.0% in 24h"})
    assert not is_system_alert({"entity": "margin",
                                "message": "Margin below Rs 500/MT on VG10 deal"})
    assert not is_system_alert({"entity": "supplier",
                                "message": "Supplier payment reliability dropped"})
