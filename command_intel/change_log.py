import streamlit as st
import datetime, json, sys, os
from pathlib import Path
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    import plotly.graph_objects as go
except ImportError:
    go = None
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(t): pass

ROOT = Path(__file__).parent.parent


def _load_real_change_log():
    """Load real change log from api_manager. Returns a display-ready DataFrame."""
    try:
        from api_manager import get_change_log
        records = get_change_log(n=500)
    except Exception:
        records = []

    if not records:
        return pd.DataFrame(columns=["Date-Time (IST)", "Field Changed", "Old Value", "New Value", "Location", "Reason", "Changed By", "Impacted Areas"])

    rows = []
    for r in records:
        trigger = r.get("trigger", "Auto")
        changed_by = f"🤖 {r.get('user_id', 'System')}" if trigger == "Auto" else r.get("user_id", "Manual")
        rows.append({
            "Date-Time (IST)": r.get("datetime_ist", ""),
            "Field Changed": r.get("what_changed", ""),
            "Old Value": r.get("old_value", ""),
            "New Value": r.get("new_value", ""),
            "Location": r.get("component", ""),
            "Reason": r.get("reason", ""),
            "Changed By": changed_by,
            "Impacted Areas": r.get("affected_tab", r.get("affected_api", "")),
        })
    return pd.DataFrame(rows)

def _load_json_log(filename):
    """Load a JSON log file from project root."""
    try:
        fpath = ROOT / filename
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return []

