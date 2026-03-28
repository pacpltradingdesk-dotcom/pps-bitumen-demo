"""
PPS Anantam -- Real-Time Insights Dashboard v1.0
===================================================
3-tab UI: Live Monitor, Alert History, Disruption Map.
Integrates MarketPulseEngine for live KPIs and alerts, and
maritime_intelligence_engine for Indian port disruption mapping.

Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

LOG = logging.getLogger("real_time_insights_dashboard")

# ── Vastu Design System ─────────────────────────────────────────────────────
_NAVY  = "#1e3a5f"
_GREEN = "#2d6a4f"
_GOLD  = "#c9a84c"
_FIRE  = "#b85c38"
_IVORY = "#faf7f2"

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
    from maritime_intelligence_engine import (
        INDIAN_PORTS,
        PortCongestionMonitor,
    )
    _MARITIME = True
except ImportError:
    _MARITIME = False
    INDIAN_PORTS = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


_BIAS_COLORS = {
    "BULLISH": _GREEN, "BEARISH": _FIRE, "NEUTRAL": _GOLD,
    "UP": _GREEN, "DOWN": _FIRE, "SIDEWAYS": _GOLD,
}

_SEVERITY_COLORS = {
    "P0": "#dc2626", "CRITICAL": "#dc2626",
    "P1": "#d97706", "HIGH": "#d97706", "WARNING": "#d97706",
    "P2": "#2563eb", "MEDIUM": "#2563eb", "INFO": "#2563eb",
    "P3": "#64748b", "LOW": "#64748b",
}

_CONGESTION_COLORS = {
    "Low": _GREEN, "Moderate": _GOLD, "High": _FIRE, "Critical": "#dc2626",
}


# ── Tab A: Live Monitor ────────────────────────────────────────────────────

def _render_live_monitor(st) -> None:
    """Live market state summary with KPI cards."""
    st.subheader("Live Market Monitor")

    if not _PULSE:
        st.warning("market_pulse_engine is not available. Cannot display live data.")
        return

    with st.spinner("Fetching market state..."):
        try:
            summary = get_market_state_summary()
        except Exception as exc:
            LOG.error("Failed to get market state: %s", exc)
            st.error(f"Failed to load market state: {exc}")
            return

    if not summary:
        st.info("No market state data available yet. The engine may still be initialising.")
        return

    # Market bias banner
    bias = summary.get("market_bias") or summary.get("market_direction", "NEUTRAL")
    bias_color = _BIAS_COLORS.get(bias.upper(), _GOLD)
    confidence = summary.get("confidence", 0)

    st.markdown(
        f'<div style="background:linear-gradient(135deg,{bias_color},{_NAVY});'
        f'color:white;padding:18px 24px;border-radius:12px;margin-bottom:14px;">'
        f'<div style="font-size:1.4rem;font-weight:700;">Market Bias: {bias}</div>'
        f'<div style="font-size:0.85rem;opacity:0.85;">Confidence: {confidence}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # KPI cards row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Market Bias",
        bias,
        help="Composite market direction signal from all data streams",
    )
    c2.metric(
        "Crude Trend",
        str(summary.get("crude_trend", summary.get("crude_direction", "N/A"))),
        help="Current crude oil price direction",
    )
    c3.metric(
        "FX Impact",
        str(summary.get("fx_impact", summary.get("currency_pressure", "N/A"))),
        help="Currency impact on import costs",
    )
    alert_count = summary.get("alert_count", summary.get("active_alerts", 0))
    c4.metric(
        "Active Alerts",
        str(alert_count),
        help="Number of unresolved market alerts",
    )

    # Additional KPIs
    st.markdown("---")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Demand Outlook", str(summary.get("demand_outlook", "N/A")))
    c6.metric("Supply Risk", str(summary.get("supply_risk", summary.get("risk_level", "N/A"))))
    c7.metric("Seasonal Factor", str(summary.get("seasonal_factor", summary.get("season", "N/A"))))
    c8.metric("Recommended Action", str(summary.get("recommended_action", "N/A")))

    # Timestamps
    ts = summary.get("computed_at") or summary.get("timestamp", _ist_now())
    st.caption(f"Computed at: {ts}")

    # Refresh
    if st.button("Refresh Monitor", key="rt_refresh_monitor"):
        st.rerun()


# ── Tab B: Alert History ────────────────────────────────────────────────────

def _render_alert_history(st) -> None:
    """Filterable alert history from MarketPulseEngine."""
    st.subheader("Alert History")

    if not _PULSE:
        st.warning("market_pulse_engine is not available.")
        return

    try:
        alerts = get_active_alerts(max_age_hours=72)
    except Exception as exc:
        LOG.error("Failed to get alerts: %s", exc)
        st.error(f"Failed to load alerts: {exc}")
        return

    if not alerts:
        st.success("No active alerts in the last 72 hours. All clear.")
        return

    # Filter controls
    filter_c1, filter_c2 = st.columns(2)
    with filter_c1:
        all_severities = sorted(set(
            a.get("severity", "P2") for a in alerts
        ))
        severity_filter = st.multiselect(
            "Filter by Severity",
            options=all_severities,
            default=all_severities,
            key="rt_sev_filter",
        )
    with filter_c2:
        all_categories = sorted(set(
            a.get("category", "general") for a in alerts
        ))
        category_filter = st.multiselect(
            "Filter by Category",
            options=all_categories,
            default=all_categories,
            key="rt_cat_filter",
        )

    # Apply filters
    filtered = [
        a for a in alerts
        if a.get("severity", "P2") in severity_filter
        and a.get("category", "general") in category_filter
    ]

    st.markdown(f"**{len(filtered)} alert(s)** matching filters (of {len(alerts)} total)")

    if _PANDAS and filtered:
        df_alerts = pd.DataFrame(filtered)
        display_cols = [c for c in [
            "severity", "category", "message", "timestamp",
            "created_at", "source", "impact",
        ] if c in df_alerts.columns]
        if not display_cols:
            display_cols = list(df_alerts.columns[:6])
        st.dataframe(
            df_alerts[display_cols],
            use_container_width=True,
            hide_index=True,
        )
    else:
        for alert in filtered[:30]:
            sev = alert.get("severity", "P2")
            color = _SEVERITY_COLORS.get(sev, "#64748b")
            msg = alert.get("message", "")
            cat = alert.get("category", "")
            ts = alert.get("timestamp") or alert.get("created_at", "")
            st.markdown(
                f'<div style="border-left:4px solid {color};padding:8px 12px;'
                f'margin-bottom:6px;background:rgba(0,0,0,0.02);border-radius:0 4px 4px 0;">'
                f'<span style="font-weight:600;color:{color};">[{sev}]</span> '
                f'<span style="color:#888;font-size:0.8em;">{cat} | {ts}</span>'
                f'<br>{msg}</div>',
                unsafe_allow_html=True,
            )

    st.caption(f"Last refreshed: {_ist_now()}")


# ── Tab C: Disruption Map ──────────────────────────────────────────────────

def _render_disruption_map(st) -> None:
    """Indian port disruption map with congestion colors."""
    st.subheader("Port Disruption Map (India)")

    if not _MARITIME:
        st.warning(
            "maritime_intelligence_engine is not available. "
            "Cannot display port congestion data."
        )
        return

    if not _PLOTLY:
        st.warning("plotly is required for the disruption map.")
        return

    # Compute congestion for all ports
    with st.spinner("Computing port congestion..."):
        try:
            congestion_data = PortCongestionMonitor.get_all_ports()
        except Exception as exc:
            LOG.error("Port congestion computation failed: %s", exc)
            st.error(f"Port congestion computation failed: {exc}")
            return

    if not congestion_data:
        st.info("No port congestion data available.")
        return

    # KPI row
    c1, c2, c3 = st.columns(3)
    scores = [p.get("score", 0) for p in congestion_data]
    avg_score = sum(scores) / len(scores) if scores else 0
    critical_count = sum(1 for s in scores if s >= 70)
    c1.metric("Ports Monitored", f"{len(congestion_data)}")
    c2.metric("Avg Congestion", f"{avg_score:.0f}%")
    c3.metric("Critical Ports", f"{critical_count}")

    # Build scatter_geo
    lats, lons, names, colors_list, sizes, hover_texts = [], [], [], [], [], []
    for port in congestion_data:
        port_name = port.get("port_name", port.get("name", ""))
        port_info = INDIAN_PORTS.get(port_name, {})
        lat = port_info.get("lat") or port.get("lat")
        lon = port_info.get("lon") or port.get("lon")
        if lat is None or lon is None:
            continue

        score = port.get("score", 0)
        if score >= 70:
            level = "Critical"
        elif score >= 45:
            level = "High"
        elif score >= 25:
            level = "Moderate"
        else:
            level = "Low"

        color = _CONGESTION_COLORS.get(level, _GOLD)
        label = port_info.get("label", port_name)

        lats.append(lat)
        lons.append(lon)
        names.append(label)
        colors_list.append(color)
        sizes.append(max(10, min(30, score // 3)))
        hover_texts.append(
            f"<b>{label}</b><br>"
            f"Congestion: {score}%<br>"
            f"Level: {level}<br>"
            f"Type: {port_info.get('type', 'N/A')}"
        )

    if not lats:
        st.info("No port coordinates available for mapping.")
        return

    fig = go.Figure()
    # Group by color for legend
    for level_name, level_color in _CONGESTION_COLORS.items():
        idx = [i for i, c in enumerate(colors_list) if c == level_color]
        if not idx:
            continue
        fig.add_trace(go.Scattergeo(
            lat=[lats[i] for i in idx],
            lon=[lons[i] for i in idx],
            text=[hover_texts[i] for i in idx],
            hoverinfo="text",
            marker=dict(
                size=[sizes[i] for i in idx],
                color=level_color,
                line=dict(width=1, color="white"),
                opacity=0.85,
            ),
            name=level_name,
        ))

    fig.update_geos(
        scope="asia",
        center=dict(lat=20, lon=78),
        projection_scale=3.5,
        showland=True,
        landcolor="#f0ebe1",
        showocean=True,
        oceancolor="#dbeafe",
        showcountries=True,
        countrycolor="#94a3b8",
        showcoastlines=True,
        coastlinecolor="#94a3b8",
    )
    fig.update_layout(
        title="Indian Port Congestion Map",
        height=520,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(
            title="Congestion Level",
            orientation="h",
            yanchor="bottom",
            y=-0.05,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Port status table
    with st.expander("Port Congestion Details", expanded=False):
        if _PANDAS:
            df = pd.DataFrame(congestion_data)
            display_cols = [c for c in [
                "port_name", "name", "score", "level", "risk_level",
                "priority", "type",
            ] if c in df.columns]
            if display_cols:
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            for p in congestion_data:
                st.write(f"**{p.get('port_name', 'N/A')}**: Score {p.get('score', 0)}%")

    st.caption(f"Last updated: {_ist_now()}")


# ── Main Render ──────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function -- called from dashboard.py routing."""
    import streamlit as st

    st.title("Real-Time Insights")
    st.caption("Live market monitoring, alert tracking, and port disruption intelligence")

    tabs = st.tabs([
        "Live Monitor",
        "Alert History",
        "Disruption Map",
    ])

    with tabs[0]:
        _render_live_monitor(st)

    with tabs[1]:
        _render_alert_history(st)

    with tabs[2]:
        _render_disruption_map(st)
