"""
PPS Anantam -- Recommendation Dashboard v1.0
===============================================
4-tab UI: Today's Recs, Price Forecast, Demand Forecast, Track Record.
Integrates the RecommendationEngine for buy/sell/hold recommendations,
ml_forecast_engine for crude/FX/demand forecasts, and accuracy tracking.

Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

LOG = logging.getLogger("recommendation_dashboard")

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
    from recommendation_engine import get_latest_recommendations, track_accuracy
    _REC_ENGINE = True
except ImportError:
    _REC_ENGINE = False

try:
    import ml_forecast_engine
    _ML = True
except ImportError:
    _ML = False
    ml_forecast_engine = None  # type: ignore[assignment]

try:
    from interactive_chart_helpers import apply_interactive_defaults, get_chart_config
    _HELPERS = True
except ImportError:
    _HELPERS = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


_ACTION_STYLES = {
    "BUY NOW": {"bg": _GREEN, "icon": "BUY"},
    "BUY":     {"bg": _GREEN, "icon": "BUY"},
    "SELL":    {"bg": _FIRE,  "icon": "SELL"},
    "SELL NOW":{"bg": _FIRE,  "icon": "SELL"},
    "WAIT":    {"bg": _GOLD,  "icon": "WAIT"},
    "HOLD":    {"bg": _GOLD,  "icon": "HOLD"},
}

_KEY_STATES = [
    "Gujarat", "Maharashtra", "Rajasthan", "Madhya Pradesh",
    "Uttar Pradesh", "Karnataka", "Tamil Nadu", "Andhra Pradesh",
    "Telangana", "West Bengal",
]


def _load_json(filename: str) -> Any:
    """Load JSON from project root."""
    path = BASE / filename
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        LOG.warning("Failed to load %s: %s", filename, exc)
    return []


# ── Tab A: Today's Recommendations ─────────────────────────────────────────

def _render_todays_recs(st) -> None:
    """Action cards: BUY NOW / WAIT / SELL with supporting signals."""
    st.subheader("Today's Recommendations")

    if not _REC_ENGINE:
        st.warning("recommendation_engine is not available.")
        return

    with st.spinner("Loading recommendations..."):
        try:
            data = get_latest_recommendations()
        except Exception as exc:
            LOG.error("Failed to get recommendations: %s", exc)
            st.error(f"Failed to load recommendations: {exc}")
            return

    if not data:
        st.info("No recommendations available yet. The engine needs to generate its first batch.")
        return

    # Extract recommendation list (handle both dict and list returns)
    if isinstance(data, dict):
        recs = data.get("recommendations", [])
        summary = data.get("summary", "")
        if summary:
            st.markdown(f"**Summary:** {summary}")
    elif isinstance(data, list):
        recs = data
    else:
        recs = []

    if not recs:
        st.info("No actionable recommendations for today.")
        return

    # Render action cards
    for rec in recs:
        action = str(rec.get("action", "HOLD")).upper()
        style = _ACTION_STYLES.get(action, {"bg": _GOLD, "icon": action})
        confidence = rec.get("confidence", 0)
        reason = rec.get("reason", rec.get("natural_language", ""))
        risk = rec.get("risk_assessment", rec.get("risk", ""))
        alt_action = rec.get("alternative_action", "")
        expires = rec.get("expires_at", "")
        category = rec.get("category", rec.get("type", ""))
        signals = rec.get("supporting_signals", [])

        st.markdown(
            f'<div style="border-left:5px solid {style["bg"]};background:#ffffff;'
            f'padding:16px 20px;border-radius:0 10px 10px 0;margin-bottom:12px;'
            f'box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-size:1.2rem;font-weight:700;color:{style["bg"]};">'
            f'{style["icon"]}</span>'
            f'<span style="font-size:0.8rem;color:#64748b;">{category}</span>'
            f'</div>'
            f'<div style="margin:8px 0;font-size:0.92rem;color:{_NAVY};">{reason}</div>'
            f'<div style="display:flex;gap:20px;font-size:0.78rem;color:#64748b;flex-wrap:wrap;">'
            f'<span>Confidence: <b>{confidence}%</b></span>'
            f'{f"<span>Risk: <b>{risk}</b></span>" if risk else ""}'
            f'{f"<span>Alt: {alt_action}</span>" if alt_action else ""}'
            f'{f"<span>Expires: {expires}</span>" if expires else ""}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if signals:
            with st.expander(f"Supporting Signals ({len(signals)})", expanded=False):
                for sig in signals:
                    if isinstance(sig, dict):
                        st.markdown(f"- **{sig.get('signal', sig.get('name', ''))}**: {sig.get('value', sig.get('detail', ''))}")
                    else:
                        st.markdown(f"- {sig}")

    ts = data.get("generated_at", "") if isinstance(data, dict) else ""
    st.caption(f"Generated: {ts or _ist_now()}")


# ── Tab B: Price Forecast ───────────────────────────────────────────────────

def _render_price_forecast(st) -> None:
    """Crude + FX forecast charts with confidence bands."""
    st.subheader("Price Forecast")

    if not _ML:
        st.info(
            "ml_forecast_engine is not available. "
            "Install required ML dependencies to enable forecasting."
        )
        return

    if not _PLOTLY:
        st.warning("plotly is required for forecast charts.")
        return

    # Crude forecast
    st.markdown("##### Crude Oil Price Forecast")
    try:
        crude_fc = ml_forecast_engine.forecast_crude(horizon_days=15)
    except Exception as exc:
        LOG.debug("Crude forecast failed: %s", exc)
        crude_fc = None

    if crude_fc and _PANDAS:
        fc_data = crude_fc if isinstance(crude_fc, list) else crude_fc.get("forecast", [])
        if fc_data:
            df_fc = pd.DataFrame(fc_data)
            date_col = next((c for c in df_fc.columns if "date" in c.lower() or "ds" in c.lower()), None)
            val_col = next((c for c in df_fc.columns if "yhat" in c.lower() or "forecast" in c.lower() or "price" in c.lower()), None)
            lower_col = next((c for c in df_fc.columns if "lower" in c.lower()), None)
            upper_col = next((c for c in df_fc.columns if "upper" in c.lower()), None)

            if date_col and val_col:
                fig = go.Figure()
                # Confidence band
                if upper_col and lower_col:
                    fig.add_trace(go.Scatter(
                        x=df_fc[date_col], y=df_fc[upper_col],
                        mode="lines", line=dict(width=0),
                        showlegend=False, name="Upper",
                    ))
                    fig.add_trace(go.Scatter(
                        x=df_fc[date_col], y=df_fc[lower_col],
                        mode="lines", line=dict(width=0),
                        fill="tonexty",
                        fillcolor="rgba(30,58,95,0.1)",
                        showlegend=True, name="Confidence Band",
                    ))
                fig.add_trace(go.Scatter(
                    x=df_fc[date_col], y=df_fc[val_col],
                    mode="lines+markers", name="Forecast",
                    line=dict(color=_NAVY, width=2),
                ))
                fig.update_layout(
                    title="Crude Oil Forecast (15-Day)",
                    xaxis_title="Date", yaxis_title="USD / bbl",
                    template="plotly_white", height=380,
                )
                if _HELPERS:
                    fig = apply_interactive_defaults(fig, show_rangeslider=False)
                st.plotly_chart(fig, use_container_width=True,
                                config=get_chart_config() if _HELPERS else {})
            else:
                st.dataframe(df_fc, use_container_width=True, hide_index=True)
        else:
            st.info("No crude forecast data returned.")
    elif crude_fc:
        st.json(crude_fc)
    else:
        st.info("Crude oil forecast is not available at this time.")

    st.markdown("---")

    # FX forecast
    st.markdown("##### USD/INR Forecast")
    try:
        fx_fc = ml_forecast_engine.forecast_fx(horizon_days=15)
    except Exception as exc:
        LOG.debug("FX forecast failed: %s", exc)
        fx_fc = None

    if fx_fc and _PANDAS:
        fc_data = fx_fc if isinstance(fx_fc, list) else fx_fc.get("forecast", [])
        if fc_data:
            df_fx = pd.DataFrame(fc_data)
            date_col = next((c for c in df_fx.columns if "date" in c.lower() or "ds" in c.lower()), None)
            val_col = next((c for c in df_fx.columns if "yhat" in c.lower() or "forecast" in c.lower() or "rate" in c.lower()), None)
            lower_col = next((c for c in df_fx.columns if "lower" in c.lower()), None)
            upper_col = next((c for c in df_fx.columns if "upper" in c.lower()), None)

            if date_col and val_col:
                fig = go.Figure()
                if upper_col and lower_col:
                    fig.add_trace(go.Scatter(
                        x=df_fx[date_col], y=df_fx[upper_col],
                        mode="lines", line=dict(width=0), showlegend=False,
                    ))
                    fig.add_trace(go.Scatter(
                        x=df_fx[date_col], y=df_fx[lower_col],
                        mode="lines", line=dict(width=0),
                        fill="tonexty", fillcolor="rgba(201,168,76,0.12)",
                        name="Confidence Band",
                    ))
                fig.add_trace(go.Scatter(
                    x=df_fx[date_col], y=df_fx[val_col],
                    mode="lines+markers", name="USD/INR Forecast",
                    line=dict(color=_GOLD, width=2),
                ))
                fig.update_layout(
                    title="USD/INR Exchange Rate Forecast (15-Day)",
                    xaxis_title="Date", yaxis_title="INR per USD",
                    template="plotly_white", height=380,
                )
                if _HELPERS:
                    fig = apply_interactive_defaults(fig, show_rangeslider=False, inr_format=True)
                st.plotly_chart(fig, use_container_width=True,
                                config=get_chart_config() if _HELPERS else {})
            else:
                st.dataframe(df_fx, use_container_width=True, hide_index=True)
        else:
            st.info("No FX forecast data returned.")
    elif fx_fc:
        st.json(fx_fc)
    else:
        st.info("FX forecast is not available at this time.")

    st.caption(f"Forecasts generated: {_ist_now()}")


# ── Tab C: Demand Forecast ──────────────────────────────────────────────────

def _render_demand_forecast(st) -> None:
    """State-wise demand heatmap."""
    st.subheader("Demand Forecast by State")

    if not _ML:
        st.info("ml_forecast_engine is not available for demand forecasting.")
        return

    # Attempt to get state-wise demand forecasts
    demand_data: List[dict] = []
    for state in _KEY_STATES:
        try:
            fc = ml_forecast_engine.forecast_state_demand(state)
            if fc:
                entry = fc if isinstance(fc, dict) else {"state": state}
                entry.setdefault("state", state)
                demand_data.append(entry)
        except Exception:
            demand_data.append({"state": state, "forecast": "N/A", "trend": "N/A"})

    if not demand_data:
        st.info("No state-wise demand forecast data available.")
        return

    if _PANDAS:
        df = pd.DataFrame(demand_data)
        state_col = "state"

        # Try to build heatmap
        demand_col = next((c for c in df.columns
                           if "demand" in c.lower() or "forecast" in c.lower()
                           or "index" in c.lower()), None)

        if demand_col and _PLOTLY:
            df[demand_col] = pd.to_numeric(df[demand_col], errors="coerce")
            valid = df.dropna(subset=[demand_col])
            if not valid.empty:
                fig = go.Figure(data=go.Bar(
                    x=valid[state_col],
                    y=valid[demand_col],
                    marker_color=[
                        _GREEN if v > 70 else _GOLD if v > 40 else _FIRE
                        for v in valid[demand_col]
                    ],
                    text=valid[demand_col].round(0),
                    textposition="auto",
                ))
                fig.update_layout(
                    title="State-wise Demand Index",
                    xaxis_title="State", yaxis_title="Demand Index",
                    template="plotly_white", height=400,
                    xaxis=dict(tickangle=-30),
                )
                st.plotly_chart(fig, use_container_width=True)

        # Table view
        st.markdown("##### Detailed Forecast Data")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        for d in demand_data:
            st.write(f"**{d.get('state', 'N/A')}**: {d.get('forecast', 'N/A')}")

    st.caption(f"Last computed: {_ist_now()}")


# ── Tab D: Track Record ────────────────────────────────────────────────────

def _render_track_record(st) -> None:
    """Recommendation accuracy metrics."""
    st.subheader("Recommendation Track Record")

    if not _REC_ENGINE:
        st.warning("recommendation_engine is not available.")
        return

    with st.spinner("Computing accuracy metrics..."):
        try:
            accuracy = track_accuracy()
        except Exception as exc:
            LOG.error("Failed to track accuracy: %s", exc)
            st.error(f"Accuracy tracking failed: {exc}")
            return

    if not accuracy:
        st.info("No accuracy data available yet. Recommendations need time to mature for validation.")
        return

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Overall Accuracy",
        f"{accuracy.get('overall_accuracy', accuracy.get('accuracy_pct', 0)):.1f}%",
        help="Percentage of recommendations that were directionally correct",
    )
    c2.metric(
        "Total Evaluated",
        str(accuracy.get("total_evaluated", accuracy.get("total", 0))),
    )
    c3.metric(
        "Correct Calls",
        str(accuracy.get("correct", 0)),
    )
    c4.metric(
        "Avg Confidence",
        f"{accuracy.get('avg_confidence', 0):.0f}%",
    )

    # Breakdown by type
    by_type = accuracy.get("by_type", accuracy.get("breakdown", {}))
    if by_type and _PANDAS:
        st.markdown("##### Accuracy by Recommendation Type")
        if isinstance(by_type, dict):
            rows = []
            for rtype, data in by_type.items():
                if isinstance(data, dict):
                    rows.append({"Type": rtype, **data})
                else:
                    rows.append({"Type": rtype, "Accuracy": data})
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        elif isinstance(by_type, list):
            df = pd.DataFrame(by_type)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Recent evaluations
    history = accuracy.get("recent_evaluations", accuracy.get("history", []))
    if history:
        with st.expander(f"Recent Evaluations ({len(history)})", expanded=False):
            if _PANDAS:
                df_hist = pd.DataFrame(history[:20])
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else:
                for h in history[:10]:
                    st.write(h)

    st.caption(f"Last computed: {_ist_now()}")


# ── Main Render ──────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function -- called from dashboard.py routing."""
    import streamlit as st

    st.title("AI Recommendations")
    st.caption("Data-driven buy/sell/hold recommendations with forecasting and accuracy tracking")

    tabs = st.tabs([
        "Today's Recs",
        "Price Forecast",
        "Demand Forecast",
        "Track Record",
    ])

    with tabs[0]:
        _render_todays_recs(st)

    with tabs[1]:
        _render_price_forecast(st)

    with tabs[2]:
        _render_demand_forecast(st)

    with tabs[3]:
        _render_track_record(st)
