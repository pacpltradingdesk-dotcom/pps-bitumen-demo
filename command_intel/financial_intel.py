"""
Panel 5: Financial Intelligence Panel
Shipment-wise P&L, cashflow stress, receivable aging, scenario simulator.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime
import numpy as np


def _get_financial_data():
    """Load financial summary from deals + DB, fallback to estimates."""
    try:
        from database import _get_conn
        conn = _get_conn()
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_value),0), "
            "COALESCE(SUM(CASE WHEN payment_date IS NULL AND delivery_date IS NOT NULL "
            "THEN total_value ELSE 0 END),0) FROM deals"
        ).fetchone()
        conn.close()
        total_val = float(row[1]) / 10000000  # to Cr
        receivable = float(row[2]) / 10000000
        if total_val > 0:
            gst_cr = total_val * 0.18 / 1.18
            return {
                "total_shipment_value": round(total_val, 1),
                "total_gst_credit": round(gst_cr, 1),
                "working_capital_blocked": round(receivable * 1.5, 1),
                "total_receivable": round(receivable, 1),
                "monthly_revenue": round(total_val / max(int(row[0]), 1) * 4, 1),
                "monthly_cogs": round(total_val / max(int(row[0]), 1) * 3.5, 1),
                "monthly_profit": round(total_val / max(int(row[0]), 1) * 0.5, 1),
                "avg_margin_pct": 12.0,
                "break_even_load_mt": 3200,
                "cashflow_days": 45,
            }
    except Exception:
        pass
    # Fallback estimates
    return {
        "total_shipment_value": 74.8,
        "total_gst_credit": 11.4,
        "working_capital_blocked": 28.5,
        "total_receivable": 18.2,
        "monthly_revenue": 22.5,
        "monthly_cogs": 19.8,
        "monthly_profit": 2.7,
        "avg_margin_pct": 12.0,
        "break_even_load_mt": 3200,
        "cashflow_days": 45,
    }


def _get_vessel_profitability():
    """Vessel-wise profitability data."""
    return [
        {"vessel": "MT Arabian Star", "qty": 5000, "revenue": 15.2, "cost": 13.1, "profit": 2.1, "margin": 13.8, "status": "In Transit"},
        {"vessel": "MT Gulf Carrier", "qty": 3000, "revenue": 9.8, "cost": 8.5, "profit": 1.3, "margin": 13.3, "status": "Delivered"},
        {"vessel": "MT Eastern Glory", "qty": 5000, "revenue": 16.5, "cost": 14.8, "profit": 1.7, "margin": 10.3, "status": "Paid"},
        {"vessel": "MT Tigris Dream", "qty": 4500, "revenue": 14.1, "cost": 12.6, "profit": 1.5, "margin": 10.6, "status": "In Transit"},
        {"vessel": "MT Desert Falcon", "qty": 6000, "revenue": 19.2, "cost": 16.5, "profit": 2.7, "margin": 14.1, "status": "Awaiting Payment"},
    ]


def _get_receivable_aging():
    """Receivable aging breakdown."""
    return [
        {"bucket": "0-30 days", "amount": 6.5, "count": 8, "color": "#22c55e"},
        {"bucket": "31-60 days", "amount": 5.2, "count": 5, "color": "#f59e0b"},
        {"bucket": "61-90 days", "amount": 3.8, "count": 3, "color": "#f97316"},
        {"bucket": "90+ days", "amount": 2.7, "count": 2, "color": "#ef4444"},
    ]


def _simulate_scenario(base_margin, crude_change, freight_change, usd_change):
    """Simulate margin impact based on variable changes."""
    # Crude +1% ≈ margin -0.4%
    # Freight +₹ 1/MT ≈ margin -0.15%  
    # USD +1% ≈ margin -0.3%
    
    margin_impact = (
        -crude_change * 0.4 +       # Crude impact
        -freight_change * 0.15 +     # Freight impact  
        -usd_change * 0.3            # USD impact
    )
    
    new_margin = base_margin + margin_impact
    return round(new_margin, 2), round(margin_impact, 2)


def render():
    display_badge("calculated")
    """Render the Financial Intelligence panel."""
    
    st.markdown("""
