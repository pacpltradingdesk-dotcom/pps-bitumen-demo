"""
backtest_engine.py — Walk-Forward Backtesting Framework
========================================================
Tests forecasting models against historical data using walk-forward validation.
Compares Prophet, ARIMA, SARIMAX, and heuristic models.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

LOG = logging.getLogger("backtest_engine")
IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "ml_models"
MODEL_DIR.mkdir(exist_ok=True)
BACKTEST_REPORT = MODEL_DIR / "backtest_report.json"


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════════
# WALK-FORWARD TEST
# ═══════════════════════════════════════════════════════════════════════════════

def walk_forward_test(
    model_fn,
    data: pd.DataFrame,
    train_window: int = 90,
    test_window: int = 30,
    step: int = 15,
    label: str = "model",
) -> dict:
    """
    Walk-forward backtesting.

    Parameters
    ----------
    model_fn : callable(df_train, days_ahead) -> dict with "predicted" list
    data : pd.DataFrame with 'ds' (datetime) and 'y' (float) columns
    train_window : number of days in training window
    test_window : number of days to predict ahead
    step : number of days to slide the window forward
    label : model name for reporting

    Returns
    -------
    dict with MAE, RMSE, MAPE, directional accuracy, fold details
    """
    if len(data) < train_window + test_window:
        return {"model": label, "error": "Insufficient data", "folds": 0}

    all_errors = []
    all_abs_errors = []
    correct_dirs = 0
    total_dirs = 0
    fold_details = []

    start = 0
    while start + train_window + test_window <= len(data):
        train_df = data.iloc[start:start + train_window].copy()
        test_df = data.iloc[start + train_window:start + train_window + test_window].copy()

        try:
            forecast = model_fn(train_df, test_window)
            predicted = forecast.get("predicted", [])

            if not predicted:
                start += step
                continue

            # Align lengths
            actual = test_df["y"].values[:len(predicted)]
            pred = np.array(predicted[:len(actual)])

            if len(actual) == 0:
                start += step
                continue

            errors = pred - actual
            abs_errors = np.abs(errors)
            all_errors.extend(errors.tolist())
            all_abs_errors.extend(abs_errors.tolist())

            # Directional accuracy
            if len(actual) >= 2:
                pred_dir = np.sign(pred[-1] - pred[0])
                actual_dir = np.sign(actual[-1] - actual[0])
                if pred_dir == actual_dir:
                    correct_dirs += 1
                total_dirs += 1

            fold_details.append({
                "train_start": str(train_df["ds"].iloc[0].date()),
                "train_end": str(train_df["ds"].iloc[-1].date()),
                "test_end": str(test_df["ds"].iloc[-1].date()),
                "mae": round(float(np.mean(abs_errors)), 4),
                "samples": len(actual),
            })

        except Exception as e:
            LOG.debug("Fold failed for %s: %s", label, e)

        start += step

    if not all_errors:
        return {"model": label, "error": "No successful folds", "folds": 0}

    errors_arr = np.array(all_errors)
    abs_errors_arr = np.array(all_abs_errors)

    mae = float(np.mean(abs_errors_arr))
    rmse = float(np.sqrt(np.mean(errors_arr ** 2)))

    # MAPE (relative to mean value)
    mean_val = abs(data["y"].mean())
    mape = float(mae / mean_val * 100) if mean_val > 0 else None

    dir_acc = float(correct_dirs / total_dirs * 100) if total_dirs > 0 else None

    return {
        "model": label,
        "folds": len(fold_details),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 2) if mape is not None else None,
        "directional_accuracy": round(dir_acc, 1) if dir_acc is not None else None,
        "total_samples": len(all_errors),
        "fold_details": fold_details,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

def compare_models(data: pd.DataFrame | None = None) -> dict:
    """
    Compare all available forecasting models on crude price data.
    Returns comparative report.
    """
    if data is None:
        data = _load_crude_data()

    if data is None or len(data) < 120:
        return {"error": "Insufficient historical data (need 120+ points)", "models": []}

    results = []

    # Model 1: Prophet
    try:
        from ml_forecast_engine import _HAS_PROPHET
        if _HAS_PROPHET:
            from ml_forecast_engine import _forecast_prophet
            result = walk_forward_test(
                lambda df, days: _forecast_prophet(df, days, "backtest"),
                data, label="prophet",
            )
            results.append(result)
    except Exception as e:
        LOG.debug("Prophet backtest failed: %s", e)

    # Model 2: ARIMA
    try:
        from ml_forecast_engine import _HAS_STATSMODELS
        if _HAS_STATSMODELS:
            from ml_forecast_engine import _forecast_arima
            result = walk_forward_test(
                lambda df, days: _forecast_arima(df, days, "backtest"),
                data, label="arima",
            )
            results.append(result)
    except Exception as e:
        LOG.debug("ARIMA backtest failed: %s", e)

    # Model 3: SARIMAX
    try:
        from ml_forecast_engine import _HAS_STATSMODELS
        if _HAS_STATSMODELS:
            from ml_forecast_engine import _forecast_sarimax
            result = walk_forward_test(
                lambda df, days: _forecast_sarimax(df, days, "backtest"),
                data, label="sarimax",
            )
            results.append(result)
    except Exception as e:
        LOG.debug("SARIMAX backtest failed: %s", e)

    # Model 4: Heuristic (baseline)
    try:
        from ml_forecast_engine import _forecast_heuristic_crude
        result = walk_forward_test(
            lambda df, days: _forecast_heuristic_crude(
                [{"brent_usd": float(df["y"].iloc[-1])}], days
            ),
            data, label="heuristic",
        )
        results.append(result)
    except Exception as e:
        LOG.debug("Heuristic backtest failed: %s", e)

    # Rank by MAE (lower is better)
    valid = [r for r in results if r.get("mae") is not None]
    valid.sort(key=lambda r: r["mae"])

    best = valid[0]["model"] if valid else "none"

    report = {
        "models": valid,
        "best_model": best,
        "data_points": len(data),
        "tested_at": _now_ist(),
    }

    # Save report
    try:
        with open(BACKTEST_REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    except Exception:
        pass

    return report


def _load_crude_data() -> pd.DataFrame | None:
    """Load crude price data into a Prophet-compatible DataFrame."""
    try:
        from ml_forecast_engine import _load_json, _build_crude_df
        raw = _load_json("tbl_crude_prices.json")
        records = raw if isinstance(raw, list) else raw.get("records", raw.get("data", []))
        return _build_crude_df(records)
    except Exception:
        return None


def generate_report() -> dict:
    """Generate a comprehensive backtest report (calls compare_models)."""
    return compare_models()


def get_latest_report() -> dict:
    """Load the most recent backtest report from disk."""
    try:
        if BACKTEST_REPORT.exists():
            return json.loads(BACKTEST_REPORT.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"error": "No backtest report found. Run compare_models() first."}
