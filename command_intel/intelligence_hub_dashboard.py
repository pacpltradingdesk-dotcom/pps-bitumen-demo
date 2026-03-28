"""
PPS Anantam -- Intelligence Hub Dashboard v1.0
=================================================
2-tab UI: Intelligence Overview, System Health.
Central command panel that aggregates KPIs from all intelligence
engines and provides health/status monitoring with quick links.

Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

LOG = logging.getLogger("intelligence_hub_dashboard")

# ── Vastu Design System ─────────────────────────────────────────────────────
_NAVY  = "#1e3a5f"
_GREEN = "#2d6a4f"
_GOLD  = "#c9a84c"
_FIRE  = "#b85c38"
_IVORY = "#faf7f2"
_SLATE = "#64748b"

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent.parent

# ── Safe imports ─────────────────────────────────────────────────────────────
try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

try:
    from market_pulse_engine import get_market_state_summary, get_active_alerts
    _PULSE = True
except ImportError:
    _PULSE = False

try:
    from recommendation_engine import get_latest_recommendations
    _REC = True
except ImportError:
    _REC = False

try:
    from business_advisor_engine import get_buy_advisory
    _ADVISOR = True
except ImportError:
    _ADVISOR = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _load_json(filename: str) -> Any:
    """Load a JSON file from the project root."""
    path = BASE / filename
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        LOG.warning("Failed to load %s: %s", filename, exc)
    return None


def _status_indicator(ok: bool) -> str:
    """HTML for green/red status dot."""
    color = _GREEN if ok else "#dc2626"
    label = "Online" if ok else "Offline"
    return (
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'border-radius:50%;background:{color};margin-right:6px;"></span>'
        f'<span style="color:{color};font-weight:600;font-size:0.82rem;">{label}</span>'
    )


_BIAS_COLORS = {
    "BULLISH": _GREEN, "BEARISH": _FIRE, "NEUTRAL": _GOLD,
    "UP": _GREEN, "DOWN": _FIRE, "SIDEWAYS": _GOLD,
}


# ── Engine Health Checks ────────────────────────────────────────────────────

_ENGINE_CHECKS: List[Dict[str, Any]] = [
    {
        "name": "Market Pulse Engine",
        "module": "market_pulse_engine",
        "description": "Real-time market alerts and state monitoring",
    },
    {
        "name": "Recommendation Engine",
        "module": "recommendation_engine",
        "description": "AI buy/sell/hold recommendations",
    },
    {
        "name": "Business Advisor Engine",
        "module": "business_advisor_engine",
        "description": "Proactive buy/sell advisory and timing",
    },
    {
        "name": "Discussion Guidance Engine",
        "module": "discussion_guidance_engine",
        "description": "Discussion briefs and negotiation support",
    },
    {
        "name": "Calculation Engine",
        "module": "calculation_engine",
        "description": "Pricing, landed costs, and 3-tier offers",
    },
    {
        "name": "Opportunity Engine",
        "module": "opportunity_engine",
        "description": "Automated trade opportunity discovery",
    },
    {
        "name": "CRM Engine",
        "module": "crm_engine",
        "description": "Intelligent customer relationship management",
    },
    {
        "name": "Market Intelligence Engine",
        "module": "market_intelligence_engine",
        "description": "10-signal composite market intelligence",
    },
    {
        "name": "ML Forecast Engine",
        "module": "ml_forecast_engine",
        "description": "Crude, FX, and demand forecasting",
    },
    {
        "name": "Maritime Intelligence Engine",
        "module": "maritime_intelligence_engine",
        "description": "Port congestion and logistics monitoring",
    },
    {
        "name": "API Hub Engine",
        "module": "api_hub_engine",
        "description": "14 API connectors and data synchronisation",
    },
    {
        "name": "SRE Engine",
        "module": "sre_engine",
        "description": "Self-healing and auto bug fixing",
    },
    {
        "name": "Chart Engine",
        "module": "chart_engine",
        "description": "Plotly chart generation with Vastu Design",
    },
    {
        "name": "Sync Engine",
        "module": "sync_engine",
        "description": "Master data sync (hourly + on-demand)",
    },
]


def _check_engine_health() -> List[dict]:
    """Check import status of all engines."""
    import importlib
    results = []
    for engine in _ENGINE_CHECKS:
        try:
            importlib.import_module(engine["module"])
            status = True
        except Exception:
            status = False
        results.append({
            "name": engine["name"],
            "module": engine["module"],
            "description": engine["description"],
            "online": status,
        })
    return results


# ── Tab A: Intelligence Overview ────────────────────────────────────────────

def _render_intelligence_overview(st) -> None:
    """KPI grid: Market Bias, Top Rec, Alerts, Crude, FX, AI Confidence."""
    st.subheader("Intelligence Overview")

    # Gather data from engines
    market_summary: dict = {}
    rec_data: dict = {}
    buy_data: dict = {}

    if _PULSE:
        try:
            market_summary = get_market_state_summary() or {}
        except Exception as exc:
            LOG.debug("Market state fetch failed: %s", exc)

    if _REC:
        try:
            rec_data = get_latest_recommendations() or {}
        except Exception as exc:
            LOG.debug("Recommendations fetch failed: %s", exc)

    if _ADVISOR:
        try:
            buy_data = get_buy_advisory() or {}
        except Exception as exc:
            LOG.debug("Buy advisory fetch failed: %s", exc)

    # Also load raw data for crude and FX
    crude_data = _load_json("tbl_crude_prices.json")
    fx_data = _load_json("tbl_fx_rates.json")

    # Extract latest crude price
    latest_crude = "N/A"
    if crude_data and isinstance(crude_data, list) and crude_data:
        last = crude_data[-1]
        brent_col = next((k for k in last if "brent" in k.lower()), None)
        if brent_col:
            latest_crude = f"${last[brent_col]}"

    # Extract latest FX rate
    latest_fx = "N/A"
    if fx_data and isinstance(fx_data, list) and fx_data:
        last_fx = fx_data[-1]
        fx_col = next((k for k in last_fx if "usd" in k.lower() and "inr" in k.lower()), None)
        if fx_col is None:
            fx_col = next((k for k in last_fx if "rate" in k.lower() or "close" in k.lower()), None)
        if fx_col:
            latest_fx = f"{last_fx[fx_col]}"

    # Market bias
    bias = market_summary.get("market_bias", market_summary.get("market_direction", "N/A"))
    confidence = market_summary.get("confidence", 0)
    alert_count = market_summary.get("alert_count", market_summary.get("active_alerts", 0))

    # Top recommendation
    top_rec = "N/A"
    if isinstance(rec_data, dict):
        recs = rec_data.get("recommendations", [])
        if recs:
            top_rec = recs[0].get("action", "N/A")
    elif isinstance(rec_data, list) and rec_data:
        top_rec = rec_data[0].get("action", "N/A")

    # Market Bias gauge
    if _PLOTLY and bias != "N/A":
        bias_color = _BIAS_COLORS.get(str(bias).upper(), _GOLD)
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{bias_color},{_NAVY});'
            f'color:white;padding:18px 24px;border-radius:12px;margin-bottom:14px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<div><div style="font-size:1.3rem;font-weight:700;">Market Bias: {bias}</div>'
            f'<div style="font-size:0.82rem;opacity:0.85;">AI Confidence: {confidence}%</div></div>'
            f'<div style="font-size:2rem;font-weight:800;">{confidence}%</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # KPI grid (3x2)
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    row1_c1.metric("Market Bias", str(bias), help="Composite market direction")
    row1_c2.metric("Top Recommendation", str(top_rec), help="Primary action recommendation")
    row1_c3.metric("Active Alerts", str(alert_count), help="Unresolved market alerts")

    row2_c1, row2_c2, row2_c3 = st.columns(3)
    row2_c1.metric("Brent Crude", str(latest_crude), help="Latest Brent crude price")
    row2_c2.metric("USD/INR", str(latest_fx), help="Latest exchange rate")
    row2_c3.metric("AI Confidence", f"{confidence}%", help="Overall AI model confidence")

    # Additional context
    st.markdown("---")
    demand = market_summary.get("demand_outlook", "N/A")
    risk = market_summary.get("risk_level", market_summary.get("supply_risk", "N/A"))
    season = market_summary.get("seasonal_factor", market_summary.get("season", "N/A"))
    action = market_summary.get("recommended_action", "N/A")

    ctx_c1, ctx_c2, ctx_c3, ctx_c4 = st.columns(4)
    ctx_c1.metric("Demand Outlook", str(demand))
    ctx_c2.metric("Risk Level", str(risk))
    ctx_c3.metric("Season", str(season))
    ctx_c4.metric("Rec. Action", str(action))

    # Buy urgency from advisor
    if buy_data:
        urgency = buy_data.get("urgency_score", buy_data.get("urgency_index", None))
        if urgency is not None:
            st.markdown("---")
            urg_c1, urg_c2 = st.columns([1, 3])
            with urg_c1:
                st.metric("Buy Urgency", f"{urgency}%")
            with urg_c2:
                reason = buy_data.get("recommendation", buy_data.get("reason", ""))
                if reason:
                    st.info(f"**Buy Advisory:** {reason}")

    st.caption(f"Last refreshed: {_ist_now()}")


# ── Tab B: System Health ────────────────────────────────────────────────────

def _render_system_health(st) -> None:
    """Engine status table with green/red indicators."""
    st.subheader("Intelligence System Health")

    with st.spinner("Checking engine status..."):
        health_results = _check_engine_health()

    # Summary KPIs
    total = len(health_results)
    online = sum(1 for r in health_results if r["online"])
    offline = total - online
    health_pct = (online / total * 100) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Engines", str(total))
    c2.metric("Online", str(online))
    c3.metric("Offline", str(offline))
    c4.metric("Health", f"{health_pct:.0f}%")

    # Health bar
    bar_color = _GREEN if health_pct >= 80 else _GOLD if health_pct >= 50 else _FIRE
    st.markdown(
        f'<div style="background:#e0d8cc;border-radius:8px;height:12px;margin-bottom:16px;">'
        f'<div style="background:{bar_color};width:{health_pct}%;height:12px;'
        f'border-radius:8px;transition:width 0.5s;"></div></div>',
        unsafe_allow_html=True,
    )

    # Engine status table
    st.markdown("##### Engine Status")
    for result in health_results:
        status_html = _status_indicator(result["online"])
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 12px;border-bottom:1px solid #e0d8cc;">'
            f'<div>'
            f'<span style="font-weight:600;color:{_NAVY};font-size:0.9rem;">'
            f'{result["name"]}</span>'
            f'<br><span style="font-size:0.75rem;color:{_SLATE};">'
            f'{result["description"]}</span>'
            f'</div>'
            f'<div>{status_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # DataFrame view
    if _PANDAS:
        with st.expander("Table View", expanded=False):
            df = pd.DataFrame(health_results)
            df["status"] = df["online"].map({True: "Online", False: "Offline"})
            st.dataframe(
                df[["name", "module", "status", "description"]],
                use_container_width=True,
                hide_index=True,
            )

    # Data file health check
    st.markdown("---")
    st.markdown("##### Data File Status")
    data_files = [
        "tbl_crude_prices.json", "tbl_fx_rates.json",
        "tbl_refinery_production.json", "tbl_news_feed.json",
        "tbl_ports_volume.json", "tbl_weather.json",
        "tbl_imports_countrywise.json", "market_alerts.json",
    ]
    file_results = []
    for fname in data_files:
        path = BASE / fname
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        records = 0
        if exists and size > 0:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = len(data) if isinstance(data, list) else 1
            except Exception:
                pass
        file_results.append({
            "file": fname,
            "exists": exists,
            "size_kb": round(size / 1024, 1),
            "records": records,
        })

    if _PANDAS:
        df_files = pd.DataFrame(file_results)
        df_files["status"] = df_files["exists"].map({True: "OK", False: "Missing"})
        st.dataframe(
            df_files[["file", "status", "size_kb", "records"]].rename(columns={
                "file": "File", "status": "Status",
                "size_kb": "Size (KB)", "records": "Records",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        for fr in file_results:
            status = "OK" if fr["exists"] else "MISSING"
            st.write(f"**{fr['file']}**: {status} ({fr['size_kb']} KB, {fr['records']} records)")

    # Quick links
    st.markdown("---")
    st.markdown("##### Quick Links to Intelligence Pages")
    link_cols = st.columns(4)
    quick_links = [
        ("Global Markets", "global_market_dashboard"),
        ("Refinery Supply", "refinery_supply_dashboard"),
        ("Real-Time Insights", "real_time_insights_dashboard"),
        ("AI Recommendations", "recommendation_dashboard"),
        ("Business Advisor", "business_advisor_dashboard"),
        ("Discussion Guidance", "discussion_guidance_dashboard"),
        ("Market Signals", "market_signals_dashboard"),
        ("Maritime Logistics", "maritime_logistics_dashboard"),
    ]
    for i, (label, _page_key) in enumerate(quick_links):
        with link_cols[i % 4]:
            st.markdown(
                f'<div style="text-align:center;padding:8px;border:1px solid #e0d8cc;'
                f'border-radius:8px;margin-bottom:6px;">'
                f'<span style="font-size:0.82rem;font-weight:600;color:{_NAVY};">'
                f'{label}</span></div>',
                unsafe_allow_html=True,
            )

    st.caption(f"Health check completed: {_ist_now()}")


# ── Main Render ──────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function -- called from dashboard.py routing."""
    import streamlit as st

    st.title("Intelligence Hub")
    st.caption("Central command panel for all AI intelligence engines")

    tabs = st.tabs([
        "Intelligence Overview",
        "System Health",
    ])

    with tabs[0]:
        _render_intelligence_overview(st)

    with tabs[1]:
        _render_system_health(st)
