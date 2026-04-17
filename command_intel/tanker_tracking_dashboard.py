"""
PPS Anantam — Tanker Tracking Dashboard
==========================================
Track bulk tanker/truck positions, ETA, delivery status.
"""
import streamlit as st
import pandas as pd
import datetime


def _get_tankers():
    try:
        from tanker_engine import get_all_tankers
        data = get_all_tankers()
        if data:
            return data
    except Exception:
        pass
    try:
        from tanker_engine import get_mock_tankers
        return get_mock_tankers()
    except Exception:
        return []


def render():
    st.header("🚛 Tanker Tracking")
    st.caption("Real-time tracking of bulk tankers and drum trucks.")

    tankers = _get_tankers()
    if not tankers:
        st.info("No tanker data available.")
        return

    df = pd.DataFrame(tankers)

    # ── KPI Row ──
    loading = len(df[df["status"] == "loading"]) if "status" in df.columns else 0
    transit = len(df[df["status"] == "in_transit"]) if "status" in df.columns else 0
    delivered = len(df[df["status"] == "delivered"]) if "status" in df.columns else 0
    delayed = len(df[df["status"] == "delayed"]) if "status" in df.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Loading", loading)
    k2.metric("In Transit", transit)
    k3.metric("Delivered", delivered)
    k4.metric("Delayed", delayed, delta="⚠️" if delayed > 0 else None)

    st.markdown("---")

    tabs = st.tabs(["🗺️ Live Map", "📋 Tanker List", "➕ Add Dispatch", "📊 Delivery Log"])

    # ── Tab 1: Live Map ──
    with tabs[0]:
        st.subheader("Tanker Positions")
        transit_df = df[df["status"].isin(["in_transit", "delayed", "loading"])] if "status" in df.columns else df

        if "lat" in transit_df.columns and "lng" in transit_df.columns:
            map_df = transit_df[transit_df["lat"].notna() & transit_df["lng"].notna()].copy()
            if not map_df.empty:
                # Color by status
                color_map = {"loading": [59, 130, 246], "in_transit": [16, 185, 129], "delayed": [239, 68, 68]}

                map_df["color_r"] = map_df["status"].map(lambda s: color_map.get(s, [148, 163, 184])[0])
                map_df["color_g"] = map_df["status"].map(lambda s: color_map.get(s, [148, 163, 184])[1])
                map_df["color_b"] = map_df["status"].map(lambda s: color_map.get(s, [148, 163, 184])[2])

                st.map(map_df, latitude="lat", longitude="lng", size=20)

                # Legend
                st.markdown("""
<div style="display:flex;gap:16px;font-size:0.78rem;margin-top:8px;">
<span>🔵 Loading</span> <span>🟢 In Transit</span> <span>🔴 Delayed</span>
</div>""", unsafe_allow_html=True)
            else:
                st.info("No tankers with location data.")
        else:
            st.info("Location data not available.")

    # ── Tab 2: Tanker List ──
    with tabs[1]:
        status_f = st.selectbox("Status", ["All", "loading", "in_transit", "delivered", "delayed"])
        filtered = df if status_f == "All" else df[df["status"] == status_f]

        for _, t in filtered.iterrows():
            status = t.get("status", "")
            color = {"loading": "#3B82F6", "in_transit": "#10B981", "delivered": "#6366F1", "delayed": "#EF4444"}.get(status, "#94A3B8")
            bg = {"loading": "#EFF6FF", "in_transit": "#F0FDF4", "delivered": "#F5F3FF", "delayed": "#FEF2F2"}.get(status, "#F8FAFC")

            eta_str = t.get("eta", "")
            hours_left = ""
            if eta_str and status == "in_transit":
                try:
                    eta_dt = datetime.datetime.strptime(str(eta_str)[:16], "%Y-%m-%d %H:%M")
                    hrs = (eta_dt - datetime.datetime.now()).total_seconds() / 3600
                    hours_left = f" | ETA: {hrs:.1f}hrs" if hrs > 0 else " | OVERDUE"
                except Exception:
                    pass

            st.markdown(f"""
<div style="background:{bg};border-left:4px solid {color};border-radius:8px;padding:12px 16px;margin-bottom:8px;">
<div style="display:flex;justify-content:space-between;align-items:center;">
<div><strong>{t.get('vehicle_no','?')}</strong>
<span style="background:{color};color:#fff;font-size:0.6rem;font-weight:700;padding:2px 8px;border-radius:6px;margin-left:8px;">{status.upper()}</span></div>
<div style="font-size:0.8rem;color:#64748B;">{t.get('source','')} → {t.get('destination','')}{hours_left}</div></div>
<div style="font-size:0.78rem;color:#64748B;margin-top:4px;">
{t.get('customer','')} | {t.get('grade','')} {t.get('qty_mt','')} MT | Driver: {t.get('driver_name','')}</div></div>""", unsafe_allow_html=True)

    # ── Tab 3: Add Dispatch ──
    with tabs[2]:
        st.subheader("New Tanker Dispatch")
        dc1, dc2 = st.columns(2)
        with dc1:
            vehicle = st.text_input("Vehicle No", key="tk_veh", placeholder="GJ05AB1234")
            source = st.text_input("Source", key="tk_src", placeholder="Kandla Terminal")
            destination = st.text_input("Destination", key="tk_dest", placeholder="Ahmedabad")
            try:
                from components.autosuggest import customer_picker
                customer = customer_picker(key="tk_cust", label="Customer")
            except Exception:
                customer = st.text_input("Customer", key="tk_cust")
        with dc2:
            driver = st.text_input("Driver Name", key="tk_drv")
            phone = st.text_input("Driver Phone", key="tk_ph")
            grade = st.selectbox("Grade", ["VG30", "VG10", "VG40", "CRMB-55"], key="tk_gr")
            qty = st.number_input("Qty (MT)", min_value=1, value=20, key="tk_qty")
            distance = st.number_input("Distance (km)", min_value=1, value=500, key="tk_dist")

        if st.button("Dispatch Tanker", type="primary"):
            if vehicle and source and destination:
                try:
                    from tanker_engine import add_tanker
                    add_tanker({
                        "vehicle_no": vehicle, "source": source, "destination": destination,
                        "customer": customer, "driver_name": driver, "driver_phone": phone,
                        "grade": grade, "qty_mt": qty, "distance_km": distance,
                        "status": "in_transit", "departed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    st.success(f"Tanker {vehicle} dispatched! ETA: ~{distance / 40:.0f} hours")
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Enter vehicle, source, and destination.")

    # ── Tab 4: Delivery Log ──
    with tabs[3]:
        st.subheader("Completed Deliveries")
        delivered_df = df[df["status"] == "delivered"] if "status" in df.columns else pd.DataFrame()
        if not delivered_df.empty:
            display_cols = [c for c in ["vehicle_no", "source", "destination", "customer",
                                        "grade", "qty_mt", "departed_at", "delivered_at"]
                          if c in delivered_df.columns]
            st.dataframe(delivered_df[display_cols], use_container_width=True, hide_index=True)

            total_delivered = delivered_df["qty_mt"].sum() if "qty_mt" in delivered_df.columns else 0
            st.metric("Total Delivered", f"{total_delivered:,.0f} MT")
        else:
            st.info("No completed deliveries yet.")
