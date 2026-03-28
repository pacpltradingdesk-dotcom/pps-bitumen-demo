"""
Panel: Purchase Advisor Dashboard
Real-time procurement urgency index with sub-signal breakdown.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime


def render():
    display_badge("calculated")
    """Render the Purchase Advisor Dashboard."""

    st.markdown("""
<div style="background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(153, 27, 27, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">🛒</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Purchase Advisor
</div>
<div style="font-size:0.75rem; color:#fca5a5; letter-spacing:1px; text-transform:uppercase;">
AI-Powered Procurement Urgency • 6-Signal Intelligence
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # ── Compute urgency ──────────────────────────────────────────────────────
    try:
        from purchase_advisor_engine import PurchaseAdvisorEngine
        engine = PurchaseAdvisorEngine()
        result = engine.compute_urgency_index()
        history = engine.get_history()
    except Exception as e:
        st.error(f"Purchase Advisor Engine unavailable: {e}")
        return

    urgency = result["urgency_index"]
    rec = result["recommendation"]
    rec_detail = result["recommendation_detail"]
    rec_color = result["recommendation_color"]
    sub = result["sub_signals"]
    stock_rec = result["stock_recommendation"]
    has_live = result["has_live_data"]

    # ── HERO: Urgency Gauge ──────────────────────────────────────────────────
    urg_color = "#ef4444" if urgency >= 75 else (
        "#f59e0b" if urgency >= 50 else (
        "#3b82f6" if urgency >= 30 else "#22c55e"))

    st.markdown(f"""
<div style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius:15px;
padding:30px; text-align:center; margin-bottom:25px;
box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
<div style="font-size:0.9rem; color:#94a3b8; font-weight:600; letter-spacing:2px;
text-transform:uppercase;">Procurement Urgency Index</div>
<div style="position:relative; margin:20px auto; width:150px; height:150px;">
<svg viewBox="0 0 36 36" style="transform:rotate(-90deg);">
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
fill="none" stroke="#334155" stroke-width="2.5"/>
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
fill="none" stroke="{urg_color}" stroke-width="2.5"
stroke-dasharray="{urgency}, 100" stroke-linecap="round"/>
</svg>
<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);">
<div style="font-size:2.5rem; font-weight:900; color:{urg_color};">{urgency}</div>
<div style="font-size:0.6rem; color:#64748b;">/ 100</div>
</div>
</div>
<div style="font-size:1.4rem; font-weight:800; color:{rec_color}; letter-spacing:1px;">
{rec}
</div>
<div style="font-size:0.8rem; color:#94a3b8; margin-top:8px;">
{rec_detail}
</div>
<div style="font-size:0.65rem; color:#475569; margin-top:12px;">
{'🟢 Live market data' if has_live else '🟡 Using estimated data'} •
Updated {result['timestamp']}
</div>
</div>
""", unsafe_allow_html=True)

    # ── Recommendation Card ──────────────────────────────────────────────────
    rc1, rc2 = st.columns([2, 1])

    with rc1:
        st.markdown(f"""
<div style="background:{rec_color}15; border:2px solid {rec_color}40; border-radius:12px;
padding:15px 20px; margin-bottom:15px;">
<div style="font-size:0.75rem; color:#64748b; font-weight:600;">AI RECOMMENDATION</div>
<div style="font-size:1.5rem; font-weight:900; color:{rec_color}; margin:8px 0;">
{rec}
</div>
<div style="font-size:0.85rem; color:#475569;">{rec_detail}</div>
</div>
""", unsafe_allow_html=True)

    with rc2:
        st.markdown(f"""
<div style="background:#f0fdf4; border:2px solid #bbf7d0; border-radius:12px;
padding:15px 20px; margin-bottom:15px;">
<div style="font-size:0.75rem; color:#64748b; font-weight:600;">📦 STOCK RECOMMENDATION</div>
<div style="font-size:0.9rem; font-weight:700; color:#166534; margin-top:8px;">
{stock_rec}
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Sub-Signal Gauges (2×3 grid) ─────────────────────────────────────────
    st.markdown("### 📊 Signal Breakdown")

    signal_labels = {
        "price_trend": ("Price Trend", "🛢️", "Crude/bitumen price direction"),
        "demand_season": ("Demand Season", "📅", "Seasonal construction demand"),
        "inventory_level": ("Inventory Level", "📦", "Current stock position"),
        "crude_momentum": ("Crude Momentum", "📈", "Oil price momentum (RSI-like)"),
        "fx_pressure": ("FX Pressure", "💵", "USD/INR import cost pressure"),
        "supply_risk": ("Supply Risk", "🚢", "Supply chain disruption risk"),
    }

    row1 = st.columns(3)
    row2 = st.columns(3)
    all_cols = row1 + row2
    signal_keys = list(signal_labels.keys())

    for i, key in enumerate(signal_keys):
        label, icon, desc = signal_labels[key]
        score = sub[key]
        weight = result["weights"].get(key, 0)
        w_pct = int(weight * 100)

        s_color = "#ef4444" if score >= 70 else (
            "#f59e0b" if score >= 40 else "#22c55e")

        with all_cols[i]:
            st.markdown(f"""
<div style="background:white; border-radius:12px; padding:12px; text-align:center;
     box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-bottom:4px solid {s_color};">
<div style="font-size:1.2rem;">{icon}</div>
<div style="font-size:0.7rem; color:#64748b; font-weight:600; text-transform:uppercase;
     letter-spacing:0.3px; margin:4px 0;">{label}</div>
<div style="position:relative; margin:10px auto; width:60px; height:60px;">
<svg viewBox="0 0 36 36" style="transform:rotate(-90deg);">
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
      fill="none" stroke="#e2e8f0" stroke-width="3"/>
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
      fill="none" stroke="{s_color}" stroke-width="3"
      stroke-dasharray="{score}, 100"/>
</svg>
<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
     font-size:1rem; font-weight:800; color:{s_color};">{score}</div>
</div>
<div style="font-size:0.6rem; color:#94a3b8;">Weight: {w_pct}%</div>
</div>
""", unsafe_allow_html=True)
            st.caption(desc)

    st.markdown("---")

    # ── Historical Trend ─────────────────────────────────────────────────────
    if history and len(history) >= 2:
        st.markdown("### 📈 Urgency Trend")
        try:
            import plotly.graph_objects as go
            dates = [h["timestamp"] for h in history]
            values = [h["urgency_index"] for h in history]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, y=values, mode="lines+markers",
                name="Urgency Index",
                line=dict(color="#ef4444", width=2),
                marker=dict(size=5),
            ))
            fig.add_hline(y=80, line_dash="dash", line_color="#ef4444",
                          annotation_text="BUY NOW", annotation_position="top left")
            fig.add_hline(y=60, line_dash="dash", line_color="#f59e0b",
                          annotation_text="PRE-BUY", annotation_position="top left")
            fig.add_hline(y=40, line_dash="dash", line_color="#3b82f6",
                          annotation_text="HOLD", annotation_position="top left")
            fig.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=20, b=20),
                xaxis_title="", yaxis_title="Urgency Index",
                yaxis=dict(range=[0, 100]),
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.caption("Install plotly for trend chart visualization.")
    else:
        st.caption("📊 Historical trend will appear after 2+ advisor runs.")
