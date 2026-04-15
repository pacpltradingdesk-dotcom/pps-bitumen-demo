"""
Document Management Dashboard — PPS Anantams v2.0
===================================================

4 dashboard pages: Purchase Orders, Sales Orders, Payment Orders, Party Master.
Each page has a form for creating new documents + a list view of existing ones.

Enhancements (v2.0):
- FY-based doc numbering (FY2526/PO/0001)
- Deal auto-fill for PO/SO
- Transporter dropdown from transporters table
- LR No, Reference No, Date pickers
- Payment mode, due dates, status tracking
- Send Email / Send WhatsApp buttons
- Green/Yellow/Red party completion status
- Transporter party type in Party Master
"""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta, date

IST = timezone(timedelta(hours=5, minutes=30))

# ── Hero gradient (matches other command_intel pages) ────────────────────

_HERO_CSS = """
<style>
.doc-hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    padding: 1.2rem 1.5rem; border-radius: 12px; margin-bottom: 1rem;
}
.doc-hero h2 { color: #fff; margin: 0 0 0.3rem 0; font-size: 1.4rem; }
.doc-hero p  { color: #cbd5e1; margin: 0; font-size: 0.9rem; }
</style>
"""


def _now_ist_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _format_inr_display(amount) -> str:
    """Simple INR formatting for display in Streamlit."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return str(amount)
    if amount < 0:
        return f"-\u20b9 {abs(amount):,.2f}"
    return f"\u20b9 {amount:,.2f}"


def _load_transporters() -> list:
    """Load active transporters from DB."""
    try:
        from database import get_all_transporters
        return get_all_transporters(active_only=True)
    except Exception:
        return []


def _load_deals() -> list:
    """Load recent active deals for auto-fill."""
    from database import get_connection, _rows_to_list
    with get_connection() as conn:
        return _rows_to_list(
            conn.execute(
                "SELECT id, deal_number, grade, quantity_mt, packaging, "
                "buy_price_per_mt, sell_price_per_mt, source_location, destination, "
                "supplier_id, customer_id "
                "FROM deals WHERE status = 'active' ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
        )


def _status_color(status: str) -> str:
    """Return colored status badge HTML."""
    colors = {
        "Paid": "#16a34a", "Received": "#16a34a",
        "Part-paid": "#eab308", "Part-received": "#eab308",
        "Pending": "#dc2626",
    }
    c = colors.get(status, "#94a3b8")
    return f'<span style="color:{c};font-weight:bold">{status}</span>'


# ═══════════════════════════════════════════════════════════════════════════
# PURCHASE ORDER PAGE
# ═══════════════════════════════════════════════════════════════════════════

def render_purchase_order():
    """Render the Purchase Order generator + list page."""
    # Phase 2: standardized refresh bar (clears caches + reruns)
    try:
        from components.refresh_bar import render_refresh_bar
        render_refresh_bar('documents')
    except Exception:
        pass
    # Phase 4: active customer banner — shows persistent customer context
    try:
        from navigation_engine import render_active_context_strip
        render_active_context_strip()
    except Exception:
        pass
    st.markdown(_HERO_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="doc-hero">'
        '<h2>Purchase Orders</h2>'
        '<p>Generate and manage purchase orders to suppliers — FY-based numbering</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_create, tab_list = st.tabs(["Create New PO", "PO History"])

    with tab_create:
        _po_create_form()

    with tab_list:
        _po_list_view()


def _po_create_form():
    """Purchase Order creation form with deal auto-fill and transporter dropdown."""
    from database import (
        get_connection, _rows_to_list, insert_purchase_order,
        get_next_doc_number,
    )
    from document_pdf_engine import generate_po_pdf, save_pdf_to_archive

    # Load suppliers
    with get_connection() as conn:
        suppliers = _rows_to_list(
            conn.execute("SELECT id, name, gstin, pan, city, state, contact, address "
                         "FROM suppliers WHERE is_active = 1 ORDER BY name").fetchall()
        )

    if not suppliers:
        st.warning("No suppliers found. Add suppliers first.")
        return

    transporters = _load_transporters()
    deals = _load_deals()
    supplier_names = [s["name"] for s in suppliers]

    # ── Deal auto-fill ───────────────────────────────────────────────────
    col_deal, col_date, col_ref = st.columns(3)
    with col_deal:
        deal_options = ["None"] + [
            f"{d['deal_number']} — {d.get('grade', '')} {d.get('quantity_mt', '')} MT"
            for d in deals
        ]
        selected_deal = st.selectbox("Link to Deal", deal_options, key="po_deal")
        deal_id = None
        deal_ref = ""
        deal_data = {}
        if selected_deal != "None":
            idx = deal_options.index(selected_deal) - 1
            deal_data = deals[idx]
            deal_id = deal_data["id"]
            deal_ref = deal_data.get("deal_number", "")

    with col_date:
        po_date = st.date_input("PO Date", value=date.today(), key="po_date")

    with col_ref:
        reference_no = st.text_input("Reference No", value=deal_ref, key="po_ref")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Supplier Details")
        # Auto-select supplier from deal
        default_idx = 0
        if deal_data.get("supplier_id"):
            for i, s in enumerate(suppliers):
                if s["id"] == deal_data["supplier_id"]:
                    default_idx = i
                    break
        selected_supplier = st.selectbox("Select Supplier", supplier_names,
                                          index=default_idx, key="po_supplier")
        supplier = next((s for s in suppliers if s["name"] == selected_supplier), {})

        if supplier:
            st.caption(f"GSTIN: {supplier.get('gstin', 'N/A')}  |  "
                       f"PAN: {supplier.get('pan', 'N/A')}")
            st.caption(f"City: {supplier.get('city', '')}  |  "
                       f"State: {supplier.get('state', '')}")

            missing = []
            for f in ("gstin", "pan", "city", "state", "contact"):
                if not supplier.get(f):
                    missing.append(f.upper())
            if missing:
                st.warning(f"Missing master data: {', '.join(missing)}")

    with col2:
        st.subheader("Material Details")
        # Auto-fill from deal
        default_product = "BITUMEN VG30"
        default_packing = "BULK"
        default_qty = 20.0
        default_rate = 35000.0
        if deal_data:
            grade = deal_data.get("grade", "")
            if "VG40" in str(grade).upper():
                default_product = "BITUMEN VG40"
            elif "CRMB 55" in str(grade).upper():
                default_product = "CRMB 55"
            elif "CRMB 60" in str(grade).upper():
                default_product = "CRMB 60"
            packing = deal_data.get("packaging", "")
            if "DRUM" in str(packing).upper():
                default_packing = "DRUM"
            if deal_data.get("quantity_mt"):
                default_qty = float(deal_data["quantity_mt"])
            if deal_data.get("buy_price_per_mt"):
                default_rate = float(deal_data["buy_price_per_mt"])

        product_opts = ["BITUMEN VG30", "BITUMEN VG40", "CRMB 55", "CRMB 60"]
        product = st.selectbox("Product", product_opts,
                                index=product_opts.index(default_product), key="po_product")
        packing_opts = ["BULK", "DRUM"]
        packing = st.selectbox("Packing", packing_opts,
                                index=packing_opts.index(default_packing), key="po_packing")

    col_a, col_b = st.columns(2)
    with col_a:
        quantity = st.number_input("Quantity (MT)", min_value=0.001, value=default_qty,
                                   step=0.001, format="%.3f", key="po_qty")
    with col_b:
        rate = st.number_input("Rate per MT (\u20b9)", min_value=0.0, value=default_rate,
                               step=100.0, format="%.2f", key="po_rate")

    gst_amount = quantity * rate * 0.18
    total_amount = quantity * rate + gst_amount

    col_e, col_f, col_g = st.columns(3)
    with col_e:
        st.metric("Subtotal", _format_inr_display(quantity * rate))
    with col_f:
        st.metric("GST @18%", _format_inr_display(gst_amount))
    with col_g:
        st.metric("Total Amount", _format_inr_display(total_amount))

    st.divider()
    st.subheader("Logistics Details")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        vehicle_no = st.text_input("Vehicle Number", key="po_vehicle")
        # Auto-fill loading point from deal
        default_loading = deal_data.get("source_location", "") if deal_data else ""
        loading_point = st.text_input("Loading Point", value=default_loading, key="po_loading")
    with col_l2:
        # Transporter dropdown
        transporter_names = ["(Manual Entry)"] + [t["name"] for t in transporters]
        selected_transporter = st.selectbox("Transporter", transporter_names, key="po_transporter_sel")
        if selected_transporter == "(Manual Entry)":
            transporter = st.text_input("Transporter Name", key="po_transporter_manual")
            transporter_id = None
        else:
            transporter = selected_transporter
            transporter_id = next((t["id"] for t in transporters if t["name"] == selected_transporter), None)

        default_delivery = deal_data.get("destination", "") if deal_data else ""
        delivery_point = st.text_input("Delivery Point", value=default_delivery, key="po_delivery")

    lr_no = st.text_input("LR Number (Lorry Receipt)", key="po_lr_no")
    notes = st.text_area("Additional Notes", key="po_notes", height=60)

    st.divider()

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("Generate PO & Download PDF", type="primary", key="po_generate",
                      use_container_width=True):
            po_number = get_next_doc_number("PO")

            po_data = {
                "supplier": {
                    "name": supplier.get("name", ""),
                    "gstin": supplier.get("gstin", ""),
                    "pan": supplier.get("pan", ""),
                    "address": supplier.get("address", ""),
                    "city": supplier.get("city", ""),
                    "state": supplier.get("state", ""),
                    "contact": supplier.get("contact", ""),
                },
                "items": [{
                    "product": product,
                    "hsn": "27132000",
                    "packing": packing,
                    "quantity": quantity,
                    "rate": rate,
                    "gst_rate": 18,
                }],
                "logistics": {
                    "vehicle_no": vehicle_no,
                    "transporter": transporter,
                    "loading_point": loading_point,
                    "delivery_point": delivery_point,
                    "lr_no": lr_no,
                },
            }

            try:
                pdf_bytes = generate_po_pdf(po_data, po_number, deal_ref)
                pdf_path = save_pdf_to_archive(pdf_bytes, "PO", po_number)

                insert_purchase_order({
                    "po_number": po_number,
                    "deal_id": deal_id,
                    "supplier_id": supplier.get("id"),
                    "supplier_name": supplier.get("name", ""),
                    "supplier_gstin": supplier.get("gstin", ""),
                    "supplier_address": f"{supplier.get('city', '')}, {supplier.get('state', '')}",
                    "items_json": po_data["items"],
                    "logistics_json": po_data["logistics"],
                    "totals_json": {
                        "subtotal": quantity * rate,
                        "gst": gst_amount,
                        "total": total_amount,
                    },
                    "notes": notes,
                    "status": "confirmed",
                    "pdf_path": pdf_path,
                    "po_date": str(po_date),
                    "reference_no": reference_no,
                    "lr_no": lr_no,
                    "transporter_id": transporter_id,
                })

                st.success(f"PO **{po_number}** generated successfully!")
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"{po_number.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    key="po_download",
                )
            except Exception as e:
                st.error(f"Error generating PO: {e}")

    with col_btn2:
        if st.button("Save as Draft", key="po_draft", use_container_width=True):
            po_number = get_next_doc_number("PO")
            insert_purchase_order({
                "po_number": po_number,
                "deal_id": deal_id,
                "supplier_id": supplier.get("id"),
                "supplier_name": supplier.get("name", ""),
                "supplier_gstin": supplier.get("gstin", ""),
                "items_json": [{
                    "product": product, "packing": packing,
                    "quantity": quantity, "rate": rate, "gst_rate": 18,
                }],
                "logistics_json": {
                    "vehicle_no": vehicle_no, "transporter": transporter,
                    "loading_point": loading_point, "delivery_point": delivery_point,
                    "lr_no": lr_no,
                },
                "totals_json": {
                    "subtotal": quantity * rate,
                    "gst": gst_amount,
                    "total": total_amount,
                },
                "notes": notes,
                "status": "draft",
                "po_date": str(po_date),
                "reference_no": reference_no,
                "lr_no": lr_no,
                "transporter_id": transporter_id,
            })
            st.info(f"Draft PO **{po_number}** saved.")


def _po_list_view():
    """List all purchase orders."""
    from database import get_all_purchase_orders

    pos = get_all_purchase_orders(limit=200)
    if not pos:
        st.info("No purchase orders yet. Create one in the 'Create New PO' tab.")
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filter = st.selectbox("Filter by Status", ["All", "draft", "confirmed", "cancelled"],
                                     key="po_list_status")
    with col_f2:
        search = st.text_input("Search by PO# or Supplier", key="po_list_search")

    filtered = pos
    if status_filter != "All":
        filtered = [p for p in filtered if p.get("status") == status_filter]
    if search:
        search_lower = search.lower()
        filtered = [
            p for p in filtered
            if search_lower in (p.get("po_number", "")).lower()
            or search_lower in (p.get("supplier_name", "")).lower()
        ]

    if not filtered:
        st.info("No purchase orders match your filters.")
        return

    rows = []
    for p in filtered:
        totals = p.get("totals_json", {})
        if isinstance(totals, str):
            try:
                totals = json.loads(totals)
            except Exception:
                totals = {}
        rows.append({
            "PO Number": p.get("po_number", ""),
            "Supplier": p.get("supplier_name", ""),
            "Total": _format_inr_display(totals.get("total", 0)),
            "Status": (p.get("status", "")).upper(),
            "Date": p.get("created_at", ""),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# SALES ORDER PAGE
# ═══════════════════════════════════════════════════════════════════════════

def render_sales_order():
    """Render the Sales Order generator + list page."""
    st.markdown(_HERO_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="doc-hero">'
        '<h2>Sales Orders</h2>'
        '<p>Generate and manage sales orders to customers — FY-based numbering</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_create, tab_list = st.tabs(["Create New SO", "SO History"])

    with tab_create:
        _so_create_form()

    with tab_list:
        _so_list_view()


def _so_create_form():
    """Sales Order creation form with deal auto-fill and transporter dropdown."""
    from database import (
        get_connection, _rows_to_list, insert_sales_order,
        get_next_doc_number,
    )
    from document_pdf_engine import generate_so_pdf, save_pdf_to_archive

    # Load customers
    with get_connection() as conn:
        customers = _rows_to_list(
            conn.execute("SELECT id, name, gstin, address, city, state, contact "
                         "FROM customers WHERE is_active = 1 ORDER BY name").fetchall()
        )

    if not customers:
        st.warning("No customers found. Add customers first.")
        return

    transporters = _load_transporters()
    deals = _load_deals()
    customer_names = [c["name"] for c in customers]

    # ── Deal auto-fill ───────────────────────────────────────────────────
    col_deal, col_date, col_ref = st.columns(3)
    with col_deal:
        deal_options = ["None"] + [
            f"{d['deal_number']} — {d.get('grade', '')} {d.get('quantity_mt', '')} MT"
            for d in deals
        ]
        selected_deal = st.selectbox("Link to Deal", deal_options, key="so_deal")
        deal_id = None
        deal_ref = ""
        deal_data = {}
        if selected_deal != "None":
            idx = deal_options.index(selected_deal) - 1
            deal_data = deals[idx]
            deal_id = deal_data["id"]
            deal_ref = deal_data.get("deal_number", "")

    with col_date:
        so_date = st.date_input("SO Date", value=date.today(), key="so_date")

    with col_ref:
        reference_no = st.text_input("Reference No", value=deal_ref, key="so_ref")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Customer Details")
        default_idx = 0
        if deal_data.get("customer_id"):
            for i, c in enumerate(customers):
                if c["id"] == deal_data["customer_id"]:
                    default_idx = i
                    break
        else:
            try:
                from navigation_engine import get_context
                _ctx_cust = get_context("customer_name", "") or ""
                if _ctx_cust and _ctx_cust in customer_names:
                    default_idx = customer_names.index(_ctx_cust)
            except Exception:
                pass
        selected_customer = st.selectbox("Select Customer", customer_names,
                                          index=default_idx, key="so_customer")
        customer = next((c for c in customers if c["name"] == selected_customer), {})

        if customer:
            st.caption(f"GSTIN: {customer.get('gstin', 'N/A')}")
            addr = customer.get("address", "")
            city = customer.get("city", "")
            state = customer.get("state", "")
            st.caption(f"{addr}, {city}, {state}" if addr else f"{city}, {state}")

            missing = []
            for f in ("gstin", "address", "city", "state", "contact"):
                if not customer.get(f):
                    missing.append(f.upper())
            if missing:
                st.warning(f"Missing master data: {', '.join(missing)}")

    with col2:
        st.subheader("Material Details")
        default_product = "BITUMEN VG30"
        default_packing = "BULK"
        default_qty = 20.0
        default_rate = 36000.0
        if deal_data:
            grade = deal_data.get("grade", "")
            if "VG40" in str(grade).upper():
                default_product = "BITUMEN VG40"
            elif "CRMB 55" in str(grade).upper():
                default_product = "CRMB 55"
            elif "CRMB 60" in str(grade).upper():
                default_product = "CRMB 60"
            packing = deal_data.get("packaging", "")
            if "DRUM" in str(packing).upper():
                default_packing = "DRUM"
            if deal_data.get("quantity_mt"):
                default_qty = float(deal_data["quantity_mt"])
            if deal_data.get("sell_price_per_mt"):
                default_rate = float(deal_data["sell_price_per_mt"])

        product_opts = ["BITUMEN VG30", "BITUMEN VG40", "CRMB 55", "CRMB 60"]
        product = st.selectbox("Product", product_opts,
                                index=product_opts.index(default_product), key="so_product")
        packing_opts = ["BULK", "DRUM"]
        packing = st.selectbox("Packing", packing_opts,
                                index=packing_opts.index(default_packing), key="so_packing")

    col_a, col_b = st.columns(2)
    with col_a:
        quantity = st.number_input("Quantity (MT)", min_value=0.001, value=default_qty,
                                   step=0.001, format="%.3f", key="so_qty")
    with col_b:
        rate = st.number_input("Rate per MT (\u20b9)", min_value=0.0, value=default_rate,
                               step=100.0, format="%.2f", key="so_rate")

    # 3-tier pricing helper
    with st.expander("3-Tier Pricing Helper"):
        st.caption("Suggested sell prices based on margin targets:")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.metric("Aggressive (+\u20b9500)", _format_inr_display(rate + 500))
        with col_p2:
            st.metric("Balanced (+\u20b9800)", _format_inr_display(rate + 800))
        with col_p3:
            st.metric("Premium (+\u20b91,200)", _format_inr_display(rate + 1200))

    gst_amount = quantity * rate * 0.18
    total_amount = quantity * rate + gst_amount

    col_e, col_f, col_g = st.columns(3)
    with col_e:
        st.metric("Subtotal", _format_inr_display(quantity * rate))
    with col_f:
        st.metric("GST @18%", _format_inr_display(gst_amount))
    with col_g:
        st.metric("Total Amount", _format_inr_display(total_amount))

    st.divider()
    st.subheader("Dispatch Details")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        vehicle_no = st.text_input("Vehicle Number", key="so_vehicle")
        default_loading = deal_data.get("source_location", "") if deal_data else ""
        loading_point = st.text_input("Dispatch From", value=default_loading, key="so_loading")
    with col_l2:
        transporter_names = ["(Manual Entry)"] + [t["name"] for t in transporters]
        selected_transporter = st.selectbox("Transporter", transporter_names, key="so_transporter_sel")
        if selected_transporter == "(Manual Entry)":
            transporter = st.text_input("Transporter Name", key="so_transporter_manual")
            transporter_id = None
        else:
            transporter = selected_transporter
            transporter_id = next((t["id"] for t in transporters if t["name"] == selected_transporter), None)

        default_delivery = deal_data.get("destination", "") if deal_data else ""
        delivery_point = st.text_input("Delivery To", value=default_delivery, key="so_delivery")

    lr_no = st.text_input("LR Number (Lorry Receipt)", key="so_lr_no")
    notes = st.text_area("Additional Notes", key="so_notes", height=60)

    st.divider()

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("Generate SO & Download PDF", type="primary", key="so_generate",
                      use_container_width=True):
            so_number = get_next_doc_number("SO")

            so_data = {
                "customer": {
                    "name": customer.get("name", ""),
                    "gstin": customer.get("gstin", ""),
                    "address": customer.get("address", ""),
                    "city": customer.get("city", ""),
                    "state": customer.get("state", ""),
                    "contact": customer.get("contact", ""),
                },
                "items": [{
                    "product": product,
                    "hsn": "27132000",
                    "packing": packing,
                    "quantity": quantity,
                    "rate": rate,
                    "gst_rate": 18,
                }],
                "logistics": {
                    "vehicle_no": vehicle_no,
                    "transporter": transporter,
                    "loading_point": loading_point,
                    "delivery_point": delivery_point,
                    "lr_no": lr_no,
                },
            }

            try:
                pdf_bytes = generate_so_pdf(so_data, so_number, deal_ref)
                pdf_path = save_pdf_to_archive(pdf_bytes, "SO", so_number)

                insert_sales_order({
                    "so_number": so_number,
                    "deal_id": deal_id,
                    "customer_id": customer.get("id"),
                    "customer_name": customer.get("name", ""),
                    "customer_gstin": customer.get("gstin", ""),
                    "customer_address": f"{customer.get('city', '')}, {customer.get('state', '')}",
                    "items_json": so_data["items"],
                    "logistics_json": so_data["logistics"],
                    "totals_json": {
                        "subtotal": quantity * rate,
                        "gst": gst_amount,
                        "total": total_amount,
                    },
                    "notes": notes,
                    "status": "confirmed",
                    "pdf_path": pdf_path,
                    "so_date": str(so_date),
                    "reference_no": reference_no,
                    "lr_no": lr_no,
                    "transporter_id": transporter_id,
                })

                st.success(f"SO **{so_number}** generated successfully!")
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"{so_number.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    key="so_download",
                )
            except Exception as e:
                st.error(f"Error generating SO: {e}")

    with col_btn2:
        if st.button("Save as Draft", key="so_draft", use_container_width=True):
            so_number = get_next_doc_number("SO")
            insert_sales_order({
                "so_number": so_number,
                "deal_id": deal_id,
                "customer_id": customer.get("id"),
                "customer_name": customer.get("name", ""),
                "customer_gstin": customer.get("gstin", ""),
                "items_json": [{
                    "product": product, "packing": packing,
                    "quantity": quantity, "rate": rate, "gst_rate": 18,
                }],
                "logistics_json": {
                    "vehicle_no": vehicle_no, "transporter": transporter,
                    "loading_point": loading_point, "delivery_point": delivery_point,
                    "lr_no": lr_no,
                },
                "totals_json": {
                    "subtotal": quantity * rate,
                    "gst": gst_amount,
                    "total": total_amount,
                },
                "notes": notes,
                "status": "draft",
                "so_date": str(so_date),
                "reference_no": reference_no,
                "lr_no": lr_no,
                "transporter_id": transporter_id,
            })
            st.info(f"Draft SO **{so_number}** saved.")


def _so_list_view():
    """List all sales orders."""
    from database import get_all_sales_orders

    sos = get_all_sales_orders(limit=200)
    if not sos:
        st.info("No sales orders yet. Create one in the 'Create New SO' tab.")
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filter = st.selectbox("Filter by Status", ["All", "draft", "confirmed", "cancelled"],
                                     key="so_list_status")
    with col_f2:
        search = st.text_input("Search by SO# or Customer", key="so_list_search")

    filtered = sos
    if status_filter != "All":
        filtered = [s for s in filtered if s.get("status") == status_filter]
    if search:
        search_lower = search.lower()
        filtered = [
            s for s in filtered
            if search_lower in (s.get("so_number", "")).lower()
            or search_lower in (s.get("customer_name", "")).lower()
        ]

    if not filtered:
        st.info("No sales orders match your filters.")
        return

    rows = []
    for s in filtered:
        totals = s.get("totals_json", {})
        if isinstance(totals, str):
            try:
                totals = json.loads(totals)
            except Exception:
                totals = {}
        rows.append({
            "SO Number": s.get("so_number", ""),
            "Customer": s.get("customer_name", ""),
            "Total": _format_inr_display(totals.get("total", 0)),
            "Status": (s.get("status", "")).upper(),
            "Date": s.get("created_at", ""),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAYMENT ORDER PAGE
# ═══════════════════════════════════════════════════════════════════════════

def render_payment_order():
    """Render the Payment Order generator + list page."""
    st.markdown(_HERO_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="doc-hero">'
        '<h2>Payment Orders</h2>'
        '<p>Purchase payable + sales receivable + profit summary + status tracking</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_create, tab_list = st.tabs(["Create Payment Order", "Payment History"])

    with tab_create:
        _payment_create_form()

    with tab_list:
        _payment_list_view()


def _payment_create_form():
    """Enhanced Payment Order creation form."""
    from database import (
        get_connection, _rows_to_list, insert_payment_order,
        get_next_doc_number, get_all_purchase_orders, get_all_sales_orders,
    )
    from document_pdf_engine import generate_payment_pdf, save_pdf_to_archive

    transporters = _load_transporters()

    st.subheader("Link to Existing Documents")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Purchase Side (Payable)**")
        pos = get_all_purchase_orders(status="confirmed", limit=50)
        po_options = ["Manual Entry"] + [
            f"{p['po_number']} — {p.get('supplier_name', '')}"
            for p in pos
        ]
        selected_po = st.selectbox("Select PO", po_options, key="pay_po")
        po_id = None
        po_number_ref = ""
        if selected_po != "Manual Entry":
            idx = po_options.index(selected_po) - 1
            po_id = pos[idx]["id"]
            po_number_ref = pos[idx]["po_number"]

    with col2:
        st.markdown("**Sales Side (Receivable)**")
        sos = get_all_sales_orders(status="confirmed", limit=50)
        so_options = ["Manual Entry"] + [
            f"{s['so_number']} — {s.get('customer_name', '')}"
            for s in sos
        ]
        selected_so = st.selectbox("Select SO", so_options, key="pay_so")
        so_id = None
        so_number_ref = ""
        if selected_so != "Manual Entry":
            idx = so_options.index(selected_so) - 1
            so_id = sos[idx]["id"]
            so_number_ref = sos[idx]["so_number"]

    st.divider()

    # Payment controls row
    col_mode, col_prepared, col_approved = st.columns(3)
    with col_mode:
        payment_mode = st.selectbox("Payment Mode", ["NEFT", "RTGS", "UPI", "Cheque"],
                                     key="pay_mode")
    with col_prepared:
        prepared_by = st.text_input("Prepared By", value="Admin", key="pay_prepared")
    with col_approved:
        approved_by = st.text_input("Approved By", key="pay_approved")

    st.divider()

    # Purchase details
    col_p1, col_p2 = st.columns(2)

    with col_p1:
        st.markdown("#### Purchase Payable")

        po_defaults = {}
        if po_id and selected_po != "Manual Entry":
            idx = po_options.index(selected_po) - 1
            po_rec = pos[idx]
            items = po_rec.get("items_json", [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            if items:
                po_defaults = items[0]
            po_defaults["supplier_name"] = po_rec.get("supplier_name", "")

        supplier_name = st.text_input("Supplier Name",
                                      value=po_defaults.get("supplier_name", ""),
                                      key="pay_supplier")
        buy_product = st.selectbox("Product", ["BITUMEN VG30", "BITUMEN VG40", "CRMB 55"],
                                   key="pay_buy_product")
        buy_packing = st.selectbox("Packing", ["BULK", "DRUM"], key="pay_buy_packing")
        buy_qty = st.number_input("Quantity (MT)", min_value=0.001,
                                  value=float(po_defaults.get("quantity", 20.0)),
                                  step=0.001, format="%.3f", key="pay_buy_qty")
        buy_rate = st.number_input("Buy Rate/MT (\u20b9)", min_value=0.0,
                                   value=float(po_defaults.get("rate", 35000.0)),
                                   step=100.0, format="%.2f", key="pay_buy_rate")

        purchase_due_date = st.date_input("Purchase Due Date", value=date.today(), key="pay_purch_due")
        purchase_status = st.selectbox("Purchase Status", ["Pending", "Paid", "Part-paid"],
                                        key="pay_purch_status")

        buy_subtotal = buy_qty * buy_rate
        buy_gst = buy_subtotal * 0.18
        buy_total = buy_subtotal + buy_gst
        st.metric("Purchase Total (incl. GST)", _format_inr_display(buy_total))

    with col_p2:
        st.markdown("#### Sales Receivable")

        so_defaults = {}
        if so_id and selected_so != "Manual Entry":
            idx = so_options.index(selected_so) - 1
            so_rec = sos[idx]
            items = so_rec.get("items_json", [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            if items:
                so_defaults = items[0]
            so_defaults["customer_name"] = so_rec.get("customer_name", "")

        _pay_cust_default = so_defaults.get("customer_name", "")
        if not _pay_cust_default:
            try:
                from navigation_engine import get_context
                _pay_cust_default = get_context("customer_name", "") or ""
            except Exception:
                pass
        customer_name = st.text_input("Customer Name",
                                      value=_pay_cust_default,
                                      key="pay_customer")
        sell_product = st.selectbox("Product", ["BITUMEN VG30", "BITUMEN VG40", "CRMB 55"],
                                    key="pay_sell_product")
        sell_packing = st.selectbox("Packing", ["BULK", "DRUM"], key="pay_sell_packing")
        sell_qty = st.number_input("Quantity (MT)", min_value=0.001,
                                   value=float(so_defaults.get("quantity", 20.0)),
                                   step=0.001, format="%.3f", key="pay_sell_qty")
        sell_rate = st.number_input("Sell Rate/MT (\u20b9)", min_value=0.0,
                                    value=float(so_defaults.get("rate", 36000.0)),
                                    step=100.0, format="%.2f", key="pay_sell_rate")

        sales_expected_date = st.date_input("Expected Receipt Date", value=date.today(), key="pay_sales_exp")
        sales_status = st.selectbox("Sales Status", ["Pending", "Received", "Part-received"],
                                     key="pay_sales_status")

        sell_subtotal = sell_qty * sell_rate
        sell_gst = sell_subtotal * 0.18
        sell_total = sell_subtotal + sell_gst
        st.metric("Sales Total (incl. GST)", _format_inr_display(sell_total))

    st.divider()

    # Transport section
    st.markdown("#### Transport Details")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        transporter_names = ["None"] + [t["name"] for t in transporters]
        selected_transporter = st.selectbox("Transporter", transporter_names, key="pay_transporter_sel")
        if selected_transporter == "None":
            transporter_name = st.text_input("Transporter Name (manual)", key="pay_transporter_manual")
        else:
            transporter_name = selected_transporter
    with col_t2:
        transport_amount = st.number_input("Transport Amount (\u20b9)", min_value=0.0,
                                            value=0.0, step=500.0, format="%.2f",
                                            key="pay_transport_amt")
    with col_t3:
        transport_status = st.selectbox("Transport Status", ["N/A", "Pending", "Paid"],
                                         key="pay_transport_status")

    # Profit calculation
    revenue = sell_qty * sell_rate
    cost = buy_qty * buy_rate
    net_profit = revenue - cost - transport_amount
    qty_for_margin = max(sell_qty, buy_qty, 0.001)
    margin_per_mt = net_profit / qty_for_margin
    margin_pct = (net_profit / revenue * 100) if revenue > 0 else 0

    st.markdown("#### Profit Summary")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("Revenue", _format_inr_display(revenue))
    with col_s2:
        st.metric("Net Profit", _format_inr_display(net_profit),
                  delta=f"{margin_pct:.1f}%")
    with col_s3:
        st.metric("Margin/MT", _format_inr_display(margin_per_mt))
    with col_s4:
        if margin_per_mt >= 500:
            st.success(f"Margin OK (\u20b9{margin_per_mt:,.0f}/MT)")
        else:
            st.warning(f"Low margin (\u20b9{margin_per_mt:,.0f}/MT < \u20b9500)")

    notes = st.text_area("Payment Notes", key="pay_notes", height=60)

    st.divider()

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        if st.button("Generate Payment Order PDF", type="primary", key="pay_generate",
                      use_container_width=True):
            pay_number = get_next_doc_number("PAY")

            pay_data = {
                "purchase": {
                    "party_name": supplier_name,
                    "product": buy_product,
                    "packing": buy_packing,
                    "quantity": buy_qty,
                    "rate": buy_rate,
                    "due_date": str(purchase_due_date),
                    "status": purchase_status,
                },
                "sales": {
                    "party_name": customer_name,
                    "product": sell_product,
                    "packing": sell_packing,
                    "quantity": sell_qty,
                    "rate": sell_rate,
                    "expected_date": str(sales_expected_date),
                    "status": sales_status,
                },
                "transport": {
                    "name": transporter_name,
                    "amount": transport_amount,
                    "status": transport_status,
                },
                "payment_mode": payment_mode,
                "prepared_by": prepared_by,
                "approved_by": approved_by,
                "po_number": po_number_ref,
                "so_number": so_number_ref,
            }

            try:
                pdf_bytes = generate_payment_pdf(pay_data, pay_number)
                pdf_path = save_pdf_to_archive(pdf_bytes, "PAY", pay_number)

                insert_payment_order({
                    "pay_number": pay_number,
                    "po_id": po_id,
                    "so_id": so_id,
                    "supplier_name": supplier_name,
                    "customer_name": customer_name,
                    "purchase_payable": buy_total,
                    "sales_receivable": sell_total,
                    "transport_cost": transport_amount,
                    "profit_json": {
                        "revenue": revenue,
                        "cost": cost,
                        "transport": transport_amount,
                        "net_profit": net_profit,
                        "margin_per_mt": margin_per_mt,
                        "margin_pct": margin_pct,
                    },
                    "notes": notes,
                    "status": "confirmed",
                    "pdf_path": pdf_path,
                    "payment_mode": payment_mode,
                    "purchase_due_date": str(purchase_due_date),
                    "sales_expected_date": str(sales_expected_date),
                    "purchase_status": purchase_status,
                    "sales_status": sales_status,
                    "transport_amount": transport_amount,
                    "transport_status": transport_status,
                    "prepared_by": prepared_by,
                    "approved_by": approved_by,
                    "po_number": po_number_ref,
                    "so_number": so_number_ref,
                    "transporter_name": transporter_name,
                })

                st.success(f"Payment Order **{pay_number}** generated!")
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"{pay_number.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    key="pay_download",
                )
            except Exception as e:
                st.error(f"Error generating payment order: {e}")

    with col_btn2:
        if st.button("Export to Excel", key="pay_excel", use_container_width=True):
            df = pd.DataFrame([{
                "Type": "Purchase", "Party": supplier_name,
                "Product": buy_product, "Qty MT": buy_qty,
                "Rate/MT": buy_rate, "Subtotal": buy_subtotal,
                "GST": buy_gst, "Total": buy_total,
                "Due Date": str(purchase_due_date), "Status": purchase_status,
            }, {
                "Type": "Sales", "Party": customer_name,
                "Product": sell_product, "Qty MT": sell_qty,
                "Rate/MT": sell_rate, "Subtotal": sell_subtotal,
                "GST": sell_gst, "Total": sell_total,
                "Due Date": str(sales_expected_date), "Status": sales_status,
            }, {
                "Type": "Transport", "Party": transporter_name,
                "Product": "", "Qty MT": "", "Rate/MT": "",
                "Subtotal": "", "GST": "", "Total": transport_amount,
                "Due Date": "", "Status": transport_status,
            }, {
                "Type": "NET PROFIT", "Party": "", "Product": "",
                "Qty MT": "", "Rate/MT": margin_per_mt,
                "Subtotal": "", "GST": f"{margin_pct:.2f}%",
                "Total": net_profit, "Due Date": "", "Status": "",
            }])
            st.download_button(
                label="Download Excel",
                data=df.to_csv(index=False).encode(),
                file_name=f"Payment_Order_{_now_ist_str().replace(' ', '_')}.csv",
                mime="text/csv",
                key="pay_excel_dl",
            )

    with col_btn3:
        if st.button("Send to Accounts Email", key="pay_email", use_container_width=True):
            try:
                from communication_engine import generate_email_template
                email = generate_email_template(
                    "payment_reminder",
                    party_name=supplier_name,
                    amount=_format_inr_display(buy_total),
                    due_date=str(purchase_due_date),
                )
                st.info("Email template generated. Copy and send via your email client:")
                st.code(email.get("body", "Payment order details attached."), language=None)
            except Exception:
                st.info(f"Email template: Payment Order for {supplier_name} — "
                        f"Amount: {_format_inr_display(buy_total)}, "
                        f"Due: {purchase_due_date}, Mode: {payment_mode}")

    with col_btn4:
        if st.button("Send WhatsApp", key="pay_whatsapp", use_container_width=True):
            msg = (f"*Payment Order Summary*\n"
                   f"Supplier: {supplier_name}\n"
                   f"Purchase: {_format_inr_display(buy_total)}\n"
                   f"Customer: {customer_name}\n"
                   f"Sales: {_format_inr_display(sell_total)}\n"
                   f"Transport: {_format_inr_display(transport_amount)}\n"
                   f"Net Profit: {_format_inr_display(net_profit)}\n"
                   f"Mode: {payment_mode}\n"
                   f"Date: {_now_ist_str()}")
            st.info("WhatsApp message ready. Copy and send:")
            st.code(msg, language=None)


def _payment_list_view():
    """Enhanced payment order list with status colors."""
    from database import get_all_payment_orders

    pays = get_all_payment_orders(limit=200)
    if not pays:
        st.info("No payment orders yet.")
        return

    rows = []
    for p in pays:
        profit = p.get("profit_json", {})
        if isinstance(profit, str):
            try:
                profit = json.loads(profit)
            except Exception:
                profit = {}
        rows.append({
            "Pay Number": p.get("pay_number", ""),
            "Supplier": p.get("supplier_name", ""),
            "Customer": p.get("customer_name", ""),
            "Purchase": _format_inr_display(p.get("purchase_payable", 0)),
            "Sales": _format_inr_display(p.get("sales_receivable", 0)),
            "Profit": _format_inr_display(profit.get("net_profit", 0)),
            "Mode": p.get("payment_mode", "NEFT"),
            "Purch Status": p.get("purchase_status", "Pending"),
            "Sales Status": p.get("sales_status", "Pending"),
            "Date": p.get("created_at", ""),
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# PARTY MASTER PAGE
# ═══════════════════════════════════════════════════════════════════════════

def render_party_master():
    """Render the Party Master management page with missing data detection."""
    st.markdown(_HERO_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="doc-hero">'
        '<h2>Party Master</h2>'
        '<p>Manage suppliers, customers &amp; transporters — detect missing fields, find duplicates</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    from party_matching_engine import PartyMatcher

    matcher = PartyMatcher()

    tab_missing, tab_match, tab_dupes, tab_transporters = st.tabs([
        "Missing Data", "Party Lookup", "Duplicate Detection", "Transporters"
    ])

    with tab_missing:
        _party_missing_data(matcher)

    with tab_match:
        _party_lookup(matcher)

    with tab_dupes:
        _party_duplicates(matcher)

    with tab_transporters:
        _transporter_management()


def _completeness_badge(pct: int) -> str:
    """Return colored completeness badge."""
    if pct >= 80:
        color = "#16a34a"  # green
    elif pct >= 50:
        color = "#eab308"  # yellow
    else:
        color = "#dc2626"  # red
    return f"{pct}%"


def _party_missing_data(matcher):
    """Show parties with incomplete master data — suppliers, customers, transporters."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### Suppliers — Missing Data")
        missing_suppliers = matcher.find_missing_master_data("supplier")
        if missing_suppliers:
            rows = []
            for m in missing_suppliers:
                rows.append({
                    "Name": m["name"],
                    "Complete": _completeness_badge(m["completeness_pct"]),
                    "Missing": ", ".join(m["missing_fields"]),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(f"{len(missing_suppliers)} suppliers with incomplete data")
        else:
            st.success("All suppliers have complete master data!")

    with col2:
        st.markdown("#### Customers — Missing Data")
        missing_customers = matcher.find_missing_master_data("customer")
        if missing_customers:
            rows = []
            for m in missing_customers:
                rows.append({
                    "Name": m["name"],
                    "Complete": _completeness_badge(m["completeness_pct"]),
                    "Missing": ", ".join(m["missing_fields"]),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(f"{len(missing_customers)} customers with incomplete data")
        else:
            st.success("All customers have complete master data!")

    with col3:
        st.markdown("#### Transporters — Missing Data")
        missing_transporters = matcher.find_missing_master_data("transporter")
        if missing_transporters:
            rows = []
            for m in missing_transporters:
                rows.append({
                    "Name": m["name"],
                    "Complete": _completeness_badge(m["completeness_pct"]),
                    "Missing": ", ".join(m["missing_fields"]),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(f"{len(missing_transporters)} transporters with incomplete data")
        else:
            st.success("All transporters have complete master data!")


def _party_lookup(matcher):
    """Party lookup by GSTIN or name — supports supplier, customer, transporter."""
    st.markdown("#### Find a Party")

    col1, col2, col3 = st.columns(3)
    with col1:
        party_type = st.selectbox("Party Type", ["supplier", "customer", "transporter"],
                                   key="match_type")
    with col2:
        search_gstin = st.text_input("GSTIN (exact match)", key="match_gstin")
    with col3:
        search_name = st.text_input("Name (exact or fuzzy)", key="match_name")

    if st.button("Search", key="match_search"):
        result = matcher.match_party(
            name=search_name or None,
            gstin=search_gstin or None,
            party_type=party_type,
        )

        if result["match_type"] == "none":
            st.warning("No match found. You may need to create a new record.")
        else:
            match_labels = {
                "gstin": "GSTIN Exact Match",
                "name": "Name Exact Match",
                "fuzzy": "Fuzzy Name Match",
            }
            confidence = result["confidence"]
            if confidence >= 95:
                badge = "🟢"
            elif confidence >= 85:
                badge = "🟡"
            else:
                badge = "🔴"
            st.success(
                f"{badge} **{match_labels.get(result['match_type'], 'Match')}** "
                f"(Confidence: {confidence}%)"
            )
            rec = result["matched_record"]
            if rec:
                st.json({
                    "ID": rec.get("id"),
                    "Name": rec.get("name"),
                    "GSTIN": rec.get("gstin"),
                    "PAN": rec.get("pan", ""),
                    "City": rec.get("city"),
                    "State": rec.get("state"),
                    "Contact": rec.get("contact"),
                })
            if result["missing_fields"]:
                st.warning(f"Missing fields: {', '.join(result['missing_fields'])}")


def _party_duplicates(matcher):
    """Detect potential duplicate parties — suppliers, customers, transporters."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### Supplier Duplicates")
        dupes_s = matcher.suggest_merge_duplicates("supplier")
        if dupes_s:
            for d in dupes_s[:10]:
                st.markdown(
                    f"**{d['record_a']['name']}** vs **{d['record_b']['name']}** "
                    f"— {d['similarity_pct']}% similar"
                    + (" (same GSTIN)" if d["same_gstin"] else "")
                )
        else:
            st.success("No potential duplicates found.")

    with col2:
        st.markdown("#### Customer Duplicates")
        dupes_c = matcher.suggest_merge_duplicates("customer")
        if dupes_c:
            for d in dupes_c[:10]:
                st.markdown(
                    f"**{d['record_a']['name']}** vs **{d['record_b']['name']}** "
                    f"— {d['similarity_pct']}% similar"
                    + (" (same GSTIN)" if d["same_gstin"] else "")
                )
        else:
            st.success("No potential duplicates found.")

    with col3:
        st.markdown("#### Transporter Duplicates")
        dupes_t = matcher.suggest_merge_duplicates("transporter")
        if dupes_t:
            for d in dupes_t[:10]:
                st.markdown(
                    f"**{d['record_a']['name']}** vs **{d['record_b']['name']}** "
                    f"— {d['similarity_pct']}% similar"
                    + (" (same GSTIN)" if d["same_gstin"] else "")
                )
        else:
            st.success("No potential duplicates found.")


def _transporter_management():
    """Add and view transporters."""
    from database import get_all_transporters, insert_transporter

    st.markdown("#### Add New Transporter")
    with st.form("add_transporter_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            t_name = st.text_input("Transporter Name *")
            t_contact = st.text_input("Contact *")
            t_gstin = st.text_input("GSTIN")
        with col2:
            t_city = st.text_input("City *")
            t_state = st.text_input("State")
            t_pan = st.text_input("PAN")
        with col3:
            t_vehicle_types = st.multiselect("Vehicle Types", ["BULK", "DRUM", "CONTAINER"])
            t_rate = st.number_input("Rate per KM (\u20b9)", min_value=0.0, value=0.0, step=0.5)
            t_notes = st.text_input("Notes")

        submitted = st.form_submit_button("Add Transporter", type="primary")
        if submitted:
            if not t_name or not t_contact or not t_city:
                st.error("Name, Contact, and City are required.")
            else:
                insert_transporter({
                    "name": t_name,
                    "contact": t_contact,
                    "gstin": t_gstin,
                    "pan": t_pan,
                    "city": t_city,
                    "state": t_state,
                    "vehicle_types": t_vehicle_types,
                    "rate_per_km": t_rate if t_rate > 0 else None,
                    "notes": t_notes,
                })
                st.success(f"Transporter **{t_name}** added successfully!")
                st.rerun()

    st.divider()
    st.markdown("#### Registered Transporters")
    all_transporters = get_all_transporters(active_only=True)
    if all_transporters:
        rows = []
        for t in all_transporters:
            vt = t.get("vehicle_types", "")
            if isinstance(vt, list):
                vt = ", ".join(vt)
            rows.append({
                "Name": t["name"],
                "City": t.get("city", ""),
                "Contact": t.get("contact", ""),
                "GSTIN": t.get("gstin", ""),
                "Vehicle Types": vt,
                "Rate/KM": t.get("rate_per_km", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No transporters registered yet. Add one above.")
