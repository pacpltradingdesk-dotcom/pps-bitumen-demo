"""
PPS Anantam — Profitability Analytics Dashboard
==================================================
Deal P&L, customer ranking, route profitability, monthly trends.
"""
import streamlit as st
import pandas as pd
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _get_deals():
    """Get all deals from database."""
    try:
        from database import _get_conn
        conn = _get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM deals ORDER BY created_at DESC LIMIT 500
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []


def _get_mock_deals():
    """Generate sample deal data for demo."""
    import random
    cities = ["Ahmedabad", "Mumbai", "Pune", "Delhi", "Chennai", "Bangalore", "Lucknow", "Jaipur",
              "Bhopal", "Hyderabad", "Kolkata", "Nashik", "Surat", "Vadodara", "Indore"]
    customers = ["Ashoka Buildcon", "L&T Roads", "NCC Ltd", "Dilip Buildcon", "Gayatri Projects",
                 "PNC Infratech", "Sadbhav Engineering", "IRB Infra", "KNR Constructions", "HG Infra",
                 "GR Infraprojects", "J Kumar Infra", "Oriental Structural", "Montecarlo Ltd", "BL Kashyap"]
    sources = ["IOCL Kandla", "HPCL Mumbai", "BPCL Vizag", "Import Mundra", "Import Kandla",
               "MRPL Mangalore", "Decanter Ahmedabad", "Decanter Pune"]
    grades = ["VG30", "VG10", "VG40", "CRMB-55"]

    deals = []
    for i in range(100):
        base = random.randint(33000, 38000)
        landed = base + random.randint(1000, 4000)
        selling = landed + random.randint(400, 2000)
        qty = random.choice([20, 25, 30, 40, 50, 60, 80, 100])
        margin = selling - landed
        dt = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 365))

        deals.append({
            "id": i + 1,
            "customer": random.choice(customers),
            "city": random.choice(cities),
            "grade": random.choice(grades),
            "source": random.choice(sources),
            "qty_mt": qty,
            "base_price": base,
            "landed_cost": landed,
            "selling_price": selling,
            "margin_per_mt": margin,
            "total_revenue": selling * qty,
            "total_cost": landed * qty,
            "total_margin": margin * qty,
            "status": random.choice(["Closed", "Closed", "Closed", "Dispatched", "Negotiation"]),
            "created_at": dt.strftime("%Y-%m-%d"),
            "month": dt.strftime("%Y-%m"),
        })
    return deals


