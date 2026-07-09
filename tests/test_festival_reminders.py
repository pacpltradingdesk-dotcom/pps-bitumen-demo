"""Festival reminders must read the real sales_calendar data.

Found in the 09-07-2026 phantom-import sweep: rotation_engine imported
get_festivals/get_upcoming_festivals from sales_calendar — neither has ever
existed — so the customer festival-greeting feature always returned [] via a
swallowed ImportError. sales_calendar DOES carry the data
(MAJOR_FESTIVALS_2026 tuples); the engine now reads it directly.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rotation_engine import upcoming_from_calendar  # noqa: E402

FESTIVALS = [
    (7, 15, "Test Parv", 1),
    (7, 29, "Door Parv", 2),
    (1, 14, "Makar Sankranti", 1),
]


def test_upcoming_within_window():
    today = datetime.date(2026, 7, 9)
    out = upcoming_from_calendar(FESTIVALS, today=today, days_ahead=7)
    assert [f["name"] for f in out] == ["Test Parv"]
    assert out[0]["date"] == "2026-07-15"
    assert out[0]["duration_days"] == 1


def test_far_and_past_festivals_excluded():
    today = datetime.date(2026, 7, 16)
    out = upcoming_from_calendar(FESTIVALS, today=today, days_ahead=7)
    assert out == []


def test_engine_method_returns_real_festivals():
    from rotation_engine import FestivalBroadcastEngine
    eng = FestivalBroadcastEngine()
    # Must not be the silent-ImportError [] path: with a full year window the
    # real 2026 calendar has many festivals.
    out = eng.get_upcoming_festivals(days_ahead=365)
    assert len(out) >= 5
    assert all(f.get("name") and f.get("date") for f in out)
