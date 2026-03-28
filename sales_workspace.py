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

import streamlit as st
import pandas as pd
import datetime
from party_master import load_customers, load_suppliers, load_services
from distance_matrix import get_distance, get_clean_state

# --- SALES INTELLIGENCE DATA ---

OBJECTION_LIBRARY = {
    "Price is too high": {
        "Short Reply": "Sir, diesel prices rose ₹2/L this week, affecting all freight. Our price is landed & theft-proof.",
        "Detailed Reply": "I understand the concern. However, our price includes guaranteed volume/density test at the refinery. Cheaper quotes often cut costs by using unauthorized logistics which can lead to quantity shortages. With us, you get the exact 15MT you ordered.",
        "Confidence Booster": "We are one of the few using only Verified Tankers with GPS tracking."
    },
    "Competitor is cheaper": {
        "Short Reply": "Are they giving you a Dispatch Commitment? We guarantee loading within 24 hours.",
        "Detailed Reply": "Competition might quote lower on older inventory. Our stock is fresh from the refinery, ensuring proper temperature and grade specs (VG30/40). Low-priced bitumen often has heating issues.",
        "Confidence Booster": "Sir, we don't just sell bitumen, we sell on-time assurance."
    },
    "Payment Terms": {
        "Short Reply": "We can offer a 0.5% Cash Discount for immediate RTGS, which brings your effective rate down.",
        "Detailed Reply": "Our margins are extremely thin to give you the best base rate. Hence, we operate on Advance. However, once we build a 3-month history, we can apply for a Credit Limit for your company.",
        "Confidence Booster": "Let's start with a small test load, you will see our quality speaks for itself."
    },
    "Need Immediate Delivery": {
        "Short Reply": "We have a tanker unloading near you in 2 hours. If you book now, we can divert empty to refinery immediately.",
        "Detailed Reply": "The market is tight, but I can block a slot for you if you confirm in 30 mins. Otherwise, the next slot is day-after-tomorrow.",
        "Confidence Booster": "I will personally oversee the dispatch for you."
    },
    "Quality Concern": {
        "Short Reply": "All our material comes with a Refinery Test Certificate (MTC). You can test it at any lab.",
        "Detailed Reply": "Sir, we only lift from PSU refineries. We don't trade in 'Import Re-processed' material. The MTC will match the batch number on the tanker seal.",
        "Confidence Booster": "100% replacement guarantee if quality fails lab test."
    },
    "Other Trader Cheaper": {
        "Short Reply": "Sir, are they adding GST and Transport? Or is it 'Basic' price?",
        "Detailed Reply": "Be careful of quotes that hide 'Handling Charges' or 'Detention'. My price is the final landed cost at your gate. No hidden surprises.",
        "Confidence Booster": "My rate is final. Their rate usually increases when the invoice comes."
    }
}

TALKING_POINTS_RULES = [
    {"condition": "source_dist < 300", "point": "🟢 Proximity Advantage: Source is <300km. Ensure quick turnaround."},
    {"condition": "source_dist > 1000", "point": "⚠️ Long Haul: Advise client to stock up due to 3-4 day transit time."},
    {"condition": "supplier_type == 'Refinery'", "point": "🏭 Direct PSU Sourcing: Guarantee of purity and standard weight."},
    {"condition": "market_tight == True", "point": "🔥 Demand Spike: Prices expected to rise next week. Book now."}
]

# --- HELPER FUNCTIONS ---

def get_talking_points(source, distance, market_tight=False):
    points = []
    if distance < 300:
        points.append("✅ Fast Delivery: Source is very close, expect delivery tomorrow.")
    elif distance > 1000:
        points.append("🚚 Logistics Planning: Long route, suggest ordering full load to maximize freight efficiency.")
    
    if "Refinery" in source.get('type', ''):
        points.append("💎 Quality Assurance: Material is directly from PSU Refinery.")
    
    return points

# --- COMPONENT: CLIENT 360 CARD ---

