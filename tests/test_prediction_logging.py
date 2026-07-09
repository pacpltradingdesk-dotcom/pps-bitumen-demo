"""Crude forecasts must be logged so the AI learning loop can close.

Live audit 09-07-2026: ai_predictions_log.json was never populated by
anything, so ai_learning_engine.daily_learn() found no predictions to
evaluate, never called _micro_adjust_weights, and ai_learned_weights.json
sat untouched for 22 days (the learning engine was a silent no-op).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ml_forecast_engine import log_crude_prediction  # noqa: E402


def _result(n_days=10, model="ensemble"):
    return {
        "dates": [f"2026-07-{9 + i:02d}" for i in range(n_days)],
        "predicted": [78.0 + i * 0.1 for i in range(n_days)],
        "model": model,
    }


def test_logs_seven_day_ahead_prediction(tmp_path):
    log = tmp_path / "preds.json"

    wrote = log_crude_prediction(_result(), path=log, today="2026-07-09")

    assert wrote is True
    entries = json.loads(log.read_text(encoding="utf-8"))
    assert len(entries) == 1
    e = entries[0]
    assert e["type"] == "crude_price"
    assert e["predicted_at"] == "2026-07-09"
    assert e["predicted_for"] == "2026-07-15"     # dates[6] = 7-day-ahead
    assert abs(e["predicted_value"] - 78.6) < 1e-9


def test_only_one_log_per_day(tmp_path):
    log = tmp_path / "preds.json"
    assert log_crude_prediction(_result(), path=log, today="2026-07-09") is True
    assert log_crude_prediction(_result(), path=log, today="2026-07-09") is False
    assert len(json.loads(log.read_text(encoding="utf-8"))) == 1


def test_short_or_heuristic_forecasts_not_logged(tmp_path):
    log = tmp_path / "preds.json"
    assert log_crude_prediction(_result(n_days=3), path=log, today="2026-07-09") is False
    assert log_crude_prediction(_result(model="heuristic"), path=log,
                                today="2026-07-09") is False
    assert not log.exists()


def test_log_capped_at_500(tmp_path):
    log = tmp_path / "preds.json"
    old = [{"type": "crude_price", "predicted_at": f"old-{i}"} for i in range(500)]
    log.write_text(json.dumps(old), encoding="utf-8")

    assert log_crude_prediction(_result(), path=log, today="2026-07-09") is True
    entries = json.loads(log.read_text(encoding="utf-8"))
    assert len(entries) == 500
    assert entries[-1]["predicted_at"] == "2026-07-09"
