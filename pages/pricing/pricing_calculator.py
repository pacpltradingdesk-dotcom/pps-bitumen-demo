"""
Pricing Calculator Page
Extracted from dashboard.py — all business logic preserved as-is.
"""

import streamlit as st
import datetime
import urllib.parse
import os

from india_localization import format_inr
from ui_badges import display_badge
from pdf_generator import create_price_pdf, get_next_quote_number
from optimizer import CostOptimizer
from feasibility_engine import get_feasibility_assessment
from sales_calendar import (
    get_season_status, get_holidays_for_month, get_city_remarks,
    MONTH_NAMES
)

# --- CUSTOMER DATABASE (live — Phase 1: sourced from customers table) ---
@st.cache_data(ttl=300)
def _load_customer_city_map() -> dict[str, str]:
    """Return {name: city} for customers — cached 5 minutes.
    Empty dict if the DB has no customers yet."""
    try:
        from customer_source import load_customers
        return {c["name"]: (c.get("city") or "")
                for c in load_customers() if c.get("name")}
    except Exception:
        return {}


# Backwards-compat module-level alias. Callers that read this dict at
# import time will see the live map (evaluated lazily on first access).
customer_city_map = _load_customer_city_map()


@st.cache_resource
def _get_optimizer():
    opt = CostOptimizer()
    if os.path.exists(opt.data_path):
        opt.load_data()
        return opt
    else:
        return None


