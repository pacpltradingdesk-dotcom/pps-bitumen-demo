"""
PPS Anantam — Road Budget & Demand Dashboard
===============================================
NHAI project pipeline, state-wise road allocation, bitumen demand correlation.
"""
try:
    from india_localization import format_inr
except ImportError:
    def format_inr(v):
        try:
            return f"{v:,.0f}"
        except Exception:
            return str(v)

import streamlit as st
import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent

ZONE_MAP = {
    "Uttar Pradesh": "North", "Rajasthan": "West", "Madhya Pradesh": "Central",
    "Maharashtra": "West", "Karnataka": "South", "Tamil Nadu": "South",
    "Andhra Pradesh": "South", "Telangana": "South", "Gujarat": "West",
    "Bihar": "East", "West Bengal": "East", "Odisha": "East",
    "Jharkhand": "East", "Chhattisgarh": "Central", "Punjab": "North",
    "Haryana": "North", "Kerala": "South", "Assam": "Northeast",
    "Uttarakhand": "North", "Himachal Pradesh": "North", "Goa": "West",
    "Jammu & Kashmir": "North",
}


def _load_json(filename):
    try:
        fp = ROOT / filename
        if fp.exists():
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def render():
    st.header("🛣️ Road Budget & Demand Analysis")
    st.caption("India road infrastructure budget and state-wise bitumen demand outlook.")

    highway_data = _load_json("tbl_highway_km.json")
    demand_data = _load_json("tbl_demand_proxy.json")

    # ── KPI Row ──
    if highway_data:
        hw_df = pd.DataFrame(highway_data)
        total_km = hw_df["nhai_km_target"].sum() if "nhai_km_target" in hw_df.columns else 0
        completed_km = hw_df["completed_km"].sum() if "completed_km" in hw_df.columns else 0
        total_demand = hw_df["bitumen_demand_mt"].sum() if "bitumen_demand_mt" in hw_df.columns else 0
        avg_completion = hw_df["completion_pct"].mean() if "completion_pct" in hw_df.columns else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total KM Target", f"{total_km:,.0f} km")
        k2.metric("Completed", f"{completed_km:,.0f} km")
        k3.metric("Bitumen Demand", f"{total_demand:,.0f} MT")
        k4.metric("Avg Completion", f"{avg_completion:.1f}%")
    else:
        st.warning("Highway data not loaded. Run data sync or check tbl_highway_km.json.")

    st.markdown("---")

    tabs = st.tabs(["📊 Budget Overview", "🗺️ State-wise", "📈 Demand Correlation", "🏗️ Zone Analysis"])

    # ── Tab 1: Budget Overview ──
    with tabs[0]:
        if highway_data:
            import plotly.express as px

            hw_df = pd.DataFrame(highway_data)
            if "state" in hw_df.columns and "nhai_km_target" in hw_df.columns:
                hw_sorted = hw_df.sort_values("nhai_km_target", ascending=True)
                fig = px.bar(hw_sorted, y="state", x="nhai_km_target",
                             title="NHAI KM Target by State",
                             orientation="h", color="nhai_km_target",
                             color_continuous_scale="YlOrRd")
                fig.update_layout(height=600, yaxis_title="", xaxis_title="KM Target")
                st.plotly_chart(fig, use_container_width=True)

            if "state" in hw_df.columns and "bitumen_demand_mt" in hw_df.columns:
                fig2 = px.bar(hw_df.sort_values("bitumen_demand_mt", ascending=True),
                              y="state", x="bitumen_demand_mt",
                              title="Estimated Bitumen Demand by State (MT)",
                              orientation="h", color="bitumen_demand_mt",
                              color_continuous_scale="Blues")
                fig2.update_layout(height=600, yaxis_title="", xaxis_title="MT")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Highway data not available. Run data sync to populate.")

    # ── Tab 2: State-wise ──
    with tabs[1]:
        st.subheader("State-wise Allocation")
        if highway_data:
            hw_df = pd.DataFrame(highway_data)
            display_cols = [c for c in ["state", "nhai_km_target", "completed_km", "completion_pct",
                                        "bitumen_demand_mt", "bitumen_per_km_mt"] if c in hw_df.columns]
            if display_cols:
                styled_df = hw_df[display_cols].sort_values(display_cols[1], ascending=False) if len(display_cols) > 1 else hw_df[display_cols]
                st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)

            # Completion progress
            if "state" in hw_df.columns and "completion_pct" in hw_df.columns:
                import plotly.express as px
                fig = px.bar(hw_df.sort_values("completion_pct", ascending=True),
                             y="state", x="completion_pct",
                             title="Completion Progress by State (%)",
                             orientation="h", color="completion_pct",
                             color_continuous_scale="RdYlGn", range_x=[0, 100])
                fig.update_layout(height=600, yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Run sync to load state-wise data.")

    # ── Tab 3: Demand Correlation ──
    with tabs[2]:
        st.subheader("Highway KM vs Bitumen Demand Correlation")
        if highway_data:
            import plotly.express as px
            hw_df = pd.DataFrame(highway_data)
            if "nhai_km_target" in hw_df.columns and "bitumen_demand_mt" in hw_df.columns:
                fig = px.scatter(hw_df, x="nhai_km_target", y="bitumen_demand_mt",
                                 text="state", title="Highway KM Target vs Bitumen Demand",
                                 trendline="ols", size="bitumen_demand_mt",
                                 color="bitumen_demand_mt", color_continuous_scale="Viridis")
                fig.update_traces(textposition="top center", textfont_size=9)
                fig.update_layout(height=500, xaxis_title="NHAI KM Target", yaxis_title="Bitumen Demand (MT)")
                st.plotly_chart(fig, use_container_width=True)

                # Correlation coefficient
                corr = hw_df["nhai_km_target"].corr(hw_df["bitumen_demand_mt"])
                st.metric("Correlation Coefficient", f"{corr:.3f}",
                          delta="Strong positive" if corr > 0.7 else "Moderate" if corr > 0.4 else "Weak")

                # Demand factor
                if "bitumen_per_km_mt" in hw_df.columns:
                    avg_factor = hw_df["bitumen_per_km_mt"].mean()
                    st.info(f"Average bitumen consumption: **{avg_factor:.1f} MT per KM** of highway construction.")
        else:
            st.info("Need highway data for correlation analysis.")

        # Seasonal demand
        if demand_data:
            st.markdown("---")
            st.subheader("Seasonal Demand Pattern")
            dm_df = pd.DataFrame(demand_data)
            if "state" in dm_df.columns and "base_demand_mt_month" in dm_df.columns:
                st.dataframe(dm_df[["state", "base_demand_mt_month", "seasonal_factor",
                                    "adjusted_demand_mt", "peak_months", "demand_category"]].sort_values(
                    "adjusted_demand_mt", ascending=False),
                    use_container_width=True, hide_index=True)

    # ── Tab 4: Zone Analysis ──
    with tabs[3]:
        st.subheader("Zone-wise Summary")
        if highway_data:
            import plotly.express as px
            hw_df = pd.DataFrame(highway_data)
            hw_df["zone"] = hw_df["state"].map(ZONE_MAP).fillna("Other")

            zone_summary = hw_df.groupby("zone").agg(
                states=("state", "count"),
                total_km=("nhai_km_target", "sum"),
                completed=("completed_km", "sum"),
                demand_mt=("bitumen_demand_mt", "sum"),
            ).reset_index()
            zone_summary["completion_pct"] = (zone_summary["completed"] / zone_summary["total_km"] * 100).round(1)

            st.dataframe(zone_summary, use_container_width=True, hide_index=True)

            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(zone_summary, values="total_km", names="zone",
                             title="KM Target by Zone", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig = px.pie(zone_summary, values="demand_mt", names="zone",
                             title="Bitumen Demand by Zone", hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Highway data needed for zone analysis.")
