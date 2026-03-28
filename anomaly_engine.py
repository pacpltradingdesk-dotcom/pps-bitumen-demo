"""
anomaly_engine.py — Anomaly Detection Engine
=============================================
IsolationForest anomaly detection for price shocks, tender spikes, demand anomalies.
Fallback: Z-score statistical detection when sklearn not installed.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
LOG = logging.getLogger("anomaly_engine")

# ── Optional dependency detection ────────────────────────────────────────────
_HAS_SKLEARN = False
try:
    from sklearn.ensemble import IsolationForest
    _HAS_SKLEARN = True
except Exception:
    pass


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: str | Path) -> list | dict:
    fp = BASE / path if not str(path).startswith(("/", "\\")) and ":" not in str(path) else Path(path)
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_anomaly_status() -> dict:
    """Returns IsolationForest availability and detection capabilities."""
    return {
        "isolation_forest_available": _HAS_SKLEARN,
        "active_engine": "isolation_forest" if _HAS_SKLEARN else "zscore",
        "capabilities": [
            "price_anomalies",
            "tender_spikes",
            "demand_anomalies",
        ],
        "install_hint": "pip install scikit-learn" if not _HAS_SKLEARN else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Z-SCORE FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════

def _zscore_detect(values: list[float], threshold: float = 2.5) -> list[int]:
    """Detect anomalies using Z-score. Returns indices of anomalous values."""
    if len(values) < 5:
        return []
    arr = np.array(values, dtype=float)
    mean = np.mean(arr)
    std = np.std(arr)
    if std < 1e-8:
        return []
    zscores = np.abs((arr - mean) / std)
    return [int(i) for i in np.where(zscores > threshold)[0]]


def _isolation_forest_detect(values: list[float], contamination: float = 0.05) -> list[int]:
    """Detect anomalies using IsolationForest. Returns indices of anomalous values."""
    if not _HAS_SKLEARN or len(values) < 10:
        return _zscore_detect(values)

    try:
        X = np.array(values, dtype=float).reshape(-1, 1)
        model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        predictions = model.fit_predict(X)
        return [int(i) for i in np.where(predictions == -1)[0]]
    except Exception as e:
        LOG.debug("IsolationForest failed, falling back to zscore: %s", e)
        return _zscore_detect(values)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PRICE ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_price_anomalies(prices: list[dict] | None = None) -> dict:
    """
    Detect anomalous price movements in crude/bitumen prices.
    Input: list of {"date": str, "value": float} or loads from tbl_crude_prices.json
    Returns: {"anomalies": [...], "model": str, "alert": bool, "total_checked": int}
    """
    if prices is None:
        raw = _load_json("tbl_crude_prices.json")
        records = raw if isinstance(raw, list) else raw.get("records", raw.get("data", []))
        prices = []
        for r in records:
            date = r.get("timestamp") or r.get("date") or r.get("created_at", "")
            brent = r.get("brent_usd") or r.get("price") or r.get("value")
            if brent:
                prices.append({"date": str(date)[:10], "value": float(brent)})

    if not prices:
        return {"anomalies": [], "model": "none", "alert": False, "total_checked": 0}

    values = [p["value"] for p in prices]
    dates = [p.get("date", f"idx_{i}") for i, p in enumerate(prices)]

    # Detect on raw values
    anomaly_idx = _isolation_forest_detect(values)

    # Also detect on price changes (returns)
    if len(values) >= 5:
        changes = [values[i] - values[i - 1] for i in range(1, len(values))]
        change_anomalies = _isolation_forest_detect(changes, contamination=0.08)
        # Offset by 1 since changes start from index 1
        anomaly_idx = sorted(set(anomaly_idx) | {i + 1 for i in change_anomalies})

    anomalies = []
    for idx in anomaly_idx:
        if idx >= len(prices):
            continue
        # Calculate severity based on z-score
        arr = np.array(values, dtype=float)
        mean_val = np.mean(arr)
        std_val = np.std(arr)
        zscore = abs(values[idx] - mean_val) / max(std_val, 0.01)
        severity = "high" if zscore > 3 else "medium"

        anomalies.append({
            "date": dates[idx],
            "value": round(values[idx], 2),
            "severity": severity,
            "zscore": round(zscore, 2),
            "deviation_pct": round((values[idx] - mean_val) / max(mean_val, 0.01) * 100, 1),
        })

    return {
        "anomalies": anomalies,
        "model": "isolation_forest" if _HAS_SKLEARN else "zscore",
        "alert": len([a for a in anomalies if a["severity"] == "high"]) > 0,
        "total_checked": len(prices),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TENDER SPIKE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_tender_spikes(tenders: list[dict] | None = None) -> dict:
    """
    Detect unusual spikes in tender activity by state/month.
    Input: list of {"state": str, "month": str, "count": int} or loads from DB.
    Returns: {"spikes": [...], "model": str, "total_checked": int}
    """
    if tenders is None:
        tenders = _load_tender_counts()

    if not tenders:
        return {"spikes": [], "model": "none", "total_checked": 0}

    # Group by state and detect spikes in counts
    state_groups: dict[str, list] = {}
    for t in tenders:
        state = t.get("state", "Unknown")
        count = t.get("count", 0)
        state_groups.setdefault(state, []).append({
            "month": t.get("month", ""),
            "count": count,
        })

    spikes = []
    for state, data in state_groups.items():
        if len(data) < 3:
            continue
        counts = [d["count"] for d in data]
        anomaly_idx = _isolation_forest_detect(counts, contamination=0.1)
        if not anomaly_idx:
            anomaly_idx = _zscore_detect(counts, threshold=2.0)

        for idx in anomaly_idx:
            if idx >= len(data):
                continue
            mean_count = np.mean(counts)
            spike_pct = (counts[idx] - mean_count) / max(mean_count, 1) * 100
            if spike_pct > 50:  # Only flag significant spikes (>50% above mean)
                spikes.append({
                    "state": state,
                    "month": data[idx].get("month", ""),
                    "count": counts[idx],
                    "mean_count": round(mean_count, 1),
                    "spike_pct": round(spike_pct, 1),
                    "severity": "high" if spike_pct > 100 else "medium",
                })

    return {
        "spikes": spikes,
        "model": "isolation_forest" if _HAS_SKLEARN else "zscore",
        "total_checked": len(tenders),
    }


def _load_tender_counts() -> list[dict]:
    """Load tender counts from infra_demand_scores."""
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT state, strftime('%Y-%m', score_date) as month, "
            "COUNT(*) as count FROM infra_demand_scores "
            "GROUP BY state, month ORDER BY month"
        ).fetchall()
        cols = [d[0] for d in conn.description]
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DEMAND ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_demand_anomalies(scores: list[dict] | None = None) -> dict:
    """
    Detect sudden demand shifts in infra_demand_scores.
    Input: list of {"state": str, "date": str, "score": float} or loads from DB.
    Returns: {"anomalies": [...], "model": str, "total_checked": int}
    """
    if scores is None:
        scores = _load_demand_scores()

    if not scores:
        return {"anomalies": [], "model": "none", "total_checked": 0}

    # Group by state and detect anomalies in scores
    state_groups: dict[str, list] = {}
    for s in scores:
        state = s.get("state", "Unknown")
        state_groups.setdefault(state, []).append({
            "date": s.get("date", ""),
            "score": float(s.get("score", 0)),
        })

    anomalies = []
    for state, data in state_groups.items():
        if len(data) < 5:
            continue
        score_vals = [d["score"] for d in data]
        anomaly_idx = _isolation_forest_detect(score_vals)
        if not anomaly_idx:
            anomaly_idx = _zscore_detect(score_vals, threshold=2.0)

        mean_score = np.mean(score_vals)
        for idx in anomaly_idx:
            if idx >= len(data):
                continue
            deviation = score_vals[idx] - mean_score
            anomalies.append({
                "state": state,
                "date": data[idx].get("date", ""),
                "score": round(score_vals[idx], 1),
                "mean_score": round(mean_score, 1),
                "deviation": round(deviation, 1),
                "direction": "surge" if deviation > 0 else "drop",
                "severity": "high" if abs(deviation) > mean_score * 0.3 else "medium",
            })

    return {
        "anomalies": anomalies,
        "model": "isolation_forest" if _HAS_SKLEARN else "zscore",
        "total_checked": len(scores),
    }


def _load_demand_scores() -> list[dict]:
    """Load demand scores from database."""
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT state, score_date as date, composite_score as score "
            "FROM infra_demand_scores ORDER BY score_date"
        ).fetchall()
        cols = [d[0] for d in conn.description]
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AGGREGATE ANOMALY SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

def get_anomaly_summary() -> dict:
    """Returns current active anomalies across all monitored metrics."""
    price = detect_price_anomalies()
    tender = detect_tender_spikes()
    demand = detect_demand_anomalies()

    total_anomalies = (
        len(price["anomalies"]) +
        len(tender["spikes"]) +
        len(demand["anomalies"])
    )

    high_severity = (
        len([a for a in price["anomalies"] if a.get("severity") == "high"]) +
        len([s for s in tender["spikes"] if s.get("severity") == "high"]) +
        len([a for a in demand["anomalies"] if a.get("severity") == "high"])
    )

    alert_level = "critical" if high_severity >= 3 else (
        "warning" if high_severity >= 1 or total_anomalies >= 5 else
        "normal"
    )

    return {
        "alert_level": alert_level,
        "total_anomalies": total_anomalies,
        "high_severity_count": high_severity,
        "price_anomalies": price,
        "tender_spikes": tender,
        "demand_anomalies": demand,
        "model": "isolation_forest" if _HAS_SKLEARN else "zscore",
        "checked_at": _now_ist(),
    }
