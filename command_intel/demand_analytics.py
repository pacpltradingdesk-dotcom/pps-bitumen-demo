"""
Panel 4: Demand & Contractor Analytics
Contractor profiles, consumption patterns, predictive demand, seasonal analysis.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime
import numpy as np

# --- HARDCODED CONTRACTOR DATABASE (fallback if DB unavailable) ---
_HARDCODED_CONTRACTORS = [
    {
        "name": "L&T Construction",
        "project": "Mumbai-Pune Expressway Expansion",
        "location": "Mumbai, Maharashtra",
        "timeline": "Mar 2025 - Dec 2026",
        "consumption_mt_month": 850,
        "credit_days": 30,
        "payment_reliability": 95,
        "total_orders": 42,
        "pending_payment_cr": 2.5,
        "grade": "VG30",
        "type": "Bulk",
        "status": "Active"
    },
    {
        "name": "Tata Projects Ltd",
        "project": "NH-44 Hyderabad Bypass",
        "location": "Hyderabad, Telangana",
        "timeline": "Jun 2025 - Mar 2027",
        "consumption_mt_month": 620,
        "credit_days": 0,
        "payment_reliability": 99,
        "total_orders": 28,
        "pending_payment_cr": 0,
        "grade": "VG30",
        "type": "Bulk",
        "status": "Active"
    },
    {
        "name": "Dilip Buildcon",
        "project": "Bhopal Ring Road Phase 2",
        "location": "Bhopal, Madhya Pradesh",
        "timeline": "Jan 2026 - Jun 2027",
        "consumption_mt_month": 450,
        "credit_days": 15,
        "payment_reliability": 88,
        "total_orders": 15,
        "pending_payment_cr": 1.2,
        "grade": "VG30",
        "type": "Drum",
        "status": "Active"
    },
    {
        "name": "IRB Infrastructure",
        "project": "Gujarat Expressway Maintenance",
        "location": "Ahmedabad, Gujarat",
        "timeline": "Apr 2025 - Sep 2026",
        "consumption_mt_month": 380,
        "credit_days": 7,
        "payment_reliability": 92,
        "total_orders": 35,
        "pending_payment_cr": 0.8,
        "grade": "VG30",
        "type": "Bulk",
        "status": "Active"
    },
    {
        "name": "PNC Infratech",
        "project": "Agra-Lucknow Expressway Extension",
        "location": "Agra, Uttar Pradesh",
        "timeline": "Aug 2025 - Feb 2027",
        "consumption_mt_month": 520,
        "credit_days": 0,
        "payment_reliability": 97,
        "total_orders": 22,
        "pending_payment_cr": 0,
        "grade": "VG10",
        "type": "Bulk",
        "status": "Active"
    },
    {
        "name": "Ashoka Buildcon",
        "project": "Nashik-Sinnar Highway",
        "location": "Nashik, Maharashtra",
        "timeline": "Nov 2025 - Aug 2026",
        "consumption_mt_month": 280,
        "credit_days": 21,
        "payment_reliability": 85,
        "total_orders": 18,
        "pending_payment_cr": 1.5,
        "grade": "VG30",
        "type": "Drum",
        "status": "Active"
    },
    {
        "name": "KNR Constructions",
        "project": "National Highway 65 Widening",
        "location": "Hyderabad, Telangana",
        "timeline": "Feb 2026 - Dec 2027",
        "consumption_mt_month": 700,
        "credit_days": 10,
        "payment_reliability": 91,
        "total_orders": 12,
        "pending_payment_cr": 0.6,
        "grade": "VG30",
        "type": "Bulk",
        "status": "New"
    },
    {
        "name": "G R Infraprojects",
        "project": "Rajasthan Border Road",
        "location": "Udaipur, Rajasthan",
        "timeline": "Jan 2026 - Nov 2027",
        "consumption_mt_month": 350,
        "credit_days": 0,
        "payment_reliability": 96,
        "total_orders": 8,
        "pending_payment_cr": 0,
        "grade": "VG10",
        "type": "Drum",
        "status": "Active"
    }
]


def _load_contractors():
    """Load contractors from DB customers table, fallback to hardcoded list."""
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT name, city, state, grade, payment_terms, "
            "total_orders, total_volume_mt FROM customers"
        ).fetchall()
        conn.close()
        if rows and len(rows) >= 3:
            contractors = []
            for r in rows:
                orders = int(r[5] or 0)
                vol = float(r[6] or 0)
                monthly = round(vol / max(orders, 1)) if orders else 200
                contractors.append({
                    "name": r[0] or "Unknown",
                    "project": "Active Projects",
                    "location": f"{r[1] or ''}, {r[2] or ''}".strip(", "),
                    "timeline": "Ongoing",
                    "consumption_mt_month": monthly,
                    "credit_days": 0 if "advance" in (r[4] or "").lower() else 15,
                    "payment_reliability": 90,
                    "total_orders": orders,
                    "pending_payment_cr": 0,
                    "grade": r[3] or "VG30",
                    "type": "Bulk",
                    "status": "Active"
                })
            return contractors
    except Exception:
        pass
    return list(_HARDCODED_CONTRACTORS)


def _get_demand_factors():
    """Predictive demand factors."""
    month = datetime.date.today().month
    
    highway_active = month in [10, 11, 12, 1, 2, 3, 4, 5]
    monsoon = month in [6, 7, 8, 9]
    try:
        from settings_engine import get as _sg
        _election_years = _sg("election_years", [2024, 2029, 2034])
    except Exception:
        _election_years = [2024, 2029, 2034]
    election_year = datetime.date.today().year in _election_years
    
    return {
        "highway_projects": {
            "label": "Highway Projects Active",
            "value": "Yes — Peak Season" if highway_active else "Reduced — Monsoon",
            "impact": "+20% demand" if highway_active else "-30% demand",
            "color": "#22c55e" if highway_active else "#ef4444",
            "icon": "🛣️"
        },
        "govt_budget": {
            "label": "Government Budget Allocation",
            "value": "₹11.11 Lakh Cr (Roads & Highways FY26)",
            "impact": "+15% YoY growth expected",
            "color": "#22c55e",
            "icon": "🏛️"
        },
        "election_cycle": {
            "label": "Election Cycle Impact",
            "value": "Pre-election push" if election_year else "Normal cycle",
            "impact": "+25% spending" if election_year else "Standard pace",
            "color": "#f59e0b" if election_year else "#94a3b8",
            "icon": "🗳️"
        },
        "monsoon": {
            "label": "Monsoon Impact",
            "value": "Active — Construction halted" if monsoon else "Clear — Full activity",
            "impact": "-40% volume" if monsoon else "+0% (baseline)",
            "color": "#ef4444" if monsoon else "#22c55e",
            "icon": "🌧️"
        }
    }


def render():
    display_badge("historical")
    """Render the Demand & Contractor Analytics panel."""
    
    st.markdown("""
