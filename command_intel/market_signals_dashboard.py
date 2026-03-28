"""
PPS Anantam — Market Intelligence Signals Dashboard v1.0
=========================================================
Renders the 10-signal composite intelligence panel.
Master signal banner + 3x3 signal grid + details.
Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import sys
import os
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

_NAVY  = "#1e3a5f"
_GOLD  = "#c9a84c"
_GREEN = "#2d6a4f"
_FIRE  = "#b85c38"
_SLATE = "#64748b"

# ── Color maps ───────────────────────────────────────────────────────────────
_STATUS_COLORS = {
    "UP": _GREEN, "HIGH": _FIRE, "DOWN": _FIRE, "RISING": _GREEN,
    "GROWING": _GREEN, "GOOD": _GREEN, "LOW": _GREEN, "POSITIVE": _GREEN,
    "NEGATIVE": _FIRE, "MEDIUM": _GOLD, "MODERATE": _GOLD, "STABLE": _GOLD,
    "SIDEWAYS": _GOLD, "POOR": _FIRE, "FALLING": _FIRE, "CONTRACTING": _FIRE,
    "WEAK": _FIRE, "STRONG": _GREEN, "NONE": _GREEN, "MINOR": _GOLD,
    "MAJOR": _FIRE,
}

_DIR_ARROWS = {"UP": "▲", "DOWN": "▼", "SIDEWAYS": "►"}

# ── Signal display config ────────────────────────────────────────────────────
_SIGNAL_DEFS = [
    ("crude_market", "Crude Market",         "direction",       "🛢️"),
    ("currency",     "Currency Impact",      "pressure",        "💱"),
    ("weather",      "Weather & Logistics",  "road_condition",  "🌦️"),
    ("news",         "News & Events",        "supply_risk",     "📰"),
    ("govt_infra",   "Govt Infrastructure",  "demand_trend",    "🏗️"),
    ("tenders",      "Tender Demand",        "demand_level",    "📋"),
    ("economic",     "Economic Outlook",     "economic_trend",  "📊"),
    ("search",       "Search Demand",        "demand_interest", "🔍"),
    ("ports",        "Port & Shipping",      "port_risk",       "🚢"),
]


def render():
    """Render the Market Intelligence Signals page."""
    from market_intelligence_engine import MarketIntelligenceEngine

    engine = MarketIntelligenceEngine()

    with st.spinner("Computing market intelligence signals..."):
        signals = engine.compute_all_signals()

    master = signals.get("master", {})

    # ── Master Signal Banner ──────────────────────────────────────────────
    _render_master_banner(master)

    # ── 3×3 Signal Grid ──────────────────────────────────────────────────
    _render_signal_grid(signals)

    # ── Detailed Breakdown ───────────────────────────────────────────────
    _render_signal_details(signals)

    # ── Refresh button ───────────────────────────────────────────────────
    if st.button("🔄 Refresh Signals", key="_mkt_refresh"):
        engine._signals_cache = None
        engine._cache_ts = 0
        st.rerun()


def _render_master_banner(master: dict) -> None:
    """Full-width master signal banner with direction, confidence, action."""
    direction = master.get("market_direction", "SIDEWAYS")
    confidence = master.get("confidence", 50)
    demand = master.get("demand_outlook", "MODERATE")
    risk = master.get("risk_level", "LOW")
    action = master.get("recommended_action", "Computing...")
    score = master.get("weighted_score", 0)
    ts = master.get("computed_at", "")

    dir_color = _STATUS_COLORS.get(direction, _NAVY)
    arrow = _DIR_ARROWS.get(direction, "►")
    demand_color = _STATUS_COLORS.get(demand, _GOLD)
    risk_color = _STATUS_COLORS.get(risk, _GREEN)

    st.markdown(f"""
