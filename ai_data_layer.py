"""
AI Data Layer — Central data access bridge for the AI Dashboard Assistant.

Aggregates live data from every dashboard module into a single structured context
dict that is safe, role-filtered, and ready for injection into an AI system prompt.

Role Permission Matrix
──────────────────────
Admin      → all modules
Sales      → prices, competitors, contractors (with CRM contacts), demand
Strategy   → prices, competitors, demand, budget, predictions
Finance    → prices, predictions, demand, budget
Operations → prices, apis, errors, changes, demand
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
import datetime
import traceback

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── Role → allowed modules ────────────────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Admin":      ["prices", "apis", "competitors", "contractors", "crm",
                   "errors", "changes", "predictions", "demand", "budget",
                   "dev", "consumption"],
    "Sales":      ["prices", "competitors", "contractors", "crm", "demand"],
    "Strategy":   ["prices", "competitors", "demand", "budget",
                   "predictions", "consumption"],
    "Finance":    ["prices", "predictions", "demand", "budget"],
    "Operations": ["prices", "apis", "errors", "changes", "demand"],
}

# ── Safe wrapper ──────────────────────────────────────────────────────────────
def _safe(fn, label: str, fallback=None):
    """Run fn(); on any exception return fallback with error key."""
    try:
        return fn()
    except Exception as exc:
        result = {"error": f"{label}: {exc}"}
        if fallback:
            result.update(fallback)
        return result


# ══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL DATA GETTERS
# ══════════════════════════════════════════════════════════════════════════════

def get_price_snapshot() -> dict:
    """Return key live prices from feasibility_engine."""
    def _inner():
        from feasibility_engine import get_live_prices
        p = get_live_prices()
        return {
            "source": "feasibility_engine → live_prices.json (defaults: IOCL circular 16-02-2026)",
            # PSU bulk basics
            "VG30_IOCL_Koyali_basic_per_MT":       p.get("IOCL Koyali",          48302),
            "VG30_IOCL_Mathura_basic_per_MT":       p.get("IOCL Mathura",         48450),
            "VG30_IOCL_Haldia_basic_per_MT":        p.get("IOCL Haldia",          48500),
            "VG30_BPCL_Mumbai_basic_per_MT":        p.get("BPCL Mumbai",          48200),
            "VG30_HPCL_Mumbai_basic_per_MT":        p.get("HPCL Mumbai",          48100),
            "VG30_HPCL_Ghaziabad_basic_per_MT":     p.get("HPCL Bhatinda",        46390),
            "VG30_CPCL_Chennai_basic_per_MT":       p.get("CPCL Chennai",         47800),
            # Drum
            "DRUM_Mumbai_VG30_per_MT":              p.get("DRUM_MUMBAI_VG30",     57500),
            "DRUM_Kandla_VG30_per_MT":              p.get("DRUM_KANDLA_VG30",     55800),
            # Logistics
            "bulk_transport_per_km_per_MT":         p.get("BULK_RATE_PER_KM",       2.5),
            "drum_transport_per_km_per_MT":         p.get("DRUM_RATE_PER_KM",       6.0),
            "decanter_conversion_cost_per_MT":      p.get("DECANTER_CONVERSION_COST", 500),
            # FX / Commodity
            "USD_INR_rate":                         p.get("USD_INR",              86.87),
            "Brent_crude_USD_per_barrel":           p.get("BRENT_CRUDE",          74.50),
        }
    return _safe(_inner, "get_price_snapshot",
                 {"VG30_IOCL_Koyali_basic_per_MT": 48302, "USD_INR_rate": 86.87})


def get_api_health_summary() -> dict:
    """Summarise API errors, changes, and health from api_manager."""
    def _inner():
        from api_manager import get_error_log, get_change_log
        errors  = get_error_log(n=50)
        changes = get_change_log(n=20)
        open_e  = [e for e in errors if "Open" in e.get("status", "")]
        p0      = [e for e in open_e if "P0" in e.get("severity", "")]
        p1      = [e for e in open_e if "P1" in e.get("severity", "")]
        auto_fx = [e for e in errors if e.get("auto_fixed")]
        return {
            "source": "api_manager → api_error_log.json + api_change_log.json",
            "total_errors_logged":  len(errors),
            "open_errors":          len(open_e),
            "p0_critical_open":     len(p0),
            "p1_high_open":         len(p1),
            "auto_fixes_executed":  len(auto_fx),
            "recent_errors_top3":   errors[:3],
            "recent_changes_top3":  changes[:3],
        }
    return _safe(_inner, "get_api_health_summary", {"open_errors": 0})


def get_competitor_summary() -> dict:
    """Pull MEE competitor intelligence data from competitor_intelligence.py."""
    def _inner():
        import competitor_intelligence as ci
        # PSU official prices
        psu = ci.PSU_PRICES.to_dict("records") if hasattr(ci, "PSU_PRICES") else []
        # MEE latest market data
        market = ci.MEE_MARKET.to_dict("records") if hasattr(ci, "MEE_MARKET") else []
        # International bitumen
        intl = ci.INTL_BITUMEN.to_dict("records") if hasattr(ci, "INTL_BITUMEN") else []
        # Forecast table
        forecasts = ci.MEE_FORECASTS.to_dict("records") if hasattr(ci, "MEE_FORECASTS") else []
        # Truth table
        truth = ci.TRUTH_TABLE.to_dict("records") if hasattr(ci, "TRUTH_TABLE") else []
        verified_right = [t for t in truth if "VERIFIED_RIGHT" in str(t.get("Verdict",""))]
        wrong           = [t for t in truth if "VERIFIED_WRONG"  in str(t.get("Verdict",""))]
        return {
            "source": "competitor_intelligence.py (MEE WhatsApp bulletins Feb 2026)",
            "competitor_name": "Multi Energy Enterprises (MEE), Mumbai",
            "competitor_type": "Industrial Fuel Management Consultants",
            "bulletin_schedule": "Daily 11 AM forecast + 11 AM & 4 PM market update",
            "key_finding_accuracy":
                "MEE forecast 16-02-2026 = +₹60 VG-30. IOCL actual = +₹60, HPCL actual = +₹60. EXACT MATCH.",
            "usd_inr_note":
                "MEE quotes 90.66–91.06 Rs/$ = bank TT/procurement rate, NOT RBI spot (~86.87 Rs/$).",
            "psu_latest_official_prices": psu,
            "market_data_latest_3":       market[:3],
            "international_fob_prices":   intl,
            "recent_forecasts_top5":      forecasts[:5],
            "verified_right_claims":      verified_right,
            "verified_wrong_claims":      wrong,
        }
    return _safe(_inner, "get_competitor_summary")


def get_contractor_crm(role: str = "Admin") -> dict:
    """Return CRM / OSINT data; filter contact details by role."""
    def _inner():
        osint_dir = BASE_DIR / "osint_data"
        def _load(name):
            p = osint_dir / f"{name}.json"
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

        contractors = _load("contractors_master")
        projects    = _load("projects_master")
        demands     = _load("bitumen_demand_estimates")
        signals     = _load("signals_feed")
        risks       = _load("risk_flags")
        changelog   = _load("change_history")

        total_mt  = sum(d.get("base_mt", 0) for d in demands)
        open_risk = [r for r in risks if r.get("status") == "OPEN"]

        # Only Sales gets raw contact details
        safe_contractors = []
        for c in contractors:
            row = {k: v for k, v in c.items()
                   if k not in ("contact_email", "contact_phone") or role == "Sales"}
            safe_contractors.append(row)

        # State-wise project spread
        state_map: dict[str, int] = {}
        for p in projects:
            s = p.get("state", "Unknown")
            state_map[s] = state_map.get(s, 0) + 1

        return {
            "source": "contractor_osint.py → osint_data/*.json",
            "data_window": "Last 6 months only (OSINT strict policy)",
            "total_contractors":         len(contractors),
            "total_projects":            len(projects),
            "total_bitumen_demand_MT":   round(total_mt, 1),
            "open_risk_flags":           len(open_risk),
            "state_wise_project_count":  state_map,
            "contractors":               safe_contractors,
            "projects_latest_5":         projects[:5],
            "demand_estimates_latest_5": demands[:5],
            "risk_flags_open":           open_risk,
            "signals_latest_5":          signals[:5],
            "recent_changelog":          changelog[:5],
        }
    return _safe(_inner, "get_contractor_crm", {"total_contractors": 0})


def get_demand_context() -> dict:
    """National road demand, budget, state-wise data from road_budget_demand."""
    def _inner():
        import road_budget_demand as rbd
        budget     = rbd.MORTH_BUDGET.to_dict("records")    if hasattr(rbd, "MORTH_BUDGET")     else []
        consump    = rbd.BITUMEN_CONSUMPTION.to_dict("records") if hasattr(rbd, "BITUMEN_CONSUMPTION") else []
        state_data = rbd.STATE_DATA.to_dict("records")      if hasattr(rbd, "STATE_DATA")       else []
        road_types = rbd.ROAD_TYPES.to_dict("records")      if hasattr(rbd, "ROAD_TYPES")       else []
        network    = rbd.ROAD_NETWORK                        if hasattr(rbd, "ROAD_NETWORK")     else {}
        return {
            "source": "road_budget_demand.py (MoRTH data, India road infra)",
            "morth_budget_history":        budget[-5:],   # Last 5 FY
            "bitumen_consumption_history": consump[-5:],
            "state_demand_profiles":       state_data,
            "road_type_reference":         road_types,
            "india_road_network":          network,
            "avg_bitumen_price_per_MT":    getattr(rbd, "AVG_BITUMEN_PRICE_PER_MT", 46000),
            "bitumen_pct_of_road_cost":    getattr(rbd, "BITUMEN_PCT_OF_COST", 0.12),
        }
    return _safe(_inner, "get_demand_context", {
        "bitumen_consumption_FY25_lakh_MT": 8.2,
        "top_states": ["Rajasthan", "Maharashtra", "UP", "MP", "Karnataka"],
    })


def get_india_consumption_series() -> dict:
    """Monthly India bitumen consumption / production from MEE charts."""
    def _inner():
        import competitor_intelligence as ci
        consumption = ci.INDIA_CONSUMPTION.to_dict("records") if hasattr(ci, "INDIA_CONSUMPTION") else []
        production  = ci.INDIA_PRODUCTION.to_dict("records")  if hasattr(ci, "INDIA_PRODUCTION")  else []
        return {
            "source": "competitor_intelligence.py (MEE India charts, TMT data)",
            "monthly_consumption_TMT": consumption,
            "monthly_production_TMT":  production,
        }
    return _safe(_inner, "get_india_consumption_series")


def get_prediction_context() -> dict:
    """Price prediction context and forecast calendar."""
    def _inner():
        import sys, os
        sys.path.insert(0, str(BASE_DIR / "command_intel"))
        from price_prediction import generate_forecast_calendar
        cal = generate_forecast_calendar()
        records = cal.head(6).to_dict("records") if cal is not None else []
        return {
            "source": "command_intel/price_prediction.py",
            "model":  "Statistical random walk + seasonal adjustment (seed=42)",
            "disclaimer": "Claimed 91.4% accuracy / MAE ₹384 is from seed-based simulation, not live ML.",
            "current_base_VG30_per_MT": 48302,
            "next_revision_date":       "01-03-2026 (1st fortnightly)",
            "forecast_direction":       "STABLE to SLIGHT_UP (Brent ₹ 74-76, INR ~86-87)",
            "upcoming_revisions_top6":  records,
        }
    return _safe(_inner, "get_prediction_context", {
        "current_base_VG30_per_MT": 48302,
        "next_revision_date": "01-03-2026",
    })


def get_dev_activity_summary() -> dict:
    """Recent developer activity from api_manager dev log."""
    def _inner():
        from api_manager import get_dev_log
        log = get_dev_log(n=10)
        return {
            "source": "api_manager → api_dev_log.json",
            "recent_dev_activity": log[:5],
        }
    return _safe(_inner, "get_dev_activity_summary", {"recent_dev_activity": []})


# ══════════════════════════════════════════════════════════════════════════════
# FULL CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_full_context(role: str = "Admin") -> dict:
    """
    Assemble all role-permitted data into one structured context dict.
    Called by ai_assistant_engine to build the AI system prompt.
    """
    allowed = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["Sales"])
    ctx: dict = {
        "dashboard_name":  "PPS Anantams Logistics — Bitumen Sales Intelligence Dashboard",
        "role":            role,
        "snapshot_ist":    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "modules_loaded":  allowed,
    }
    if "prices" in allowed:
        ctx["live_prices"] = get_price_snapshot()
    if "apis" in allowed or "errors" in allowed or "changes" in allowed:
        ctx["api_health"] = get_api_health_summary()
    if "competitors" in allowed:
        ctx["competitor_intelligence"] = get_competitor_summary()
    if "contractors" in allowed or "crm" in allowed:
        ctx["contractor_crm"] = get_contractor_crm(role)
    if "demand" in allowed or "budget" in allowed:
        ctx["national_demand"] = get_demand_context()
    if "consumption" in allowed:
        ctx["india_consumption_series"] = get_india_consumption_series()
    if "predictions" in allowed:
        ctx["price_predictions"] = get_prediction_context()
    if "dev" in allowed:
        ctx["dev_activity"] = get_dev_activity_summary()

    # ── Anomaly alerts (if available) ──────────────────────────────────────
    try:
        from anomaly_engine import get_anomaly_summary
        anomaly = get_anomaly_summary()
        if anomaly.get("total_anomalies", 0) > 0:
            ctx["anomaly_alerts"] = {
                "alert_level": anomaly["alert_level"],
                "total_anomalies": anomaly["total_anomalies"],
                "high_severity": anomaly["high_severity_count"],
                "price_anomalies": len(anomaly.get("price_anomalies", {}).get("anomalies", [])),
                "tender_spikes": len(anomaly.get("tender_spikes", {}).get("spikes", [])),
                "demand_anomalies": len(anomaly.get("demand_anomalies", {}).get("anomalies", [])),
            }
    except Exception:
        pass

    # ── Market sentiment (if FinBERT available) ────────────────────────────
    try:
        from finbert_engine import get_market_sentiment
        sentiment = get_market_sentiment()
        if sentiment.get("article_count", 0) > 0:
            ctx["market_sentiment"] = {
                "overall": sentiment["overall"],
                "trend": sentiment["trend"],
                "score": sentiment["score"],
                "articles_analyzed": sentiment["article_count"],
            }
    except Exception:
        pass

    return ctx


def build_context_json(role: str = "Admin") -> str:
    """Return full context as a JSON string for injection into AI system prompt."""
    ctx = build_full_context(role)
    return json.dumps(ctx, indent=2, ensure_ascii=False, default=str)


# ══════════════════════════════════════════════════════════════════════════════
# FULL TRADING CONTEXT (Step 4/10 — feeds the AI Trading Chatbot)
# ══════════════════════════════════════════════════════════════════════════════

def get_full_trading_context(role: str = "Admin") -> dict:
    """Aggregate ALL data sources into one context dict for the Trading Chatbot.

    Returns a superset of build_full_context() with additional:
    - Market pulse alerts & state
    - Trading recommendations
    - Business advisory
    - Supply chain / logistics context
    - Forecast data
    """
    # Start with existing full context
    ctx = build_full_context(role)

    # ── Market Pulse ─────────────────────────────────────────────────
    try:
        from market_pulse_engine import get_market_state_summary, get_active_alerts
        ctx["market_pulse"] = get_market_state_summary()
        alerts = get_active_alerts(max_age_hours=24)
        ctx["active_alerts"] = alerts[:10] if alerts else []
    except Exception:
        pass

    # ── Recommendations ──────────────────────────────────────────────
    try:
        from recommendation_engine import get_latest_recommendations
        recs = get_latest_recommendations()
        if recs and not recs.get("error"):
            ctx["recommendations"] = {
                "buy_timing": recs.get("buy_timing"),
                "sell_timing": recs.get("sell_timing"),
            }
    except Exception:
        pass

    # ── Business Advisory ────────────────────────────────────────────
    try:
        from business_advisor_engine import get_buy_advisory, get_sell_advisory
        ctx["buy_advisory"] = get_buy_advisory()
        ctx["sell_advisory"] = get_sell_advisory()
    except Exception:
        pass

    # ── Market Intelligence Master Signal ────────────────────────────
    try:
        from market_intelligence_engine import get_master_signal
        master = get_master_signal() or {}
        if master:
            ctx["master_signal"] = {
                "direction": master.get("market_direction"),
                "confidence": master.get("confidence"),
                "demand_outlook": master.get("demand_outlook"),
                "risk_level": master.get("risk_level"),
                "action": master.get("action"),
            }
    except Exception:
        pass

    # ── Purchase Advisor ─────────────────────────────────────────────
    try:
        from purchase_advisor_engine import PurchaseAdvisorEngine
        pa = PurchaseAdvisorEngine()
        advice = pa.compute_urgency_index()
        if advice:
            ctx["purchase_urgency"] = {
                "score": advice.get("urgency_index"),
                "action": advice.get("recommendation"),
                "detail": advice.get("recommendation_detail"),
                "stock": advice.get("stock_recommendation"),
            }
    except Exception:
        pass

    # ── Forecasts ────────────────────────────────────────────────────
    try:
        from ml_forecast_engine import forecast_crude_price, forecast_fx_rate
        crude_fc = forecast_crude_price(15)
        if crude_fc and crude_fc.get("predicted"):
            ctx["crude_forecast_15d"] = {
                "trend": crude_fc.get("trend"),
                "confidence": crude_fc.get("confidence"),
            }
        fx_fc = forecast_fx_rate(15)
        if fx_fc and fx_fc.get("predicted"):
            ctx["fx_forecast_15d"] = {
                "trend": fx_fc.get("trend"),
                "confidence": fx_fc.get("confidence"),
            }
    except Exception:
        pass

    # ── Supply Chain / Logistics ─────────────────────────────────────
    try:
        from api_hub_engine import HubCache
        maritime = HubCache.get("maritime_intel")
        if maritime:
            ctx["maritime_status"] = "available"
        ports = HubCache.get("ports")
        if ports:
            ctx["ports_status"] = "available"
    except Exception:
        pass

    return ctx


def get_supply_chain_context() -> dict:
    """Get supply chain and logistics context."""
    ctx = {}
    try:
        from api_hub_engine import HubCache
        ctx["maritime"] = HubCache.get("maritime_intel") or {}
        ctx["ports"] = HubCache.get("ports") or {}
        ctx["bdi"] = HubCache.get("bdi_index") or {}
    except Exception:
        pass
    return ctx


def get_logistics_context() -> dict:
    """Get logistics-specific context for chatbot."""
    ctx = {}
    try:
        from maritime_intelligence_engine import get_maritime_summary
        ctx["maritime_summary"] = get_maritime_summary()
    except Exception:
        pass
    try:
        from api_hub_engine import HubCache
        bdi = HubCache.get("bdi_index")
        if bdi:
            ctx["bdi_latest"] = bdi.get("latest")
    except Exception:
        pass
    return ctx


# ══════════════════════════════════════════════════════════════════════════════
# PRE-BUILT CHART DATA (called by UI to render quick charts)
# ══════════════════════════════════════════════════════════════════════════════

def get_chart_data(chart_key: str, role: str = "Admin") -> dict | None:
    """
    Return ready-to-render Plotly data for named quick charts.
    chart_key options:
      india_consumption_12m | state_demand_bar | price_trend_refinery |
      mee_forecasts | contractor_demand_bar | api_health_pie | intl_bitumen_fob
    """
    try:
        if chart_key == "india_consumption_12m":
            d = get_india_consumption_series()
            records = d.get("monthly_consumption_TMT", [])
            if records:
                x = [r.get("Month", r.get("month", "")) for r in records]
                y = [r.get("Consumption_TMT", r.get("consumption", 0)) for r in records]
                return {"type": "bar", "title": "India Bitumen Consumption (TMT) — Last 12 Months",
                        "x": x, "y": y, "x_label": "Month", "y_label": "Thousand MT",
                        "color": "#0284c7", "source": d.get("source", "")}

        elif chart_key == "state_demand_bar":
            d = get_demand_context()
            rows = d.get("state_demand_profiles", [])
            if rows:
                states = [r.get("State", "") for r in rows]
                budgets = [r.get("Total_Budget_Cr", r.get("Central_Cr", 0)) for r in rows]
                return {"type": "bar", "title": "State-wise Road Budget (₹ Crore) FY2025-26",
                        "x": states, "y": budgets,
                        "x_label": "State", "y_label": "₹ Crore",
                        "color": "#16a34a", "source": d.get("source", "")}

        elif chart_key == "price_trend_refinery":
            p = get_price_snapshot()
            refineries = {
                "IOCL Koyali":    p.get("VG30_IOCL_Koyali_basic_per_MT",    48302),
                "IOCL Mathura":   p.get("VG30_IOCL_Mathura_basic_per_MT",   48450),
                "IOCL Haldia":    p.get("VG30_IOCL_Haldia_basic_per_MT",    48500),
                "BPCL Mumbai":    p.get("VG30_BPCL_Mumbai_basic_per_MT",    48200),
                "HPCL Mumbai":    p.get("VG30_HPCL_Mumbai_basic_per_MT",    48100),
                "HPCL Ghaziabad": p.get("VG30_HPCL_Ghaziabad_basic_per_MT",46390),
                "CPCL Chennai":   p.get("VG30_CPCL_Chennai_basic_per_MT",   47800),
            }
            return {"type": "bar", "title": "VG-30 Basic Ex-Refinery Prices (₹/MT) — Current",
                    "x": list(refineries.keys()), "y": list(refineries.values()),
                    "x_label": "Refinery", "y_label": "₹/MT",
                    "color": "#7c3aed", "source": p.get("source", "")}

        elif chart_key == "contractor_demand_bar":
            if "contractors" not in ROLE_PERMISSIONS.get(role, []) and role != "Admin":
                return None
            d = get_contractor_crm(role)
            demands = d.get("demand_estimates_latest_5", [])
            if demands:
                labels = [r.get("project_id", "?") for r in demands]
                vals   = [r.get("base_mt", 0) for r in demands]
                return {"type": "bar", "title": "Contractor Bitumen Demand by Project (MT)",
                        "x": labels, "y": vals,
                        "x_label": "Project", "y_label": "MT",
                        "color": "#dc2626", "source": d.get("source", "")}

        elif chart_key == "intl_bitumen_fob":
            import competitor_intelligence as ci
            if hasattr(ci, "INTL_BITUMEN"):
                rows = ci.INTL_BITUMEN.to_dict("records")
                if rows:
                    countries = [r.get("Country", r.get("country", "")) for r in rows]
                    prices    = [r.get("FOB_USD_per_MT", r.get("price", 0)) for r in rows]
                    return {"type": "bar",
                            "title": "International Bitumen FOB Prices (USD/MT)",
                            "x": countries, "y": prices,
                            "x_label": "Country/Port", "y_label": "USD/MT",
                            "color": "#f59e0b",
                            "source": "competitor_intelligence.py (MEE bulletins Feb 2026)"}

        elif chart_key == "api_health_pie":
            d = get_api_health_summary()
            total   = d.get("total_errors_logged", 0)
            open_e  = d.get("open_errors", 0)
            fixed   = d.get("auto_fixes_executed", 0)
            return {"type": "pie",
                    "title": "API Error Resolution Status",
                    "labels": ["Open", "Auto-Fixed", "Suppressed/Closed"],
                    "values": [open_e, fixed, max(0, total - open_e - fixed)],
                    "source": d.get("source", "")}

    except Exception:
        pass
    return None
