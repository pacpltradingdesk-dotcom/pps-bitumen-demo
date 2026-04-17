"""
PPS Anantam — E-Way Bill Dashboard
=====================================
Generate, track, and manage e-way bills for bitumen shipments.
"""
import streamlit as st
import pandas as pd
import datetime


def _get_bills():
    try:
        from eway_bill_engine import get_all_bills, expire_bills
        expire_bills()
        bills = get_all_bills()
        if bills:
            return bills
    except Exception:
        pass
    try:
        from eway_bill_engine import get_mock_bills
        return get_mock_bills()
    except Exception:
        return []


def render():
    st.header("📄 E-Way Bill Management")
    st.caption("Generate, track, and manage e-way bills for bitumen shipments. HSN: 27132000")

    bills = _get_bills()
    df = pd.DataFrame(bills) if bills else pd.DataFrame()

    # ── KPI Row ──
    active = len(df[df["status"] == "active"]) if "status" in df.columns else 0
    expired = len(df[df["status"] == "expired"]) if "status" in df.columns else 0
    total_value = df["value"].sum() if "value" in df.columns else 0

    # Check expiring soon (within 24 hours)
    expiring_soon = 0
    if "valid_until" in df.columns and "status" in df.columns:
        now = datetime.datetime.now()
        for _, row in df[df["status"] == "active"].iterrows():
            try:
                vu = datetime.datetime.strptime(str(row["valid_until"])[:16], "%Y-%m-%d %H:%M")
                if vu - now < datetime.timedelta(hours=24):
                    expiring_soon += 1
            except Exception:
                pass

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Active Bills", active)
    k2.metric("Expiring (<24hr)", expiring_soon, delta="⚠️" if expiring_soon > 0 else None)
    k3.metric("Expired", expired)
    k4.metric("Total Value", f"₹{total_value / 100000:,.1f}L")

    st.markdown("---")

    tabs = st.tabs(["📋 All Bills", "➕ Generate New", "⚠️ Expiring Soon", "📊 Analytics"])

    # ── Tab 1: All Bills ──
    with tabs[0]:
        if not df.empty:
            status_filter = st.selectbox("Status", ["All", "active", "expired"])
            filtered = df if status_filter == "All" else df[df["status"] == status_filter]

            display_cols = [c for c in ["bill_no", "from_city", "to_city", "vehicle_no", "value",
                                        "distance_km", "valid_from", "valid_until", "status"]
                          if c in filtered.columns]
            st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True, height=450)
        else:
            st.info("No e-way bills found.")

    # ── Tab 2: Generate New ──
    with tabs[1]:
        st.subheader("Generate E-Way Bill")

        try:
            from components.autosuggest import city_picker as _city_picker
            _have_city_picker = True
        except Exception:
            _have_city_picker = False

        gc1, gc2 = st.columns(2)
        with gc1:
            if _have_city_picker:
                from_city = _city_picker(key="ew_from", default="Vadodara", label="From City")
                to_city = _city_picker(key="ew_to", label="To City")
            else:
                from_city = st.text_input("From City", value="Vadodara", key="ew_from")
                to_city = st.text_input("To City", key="ew_to", placeholder="Destination city")
            vehicle = st.text_input("Vehicle No", key="ew_veh", placeholder="GJ05AB1234")
        with gc2:
            to_gstin = st.text_input("Buyer GSTIN", key="ew_gstin", placeholder="27XXXXX...")
            value = st.number_input("Invoice Value (₹)", min_value=0, value=500000, step=50000, key="ew_val")
            distance = st.number_input("Distance (km)", min_value=1, value=500, step=50, key="ew_dist")

        if st.button("Generate E-Way Bill", type="primary"):
            if to_city and vehicle:
                try:
                    from eway_bill_engine import create_eway_bill
                    result = create_eway_bill({
                        "from_city": from_city, "to_city": to_city, "vehicle_no": vehicle,
                        "to_gstin": to_gstin, "value": value, "distance_km": distance,
                    })
                    st.success(f"E-Way Bill generated: **{result['bill_no']}** | Valid until: {result['valid_until']}")
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Enter destination city and vehicle number.")

        st.markdown("---")
        st.caption("**Rules:** HSN 27132000 | Validity: 1 day per 200km | From GSTIN: 24AAHCV1611L2ZD (PPS)")

    # ── Tab 3: Expiring Soon ──
    with tabs[2]:
        st.subheader("Bills Expiring Within 24 Hours")
        if not df.empty and "valid_until" in df.columns:
            now = datetime.datetime.now()
            expiring = []
            for _, row in df[df["status"] == "active"].iterrows():
                try:
                    vu = datetime.datetime.strptime(str(row["valid_until"])[:16], "%Y-%m-%d %H:%M")
                    hours_left = (vu - now).total_seconds() / 3600
                    if hours_left < 24 and hours_left > 0:
                        r = row.to_dict()
                        r["hours_left"] = round(hours_left, 1)
                        expiring.append(r)
                except Exception:
                    pass

            if expiring:
                for bill in sorted(expiring, key=lambda x: x["hours_left"]):
                    hrs = bill["hours_left"]
                    color = "#DC2626" if hrs < 6 else "#D97706" if hrs < 12 else "#2563EB"
                    st.markdown(f"""
<div style="background:#fff;border-left:4px solid {color};border-radius:8px;padding:12px 16px;margin-bottom:8px;border:1px solid #E2E8F0;">
<div style="display:flex;justify-content:space-between;align-items:center;">
<div><strong>{bill.get('bill_no','?')}</strong> | {bill.get('from_city','')} → {bill.get('to_city','')}</div>
<div><span style="color:{color};font-weight:700;">{hrs:.1f} hrs left</span> | {bill.get('vehicle_no','')}</div>
</div></div>""", unsafe_allow_html=True)
            else:
                st.success("No bills expiring in the next 24 hours.")
        else:
            st.info("No active bills to check.")

    # ── Tab 4: Analytics ──
    with tabs[3]:
        if not df.empty:
            import plotly.express as px

            c1, c2 = st.columns(2)
            with c1:
                if "status" in df.columns:
                    status_counts = df["status"].value_counts().reset_index()
                    status_counts.columns = ["Status", "Count"]
                    fig = px.pie(status_counts, values="Count", names="Status", title="Bills by Status",
                                 color_discrete_map={"active": "#10B981", "expired": "#EF4444"}, hole=0.4)
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

            with c2:
                if "to_city" in df.columns:
                    city_counts = df["to_city"].value_counts().head(10).reset_index()
                    city_counts.columns = ["City", "Bills"]
                    fig = px.bar(city_counts, x="City", y="Bills", title="Top Destination Cities",
                                 color="Bills", color_continuous_scale="Blues")
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for analytics.")
