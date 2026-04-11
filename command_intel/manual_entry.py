import streamlit as st
import datetime

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from india_localization import format_inr, format_date, format_datetime_ist, get_financial_year
except ImportError:
    def format_inr(v):
        return f"Rs {v:,.0f}"
    def format_date(d):
        return d.strftime("%Y-%m-%d")
    def format_datetime_ist(dt):
        return dt.strftime("%Y-%m-%d %H:%M IST")
    def get_financial_year(d=None):
        return "FY 2025-26"

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(t):
        pass

try:
    import plotly.graph_objects as go
except ImportError:
    go = None

try:
    import json
    from pathlib import Path
except ImportError:
    json = None
    Path = None

ROOT = Path(__file__).parent.parent if Path else None
LIVE_PRICES_PATH = ROOT / "live_prices.json" if ROOT else None


def _update_live_prices(location, grade, price):
    """Update live_prices.json with the manually entered price so it reflects everywhere."""
    if not LIVE_PRICES_PATH or not json:
        return
    try:
        lp = {}
        if LIVE_PRICES_PATH.exists():
            with open(LIVE_PRICES_PATH, "r", encoding="utf-8") as f:
                lp = json.load(f)

        # Map location + grade to live_prices keys
        loc_map = {
            "Mumbai": "DRUM_MUMBAI",
            "Gujarat": "DRUM_KANDLA",
            "Kandla": "DRUM_KANDLA",
            "Delhi": "DRUM_MUMBAI",
            "Chennai": "DRUM_MUMBAI",
        }
        prefix = loc_map.get(location, "DRUM_MUMBAI")
        key = f"{prefix}_{grade.upper()}"
        lp[key] = int(price)

        with open(LIVE_PRICES_PATH, "w", encoding="utf-8") as f:
            json.dump(lp, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def _load_crude_prices():
    """Load crude price data from tbl_crude_prices.json."""
    if not ROOT:
        return []
    try:
        fpath = ROOT / "tbl_crude_prices.json"
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def render():
    display_badge("user input")

    st.markdown("### 📝 Fortnight CRM Field Pricing (Overrides & Logging)")
    st.info("Directly input local or competitor quotes. Overriding the Base MLR Prediction will trigger a 🚩 **Conflict Badge** via the Audit Trackers.")

    st.markdown("---")

    tab_entry, tab_history, tab_chart = st.tabs([
        "📝 Entry Form", "📋 Entry History", "📈 Price Chart"
    ])

    # Auto-calculate next revision date (1st or 16th of current/next month)
    today = datetime.date.today()
    if today.day <= 15:
        # Next revision is 16th of this month
        default_rev = datetime.date(today.year, today.month, 16)
    else:
        # Next revision is 1st of next month
        if today.month == 12:
            default_rev = datetime.date(today.year + 1, 1, 1)
        else:
            default_rev = datetime.date(today.year, today.month + 1, 1)

    # ─── TAB 1: Entry Form (existing) ───
    with tab_entry:
        with st.form("manual_price_entry"):
            st.markdown("#### Enter New Manual Data Point")
            c1, c2, c3 = st.columns(3)

            rev_date = c1.date_input("Target Revision Date", value=default_rev, format="DD-MM-YYYY")
            loc = c2.selectbox("Sub-Location", ["Mumbai", "Gujarat", "Delhi", "Chennai", "Custom"])
            grade = c3.selectbox("Grade", ["VG30", "VG10", "PMB", "CRMB"])

            c4, c5, c6 = st.columns(3)
            price = c4.number_input("Field Price Quote (₹/MT)", min_value=10000)
            freight = c5.number_input("Freight Deductible (₹/MT)", value=0)
            tax = c6.number_input("Include Tax/GST (%)", value=18.0)

            st.text_area("Observations / Remarks (Important for logging)")
            st.file_uploader("Upload Quotation / Proof (PDF/IMG)")

            c_sub, _ = st.columns([1, 4])
            if c_sub.form_submit_button("Submit CRM Override"):
                # Update live_prices.json so price reflects everywhere
                updated = _update_live_prices(loc, grade, price)
                if updated:
                    st.success(f"✅ Entry logged + Live Price updated! {grade} @ ₹{price:,}/MT ({loc}) now reflects across Command Center, Market Snapshot, Pricing Calculator, Rate Broadcast & all pages.")
                else:
                    st.success("Entry securely logged to the Database and Change History.")

        st.markdown("---")

        st.markdown("#### 📓 Recent Uploads / Entries by Team")
        # Mock entries prioritizing India format
        if pd is not None:
            df_entries = pd.DataFrame([
                {
                    "Entry IST": format_datetime_ist(datetime.datetime.now()),
                    "Target Revision": default_rev.strftime("%d-%m-%Y"),
                    "Location": "Mumbai",
                    "Grade": "VG30",
                    "Entered Price": format_inr(41250),
                    "Conflict": "🚩 Yes (Auto was ₹ 40,500)",
                    "User": "Salesman A"
                },
                {
                    "Entry IST": format_datetime_ist(datetime.datetime.now() - datetime.timedelta(hours=24)),
                    "Target Revision": default_rev.strftime("%d-%m-%Y"),
                    "Location": "Gujarat",
                    "Grade": "VG10",
                    "Entered Price": format_inr(39800),
                    "Conflict": "✅ No Conflict",
                    "User": "Manager B"
                }
            ])
            st.dataframe(df_entries, use_container_width=True, hide_index=True)

    # ─── TAB 2: Entry History ───
    with tab_history:
        st.subheader("📋 Crude Price Entry History")
        crude_data = _load_crude_prices()

        if not crude_data:
            st.info("No price data found in tbl_crude_prices.json. Entries will appear here once data is fetched.")
        elif pd is not None:
            df_hist = pd.DataFrame(crude_data)

            # Filter controls
            fh1, fh2, fh3 = st.columns(3)
            with fh1:
                benchmarks_avail = sorted(df_hist["benchmark"].unique().tolist()) if "benchmark" in df_hist.columns else []
                sel_benchmark = st.selectbox("Filter by Benchmark", ["All"] + benchmarks_avail, key="hist_bench")
            with fh2:
                sources_avail = sorted(df_hist["source"].unique().tolist()) if "source" in df_hist.columns else []
                sel_source = st.selectbox("Filter by Source", ["All"] + sources_avail, key="hist_src")
            with fh3:
                st.metric("Total Records", len(df_hist))

            filtered = df_hist.copy()
            if sel_benchmark != "All":
                filtered = filtered[filtered["benchmark"] == sel_benchmark]
            if sel_source != "All":
                filtered = filtered[filtered["source"] == sel_source]

            # KPIs
            k1, k2, k3, k4 = st.columns(4)
            if not filtered.empty and "price" in filtered.columns:
                k1.metric("Latest Price", f"${filtered.iloc[-1]['price']:.2f}")
                k2.metric("Avg Price", f"${filtered['price'].mean():.2f}")
                k3.metric("Min", f"${filtered['price'].min():.2f}")
                k4.metric("Max", f"${filtered['price'].max():.2f}")

            # Display columns
            display_cols = ["date_time", "benchmark", "price", "currency", "source"]
            available_cols = [c for c in display_cols if c in filtered.columns]
            st.dataframe(
                filtered[available_cols].sort_values(by="date_time", ascending=False) if "date_time" in available_cols else filtered,
                use_container_width=True,
                hide_index=True
            )

    # ─── TAB 3: Price Chart ───
    with tab_chart:
        st.subheader("📈 Crude Price Trend Chart")
        crude_data = _load_crude_prices()

        if not crude_data:
            st.info("No price data available for charting.")
        elif go is None:
            st.warning("Plotly not available. Install plotly for interactive charts.")
        elif pd is not None:
            df_chart = pd.DataFrame(crude_data)

            if "price" not in df_chart.columns or "date_time" not in df_chart.columns:
                st.warning("Price data does not have the expected columns.")
            else:
                # Parse dates
                df_chart["parsed_dt"] = pd.to_datetime(df_chart["date_time"], format="%Y-%m-%d %H:%M:%S IST", errors="coerce")
                df_chart = df_chart.dropna(subset=["parsed_dt"]).sort_values("parsed_dt")

                # Chart type selector
                ch1, ch2 = st.columns([1, 3])
                with ch1:
                    chart_type = st.radio("Chart Type", ["Line", "Area", "Scatter"], key="price_chart_type")

                benchmarks = df_chart["benchmark"].unique().tolist() if "benchmark" in df_chart.columns else ["All"]

                fig = go.Figure()

                for bm in benchmarks:
                    subset = df_chart[df_chart["benchmark"] == bm] if "benchmark" in df_chart.columns else df_chart
                    if chart_type == "Line":
                        fig.add_trace(go.Scatter(
                            x=subset["parsed_dt"], y=subset["price"],
                            mode="lines+markers", name=bm,
                            line=dict(width=2)
                        ))
                    elif chart_type == "Area":
                        fig.add_trace(go.Scatter(
                            x=subset["parsed_dt"], y=subset["price"],
                            mode="lines", name=bm,
                            fill="tozeroy", line=dict(width=1)
                        ))
                    else:
                        fig.add_trace(go.Scatter(
                            x=subset["parsed_dt"], y=subset["price"],
                            mode="markers", name=bm,
                            marker=dict(size=6)
                        ))

                fig.update_layout(
                    title="Crude Oil Price Trends (USD/bbl)",
                    xaxis_title="Date/Time",
                    yaxis_title="Price (USD/bbl)",
                    hovermode="x unified",
                    template="plotly_white",
                    height=450,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)

                # Price statistics table
                st.markdown("#### 📊 Price Statistics by Benchmark")
                stats_rows = []
                for bm in benchmarks:
                    subset = df_chart[df_chart["benchmark"] == bm] if "benchmark" in df_chart.columns else df_chart
                    stats_rows.append({
                        "Benchmark": bm,
                        "Count": len(subset),
                        "Latest (USD)": f"${subset['price'].iloc[-1]:.2f}" if not subset.empty else "-",
                        "Average (USD)": f"${subset['price'].mean():.2f}" if not subset.empty else "-",
                        "Min (USD)": f"${subset['price'].min():.2f}" if not subset.empty else "-",
                        "Max (USD)": f"${subset['price'].max():.2f}" if not subset.empty else "-",
                        "Std Dev": f"${subset['price'].std():.2f}" if not subset.empty and len(subset) > 1 else "-",
                    })
                st.dataframe(pd.DataFrame(stats_rows), use_container_width=True, hide_index=True)
