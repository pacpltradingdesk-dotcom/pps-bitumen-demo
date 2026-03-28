"""
PPS Anantam — Credit Limit & Aging Dashboard
===============================================
Customer credit tracking, aging buckets, overdue alerts, payment history.
"""
import streamlit as st
import pandas as pd


def _get_credit_data():
    """Get credit data from engine or mock."""
    try:
        from credit_engine import get_all_credits
        data = get_all_credits()
        if data:
            return data
    except Exception:
        pass
    try:
        from credit_engine import get_mock_credits
        return get_mock_credits()
    except Exception:
        return []


def render():
    st.header("💳 Credit Limit & Aging")
    st.caption("Customer credit tracking, aging buckets, and overdue alerts.")

    credits = _get_credit_data()
    if not credits:
        st.info("No credit data available. Add customer credit limits to get started.")
        return

    df = pd.DataFrame(credits)
    for col in ["credit_limit", "outstanding", "days_outstanding", "last_payment_amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ── KPI Row ──
    total_outstanding = df["outstanding"].sum()
    overdue_60 = df[df["days_outstanding"] > 60]["outstanding"].sum() if "days_outstanding" in df.columns else 0
    at_risk = len(df[df["outstanding"] > df["credit_limit"] * 0.8]) if "credit_limit" in df.columns else 0
    avg_days = df["days_outstanding"].mean() if "days_outstanding" in df.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Outstanding", f"₹{total_outstanding / 100000:,.1f}L")
    k2.metric("Overdue (60+ days)", f"₹{overdue_60 / 100000:,.1f}L")
    k3.metric("At Risk (>80% limit)", at_risk)
    k4.metric("Avg Days Outstanding", f"{avg_days:.0f}")

    st.markdown("---")

    tabs = st.tabs(["📋 Credit Table", "📊 Aging Buckets", "⚠️ Overdue Alerts", "➕ Manage"])

    # ── Tab 1: Credit Table ──
    with tabs[0]:
        st.subheader("Customer Credit Summary")

        # Add utilization column
        if "credit_limit" in df.columns and "outstanding" in df.columns:
            df["utilization_pct"] = (df["outstanding"] / df["credit_limit"].replace(0, 1) * 100).round(1)
            df["available"] = (df["credit_limit"] - df["outstanding"]).clip(lower=0)

        # Risk filter
        risk_filter = st.selectbox("Risk Level", ["All", "critical", "high", "medium", "low"])
        filtered = df if risk_filter == "All" else df[df["risk_level"] == risk_filter]

        display_cols = [c for c in ["customer_name", "credit_limit", "outstanding", "available",
                                    "utilization_pct", "days_outstanding", "risk_level",
                                    "last_payment_date", "last_payment_amount"]
                       if c in filtered.columns]
        st.dataframe(filtered[display_cols].sort_values("outstanding", ascending=False),
                     use_container_width=True, hide_index=True, height=450)

    # ── Tab 2: Aging Buckets ──
    with tabs[1]:
        st.subheader("Aging Bucket Analysis")

        try:
            from credit_engine import get_aging_summary
            aging = get_aging_summary()
        except Exception:
            # Calculate from dataframe
            aging = {"counts": {}, "amounts": {}}
            for label, lo, hi in [("0-30", 0, 30), ("31-60", 31, 60), ("61-90", 61, 90), ("90+", 91, 9999)]:
                mask = (df["days_outstanding"] >= lo) & (df["days_outstanding"] <= hi)
                aging["counts"][label] = int(mask.sum())
                aging["amounts"][label] = float(df.loc[mask, "outstanding"].sum())

        import plotly.graph_objects as go

        buckets = list(aging["counts"].keys())
        counts = list(aging["counts"].values())
        amounts = [a / 100000 for a in aging["amounts"].values()]
        colors = ["#10B981", "#F59E0B", "#F97316", "#EF4444"]

        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Bar(x=buckets, y=counts, marker_color=colors, text=counts, textposition="auto"))
            fig.update_layout(title="Customers by Aging Bucket", height=350, yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = go.Figure(go.Bar(x=buckets, y=amounts, marker_color=colors,
                                   text=[f"₹{a:.1f}L" for a in amounts], textposition="auto"))
            fig.update_layout(title="Outstanding by Aging Bucket (₹ Lakhs)", height=350, yaxis_title="₹ Lakhs")
            st.plotly_chart(fig, use_container_width=True)

        # Pie chart
        import plotly.express as px
        pie_df = pd.DataFrame({"Bucket": buckets, "Amount": list(aging["amounts"].values())})
        fig = px.pie(pie_df, values="Amount", names="Bucket", title="Outstanding Distribution",
                     color_discrete_sequence=colors, hole=0.4)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 3: Overdue Alerts ──
    with tabs[2]:
        st.subheader("Overdue Alerts")

        overdue = df[df["days_outstanding"] > 60].sort_values("days_outstanding", ascending=False) if "days_outstanding" in df.columns else pd.DataFrame()

        if len(overdue) > 0:
            for _, row in overdue.iterrows():
                days = row.get("days_outstanding", 0)
                amt = row.get("outstanding", 0)
                cust = row.get("customer_name", "?")
                risk = row.get("risk_level", "high")

                if days > 90:
                    color, bg, badge = "#DC2626", "#FEF2F2", "CRITICAL"
                elif days > 60:
                    color, bg, badge = "#D97706", "#FFFBEB", "HIGH"
                else:
                    color, bg, badge = "#2563EB", "#EFF6FF", "MEDIUM"

                st.markdown(f"""
<div style="background:{bg};border-left:4px solid {color};border-radius:8px;padding:14px 18px;margin-bottom:8px;">
<div style="display:flex;justify-content:space-between;align-items:center;">
<div><strong>{cust}</strong>
<span style="background:{color};color:#fff;font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:6px;margin-left:8px;">{badge}</span></div>
<div style="text-align:right;">
<strong style="color:{color};">₹{amt:,.0f}</strong>
<div style="font-size:0.72rem;color:#64748B;">{days} days overdue</div></div></div></div>""", unsafe_allow_html=True)

            st.caption(f"{len(overdue)} customers overdue (60+ days) | Total: ₹{overdue['outstanding'].sum():,.0f}")
        else:
            st.success("No overdue accounts! All customers within credit terms.")

    # ── Tab 4: Manage ──
    with tabs[3]:
        st.subheader("Set Credit Limit")

        mc1, mc2 = st.columns(2)
        with mc1:
            cust_name = st.text_input("Customer Name", key="cl_cust")
        with mc2:
            limit = st.number_input("Credit Limit (₹)", min_value=0, value=500000, step=50000, key="cl_limit")

        if st.button("Set Credit Limit", type="primary"):
            if cust_name:
                try:
                    from credit_engine import set_credit_limit
                    set_credit_limit(cust_name, limit)
                    st.success(f"Credit limit set: {cust_name} → ₹{limit:,.0f}")
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Enter customer name.")

        st.markdown("---")
        st.subheader("Record Payment")
        pc1, pc2 = st.columns(2)
        with pc1:
            pay_cust = st.text_input("Customer", key="cl_pay_cust")
        with pc2:
            pay_amt = st.number_input("Payment Amount (₹)", min_value=0, value=100000, step=10000, key="cl_pay_amt")

        if st.button("Record Payment", type="primary", key="cl_pay_btn"):
            if pay_cust:
                try:
                    from credit_engine import record_payment
                    record_payment(pay_cust, pay_amt)
                    st.success(f"Payment recorded: {pay_cust} → ₹{pay_amt:,.0f}")
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Enter customer name.")
