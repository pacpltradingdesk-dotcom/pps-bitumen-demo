"""
PPS Anantam -- Unified Intelligence Engine v1.0
=================================================
Central orchestrator tying ALL intelligence systems together.
Single entry point coordinating: market monitoring, recommendations,
business advisory, chatbot, discussion guidance, ML forecasts,
API health, SRE health, and model monitoring.

Results cached 15 min to avoid redundant computation.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

# -- Constants ---------------------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))
LOG = logging.getLogger("unified_intelligence_engine")
CACHE_TTL_SEC = 15 * 60

TOP_STATES = [
    "Gujarat", "Maharashtra", "Rajasthan", "Uttar Pradesh", "Tamil Nadu",
    "Karnataka", "Madhya Pradesh", "West Bengal", "Andhra Pradesh", "Bihar",
]

def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")

def _safe(fn, *args, default=None, label: str = ""):
    """Call fn(*args); swallow exceptions, return default on failure."""
    try:
        return fn(*args)
    except Exception as exc:
        LOG.debug("safe-call [%s]: %s", label or fn.__name__, exc)
        return default

# -- Optional engine imports (all try/except) --------------------------------
_market_pulse = _recommendation = _business_advisor = None
_trading_chatbot = _discussion_guidance = _ml_forecast = None
_market_intel = _api_hub = _sre = _model_monitor = None
_purchase_advisor_mod = None

try: import market_pulse_engine as _market_pulse  # noqa: E702
except Exception: pass
try: import recommendation_engine as _recommendation  # noqa: E702
except Exception: pass
try: import business_advisor_engine as _business_advisor  # noqa: E702
except Exception: pass
try: import trading_chatbot_engine as _trading_chatbot  # noqa: E702
except Exception: pass
try: import discussion_guidance_engine as _discussion_guidance  # noqa: E702
except Exception: pass
try: import ml_forecast_engine as _ml_forecast  # noqa: E702
except Exception: pass
try: import market_intelligence_engine as _market_intel  # noqa: E702
except Exception: pass
try:
    from purchase_advisor_engine import PurchaseAdvisorEngine  # noqa: F401
    _purchase_advisor_mod = True
except Exception: pass
try: import api_hub_engine as _api_hub  # noqa: E702
except Exception: pass
try: import sre_engine as _sre  # noqa: E702
except Exception: pass
try: import model_monitor as _model_monitor  # noqa: E702
except Exception: pass

# -- In-memory TTL cache -----------------------------------------------------
_cache: Dict[str, Any] = {}
_cache_ts: Dict[str, float] = {}

def _cget(key: str):
    if time.time() - _cache_ts.get(key, 0) < CACHE_TTL_SEC:
        return _cache.get(key)
    return None

def _cset(key: str, val):
    _cache[key] = val; _cache_ts[key] = time.time(); return val  # noqa: E702

# -- Internal builders -------------------------------------------------------

def _build_forecasts() -> dict:
    if not _ml_forecast:
        return {"error": "ml_forecast_engine not available"}
    fc: Dict[str, Any] = {
        "crude": _safe(_ml_forecast.forecast_crude_price, 30, default={}) or {},
        "fx": _safe(_ml_forecast.forecast_fx_rate, 30, default={}) or {},
    }
    demand = {}
    for st in TOP_STATES:
        demand[st] = _safe(_ml_forecast.forecast_state_demand, st, 3, default={}) or {}
    fc["demand"] = demand
    return fc

def _build_api_health() -> dict:
    if not _api_hub:
        return {"error": "api_hub_engine not available"}
    try:
        cat = _api_hub.HubCatalog.load()
        total = len(cat)
        live = sum(1 for v in cat.values() if v.get("status") == "Live")
        return {
            "total_connectors": total, "live": live,
            "failing": sum(1 for v in cat.values() if v.get("status") == "Failing"),
            "disabled": sum(1 for v in cat.values() if v.get("status") == "Disabled"),
            "health_pct": round((live / total) * 100, 1) if total else 0,
            "checked_at": _now_ist(),
        }
    except Exception as exc:
        return {"error": str(exc)}

# ============================================================================
# UnifiedIntelligence
# ============================================================================

class UnifiedIntelligence:
    """Central orchestrator for the AI Trading Intelligence System."""

    @staticmethod
    def get_complete_state() -> dict:
        """Full system state -- feeds AI context and Home page."""
        cached = _cget("complete_state")
        if cached is not None:
            return cached
        return _cset("complete_state", {
            "market": _safe(_market_pulse.monitor_all, default={}) if _market_pulse else {},
            "recommendations": _safe(_recommendation.get_latest_recommendations, default={}) if _recommendation else {},
            "advisory": _safe(_business_advisor.get_daily_brief, default={}) if _business_advisor else {},
            "alerts": _safe(_market_pulse.get_active_alerts, default=[]) if _market_pulse else [],
            "forecasts": _build_forecasts(),
            "api_health": _build_api_health(),
            "system_health": _safe(_sre.get_health_status, default=[]) if _sre else [],
            "generated_at": _now_ist(),
        })

    @staticmethod
    def get_dashboard_summary() -> dict:
        """Lightweight summary for Home page KPI cards."""
        cached = _cget("dashboard_summary")
        if cached is not None:
            return cached

        master = (_safe(_market_intel.get_master_signal, default={}) or {}) if _market_intel else {}
        top_rec, rec_conf = "No recommendation", 0
        if _recommendation:
            recs = _safe(_recommendation.get_latest_recommendations, default={}) or {}
            rl = recs.get("recommendations", [])
            if rl and isinstance(rl, list):
                top_rec = rl[0].get("action", rl[0].get("summary", top_rec))
                rec_conf = rl[0].get("confidence", 0)

        alert_count = len(_safe(_market_pulse.get_active_alerts, default=[]) or []) if _market_pulse else 0

        crude_price = fx_rate = None
        if _ml_forecast:
            cp = _safe(_ml_forecast.forecast_crude_price, 30, default={}) or {}
            crude_price = cp.get("current_price", cp.get("last_known"))
            fx = _safe(_ml_forecast.forecast_fx_rate, 30, default={}) or {}
            fx_rate = fx.get("current_rate", fx.get("last_known"))

        demand_outlook = "stable"
        if _ml_forecast:
            guj = _safe(_ml_forecast.forecast_state_demand, "Gujarat", 3, default={}) or {}
            demand_outlook = guj.get("outlook", guj.get("trend", "stable"))

        return _cset("dashboard_summary", {
            "market_bias": master.get("bias", master.get("direction", "neutral")),
            "top_recommendation": top_rec,
            "alert_count": alert_count,
            "crude_price": crude_price,
            "fx_rate": fx_rate,
            "demand_outlook": demand_outlook,
            "ai_confidence": rec_conf,
            "generated_at": _now_ist(),
        })

    @staticmethod
    def process_trading_query(query: str, history: list = None) -> dict:
        """Routes to TradingChatbot with full context."""
        if not _trading_chatbot:
            return {"answer": "Trading chatbot engine is not available.",
                    "source": "unified_intelligence_engine", "error": True,
                    "generated_at": _now_ist()}
        return _safe(_trading_chatbot.ask_trading_question, query, history,
                      default={"answer": "Unable to process query.", "error": True}) or \
               {"answer": "No response generated.", "error": True}

    @staticmethod
    def refresh_intelligence() -> dict:
        """Trigger full intelligence refresh (called by sync_engine Batch 5)."""
        results: Dict[str, str] = {}
        errors: List[str] = []
        _steps = [
            ("recommendations", _recommendation, lambda: _recommendation.generate_daily_recommendations()),
            ("advisory", _business_advisor, lambda: _business_advisor.get_daily_brief()),
            ("market_pulse", _market_pulse, lambda: _market_pulse.monitor_all()),
            ("model_health", _model_monitor, lambda: _model_monitor.get_model_health()),
            ("market_intelligence", _market_intel, lambda: _market_intel.compute_all_signals()),
        ]
        for name, mod, fn in _steps:
            if not mod:
                results[name] = "unavailable"; continue
            r = _safe(fn, label=name)
            results[name] = "refreshed" if r is not None else "skipped"
            if r is None:
                errors.append(name)

        _cache.clear(); _cache_ts.clear()
        return {"status": "completed", "engines_refreshed": results,
                "errors": errors, "error_count": len(errors),
                "refreshed_at": _now_ist()}

    @staticmethod
    def health_check() -> dict:
        """All engines operational status."""
        engines = {
            "market_pulse_engine": _market_pulse,
            "recommendation_engine": _recommendation,
            "business_advisor_engine": _business_advisor,
            "trading_chatbot_engine": _trading_chatbot,
            "discussion_guidance_engine": _discussion_guidance,
            "ml_forecast_engine": _ml_forecast,
            "market_intelligence_engine": _market_intel,
            "purchase_advisor_engine": _purchase_advisor_mod,
            "api_hub_engine": _api_hub,
            "sre_engine": _sre,
            "model_monitor": _model_monitor,
        }
        result = {n: {"available": m is not None, "status": "loaded" if m else "import_failed"}
                  for n, m in engines.items()}
        avail = sum(1 for v in result.values() if v.get("available"))
        result["_summary"] = {"total": len(engines), "available": avail,
                              "checked_at": _now_ist()}
        return result

# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================
_instance = UnifiedIntelligence()

def get_complete_state() -> dict:
    """Full system state -- feeds AI context and Home page."""
    return _instance.get_complete_state()

def get_dashboard_summary() -> dict:
    """Lightweight summary for Home page KPI cards."""
    return _instance.get_dashboard_summary()

def process_query(query: str, history: list = None) -> dict:
    """Route a trading query through the chatbot with full context."""
    return _instance.process_trading_query(query, history)

def refresh_intelligence() -> dict:
    """Trigger full intelligence refresh (called by sync_engine Batch 5)."""
    return _instance.refresh_intelligence()

def health_check() -> dict:
    """All engines operational status."""
    return _instance.health_check()

def get_intelligence_status() -> dict:
    """Quick status dict for sidebar display."""
    hc = _instance.health_check()
    s = hc.get("_summary", {})
    avail, total = s.get("available", 0), s.get("total", 0)
    return {
        "engines_online": avail, "engines_total": total,
        "health_pct": round((avail / total) * 100, 1) if total else 0,
        "status": "healthy" if avail >= total * 0.7 else "degraded",
        "checked_at": _now_ist(),
    }