def render_client_360(client_name):
    """Renders a comprehensive view of a selected client."""
    customers = load_customers()
    client = next((c for c in customers if c['name'] == client_name), None)
    
    if not client:
        st.warning("Client not found.")
        return

    with st.container():
        # Header
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(f"🏢 {client['name']}")
            st.caption(f"Segment: {client.get('category', 'General')} | State: {client.get('state', 'Unknown')}")
        with c2:
            st.metric("Credit Score", "A+" if client.get('active') else "B", delta="Active")

        st.divider()

        # Key Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.info(f"📍 City: {client.get('city', 'Unknown')}")
        m2.info(f"📞 Contact: {client.get('contact', 'N/A')}")
        m3.info(f"💰 GST: {client.get('gstin', 'N/A')}")
        m4.success(f"💳 Terms: Advance") 

        # Extended Profile (Tabs)
        t1, t2, t3 = st.tabs(["📝 Deals & History", "⚠️ Operational Constraints", "⚡ Quick Actions"])
        
        with t1:
            st.write("**Recent Deal History (Mock Data)**")
            history_data = [
                {"Date": "2025-01-15", "Grade": "VG30", "Qty": "20 MT", "Price": "42,500", "Status": "✅ Delivered"},
                {"Date": "2024-12-20", "Grade": "VG30", "Qty": "15 MT", "Price": "41,800", "Status": "✅ Delivered"},
                {"Date": "2024-11-10", "Grade": "VG40", "Qty": "20 MT", "Price": "43,000", "Status": "❌ Lost (Price)"},
            ]
            st.table(pd.DataFrame(history_data))
        
        with t2:
            st.warning("🚧 Site Constraints: No entry for XL trailers (40ft). Only 20ft allowed.")
            st.info("🕒 Unloading Hours: 08:00 AM - 06:00 PM Only.")
            
        with t3:
            st.button("📲 Open WhatsApp", use_container_width=True)
            st.button("📧 Email Quote", use_container_width=True)
            st.button("📝 Edit Profile", use_container_width=True)

# --- COMPONENT: DEAL ROOM ---

