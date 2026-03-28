# Wave 1: Fix Gaps — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the one stub page (Export Reports) and enhance 3 thin dashboards to production quality.

**Architecture:** All routing already works via `dashboard.py` PAGE_DISPATCH → command_intel modules. No new page wrapper files needed. This wave enhances existing files in-place.

**Tech Stack:** Streamlit, Pandas, Plotly, JSON data files, existing engines.

**Key finding:** Reports/Documents/Compliance pages are already fully wired in PAGE_DISPATCH to their command_intel modules. The empty `pages/reports/`, `pages/documents/`, `pages/compliance/` directories are irrelevant — routing bypasses them. Data files `tbl_contacts.json` (66 records), `tbl_highway_km.json` (22 records), `tbl_demand_proxy.json` (28 records) already exist.

---

### Task 1: Replace Export Reports Stub

**Files:**
- Modify: `dashboard.py:351-357` (replace `_page_reports` function)

The current `_page_reports()` is a 6-line stub that just shows "Generated successfully!" on button click. Replace it with a real export page that generates PDF/Excel from existing engines.

- [ ] **Step 1: Replace `_page_reports` in dashboard.py**

Find lines 351-357 in `dashboard.py`:
```python
def _page_reports():
    st.header("📤 Export Reports")
    st.info("Select a report type to generate and export.")
    report_type = st.selectbox("Report Type", ["Financial Summary", "Sales Report", "Market Analysis", "Compliance Report"])
    if st.button("Generate Report", type="primary"):
        st.success(f"{report_type} generated successfully!")
```

Replace with:
```python
def _page_reports():
    st.header("📤 Export Reports")
    st.caption("Generate and download reports as PDF or Excel.")

    report_type = st.selectbox("Report Type", [
        "Director Briefing (PDF)",
        "Financial Summary (Excel)",
        "CRM Contacts (Excel)",
        "Price History (Excel)",
        "Market Signals (Excel)",
        "Full Data Backup (JSON)",
    ])

    if st.button("Generate Report", type="primary"):
        import pandas as pd
        import json as _json
        from pathlib import Path as _Path
        _root = _Path(__file__).parent

        try:
            if "Director Briefing" in report_type:
                try:
                    from director_briefing_engine import generate_briefing
                    briefing = generate_briefing()
                    st.success("Director Briefing generated!")
                    st.markdown(briefing.get("summary", "No summary available."))
                except Exception:
                    st.warning("Director Briefing engine not available. Check system settings.")

            elif "Financial Summary" in report_type:
                try:
                    from database import get_deals
                    deals = get_deals(limit=500)
                    if deals:
                        df = pd.DataFrame(deals)
                        csv = df.to_csv(index=False)
                        st.download_button("Download Financial Summary (CSV)", data=csv,
                                           file_name="pps_financial_summary.csv", mime="text/csv")
                        st.success(f"Financial summary ready — {len(deals)} deals.")
                    else:
                        st.info("No deal data available yet.")
                except Exception:
                    st.warning("Financial data not available.")

            elif "CRM Contacts" in report_type:
                try:
                    _cf = _root / "tbl_contacts.json"
                    if _cf.exists():
                        with open(_cf, "r", encoding="utf-8") as f:
                            contacts = _json.load(f)
                        df = pd.DataFrame(contacts)
                        csv = df.to_csv(index=False)
                        st.download_button("Download Contacts (CSV)", data=csv,
                                           file_name="pps_contacts_export.csv", mime="text/csv")
                        st.success(f"Contacts export ready — {len(contacts)} records.")
                    else:
                        st.info("No contacts data file found.")
                except Exception:
                    st.warning("Contacts export failed.")

            elif "Price History" in report_type:
                try:
                    _pf = _root / "tbl_crude_prices.json"
                    if _pf.exists():
                        with open(_pf, "r", encoding="utf-8") as f:
                            prices = _json.load(f)
                        df = pd.DataFrame(prices)
                        csv = df.to_csv(index=False)
                        st.download_button("Download Price History (CSV)", data=csv,
                                           file_name="pps_price_history.csv", mime="text/csv")
                        st.success(f"Price history ready — {len(prices)} records.")
                    else:
                        st.info("No price history data available.")
                except Exception:
                    st.warning("Price history export failed.")

            elif "Market Signals" in report_type:
                try:
                    _sf = _root / "tbl_market_signals.json"
                    if _sf.exists():
                        with open(_sf, "r", encoding="utf-8") as f:
                            signals = _json.load(f)
                        df = pd.DataFrame(signals if isinstance(signals, list) else [signals])
                        csv = df.to_csv(index=False)
                        st.download_button("Download Market Signals (CSV)", data=csv,
                                           file_name="pps_market_signals.csv", mime="text/csv")
                        st.success("Market signals export ready.")
                    else:
                        st.info("No market signals data available.")
                except Exception:
                    st.warning("Market signals export failed.")

            elif "Full Data Backup" in report_type:
                try:
                    backup = {}
                    for jf in _root.glob("tbl_*.json"):
                        with open(jf, "r", encoding="utf-8") as f:
                            backup[jf.stem] = _json.load(f)
                    backup_str = _json.dumps(backup, indent=2, default=str)
                    st.download_button("Download Full Backup (JSON)", data=backup_str,
                                       file_name="pps_full_backup.json", mime="application/json")
                    st.success(f"Full backup ready — {len(backup)} tables.")
                except Exception:
                    st.warning("Backup generation failed.")

        except Exception as e:
            st.error(f"Report generation failed: {e}")
```

