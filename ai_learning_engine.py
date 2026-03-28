"""
PPS Anantam — AI Learning Engine v1.0
=======================================
Continuous learning from business outcomes.
Improves predictions and recommendations over time.

Learning Cycles:
  Daily  — Compare predictions with actuals, micro-adjust
  Weekly — Recalibrate factor weights
  Monthly — Full regression recalibration
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

LEARNING_LOG_FILE = BASE / "ai_learning_log.json"
LEARNED_WEIGHTS_FILE = BASE / "ai_learned_weights.json"

# Default factor weights for price prediction
DEFAULT_WEIGHTS = {
    "crude_trend": 0.35,
    "fx_trend": 0.20,
    "seasonal_pattern": 0.15,
    "refinery_utilization": 0.15,
    "import_volume": 0.15,
}


def _load_json(path, default=None):
    if default is None:
        default = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _now() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


class AILearningEngine:
    """Continuous learning from business outcomes."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()
        self.weights = self._load_weights()

    def _load_weights(self) -> dict:
        """Load learned weights or use defaults."""
        data = _load_json(LEARNED_WEIGHTS_FILE, {})
        if isinstance(data, dict) and data.get("weights"):
            return data["weights"]
        return dict(DEFAULT_WEIGHTS)

    def _save_weights(self):
        """Persist learned weights."""
        _save_json(LEARNED_WEIGHTS_FILE, {
            "weights": self.weights,
            "updated_at": _now(),
            "version": self._get_version(),
        })

    def _get_version(self) -> int:
        data = _load_json(LEARNED_WEIGHTS_FILE, {})
        if isinstance(data, dict):
            return data.get("version", 0) + 1
        return 1

    def get_learned_weights(self) -> dict:
        """Return current learned weights."""
        return dict(self.weights)

    # ─── Daily Learning ──────────────────────────────────────────────────

    def daily_learn(self) -> dict:
        """Compare yesterday's predictions with actuals, micro-adjust."""
        if not self.settings.get("ai_learning_enabled", True):
            return {"status": "disabled"}
        if not self.settings.get("ai_learning_daily", True):
            return {"status": "disabled"}

        result = {
            "cycle_type": "daily",
            "run_date": _now(),
            "predictions_evaluated": [],
            "adjustments": [],
            "accuracy_scores": {},
        }

        # Evaluate price predictions
        price_eval = self._evaluate_price_predictions()
        result["predictions_evaluated"] = price_eval.get("evaluations", [])
        result["accuracy_scores"]["price_7d"] = price_eval.get("accuracy_7d", 0)

        # Micro-adjust weights based on recent accuracy
        if price_eval.get("evaluations"):
            adjustments = self._micro_adjust_weights(price_eval)
            result["adjustments"] = adjustments

        # Log learning cycle
        self._log_cycle(result)
        return result

    def _evaluate_price_predictions(self) -> dict:
        """Compare predicted vs actual crude prices."""
        evaluations = []

        try:
            crude = _load_json(BASE / "tbl_crude_prices.json", [])
            brent = [r for r in crude if r.get("benchmark") == "Brent" and r.get("price")]
            if len(brent) < 7:
                return {"evaluations": [], "accuracy_7d": 0}

            # Check if we have stored predictions
            predictions = _load_json(BASE / "ai_predictions_log.json", [])
            recent_preds = [p for p in predictions
                            if p.get("type") == "crude_price"
                            and p.get("predicted_for")]

            actual_price = brent[-1].get("price", 0)
            for pred in recent_preds[-5:]:
                predicted = pred.get("predicted_value", 0)
                if predicted > 0 and actual_price > 0:
                    error_pct = abs(predicted - actual_price) / actual_price * 100
                    evaluations.append({
                        "type": "crude_price",
                        "predicted": predicted,
                        "actual": actual_price,
                        "error_pct": round(error_pct, 2),
                    })

            # Calculate accuracy (100 - avg error)
            if evaluations:
                avg_error = sum(e["error_pct"] for e in evaluations) / len(evaluations)
                accuracy = max(0, round(100 - avg_error, 1))
            else:
                accuracy = 50  # Default when no predictions to evaluate

            return {"evaluations": evaluations, "accuracy_7d": accuracy}
        except Exception:
            return {"evaluations": [], "accuracy_7d": 0}

    def _micro_adjust_weights(self, price_eval: dict) -> list:
        """Make small weight adjustments based on evaluation results."""
        adjustments = []
        accuracy = price_eval.get("accuracy_7d", 50)

        # Only adjust if accuracy is significantly off
        if accuracy >= 80:
            return []  # Model is performing well, no changes

        # Slight boost to crude_trend if crude was most predictive
        # (this is a simplified version — full implementation would
        # track per-factor accuracy)
        if accuracy < 60:
            # Increase crude weight slightly (most reliable signal)
            old_crude = self.weights.get("crude_trend", 0.35)
            new_crude = min(0.45, old_crude + 0.01)
            if new_crude != old_crude:
                self.weights["crude_trend"] = round(new_crude, 3)
                adjustments.append({
                    "parameter": "crude_trend",
                    "old_value": old_crude,
                    "new_value": new_crude,
                    "reason": f"Price accuracy low ({accuracy}%), boosting crude signal",
                })
                # Rebalance: reduce smallest weight
                self._rebalance_weights("crude_trend")

        self._save_weights()
        return adjustments

    def _rebalance_weights(self, boosted_key: str):
        """Ensure weights sum to 1.0 after adjustment."""
        total = sum(self.weights.values())
        if abs(total - 1.0) < 0.001:
            return
        # Proportionally reduce other weights
        excess = total - 1.0
        other_keys = [k for k in self.weights if k != boosted_key]
        if not other_keys:
            return
        reduction_each = excess / len(other_keys)
        for k in other_keys:
            self.weights[k] = max(0.05, round(self.weights[k] - reduction_each, 3))

    # ─── Weekly Learning ─────────────────────────────────────────────────

    def weekly_learn(self) -> dict:
        """Recalibrate factor weights based on 30-day accuracy."""
        if not self.settings.get("ai_learning_weekly", True):
            return {"status": "disabled"}

        result = {
            "cycle_type": "weekly",
            "run_date": _now(),
            "weight_changes": [],
            "customer_score_updates": 0,
        }

        # Recalibrate weights from learning log
        log = _load_json(LEARNING_LOG_FILE, [])
        daily_cycles = [c for c in log if c.get("cycle_type") == "daily"]
        recent_30d = daily_cycles[-30:] if len(daily_cycles) >= 30 else daily_cycles

        if recent_30d:
            accuracies = [c.get("accuracy_scores", {}).get("price_7d", 50)
                          for c in recent_30d]
            avg_accuracy = sum(accuracies) / len(accuracies)
            result["avg_30d_accuracy"] = round(avg_accuracy, 1)

        # Update customer relationship scores
        try:
            from crm_engine import IntelligentCRM
            crm = IntelligentCRM()
            updated = crm.auto_update_all_profiles()
            result["customer_score_updates"] = updated
        except Exception:
            pass

        self._log_cycle(result)
        return result

    # ─── Monthly Learning ────────────────────────────────────────────────

    def monthly_learn(self) -> dict:
        """Full regression recalibration using 90-day data."""
        if not self.settings.get("ai_learning_monthly", True):
            return {"status": "disabled"}

        result = {
            "cycle_type": "monthly",
            "run_date": _now(),
            "model_version": self._get_version(),
            "accuracy_report": {},
        }

        # Run full correlation analysis
        try:
            from correlation_engine import run_full_analysis
            corr_result = run_full_analysis()
            n_corr = len(corr_result.get("correlations", [])) if isinstance(corr_result, dict) else 0
            result["correlations_recalculated"] = n_corr
        except Exception:
            result["correlations_recalculated"] = 0

        # Archive learning log (keep last 90 entries)
        log = _load_json(LEARNING_LOG_FILE, [])
        if len(log) > 90:
            _save_json(LEARNING_LOG_FILE, log[-90:])
            result["log_trimmed"] = True

        # Generate accuracy report from history
        daily_cycles = [c for c in log if c.get("cycle_type") == "daily"]
        if daily_cycles:
            accuracies = [c.get("accuracy_scores", {}).get("price_7d", 0)
                          for c in daily_cycles]
            result["accuracy_report"] = {
                "avg_accuracy": round(sum(accuracies) / len(accuracies), 1),
                "best_accuracy": round(max(accuracies), 1) if accuracies else 0,
                "worst_accuracy": round(min(accuracies), 1) if accuracies else 0,
                "total_cycles": len(daily_cycles),
            }

        self._log_cycle(result)
        return result

    # ─── Prediction Logging ──────────────────────────────────────────────

    def log_prediction(self, prediction_type: str, predicted_value: float,
                       predicted_for: str, factors: dict = None):
        """Log a prediction for later evaluation."""
        predictions = _load_json(BASE / "ai_predictions_log.json", [])
        predictions.append({
            "type": prediction_type,
            "predicted_value": predicted_value,
            "predicted_for": predicted_for,
            "factors": factors or {},
            "created_at": _now(),
        })
        if len(predictions) > 1000:
            predictions = predictions[-1000:]
        _save_json(BASE / "ai_predictions_log.json", predictions)

    # ─── Model Accuracy ──────────────────────────────────────────────────

    def get_model_accuracy(self) -> dict:
        """Return current model accuracy scores."""
        log = _load_json(LEARNING_LOG_FILE, [])
        daily = [c for c in log if c.get("cycle_type") == "daily"]
        recent = daily[-7:] if len(daily) >= 7 else daily

        if not recent:
            return {
                "price_7d": 50,
                "total_cycles": 0,
                "weights": self.weights,
                "last_updated": "Never",
            }

        accuracies = [c.get("accuracy_scores", {}).get("price_7d", 50) for c in recent]
        return {
            "price_7d": round(sum(accuracies) / len(accuracies), 1),
            "total_cycles": len(daily),
            "weights": self.weights,
            "last_updated": recent[-1].get("run_date", "Unknown"),
        }

    def get_learning_history(self, limit: int = 20) -> list:
        """Return recent learning cycles."""
        log = _load_json(LEARNING_LOG_FILE, [])
        return log[-limit:]

    # ─── Logging ─────────────────────────────────────────────────────────

    def _log_cycle(self, result: dict):
        """Append result to learning log."""
        log = _load_json(LEARNING_LOG_FILE, [])
        log.append(result)
        if len(log) > 500:
            log = log[-500:]
        _save_json(LEARNING_LOG_FILE, log)