<div style="background: linear-gradient(135deg, #7c2d12 0%, #9a3412 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(154, 52, 18, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">👷</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Demand & Contractor Analytics
</div>
<div style="font-size:0.75rem; color:#fdba74; letter-spacing:1px; text-transform:uppercase;">
Consumption Modeling • Payment Intelligence • Demand Forecasting
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    # --- LOAD CONTRACTORS ---
    CONTRACTORS = _load_contractors()

    # --- SUMMARY METRICS ---
    total_monthly = sum(c["consumption_mt_month"] for c in CONTRACTORS)
    total_pending = sum(c["pending_payment_cr"] for c in CONTRACTORS)
    avg_reliability = np.mean([c["payment_reliability"] for c in CONTRACTORS])
    active = sum(1 for c in CONTRACTORS if c["status"] == "Active")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("📊 Monthly Demand", f"{total_monthly:,} MT")
    with m2:
        st.metric("👷 Active Contractors", f"{active}/{len(CONTRACTORS)}")
    with m3:
        st.metric("💰 Pending Payments", f"{total_pending:.1f} Cr")
    with m4:
        st.metric("⭐ Avg Payment Score", f"{avg_reliability:.0f}%")
    
    st.markdown("---")
    
    # --- PREDICTIVE DEMAND FACTORS ---
    st.markdown("### 🔮 Predictive Demand Factors")
    factors = _get_demand_factors()
    
    f_cols = st.columns(4)
    for i, (key, f) in enumerate(factors.items()):
        with f_cols[i]:
            st.markdown(f"""
<div style="background:white; border-radius:10px; padding:12px; 
border-left:4px solid {f['color']}; box-shadow:0 2px 8px rgba(0,0,0,0.08);
min-height:120px;">
<div style="font-size:1.2rem;">{f['icon']}</div>
<div style="font-weight:600; color:#1e293b; font-size:0.85rem; margin:5px 0;">{f['label']}</div>
<div style="font-size:0.75rem; color:#475569;">{f['value']}</div>
<div style="font-size:0.7rem; color:{f['color']}; font-weight:600; margin-top:5px;">{f['impact']}</div>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- CONTRACTOR PROFILES ---
    st.markdown("### 👷 Contractor Profiles")
    
    # Filter
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        sort_by = st.selectbox("Sort By", ["Consumption (High→Low)", "Payment Reliability", "Pending Payments", "Name"])
    with filter_col2:
        filter_type = st.selectbox("Filter Type", ["All", "Bulk", "Drum"])
    
    # Apply filters
    filtered = CONTRACTORS.copy()
    if filter_type != "All":
        filtered = [c for c in filtered if c["type"] == filter_type]
    
    if sort_by == "Consumption (High→Low)":
        filtered.sort(key=lambda x: x["consumption_mt_month"], reverse=True)
    elif sort_by == "Payment Reliability":
        filtered.sort(key=lambda x: x["payment_reliability"], reverse=True)
    elif sort_by == "Pending Payments":
        filtered.sort(key=lambda x: x["pending_payment_cr"], reverse=True)
    
    for c in filtered:
        # Reliability color
        rel_color = "#22c55e" if c["payment_reliability"] >= 90 else ("#f59e0b" if c["payment_reliability"] >= 80 else "#ef4444")
        
        with st.expander(f"{'🟢' if c['status']=='Active' else '🔵'} {c['name']} — {c['consumption_mt_month']:,} MT/month | ⭐ {c['payment_reliability']}%"):
            cc1, cc2, cc3 = st.columns(3)
            
            with cc1:
                st.markdown("**📋 Project Details**")
                st.caption(f"🏗️ {c['project']}")
                st.caption(f"📍 {c['location']}")
                st.caption(f"📅 {c['timeline']}")
                st.caption(f"🧪 Grade: {c['grade']} | Type: {c['type']}")
            
            with cc2:
                st.markdown("**📊 Consumption**")
                st.metric("Monthly Volume", f"{c['consumption_mt_month']:,} MT")
                st.caption(f"Total Orders: {c['total_orders']}")
                yearly = c["consumption_mt_month"] * 12
                st.caption(f"Annual Estimate: {yearly:,} MT")
            
            with cc3:
                st.markdown("**💰 Payment Profile**")
                st.metric("Reliability Score", f"{c['payment_reliability']}%")
                st.caption(f"Credit Days: {c['credit_days']}")
                st.caption(f"Pending: {c['pending_payment_cr']} Cr")
                
                # Risk badge
                if c["credit_days"] > 15 and c["payment_reliability"] < 90:
                    st.warning("⚠️ Credit Risk — Monitor closely")
                elif c["credit_days"] == 0:
                    st.success("✅ Advance Payment — No Risk")
    
    # --- SEASONAL DEMAND HEATMAP ---
    st.markdown("---")
    st.markdown("### 📅 Seasonal Demand Pattern")
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    demand_pct = [95, 100, 100, 90, 80, 40, 25, 20, 35, 85, 95, 100]
    
    heatmap_html = '<div style="display:flex; gap:4px; margin:10px 0;">'
    for m, d in zip(months, demand_pct):
        if d >= 80:
            bg = "#22c55e"
        elif d >= 50:
            bg = "#f59e0b"
        else:
            bg = "#ef4444"
        
        heatmap_html += f"""
<div style="flex:1; text-align:center; padding:8px 4px; background:{bg}20; 
             border:1px solid {bg}; border-radius:6px;">
<div style="font-size:0.65rem; font-weight:600; color:#475569;">{m}</div>
<div style="font-size:0.9rem; font-weight:700; color:{bg};">{d}%</div>
</div>
        """
    heatmap_html += '</div>'
    
    st.markdown(heatmap_html, unsafe_allow_html=True)
    st.caption("📊 Demand Index: 🟢 High (80%+) | 🟡 Moderate (50-80%) | 🔴 Low (<50%)")