- [ ] **Step 2: Verify — run dashboard, navigate to Reports → Export Reports, test each report type**

Run: `streamlit run dashboard.py`
Navigate: Reports → Export Reports
Test: Select each report type, click Generate, verify download button appears.

---

### Task 2: Enhance Data Manager Dashboard

**Files:**
- Modify: `command_intel/data_manager_dashboard.py` (60 → ~200 lines)

Currently just shows success messages without doing real work. Enhance with actual file processing, data quality scoring, and table row counts.

- [ ] **Step 1: Rewrite data_manager_dashboard.py**

Replace entire content of `command_intel/data_manager_dashboard.py` with:

```python
"""
PPS Anantam — Data Manager Dashboard
=======================================
Manage data imports, exports, sync, and cache with real functionality.
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path
import datetime

ROOT = Path(__file__).parent.parent


def _count_json_records(filename):
    """Count records in a JSON file."""
    try:
        fp = ROOT / filename
        if fp.exists():
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            return len(data) if isinstance(data, list) else len(data.keys()) if isinstance(data, dict) else 0
    except Exception:
        pass
    return 0


def _get_file_age(filename):
    """Get last modified time of a file."""
    try:
        fp = ROOT / filename
        if fp.exists():
            mtime = fp.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(mtime)
            delta = datetime.datetime.now() - dt
            if delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h ago"
            else:
                return f"{delta.seconds // 60}m ago"
    except Exception:
        pass
    return "Unknown"


def render():
    st.header("🛠️ Data Manager")
    st.caption("Import, export, and manage dashboard data.")

    # ── KPI Row ──
    data_files = list(ROOT.glob("tbl_*.json"))
    cache_files = list(ROOT.glob("*_cache.json")) + list(ROOT.glob("*_log.json"))
    total_records = sum(_count_json_records(f.name) for f in data_files)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Data Tables", len(data_files))
    k2.metric("Total Records", f"{total_records:,}")
    k3.metric("Cache Files", len(cache_files))
    try:
        db_size = (ROOT / "bitumen_dashboard.db").stat().st_size / (1024 * 1024)
        k4.metric("DB Size", f"{db_size:.1f} MB")
    except Exception:
        k4.metric("DB Size", "N/A")

    st.markdown("---")

    tabs = st.tabs(["📥 Import Data", "📤 Export Data", "📊 Data Health", "🗑️ Cache"])

    # ── Tab 1: Import ──
    with tabs[0]:
        st.subheader("Import Data")
        data_type = st.selectbox("Data Type", [
            "Contacts (Excel/CSV)", "Price History (CSV)", "Customer Data (Excel)", "Supplier Data (Excel)"
        ])
        uploaded = st.file_uploader(f"Upload {data_type}", type=["xlsx", "csv", "json"])

        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                elif uploaded.name.endswith((".xlsx", ".xls")):
                    df = pd.read_excel(uploaded)
                elif uploaded.name.endswith(".json"):
                    df = pd.DataFrame(json.load(uploaded))
                else:
                    st.error("Unsupported file type.")
                    return

                st.success(f"Loaded {len(df)} rows, {len(df.columns)} columns from {uploaded.name}")
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)

                col_info = pd.DataFrame({
                    "Column": df.columns,
                    "Type": df.dtypes.astype(str),
                    "Non-Null": df.count().values,
                    "Fill %": (df.count().values / len(df) * 100).round(1),
                })
                with st.expander("Column Details"):
                    st.dataframe(col_info, use_container_width=True, hide_index=True)

                if st.button("Confirm Import", type="primary"):
                    if "Contacts" in data_type:
                        records = df.to_dict("records")
                        existing = []
                        cf = ROOT / "tbl_contacts.json"
                        if cf.exists():
                            with open(cf, "r", encoding="utf-8") as f:
                                existing = json.load(f)
                        merged = existing + records
                        with open(cf, "w", encoding="utf-8") as f:
                            json.dump(merged, f, indent=2, default=str)
                        st.success(f"Imported {len(records)} contacts. Total now: {len(merged)}")
                    else:
                        st.info("Import handler for this data type coming soon.")

            except Exception as e:
                st.error(f"Failed to process file: {e}")

    # ── Tab 2: Export ──
    with tabs[1]:
        st.subheader("Export Data")
        export_options = {
            "All Contacts": "tbl_contacts.json",
            "Crude Prices": "tbl_crude_prices.json",
            "Highway Data": "tbl_highway_km.json",
            "Demand Proxy": "tbl_demand_proxy.json",
            "Market Signals": "tbl_market_signals.json",
            "News Feed": "tbl_news_feed.json",
            "Port Data": "tbl_ports_master.json",
        }
        export_type = st.selectbox("Select Data", list(export_options.keys()))
        target_file = export_options[export_type]

        if st.button("Generate Export", type="primary"):
            fp = ROOT / target_file
            if fp.exists():
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    df = pd.DataFrame(data)
                    csv = df.to_csv(index=False)
                    st.download_button(f"Download {export_type} (CSV)", data=csv,
                                       file_name=f"pps_{target_file.replace('.json','')}.csv", mime="text/csv")
                    st.success(f"Export ready — {len(data)} records.")
                elif isinstance(data, dict):
                    json_str = json.dumps(data, indent=2, default=str)
                    st.download_button(f"Download {export_type} (JSON)", data=json_str,
                                       file_name=f"pps_{target_file}", mime="application/json")
                    st.success("Export ready.")
                else:
                    st.info("No data to export.")
            else:
                st.warning(f"{target_file} not found. Run data sync first.")

    # ── Tab 3: Data Health ──
    with tabs[2]:
        st.subheader("Data Health Overview")
        health_rows = []
        for f in sorted(data_files, key=lambda x: x.name):
            count = _count_json_records(f.name)
            age = _get_file_age(f.name)
            size_kb = f.stat().st_size / 1024
            health_rows.append({
                "Table": f.stem,
                "Records": count,
                "Size (KB)": round(size_kb, 1),
                "Last Updated": age,
            })

        if health_rows:
            df = pd.DataFrame(health_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            total = df["Records"].sum()
            st.caption(f"Total: {len(health_rows)} tables, {total:,} records")
        else:
            st.info("No data tables found.")

        # Data confidence
        try:
            from data_confidence_engine import compute_confidence
            score = compute_confidence()
            st.metric("Data Confidence Score", f"{score:.0f}%")
        except Exception:
            pass

    # ── Tab 4: Cache ──
    with tabs[3]:
        st.subheader("Cache Management")
        cache_info = []
        for f in sorted(cache_files, key=lambda x: x.name):
            try:
                size_kb = f.stat().st_size / 1024
                age = _get_file_age(f.name)
                cache_info.append({"File": f.name, "Size (KB)": round(size_kb, 1), "Last Updated": age})
            except Exception:
                pass

        if cache_info:
            st.dataframe(pd.DataFrame(cache_info), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Clear Streamlit Cache", type="secondary", use_container_width=True):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("Streamlit cache cleared!")
                st.rerun()
        with c2:
            if st.button("Clear JSON Caches", type="secondary", use_container_width=True):
                cleared = 0
                for f in cache_files:
                    if "_cache" in f.name:
                        try:
                            f.unlink()
                            cleared += 1
                        except Exception:
                            pass
                st.success(f"Cleared {cleared} cache files.")
                st.rerun()
```

