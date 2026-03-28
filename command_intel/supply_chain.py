"""
Panel 3: Supply Chain Visibility Panel
Track shipments from Iraq loading port → India port → Tanker dispatch → Delivery → Payment.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime
import random

# --- MOCK SHIPMENT DATA ---
def _get_shipment_data():
    """Generate realistic mock shipment tracking data."""
    today = datetime.date.today()
    
    shipments = [
        {
            "id": "SHP-2026-001",
            "loading_port": "Basrah, Iraq",
            "vessel_name": "MT Arabian Star",
            "bl_number": "BSRH/2026/0142",
            "quantity_mt": 5000,
            "loading_date": today - datetime.timedelta(days=18),
            "eta": today + datetime.timedelta(days=2),
            "discharge_port": "Mangalore",
            "tanker_dispatch": None,
            "delivery_confirmed": False,
            "consumption_proof": False,
            "invoice_generated": False,
            "payment_received": False,
            "status": "in_transit",
            "buyer": "IRB Infrastructure",
            "value_cr": 15.2
        },
        {
            "id": "SHP-2026-002",
            "loading_port": "Bandar Abbas, Iran",
            "vessel_name": "MT Gulf Carrier",
            "bl_number": "BND/2026/0088",
            "quantity_mt": 3000,
            "loading_date": today - datetime.timedelta(days=25),
            "eta": today - datetime.timedelta(days=3),
            "discharge_port": "Kandla",
            "tanker_dispatch": today - datetime.timedelta(days=1),
            "delivery_confirmed": True,
            "consumption_proof": False,
            "invoice_generated": True,
            "payment_received": False,
            "status": "delivered",
            "buyer": "L&T Construction",
            "value_cr": 9.8
        },
        {
            "id": "SHP-2026-003",
            "loading_port": "Basrah, Iraq",
            "vessel_name": "MT Eastern Glory",
            "bl_number": "BSRH/2026/0156",
            "quantity_mt": 5000,
            "loading_date": today - datetime.timedelta(days=35),
            "eta": today - datetime.timedelta(days=12),
            "discharge_port": "Mumbai (JNPT)",
            "tanker_dispatch": today - datetime.timedelta(days=10),
            "delivery_confirmed": True,
            "consumption_proof": True,
            "invoice_generated": True,
            "payment_received": True,
            "status": "completed",
            "buyer": "Tata Projects Ltd",
            "value_cr": 16.5
        },
        {
            "id": "SHP-2026-004",
            "loading_port": "Basrah, Iraq",
            "vessel_name": "MT Tigris Dream",
            "bl_number": "BSRH/2026/0170",
            "quantity_mt": 4500,
            "loading_date": today - datetime.timedelta(days=5),
            "eta": today + datetime.timedelta(days=15),
            "discharge_port": "Mangalore",
            "tanker_dispatch": None,
            "delivery_confirmed": False,
            "consumption_proof": False,
            "invoice_generated": False,
            "payment_received": False,
            "status": "in_transit",
            "buyer": "Dilip Buildcon",
            "value_cr": 14.1
        },
        {
            "id": "SHP-2026-005",
            "loading_port": "Umm Qasr, Iraq",
            "vessel_name": "MT Desert Falcon",
            "bl_number": "UMQ/2026/0045",
            "quantity_mt": 6000,
            "loading_date": today - datetime.timedelta(days=28),
            "eta": today - datetime.timedelta(days=5),
            "discharge_port": "Kandla",
            "tanker_dispatch": today - datetime.timedelta(days=3),
            "delivery_confirmed": True,
            "consumption_proof": True,
            "invoice_generated": True,
            "payment_received": False,
            "status": "awaiting_payment",
            "buyer": "PNC Infratech",
            "value_cr": 19.2
        }
    ]
    return shipments


def _get_status_color(status):
    return {
        "completed": ("#22c55e", "🟢"),
        "delivered": ("#22c55e", "🟢"),
        "in_transit": ("#eab308", "🟡"),
        "awaiting_payment": ("#f59e0b", "🟠"),
        "risk": ("#ef4444", "🔴"),
        "delayed": ("#ef4444", "🔴"),
    }.get(status, ("#94a3b8", "⚪"))


def _get_pipeline_stages(shipment):
    """Get pipeline stages with completion status."""
    stages = [
        ("📦 Loading", True, shipment["loading_port"]),
        ("🚢 In Transit", shipment["status"] != "loading", shipment["vessel_name"]),
        ("⚓ Port Discharge", shipment["eta"] <= datetime.date.today(), shipment["discharge_port"]),
        ("🚛 Tanker Dispatch", shipment["tanker_dispatch"] is not None, 
         str(shipment["tanker_dispatch"]) if shipment["tanker_dispatch"] else "Pending"),
        ("✅ Delivery", shipment["delivery_confirmed"], shipment["buyer"]),
        ("📋 Consumption Proof", shipment["consumption_proof"], "Verified" if shipment["consumption_proof"] else "Pending"),
        ("🧾 Invoice", shipment["invoice_generated"], "Generated" if shipment["invoice_generated"] else "Pending"),
        ("💰 Payment", shipment["payment_received"], "Received" if shipment["payment_received"] else "Pending"),
    ]
    return stages


def render():
    display_badge("historical")
    """Render the Supply Chain Visibility panel."""
    
    st.markdown("""
