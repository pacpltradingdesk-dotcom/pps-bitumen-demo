"""
model_monitor.py — ML Model Performance Monitor
=================================================
Tracks prediction accuracy, detects concept drift, and alerts on degradation.
Logs predictions + actuals to ml_models/predictions_log.json for evaluation.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

LOG = logging.getLogger("model_monitor")
IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "ml_models"
MODEL_DIR.mkdir(exist_ok=True)
PREDICTIONS_LOG = MODEL_DIR / "predictions_log.json"
HEALTH_FILE = MODEL_DIR / "model_health.json"


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _load_predictions() -> list[dict]:
    try:
        if PREDICTIONS_LOG.exists():
            return json.loads(PREDICTIONS_LOG.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_predictions(preds: list[dict]):
    # Keep max 5000 entries
    if len(preds) > 5000:
        preds = preds[-5000:]
    try:
        with open(PREDICTIONS_LOG, "w", encoding="utf-8") as f:
            json.dump(preds, f, indent=1, ensure_ascii=False)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# LOG PREDICTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def log_prediction(
    model_name: str,
    prediction: float,
    confidence: float = 0.0,
    features: dict | None = None,
    actual: float | None = None,
    target_date: str = "",
) -> None:
    """Log a model prediction for later accuracy evaluation."""
    preds = _load_predictions()
    preds.append({
        "model": model_name,
        "prediction": prediction,
        "confidence": confidence,
        "features": features or {},
        "actual": actual,
        "target_date": target_date,
        "logged_at": _now_ist(),
        "evaluated": actual is not None,
    })
    _save_predictions(preds)


def update_actual(model_name: str, target_date: str, actual: float) -> int:
    """Back-fill actual values for past predictions."""
    preds = _load_predictions()
    updated = 0
    for p in preds:
        if p.get("model") == model_name and p.get("target_date") == target_date and not p.get("evaluated"):
            p["actual"] = actual
            p["evaluated"] = True
            updated += 1
    if updated:
        _save_predictions(preds)
    return updated


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATE ACCURACY
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_accuracy(model_name: str, lookback_days: int = 30) -> dict:
    """
    Evaluate prediction accuracy for a model.
    Returns: MAE, RMSE, MAPE, directional accuracy, sample count.
    """
    preds = _load_predictions()
    cutoff = (datetime.now(IST) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    evaluated = [
        p for p in preds
        if p.get("model") == model_name
        and p.get("evaluated")
        and p.get("actual") is not None
        and p.get("logged_at", "") >= cutoff
    ]

    if not evaluated:
        return {
            "model": model_name,
            "samples": 0,
            "mae": None, "rmse": None, "mape": None,
            "directional_accuracy": None,
            "note": "No evaluated predictions found",
        }

    predictions = np.array([p["prediction"] for p in evaluated])
    actuals = np.array([p["actual"] for p in evaluated])

    errors = predictions - actuals
    abs_errors = np.abs(errors)

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # MAPE (avoid division by zero)
    nonzero_mask = actuals != 0
    mape = float(np.mean(abs_errors[nonzero_mask] / np.abs(actuals[nonzero_mask])) * 100) if nonzero_mask.any() else None

    # Directional accuracy (did we predict up/down correctly?)
    if len(evaluated) >= 2:
        pred_dirs = np.sign(np.diff(predictions))
        actual_dirs = np.sign(np.diff(actuals))
        correct = np.sum(pred_dirs == actual_dirs)
        dir_acc = float(correct / len(pred_dirs) * 100) if len(pred_dirs) > 0 else None
    else:
        dir_acc = None

    return {
        "model": model_name,
        "samples": len(evaluated),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 2) if mape is not None else None,
        "directional_accuracy": round(dir_acc, 1) if dir_acc is not None else None,
        "lookback_days": lookback_days,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_drift(model_name: str, window_days: int = 14) -> dict:
    """
    Detect concept drift using Population Stability Index (PSI)
    and mean/std shift between recent and older predictions.
    """
    preds = _load_predictions()
    model_preds = [p for p in preds if p.get("model") == model_name and p.get("evaluated")]

    if len(model_preds) < 20:
        return {"model": model_name, "drift_detected": False, "note": "Insufficient data"}

    cutoff = (datetime.now(IST) - timedelta(days=window_days)).strftime("%Y-%m-%d")
    recent = [p["prediction"] for p in model_preds if p.get("logged_at", "") >= cutoff]
    older = [p["prediction"] for p in model_preds if p.get("logged_at", "") < cutoff]

    if len(recent) < 5 or len(older) < 5:
        return {"model": model_name, "drift_detected": False, "note": "Insufficient split data"}

    recent_arr = np.array(recent)
    older_arr = np.array(older)

    # Mean/std shift
    mean_shift = abs(np.mean(recent_arr) - np.mean(older_arr))
    std_ratio = np.std(recent_arr) / max(np.std(older_arr), 1e-8)

    # Simplified PSI (using histogram bins)
    psi = _compute_psi(older_arr, recent_arr, buckets=10)

    drift_detected = psi > 0.2 or mean_shift > np.std(older_arr) * 2 or std_ratio > 2.0

    return {
        "model": model_name,
        "drift_detected": drift_detected,
        "psi": round(psi, 4),
        "mean_shift": round(float(mean_shift), 4),
        "std_ratio": round(float(std_ratio), 4),
        "recent_count": len(recent),
        "older_count": len(older),
        "threshold": {"psi": 0.2, "mean_shift": "2x std", "std_ratio": 2.0},
    }


def _compute_psi(reference: np.ndarray, current: np.ndarray, buckets: int = 10) -> float:
    """Compute Population Stability Index."""
    try:
        breakpoints = np.linspace(
            min(reference.min(), current.min()),
            max(reference.max(), current.max()),
            buckets + 1,
        )
        ref_hist = np.histogram(reference, bins=breakpoints)[0] / len(reference)
        cur_hist = np.histogram(current, bins=breakpoints)[0] / len(current)

        # Avoid log(0)
        ref_hist = np.clip(ref_hist, 1e-6, None)
        cur_hist = np.clip(cur_hist, 1e-6, None)

        psi = np.sum((cur_hist - ref_hist) * np.log(cur_hist / ref_hist))
        return float(psi)
    except Exception:
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL HEALTH DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def get_model_health() -> dict:
    """Aggregate health status for all tracked models."""
    preds = _load_predictions()
    model_names = list({p.get("model") for p in preds if p.get("model")})

    health = {}
    for name in model_names:
        acc = evaluate_accuracy(name, lookback_days=30)
        drift = detect_drift(name)
        health[name] = {
            "accuracy": acc,
            "drift": drift,
            "status": "healthy" if not drift.get("drift_detected") else "degraded",
        }

    # Save health snapshot
    result = {"models": health, "checked_at": _now_ist(), "total_predictions": len(preds)}
    try:
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result


def alert_on_degradation(mape_threshold: float = 15.0) -> list[dict]:
    """Return alerts for models with MAPE above threshold or drift detected."""
    health = get_model_health()
    alerts = []
    for name, info in health.get("models", {}).items():
        acc = info.get("accuracy", {})
        drift = info.get("drift", {})

        if acc.get("mape") and acc["mape"] > mape_threshold:
            alerts.append({
                "model": name,
                "type": "accuracy_degradation",
                "mape": acc["mape"],
                "threshold": mape_threshold,
                "message": f"Model '{name}' MAPE ({acc['mape']}%) exceeds threshold ({mape_threshold}%)",
            })
        if drift.get("drift_detected"):
            alerts.append({
                "model": name,
                "type": "concept_drift",
                "psi": drift.get("psi"),
                "message": f"Concept drift detected in model '{name}' (PSI={drift.get('psi', 0):.3f})",
            })

    return alerts
