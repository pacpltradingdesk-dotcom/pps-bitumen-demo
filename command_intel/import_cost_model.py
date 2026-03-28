try:
    from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    try:
        from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
    except:
        pass
"""
Panel 2: Import Cost Modeling Panel
Full Iraq-to-India import cost calculator with sensitivity analysis.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import numpy as np

# --- DEFAULT COST PARAMETERS ---
DEFAULT_PARAMS = {
    "fob_price_usd": 380.0,        # FOB price per MT in USD
    "freight_usd": 35.0,           # Ocean freight per MT in USD
    "insurance_pct": 0.5,          # Insurance as % of CIF
    "switch_bl_usd": 2.0,          # Switch Bill of Lading per MT
    "port_berthing_total": 10000,   # Fixed port berthing charge ₹
    "cha_per_mt": 75.0,            # CHA charge per MT ₹
    "handling_per_mt": 100.0,       # Handling charge per MT ₹
    "customs_duty_pct": 2.5,       # Customs duty %
    "gst_pct": 18.0,              # GST %
    "usd_inr": 83.25,             # Exchange rate
    "vessel_qty_mt": 5000.0,       # Vessel quantity in MT
    "target_margin_pct": 5.0,      # Target margin %
}


def _calculate_import_cost(params):
    """Calculate complete import landed cost breakdown."""
    usd_inr = params["usd_inr"]
    qty = params["vessel_qty_mt"]
    
    # FOB in INR
    fob_inr = params["fob_price_usd"] * usd_inr
    
    # Freight in INR
    freight_inr = params["freight_usd"] * usd_inr
    
    # CIF = FOB + Freight + Insurance
    cif_usd = params["fob_price_usd"] + params["freight_usd"]
    insurance_inr = (cif_usd * usd_inr) * (params["insurance_pct"] / 100)
    cif_inr = fob_inr + freight_inr + insurance_inr
    
    # Switch BL
    switch_bl_inr = params["switch_bl_usd"] * usd_inr
    
    # Port berthing per MT
    port_berthing_per_mt = params["port_berthing_total"] / qty if qty > 0 else 0
    
    # CHA & Handling
    cha = params["cha_per_mt"]
    handling = params["handling_per_mt"]
    
    # Customs duty on CIF
    customs_duty = cif_inr * (params["customs_duty_pct"] / 100)
    
    # Total before GST
    total_before_gst = cif_inr + switch_bl_inr + port_berthing_per_mt + cha + handling + customs_duty
    
    # GST
    gst = total_before_gst * (params["gst_pct"] / 100)
    
    # Total Landed Cost
    landed_cost = total_before_gst + gst
    
    # Break-even & Margin
    breakeven_price = landed_cost
    target_margin = landed_cost * (params["target_margin_pct"] / 100)
    sale_price = landed_cost + target_margin
    
    return {
        "fob_inr": round(fob_inr, 2),
        "freight_inr": round(freight_inr, 2),
        "insurance_inr": round(insurance_inr, 2),
        "cif_inr": round(cif_inr, 2),
        "switch_bl_inr": round(switch_bl_inr, 2),
        "port_berthing_per_mt": round(port_berthing_per_mt, 2),
        "cha": cha,
        "handling": handling,
        "customs_duty": round(customs_duty, 2),
        "total_before_gst": round(total_before_gst, 2),
        "gst": round(gst, 2),
        "landed_cost": round(landed_cost, 2),
        "breakeven_price": round(breakeven_price, 2),
        "target_margin": round(target_margin, 2),
        "sale_price": round(sale_price, 2),
        "total_shipment_value": round(landed_cost * qty, 2),
        "total_gst_credit": round(gst * qty, 2),
    }


def render():
    display_badge("calculated")
    """Render the Import Cost Modeling panel."""
    
    st.markdown("""
