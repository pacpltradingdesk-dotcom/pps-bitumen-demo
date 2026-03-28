"""
PPS Anantam — NHAI Tender Feed Dashboard
===========================================
Track live NHAI/MoRTH road project tenders for bitumen demand estimation.
"""
import streamlit as st
import pandas as pd
import datetime


def _get_tenders():
    try:
        from tender_engine import get_tenders
        data = get_tenders()
        if data:
            return data
    except Exception:
        pass
    try:
        from tender_engine import get_mock_tenders
        return get_mock_tenders()
    except Exception:
        return []


def render():
    st.header("🏗️ NHAI Tender Feed")
    st.caption("Track road project tenders and estimate bitumen demand opportunities.")

    tenders = _get_tenders()
    if not tenders:
        st.info("No tender data available.")
        return

    df = pd.DataFrame(tenders)
    for col in ["road_length_km", "estimated_bitumen_mt", "value_cr"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ── KPI Row ──
    open_tenders = len(df[df["status"] == "open"]) if "status" in df.columns else 0
    total_km = df["road_length_km"].sum()
    total_bitumen = df["estimated_bitumen_mt"].sum()
    total_value = df["value_cr"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Open Tenders", open_tenders)
    k2.metric("Total Road KM", f"{total_km:,.0f}")
    k3.metric("Est. Bitumen (MT)", f"{total_bitumen:,.0f}")
    k4.metric("Project Value", f"₹{total_value:,.0f} Cr")

    st.markdown("---")

    tabs = st.tabs(["📋 Live Tenders", "🗺️ State Map", "📊 Demand Estimate", "➕ Add Tender"])

    # ── Tab 1: Live Tenders ──
    with tabs[0]:
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            status_f = st.selectbox("Status", ["All", "open", "closed"])
        with fc2:
            states = sorted(df["state"].unique().tolist()) if "state" in df.columns else []
            state_f = st.selectbox("State", ["All"] + states)
        with fc3:
            auth_f = st.selectbox("Authority", ["All"] + sorted(df["authority"].unique().tolist()) if "authority" in df.columns else ["All"])

        filtered = df.copy()
        if status_f != "All":
            filtered = filtered[filtered["status"] == status_f]
        if state_f != "All":
            filtered = filtered[filtered["state"] == state_f]
        if auth_f != "All":
            filtered = filtered[filtered["authority"] == auth_f]

        display_cols = [c for c in ["tender_id", "title", "authority", "state", "road_length_km",
                                    "estimated_bitumen_mt", "value_cr", "deadline", "status"]
                       if c in filtered.columns]
        st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True, height=450)
        st.caption(f"Showing {len(filtered)} of {len(df)} tenders")

    # ── Tab 2: State Map ──
    with tabs[1]:
        st.subheader("State-wise Tender Distribution")
        if "state" in df.columns:
            import plotly.express as px

            state_summary = df[df["status"] == "open"].groupby("state").agg(
                tenders=("state", "count"),
                total_km=("road_length_km", "sum"),
                bitumen_mt=("estimated_bitumen_mt", "sum"),
                value_cr=("value_cr", "sum"),
            ).reset_index().sort_values("bitumen_mt", ascending=True)

            fig = px.bar(state_summary, y="state", x="bitumen_mt",
                         title="Estimated Bitumen Demand by State (Open Tenders)",
                         orientation="h", color="bitumen_mt", color_continuous_scale="YlOrRd",
                         text="bitumen_mt")
            fig.update_traces(texttemplate="%{text:,.0f} MT", textposition="outside")
            fig.update_layout(height=500, yaxis_title="", xaxis_title="Estimated Bitumen (MT)")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(state_summary, use_container_width=True, hide_index=True)

    # ── Tab 3: Demand Estimate ──
    with tabs[2]:
        st.subheader("Bitumen Demand Estimation")
        st.info("**Formula:** Road Length (km) × 45 MT/km = Estimated Bitumen Demand")

        if "road_length_km" in df.columns:
            import plotly.express as px

            open_df = df[df["status"] == "open"] if "status" in df.columns else df

            fig = px.scatter(open_df, x="road_length_km", y="estimated_bitumen_mt",
                            size="value_cr", color="state", hover_name="title",
                            title="Road Length vs Bitumen Demand (Bubble = Project Value)",
                            labels={"road_length_km": "Road Length (km)", "estimated_bitumen_mt": "Bitumen (MT)"})
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

            # Top opportunities
            st.markdown("**Top 10 Bitumen Opportunities**")
            top = open_df.nlargest(10, "estimated_bitumen_mt")[["title", "state", "road_length_km",
                                                                "estimated_bitumen_mt", "value_cr", "deadline"]]
            st.dataframe(top, use_container_width=True, hide_index=True)

    # ── Tab 4: Add Tender ──
    with tabs[3]:
        st.subheader("Add New Tender")
        ac1, ac2 = st.columns(2)
        with ac1:
            title = st.text_input("Tender Title", key="td_title")
            state = st.text_input("State", key="td_state")
            authority = st.selectbox("Authority", ["NHAI", "MoRTH", "State PWD", "NHIDCL"], key="td_auth")
        with ac2:
            length = st.number_input("Road Length (km)", min_value=0, value=50, key="td_km")
            value = st.number_input("Project Value (₹ Cr)", min_value=0.0, value=100.0, step=10.0, key="td_val")
            deadline = st.date_input("Deadline", key="td_dead")

        if st.button("Add Tender", type="primary"):
            if title and state:
                try:
                    from tender_engine import add_tender
                    add_tender({
                        "title": title, "state": state, "authority": authority,
                        "road_length_km": length, "value_cr": value,
                        "deadline": deadline.strftime("%Y-%m-%d"),
                    })
                    st.success(f"Tender added! Est. bitumen: {length * 45:,.0f} MT")
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Enter title and state.")