<div style="background:linear-gradient(135deg,{dir_color},{_NAVY});
            color:white;padding:22px 28px;border-radius:14px;margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <div>
      <div style="font-size:1.6rem;font-weight:800;">
        Market Signal: {direction} {arrow}
      </div>
      <div style="font-size:0.85rem;opacity:0.88;margin-top:6px;">
        {action}
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:2rem;font-weight:700;">{confidence}%</div>
      <div style="font-size:0.7rem;opacity:0.7;">Confidence</div>
    </div>
  </div>
  <div style="display:flex;gap:30px;margin-top:14px;font-size:0.78rem;flex-wrap:wrap;">
    <div>Demand: <span style="font-weight:700;color:{demand_color};">{demand}</span></div>
    <div>Risk: <span style="font-weight:700;color:{risk_color};">{risk}</span></div>
    <div>Score: <b>{score}</b></div>
    <div style="opacity:0.6;margin-left:auto;">{ts}</div>
  </div>
</div>
""", unsafe_allow_html=True)


def _render_signal_grid(signals: dict) -> None:
    """3×3 grid of individual signal cards."""
    for row_start in range(0, 9, 3):
        cols = st.columns(3)
        for idx, col in enumerate(cols):
            i = row_start + idx
            if i >= len(_SIGNAL_DEFS):
                break
            sig_id, label, key_field, icon = _SIGNAL_DEFS[i]
            sig = signals.get(sig_id, {})
            _render_signal_card(col, sig, label, key_field, icon)


def _render_signal_card(col, sig: dict, label: str, key_field: str, icon: str) -> None:
    """Render a single signal card in a column."""
    status_val = sig.get(key_field, "N/A")
    status_color = _STATUS_COLORS.get(str(status_val), _SLATE)
    confidence = sig.get("confidence", "—")
    status = sig.get("status", "N/A")

    # Extra detail line per signal type
    detail = ""
    sig_id = sig.get("signal_id", "")
    if sig_id == "crude_market":
        detail = f"Brent: ${sig.get('latest_brent', '—')} | Mom: {sig.get('momentum', '—')}%"
    elif sig_id == "currency":
        detail = f"USD/INR: {sig.get('latest_usdinr', '—')} | {sig.get('trend', '—')}"
    elif sig_id == "weather":
        prob = sig.get("construction_probability", "—")
        detail = f"Construction Prob: {prob}% | {sig.get('monsoon_factor', '—')}"
    elif sig_id == "news":
        detail = f"Sentiment: {sig.get('sentiment', '—')} | {sig.get('articles_analyzed', 0)} articles"
    elif sig_id == "govt_infra":
        top = sig.get("top_states", [{}])
        top_name = top[0].get("state", "—") if top else "—"
        detail = f"Top: {top_name} | {sig.get('states_analyzed', 0)} states"
    elif sig_id == "tenders":
        detail = f"Found: {sig.get('new_tenders', 0)} | {sig.get('top_state', '—')}"
    elif sig_id == "economic":
        detail = f"GDP: {sig.get('gdp_growth', '—')}% | CPI: {sig.get('cpi', '—')}%"
    elif sig_id == "search":
        detail = f"Score: {sig.get('interest_score', '—')} | {sig.get('signal_strength', '—')}"
    elif sig_id == "ports":
        detail = f"Vol: {sig.get('total_volume_mt', '—'):,} MT" if isinstance(sig.get("total_volume_mt"), (int, float)) else ""

    with col:
        st.markdown(f"""
<div style="border:1px solid #e0d8cc;border-radius:10px;padding:14px;
            border-left:4px solid {status_color};margin-bottom:8px;
            background:#ffffff;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:0.73rem;color:{_SLATE};font-weight:600;">{icon} {label}</span>
    <span style="font-size:0.6rem;color:{_SLATE};background:#f3f0ea;padding:1px 6px;
                 border-radius:8px;">{status}</span>
  </div>
  <div style="font-size:1.25rem;font-weight:700;color:{status_color};margin:6px 0 4px 0;">
    {status_val}
  </div>
  <div style="font-size:0.65rem;color:{_SLATE};">
    Conf: {confidence}%{(' | ' + detail) if detail else ''}
  </div>