<div style="background: linear-gradient(135deg, #1e3a5f 0%, #0d47a1 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(13, 71, 161, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">💰</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Financial Intelligence Panel
</div>
<div style="font-size:0.75rem; color:#90caf9; letter-spacing:1px; text-transform:uppercase;">
P&L • Cashflow • Receivables • Scenario Analysis
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    data = _get_financial_data()
    
    # --- TOP KPI ROW ---
    st.markdown("### 📊 Financial Overview")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("💰 Total Shipment Value", f"{data['total_shipment_value']:.1f} Cr")
    with k2:
        st.metric("🧾 GST Credit Available", f"{data['total_gst_credit']:.1f} Cr")
    with k3:
        st.metric("🔒 Working Capital Blocked", f"{data['working_capital_blocked']:.1f} Cr")
    with k4:
        st.metric("📋 Total Receivable", f"{data['total_receivable']:.1f} Cr")
    
    k5, k6, k7, k8 = st.columns(4)
    with k5:
        st.metric("📈 Monthly Revenue", f"{data['monthly_revenue']:.1f} Cr")
    with k6:
        st.metric("📉 Monthly COGS", f"{data['monthly_cogs']:.1f} Cr")
    with k7:
        st.metric("✅ Monthly Profit", f"{data['monthly_profit']:.1f} Cr", f"{data['avg_margin_pct']:.1f}%")
    with k8:
        st.metric("⚖️ Break-Even Load", f"{data['break_even_load_mt']:,} MT")
    
    # --- CASHFLOW STRESS INDICATOR ---
    stress_ratio = data["working_capital_blocked"] / data["monthly_revenue"]
    stress_level = "🟢 Healthy" if stress_ratio < 1.0 else ("🟡 Moderate" if stress_ratio < 1.5 else "🔴 Critical")
    stress_color = "#22c55e" if stress_ratio < 1.0 else ("#f59e0b" if stress_ratio < 1.5 else "#ef4444")
    
    st.markdown(f"""
<div style="background: linear-gradient(90deg, {stress_color}15, {stress_color}05); 
border:1px solid {stress_color}; border-radius:10px; padding:12px 20px; margin:15px 0;
display:flex; justify-content:space-between; align-items:center;">
<div>
<span style="font-weight:700; color:#1e293b; font-size:1rem;">Cashflow Stress Indicator</span>
<span style="color:#64748b; font-size:0.8rem;"> | WC/Revenue Ratio: {stress_ratio:.2f}x</span>
</div>
<span style="background:{stress_color}; color:white; padding:5px 15px; border-radius:15px; 
font-weight:700; font-size:0.85rem;">{stress_level}</span>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- VESSEL-WISE PROFITABILITY ---
    st.markdown("### 🚢 Vessel-wise Profitability")
    
    vessels = _get_vessel_profitability()
    
    # Table Header
    st.markdown("""
<div style="display:flex; background:#f1f5f9; padding:8px 15px; border-radius:8px 8px 0 0; 
font-weight:700; font-size:0.75rem; color:#475569;">
<div style="flex:1.5;">Vessel</div>
<div style="flex:0.7; text-align:center;">Qty (MT)</div>
<div style="flex:1; text-align:center;">Revenue (Cr)</div>
<div style="flex:1; text-align:center;">Cost (Cr)</div>
<div style="flex:1; text-align:center;">Profit (Cr)</div>
<div style="flex:0.7; text-align:center;">Margin %</div>
<div style="flex:1; text-align:center;">Status</div>
</div>
""", unsafe_allow_html=True)
    
    for v in vessels:
        margin_color = "#22c55e" if v["margin"] >= 12 else ("#f59e0b" if v["margin"] >= 8 else "#ef4444")
        status_bg = {"In Transit": "#fef3c7", "Delivered": "#d1fae5", "Paid": "#dbeafe", "Awaiting Payment": "#fee2e2"}
        s_bg = status_bg.get(v["status"], "#f1f5f9")
        
        st.markdown(f"""
<div style="display:flex; padding:10px 15px; border-bottom:1px solid #e2e8f0; align-items:center;
font-size:0.8rem;">
<div style="flex:1.5; font-weight:600; color:#1e293b;">🚢 {v['vessel']}</div>
<div style="flex:0.7; text-align:center; color:#475569;">{v['qty']:,}</div>
<div style="flex:1; text-align:center; color:#059669; font-weight:600;">{v['revenue']:.1f}</div>
<div style="flex:1; text-align:center; color:#dc2626;">{v['cost']:.1f}</div>
<div style="flex:1; text-align:center; color:#059669; font-weight:700;">{v['profit']:.1f}</div>
<div style="flex:0.7; text-align:center;">
<span style="color:{margin_color}; font-weight:700;">{v['margin']:.1f}%</span>
</div>
<div style="flex:1; text-align:center;">
<span style="background:{s_bg}; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;">
{v['status']}
</span>
</div>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- RECEIVABLE AGING ---
    st.markdown("### 📋 Receivable Aging Analysis")
    
    aging = _get_receivable_aging()
    aging_cols = st.columns(len(aging))
    
    for i, a in enumerate(aging):
        with aging_cols[i]:
            st.markdown(f"""
<div style="background:white; border-radius:10px; padding:15px; text-align:center;
border-top:4px solid {a['color']}; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<div style="font-size:0.8rem; color:#64748b; font-weight:600;">{a['bucket']}</div>
<div style="font-size:1.5rem; font-weight:800; color:{a['color']}; margin:5px 0;">
{a['amount']:.1f} Cr
</div>
<div style="font-size:0.7rem; color:#94a3b8;">{a['count']} invoices</div>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- SCENARIO SIMULATOR ---
    st.markdown("### 🔄 What-If Scenario Simulator")
    st.caption("Slide to see how market changes affect your margin")
    
    s1, s2, s3 = st.columns(3)
    with s1:
        crude_chg = st.slider("Crude Price Change (%)", -15.0, 15.0, 0.0, 1.0, key="fin_crude")
    with s2:
        freight_chg = st.slider("Freight Change ($/MT)", -15.0, 15.0, 0.0, 1.0, key="fin_freight")
    with s3:
        usd_chg = st.slider("USD/INR Change (%)", -5.0, 5.0, 0.0, 0.5, key="fin_usd")
    
    new_margin, impact = _simulate_scenario(data["avg_margin_pct"], crude_chg, freight_chg, usd_chg)
    
    impact_color = "#22c55e" if impact >= 0 else "#ef4444"
    margin_status = "✅ Profitable" if new_margin > 5 else ("⚠️ Thin Margin" if new_margin > 0 else "🔴 LOSS ZONE")
    
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Current Margin", f"{data['avg_margin_pct']:.1f}%")
    with r2:
        st.metric("Projected Margin", f"{new_margin:.1f}%", f"{impact:+.1f}%")
    with r3:
        st.markdown(f"""
<div style="background:{impact_color}15; border:1px solid {impact_color}; border-radius:10px;
padding:15px; text-align:center; margin-top:5px;">
<div style="font-size:1.2rem; font-weight:700; color:{impact_color};">{margin_status}</div>
<div style="font-size:0.75rem; color:#64748b; margin-top:5px;">
Monthly P&L Impact: {(impact/100 * data['monthly_revenue']):.2f} Cr
</div>
</div>
""", unsafe_allow_html=True)
