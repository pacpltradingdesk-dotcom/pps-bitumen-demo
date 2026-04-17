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
"""PPS Anantam — SOS Special Pricing Dashboard"""
import streamlit as st
import json
import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    go = None
    px = None

ROOT = Path(__file__).parent.parent


def _load_sos_data():
    """Load SOS opportunities from JSON."""
    try:
        sos_path = ROOT / "sos_opportunities.json"
        if sos_path.exists():
            with open(sos_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_sos_data(data):
    """Save SOS data to JSON."""
    try:
        sos_path = ROOT / "sos_opportunities.json"
        with open(sos_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass


def _auto_expire_entries(sos_data):
    """Auto-expire SOS entries older than 24 hours."""
    now = datetime.datetime.now()
    modified = False
    for entry in sos_data:
        if entry.get("status", "").lower() != "active":
            continue
        valid_until = entry.get("valid_until", "") or entry.get("created_at", "")
        if not valid_until:
            continue
        try:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
                try:
                    expiry_dt = datetime.datetime.strptime(valid_until, fmt)
                    break
                except ValueError:
                    continue
            else:
                continue
            if expiry_dt < now:
                entry["status"] = "Expired"
                modified = True
        except Exception:
            continue
    return sos_data, modified


def _get_urgency(entry):
    """Calculate urgency level based on time remaining."""
    valid_until = entry.get("valid_until", "")
    if not valid_until:
        return "Unknown", "⚪"
    now = datetime.datetime.now()
    try:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                expiry_dt = datetime.datetime.strptime(valid_until, fmt)
                break
            except ValueError:
                continue
        else:
            return "Unknown", "⚪"
        remaining = (expiry_dt - now).total_seconds()
        if remaining <= 0:
            return "EXPIRED", "🔴"
        elif remaining <= 3600:
            return "CRITICAL (<1hr)", "🔴"
        elif remaining <= 14400:
            return "HIGH (<4hr)", "🟠"
        elif remaining <= 43200:
            return "MEDIUM (<12hr)", "🟡"
        else:
            return "LOW (>12hr)", "🟢"
    except Exception:
        return "Unknown", "⚪"


def render():
    st.header("🚨 SOS Special Pricing")
    st.caption("Emergency pricing overrides for urgent orders.")

    sos_data = _load_sos_data()

    # Auto-expire old entries
    sos_data, was_modified = _auto_expire_entries(sos_data)
    if was_modified:
        _save_sos_data(sos_data)

    # KPI row
    active_count = sum(1 for s in sos_data if s.get("status", "").lower() == "active")
    expired_count = sum(1 for s in sos_data if s.get("status", "").lower() == "expired")
    total_count = len(sos_data)
    total_savings = sum(s.get("saving", 0) for s in sos_data if s.get("saving"))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🟢 Active SOS", active_count)
    m2.metric("🔴 Expired", expired_count)
    m3.metric("📊 Total Entries", total_count)
    m4.metric("💰 Total Savings", f"{format_inr(total_savings)}/MT")

    st.markdown("---")

    tabs = st.tabs(["🚨 Active SOS", "➕ New SOS Entry", "📋 History", "📊 Analytics"])

    # ─── TAB 1: Active SOS with urgency indicators ───
    with tabs[0]:
        active = [s for s in sos_data if s.get("status", "").lower() == "active"]
        if active:
            for entry in active:
                urgency_text, urgency_icon = _get_urgency(entry)
                with st.container():
                    ec1, ec2, ec3, ec4 = st.columns([2, 2, 1, 1])
                    with ec1:
                        st.markdown(f"**{entry.get('customer', entry.get('location', 'N/A'))}**")
                        st.caption(f"📍 {entry.get('location', entry.get('city', '-'))} | Grade: {entry.get('product', entry.get('grade', '-'))}")
                    with ec2:
                        old_p = entry.get("old_price", entry.get("price", 0))
                        new_p = entry.get("new_price", old_p)
                        saving = entry.get("saving", 0)
                        st.markdown(f"{format_inr(old_p)} → **{format_inr(new_p)}** (Save {format_inr(saving)}/MT)")
                        st.caption(f"Qty: {entry.get('quantity', '-')} MT | Reason: {entry.get('reason', '-')}")
                    with ec3:
                        if urgency_text.startswith("CRITICAL") or urgency_text == "EXPIRED":
                            st.error(f"{urgency_icon} {urgency_text}")
                        elif urgency_text.startswith("HIGH"):
                            st.warning(f"{urgency_icon} {urgency_text}")
                        else:
                            st.info(f"{urgency_icon} {urgency_text}")
                    with ec4:
                        st.caption(f"Valid: {entry.get('valid_until', '-')}")
                        st.caption(f"ID: {entry.get('id', '-')[:8]}")
                    st.markdown("---")
            if pd is not None:
                with st.expander("View as Table"):
                    st.dataframe(pd.DataFrame(active), use_container_width=True, hide_index=True)
        else:
            st.info("No active SOS pricing. Use 'New SOS Entry' to create one.")

    # ─── TAB 2: New SOS Entry ───
    with tabs[1]:
        with st.form("sos_form"):
            c1, c2 = st.columns(2)
            try:
                from components.autosuggest import customer_picker, city_picker
                _have_auto = True
            except Exception:
                _have_auto = False
            with c1:
                if _have_auto:
                    customer = customer_picker(key="sos_cust", label="Customer Name")
                    city = city_picker(key="sos_city", label="City")
                else:
                    customer = st.text_input("Customer Name")
                    city = st.text_input("City")
                grade = st.selectbox("Grade", ["VG30", "VG10"])
            with c2:
                qty = st.number_input("Quantity (MT)", min_value=1, value=50)
                price = st.number_input("Special Price (₹/MT)", min_value=10000, value=40000)
                reason = st.text_input("Reason", placeholder="Urgent order, competition match...")
            if st.form_submit_button("Create SOS Entry", type="primary"):
                new_entry = {
                    "customer": customer, "city": city, "grade": grade,
                    "quantity": qty, "price": price, "reason": reason,
                    "status": "active",
                    "created_at": str(datetime.datetime.now()),
                    "valid_until": str(datetime.datetime.now() + datetime.timedelta(hours=24)),
                    "location": city,
                    "product": grade,
                    "old_price": price + 1000,
                    "new_price": price,
                    "saving": 1000,
                    "id": str(__import__("uuid").uuid4())[:8]
                }
                sos_data.append(new_entry)
                _save_sos_data(sos_data)
                st.success("SOS entry created! Valid for 24 hours.")
                st.rerun()

    # ─── TAB 3: History ───
    with tabs[2]:
        if sos_data and pd is not None:
            df_all = pd.DataFrame(sos_data)
            # Status filter
            status_filter = st.selectbox("Filter by Status", ["All", "Active", "Expired"], key="sos_hist_status")
            if status_filter != "All":
                df_all = df_all[df_all["status"].str.lower() == status_filter.lower()]
            st.dataframe(df_all, use_container_width=True, hide_index=True)
        elif not sos_data:
            st.caption("No SOS history yet.")
        else:
            st.warning("pandas not available for table display.")

    # ─── TAB 4: Analytics ───
    with tabs[3]:
        st.subheader("📊 SOS Analytics")

        if not sos_data:
            st.info("No SOS data for analytics.")
        elif pd is None:
            st.warning("pandas not available for analytics.")
        else:
            df_analytics = pd.DataFrame(sos_data)

            # SOS count by location/city
            st.markdown("#### SOS Count by Location")
            location_col = "location" if "location" in df_analytics.columns else "city"
            if location_col in df_analytics.columns:
                loc_counts = df_analytics[location_col].value_counts().reset_index()
                loc_counts.columns = ["Location", "Count"]

                lc1, lc2 = st.columns([2, 1])
                with lc1:
                    if go is not None:
                        fig_loc = go.Figure(go.Bar(
                            x=loc_counts["Location"], y=loc_counts["Count"],
                            marker_color="#1e3a5f",
                            text=loc_counts["Count"], textposition="auto"
                        ))
                        fig_loc.update_layout(
                            title="SOS Entries by Location",
                            xaxis_title="Location", yaxis_title="Count",
                            template="plotly_white", height=350
                        )
                        st.plotly_chart(fig_loc, use_container_width=True)
                    else:
                        st.dataframe(loc_counts, use_container_width=True, hide_index=True)
                with lc2:
                    st.dataframe(loc_counts, use_container_width=True, hide_index=True)

            # SOS by product/grade
            st.markdown("#### SOS Count by Product")
            product_col = "product" if "product" in df_analytics.columns else "grade"
            if product_col in df_analytics.columns:
                prod_counts = df_analytics[product_col].value_counts().reset_index()
                prod_counts.columns = ["Product", "Count"]
                pc1, pc2 = st.columns(2)
                with pc1:
                    if go is not None:
                        fig_prod = go.Figure(go.Pie(
                            labels=prod_counts["Product"], values=prod_counts["Count"],
                            hole=0.4, marker_colors=["#1e3a5f", "#e8dcc8", "#3b82f6", "#f59e0b"]
                        ))
                        fig_prod.update_layout(title="Product Distribution", height=300)
                        st.plotly_chart(fig_prod, use_container_width=True)
                    else:
                        st.dataframe(prod_counts, use_container_width=True, hide_index=True)
                with pc2:
                    st.dataframe(prod_counts, use_container_width=True, hide_index=True)

            # Status breakdown
            st.markdown("#### Status Breakdown")
            if "status" in df_analytics.columns:
                status_counts = df_analytics["status"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                for _, row in status_counts.iterrows():
                    status_label = row["Status"]
                    count_val = row["Count"]
                    if str(status_label).lower() == "active":
                        st.success(f"🟢 {status_label}: {count_val}")
                    elif str(status_label).lower() == "expired":
                        st.error(f"🔴 {status_label}: {count_val}")
                    else:
                        st.info(f"⚪ {status_label}: {count_val}")

            # Target customers summary
            st.markdown("#### 👥 Target Customers Summary")
            customers_all = []
            for entry in sos_data:
                for tc in entry.get("target_customers", []):
                    customers_all.append({
                        "SOS ID": entry.get("id", "-"),
                        "Customer": tc.get("name", "-"),
                        "Contact": tc.get("contact", "-"),
                        "Last Price": f"{format_inr(tc.get('last_price', 0))}",
                        "Priority": tc.get("priority", "-"),
                    })
            if customers_all:
                st.dataframe(pd.DataFrame(customers_all), use_container_width=True, hide_index=True)
            else:
                st.caption("No target customer data available.")