</div>
""", unsafe_allow_html=True)


def _render_signal_details(signals: dict) -> None:
    """Expandable signal details with key data points."""
    with st.expander("📊 Signal Weights & Breakdown", expanded=False):
        master = signals.get("master", {})
        summary = master.get("signals_summary", [])
        if summary:
            import pandas as pd
            df = pd.DataFrame(summary)
            df.columns = ["Signal", "Direction Score", "Weight %", "Status"]
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown(f"""
**Composite Score:** {master.get('weighted_score', 0)}
| > 0.2 = UP | < -0.2 = DOWN | else = SIDEWAYS |
""")

    # Individual signal expanders
    with st.expander("🛢️ Crude Market Details", expanded=False):
        sig = signals.get("crude_market", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Direction", sig.get("direction", "—"))
        c2.metric("Momentum", f"{sig.get('momentum', 0)}%")
        c3.metric("Volatility", sig.get("volatility", "—"))
        c1.metric("Brent", f"${sig.get('latest_brent', '—')}")
        c2.metric("Support", f"${sig.get('support', '—')}")
        c3.metric("Resistance", f"${sig.get('resistance', '—')}")

    with st.expander("💱 Currency Impact Details", expanded=False):
        sig = signals.get("currency", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Import Pressure", sig.get("pressure", "—"))
        c2.metric("USD/INR", sig.get("latest_usdinr", "—"))
        c3.metric("FX Momentum", f"{sig.get('fx_momentum', 0)}%")
        st.info(f"💡 **Advice:** {sig.get('advice', '—')}")

    with st.expander("🌦️ Weather & Logistics Details", expanded=False):
        sig = signals.get("weather", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Road Condition", sig.get("road_condition", "—"))
        c2.metric("Construction Prob", f"{sig.get('construction_probability', '—')}%")
        c3.metric("Monsoon", sig.get("monsoon_factor", "—"))
        if sig.get("affected_cities"):
            st.warning(f"⚠️ Affected: {', '.join(sig['affected_cities'])}")
        city_details = sig.get("city_details", {})
        if city_details:
            for city, data in city_details.items():
                st.caption(f"{city}: {data.get('condition', '—')} | Rain: {data.get('rain_mm', 0)}mm | Temp: {data.get('temp', 0)}°C")

    with st.expander("📰 News & Events Details", expanded=False):
        sig = signals.get("news", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Supply Risk", sig.get("supply_risk", "—"))
        c2.metric("Sentiment", sig.get("sentiment", "—"))
        c3.metric("Articles", sig.get("articles_analyzed", 0))
        cats = sig.get("category_counts", {})
        if cats:
            st.caption(f"Refinery: {cats.get('refinery_shutdown', 0)} | Infra: {cats.get('infrastructure', 0)} | Geopolitics: {cats.get('geopolitics', 0)} | Port: {cats.get('port_disruption', 0)}")
        events = sig.get("events", [])
        if events:
            for ev in events[:5]:
                st.markdown(f"- **{ev.get('type', '')}**: {ev.get('headline', '')} _(~{ev.get('impact_days', '?')} days)_")

    with st.expander("🏗️ Govt Infrastructure Details", expanded=False):
        sig = signals.get("govt_infra", {})
        top_states = sig.get("top_states", [])
        if top_states:
            import pandas as pd
            df = pd.DataFrame(top_states[:10])
            st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("📋 Tender Demand Details", expanded=False):
        sig = signals.get("tenders", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Tenders Found", sig.get("new_tenders", 0))
        c2.metric("Top State", sig.get("top_state", "—"))
        c3.metric("Top City", sig.get("top_city", "—"))
        tenders = sig.get("recent_tenders", [])
        if tenders:
            for t in tenders:
                st.caption(f"📄 {t.get('headline', '')} — {t.get('date', '')}")

    with st.expander("📊 Economic & Search & Ports", expanded=False):
        c1, c2, c3 = st.columns(3)
        econ = signals.get("economic", {})
        search = signals.get("search", {})
        ports = signals.get("ports", {})
        c1.metric("GDP Growth", f"{econ.get('gdp_growth', '—')}%")
        c1.metric("CPI", f"{econ.get('cpi', '—')}%")
        c1.metric("Outlook", econ.get("construction_outlook", "—"))
        c2.metric("Search Interest", search.get("demand_interest", "—"))
        c2.metric("Interest Score", search.get("interest_score", "—"))
        c2.metric("Trending", ", ".join(search.get("trending_terms", [])) or "—")
        c3.metric("Port Risk", ports.get("port_risk", "—"))
        c3.metric("Freight Delay", ports.get("freight_delay", "—"))
        c3.metric("Volume Trend", ports.get("volume_trend", "—"))