<div style="background: linear-gradient(135deg, #065f46 0%, #047857 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(6, 95, 70, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">🚢</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Supply Chain Visibility Panel
</div>
<div style="font-size:0.75rem; color:#6ee7b7; letter-spacing:1px; text-transform:uppercase;">
Iraq → India Port → Tanker → Delivery → Payment Tracking
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    shipments = _get_shipment_data()
    
    # --- SUMMARY METRICS ---
    total_qty = sum(s["quantity_mt"] for s in shipments)
    in_transit = sum(1 for s in shipments if s["status"] == "in_transit")
    delivered = sum(1 for s in shipments if s["status"] in ["delivered", "completed", "awaiting_payment"])
    total_value = sum(s["value_cr"] for s in shipments)
    awaiting_pay = sum(s["value_cr"] for s in shipments if not s["payment_received"])
    
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("📦 Total Shipments", len(shipments))
    with m2:
        st.metric("🟡 In Transit", in_transit)
    with m3:
        st.metric("🟢 Delivered", delivered)
    with m4:
        st.metric("💰 Total Value", f"{total_value:.1f} Cr")
    with m5:
        st.metric("⏳ Awaiting Payment", f"{awaiting_pay:.1f} Cr")
    
    st.markdown("---")
    
    # --- SHIPMENT CARDS ---
    for shipment in shipments:
        color, icon = _get_status_color(shipment["status"])
        status_label = shipment["status"].replace("_", " ").title()
        stages = _get_pipeline_stages(shipment)
        
        completed_count = sum(1 for s in stages if s[1])
        progress_pct = (completed_count / len(stages)) * 100
        
        with st.expander(f"{icon} {shipment['id']} — {shipment['vessel_name']} | {shipment['quantity_mt']:,} MT → {shipment['discharge_port']} | {status_label}", expanded=(shipment["status"] == "in_transit")):
            
            # Info Row
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.caption(f"📦 **BL:** {shipment['bl_number']}")
                st.caption(f"🏭 **From:** {shipment['loading_port']}")
            with c2:
                st.caption(f"⚓ **To:** {shipment['discharge_port']}")
                st.caption(f"📅 **Loaded:** {shipment['loading_date']}")
            with c3:
                st.caption(f"📅 **ETA:** {shipment['eta']}")
                st.caption(f"👷 **Buyer:** {shipment['buyer']}")
            with c4:
                st.caption(f"💰 **Value:** {shipment['value_cr']} Cr")
                st.caption(f"📊 **Qty:** {shipment['quantity_mt']:,} MT")
            
            # Progress Bar
            st.markdown(f"""
<div style="background:#e2e8f0; border-radius:10px; height:8px; margin:10px 0;">
<div style="background:{color}; width:{progress_pct:.0f}%; height:100%; border-radius:10px;
transition: width 0.5s;"></div>
</div>
<div style="text-align:right; font-size:0.7rem; color:#94a3b8;">{completed_count}/{len(stages)} stages complete</div>
""", unsafe_allow_html=True)
            
            # Pipeline Stages
            stage_html = '<div style="display:flex; justify-content:space-between; margin-top:10px;">'
            for label, done, detail in stages:
                bg = "#dcfce7" if done else "#fef2f2"
                border = "#22c55e" if done else "#fecaca"
                text_c = "#166534" if done else "#991b1b"
                check = "✅" if done else "⏳"
                stage_html += f"<div style='text-align:center; flex:1; padding:5px; margin:2px; background:{bg}; border:1px solid {border}; border-radius:6px;'><div style='font-size:0.65rem; font-weight:600; color:{text_c};'>{check} {label}</div><div style='font-size:0.6rem; color:#64748b; margin-top:2px;'>{detail}</div></div>"
            stage_html += '</div>'
            st.markdown(stage_html, unsafe_allow_html=True)
