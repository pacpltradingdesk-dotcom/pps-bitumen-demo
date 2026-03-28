"""
PPS Anantam -- Business Advisor Dashboard v1.0
=================================================
4-tab UI: Buy Advisory, Sell Advisory, Market Timing, Risk Dashboard.
Integrates BusinessAdvisor engine for proactive buy/sell guidance,
IOCL fortnightly revision tracking, and multi-dimensional risk assessment.

Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

LOG = logging.getLogger("business_advisor_dashboard")

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
    from business_advisor_engine import (
        get_buy_advisory,
        get_sell_advisory,
        get_timing_advisory,
    )
    _ADVISOR = True
except ImportError:
    _ADVISOR = False

try:
    from interactive_chart_helpers import apply_interactive_defaults, get_chart_config
    _HELPERS = True
except ImportError:
    _HELPERS = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


_URGENCY_COLORS = {
    "CRITICAL": "#dc2626", "HIGH": _FIRE, "MEDIUM": _GOLD,
    "LOW": _GREEN, "NONE": _SLATE,
}

_RISK_COLORS = {
    "CRITICAL": "#dc2626", "HIGH": _FIRE, "ELEVATED": "#e67e22",
    "MEDIUM": _GOLD, "MODERATE": _GOLD,
    "LOW": _GREEN, "MINIMAL": _GREEN, "NONE": _SLATE,
}


def _render_urgency_gauge(st, urgency_score: float, label: str = "Buy Urgency") -> None:
    """Render a gauge chart showing urgency level (0-100)."""
    if not _PLOTLY:
        st.metric(label, f"{urgency_score:.0f}/100")
        return

    if urgency_score >= 80:
        bar_color = "#dc2626"
    elif urgency_score >= 60:
        bar_color = _FIRE
    elif urgency_score >= 40:
        bar_color = _GOLD
    else:
        bar_color = _GREEN

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=urgency_score,
        title={"text": label, "font": {"size": 14, "color": _NAVY}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": bar_color},
            "bgcolor": "white",
            "steps": [
                {"range": [0, 30], "color": "rgba(45,106,79,0.15)"},
                {"range": [30, 60], "color": "rgba(201,168,76,0.15)"},
                {"range": [60, 80], "color": "rgba(184,92,56,0.15)"},
                {"range": [80, 100], "color": "rgba(220,38,38,0.15)"},
            ],
        },
        number={"suffix": "%", "font": {"size": 28}},
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _render_risk_badge(level: str) -> str:
    """Return HTML for a colored risk badge."""
    color = _RISK_COLORS.get(level.upper(), _SLATE)
    return (
        f'<span style="background:{color};color:white;padding:3px 10px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:600;">{level}</span>'
    )


# ── Tab A: Buy Advisory ────────────────────────────────────────────────────

def _render_buy_advisory(st) -> None:
    """Buy urgency gauge + ranked sources table."""
    st.subheader("Buy Advisory")

    if not _ADVISOR:
        st.warning("business_advisor_engine is not available.")
        return

    with st.spinner("Computing buy advisory..."):
        try:
            advisory = get_buy_advisory()
        except Exception as exc:
            LOG.error("Buy advisory failed: %s", exc)
            st.error(f"Failed to load buy advisory: {exc}")
            return

    if not advisory:
        st.info("No buy advisory available at this time.")
        return

    # Urgency gauge
    urgency = advisory.get("urgency_score", advisory.get("urgency_index", 50))
    urgency_label = advisory.get("urgency_level", "MEDIUM")
    gauge_c, info_c = st.columns([1, 2])
    with gauge_c:
        _render_urgency_gauge(st, urgency, label="Buy Urgency")
    with info_c:
        st.markdown(f"**Urgency Level:** {urgency_label}")
        st.markdown(f"**Recommendation:** {advisory.get('recommendation', advisory.get('action', 'N/A'))}")
        reason = advisory.get("reason", advisory.get("rationale", ""))
        if reason:
            st.markdown(f"**Rationale:** {reason}")
        window = advisory.get("optimal_window", advisory.get("buy_window", ""))
        if window:
            st.markdown(f"**Optimal Window:** {window}")

    st.markdown("---")

    # Ranked sources table
    sources = advisory.get("ranked_sources", advisory.get("sources", []))
    if sources:
        st.markdown("##### Recommended Sources (Ranked)")
        if _PANDAS:
            df_src = pd.DataFrame(sources)
            display_cols = [c for c in [
                "rank", "name", "supplier", "source", "type",
                "landed_cost", "price", "margin", "score",
                "advantage", "city", "state",
            ] if c in df_src.columns]
            if display_cols:
                st.dataframe(
                    df_src[display_cols],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.dataframe(df_src, use_container_width=True, hide_index=True)
        else:
            for i, src in enumerate(sources[:10], 1):
                name = src.get("name") or src.get("supplier", f"Source #{i}")
                cost = src.get("landed_cost") or src.get("price", "N/A")
                st.write(f"{i}. **{name}** -- Cost: {cost}")
    else:
        st.info("No source ranking data available.")

    # Supporting signals
    signals = advisory.get("supporting_signals", advisory.get("signals", []))
    if signals:
        with st.expander("Supporting Signals", expanded=False):
            for sig in signals:
                if isinstance(sig, dict):
                    st.markdown(f"- **{sig.get('signal', sig.get('name', ''))}**: {sig.get('value', sig.get('detail', ''))}")
                else:
                    st.markdown(f"- {sig}")

    st.caption(f"Generated: {advisory.get('generated_at', _ist_now())}")


# ── Tab B: Sell Advisory ────────────────────────────────────────────────────

def _render_sell_advisory(st) -> None:
    """Priority customer list with 3-tier pricing."""
    st.subheader("Sell Advisory")

    if not _ADVISOR:
        st.warning("business_advisor_engine is not available.")
        return

    with st.spinner("Computing sell advisory..."):
        try:
            advisory = get_sell_advisory()
        except Exception as exc:
            LOG.error("Sell advisory failed: %s", exc)
            st.error(f"Failed to load sell advisory: {exc}")
            return

    if not advisory:
        st.info("No sell advisory available at this time.")
        return

    # Summary KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Market Condition",
        str(advisory.get("market_condition", advisory.get("market_state", "N/A"))),
    )
    c2.metric(
        "Sell Priority",
        str(advisory.get("sell_priority", advisory.get("priority", "N/A"))),
    )
    c3.metric(
        "Customers Targeted",
        str(advisory.get("customer_count", len(advisory.get("customers", [])))),
    )

    # 3-tier pricing summary
    pricing = advisory.get("pricing_tiers", advisory.get("tiers", {}))
    if pricing:
        st.markdown("##### 3-Tier Pricing")
        tier_c1, tier_c2, tier_c3 = st.columns(3)
        if isinstance(pricing, dict):
            agg = pricing.get("aggressive", pricing.get("tier_1", {}))
            bal = pricing.get("balanced", pricing.get("tier_2", {}))
            prem = pricing.get("premium", pricing.get("tier_3", {}))
            tier_c1.metric(
                "Aggressive",
                f"Rs {agg.get('price', agg) if isinstance(agg, dict) else agg}/MT",
            )
            tier_c2.metric(
                "Balanced",
                f"Rs {bal.get('price', bal) if isinstance(bal, dict) else bal}/MT",
            )
            tier_c3.metric(
                "Premium",
                f"Rs {prem.get('price', prem) if isinstance(prem, dict) else prem}/MT",
            )

    st.markdown("---")

    # Priority customer list
    customers = advisory.get("customers", advisory.get("priority_customers", []))
    if customers:
        st.markdown("##### Priority Customers")
        if _PANDAS:
            df_cust = pd.DataFrame(customers)
            display_cols = [c for c in [
                "rank", "name", "customer", "city", "state", "segment",
                "last_contact", "recommended_price", "tier",
                "potential_qty", "priority_score",
            ] if c in df_cust.columns]
            if display_cols:
                st.dataframe(
                    df_cust[display_cols],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.dataframe(df_cust, use_container_width=True, hide_index=True)
        else:
            for cust in customers[:10]:
                name = cust.get("name") or cust.get("customer", "N/A")
                st.write(f"- **{name}** ({cust.get('city', '')}, {cust.get('state', '')})")
    else:
        st.info("No priority customer data available.")

    reason = advisory.get("rationale", advisory.get("reason", ""))
    if reason:
        st.info(f"**Rationale:** {reason}")

    st.caption(f"Generated: {advisory.get('generated_at', _ist_now())}")


# ── Tab C: Market Timing ───────────────────────────────────────────────────

def _render_market_timing(st) -> None:
    """IOCL revision tracker + forecast chart."""
    st.subheader("Market Timing Advisory")

    if not _ADVISOR:
        st.warning("business_advisor_engine is not available.")
        return

    with st.spinner("Computing timing advisory..."):
        try:
            advisory = get_timing_advisory()
        except Exception as exc:
            LOG.error("Timing advisory failed: %s", exc)
            st.error(f"Failed to load timing advisory: {exc}")
            return

    if not advisory:
        st.info("No timing advisory available at this time.")
        return

    # Revision tracker
    st.markdown("##### IOCL Fortnightly Revision Tracker")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Next Revision", str(advisory.get("next_revision_date", "N/A")))
    c2.metric("Days Until", str(advisory.get("days_until_revision", "N/A")))
    c3.metric(
        "Expected Direction",
        str(advisory.get("expected_direction", advisory.get("price_direction", "N/A"))),
    )
    c4.metric(
        "Confidence",
        f"{advisory.get('direction_confidence', advisory.get('confidence', 0))}%",
    )

    # Action recommendation
    action = advisory.get("timing_recommendation", advisory.get("recommendation", ""))
    if action:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{_NAVY},{_GREEN});'
            f'color:white;padding:14px 20px;border-radius:10px;margin:12px 0;">'
            f'<div style="font-size:0.8rem;opacity:0.8;">Timing Recommendation</div>'
            f'<div style="font-size:1.1rem;font-weight:700;">{action}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Price trend forecast chart
    forecast = advisory.get("price_forecast", advisory.get("forecast", []))
    if forecast and _PANDAS and _PLOTLY:
        st.markdown("##### Price Trend Forecast")
        df_fc = pd.DataFrame(forecast) if isinstance(forecast, list) else pd.DataFrame()
        if not df_fc.empty:
            date_col = next((c for c in df_fc.columns if "date" in c.lower()), None)
            price_col = next((c for c in df_fc.columns if "price" in c.lower() or "value" in c.lower()), None)
            if date_col and price_col:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_fc[date_col], y=df_fc[price_col],
                    mode="lines+markers", name="Price Forecast",
                    line=dict(color=_NAVY, width=2),
                ))
                fig.update_layout(
                    title="Bitumen Price Forecast",
                    xaxis_title="Date", yaxis_title="Rs / MT",
                    template="plotly_white", height=350,
                )
                if _HELPERS:
                    fig = apply_interactive_defaults(fig, show_rangeslider=False)
                st.plotly_chart(fig, use_container_width=True,
                                config=get_chart_config() if _HELPERS else {})
            else:
                st.dataframe(df_fc, use_container_width=True, hide_index=True)

    # Revision history
    history = advisory.get("revision_history", advisory.get("past_revisions", []))
    if history:
        with st.expander("Recent Revision History", expanded=False):
            if _PANDAS:
                st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
            else:
                for h in history[:5]:
                    st.write(h)

    # Reasoning
    reasoning = advisory.get("reasoning", advisory.get("rationale", ""))
    if reasoning:
        with st.expander("Detailed Reasoning", expanded=False):
            if isinstance(reasoning, list):
                for r in reasoning:
                    st.markdown(f"- {r}")
            else:
                st.markdown(str(reasoning))

    st.caption(f"Generated: {advisory.get('generated_at', _ist_now())}")


# ── Tab D: Risk Dashboard ──────────────────────────────────────────────────

def _render_risk_dashboard(st) -> None:
    """Supply, FX, credit, and seasonal risk levels as colored badges."""
    st.subheader("Risk Dashboard")

    # Build risk data from all advisories
    risks: Dict[str, Dict[str, str]] = {}

    # Try to extract risk info from each advisory
    if _ADVISOR:
        try:
            buy = get_buy_advisory()
            if buy:
                for key in ("supply_risk", "procurement_risk"):
                    if key in buy:
                        risks["Supply Risk"] = {"level": str(buy[key]), "source": "Buy Advisory"}
        except Exception:
            pass

        try:
            sell = get_sell_advisory()
            if sell:
                for key in ("credit_risk", "payment_risk"):
                    if key in sell:
                        risks["Credit Risk"] = {"level": str(sell[key]), "source": "Sell Advisory"}
        except Exception:
            pass

        try:
            timing = get_timing_advisory()
            if timing:
                for key in ("fx_risk", "currency_risk"):
                    if key in timing:
                        risks["FX Risk"] = {"level": str(timing[key]), "source": "Timing Advisory"}
                for key in ("seasonal_risk", "demand_risk"):
                    if key in timing:
                        risks["Seasonal Risk"] = {"level": str(timing[key]), "source": "Timing Advisory"}
                # Price volatility
                for key in ("volatility_risk", "price_risk"):
                    if key in timing:
                        risks["Price Volatility"] = {"level": str(timing[key]), "source": "Timing Advisory"}
        except Exception:
            pass

    # Default risks if engines didn't provide them
    default_risks = {
        "Supply Risk": {"level": "MEDIUM", "source": "Default"},
        "FX Risk": {"level": "MEDIUM", "source": "Default"},
        "Credit Risk": {"level": "LOW", "source": "Default"},
        "Seasonal Risk": {"level": "MEDIUM", "source": "Default"},
        "Price Volatility": {"level": "MEDIUM", "source": "Default"},
        "Logistics Risk": {"level": "LOW", "source": "Default"},
    }
    for k, v in default_risks.items():
        risks.setdefault(k, v)

    # Risk grid (2 columns)
    cols = st.columns(2)
    for i, (risk_name, risk_info) in enumerate(risks.items()):
        with cols[i % 2]:
            level = risk_info.get("level", "MEDIUM").upper()
            color = _RISK_COLORS.get(level, _SLATE)
            source = risk_info.get("source", "")
            st.markdown(
                f'<div style="border:1px solid #e0d8cc;border-radius:10px;padding:14px;'
                f'border-left:4px solid {color};margin-bottom:10px;background:#ffffff;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-size:0.85rem;font-weight:600;color:{_NAVY};">{risk_name}</span>'
                f'{_render_risk_badge(level)}'
                f'</div>'
                f'<div style="font-size:0.7rem;color:{_SLATE};margin-top:4px;">Source: {source}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Risk matrix visualisation
    if _PLOTLY and risks:
        st.markdown("---")
        st.markdown("##### Risk Level Summary")
        level_order = {"LOW": 1, "MINIMAL": 1, "NONE": 0, "MODERATE": 2, "MEDIUM": 2, "ELEVATED": 3, "HIGH": 3, "CRITICAL": 4}
        names = list(risks.keys())
        values = [level_order.get(risks[n]["level"].upper(), 2) for n in names]
        colors = [_RISK_COLORS.get(risks[n]["level"].upper(), _SLATE) for n in names]

        fig = go.Figure(data=go.Bar(
            x=names,
            y=values,
            marker_color=colors,
            text=[risks[n]["level"] for n in names],
            textposition="auto",
        ))
        fig.update_layout(
            title="Risk Level Overview",
            yaxis=dict(
                tickvals=[0, 1, 2, 3, 4],
                ticktext=["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
                range=[0, 4.5],
            ),
            template="plotly_white", height=320,
            xaxis=dict(tickangle=-20),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Last assessed: {_ist_now()}")


# ── Main Render ──────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function -- called from dashboard.py routing."""
    import streamlit as st

    st.title("Business Advisor")
    st.caption("AI-powered buy/sell advisory, market timing, and risk assessment")

    tabs = st.tabs([
        "Buy Advisory",
        "Sell Advisory",
        "Market Timing",
        "Risk Dashboard",
    ])

    with tabs[0]:
        _render_buy_advisory(st)

    with tabs[1]:
        _render_sell_advisory(st)

    with tabs[2]:
        _render_market_timing(st)

    with tabs[3]:
        _render_risk_dashboard(st)
