import streamlit as st
import sys, os, json, datetime
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


def _load_real_error_log():
    """Load real error log from api_manager. Returns a display-ready DataFrame."""
    try:
        from api_manager import get_error_log
        records = get_error_log(n=200)
    except Exception:
        records = []

    if not records:
        return pd.DataFrame(columns=["Timestamp (IST)", "Severity", "Component", "Message", "Auto-Fix?", "Status", "Notes"])

    rows = []
    for r in records:
        auto_fix = "✅ Yes" if r.get("auto_fixed") else "❌ No"
        status_raw = r.get("status", "Open")
        if status_raw == "Auto-Fixed":
            status = "✅ Fixed"
        elif status_raw == "Open":
            status = "🔴 Open"
        elif status_raw == "Suppressed":
            status = "⚫ Suppressed"
        else:
            status = f"⚠️ {status_raw}"
        rows.append({
            "Timestamp (IST)": r.get("datetime_ist", ""),
            "Severity": r.get("severity", ""),
            "Component": r.get("component", ""),
            "Message": r.get("message", ""),
            "Auto-Fix?": auto_fix,
            "Status": status,
            "Notes": r.get("resolution_notes", r.get("root_cause", "")),
        })
    return pd.DataFrame(rows)


def _load_json(filename):
    """Load a JSON file from project root."""
    try:
        fpath = ROOT / filename
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def render():
    display_badge("errors")
    st.markdown("### 🐞 Developer Ops & Bug / Error Tracker")
    st.info("Live feed from `api_manager.py` error log. Every API fault, fallback, and auto-heal is stamped here in real time.")

    st.markdown("---")

    df = _load_real_error_log()
    dir_bugs = _load_json("tbl_dir_bugs.json")
    sre_bugs = _load_json("sre_bugs.json")
    all_bugs = dir_bugs + sre_bugs

    # Combined metrics
    c1, c2, c3, c4 = st.columns(4)
    p0_open = len(df[(df["Severity"].str.contains("P0", na=False)) & (df["Status"].str.contains("Open", na=False))]) if not df.empty else 0
    auto_heals = len(df[df["Auto-Fix?"].str.startswith("✅", na=False)]) if not df.empty else 0
    total = len(df)
    json_bugs_total = len(all_bugs)

    c1.metric("Total Logged Errors", str(total))
    c2.metric("P0 Open Bugs", str(p0_open), "All Clear" if p0_open == 0 else f"⚠️ {p0_open} Open")
    c3.metric("Auto-Heals Logged", str(auto_heals))
    c4.metric("JSON Bug Records", str(json_bugs_total))

    st.markdown("---")

    # Tabs: Open Bugs | Resolved | Analytics
    tab_open, tab_resolved, tab_analytics = st.tabs(["🔴 Open Bugs", "✅ Resolved", "📊 Analytics"])

    # ─── TAB 1: Open Bugs ───
    with tab_open:
        st.subheader("Open / Active Bugs")

        # Severity filter
        sev_col1, sev_col2 = st.columns([1, 3])
        with sev_col1:
            sev_filter = st.selectbox("Severity Filter", ["All", "P0", "P1", "P2", "P3"], key="open_sev")

        # From error log
        if not df.empty:
            open_df = df[df["Status"].str.contains("Open", na=False)]
            if sev_filter != "All":
                open_df = open_df[open_df["Severity"].str.contains(sev_filter, na=False)]
            if not open_df.empty:
                st.markdown("##### From API Error Log")
                st.dataframe(open_df, use_container_width=True, hide_index=True)
            else:
                st.success("No open bugs matching the filter from API error log.")

        # From JSON files
        open_json = [b for b in all_bugs if b.get("status", "").lower() not in ("verified", "resolved", "closed", "fixed")]
        if sev_filter != "All":
            open_json = [b for b in open_json if b.get("severity", "") == sev_filter]

        if open_json and pd is not None:
            st.markdown("##### From Bug Database (JSON)")
            df_open_json = pd.DataFrame(open_json)
            display_cols = [c for c in ["bug_id", "severity", "title", "component_owner", "status", "created_ist"] if c in df_open_json.columns]
            st.dataframe(df_open_json[display_cols] if display_cols else df_open_json, use_container_width=True, hide_index=True)
        elif not open_json:
            st.success("No open bugs in JSON bug database.")

        # Bug detail cards
        if open_json:
            st.markdown("##### Bug Details")
            for bug in open_json[:10]:
                severity = bug.get("severity", "P2")
                sev_color = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(severity, "⚪")
                with st.expander(f"{sev_color} [{severity}] {bug.get('title', 'Untitled')} — {bug.get('bug_id', '')}"):
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        st.write(f"**Component:** {bug.get('component_owner', '-')}")
                        st.write(f"**Entity:** {bug.get('entity', '-')}")
                        st.write(f"**Created:** {bug.get('created_ist', '-')}")
                    with bc2:
                        st.write(f"**Status:** {bug.get('status', '-')}")
                        st.write(f"**Auto-Created:** {'Yes' if bug.get('auto_created') else 'No'}")
                        st.write(f"**Updated:** {bug.get('updated_ist', '-')}")
                    steps = bug.get("reproduction_steps", [])
                    if steps:
                        st.markdown("**Reproduction Steps:**")
                        for step in steps:
                            st.markdown(f"  - {step}")

    # ─── TAB 2: Resolved ───
    with tab_resolved:
        st.subheader("Resolved / Verified Bugs")

        # From error log
        if not df.empty:
            resolved_df = df[df["Status"].str.contains("Fixed|Suppressed", na=False)]
            if not resolved_df.empty:
                st.markdown("##### Auto-Fixed from API Error Log")
                st.dataframe(resolved_df, use_container_width=True, hide_index=True)
            else:
                st.info("No resolved bugs from API error log.")

        # From JSON
        resolved_json = [b for b in all_bugs if b.get("status", "").lower() in ("verified", "resolved", "closed", "fixed")]
        if resolved_json and pd is not None:
            st.markdown("##### Verified/Resolved from Bug Database")
            df_resolved = pd.DataFrame(resolved_json)
            display_cols = [c for c in ["bug_id", "severity", "title", "component_owner", "status", "created_ist", "updated_ist"] if c in df_resolved.columns]
            st.dataframe(df_resolved[display_cols] if display_cols else df_resolved, use_container_width=True, hide_index=True)
        elif not resolved_json:
            st.info("No resolved bugs in JSON bug database.")

    # ─── TAB 3: Analytics ───
    with tab_analytics:
        st.subheader("📊 Bug Analytics & Trends")

        if not all_bugs and df.empty:
            st.info("No bug data available for analytics.")
        else:
            # Severity distribution
            st.markdown("#### Severity Distribution")
            if all_bugs and pd is not None:
                df_bugs = pd.DataFrame(all_bugs)
                if "severity" in df_bugs.columns:
                    sev_counts = df_bugs["severity"].value_counts().reset_index()
                    sev_counts.columns = ["Severity", "Count"]

                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if go is not None:
                            colors_map = {"P0": "#ef4444", "P1": "#f97316", "P2": "#eab308", "P3": "#22c55e"}
                            fig_sev = go.Figure(go.Bar(
                                x=sev_counts["Severity"], y=sev_counts["Count"],
                                marker_color=[colors_map.get(s, "#64748b") for s in sev_counts["Severity"]],
                                text=sev_counts["Count"], textposition="auto"
                            ))
                            fig_sev.update_layout(
                                title="Bugs by Severity", template="plotly_white", height=350,
                                xaxis_title="Severity", yaxis_title="Count"
                            )
                            st.plotly_chart(fig_sev, use_container_width=True)
                        else:
                            st.dataframe(sev_counts, use_container_width=True, hide_index=True)
                    with sc2:
                        if go is not None:
                            fig_pie = go.Figure(go.Pie(
                                labels=sev_counts["Severity"], values=sev_counts["Count"],
                                hole=0.4,
                                marker_colors=[colors_map.get(s, "#64748b") for s in sev_counts["Severity"]]
                            ))
                            fig_pie.update_layout(title="Severity Share", height=350)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        else:
                            st.dataframe(sev_counts, use_container_width=True, hide_index=True)

            # Status breakdown
            st.markdown("#### Status Breakdown")
            if all_bugs and pd is not None:
                if "status" in df_bugs.columns:
                    status_counts = df_bugs["status"].value_counts().reset_index()
                    status_counts.columns = ["Status", "Count"]
                    s1, s2, s3 = st.columns(3)
                    for idx, row in status_counts.iterrows():
                        col = [s1, s2, s3][idx % 3]
                        with col:
                            st.metric(row["Status"], row["Count"])

            # Component distribution
            st.markdown("#### Bugs by Component")
            if all_bugs and pd is not None:
                comp_col = "component_owner" if "component_owner" in df_bugs.columns else "component"
                if comp_col in df_bugs.columns:
                    comp_counts = df_bugs[comp_col].value_counts().reset_index()
                    comp_counts.columns = ["Component", "Count"]
                    st.dataframe(comp_counts, use_container_width=True, hide_index=True)

            # Trend chart — bugs over time
            st.markdown("#### Bug Creation Trend")
            if all_bugs and pd is not None and go is not None:
                dates_parsed = []
                for b in all_bugs:
                    created = b.get("created_ist", "")
                    status = b.get("status", "Open")
                    for fmt in ("%Y-%m-%d %H:%M:%S IST", "%Y-%m-%d %H:%M IST", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                        try:
                            dt = datetime.datetime.strptime(created, fmt)
                            dates_parsed.append({"date": dt.date(), "status": status})
                            break
                        except ValueError:
                            continue

                if dates_parsed:
                    df_trend = pd.DataFrame(dates_parsed)
                    # Created count by date
                    created_by_date = df_trend.groupby("date").size().reset_index(name="Created")
                    # Resolved count by date
                    resolved_mask = df_trend["status"].str.lower().isin(["verified", "resolved", "closed", "fixed"])
                    resolved_by_date = df_trend[resolved_mask].groupby("date").size().reset_index(name="Resolved")

                    merged = created_by_date.merge(resolved_by_date, on="date", how="left").fillna(0)
                    merged = merged.sort_values("date")

                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(
                        x=merged["date"], y=merged["Created"],
                        mode="lines+markers", name="Created",
                        line=dict(color="#ef4444", width=2)
                    ))
                    fig_trend.add_trace(go.Scatter(
                        x=merged["date"], y=merged["Resolved"],
                        mode="lines+markers", name="Resolved",
                        line=dict(color="#22c55e", width=2)
                    ))
                    fig_trend.update_layout(
                        title="Bugs Created vs Resolved Over Time",
                        xaxis_title="Date", yaxis_title="Count",
                        template="plotly_white", height=400,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.caption("No date-parseable bugs for trend chart.")

            # Full log archive
            st.markdown("---")
            st.markdown("#### System Log Archive")
            filter_val = st.selectbox("Severity", ["All", "P0", "P1", "P2", "P3"], key="archive_sev")
            if not df.empty:
                df_display = df if filter_val == "All" else df[df["Severity"].str.contains(filter_val, na=False)]
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.info("No errors logged yet.")