def render():
    display_badge("notifications")
    st.markdown("### 🔔 System Activity & Change Log")
    st.info("Live feed from `api_manager.py` change log. Every modification (Auto or Manual) is stamped here in IST.")

    st.markdown("---")

    df = _load_real_change_log()
    api_log = _load_json_log("api_change_log.json")
    sre_log = _load_json_log("sre_change_history.json")

    # KPI metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("API Log Entries", len(df) if not df.empty else 0)
    m2.metric("API Change Records", len(api_log))
    m3.metric("SRE Change Records", len(sre_log))
    total_all = (len(df) if not df.empty else 0) + len(api_log) + len(sre_log)
    m4.metric("Total Records", total_all)

    st.markdown("---")

    # Main tabs
    tab_live, tab_api, tab_sre, tab_search, tab_export = st.tabs([
        "📡 Live Changes", "🔌 API Changes", "🛠️ SRE History", "🔍 Search", "📤 Export"
    ])

    # ─── TAB 1: Live Changes (existing enhanced) ───
    with tab_live:
        c1, c2 = st.columns(2)
        filter_val = c1.selectbox("Filter History Logs By:", ["All Changes", "🤖 Auto Updates Only", "👤 Manual Overrides Only"])
        date_range = c2.date_input(
            "Filter Date Range",
            value=(datetime.date.today() - datetime.timedelta(days=7), datetime.date.today()),
            key="live_date_range"
        )

        st.markdown("#### Audit Trail")

        if df.empty:
            st.info("No changes logged yet. Changes will appear here as the system runs.")
        else:
            filtered_df = df.copy()

            if "Auto" in filter_val:
                filtered_df = filtered_df[filtered_df["Changed By"].str.contains("🤖", na=False)]
            elif "Manual" in filter_val:
                filtered_df = filtered_df[~filtered_df["Changed By"].str.contains("🤖", na=False)]

            # Date filter
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                start_d, end_d = date_range
                def _parse_date(s):
                    try:
                        return pd.to_datetime(s, dayfirst=True).date()
                    except Exception:
                        return None
                filtered_df["_date"] = filtered_df["Date-Time (IST)"].apply(_parse_date)
                filtered_df = filtered_df[(filtered_df["_date"] >= start_d) & (filtered_df["_date"] <= end_d)]
                filtered_df = filtered_df.drop(columns=["_date"])

            st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # ─── TAB 2: API Change Log ───
    with tab_api:
        st.subheader("🔌 API Change Log")
        if not api_log:
            st.info("No API change log entries found.")
        elif pd is not None:
            df_api = pd.DataFrame(api_log)

            # Filters
            af1, af2, af3 = st.columns(3)
            with af1:
                if "component" in df_api.columns:
                    components = sorted(df_api["component"].unique().tolist())
                    sel_comp = st.selectbox("Component", ["All"] + components, key="api_comp")
                else:
                    sel_comp = "All"
            with af2:
                if "trigger" in df_api.columns:
                    triggers = sorted(df_api["trigger"].unique().tolist())
                    sel_trigger = st.selectbox("Trigger Type", ["All"] + triggers, key="api_trigger")
                else:
                    sel_trigger = "All"
            with af3:
                st.metric("Total API Changes", len(df_api))

            filtered_api = df_api.copy()
            if sel_comp != "All" and "component" in filtered_api.columns:
                filtered_api = filtered_api[filtered_api["component"] == sel_comp]
            if sel_trigger != "All" and "trigger" in filtered_api.columns:
                filtered_api = filtered_api[filtered_api["trigger"] == sel_trigger]

            display_cols = [c for c in ["datetime_ist", "component", "what_changed", "old_value", "new_value", "reason", "trigger", "user_id"] if c in filtered_api.columns]
            st.dataframe(filtered_api[display_cols] if display_cols else filtered_api, use_container_width=True, hide_index=True)

    # ─── TAB 3: SRE Change History ───
    with tab_sre:
        st.subheader("🛠️ SRE Change History")
        if not sre_log:
            st.info("No SRE change history entries found.")
        elif pd is not None:
            df_sre = pd.DataFrame(sre_log)

            # Filters
            sf1, sf2, sf3 = st.columns(3)
            with sf1:
                if "source" in df_sre.columns:
                    sources = sorted(df_sre["source"].unique().tolist())
                    sel_source = st.selectbox("Source", ["All"] + sources, key="sre_source")
                else:
                    sel_source = "All"
            with sf2:
                if "actor" in df_sre.columns:
                    actors = sorted(df_sre["actor"].unique().tolist())
                    sel_actor = st.selectbox("Actor", ["All"] + actors, key="sre_actor")
                else:
                    sel_actor = "All"
            with sf3:
                st.metric("Total SRE Changes", len(df_sre))

            filtered_sre = df_sre.copy()
            if sel_source != "All" and "source" in filtered_sre.columns:
                filtered_sre = filtered_sre[filtered_sre["source"] == sel_source]
            if sel_actor != "All" and "actor" in filtered_sre.columns:
                filtered_sre = filtered_sre[filtered_sre["actor"] == sel_actor]

            display_cols = [c for c in ["change_id", "timestamp_ist", "entity", "field", "old_value", "new_value", "actor", "source"] if c in filtered_sre.columns]
            st.dataframe(filtered_sre[display_cols] if display_cols else filtered_sre, use_container_width=True, hide_index=True)

    # ─── TAB 4: Search ───
    with tab_search:
        st.subheader("🔍 Search Change Log")
        search_query = st.text_input("Search across all change logs", placeholder="e.g. fallback, price, manual...", key="cl_search")

        if search_query and pd is not None:
            results_found = False

            # Search in live log
            if not df.empty:
                mask = df.apply(lambda row: search_query.lower() in str(row.values).lower(), axis=1)
                matched_live = df[mask]
                if not matched_live.empty:
                    st.markdown(f"##### Live Change Log ({len(matched_live)} matches)")
                    st.dataframe(matched_live, use_container_width=True, hide_index=True)
                    results_found = True

            # Search in API log
            if api_log:
                df_api_search = pd.DataFrame(api_log)
                mask = df_api_search.apply(lambda row: search_query.lower() in str(row.values).lower(), axis=1)
                matched_api = df_api_search[mask]
                if not matched_api.empty:
                    st.markdown(f"##### API Change Log ({len(matched_api)} matches)")
                    st.dataframe(matched_api, use_container_width=True, hide_index=True)
                    results_found = True

            # Search in SRE log
            if sre_log:
                df_sre_search = pd.DataFrame(sre_log)
                mask = df_sre_search.apply(lambda row: search_query.lower() in str(row.values).lower(), axis=1)
                matched_sre = df_sre_search[mask]
                if not matched_sre.empty:
                    st.markdown(f"##### SRE Change History ({len(matched_sre)} matches)")
                    st.dataframe(matched_sre, use_container_width=True, hide_index=True)
                    results_found = True

            if not results_found:
                st.warning(f"No results found for '{search_query}'.")
        elif not search_query:
            st.info("Enter a search term to search across all change logs.")

    # ─── TAB 5: Export ───
    with tab_export:
        st.subheader("📤 Export Change Logs")

        export_source = st.selectbox("Select Source to Export", [
            "Live Change Log", "API Change Log", "SRE Change History", "All Combined"
        ], key="export_src")

        if st.button("Generate CSV Export", type="primary", key="export_btn"):
            if pd is None:
                st.error("pandas not available for export.")
            else:
                export_df = pd.DataFrame()

                if export_source == "Live Change Log" and not df.empty:
                    export_df = df.copy()
                elif export_source == "API Change Log" and api_log:
                    export_df = pd.DataFrame(api_log)
                elif export_source == "SRE Change History" and sre_log:
                    export_df = pd.DataFrame(sre_log)
                elif export_source == "All Combined":
                    frames = []
                    if not df.empty:
                        live_copy = df.copy()
                        live_copy["_source"] = "Live"
                        frames.append(live_copy)
                    if api_log:
                        api_df = pd.DataFrame(api_log)
                        api_df["_source"] = "API"
                        frames.append(api_df)
                    if sre_log:
                        sre_df = pd.DataFrame(sre_log)
                        sre_df["_source"] = "SRE"
                        frames.append(sre_df)
                    if frames:
                        export_df = pd.concat(frames, ignore_index=True)

                if export_df.empty:
                    st.warning("No data available for the selected source.")
                else:
                    csv_data = export_df.to_csv(index=False).encode("utf-8")
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"change_log_export_{timestamp}.csv"
                    st.download_button(
                        label=f"⬇️ Download {filename}",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        key="download_csv"
                    )
                    st.success(f"Export ready! {len(export_df)} rows.")
                    st.dataframe(export_df.head(10), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 📊 Change Log Overview")
        if go is not None and pd is not None:
            source_data = {
                "Live Log": len(df) if not df.empty else 0,
                "API Changes": len(api_log),
                "SRE History": len(sre_log),
            }
            fig_overview = go.Figure(go.Bar(
                x=list(source_data.keys()), y=list(source_data.values()),
                marker_color=["#1e3a5f", "#3b82f6", "#e8dcc8"],
                text=list(source_data.values()), textposition="auto"
            ))
            fig_overview.update_layout(
                title="Records by Source",
                template="plotly_white", height=300,
                yaxis_title="Count"
            )
            st.plotly_chart(fig_overview, use_container_width=True)
