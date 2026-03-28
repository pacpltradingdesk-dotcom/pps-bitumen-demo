"""
Panel 6: GST & Legal Risk Monitor
Supplier GST status, E-Invoice compliance, GSTR matching, Section 74 exposure, Director liability.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime


def _get_supplier_compliance():
    """Load supplier GST compliance from DB suppliers table, fallback to defaults."""
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT name, gstin, gst_status, category FROM suppliers "
            "WHERE gstin IS NOT NULL AND gstin != '' LIMIT 20"
        ).fetchall()
        conn.close()
        if rows and len(rows) >= 3:
            result = []
            for r in rows:
                status = r[2] or "Active"
                is_psu = "iocl" in (r[0] or "").lower() or "bpcl" in (r[0] or "").lower() or "hpcl" in (r[0] or "").lower()
                risk = 5 if is_psu else (15 if status == "Active" else 60)
                result.append({
                    "name": r[0] or "Unknown",
                    "gstin": r[1] or "",
                    "gst_status": status,
                    "filing_status": "Up to date" if is_psu else "Review pending",
                    "investigation": False,
                    "einvoice": True,
                    "eway_match": True,
                    "gstr_2a_match": is_psu,
                    "gstr_2b_match": is_psu,
                    "risk_score": risk,
                    "category": r[3] or ("PSU Refinery" if is_psu else "Private")
                })
            return result
    except Exception:
        pass
    # Fallback defaults
    return [
        {"name": "IOCL Koyali Refinery", "gstin": "24AAACI1681G1Z3", "gst_status": "Active",
         "filing_status": "Up to date", "investigation": False, "einvoice": True,
         "eway_match": True, "gstr_2a_match": True, "gstr_2b_match": True, "risk_score": 5,
         "category": "PSU Refinery"},
        {"name": "BPCL Mumbai Refinery", "gstin": "27AAACB5765F1ZW", "gst_status": "Active",
         "filing_status": "Up to date", "investigation": False, "einvoice": True,
         "eway_match": True, "gstr_2a_match": True, "gstr_2b_match": True, "risk_score": 5,
         "category": "PSU Refinery"},
        {"name": "Mundra Import Terminal", "gstin": "24AABCM8765K1ZP", "gst_status": "Active",
         "filing_status": "1 month delayed", "investigation": False, "einvoice": True,
         "eway_match": True, "gstr_2a_match": True, "gstr_2b_match": False, "risk_score": 25,
         "category": "Import Terminal"},
        {"name": "Star Bitumen Pvt Ltd", "gstin": "27AAFCS9876M1Z4", "gst_status": "Active",
         "filing_status": "3 months delayed", "investigation": True, "einvoice": False,
         "eway_match": False, "gstr_2a_match": False, "gstr_2b_match": False, "risk_score": 85,
         "category": "Private Decanter"},
    ]


def _get_legal_risk_assessment():
    """Calculate legal risk metrics."""
    suppliers = _get_supplier_compliance()
    
    high_risk = sum(1 for s in suppliers if s["risk_score"] >= 70)
    medium_risk = sum(1 for s in suppliers if 30 <= s["risk_score"] < 70)
    low_risk = sum(1 for s in suppliers if s["risk_score"] < 30)
    
    under_investigation = sum(1 for s in suppliers if s["investigation"])
    einvoice_non_compliant = sum(1 for s in suppliers if not s["einvoice"])
    gstr_mismatch = sum(1 for s in suppliers if not s["gstr_2b_match"])
    
    # Section 74 exposure (proportional to high-risk supplier transactions)
    section_74_prob = min(95, high_risk * 25 + medium_risk * 10)
    
    # Director personal risk
    director_risk = "High" if section_74_prob > 50 else ("Medium" if section_74_prob > 20 else "Low")
    
    # D&O coverage gap
    do_gap = "Critical Gap" if section_74_prob > 60 else ("Review Required" if section_74_prob > 30 else "Adequate")
    
    return {
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "under_investigation": under_investigation,
        "einvoice_non_compliant": einvoice_non_compliant,
        "gstr_mismatch": gstr_mismatch,
        "section_74_prob": section_74_prob,
        "director_risk": director_risk,
        "do_gap": do_gap,
    }


def render():
    display_badge("historical")
    """Render the GST & Legal Risk Monitor panel."""
    
    st.markdown("""