def render():
    st.markdown('<div class="pps-page-header"><div class="pps-page-title">\U0001f9ee Pricing Calculator</div></div>', unsafe_allow_html=True)
    display_badge("calculated")

    optimizer = _get_optimizer()

    # Pull any pre-selected customer from global context (set by picker / nav)
    _ctx_customer = ""
    _ctx_city     = ""
    _ctx_state    = ""
    try:
        from navigation_engine import get_context
        _ctx_customer = get_context("customer_name", "") or ""
        _ctx_city     = get_context("customer_city", "") or ""
        _ctx_state    = get_context("customer_state", "") or ""
    except Exception:
        pass

    col_left, col_mid, col_right = st.columns([1.2, 1.3, 2.0])

    # --- COLUMN 1: SELECTION PANEL & SALES CONTEXT ---
    with col_left:
        st.markdown("### \U0001f50d Parameters & Context")

        # 1. Selection Mode — auto-switch to Customer mode if context set
        _default_mode = "Customer" if _ctx_customer else "Location"
        _mode_idx = ["Location", "Customer"].index(_default_mode)
        search_mode = st.radio("Search By", ["Location", "Customer"],
                                index=_mode_idx,
                                horizontal=True, label_visibility="collapsed")

        selected_city = None
        selected_client_name = None

        if search_mode == "Location":
            from distance_matrix import ALL_STATES, get_cities_by_state, get_state_by_city, CITY_STATE_MAP

            all_cities = sorted(list(CITY_STATE_MAP.keys()))
            state_options = ["All States"] + ALL_STATES
            # Pre-select from context if available
            _state_default = state_options.index(_ctx_state) if _ctx_state in state_options else 0
            selected_state = st.selectbox("\U0001f4cd Select State", state_options,
                                          index=_state_default, key="state_select")

            if selected_state == "All States":
                city_options = all_cities
            else:
                city_options = sorted(get_cities_by_state(selected_state))

            _city_default = city_options.index(_ctx_city) if _ctx_city in city_options else 0
            selected_city = st.selectbox("\U0001f3d9\ufe0f Select City", city_options,
                                          index=_city_default, key="city_select")

            if selected_city and selected_state == "All States":
                detected_state = get_state_by_city(selected_city)

        else:
            cust_names = sorted(list(customer_city_map.keys()))
            _cust_default = cust_names.index(_ctx_customer) if _ctx_customer in cust_names else 0
            selected_cust = st.selectbox("Select Customer", cust_names, index=_cust_default)
            if selected_cust:
                selected_city = customer_city_map[selected_cust]
                selected_client_name = selected_cust
                from distance_matrix import get_state_by_city
                cust_state = get_state_by_city(selected_city)
                st.info(f"\U0001f4cd {selected_city}, {cust_state}")

        # --- SALES CONTEXT WIDGET (NEW) ---
        if selected_city:
            today = datetime.date.today()
            # Determine state
            if search_mode == "Location" and 'selected_state' in locals() and selected_state != "All States":
                ctx_state = selected_state
            else:
                from distance_matrix import get_state_by_city
                ctx_state = get_state_by_city(selected_city)

            # Get Data
            season_info = get_season_status(selected_city, today.month)
            holidays = get_holidays_for_month(today.year, today.month, ctx_state)

            # --- SALES CARD ---
            st.markdown(f"""
<div style="border: 1px solid #ddd; border-radius: 8px; padding: 10px; background-color: #fff; margin: 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
<div style="font-weight: bold; color: #444; margin-bottom: 5px; border-bottom: 1px solid #eee; padding-bottom: 3px;">
\U0001f5e3\ufe0f Sales Insights for {selected_city}
</div>
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
<span style="font-size: 0.85em; color: #666;">Season:</span>
<span style="background-color: {season_info['color']}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; font-weight: bold;">
{season_info['label'].replace('\u2705 ', '').replace('\u274c ', '').replace('\u26a0\ufe0f ', '')}
</span>
</div>
""", unsafe_allow_html=True)

            # Holidays Integration
            if holidays:
                # Find next future holiday
                future_holidays = [h for h in holidays if h['date'] >= today]
                next_holiday = future_holidays[0] if future_holidays else holidays[0]
                days_left = (next_holiday['date'] - today).days
                holiday_msg = ""
                if days_left == 0:
                     holiday_msg = f"\U0001f389 Today is <b>{next_holiday['name']}</b>!"
                elif 0 < days_left <= 7:
                     holiday_msg = f"\U0001f4c5 Upcoming: <b>{next_holiday['name']}</b> in {days_left} days."
                else:
                     holiday_msg = f"\U0001f4c5 {next_holiday['date'].day} {MONTH_NAMES[today.month]}: {next_holiday['name']}"

                if holiday_msg:
                    st.markdown(f"""
<div style="background-color: #fce4ec; color: #c2185b; padding: 6px; border-radius: 4px; font-size: 0.8em; margin-bottom: 5px;">
{holiday_msg}
</div>
""", unsafe_allow_html=True)
            else:
                st.caption("No major holidays this month.")

            # Remarks (Weather)
            remarks = get_city_remarks(selected_city)
            if remarks:
                 st.caption(f"\U0001f4dd {remarks}")

            st.markdown("</div>", unsafe_allow_html=True)
            # ---------------------------

        # 2. Product Info
        product_grade = st.radio("Select Grade", ["VG30", "VG10"], horizontal=True)

        load_type = "Bulk"
        if search_mode == "Location":
             load_type = st.radio("Select Type", ["Bulk", "Drum"], horizontal=True)

        product_name = f"Bitumen {product_grade}"

        calc_btn = st.button("Calculate Cost", use_container_width=True, type="primary")

    # --- COLUMN 2: RANKING LIST (Landing Price) - CATEGORIZED ---
    with col_mid:
        st.markdown("### \U0001f4c9 Best Prices")

        # Initialize result to None
        result = None
        selected_option = None

        if selected_city and calc_btn:
            # Get feasibility assessment for this destination
            assessment = get_feasibility_assessment(selected_city, top_n=3, grade=product_grade)

            if assessment:
                st.caption(f"Ranking for {product_grade} | Destination: {selected_city}")

                # Build options list for selection
                price_options = []

                # --- 1. DRUM DIRECT (TOP PRIORITY) ---
                st.markdown("#### \U0001f6e2\ufe0f Drum Import (Main)")
                drum = assessment.get('drum_direct')
                if drum:
                    price_options.append({
                        'label': f"\U0001f6e2\ufe0f {drum['source']} - {format_inr(drum['landed_cost'])}",
                        'source': drum['source'],
                        'price': drum['landed_cost'],
                        'base': drum.get('base_price', 0),
                        'transport': drum.get('transport', 0),
                        'distance': drum.get('distance_km', 0),
                        'type': 'Drum'
                    })
                    st.markdown(f'''
<div style="background-color:#FADBD8; padding:10px; border-radius:5px; margin-bottom:5px; border-left:5px solid #C0392B;">
<b style="font-size:1.1em;">{drum['source']}</b><br>
<span style="font-weight:bold; font-size:1.3em; color:#C0392B;">\U0001f6e2\ufe0f {format_inr(drum['landed_cost'])} PMT</span>
<small style="color:#666;"> ({drum['distance_km']:.0f} km)</small>
</div>
''', unsafe_allow_html=True)

                # --- 2. LOCAL DECANTER BULK ---
                st.markdown("#### \U0001f504 Decanter Bulk")
                dec = assessment.get('local_decanter')
                if dec:
                    price_options.append({
                        'label': f"\U0001f504 {dec['source']} - {format_inr(dec['landed_cost'])}",
                        'source': dec['source'],
                        'price': dec['landed_cost'],
                        'base': dec.get('drum_base_price', 0),
                        'transport': dec.get('drum_transport', 0) + dec.get('local_transport', 0),
                        'distance': 30,
                        'type': 'Decanter Bulk'
                    })
                    st.markdown(f'''
<div style="background-color:#FCF3CF; padding:8px; border-radius:5px; margin-bottom:5px; border-left:5px solid #9A7D0A;">
<small><b>{dec['source']}</b></small><br>
<small>From: {dec.get('drum_source', 'N/A')} | Conv: {dec.get('conversion_cost', 500)}</small><br>
<span style="font-weight:bold; font-size:1.1em; color:#9A7D0A;">\U0001f7e2 {format_inr(dec['landed_cost'])} PMT</span>
</div>
''', unsafe_allow_html=True)

                # --- 3. IMPORT BULK ---
                st.markdown("#### \U0001f6a2 Import Bulk")
                for i, opt in enumerate(assessment['imports'][:2]):
                    price_options.append({
                        'label': f"\U0001f6a2 {opt['source']} - {format_inr(opt['landed_cost'])}",
                        'source': opt['source'],
                        'price': opt['landed_cost'],
                        'base': opt.get('base_price', 0),
                        'transport': opt.get('transport', 0),
                        'distance': opt.get('distance_km', 0),
                        'type': 'Import Bulk'
                    })
                    bg_color = "#D6EAF8" if i == 0 else "#EBF5FB"
                    border = "#21618C" if i == 0 else "#AED6F1"
                    st.markdown(f'''
<div style="background-color:{bg_color}; padding:8px; border-radius:5px; margin-bottom:5px; border-left:5px solid {border};">
<small><b>{opt['source']}</b></small><br>
<span style="font-weight:bold; font-size:1.1em; color:{border};">{format_inr(opt['landed_cost'])} PMT</span>
<small style="color:#666;"> ({opt['distance_km']:.0f} km)</small>
</div>
''', unsafe_allow_html=True)

                # --- 4. PSU REFINERIES (Last) ---
                st.markdown("#### \U0001f3ed PSU Refinery Bulk")
                for i, opt in enumerate(assessment['refineries'][:2]):
                    price_options.append({
                        'label': f"\U0001f3ed {opt['source']} - {format_inr(opt['landed_cost'])}",
                        'source': opt['source'],
                        'price': opt['landed_cost'],
                        'base': opt.get('base_price', 0),
                        'transport': opt.get('transport', 0),
                        'distance': opt.get('distance_km', 0),
                        'type': 'Refinery Bulk'
                    })
                    bg_color = "#D4EFDF" if i == 0 else "#EAFAF1"
                    border = "#196F3D" if i == 0 else "#A9DFBF"
                    st.markdown(f'''
<div style="background-color:{bg_color}; padding:8px; border-radius:5px; margin-bottom:5px; border-left:5px solid {border};">
<small><b>{opt['source']}</b></small><br>
<span style="font-weight:bold; font-size:1.1em; color:{border};">{format_inr(opt['landed_cost'])} PMT</span>
<small style="color:#666;"> ({opt['distance_km']:.0f} km)</small>
</div>
''', unsafe_allow_html=True)

                # --- SELECT PRICE FOR PDF ---
                st.markdown("---")
                st.markdown("**\U0001f4cb Select Price for Quote:**")
                option_labels = [opt['label'] for opt in price_options]
                selected_label = st.radio("Choose option for PDF", option_labels, key="pdf_price_select", label_visibility="collapsed")

                # Find selected option
                for opt in price_options:
                    if opt['label'] == selected_label:
                        selected_option = opt
                        break

                # Store in session state for PDF
                if selected_option:
                    st.session_state['selected_price_option'] = selected_option
                    st.success(f"\u2705 Selected: {selected_option['source']} @ {format_inr(selected_option['price'])}")

                # Set result for the right panel
                result = {
                    'best_option': {
                        'source_location': selected_option['source'] if selected_option else 'N/A',
                        'final_landed_cost': selected_option['price'] if selected_option else 0,
                        'base_price': selected_option['base'] if selected_option else 0,
                        'transport_cost': selected_option['transport'] if selected_option else 0,
                        'discount': 0,
                        'distance_km': selected_option['distance'] if selected_option else 0,
                        'type': selected_option['type'] if selected_option else 'N/A'
                    },
                    'all_options': None,
                    'assessment': assessment
                }
            else:
                # Fallback to original optimizer
                if optimizer:
                    result = optimizer.calculate_best_price(selected_city, load_type, product_grade=product_grade)

                    if result:
                         st.caption(f"Ranking for {load_type} | {product_grade}")
                         top_sources = result['all_options'].head(5)
                         for idx, (i, row) in enumerate(top_sources.iterrows()):
                            icon = "\U0001f7e2" if idx == 0 else "\U0001f534"
                            text_color = "#27AE60" if idx == 0 else "#C0392B"
                            bg_color = "#EAFAF1" if idx == 0 else "#FADBD8"

                            st.markdown(f"""
<div style="background-color:{bg_color}; padding:8px; border-radius:5px; margin-bottom:5px; border-left: 5px solid {text_color};">
<small><b>{row['source_location']}</b></small><br>
<span style="color:{text_color}; font-weight:bold; font-size:1.1em;">{icon} {format_inr(row['final_price'])} PMT</span>
</div>
""", unsafe_allow_html=True)

            if not result:
                st.warning("No Data Found.")


        elif selected_city:
            st.info("Press 'Calculate Cost' to see pricing.")




    # --- COLUMN 3: DETAILED SLIP (Landing Cost Information) ---
    with col_right:
        st.markdown("### \U0001f4dd Landing Cost Information")

        # Display details only if a calculation has been performed and result is available
        if selected_city and calc_btn and 'result' in locals() and result:
            # Get best option from result
            best_opt = result.get('best_option', {})
            assessment = result.get('assessment', {})

            # Header Box
            st.markdown(f"""
<div style="background-color:#F5B041; padding:5px; text-align:center; font-weight:bold;">
{load_type.upper()} ENQUIRY DETAILS ({datetime.date.today().strftime('%d-%m-%Y')})
</div>
""", unsafe_allow_html=True)

            # Details Table Logic using Columns
            d1, d2 = st.columns([2, 1])

            with d1:
                source_name = best_opt.get('source_location', 'N/A')
                st.write(f"**From**: {source_name}")
                st.write(f"**To**: {selected_city}")
                st.write(f"**Product**: {product_name}")
                st.divider()

                # Maths
                base_price = best_opt.get('base_price', 0)
                discount = best_opt.get('discount', 0)
                transport = best_opt.get('transport_cost', 0)
                final_cost = best_opt.get('final_landed_cost', 0)
                distance = best_opt.get('distance_km', 0)

                st.write(f"Basic Rate: {format_inr(base_price)} PMT")
                st.write(f"Discount: - {format_inr(discount)}")

                tax_val = base_price * 0.18
                st.write(f"GST 18%: + {format_inr(tax_val)}")

                net_start = base_price + tax_val - discount
                st.markdown(f"**Ex-Refinery Price: {format_inr(net_start)} PMT**")

                st.info(f"\u2795 Transport: {format_inr(transport)}")

                # Show Mileage if available
                if distance > 0:
                    rate_km = transport / distance if distance > 0 else 0
                    st.caption(f"\U0001f4cf Distance: {distance:.0f} KM | Rate: \u20b9 {rate_km:.2f}/KM")

                st.success(f"**FINAL LANDING COST: {format_inr(final_cost)} PMT**")

            with d2:
                st.markdown("**Terms & Conditions**")
                st.caption("1. Price valid for 24 hours only.")
                st.caption("2. Payment: 100% Advance before dispatch.")
                st.caption("3. We do NOT arrange, pay, or refer any transporter.")
                st.caption("4. Buyer is responsible for all transport payment & issues.")
                st.caption("5. Driver/Transporter is final authority to accept/reject qty, quality, or packing.")
                st.caption("6. All halting & demurrage charges at loading point - Driver's responsibility.")
                st.caption("7. All loading & unloading charges - at Driver's cost.")
                st.caption("8. Subject to material availability.")

                st.markdown("---")
                st.markdown("\U0001f3e6 **Pay To:**")
                st.caption(f"ICICI Bank | A/C: 184105001402")
                st.caption(f"IFSC: ICIC0001841")


            # PDF GENERATION (Legacy Wrapper)
            # We keep the legacy function for now but add a generic call to the new system if needed.
            # For this interaction, we will stick to the existing visual flow but using the new robust engine is possible.

            # --- NEW: GENERATE FORMAL QUOTE (Via new System) ---
            if st.button("\U0001f680 Generate & Save Formal Quote (SQL DB)"):
                try:
                    from quotation_system.models import Quotation, QuotationItem
                    from quotation_system.pdf_maker import generate_pdf
                    from quotation_system.db import create_db_and_tables, engine
                    from sqlmodel import Session

                    # Ensure DB exists
                    create_db_and_tables()

                    # Create Session
                    with Session(engine) as session:
                        # Prepare Data
                        q_num = get_next_quote_number() # Use existing counter for ID

                        # Calc Totals
                        row_price = final_cost  # Use the variable from above
                        qty = 1.0
                        basic = qty * row_price
                        tax = basic * 0.18
                        grand = basic + tax

                        # Create Object
                        new_quote = Quotation(
                            quote_number=q_num,
                            quote_date=datetime.date.today(),
                            valid_until=datetime.date.today() + datetime.timedelta(days=1),
                            seller_name="PPS Anantams Corporation Pvt. Ltd.",
                            seller_address="04, Signet plaza Tower- B, Vadodara-390021",
                            seller_gstin="24AAHCV1611L2ZD",
                            buyer_name=selected_client_name or "Valued Client",
                            buyer_address="Billing Address...",
                            delivery_terms=f"FOR {selected_city}",
                            payment_terms="100% Advance",
                            dispatch_mode="Road",
                            subtotal=basic,
                            total_tax=tax,
                            grand_total=grand,
                            status="FINAL"
                        )

                        # Add Item
                        item = QuotationItem(
                            product_name=f"{product_name} ({load_type})",
                            description=f"Source: {source_name}",
                            quantity=qty,
                            rate=row_price,
                            total_amount=basic
                        )
                        new_quote.items = [item]

                        session.add(new_quote)
                        session.commit()
                        session.refresh(new_quote)

                        # Generate PDF
                        pdf_path = f"Formal_Quote_{new_quote.quote_number.replace('/','-')}.pdf"
                        generate_pdf(new_quote, pdf_path)

                        st.success(f"\u2705 Quote Saved to DB (ID: {new_quote.id}) and PDF Generated!")

                        # Download Button
                        with open(pdf_path, "rb") as f:
                            st.download_button("\U0001f4c4 Download Formal PDF", f, file_name=pdf_path)

                except Exception as e:
                    st.error(f"System Error: {e}")

            # Legacy PDF Logic (Kept for fallback)
            pdf_filename = f"Quote_{selected_city}_{product_grade}.pdf"
            client_name_for_pdf = selected_client_name if selected_client_name else "Valued Customer"

            # Generate quote number only once per PDF download
            if 'current_quote_no' not in st.session_state:
                st.session_state.current_quote_no = get_next_quote_number()
            quote_no = st.session_state.current_quote_no

            # Generate the file
            create_price_pdf(client_name_for_pdf, product_name, source_name, final_cost, filename=pdf_filename, quote_no=quote_no)

            # Read Bytes for Download
            with open(pdf_filename, "rb") as f:
                st.download_button(
                    label="\U0001f4c4 Download Official Quote PDF",
                    data=f,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    use_container_width=True
                )

            # Premium PDF (new branded version)
            try:
                from share_formatter import build_quote_pdf
                _premium_pdf = build_quote_pdf(
                    client_name_for_pdf or (selected_client_name or "Customer"),
                    selected_city or "",
                    product_name or "VG30",
                    100,
                    float(final_cost or 0),
                    source=source_name or "",
                    quote_no=quote_no,
                )
                if _premium_pdf:
                    st.download_button(
                        label="✨ Download Premium Branded PDF",
                        data=_premium_pdf,
                        file_name=f"PPS_Premium_Quote_{quote_no}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_premium_price_pdf",
                    )
            except Exception:
                pass

            # WHATSAPP INTEGRATION
            wa_message = f"""*PPS Anantams Price Offer* \U0001f69b
Product: {product_name}
Best Source: {source_name}
Est. Distance: {distance:.0f} KM

*Final Landed Rate: {format_inr(final_cost)} PMT*

_Terms: 100% Advance. Valid for 24 Hrs._
"""
            encoded_wa = urllib.parse.quote(wa_message)
            wa_link = f"https://wa.me/?text={encoded_wa}"

            st.markdown(f"""
<a href="{wa_link}" target="_blank" style="text-decoration:none;">
<button style="width:100%; border:none; background-color:#25D366; color:white; padding:10px; border-radius:5px; margin-top:5px; font-weight:bold; cursor:pointer;">
\U0001f4ac Share via WhatsApp
</button>
</a>
""", unsafe_allow_html=True)
        elif selected_city:
            st.info("Select configuration and click 'Calculate Cost' to see detailed information.")
        else:
            st.info("Please select a city to begin.")

    # ── Smart navigation: contextual next steps ──
    try:
        from navigation_engine import render_next_step_cards
        render_next_step_cards("🧮 Pricing Calculator")
        st.session_state["_ns_rendered_inline"] = True
    except Exception:
        pass