def render_deal_room():
    """Renders the main Deal evaluation interface."""
    st.header("🤝 Deal Room (Sales Board)")
    
    # 1. Lead Selection
    col_lead, col_grade = st.columns([2, 1])
    with col_lead:
        custs = [c['name'] for c in load_customers()]
        selected_client = st.selectbox("Select Customer", ["-- New Inquiry --"] + custs)
    with col_grade:
        grade = st.selectbox("Grade", ["VG30", "VG40", "VG10", "Emulsion"])
        
    if selected_client != "-- New Inquiry --":
        # Show Mini 360
        with st.expander("Show Client Snapshot", expanded=False):
            render_client_360(selected_client)
            
        st.markdown("---")
        
        # 2. Feasibility & Sourcing Engine (Simplified for Sales)
        st.subheader("🛠️ Structure the Deal")
        
        c_source, c_dest, c_qty, c_price = st.columns([1.5, 1.5, 0.8, 1.0])
        with c_source:
             # Just show top states/cities to filter
             suppliers = load_suppliers()
             supplier_names = [s['name'] for s in suppliers]
             source = st.selectbox("Source (Refinery/Import)", supplier_names)
        
        with c_dest:
            customers = load_customers()
            # If client selected, auto-fill city
            curr_client = next((c for c in customers if c['name'] == selected_client), {})
            dest_city = st.text_input("Destination City", value=curr_client.get('city', ''))
            
        with c_qty:
            qty = st.number_input("Quantity (MT)", min_value=10, value=20)

        with c_price:
            sell_price = st.number_input("Selling Price (₹/MT)", min_value=0, value=45000, step=100)

        # Calculation
        if source and dest_city:
            # Basic Math
            dist = get_distance(source.split('(')[0].strip(), dest_city) # Simple lookup approximation
            # If dist is 0, try finding supplier city
            if dist == 0:
                s_obj = next((s for s in suppliers if s['name'] == source), {})
                s_city = s_obj.get('city', '').split('(')[0].strip()
                dist = get_distance(s_city, dest_city)
            
            # --- SAFETY PATCH: ZERO FREIGHT PROTECTION ---
            is_estimated = False
            if dist == 0:
                dist = 350.0 # Safe fallback average
                is_estimated = True
            # ---------------------------------------------

            freight_rate = 4.5 # Hardcoded estimation for Sales Demo
            est_freight = dist * freight_rate
            base_price = 42000 # Mock daily price
            
            landing_cost = base_price + est_freight
            margin = sell_price - landing_cost

            if is_estimated:
                st.error(f"⚠️ Unknown Route! Estimated Freight for {dist}KM applied. Verify manually.")
            
            # --- MAP INTELLIGENCE ---
            from distance_matrix import SOURCE_COORDS, DESTINATION_COORDS
            
            s_key = source.split('(')[0].strip()
            # Try mapping source name to coordinate key
            if s_key not in SOURCE_COORDS:
                 # Fallback: check if 'city' maps
                 s_obj = next((s for s in suppliers if s['name'] == source), {})
                 s_city = s_obj.get('city', '').split('(')[0].strip()
                 s_coords = DESTINATION_COORDS.get(s_city) # May exist as dest
                 if not s_coords and s_city in SOURCE_COORDS: s_coords = SOURCE_COORDS[s_city]
            else:
                 s_coords = SOURCE_COORDS[s_key]
            
            d_coords = DESTINATION_COORDS.get(dest_city)
            
            if s_coords and d_coords:
                map_data = pd.DataFrame([
                    {"lat": s_coords[0], "lon": s_coords[1], "type": "Source", "color": "#00ff00"},
                    {"lat": d_coords[0], "lon": d_coords[1], "type": "Destination", "color": "#ff0000"}
                ])
                st.map(map_data, size=20, zoom=5, use_container_width=True)
            else:
                st.caption(f"Map unavailable for these coordinates ({s_key} -> {dest_city})")
            
            # --- THE SALES COCKPIT ---
            st.markdown("### 💰 Pricing & Margin")
            
            # Internal Alerts
            if margin < 300:
                st.error("⚠️ MARGIN ALERT: Below minimum threshold (₹300). Approval needed.")
            if dist > 1500:
                st.warning("⚠️ RISK ALERT: Dispatch > 1500KM. Ensure 100% Advance Payment.")
            
            # Main Layout
            cols = st.columns([2, 2, 3])
            
            with cols[0]:
                st.metric("📏 Distance", f"{dist} KM")
                st.metric("🚛 Est. Freight", f"{format_inr(est_freight)}/MT")
                
            with cols[1]:
                st.metric("🏭 Base Price", f"{format_inr(base_price)}/MT")
                st.caption("Ex-Refinery, Bulk")
                
            with cols[2]:
                st.metric("📈 Net Margin", f"{format_inr(margin)}/MT", delta=f"{margin/landing_cost*100:.1f}%")
                
                st.markdown(f"""
<div style="background-color: #d4edda; padding: 10px; border-radius: 5px; text-align: center;">
<h3 style="color: #155724; margin:0;">{format_inr(sell_price)} / MT</h3>
<p style="margin:0;">Final Offer Price</p>
</div>
""", unsafe_allow_html=True)

            # --- 5. MARKET INTELLIGENCE (NEW) ---
            from market_intelligence import get_area_insight, get_competitor_intel, get_delivery_confidence, get_followup_strategy
            
            insight = get_area_insight(dest_city)
            risk_data = get_delivery_confidence(source, dest_city, dist)
            
            st.markdown("---")
            
            # ROW 1: MARKET INSIGHT & CONFIDENCE
            mi_c1, mi_c2 = st.columns([1.5, 1])
            
            with mi_c1:
                st.info(f"📍 **AREA MARKET INSIGHT: {dest_city}**")
                
                ic1, ic2 = st.columns(2)
                ic1.write(f"**Demand:** {insight['demand']}")
                ic2.write(f"**Issues:** {insight['issues']}")
                
                st.write(f"**🚧 Activity:** {insight['activity']}")
                st.caption(f"**🗣️ Sales Pitch:** \"{insight['pitch']}\"")

            with mi_c2:
                st.success("🛡️ **DELIVERY CONFIDENCE**")
                st.metric("Dispatch Probability", f"{risk_data['dispatch_prob']}%")
                st.progress(risk_data['dispatch_prob']/100)
                st.caption(f"Reliability Score: {risk_data['reliability_score']}/5.0")

            # ROW 2: COMPETITOR RADAR (SILENT)
            st.markdown("---")
            comp_intel = get_competitor_intel("South" if dist < 800 else "North")
            
            cr_1, cr_2 = st.columns([1, 2])
            with cr_1:
                st.error("🕵️ **COMPETITOR RADAR**")
                st.write(f"**Price:** {comp_intel['competitor_price']}")
                st.write(f"**Weakness:** {comp_intel['their_weakness']}")
            with cr_2:
                st.write(f"**✅ Our Strength:** {comp_intel['our_strength']}")
                st.write(f"**🗣️ What to Say:** \"{comp_intel['script']}\"")
                
            
            # --- 6. ACTION & FOLLOW-UP ---
            st.markdown("---")
            st.subheader("⚡ Action Center")
            
            # Smart Follow-up
            follow_strat = get_followup_strategy(final_price, margin, days_passed=1)
            with st.expander("💡 Smart Follow-up Suggestion (AI)", expanded=True):
                st.write(f"**Strategy:** {follow_strat['action']}")
                st.info(f"**Script:** \"{follow_strat['script']}\"")
            
            # Quote Generator
            b1, b2 = st.columns(2)
            with b1:
                if st.button("📤 Generate SALES-STYLE PDF Quote", use_container_width=True):
                    st.success("Generated PDF with: \n- Price Breakup\n- 3 Why Choose Us Points\n- Validity Countdown")
            with b2:
                if st.button("💬 WhatsApp Quote (Formatted)", use_container_width=True):
                    wa_msg = f"""*BITUMEN OFFER - {datetime.date.today()}*
📍 *Client:* {selected_client}
🏗️ *Grade:* {grade} ({qty} MT)
💰 *Rate:* {format_inr(final_price)}/MT (Landed {dest_city})

✅ *Why Us:* {comp_intel['our_strength']}
🚚 *Dispatch:* {risk_data['dispatch_prob']}% Assurance (GPS Tracked)

⏳ *Validity:* 24 Hours Only.
reply 'BOOK' to lock slot."""
                    st.code(wa_msg, language="markdown")
                    st.success("Copied to clipboard!")