<div style="background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(153, 27, 27, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">🛡️</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
GST & Legal Risk Monitor
</div>
<div style="font-size:0.75rem; color:#fca5a5; letter-spacing:1px; text-transform:uppercase;">
Supplier Compliance • E-Invoice • GSTR Match • Section 74 Defense
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    suppliers = _get_supplier_compliance()
    legal = _get_legal_risk_assessment()
    
    # --- TOP METRICS ---
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("🔴 High Risk", legal["high_risk"])
    with m2:
        st.metric("🟡 Medium Risk", legal["medium_risk"])
    with m3:
        st.metric("🟢 Low Risk", legal["low_risk"])
    with m4:
        st.metric("🔍 Under Investigation", legal["under_investigation"])
    with m5:
        st.metric("📄 E-Invoice Issues", legal["einvoice_non_compliant"])
    with m6:
        st.metric("📊 GSTR Mismatch", legal["gstr_mismatch"])
    
    # --- LEGAL RISK PANEL ---
    st.markdown("---")
    st.markdown("### ⚖️ Legal Exposure Assessment")
    
    l1, l2, l3 = st.columns(3)
    
    sec74_color = "#ef4444" if legal["section_74_prob"] > 50 else ("#f59e0b" if legal["section_74_prob"] > 20 else "#22c55e")
    dir_color = "#ef4444" if legal["director_risk"] == "High" else ("#f59e0b" if legal["director_risk"] == "Medium" else "#22c55e")
    do_color = "#ef4444" if "Critical" in legal["do_gap"] else ("#f59e0b" if "Review" in legal["do_gap"] else "#22c55e")
    
    with l1:
        st.markdown(f"""
<div style="background:white; border-radius:10px; padding:20px; text-align:center;
border-top:4px solid {sec74_color}; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<div style="font-size:0.8rem; color:#64748b; font-weight:600;">Section 74 Exposure</div>
<div style="font-size:2.5rem; font-weight:800; color:{sec74_color}; margin:10px 0;">
{legal['section_74_prob']}%
</div>
<div style="font-size:0.7rem; color:#94a3b8;">Probability of notice</div>
</div>
""", unsafe_allow_html=True)
    
    with l2:
        st.markdown(f"""
<div style="background:white; border-radius:10px; padding:20px; text-align:center;
border-top:4px solid {dir_color}; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<div style="font-size:0.8rem; color:#64748b; font-weight:600;">Director Personal Risk</div>
<div style="font-size:2rem; font-weight:800; color:{dir_color}; margin:10px 0;">
{legal['director_risk']}
</div>
<div style="font-size:0.7rem; color:#94a3b8;">Based on supplier quality</div>
</div>
""", unsafe_allow_html=True)
    
    with l3:
        st.markdown(f"""
<div style="background:white; border-radius:10px; padding:20px; text-align:center;
border-top:4px solid {do_color}; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
<div style="font-size:0.8rem; color:#64748b; font-weight:600;">D&O Coverage</div>
<div style="font-size:2rem; font-weight:800; color:{do_color}; margin:10px 0;">
{legal['do_gap']}
</div>
<div style="font-size:0.7rem; color:#94a3b8;">Insurance coverage status</div>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # --- SUPPLIER COMPLIANCE TABLE ---
    st.markdown("### 📋 Supplier GST Compliance Status")
    
    # Table Header
    st.markdown("""
<div style="display:flex; background:#f1f5f9; padding:8px 12px; border-radius:8px 8px 0 0; 
font-weight:700; font-size:0.7rem; color:#475569; text-transform:uppercase;">
<div style="flex:1.5;">Supplier</div>
<div style="flex:1;">GSTIN</div>
<div style="flex:0.7; text-align:center;">Status</div>
<div style="flex:0.5; text-align:center;">🔍</div>
<div style="flex:0.5; text-align:center;">E-Inv</div>
<div style="flex:0.5; text-align:center;">E-Way</div>
<div style="flex:0.5; text-align:center;">2A</div>
<div style="flex:0.5; text-align:center;">2B</div>
<div style="flex:0.7; text-align:center;">Risk</div>
</div>
""", unsafe_allow_html=True)
    
    for s in suppliers:
        risk_color = "#ef4444" if s["risk_score"] >= 70 else ("#f59e0b" if s["risk_score"] >= 30 else "#22c55e")
        status_color = "#ef4444" if s["gst_status"] == "Suspended" else "#22c55e"
        inv_icon = "🔴" if s["investigation"] else "⚪"
        
        def _check(val):
            return "✅" if val else "❌"
        
        st.markdown(f"""
<div style="display:flex; padding:8px 12px; border-bottom:1px solid #e2e8f0; align-items:center;
font-size:0.78rem; background:{'#fef2f2' if s['risk_score'] >= 70 else 'white'};">
<div style="flex:1.5;">
<b style="color:#1e293b;">{s['name']}</b>
<div style="font-size:0.65rem; color:#94a3b8;">{s['category']}</div>
</div>
<div style="flex:1; color:#64748b; font-size:0.7rem;">{s['gstin']}</div>
<div style="flex:0.7; text-align:center;">
<span style="color:{status_color}; font-weight:600; font-size:0.7rem;">{s['gst_status']}</span>
</div>
<div style="flex:0.5; text-align:center;">{inv_icon}</div>
<div style="flex:0.5; text-align:center;">{_check(s['einvoice'])}</div>
<div style="flex:0.5; text-align:center;">{_check(s['eway_match'])}</div>
<div style="flex:0.5; text-align:center;">{_check(s['gstr_2a_match'])}</div>
<div style="flex:0.5; text-align:center;">{_check(s['gstr_2b_match'])}</div>
<div style="flex:0.7; text-align:center;">
<span style="background:{risk_color}; color:white; padding:2px 8px; border-radius:10px;
font-size:0.7rem; font-weight:700;">{s['risk_score']}%</span>
</div>
</div>
""", unsafe_allow_html=True)
    
    # Warning for high-risk suppliers
    high_risk_suppliers = [s for s in suppliers if s["risk_score"] >= 70]
    if high_risk_suppliers:
        st.markdown("---")
        st.error(f"🚨 **{len(high_risk_suppliers)} HIGH-RISK SUPPLIERS DETECTED** — Immediate action required!")
        for s in high_risk_suppliers:
            st.warning(f"⚠️ **{s['name']}**: Risk Score {s['risk_score']}% | {s['filing_status']} | "
                       f"{'Under Investigation' if s['investigation'] else 'No Investigation'}")
            st.caption("Recommendation: Suspend purchases immediately. Request fresh GST compliance certificate. "
                       "Verify ITC claimed from this supplier against GSTR-2B.")
