"""
ml_boost_engine.py — LightGBM / XGBoost Gradient Boosting + SHAP Explainability
=================================================================================
Multi-factor scoring for opportunities, risk, state ranking, buyer scoring.
Every function has 3-tier fallback: LightGBM/XGBoost → sklearn → rule-based.
Works with ZERO new packages installed (falls back gracefully).
"""
from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "ml_models"
MODEL_DIR.mkdir(exist_ok=True)

LOG = logging.getLogger("ml_boost")

# ── Optional dependency detection ────────────────────────────────────────────
_HAS_LIGHTGBM = False
_HAS_XGBOOST = False
_HAS_SHAP = False
_HAS_SKLEARN = False
_HAS_JOBLIB = False

try:
    import lightgbm as lgb
    _HAS_LIGHTGBM = True
except Exception:
    pass

try:
    import xgboost as xgb
    _HAS_XGBOOST = True
except Exception:
    pass

try:
    import shap
    _HAS_SHAP = True
except Exception:
    pass

try:
    from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    _HAS_SKLEARN = True
except Exception:
    pass

try:
    import joblib
    _HAS_JOBLIB = True
except Exception:
    pass


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: str | Path) -> list | dict:
    fp = BASE / path if not os.path.isabs(str(path)) else Path(path)
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_boost_status() -> dict:
    """Returns which boost libraries are available and model freshness."""
    boost_models = [f.name for f in MODEL_DIR.glob("boost_*.pkl")]
    return {
        "lightgbm_available": _HAS_LIGHTGBM,
        "xgboost_available": _HAS_XGBOOST,
        "shap_available": _HAS_SHAP,
        "sklearn_fallback": _HAS_SKLEARN,
        "boost_models_on_disk": boost_models,
        "active_engine": (
            "lightgbm" if _HAS_LIGHTGBM else
            "xgboost" if _HAS_XGBOOST else
            "sklearn" if _HAS_SKLEARN else
            "rule-based"
        ),
        "install_hints": {
            "lightgbm": "pip install lightgbm",
            "xgboost": "pip install xgboost",
            "shap": "pip install shap",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

_OPPORTUNITY_FEATURES = [
    "price_delta", "relationship_score", "days_since_contact",
    "qty", "grade_vg30", "season_factor", "state_demand",
]

_RISK_FEATURES = [
    "payment_reliability", "overdue_days", "credit_terms_days",
    "total_orders", "avg_order_value", "days_since_last_order",
]

_STATE_FEATURES = [
    "demand_score", "tender_count", "budget_allocation",
    "weather_favorability", "competitor_density", "avg_price",
]

_BUYER_FEATURES = [
    "payment_reliability", "volume_consistency", "growth_trend",
    "order_frequency", "avg_order_size", "relationship_years",
]


def _features_to_array(features: dict, feature_names: list) -> np.ndarray:
    """Convert a feature dict to a numpy array in consistent order."""
    return np.array([[features.get(f, 0.0) for f in feature_names]])


def _explain_with_shap(model, X: np.ndarray, feature_names: list) -> dict:
    """Generate SHAP explanations for a prediction."""
    if not _HAS_SHAP:
        return _explain_with_importance(model, feature_names)
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        # For binary classification, shap_values may be a list
        if isinstance(shap_values, list):
            sv = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        else:
            sv = shap_values
        vals = sv[0] if len(sv.shape) > 1 else sv
        explanation = {}
        for i, name in enumerate(feature_names):
            if i < len(vals):
                explanation[name] = round(float(vals[i]), 3)
        return explanation
    except Exception as e:
        LOG.debug("SHAP failed: %s", e)
        return _explain_with_importance(model, feature_names)


def _explain_with_importance(model, feature_names: list) -> dict:
    """Fallback: use model's feature_importances_ attribute."""
    try:
        importances = model.feature_importances_
        return {
            name: round(float(imp), 3)
            for name, imp in zip(feature_names, importances)
        }
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. OPPORTUNITY SCORING — LightGBM → XGBoost → sklearn → rule
# ═══════════════════════════════════════════════════════════════════════════════

def score_opportunity_boost(features: dict) -> dict:
    """LightGBM/XGBoost multi-factor opportunity scoring with SHAP explanations."""
    X = _features_to_array(features, _OPPORTUNITY_FEATURES)

    # Tier 1: LightGBM
    model_path = MODEL_DIR / "boost_opportunity_lgb.pkl"
    if _HAS_LIGHTGBM and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            prob = float(model.predict_proba(X)[0][1]) * 100
            label = "Hot" if prob >= 70 else ("Warm" if prob >= 40 else "Cold")
            explanation = _explain_with_shap(model, X, _OPPORTUNITY_FEATURES)
            return {"score": round(prob, 1), "label": label, "model": "lightgbm",
                    "explanation": explanation}
        except Exception as e:
            LOG.debug("LightGBM opportunity failed: %s", e)

    # Tier 2: XGBoost
    model_path = MODEL_DIR / "boost_opportunity_xgb.pkl"
    if _HAS_XGBOOST and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            prob = float(model.predict_proba(X)[0][1]) * 100
            label = "Hot" if prob >= 70 else ("Warm" if prob >= 40 else "Cold")
            explanation = _explain_with_shap(model, X, _OPPORTUNITY_FEATURES)
            return {"score": round(prob, 1), "label": label, "model": "xgboost",
                    "explanation": explanation}
        except Exception as e:
            LOG.debug("XGBoost opportunity failed: %s", e)

    # Tier 3: sklearn GradientBoosting (Phase D model)
    model_path = MODEL_DIR / "opportunity_scorer.pkl"
    if _HAS_SKLEARN and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            # Phase D model uses 5 features, extract those
            X_sk = np.array([[
                features.get("price_delta", 0),
                features.get("relationship_score", 50),
                features.get("days_since_contact", 30),
                features.get("qty", 50),
                1 if features.get("grade_vg30", 0) else 0,
            ]])
            prob = float(model.predict_proba(X_sk)[0][1]) * 100
            label = "Hot" if prob >= 70 else ("Warm" if prob >= 40 else "Cold")
            return {"score": round(prob, 1), "label": label, "model": "sklearn",
                    "explanation": _explain_with_importance(model, _OPPORTUNITY_FEATURES[:5])}
        except Exception:
            pass

    # Tier 4: Rule-based
    return _rule_opportunity(features)


def _rule_opportunity(features: dict) -> dict:
    """Rule-based opportunity scoring fallback."""
    score = 50.0
    explanation = {}

    pd_val = features.get("price_delta", 0)
    if pd_val < 0:
        delta = min(20, abs(pd_val) / 100)
        score += delta
        explanation["price_delta"] = round(delta, 1)

    days = features.get("days_since_contact", 999)
    if days < 7:
        score += 15
        explanation["days_since_contact"] = 15.0
    elif days < 30:
        score += 8
        explanation["days_since_contact"] = 8.0

    rel = features.get("relationship_score", 0)
    if rel > 70:
        score += 10
        explanation["relationship_score"] = 10.0

    qty = features.get("qty", 0)
    if qty > 100:
        score += 5
        explanation["qty"] = 5.0

    sf = features.get("season_factor", 1.0)
    if sf > 1.02:
        score += 5
        explanation["season_factor"] = 5.0

    sd = features.get("state_demand", 50)
    if sd > 70:
        score += 5
        explanation["state_demand"] = 5.0

    score = min(100, max(0, score))
    label = "Hot" if score >= 70 else ("Warm" if score >= 40 else "Cold")
    return {"score": round(score, 1), "label": label, "model": "rule",
            "explanation": explanation}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RISK SCORING — LightGBM → XGBoost → sklearn → rule
# ═══════════════════════════════════════════════════════════════════════════════

def score_risk_boost(customer_data: dict) -> dict:
    """XGBoost/LightGBM customer risk scoring with SHAP explanations."""
    X = _features_to_array(customer_data, _RISK_FEATURES)

    # Tier 1: XGBoost (better for risk scoring with imbalanced data)
    model_path = MODEL_DIR / "boost_risk_xgb.pkl"
    if _HAS_XGBOOST and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            prob = float(model.predict_proba(X)[0][1]) * 100
            label = "High" if prob >= 70 else ("Medium" if prob >= 40 else "Low")
            explanation = _explain_with_shap(model, X, _RISK_FEATURES)
            return {"score": round(prob, 1), "label": label, "model": "xgboost",
                    "explanation": explanation}
        except Exception as e:
            LOG.debug("XGBoost risk failed: %s", e)

    # Tier 2: LightGBM
    model_path = MODEL_DIR / "boost_risk_lgb.pkl"
    if _HAS_LIGHTGBM and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            prob = float(model.predict_proba(X)[0][1]) * 100
            label = "High" if prob >= 70 else ("Medium" if prob >= 40 else "Low")
            explanation = _explain_with_shap(model, X, _RISK_FEATURES)
            return {"score": round(prob, 1), "label": label, "model": "lightgbm",
                    "explanation": explanation}
        except Exception as e:
            LOG.debug("LightGBM risk failed: %s", e)

    # Tier 3: sklearn (Phase D model)
    model_path = MODEL_DIR / "risk_scorer.pkl"
    if _HAS_SKLEARN and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            X_sk = np.array([[
                customer_data.get("payment_reliability", 90),
                customer_data.get("overdue_days", 0),
                customer_data.get("credit_terms_days", 0),
                customer_data.get("total_orders", 0),
                customer_data.get("avg_order_value", 0),
            ]])
            prob = float(model.predict_proba(X_sk)[0][1]) * 100
            label = "High" if prob >= 70 else ("Medium" if prob >= 40 else "Low")
            return {"score": round(prob, 1), "label": label, "model": "sklearn",
                    "explanation": _explain_with_importance(model, _RISK_FEATURES[:5])}
        except Exception:
            pass

    # Tier 4: Rule-based
    return _rule_risk(customer_data)


def _rule_risk(data: dict) -> dict:
    """Rule-based risk scoring fallback."""
    score = 30.0
    explanation = {}

    pay = data.get("payment_reliability", 90)
    if pay < 70:
        score += 40
        explanation["payment_reliability"] = 40.0
    elif pay < 85:
        score += 20
        explanation["payment_reliability"] = 20.0

    overdue = data.get("overdue_days", 0)
    if overdue > 30:
        score += 20
        explanation["overdue_days"] = 20.0
    elif overdue > 7:
        score += 10
        explanation["overdue_days"] = 10.0

    credit = data.get("credit_terms_days", 0)
    if credit > 30:
        score += 10
        explanation["credit_terms_days"] = 10.0

    days_since = data.get("days_since_last_order", 0)
    if days_since > 180:
        score += 10
        explanation["days_since_last_order"] = 10.0

    score = min(100, max(0, score))
    label = "High" if score >= 70 else ("Medium" if score >= 40 else "Low")
    return {"score": round(score, 1), "label": label, "model": "rule",
            "explanation": explanation}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. STATE DEMAND RANKING — LightGBM → rule
# ═══════════════════════════════════════════════════════════════════════════════

def rank_states(states_data: list[dict] | None = None) -> dict:
    """LightGBM state-level demand ranking with explanations."""
    if states_data is None:
        states_data = _load_state_features()

    if not states_data:
        return {"rankings": [], "model": "rule", "explanation": {}}

    # Tier 1: LightGBM regressor
    model_path = MODEL_DIR / "boost_state_ranker_lgb.pkl"
    if _HAS_LIGHTGBM and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            rankings = []
            for sd in states_data:
                X = _features_to_array(sd, _STATE_FEATURES)
                pred = float(model.predict(X)[0])
                explanation = _explain_with_shap(model, X, _STATE_FEATURES)
                rankings.append({
                    "state": sd.get("state", "Unknown"),
                    "score": round(pred, 1),
                    "explanation": explanation,
                })
            rankings.sort(key=lambda x: x["score"], reverse=True)
            return {"rankings": rankings, "model": "lightgbm"}
        except Exception as e:
            LOG.debug("LightGBM state ranking failed: %s", e)

    # Tier 2: Rule-based weighted scoring
    rankings = []
    for sd in states_data:
        score = (
            sd.get("demand_score", 50) * 0.30 +
            sd.get("tender_count", 0) * 0.5 +
            sd.get("budget_allocation", 50) * 0.25 +
            sd.get("weather_favorability", 50) * 0.05 -
            sd.get("competitor_density", 5) * 2 +
            sd.get("avg_price", 40000) * 0.0001
        )
        rankings.append({
            "state": sd.get("state", "Unknown"),
            "score": round(max(0, min(100, score)), 1),
            "explanation": {
                "demand_score": round(sd.get("demand_score", 50) * 0.30, 1),
                "tender_count": round(sd.get("tender_count", 0) * 0.5, 1),
                "budget_allocation": round(sd.get("budget_allocation", 50) * 0.25, 1),
            },
        })
    rankings.sort(key=lambda x: x["score"], reverse=True)
    return {"rankings": rankings, "model": "rule"}


def _load_state_features() -> list[dict]:
    """Load state-level features from infra_demand_scores."""
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT state, AVG(composite_score) as demand_score, COUNT(*) as tender_count "
            "FROM infra_demand_scores GROUP BY state ORDER BY demand_score DESC"
        ).fetchall()
        cols = [d[0] for d in conn.description]
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 4. BUYER SCORING — LightGBM → rule
# ═══════════════════════════════════════════════════════════════════════════════

def score_buyer(buyer_data: dict) -> dict:
    """Buyer scoring: payment reliability, volume consistency, growth trend."""
    X = _features_to_array(buyer_data, _BUYER_FEATURES)

    # Tier 1: LightGBM
    model_path = MODEL_DIR / "boost_buyer_lgb.pkl"
    if _HAS_LIGHTGBM and _HAS_JOBLIB and model_path.exists():
        try:
            model = joblib.load(model_path)
            pred = float(model.predict(X)[0])
            score = max(0, min(100, pred))
            tier = "A" if score >= 75 else ("B" if score >= 50 else "C")
            explanation = _explain_with_shap(model, X, _BUYER_FEATURES)
            return {"score": round(score, 1), "tier": tier, "model": "lightgbm",
                    "explanation": explanation}
        except Exception:
            pass

    # Tier 2: Rule-based
    return _rule_buyer(buyer_data)


def _rule_buyer(data: dict) -> dict:
    """Rule-based buyer scoring."""
    score = 50.0
    explanation = {}

    pay = data.get("payment_reliability", 50)
    pay_contrib = (pay - 50) * 0.3
    score += pay_contrib
    explanation["payment_reliability"] = round(pay_contrib, 1)

    vol = data.get("volume_consistency", 50)
    vol_contrib = (vol - 50) * 0.2
    score += vol_contrib
    explanation["volume_consistency"] = round(vol_contrib, 1)

    growth = data.get("growth_trend", 0)
    growth_contrib = growth * 5
    score += growth_contrib
    explanation["growth_trend"] = round(growth_contrib, 1)

    freq = data.get("order_frequency", 1)
    freq_contrib = min(10, freq * 2)
    score += freq_contrib
    explanation["order_frequency"] = round(freq_contrib, 1)

    years = data.get("relationship_years", 0)
    years_contrib = min(10, years * 2)
    score += years_contrib
    explanation["relationship_years"] = round(years_contrib, 1)

    score = max(0, min(100, score))
    tier = "A" if score >= 75 else ("B" if score >= 50 else "C")
    return {"score": round(score, 1), "tier": tier, "model": "rule",
            "explanation": explanation}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SHAP EXPLANATION API
# ═══════════════════════════════════════════════════════════════════════════════

def explain_prediction(model_name: str, features: dict) -> dict:
    """Generate SHAP explanation for any trained boost model."""
    model_map = {
        "opportunity": ("boost_opportunity_lgb.pkl", _OPPORTUNITY_FEATURES),
        "risk": ("boost_risk_xgb.pkl", _RISK_FEATURES),
        "state": ("boost_state_ranker_lgb.pkl", _STATE_FEATURES),
        "buyer": ("boost_buyer_lgb.pkl", _BUYER_FEATURES),
    }

    if model_name not in model_map:
        return {"error": f"Unknown model: {model_name}", "available": list(model_map.keys())}

    pkl_name, feat_names = model_map[model_name]
    model_path = MODEL_DIR / pkl_name

    if not _HAS_JOBLIB or not model_path.exists():
        return {"error": "Model not trained yet", "model": model_name}

    try:
        model = joblib.load(model_path)
        X = _features_to_array(features, feat_names)
        explanation = _explain_with_shap(model, X, feat_names)
        return {
            "model": model_name,
            "engine": "shap" if _HAS_SHAP else "feature_importance",
            "feature_importance": explanation,
        }
    except Exception as e:
        return {"error": str(e), "model": model_name}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. TRAINING — LightGBM / XGBoost models
# ═══════════════════════════════════════════════════════════════════════════════

def train_boost_models() -> dict:
    """Train all LightGBM/XGBoost models. Called from sync_engine."""
    if not (_HAS_LIGHTGBM or _HAS_XGBOOST) or not _HAS_JOBLIB:
        return {"models_trained": 0, "note": "LightGBM/XGBoost or joblib not installed"}

    trained = 0
    accuracy = {}

    # 1. Opportunity scorer
    try:
        X, y = _build_boost_opportunity_data()
        if len(X) >= 30:
            model, name, acc = _train_classifier(X, y, "opportunity")
            if model:
                trained += 1
                accuracy["opportunity"] = acc
    except Exception as e:
        LOG.warning("Boost opportunity training failed: %s", e)

    # 2. Risk scorer
    try:
        X, y = _build_boost_risk_data()
        if len(X) >= 30:
            model, name, acc = _train_classifier(X, y, "risk")
            if model:
                trained += 1
                accuracy["risk"] = acc
    except Exception as e:
        LOG.warning("Boost risk training failed: %s", e)

    # 3. State ranker (regression)
    try:
        X, y = _build_boost_state_data()
        if len(X) >= 20:
            model, name, acc = _train_regressor(X, y, "state_ranker")
            if model:
                trained += 1
                accuracy["state_ranker"] = acc
    except Exception as e:
        LOG.warning("Boost state ranker training failed: %s", e)

    # 4. Buyer scorer (regression)
    try:
        X, y = _build_boost_buyer_data()
        if len(X) >= 20:
            model, name, acc = _train_regressor(X, y, "buyer")
            if model:
                trained += 1
                accuracy["buyer"] = acc
    except Exception as e:
        LOG.warning("Boost buyer training failed: %s", e)

    return {"models_trained": trained, "accuracy": accuracy, "timestamp": _now_ist()}


def _train_classifier(X, y, name: str):
    """Train a classifier using best available library."""
    if _HAS_LIGHTGBM:
        try:
            model = lgb.LGBMClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.1,
                random_state=42, verbose=-1,
            )
            scores = cross_val_score(model, X, y, cv=min(5, len(X) // 6), scoring="accuracy")
            model.fit(X, y)
            joblib.dump(model, MODEL_DIR / f"boost_{name}_lgb.pkl")
            return model, "lightgbm", round(float(scores.mean()) * 100, 1)
        except Exception as e:
            LOG.debug("LightGBM classifier %s failed: %s", name, e)

    if _HAS_XGBOOST:
        try:
            model = xgb.XGBClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.1,
                random_state=42, eval_metric="logloss", verbosity=0,
            )
            scores = cross_val_score(model, X, y, cv=min(5, len(X) // 6), scoring="accuracy")
            model.fit(X, y)
            joblib.dump(model, MODEL_DIR / f"boost_{name}_xgb.pkl")
            return model, "xgboost", round(float(scores.mean()) * 100, 1)
        except Exception as e:
            LOG.debug("XGBoost classifier %s failed: %s", name, e)

    if _HAS_SKLEARN:
        try:
            model = GradientBoostingClassifier(
                n_estimators=50, max_depth=3, random_state=42,
            )
            scores = cross_val_score(model, X, y, cv=min(5, len(X) // 6), scoring="accuracy")
            model.fit(X, y)
            joblib.dump(model, MODEL_DIR / f"boost_{name}_sklearn.pkl")
            return model, "sklearn", round(float(scores.mean()) * 100, 1)
        except Exception as e:
            LOG.debug("sklearn classifier %s failed: %s", name, e)

    return None, "none", 0


def _train_regressor(X, y, name: str):
    """Train a regressor using best available library."""
    if _HAS_LIGHTGBM:
        try:
            model = lgb.LGBMRegressor(
                n_estimators=100, max_depth=5, learning_rate=0.1,
                random_state=42, verbose=-1,
            )
            scores = cross_val_score(model, X, y, cv=min(5, len(X) // 5), scoring="r2")
            model.fit(X, y)
            joblib.dump(model, MODEL_DIR / f"boost_{name}_lgb.pkl")
            return model, "lightgbm", round(float(max(0, scores.mean())) * 100, 1)
        except Exception as e:
            LOG.debug("LightGBM regressor %s failed: %s", name, e)

    if _HAS_XGBOOST:
        try:
            model = xgb.XGBRegressor(
                n_estimators=100, max_depth=5, learning_rate=0.1,
                random_state=42, verbosity=0,
            )
            scores = cross_val_score(model, X, y, cv=min(5, len(X) // 5), scoring="r2")
            model.fit(X, y)
            joblib.dump(model, MODEL_DIR / f"boost_{name}_xgb.pkl")
            return model, "xgboost", round(float(max(0, scores.mean())) * 100, 1)
        except Exception as e:
            LOG.debug("XGBoost regressor %s failed: %s", name, e)

    if _HAS_SKLEARN:
        try:
            model = GradientBoostingRegressor(
                n_estimators=50, max_depth=3, random_state=42,
            )
            scores = cross_val_score(model, X, y, cv=min(5, len(X) // 5), scoring="r2")
            model.fit(X, y)
            joblib.dump(model, MODEL_DIR / f"boost_{name}_sklearn.pkl")
            return model, "sklearn", round(float(max(0, scores.mean())) * 100, 1)
        except Exception as e:
            LOG.debug("sklearn regressor %s failed: %s", name, e)

    return None, "none", 0


# ── Training data builders ────────────────────────────────────────────────────

def _build_boost_opportunity_data():
    """Build training data for opportunity scorer (7 features)."""
    rng = np.random.default_rng(42)
    X, y = [], []
    for _ in range(200):
        price_delta = float(rng.normal(-500, 800))
        rel_score = float(rng.integers(20, 100))
        days_contact = float(rng.integers(0, 90))
        qty = float(rng.integers(10, 500))
        grade_vg30 = float(rng.choice([0, 1]))
        season = float(rng.choice([0.85, 0.92, 0.98, 1.0, 1.02, 1.05, 1.06]))
        state_demand = float(rng.integers(30, 95))

        won = 1 if (
            price_delta < -200 and rel_score > 55 and days_contact < 21
            and season > 0.95 and state_demand > 50
        ) else 0
        if rng.random() < 0.12:
            won = 1 - won
        X.append([price_delta, rel_score, days_contact, qty, grade_vg30, season, state_demand])
        y.append(won)
    return np.array(X), np.array(y)


def _build_boost_risk_data():
    """Build training data for risk scorer (6 features)."""
    rng = np.random.default_rng(43)
    X, y = [], []
    for _ in range(200):
        pay_rel = float(rng.integers(40, 100))
        overdue = float(rng.integers(0, 90))
        credit = float(rng.choice([0, 7, 15, 30, 45, 60]))
        orders = float(rng.integers(1, 80))
        avg_val = float(rng.integers(50000, 8000000))
        days_last = float(rng.integers(0, 365))

        risky = 1 if (pay_rel < 70 or overdue > 25 or (days_last > 180 and pay_rel < 80)) else 0
        if rng.random() < 0.10:
            risky = 1 - risky
        X.append([pay_rel, overdue, credit, orders, avg_val, days_last])
        y.append(risky)
    return np.array(X), np.array(y)


def _build_boost_state_data():
    """Build training data for state demand ranker (regression)."""
    rng = np.random.default_rng(44)
    X, y = [], []
    for _ in range(100):
        demand = float(rng.integers(20, 95))
        tenders = float(rng.integers(0, 50))
        budget = float(rng.integers(20, 100))
        weather = float(rng.integers(30, 90))
        competition = float(rng.integers(1, 15))
        price = float(rng.integers(35000, 50000))

        score = demand * 0.30 + tenders * 0.5 + budget * 0.25 + weather * 0.05 - competition * 2
        score += rng.normal(0, 3)
        X.append([demand, tenders, budget, weather, competition, price])
        y.append(max(0, min(100, score)))
    return np.array(X), np.array(y)


def _build_boost_buyer_data():
    """Build training data for buyer scorer (regression)."""
    rng = np.random.default_rng(45)
    X, y = [], []
    for _ in range(100):
        pay_rel = float(rng.integers(50, 100))
        vol_cons = float(rng.integers(30, 95))
        growth = float(rng.normal(0, 2))
        freq = float(rng.integers(1, 24))
        avg_size = float(rng.integers(20, 500))
        years = float(rng.integers(0, 15))

        score = (
            (pay_rel - 50) * 0.3 + (vol_cons - 50) * 0.2 +
            growth * 5 + min(10, freq * 2) + min(10, years * 2) + 50
        )
        score += rng.normal(0, 3)
        X.append([pay_rel, vol_cons, growth, freq, avg_size, years])
        y.append(max(0, min(100, score)))
    return np.array(X), np.array(y)