<div style="background: linear-gradient(135deg, #0c4a6e 0%, #075985 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(7, 89, 133, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">📦</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Import Cost Modeling Panel
</div>
<div style="font-size:0.75rem; color:#7dd3fc; letter-spacing:1px; text-transform:uppercase;">
Iraq → India Complete Landed Cost Calculator
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    # --- INPUT FORM ---
    col_input, col_result = st.columns([1.2, 1.8])
    
    with col_input:
        st.markdown("### 📝 Cost Parameters")

        # ── Port selector — loads port-specific charges from settings ──
        try:
            from settings_engine import get as _sg
            _port_charges = _sg("port_charges", {})
        except Exception:
            _port_charges = {}
        _port_names = list(_port_charges.keys()) if _port_charges else [
            "Kandla", "Mundra", "Mangalore", "JNPT", "Karwar", "Haldia", "Ennore", "Paradip"
        ]
        selected_port = st.selectbox("⚓ Import Port", _port_names, key="import_port_sel")
        _pc = _port_charges.get(selected_port, {})
        _def_berthing = int(_pc.get("berthing", DEFAULT_PARAMS["port_berthing_total"]))
        _def_cha = float(_pc.get("cha_per_mt", DEFAULT_PARAMS["cha_per_mt"]))
        _def_handling = float(_pc.get("handling_per_mt", DEFAULT_PARAMS["handling_per_mt"]))

        with st.form("import_cost_form"):
            st.markdown("**🌍 International Costs (USD/MT)**")
            fob = st.number_input("FOB Price ($/MT)", value=DEFAULT_PARAMS["fob_price_usd"], step=5.0)
            freight = st.number_input("Ocean Freight ($/MT)", value=DEFAULT_PARAMS["freight_usd"], step=1.0)
            insurance = st.number_input("Insurance (%)", value=DEFAULT_PARAMS["insurance_pct"], step=0.1)
            switch_bl = st.number_input("Switch BL Cost ($/MT)", value=DEFAULT_PARAMS["switch_bl_usd"], step=0.5)

            st.markdown(f"**🇮🇳 Port Charges — {selected_port} (₹)**")
            port_berthing = st.number_input("Port Berthing (₹ Total)", value=_def_berthing, step=1000)
            cha = st.number_input("CHA (₹/MT)", value=_def_cha, step=5.0)
            handling = st.number_input("Handling (₹/MT)", value=_def_handling, step=10.0)
            
            st.markdown("**🏛️ Duties & Taxes**")
            customs = st.number_input("Customs Duty (%)", value=DEFAULT_PARAMS["customs_duty_pct"], step=0.5)
            gst = st.number_input("GST (%)", value=DEFAULT_PARAMS["gst_pct"], step=1.0)
            
            st.markdown("**💵 Exchange & Volume**")
            usd_inr = st.number_input("USD/INR Rate", value=DEFAULT_PARAMS["usd_inr"], step=0.25)
            vessel_qty = st.number_input("Vessel Quantity (MT)", value=DEFAULT_PARAMS["vessel_qty_mt"], step=500.0)
            margin_pct = st.number_input("Target Margin %", value=DEFAULT_PARAMS["target_margin_pct"], step=0.5)
            
            calc_submitted = st.form_submit_button("🧮 Calculate Landed Cost", type="primary", use_container_width=True)
    
    # --- RESULTS ---
    with col_result:
        params = {
            "fob_price_usd": fob, "freight_usd": freight, "insurance_pct": insurance,
            "switch_bl_usd": switch_bl, "port_berthing_total": port_berthing,
            "cha_per_mt": cha, "handling_per_mt": handling, "customs_duty_pct": customs,
            "gst_pct": gst, "usd_inr": usd_inr, "vessel_qty_mt": vessel_qty,
            "target_margin_pct": margin_pct
        }
        
        result = _calculate_import_cost(params)
        
        st.markdown("### 💰 Cost Breakdown (₹/MT)")
        
        # Waterfall breakdown
        breakdown_items = [
            ("FOB Price", result["fob_inr"], "#3b82f6"),
            ("Ocean Freight", result["freight_inr"], "#6366f1"),
            ("Insurance", result["insurance_inr"], "#8b5cf6"),
            ("Switch BL", result["switch_bl_inr"], "#a855f7"),
            ("Port Berthing", result["port_berthing_per_mt"], "#d946ef"),
            ("CHA Charges", result["cha"], "#ec4899"),
            ("Handling", result["handling"], "#f43f5e"),
            ("Customs Duty", result["customs_duty"], "#f97316"),
            ("GST (18%)", result["gst"], "#eab308"),
        ]
        
        for label, value, color in breakdown_items:
            pct = (value / result["landed_cost"]) * 100 if result["landed_cost"] > 0 else 0
            st.markdown(f"""
<div style="display:flex; align-items:center; margin:3px 0; gap:10px;">
<div style="width:140px; font-size:0.8rem; color:#475569; font-weight:500;">{label}</div>
<div style="flex:1; background:#f1f5f9; border-radius:4px; height:22px; overflow:hidden;">
<div style="width:{min(pct*2, 100):.0f}%; height:100%; background:{color}; border-radius:4px;
display:flex; align-items:center; padding-left:8px;">
<span style="color:white; font-size:0.7rem; font-weight:600; white-space:nowrap;">{format_inr(value)}</span>
</div>
</div>
<div style="width:50px; text-align:right; font-size:0.75rem; color:#94a3b8;">{pct:.1f}%</div>
</div>
""", unsafe_allow_html=True)
        
        # Total Row
        st.markdown(f"""
<div style="background: linear-gradient(135deg, #059669, #10b981); padding:15px; border-radius:10px; 
margin-top:15px; box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3);">
<div style="display:flex; justify-content:space-between; align-items:center;">
<span style="color:white; font-weight:700; font-size:1.1rem;">TOTAL LANDED COST</span>
<span style="color:white; font-weight:800; font-size:1.5rem;">{format_inr(result['landed_cost'])}/MT</span>
</div>
</div>
""", unsafe_allow_html=True)
        
        # Key metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("🎯 Break-Even Price", f"{format_inr(result['breakeven_price'])}/MT")
        with m2:
            st.metric("💸 Sale Price (w/ margin)", f"{format_inr(result['sale_price'])}/MT")
        with m3:
            st.metric("📊 Margin/MT", f"{format_inr(result['target_margin'])}")
        
        m4, m5 = st.columns(2)
        with m4:
            st.metric("🚢 Total Shipment Value", f"{result['total_shipment_value']/10000000:.2f} Cr")
        with m5:
            st.metric("🧾 GST Input Credit", f"{result['total_gst_credit']/100000:.2f} L")
    
    # --- SENSITIVITY ANALYSIS ---
    st.markdown("---")
    st.markdown("### 🔄 Sensitivity Simulator")
    st.caption("See how changes in key variables affect your landed cost")
    
    s1, s2, s3 = st.columns(3)
    
    with s1:
        usd_change = st.slider("USD/INR Change (%)", -5.0, 5.0, 0.0, 0.5)
        new_usd = usd_inr * (1 + usd_change/100)
        p_usd = params.copy()
        p_usd["usd_inr"] = new_usd
        r_usd = _calculate_import_cost(p_usd)
        delta = r_usd["landed_cost"] - result["landed_cost"]
        st.metric(f"New Rate: {new_usd:.2f}", f"{format_inr(r_usd['landed_cost'])}/MT", f"{delta:+,.0f}")
    
    with s2:
        freight_change = st.slider("Freight Change ($/MT)", -15.0, 15.0, 0.0, 1.0)
        p_frt = params.copy()
        p_frt["freight_usd"] = freight + freight_change
        r_frt = _calculate_import_cost(p_frt)
        delta_f = r_frt["landed_cost"] - result["landed_cost"]
        st.metric(f"New Freight: ${freight+freight_change:.0f}", f"{format_inr(r_frt['landed_cost'])}/MT", f"{delta_f:+,.0f}")
    
    with s3:
        crude_change = st.slider("FOB/Crude Change (%)", -10.0, 10.0, 0.0, 1.0)
        p_crude = params.copy()
        p_crude["fob_price_usd"] = fob * (1 + crude_change/100)
        r_crude = _calculate_import_cost(p_crude)
        delta_c = r_crude["landed_cost"] - result["landed_cost"]
        st.metric(f"New FOB: ${fob*(1+crude_change/100):.0f}", f"{format_inr(r_crude['landed_cost'])}/MT", f"{delta_c:+,.0f}")
