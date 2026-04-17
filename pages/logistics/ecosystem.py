import streamlit as st
import pandas as pd
import os
import datetime
from pathlib import Path

from party_master import (
    load_suppliers, save_suppliers, add_supplier,
    load_customers, save_customers, add_customer,
    load_services, save_services, add_service_provider,
    import_sales_from_excel, toggle_purchase_party,
    SUPPLIER_CATEGORIES, CUSTOMER_CATEGORIES, SERVICE_CATEGORIES
)
from distance_matrix import get_state_by_city


def render():
    _today_str = datetime.date.today().strftime("%d %b %Y")
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            border-bottom:2px solid var(--sandal,#e8dcc8);
            padding-bottom:6px;
            margin-bottom:10px;">
  <div style="display:flex;align-items:baseline;gap:10px;">
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">👥 Ecosystem Management</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">Technology</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.header("👥 Ecosystem Management")
    st.caption("Manage Suppliers, Customers, and Logistics Partners in your ecosystem.")

    # --- ANALYTICS DASHBOARD (NEW) ---
    with st.expander("📊 Ecosystem Analytics (Head Count Summary)", expanded=True):
        st.caption("Total counts of Suppliers, Service Providers, and Customers by Category, City, and State.")

        # Load all data
        all_suppliers = load_suppliers()
        all_services = load_services()
        all_customers = load_customers()

        # Create Columns for High Level Stats
        stat1, stat2, stat3, stat4 = st.columns(4)
        total_partners = len(all_suppliers) + len(all_services) + len(all_customers)
        stat1.metric("🌍 Total Ecosystem", total_partners)
        stat2.metric("🏭 Suppliers", len(all_suppliers))
        stat3.metric("🚚 Logistics", len(all_services))
        stat4.metric("💰 Customers", len(all_customers))

        st.markdown("---")

        # Prepare Data for Aggregation
        # Combine Suppliers + Services for "Partner Ecosystem" analysis
        ecosystem_data = []

        def get_clean_state(raw_city):
            if not raw_city: return "Unknown"
            # Cleaning city name (e.g. "Mumbai (Chembur)" -> "Mumbai")
            clean_city = raw_city.split('(')[0].strip()

            # Manual Mapping for specific cases
            if 'Navi Mumbai' in raw_city: return 'Maharashtra'
            if 'Chembur' in raw_city: return 'Maharashtra'
            if 'Taloja' in raw_city: return 'Maharashtra'
            if 'Kandla' in raw_city or 'Mundra' in raw_city: return 'Gujarat'
            if 'Haldia' in raw_city: return 'West Bengal'
            if 'Bhatinda' in raw_city: return 'Punjab'

            # Standard Lookup
            state = get_state_by_city(clean_city)

            # Fallback for capitals if needed
            if state == "Unknown":
                if clean_city in ['Delhi', 'New Delhi']: return 'Delhi'
                if clean_city == 'Guwahati': return 'Assam'
                if clean_city == 'Bhubaneswar': return 'Odisha'
                if clean_city == 'Kolkata': return 'West Bengal'

            return state

        for s in all_suppliers:
            city_val = s.get('city', 'Unknown')
            ecosystem_data.append({
                'Name': s.get('name'),
                'Category': s.get('type'),
                'City': city_val,
                'State': get_clean_state(city_val),
                'Group': 'Supplier'
            })

        for s in all_services:
            city_val = s.get('city', 'Unknown')
            ecosystem_data.append({
                'Name': s.get('name'),
                'Category': s.get('category'),
                'City': city_val,
                'State': get_clean_state(city_val),
                'Group': 'Logistics'
            })

        for c in all_customers:
             city_val = c.get('city', 'Unknown')
             ecosystem_data.append({
                'Name': c.get('name'),
                'Category': c.get('category', 'General'), # Use category, fallback to General
                'City': city_val,
                'State': get_clean_state(city_val),
                'Group': 'Customer'
            })

        if ecosystem_data:
            df_eco = pd.DataFrame(ecosystem_data)

            # TABS for specific breakdowns
            ana_tab1, ana_tab2, ana_tab3 = st.tabs(["📂 By Category", "🏙️ By City", "🗺️ By State"])

            with ana_tab1:
                st.subheader("Head Count by Category")
                cat_counts = df_eco['Category'].value_counts().reset_index()
                cat_counts.columns = ['Category', 'Count']
                st.dataframe(cat_counts, use_container_width=True, hide_index=True)

                # Bar Chart
                st.bar_chart(cat_counts.set_index('Category'))

            with ana_tab2:
                st.subheader("Head Count by City")
                city_counts = df_eco['City'].value_counts().reset_index()
                city_counts.columns = ['City', 'Count']
                st.dataframe(city_counts, use_container_width=True, hide_index=True)

            with ana_tab3:
                st.subheader("Head Count by State")
                state_counts = df_eco['State'].value_counts().reset_index()
                state_counts.columns = ['State', 'Count']
                st.dataframe(state_counts, use_container_width=True, hide_index=True)

                # Show Map visualization if possible (simple scatter map requires lat/lon, skipping for now to keep it simple stats)

        else:
            st.info("No ecosystem data available to analyze.")

    # Sub-tabs
    m_tab1, m_tab2, m_tab3 = st.tabs(["🏭 Source & Supply", "💰 Sales & Clients", "🚚 Logistics & Services"])

    # ======== 1. SOURCE & SUPPLY ========
    with m_tab1:
        st.subheader("Manage Sources (Exporters, Importers, Mfg)")

        # Display Section
        suppliers = load_suppliers()
        if suppliers:
            # Convert to DF for easy viewing
            s_df = pd.DataFrame(suppliers)

            # --- FILTERS & SORTING ---
            c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
            with c_f1:
                # Filter by Category
                cat_filter = st.multiselect("Filter Category", SUPPLIER_CATEGORIES, default=["Importer of India"])
            with c_f2:
                # Filter by City
                unique_cities = sorted(list(set([s.get('city', '') for s in suppliers if s.get('city')])))
                city_filter = st.multiselect("Filter by City", unique_cities)
            with c_f3:
                # Sorting
                sort_order = st.radio("Sort Name", ["A-Z", "Z-A"], horizontal=True)

            # Apply Filters
            if not cat_filter:
                cat_filter = SUPPLIER_CATEGORIES # Show all if none selected

            filtered_s = [s for s in suppliers if s.get('type') in cat_filter or s.get('type') in ['Bulk', 'Bulk/PSU', 'Drum']]

            if city_filter:
                filtered_s = [s for s in filtered_s if s.get('city') in city_filter]

            # Apply Sorting
            reverse_sort = True if sort_order == "Z-A" else False
            filtered_s = sorted(filtered_s, key=lambda x: x.get('name', '').lower(), reverse=reverse_sort)

            if filtered_s:
                s_df = pd.DataFrame(filtered_s)

                # Standardize Columns
                required_cols = ['name', 'type', 'city', 'contact', 'details', 'gstin']
                for col in required_cols:
                    if col not in s_df.columns:
                        s_df[col] = "" # Fill missing cols

                # Select & Rename for Display
                display_df = s_df[required_cols].copy()
                display_df.columns = ["Company Name", "Category", "City", "Contact / Email", "Address / Details", "GSTIN"]

                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No suppliers found in selected categories.")

        st.markdown("---")
        st.markdown("#### ➕ Add New Source")
        with st.form("add_supplier_form"):
            try:
                from components.autosuggest import city_picker as _city_picker
                _have_ecos_city_picker = True
            except Exception:
                _have_ecos_city_picker = False
            c1, c2 = st.columns(2)
            with c1:
                s_name = st.text_input("Company Name")
                s_cat = st.selectbox("Category", SUPPLIER_CATEGORIES)
                if _have_ecos_city_picker:
                    s_city = _city_picker(key="ecos_supp_city", label="City/Location")
                else:
                    s_city = st.text_input("City/Location")
            with c2:
                s_contact = st.text_input("Contact Number/Person")
                s_gst = st.text_input("GSTIN")
                s_details = st.text_area("Extra Details (Loading Person/Notes)", height=40)

            if st.form_submit_button("Add Source"):
                if s_name and s_cat:
                    add_supplier(s_name, s_cat, s_city, s_contact, s_gst, s_details)
                    st.success(f"Added {s_name} to database!")
                    st.rerun()
                else:
                    st.error("Name and Category are required.")

    # ======== 2. SALES & CLIENTS ========
    with m_tab2:
        st.subheader("Manage Customers (Contractors & Traders)")

        customers = load_customers()

        # Stats
        if customers:
            total_c = len(customers)
             # View Data
            st.markdown("#### 📋 Client Directory")

            # --- FILTERS & SORTING ---
            cf_1, cf_2, cf_3 = st.columns([2, 1, 1])
            with cf_1:
                c_filter = st.selectbox("Filter Category", ["All"] + CUSTOMER_CATEGORIES)
            with cf_2:
                # Get unique states from customers
                cust_states = sorted(list(set([c.get('state', '') for c in customers if c.get('state')])))
                s_filter = st.multiselect("Filter State", cust_states)
            with cf_3:
                cust_sort = st.radio("Sort", ["A-Z", "Z-A"], horizontal=True, key="cust_sort")

            filtered_c = customers
            if c_filter != "All":
                filtered_c = [c for c in filtered_c if c.get('category') == c_filter]

            if s_filter:
                filtered_c = [c for c in filtered_c if c.get('state') in s_filter]

            # Apply Sorting
            rev_cust = True if cust_sort == "Z-A" else False
            filtered_c = sorted(filtered_c, key=lambda x: x.get('name', '').lower(), reverse=rev_cust)

            if filtered_c:
                c_df = pd.DataFrame(filtered_c)
                # Standardize
                req_cols_c = ['name', 'category', 'city', 'state', 'contact', 'gstin']
                for col in req_cols_c:
                    if col not in c_df.columns:
                        c_df[col] = ""

                display_c = c_df[req_cols_c].copy()
                display_c.columns = ["Client Name", "Segment", "City", "State", "Contact / Mobile", "GSTIN"]
                st.dataframe(display_c, use_container_width=True, hide_index=True)
            else:
                st.info("No clients found matching criteria.")

        st.markdown("---")
        st.markdown("#### ➕ Add New Client")
        with st.form("add_client_form"):
            ac1, ac2 = st.columns(2)
            try:
                from components.autosuggest import city_picker, state_picker
                _auto = True
            except Exception:
                _auto = False
            with ac1:
                c_name = st.text_input("Client/Company Name")
                c_cat = st.selectbox("Category", CUSTOMER_CATEGORIES)
                if _auto:
                    c_city = city_picker(key="eco_cust_city", label="City")
                    c_state = state_picker(key="eco_cust_state", label="State")
                else:
                    c_city = st.text_input("City")
                    c_state = st.selectbox("State", ["Gujarat", "Maharashtra", "Rajasthan", "MP", "Delhi", "Punjab", "Haryana", "UP", "South India", "Other"])
            with ac2:
                c_contact = st.text_input("Phone/Mobile")
                c_gst = st.text_input("GSTIN")
                c_addr = st.text_area("Full Address")

            if st.form_submit_button("Add Client"):
                if c_name:
                    add_customer(c_name, c_cat, c_city, c_state, c_contact, c_gst, c_addr)
                    st.success(f"Added {c_name}!")
                    st.rerun()
                else:
                    st.error("Name required.")

        # Excel Import (Compact)
        with st.expander("📤 Import from Excel (Bulk Upload)"):
            st.warning("Excel columns must include: Name, City, State, Contact")
            up_file = st.file_uploader("Upload Excel", type=['xlsx'])
            def_cat = st.selectbox("Default Category for Import", CUSTOMER_CATEGORIES)
            if up_file and st.button("Process Import"):
                cnt, msg = import_sales_from_excel(up_file, def_cat)
                if cnt > 0:
                    st.success(f"Imported {cnt} records!")
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")

    # ======== 3. LOGISTICS & SERVICES ========
    with m_tab3:
        st.subheader("Manage Services (Transporters, CHA, Terminals)")

        services = load_services()

        # --- FILTERS & SORTING ---
        sf_1, sf_2, sf_3 = st.columns([2, 1, 1])
        with sf_1:
            serv_cat_filter = st.multiselect("Filter Service Type", SERVICE_CATEGORIES, default=["Transporter - Bulk"])
        with sf_2:
            serv_cities = sorted(list(set([s.get('city', '') for s in services if s.get('city')])))
            serv_city_filter = st.multiselect("Filter Hub/City", serv_cities)
        with sf_3:
             serv_sort = st.radio("Sort", ["A-Z", "Z-A"], horizontal=True, key="serv_sort")

        filtered_services = services
        # Apply Category Filter
        if not serv_cat_filter:
            serv_cat_filter = SERVICE_CATEGORIES
        filtered_services = [s for s in services if s.get('category') in serv_cat_filter]

        # Apply City Filter
        if serv_city_filter:
            filtered_services = [s for s in filtered_services if s.get('city') in serv_city_filter]

        # Apply Sorting
        rev_serv = True if serv_sort == "Z-A" else False
        filtered_services = sorted(filtered_services, key=lambda x: x.get('name', '').lower(), reverse=rev_serv)

        if filtered_services:
            srv_df = pd.DataFrame(filtered_services)
            # Standardize
            req_cols_s = ['name', 'category', 'city', 'contact', 'details']
            for col in req_cols_s:
                if col not in srv_df.columns:
                    srv_df[col] = ""

            display_s = srv_df[req_cols_s].copy()
            display_s.columns = ["Provider Name", "Service Type", "Hub / City", "Contact Info", "Details / Routes"]
            st.dataframe(display_s, use_container_width=True, hide_index=True)
        else:
            st.info("No service providers found matching criteria.")

        st.markdown("---")
        st.markdown("#### ➕ Add Service Provider")

        with st.form("add_service_form"):
            sc1, sc2 = st.columns(2)
            with sc1:
                svc_name = st.text_input("Name (Transporter/CHA/Person)")
                svc_cat = st.selectbox("Service Type", SERVICE_CATEGORIES)
                svc_city = st.text_input("Base Location/Port")
            with sc2:
                svc_contact = st.text_input("Contact Number")
                svc_details = st.text_area("Details (Vehicle Counts, Specialization, Loading Person Name)", help="Enter name of loading person or specific CHA contact here")

            if st.form_submit_button("Add Service Provider"):
                if svc_name:
                    add_service_provider(svc_name, svc_cat, svc_city, svc_contact, svc_details)
                    st.success("Added successfully!")
                    st.rerun()
                else:
                    st.error("Name required.")

        st.markdown("---")

        # Two columns: Bulk and Drum
        bulk_col, drum_col = st.columns(2)

        with bulk_col:
            st.markdown("### 🏭 Bulk Importers (10,000+ MT)")
            st.caption("Select parties for bulk purchase - Limited options")

            bulk_parties = load_suppliers()
            bulk_only = [p for p in bulk_parties if p['type'] in ['Bulk', 'Bulk/PSU']]

            for p in bulk_only:
                col_a, col_b, col_c = st.columns([0.5, 2, 1])
                with col_a:
                    checked = st.checkbox("Active", value=p.get('marked_for_purchase', True), key=f"bulk_{p['name'][:20]}", label_visibility="collapsed")
                    if checked != p.get('marked_for_purchase', True):
                        toggle_purchase_party(p['name'], checked)
                with col_b:
                    st.markdown(f"**{p['name']}**")
                    st.caption(f"📍 {p['city']} | 📦 {p['qty_mt']:,} MT")
                with col_c:
                    if checked:
                        st.success("✓ Active")
                    else:
                        st.warning("✗ Inactive")

        with drum_col:
            st.markdown("### 🛢️ Drum Importers (<10,000 MT)")
            st.caption("Open purchase from all - Scroll to view all")

            drum_only = [p for p in bulk_parties if p.get('type') in ['Drum', 'Indian Importer - Drum']]

            # Display in scrollable container
            if drum_only:
                drum_df = pd.DataFrame(drum_only)
                for col in ['name', 'qty_mt', 'city', 'marked_for_purchase']:
                     if col not in drum_df.columns:
                         drum_df[col] = False if col == 'marked_for_purchase' else ""

                drum_df = drum_df[['name', 'qty_mt', 'city', 'marked_for_purchase']]
                drum_df.columns = ['Company Name', 'Qty (MT)', 'City', 'Active']
                drum_df['Active'] = drum_df['Active'].apply(lambda x: '✓' if x else '✗')
                st.dataframe(drum_df, use_container_width=True, hide_index=True, height=400)
            else:
                st.info("No Drum Importers found.")

        # Add new purchase party
        st.markdown("---")
        st.subheader("➕ Add New Purchase Party")

        add_col1, add_col2, add_col3, add_col4 = st.columns(4)
        with add_col1:
            new_name = st.text_input("Company Name", key="new_purchase_name")
        with add_col2:
            new_type = st.selectbox("Type", SUPPLIER_CATEGORIES, key="new_purchase_type")
        with add_col3:
            new_city = st.selectbox("City", ["Mumbai", "Kandla", "Chennai", "Other"], key="new_purchase_city")
        with add_col4:
            new_qty = st.number_input("Est. Qty (MT)", min_value=0, value=1000, key="new_purchase_qty")

        add_col5, add_col6 = st.columns(2)
        with add_col5:
            new_contact = st.text_input("Contact Number", key="new_purchase_contact")
        with add_col6:
            new_gstin = st.text_input("GSTIN", key="new_purchase_gstin")

        if st.button("➕ Add Purchase Party", type="primary"):
            if new_name:
                # Using add_supplier wrapper
                add_supplier(new_name, new_type, new_city, new_contact, new_gstin)
                st.success(f"✅ Added {new_name} as {new_type} supplier!")
                st.rerun()
            else:
                st.error("Please enter company name")

    # ======== SALES PARTIES ========
    with m_tab2:
        st.subheader("💰 Sales Parties - Your Customers")

        sales_parties = load_customers()

        if sales_parties:
            sales_summary = {'total': len(sales_parties)}
            st.metric("Total Customers", sales_summary['total'])

            sales_df = pd.DataFrame(sales_parties)
            st.dataframe(sales_df, use_container_width=True, hide_index=True)
        else:
            st.info("No sales parties added yet. Add manually or import from Excel below.")

        # Add new sales party
        st.markdown("---")
        st.subheader("➕ Add New Sales Party / Customer")

        s_col1, s_col2, s_col3 = st.columns(3)
        try:
            from components.autosuggest import city_picker, state_picker
            _auto_s = True
        except Exception:
            _auto_s = False
        with s_col1:
            s_name = st.text_input("Customer Name", key="new_sales_name")
            s_cat = st.selectbox("Category", CUSTOMER_CATEGORIES, key="new_sales_cat")
        with s_col2:
            if _auto_s:
                s_city = city_picker(key="new_sales_city", label="City")
                s_state = state_picker(key="new_sales_state", label="State")
            else:
                s_city = st.text_input("City", key="new_sales_city")
                s_state = st.selectbox("State", ["Gujarat", "Maharashtra", "Rajasthan", "Madhya Pradesh", "Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Delhi", "Uttar Pradesh", "Bihar", "West Bengal", "Other"], key="new_sales_state")
            s_contact = st.text_input("Contact Number", key="new_sales_contact")
        with s_col3:
            s_gstin = st.text_input("GSTIN", key="new_sales_gstin")
            s_address = st.text_input("Address", key="new_sales_address")

        if st.button("➕ Add Customer", type="primary", key="add_sales_btn"):
            if s_name and s_city:
                # Using add_customer imported function
                add_customer(s_name, s_cat, s_city, s_state, s_contact, s_gstin, s_address)
                st.success(f"✅ Customer Saved (Added/Updated): {s_name} ({s_cat})")
                st.rerun()
            else:
                st.error("Please enter customer name and city")

    # ======== IMPORT/EXPORT ========
    with m_tab3:
        st.subheader("📤 Import / Export Party Data")

        imp_col, exp_col = st.columns(2)

        with imp_col:
            st.markdown("### 📥 Import Sales Parties from Excel")
            st.caption("Upload Excel file with columns: Company Name, City, State, Contact, GSTIN, Address")

            uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'], key="sales_excel_upload")

            imp_def_cat = st.selectbox("Default Category (if missing in Excel)", CUSTOMER_CATEGORIES, key="imp_def_cat_sel")

            if uploaded_file is not None:
                if st.button("📥 Import & Merge Data"):
                    # Save temp file
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    msg, status = import_sales_from_excel(tmp_path, default_category=imp_def_cat)

                    if status == "Success":
                        st.success(f"✅ Data Processed: {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ Import failed: {status}")

                    os.remove(tmp_path)

            st.markdown("---")
            st.markdown("**Sample Excel Format:**")
            sample_data = {
                'Company Name': ['ABC Infra Ltd', 'XYZ Construction'],
                'City': ['Ahmedabad', 'Surat'],
                'State': ['Gujarat', 'Gujarat'],
                'Contact': ['9876543210', '9876543211'],
                'GSTIN': ['24ABCDE1234F1Z5', '24FGHIJ5678K2Z6'],
                'Address': ['123 Main Road', '456 Highway']
            }
            st.dataframe(pd.DataFrame(sample_data), use_container_width=True, hide_index=True)

        with exp_col:
            st.markdown("### 📤 Export Party Data")

            if st.button("📤 Export Purchase Parties"):
                purchase_df = pd.DataFrame(load_suppliers())
                st.session_state["_eco_export_purchase"] = purchase_df.to_csv(index=False)
                st.rerun()

            if st.session_state.get("_eco_export_purchase"):
                st.download_button(
                    "⬇️ Download Purchase Parties CSV",
                    data=st.session_state["_eco_export_purchase"],
                    file_name="purchase_parties.csv",
                    mime="text/csv"
                )
                if st.button("Clear Purchase Export", key="clear_eco_export_purchase"):
                    st.session_state.pop("_eco_export_purchase", None)
                    st.rerun()

            if st.button("📤 Export Sales Parties"):
                sales_df = pd.DataFrame(load_customers())
                if not sales_df.empty:
                    st.session_state["_eco_export_sales"] = sales_df.to_csv(index=False)
                else:
                    st.session_state["_eco_export_sales"] = None
                    st.warning("No sales parties to export")
                st.rerun()

            if st.session_state.get("_eco_export_sales"):
                st.download_button(
                    "⬇️ Download Sales Parties CSV",
                    data=st.session_state["_eco_export_sales"],
                    file_name="sales_parties.csv",
                    mime="text/csv"
                )
                if st.button("Clear Sales Export", key="clear_eco_export_sales"):
                    st.session_state.pop("_eco_export_sales", None)
                    st.rerun()
