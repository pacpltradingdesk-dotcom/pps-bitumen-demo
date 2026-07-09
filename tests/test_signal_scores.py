"""Per-signal 0-100 scores must use each signal's own direction field.

Live audit 09-07-2026: Command Center's Market Signals grid showed all nine
sub-signals as an identical "Neutral 50%" while the composite read 66 — the
renderer's local mapper only understood a `direction` key, but currency uses
`pressure`, weather uses `road_condition`, govt uses `demand_trend`, etc.
The engine's master composite already knows these semantics; the public
signal_score() reuses them so the grid can never disagree with the master.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from market_intelligence_engine import signal_score  # noqa: E402


def test_direction_field_scores_above_50_when_up():
    assert signal_score({"direction": "UP", "confidence": 60}) == 80.0


def test_currency_pressure_field_is_understood():
    # pressure LOW -> downward price pressure -> bearish score, NOT flat 50
    s = signal_score({"pressure": "LOW", "confidence": 72})
    assert s == 14.0


def test_weather_road_condition_field_is_understood():
    s = signal_score({"road_condition": "POOR"})
    assert s < 50


def test_govt_demand_trend_falling_is_bearish():
    s = signal_score({"demand_trend": "FALLING"})
    assert s < 50


def test_unknown_or_stable_direction_is_neutral_50():
    assert signal_score({"demand_level": "MEDIUM"}) == 50.0
    assert signal_score({}) == 50.0


def test_score_clamped_to_0_100():
    assert signal_score({"direction": "UP", "confidence": 200}) == 100.0
    assert signal_score({"direction": "DOWN", "confidence": 200}) == 0.0


def test_command_center_uses_engine_score():
    # Drift guard: the renderer must not keep a private direction-only mapper.
    src = (Path(__file__).parent.parent / "pages" / "home" /
           "command_center.py").read_text(encoding="utf-8")
    assert "from market_intelligence_engine import" in src
    assert "signal_score" in src