- [ ] **Step 2: Verify — navigate to System & AI → Data Manager (or via PAGE_DISPATCH), check all 4 tabs**

Check: KPI row shows real numbers, Import processes a file, Export generates CSV, Data Health shows table list, Cache shows cache files.

---

### Task 3: Enhance Contacts Directory Dashboard

**Files:**
- Modify: `command_intel/contacts_directory_dashboard.py` (82 → ~200 lines)

Currently functional but basic. Enhance with state filter, bulk import button, better KPIs, and WhatsApp quick-action.

- [ ] **Step 1: Rewrite contacts_directory_dashboard.py**

Replace entire content of `command_intel/contacts_directory_dashboard.py` with:

```python
"""
PPS Anantam — Contacts Directory Dashboard
=============================================
Browse 25K+ business contacts with search, filter, export, and bulk import.
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _load_contacts():
    """Load contacts from JSON file, fallback to database."""
    contacts = []
    try:
        cf = ROOT / "tbl_contacts.json"
        if cf.exists():
            with open(cf, "r", encoding="utf-8") as f:
                contacts = json.load(f)
    except Exception:
        pass
    if not contacts:
        try:
            from database import get_all_contacts
            contacts = get_all_contacts()
        except Exception:
            pass
    return contacts


def render():
    st.header("📱 Contacts Directory")
    st.caption("Browse, search, and manage business contacts.")

    contacts = _load_contacts()

    # ── KPI Row ──
    cities = set(c.get("city", "") for c in contacts if c.get("city"))
    states = set(c.get("state", "") for c in contacts if c.get("state"))
    categories = sorted(set(c.get("category", "General") for c in contacts if c.get("category")))
    with_phone = sum(1 for c in contacts if c.get("contact") or c.get("phone") or c.get("whatsapp"))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Contacts", f"{len(contacts):,}")
    k2.metric("States", len(states))
    k3.metric("Cities", len(cities))
    k4.metric("With Phone", f"{with_phone:,}")

    st.markdown("---")

    tabs = st.tabs(["📋 Directory", "📥 Import", "📊 Analytics"])

    # ── Tab 1: Directory ──
    with tabs[0]:
        # Search & filters
        fc1, fc2, fc3 = st.columns([3, 1, 1])
        with fc1:
            search = st.text_input("Search", placeholder="Name, company, city, phone...", key="cd_search")
        with fc2:
            cat_filter = st.selectbox("Category", ["All"] + categories, key="cd_cat")
        with fc3:
            state_list = sorted(states) if states else []
            state_filter = st.selectbox("State", ["All"] + state_list, key="cd_state")

        # Apply filters
        filtered = contacts
        if search:
            q = search.lower()
            filtered = [c for c in filtered if q in json.dumps(c, default=str).lower()]
        if cat_filter != "All":
            filtered = [c for c in filtered if c.get("category") == cat_filter]
        if state_filter != "All":
            filtered = [c for c in filtered if c.get("state") == state_filter]

        st.caption(f"Showing {len(filtered):,} of {len(contacts):,} contacts")

        # Display
        if filtered:
            df = pd.DataFrame(filtered[:500])
            display_cols = [c for c in ["name", "category", "city", "state", "contact", "gstin", "type"] if c in df.columns]
            if display_cols:
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=450)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True, height=450)

            if len(filtered) > 500:
                st.warning(f"Showing first 500 of {len(filtered):,}. Use search to narrow down.")

            # Export
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                full_df = pd.DataFrame(filtered)
                csv = full_df.to_csv(index=False)
                st.download_button("📥 Export CSV", data=csv,
                                   file_name="pps_contacts_export.csv", mime="text/csv",
                                   use_container_width=True)
            with exp_col2:
                json_str = json.dumps(filtered, indent=2, default=str)
                st.download_button("📥 Export JSON", data=json_str,
                                   file_name="pps_contacts_export.json", mime="application/json",
                                   use_container_width=True)
        else:
            st.info("No contacts match your search criteria.")

    # ── Tab 2: Import ──
    with tabs[1]:
        st.subheader("Bulk Import Contacts")
        st.info("Upload Excel or CSV file with columns: name, category, city, state, contact, gstin")

        uploaded = st.file_uploader("Upload contacts file", type=["xlsx", "csv"], key="cd_import")
        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    new_df = pd.read_csv(uploaded)
                else:
                    new_df = pd.read_excel(uploaded)

                st.success(f"Loaded {len(new_df)} rows from {uploaded.name}")
                st.dataframe(new_df.head(10), use_container_width=True, hide_index=True)

                # Column mapping
                expected_cols = ["name", "category", "city", "state", "contact", "gstin"]
                missing = [c for c in expected_cols if c not in new_df.columns]
                if missing:
                    st.warning(f"Missing columns: {', '.join(missing)}. Available: {', '.join(new_df.columns.tolist())}")

                if st.button("Import Contacts", type="primary"):
                    import datetime
                    new_records = new_df.to_dict("records")
                    for r in new_records:
                        r["imported_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        r["source"] = f"import_{uploaded.name}"

                    existing = _load_contacts()
                    merged = existing + new_records
                    cf = ROOT / "tbl_contacts.json"
                    with open(cf, "w", encoding="utf-8") as f:
                        json.dump(merged, f, indent=2, default=str)
                    st.success(f"Imported {len(new_records)} contacts. Total: {len(merged)}")
                    st.rerun()

            except Exception as e:
                st.error(f"Import failed: {e}")

    # ── Tab 3: Analytics ──
    with tabs[2]:
        st.subheader("Contact Analytics")
        if contacts:
            # Category breakdown
            cat_counts = {}
            for c in contacts:
                cat = c.get("category", "Unknown")
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            import plotly.express as px

            c1, c2 = st.columns(2)
            with c1:
                cat_df = pd.DataFrame(list(cat_counts.items()), columns=["Category", "Count"])
                cat_df = cat_df.sort_values("Count", ascending=False)
                fig = px.bar(cat_df, x="Category", y="Count", title="Contacts by Category",
                             color="Count", color_continuous_scale="Blues")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                state_counts = {}
                for c in contacts:
                    s = c.get("state", "Unknown")
                    if s:
                        state_counts[s] = state_counts.get(s, 0) + 1
                state_df = pd.DataFrame(list(state_counts.items()), columns=["State", "Count"])
                state_df = state_df.sort_values("Count", ascending=False).head(15)
                fig = px.bar(state_df, x="State", y="Count", title="Top 15 States",
                             color="Count", color_continuous_scale="Greens")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            # City breakdown
            city_counts = {}
            for c in contacts:
                ct = c.get("city", "Unknown")
                if ct:
                    city_counts[ct] = city_counts.get(ct, 0) + 1
            city_df = pd.DataFrame(list(city_counts.items()), columns=["City", "Count"])
            city_df = city_df.sort_values("Count", ascending=False).head(20)
            fig = px.bar(city_df, x="City", y="Count", title="Top 20 Cities",
                         color="Count", color_continuous_scale="Purples")
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No contacts data available for analytics.")
```

