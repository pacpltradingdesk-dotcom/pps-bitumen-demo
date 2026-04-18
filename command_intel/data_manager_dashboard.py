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
        ic1, ic2 = st.columns([1, 2])
        with ic1:
            data_type = st.selectbox("Data Type", [
                "Contacts (Excel/CSV)",
            ], help="Only Contacts import is implemented. Other types: use the Import Wizard.")
        with ic2:
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