def render():
    st.header("💰 Profitability Analytics")
    st.caption("Deal P&L, customer ranking, route profitability, and monthly trends.")

    deals = _get_deals()
    if not deals:
        deals = _get_mock_deals()
        st.info("Showing demo data. Real data will appear as deals are recorded.")

    df = pd.DataFrame(deals)

    # Ensure numeric columns
    for col in ["qty_mt", "landed_cost", "selling_price", "margin_per_mt", "total_revenue", "total_cost", "total_margin"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ── KPI Row ──
    total_revenue = df["total_revenue"].sum() if "total_revenue" in df.columns else 0
    total_margin = df["total_margin"].sum() if "total_margin" in df.columns else 0
    avg_margin = df["margin_per_mt"].mean() if "margin_per_mt" in df.columns else 0
    total_qty = df["qty_mt"].sum() if "qty_mt" in df.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", f"₹{total_revenue / 100000:,.1f}L")
    k2.metric("Total Margin", f"₹{total_margin / 100000:,.1f}L")
    k3.metric("Avg Margin/MT", f"₹{avg_margin:,.0f}")
    k4.metric("Total Qty", f"{total_qty:,.0f} MT")

    st.markdown("---")

    tabs = st.tabs(["📊 Deal P&L", "👥 Customer Ranking", "🗺️ Route Profitability", "📈 Monthly Trends"])

    # ── Tab 1: Deal P&L ──
    with tabs[0]:
        st.subheader("Deal-wise Profit & Loss")

        # Filter
        fc1, fc2 = st.columns(2)
        with fc1:
            status_filter = st.selectbox("Status", ["All"] + sorted(df["status"].unique().tolist()) if "status" in df.columns else ["All"])
        with fc2:
            grade_filter = st.selectbox("Grade", ["All"] + sorted(df["grade"].unique().tolist()) if "grade" in df.columns else ["All"])

        filtered = df.copy()
        if status_filter != "All":
            filtered = filtered[filtered["status"] == status_filter]
        if grade_filter != "All":
            filtered = filtered[filtered["grade"] == grade_filter]

        display_cols = [c for c in ["customer", "city", "grade", "source", "qty_mt", "landed_cost",
                                    "selling_price", "margin_per_mt", "total_margin", "status", "created_at"]
                       if c in filtered.columns]
        st.dataframe(filtered[display_cols].sort_values("total_margin", ascending=False) if "total_margin" in filtered.columns else filtered[display_cols],
                     use_container_width=True, hide_index=True, height=450)

        st.caption(f"Showing {len(filtered)} deals | Total margin: ₹{filtered['total_margin'].sum():,.0f}")

    # ── Tab 2: Customer Ranking ──
    with tabs[1]:
        st.subheader("Top Customers by Profitability")

        if "customer" in df.columns and "total_margin" in df.columns:
            cust_summary = df.groupby("customer").agg(
                deals=("customer", "count"),
                total_qty=("qty_mt", "sum"),
                total_revenue=("total_revenue", "sum"),
                total_margin=("total_margin", "sum"),
                avg_margin_mt=("margin_per_mt", "mean"),
            ).reset_index().sort_values("total_margin", ascending=False)

            import plotly.express as px

            fig = px.bar(cust_summary.head(15), x="customer", y="total_margin",
                         title="Top 15 Customers by Total Margin",
                         color="total_margin", color_continuous_scale="Greens",
                         text="total_margin")
            fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            fig.update_layout(height=450, xaxis_title="", yaxis_title="Total Margin (₹)",
                             xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(cust_summary, use_container_width=True, hide_index=True)

    # ── Tab 3: Route Profitability ──
    with tabs[2]:
        st.subheader("Source → City Route Profitability")

        if "source" in df.columns and "city" in df.columns:
            route_summary = df.groupby(["source", "city"]).agg(
                deals=("source", "count"),
                avg_margin=("margin_per_mt", "mean"),
                total_margin=("total_margin", "sum"),
                total_qty=("qty_mt", "sum"),
            ).reset_index().sort_values("total_margin", ascending=False)

            import plotly.express as px

            # Heatmap
            pivot = df.pivot_table(values="margin_per_mt", index="source", columns="city",
                                   aggfunc="mean").fillna(0)
            import plotly.graph_objects as go
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale="RdYlGn",
                text=[[f"₹{v:,.0f}" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                hovertemplate="Source: %{y}<br>City: %{x}<br>Margin: %{text}<extra></extra>",
            ))
            fig.update_layout(title="Avg Margin/MT by Route (Source → City)",
                             height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Top routes table
            st.markdown("**Top 20 Most Profitable Routes**")
            st.dataframe(route_summary.head(20), use_container_width=True, hide_index=True)

    # ── Tab 4: Monthly Trends ──
    with tabs[3]:
        st.subheader("Monthly Revenue & Margin Trends")

        if "month" in df.columns:
            monthly = df.groupby("month").agg(
                deals=("month", "count"),
                revenue=("total_revenue", "sum"),
                cost=("total_cost", "sum"),
                margin=("total_margin", "sum"),
                qty=("qty_mt", "sum"),
                avg_margin_mt=("margin_per_mt", "mean"),
            ).reset_index().sort_values("month")

            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly["month"], y=monthly["revenue"],
                                 name="Revenue", marker_color="#6366F1", opacity=0.7))
            fig.add_trace(go.Bar(x=monthly["month"], y=monthly["cost"],
                                 name="Cost", marker_color="#94A3B8", opacity=0.7))
            fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["margin"],
                                     name="Margin", line=dict(color="#10B981", width=3),
                                     mode="lines+markers"))
            fig.update_layout(title="Monthly Revenue vs Cost vs Margin",
                             height=450, barmode="group",
                             yaxis_title="Amount (₹)", xaxis_title="Month")
            st.plotly_chart(fig, use_container_width=True)

            # Avg margin per MT trend
            import plotly.express as px
            fig2 = px.line(monthly, x="month", y="avg_margin_mt",
                          title="Average Margin per MT — Monthly Trend",
                          markers=True, line_shape="spline")
            fig2.update_traces(line_color="#8B5CF6", line_width=3)
            fig2.update_layout(height=350, yaxis_title="₹/MT")
            st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(monthly, use_container_width=True, hide_index=True)