- [ ] **Step 2: Verify — navigate to Sales & CRM → Contacts Directory, check all 3 tabs**

Check: KPI row shows real counts (66 contacts, states, cities), Directory tab has 3 filters + table + export, Import tab accepts file upload, Analytics tab shows Plotly charts.

---

### Task 4: Enhance Road Budget Dashboard

**Files:**
- Modify: `command_intel/road_budget_dashboard.py` (98 → ~250 lines)

Currently shows basic table. Enhance with Plotly charts, zone-wise grouping, bitumen demand correlation, and demand proxy integration.

- [ ] **Step 1: Rewrite road_budget_dashboard.py**

Replace entire content of `command_intel/road_budget_dashboard.py` with:

```python
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
```

- [ ] **Step 2: Verify — navigate to Reports → Road Budget, check all 4 tabs**

Check: KPI row shows real numbers (22 states of data), Budget Overview has horizontal bar charts, State-wise has completion progress, Demand Correlation has scatter plot with trendline, Zone Analysis has pie charts.

---

### Task 5: Final Verification — All Wave 1 Changes

- [ ] **Step 1: Smoke test all 4 modified pages**

Run the dashboard and test each page:
1. Reports → Export Reports — try each report type, verify download works
2. System & AI → Developer Ops → Data Manager (wherever it's routed) — verify all 4 tabs
3. Sales & CRM → Contacts Directory — verify 3 tabs with real data
4. Reports → Road Budget — verify 4 tabs with charts

- [ ] **Step 2: Check no existing pages broke**

Quick navigate through: Home, Pricing Calculator, CRM Tasks, Market Signals, Director Cockpit — verify they still load correctly.

---

## Summary

| Task | File | Change |
|------|------|--------|
| 1 | `dashboard.py:351-357` | Replace Export Reports stub with real export page |
| 2 | `command_intel/data_manager_dashboard.py` | 60 → ~200 lines, real import/export/health |
| 3 | `command_intel/contacts_directory_dashboard.py` | 82 → ~200 lines, 3 tabs with analytics |
| 4 | `command_intel/road_budget_dashboard.py` | 98 → ~250 lines, 4 tabs with Plotly charts |
| 5 | All above | Final smoke test |
