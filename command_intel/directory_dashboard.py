# command_intel/directory_dashboard.py
# PPS Anantam Agentic AI Eco System — v3.3.0
# India Bitumen & Roads Procurement Directory — Dashboard (5-tab UI)

from __future__ import annotations

import datetime
import io
from typing import Any, Dict, List

import streamlit as st

# ── Safe imports ───────────────────────────────────────────────────────────────
try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    import plotly.express as px
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

try:
    from directory_engine import (
        init_directory,
        search_directory,
        get_coverage_report,
        add_org_to_crm,
        create_task_for_org,
        SEED_PHASE1,
    )
    _ENGINE = True
except ImportError:
    _ENGINE = False
    SEED_PHASE1 = []

try:
    from directory_fetcher import (
        SOURCE_REGISTRY,
        run_phase1_refresh,
        get_fetch_stats,
    )
    _FETCHER = True
except ImportError:
    _FETCHER = False
    SOURCE_REGISTRY = {}

try:
    from pdf_export_bar import render_export_bar
    _PDF_BAR = True
except ImportError:
    _PDF_BAR = False
    def render_export_bar(*a, **kw): pass

# ── Constants ──────────────────────────────────────────────────────────────────
_LEVEL_COLORS = {
    "Central":  "#1e3a5f",
    "State":    "#2d6a4f",
    "City":     "#c9a84c",
    "District": "#7b5ea7",
    "Block":    "#b5451b",
    "Village":  "#5a6474",
}

_CONF_BADGE = {
    "High":   ("🟢", "#d4edda", "#155724"),
    "Medium": ("🟡", "#fff3cd", "#856404"),
    "Low":    ("🔴", "#f8d7da", "#721c24"),
}

_PAGE_SIZE = 25

_ALL_STATES = sorted(set(o["state_ut"] for o in SEED_PHASE1)) if SEED_PHASE1 else []
_ALL_LEVELS = ["Central", "State", "City", "District", "Block", "Village"]
_ALL_DEPT_TYPES = ["NHAI", "PWD", "PMGSY", "BRO", "StateCorpn", "Municipal"]


# ══════════════════════════════════════════════════════════════════════════════
# KPI BAR
# ══════════════════════════════════════════════════════════════════════════════
def _render_kpi_bar() -> None:
    if not _ENGINE:
        st.warning("directory_engine not available.")
        return

    report  = get_coverage_report()
    p1      = report.get("phase1", {})
    orgs    = search_directory(page_size=9999)
    all_res = orgs.get("results", []) if not orgs.get("total", 0) else []
    # Use full count
    total   = search_directory(page_size=1).get("total", 0) + (p1.get("total", 0) if True else 0)
    # Simpler: use coverage report grand total
    total   = report.get("grand_total", 0)

    central_cnt = sum(1 for o in SEED_PHASE1 if o.get("level") == "Central")
    state_cnt   = sum(1 for o in SEED_PHASE1 if o.get("level") == "State")
    corp_cnt    = sum(1 for o in SEED_PHASE1 if o.get("dept_type") == "StateCorpn")
    p1_pct      = p1.get("pct", 0.0)

    fetch_stats = get_fetch_stats() if _FETCHER else {}
    last_run    = fetch_stats.get("last_run_ist", "Never")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Entries",   f"{total:,}",       help="All Phase 1 entries in directory")
    c2.metric("Central Bodies",  f"{central_cnt}",   help="MoRTH, NHAI, NHIDCL, NRIDA, CPWD, BRO + ROs")
    c3.metric("State/UT HQs",   f"{state_cnt}",     help="All 28 states + 8 UTs (PWD/R&B/Highways)")
    c4.metric("Corporations",    f"{corp_cnt}",      help="State Road Development Corporations")
    c5.metric("Phase 1 Cover%", f"{p1_pct:.1f}%",   help="% of Phase 1 target entries seeded")
    c6.metric("Last Verified",   last_run,           help="Most recent live URL verification")


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH + FILTER BAR
# ══════════════════════════════════════════════════════════════════════════════
def _render_search_filters() -> dict:
    """Renders search bar + filter expander. Returns filters dict."""
    query = st.text_input(
        "Search directory",
        placeholder="Type org name, city, state, email, role...",
        key="dir_search_query",
    )

    filters: dict = {}
    with st.expander("Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            lvl = st.multiselect("Level", _ALL_LEVELS, key="dir_f_level")
            if lvl:
                filters["level"] = lvl
        with col2:
            st_sel = st.multiselect("State / UT", _ALL_STATES, key="dir_f_state")
            if st_sel:
                filters["state_ut"] = st_sel
        with col3:
            dt_sel = st.multiselect("Dept Type", _ALL_DEPT_TYPES, key="dir_f_dtype")
            if dt_sel:
                filters["dept_type"] = dt_sel

        col4, col5, col6 = st.columns(3)
        with col4:
            if st.checkbox("Has Email", key="dir_f_email"):
                filters["has_email"] = True
        with col5:
            if st.checkbox("Has Phone", key="dir_f_phone"):
                filters["has_phone"] = True
        with col6:
            conf = st.multiselect("Confidence", ["High", "Medium", "Low"], key="dir_f_conf")
            if conf:
                filters["confidence"] = conf

    return {"query": query, "filters": filters}


# ══════════════════════════════════════════════════════════════════════════════
# TAB A — DIRECTORY TABLE
# ══════════════════════════════════════════════════════════════════════════════
def _render_directory_tab(query: str, filters: dict) -> None:
    if not _ENGINE:
        st.error("directory_engine module not available.")
        return

    # Pagination state
    if "dir_page" not in st.session_state:
        st.session_state["dir_page"] = 0

    page = st.session_state["dir_page"]
    result = search_directory(query=query, filters=filters, page=page, page_size=_PAGE_SIZE)
    items  = result["results"]
    total  = result["total"]
    pages  = result["pages"]

    # Result count + CSV download
    hdr_col, dl_col = st.columns([4, 1])
    with hdr_col:
        st.caption(f"Showing {len(items)} of {total} entries | Page {page + 1} of {pages}")
    with dl_col:
        if _PANDAS and items:
            all_result = search_directory(query=query, filters=filters, page=0, page_size=9999)
            df_dl = pd.DataFrame(all_result["results"])
            csv_bytes = df_dl.to_csv(index=False).encode("utf-8")
            st.download_button(
                "CSV Export",
                data=csv_bytes,
                file_name=f"india_procurement_dir_{datetime.date.today()}.csv",
                mime="text/csv",
                key="dir_csv_dl",
            )

    if not items:
        st.info("No entries match your search. Try clearing filters or broadening the query.")
        return

    # Table rows
    for org in items:
        conf_icon, conf_bg, conf_fg = _CONF_BADGE.get(org.get("confidence", "Low"), ("🔴", "#f8d7da", "#721c24"))
        lvl_color = _LEVEL_COLORS.get(org.get("level", "State"), "#5a6474")

        with st.container():
            row_col1, row_col2, row_col3, row_col4 = st.columns([4, 2, 2, 2])

            with row_col1:
                st.markdown(
                    f"**{org.get('dept_name', '')}** "
                    f"<span style='font-size:0.7rem;color:{lvl_color};font-weight:700;'>"
                    f"[{org.get('level', '')}]</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"{org.get('city', '')} · {org.get('state_ut', '')} | "
                    f"{org.get('dept_type', '')} | {org.get('short_name', '')}"
                )
                if org.get("roads_role"):
                    st.caption(f"Role: {org.get('roads_role', '')[:100]}")

            with row_col2:
                email = org.get("official_email", "")
                phone = org.get("official_phone", "") or org.get("helpline", "")
                if email and "not published" not in email.lower():
                    st.markdown(f"📧 {email}")
                else:
                    st.caption("Email: Not Published")
                if phone:
                    st.markdown(f"📞 {phone}")
                if org.get("helpline") and org.get("helpline") != phone:
                    st.markdown(f"🆘 {org.get('helpline')}")

            with row_col3:
                website = org.get("website", "")
                if website:
                    st.markdown(f"[🌐 Website]({website})")
                src = org.get("source_url", "")
                if src:
                    st.markdown(f"[📋 Source]({src})")
                # Confidence badge
                st.markdown(
                    f"<span style='background:{conf_bg};color:{conf_fg};font-size:0.7rem;"
                    f"padding:2px 8px;border-radius:10px;font-weight:700;'>"
                    f"{conf_icon} {org.get('confidence', '')}</span>",
                    unsafe_allow_html=True,
                )

            with row_col4:
                org_id = org.get("org_id", "")
                # CRM button
                if st.button("+ CRM", key=f"crm_{org_id}", help="Add to CRM tasks"):
                    tid = add_org_to_crm(org_id, task_type="Email")
                    if tid:
                        st.success(f"CRM task created: {tid}")
                    else:
                        st.warning("CRM not available.")
                # Task button with form
                with st.popover("Task"):
                    task_type = st.selectbox(
                        "Type", ["Email", "Call", "Visit", "Follow-Up", "Tender"],
                        key=f"tt_{org_id}"
                    )
                    task_note = st.text_input("Note", key=f"tn_{org_id}")
                    due_hours = st.selectbox("Due in", [24, 48, 72, 168], key=f"due_{org_id}")
                    if st.button("Create Task", key=f"ct_{org_id}"):
                        tid = create_task_for_org(org_id, task_type, int(due_hours), task_note)
                        if tid:
                            st.success(f"Task {tid} created")
                        else:
                            st.warning("CRM unavailable.")

            st.markdown('<hr style="margin:4px 0;border-color:#e8dcc8;">', unsafe_allow_html=True)

    # Pagination controls
    pg_col1, pg_col2, pg_col3 = st.columns([2, 4, 2])
    with pg_col1:
        if page > 0:
            if st.button("Prev", key="dir_prev"):
                st.session_state["dir_page"] = page - 1
                st.rerun()
    with pg_col2:
        st.caption(f"Page {page + 1} / {pages}")
    with pg_col3:
        if page < pages - 1:
            if st.button("Next", key="dir_next"):
                st.session_state["dir_page"] = page + 1
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB B — INDIA MAP
# ══════════════════════════════════════════════════════════════════════════════
def _render_map_tab() -> None:
    if not _PLOTLY:
        st.warning("Plotly not installed. Install with: pip install plotly")
        return
    if not _ENGINE:
        st.error("directory_engine not available.")
        return
    if not _PANDAS:
        st.warning("Pandas not available for map data.")
        return

    result = search_directory(page_size=9999)
    # Get all orgs regardless of filter for full map view
    from directory_engine import _load, TBL_DIR_ORGS
    all_orgs = _load(TBL_DIR_ORGS, [])

    if not all_orgs:
        st.info("No data available. Run init_directory() first.")
        return

    df = pd.DataFrame(all_orgs)
    df = df.dropna(subset=["lat", "long"])
    df = df[(df["lat"] != 0) & (df["long"] != 0)]

    if df.empty:
        st.info("No geo data available.")
        return

    df["hover_text"] = (
        df["dept_name"] + "<br>" +
        df["city"] + ", " + df["state_ut"] + "<br>" +
        "Phone: " + df["official_phone"].fillna("—") + "<br>" +
        "Email: " + df["official_email"].fillna("—") + "<br>" +
        "Confidence: " + df["confidence"].fillna("—")
    )

    fig = px.scatter_geo(
        df,
        lat="lat",
        lon="long",
        color="level",
        color_discrete_map={
            "Central":  "#1e3a5f",
            "State":    "#2d6a4f",
            "City":     "#c9a84c",
            "District": "#7b5ea7",
            "Block":    "#b5451b",
            "Village":  "#5a6474",
        },
        hover_name="dept_name",
        hover_data={
            "lat":   False,
            "long":  False,
            "city":  True,
            "state_ut":  True,
            "official_phone":  True,
            "confidence": True,
        },
        scope="asia",
        center={"lat": 20.5937, "lon": 78.9629},
        title="India Roads & Bitumen Procurement Directory — Phase 1",
        size_max=12,
    )

    fig.update_geos(
        fitbounds="locations",
        visible=True,
        resolution=50,
        showcountries=True,
        countrycolor="#e8dcc8",
        showsubunits=True,
        subunitcolor="#f0ebe1",
        bgcolor="#fafaf8",
    )
    fig.update_layout(
        height=620,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="#fafaf8",
        legend=dict(
            title="Level",
            bgcolor="#ffffff",
            bordercolor="#e8dcc8",
            borderwidth=1,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Map shows all Phase 1 entries (56 entries). "
        "Central = MoRTH/NHAI/NHIDCL/NRIDA/CPWD/BRO. "
        "State = PWD/R&B/Highways HQ + NHAI ROs. "
        "Corporations = MSRDC/GSRDC/KRDCL etc."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB C — COVERAGE REPORT
# ══════════════════════════════════════════════════════════════════════════════
def _render_coverage_tab() -> None:
    if not _ENGINE:
        st.error("directory_engine not available.")
        return

    report = get_coverage_report()
    st.subheader("Phase Completion")

    phases = [
        ("Phase 1", "Central, State HQs, NHAI ROs, Corporations", report.get("phase1", {})),
        ("Phase 2", "District Offices (700+ targets)", report.get("phase2", {})),
        ("Phase 3", "City/Block Offices (4,000+ targets)", report.get("phase3", {})),
        ("Phase 4", "Village/GP Contacts (30,000+ targets)", report.get("phase4", {})),
    ]

    for ph_name, ph_desc, ph_data in phases:
        found  = ph_data.get("total", 0)
        target = ph_data.get("target", 1)
        pct    = ph_data.get("pct", 0.0)
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.markdown(f"**{ph_name}** — {ph_desc}")
            st.progress(min(pct / 100, 1.0))
        with col_b:
            st.markdown(f"**{found:,} / {target:,}** ({pct:.1f}%)")
        st.markdown("")

    st.markdown("---")
    st.subheader("State / UT Coverage (Phase 1)")

    p1_by_state = report.get("phase1", {}).get("pct_by_state", {})
    if not p1_by_state:
        st.info("No data yet.")
        return

    rows = []
    for state, data in sorted(p1_by_state.items()):
        found  = data.get("found", 0)
        target = data.get("target", 1)
        status = "Complete" if found >= target else "Missing"
        rows.append({
            "State / UT":   state,
            "Phase 1 HQ":   found,
            "Target":       target,
            "Status":       status,
        })

    if _PANDAS:
        df = pd.DataFrame(rows)
        # Color-code missing rows
        def _color_status(val):
            if val == "Missing":
                return "background-color: #fff3cd; color: #856404;"
            return "background-color: #d4edda; color: #155724;"
        st.dataframe(
            df.style.applymap(_color_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        for r in rows:
            icon = "✅" if r["Status"] == "Complete" else "⚠️"
            st.write(f"{icon} {r['State / UT']} — Phase 1 HQ: {r['Phase 1 HQ']}/{r['Target']}")

    st.caption(
        f"Generated: {report.get('generated_ist', '')} | "
        "Phase 2-4 data will be added in subsequent releases."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB D — SOURCE REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
def _render_source_registry_tab() -> None:
    if not _FETCHER:
        st.warning("directory_fetcher module not available.")
        return

    st.subheader("Source Registry — Phase 1 (56 URLs)")

    stats = get_fetch_stats()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Fetches",   stats.get("total_fetches", 0))
    m2.metric("Successful",      stats.get("ok", 0))
    m3.metric("Errors",          stats.get("errors", 0))
    m4.metric("Open Bugs",       stats.get("open_bugs", 0))

    st.markdown("---")

    # Refresh button
    col_a, col_b = st.columns([4, 1])
    with col_b:
        if st.button("Refresh Phase 1", key="dir_refresh_btn"):
            with st.spinner("Refreshing... this may take 2-5 minutes (56 URLs)"):
                result = run_phase1_refresh(force=True)
            st.success(
                f"Done — Updated: {result.get('updated', 0)} | "
                f"Failed: {result.get('failed', 0)} | "
                f"Skipped: {result.get('skipped', 0)}"
            )

    with col_a:
        st.caption("Click 'Refresh Phase 1' to live-verify all 56 source URLs.")

    # Registry table
    if not _PANDAS:
        for org_id, reg in SOURCE_REGISTRY.items():
            st.write(f"**{org_id}** — {reg['url']} ({reg['schedule']})")
        return

    rows = []
    for org_id, reg in SOURCE_REGISTRY.items():
        rows.append({
            "Org ID":   org_id,
            "URL":      reg.get("url", ""),
            "Schedule": reg.get("schedule", ""),
            "Type":     reg.get("type", "HTML"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Total: {len(SOURCE_REGISTRY)} source URLs registered for Phase 1.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB E — BUG TRACKER
# ══════════════════════════════════════════════════════════════════════════════
def _render_bug_tracker_tab() -> None:
    from pathlib import Path
    import json
    _BASE = Path(__file__).parent.parent
    _TBL_BUGS = _BASE / "tbl_dir_bugs.json"

    try:
        with open(_TBL_BUGS, encoding="utf-8") as f:
            bugs = json.load(f)
    except Exception:
        bugs = []

    open_bugs   = [b for b in bugs if b.get("status") == "open"]
    closed_bugs = [b for b in bugs if b.get("status") != "open"]

    st.subheader(f"Bug Tracker — {len(open_bugs)} Open / {len(closed_bugs)} Resolved")

    if not open_bugs:
        st.success("No open bugs. All source URLs are healthy.")
    else:
        st.warning(f"{len(open_bugs)} open fetch failures.")

    col_a, col_b = st.columns([4, 1])
    with col_b:
        if st.button("Retry Failed", key="dir_retry_btn") and _FETCHER:
            failed_ids = [b["org_id"] for b in open_bugs]
            if failed_ids:
                from directory_fetcher import fetch_and_verify_org
                ok_count = 0
                for oid in failed_ids:
                    r = fetch_and_verify_org(oid)
                    if r.get("ok"):
                        ok_count += 1
                st.success(f"Retried {len(failed_ids)} orgs — {ok_count} recovered.")
            else:
                st.info("No failed orgs to retry.")

    if bugs and _PANDAS:
        df = pd.DataFrame(bugs)
        cols = ["org_id", "source_url", "error", "http_code",
                "first_seen_ist", "last_seen_ist", "retry_count", "status"]
        existing_cols = [c for c in cols if c in df.columns]
        st.dataframe(df[existing_cols], use_container_width=True, hide_index=True)
    elif bugs:
        for b in bugs[:20]:
            icon = "🔴" if b.get("status") == "open" else "✅"
            st.write(f"{icon} **{b.get('org_id')}** — {b.get('error', '')} (HTTP {b.get('http_code', '')})")


# ══════════════════════════════════════════════════════════════════════════════
# PDF EXPORT CONTENT FUNCTION
# ══════════════════════════════════════════════════════════════════════════════
def _pdf_content() -> list:
    """Returns structured content list for render_export_bar."""
    if not _ENGINE:
        return []

    report = get_coverage_report()
    p1     = report.get("phase1", {})

    sections = [
        {"type": "section", "text": "India Procurement Directory — Phase 1 Summary"},
        {"type": "table",
         "headers": ["Metric", "Value"],
         "rows": [
             ["Total Entries",       str(report.get("grand_total", 0))],
             ["Phase 1 Coverage",    f"{p1.get('pct', 0):.1f}%"],
             ["Phase 1 Target",      str(p1.get("target", 56))],
             ["Phase 1 Found",       str(p1.get("total", 0))],
             ["Generated",           report.get("generated_ist", "")],
         ]},
        {"type": "section", "text": "Directory Entries"},
    ]

    result = search_directory(page_size=9999)
    orgs   = result.get("results", [])
    if orgs:
        rows = []
        for o in orgs[:200]:   # cap at 200 for PDF
            rows.append([
                o.get("dept_name", ""),
                o.get("level", ""),
                o.get("state_ut", ""),
                o.get("city", ""),
                o.get("official_phone", "") or o.get("helpline", ""),
                o.get("official_email", ""),
                o.get("confidence", ""),
            ])
        sections.append({
            "type":    "table",
            "headers": ["Dept Name", "Level", "State/UT", "City", "Phone", "Email", "Conf."],
            "rows":    rows,
        })

    return sections


# ══════════════════════════════════════════════════════════════════════════════
# MAIN render()
# ══════════════════════════════════════════════════════════════════════════════
def render() -> None:
    """Main entry point — called from dashboard.py routing."""
    # Ensure tables initialised
    if _ENGINE:
        try:
            init_directory()
        except Exception:
            pass

    # KPI bar
    _render_kpi_bar()
    st.markdown("---")

    # Search + filters
    sf = _render_search_filters()
    query   = sf.get("query", "")
    filters = sf.get("filters", {})

    # Reset page on new query/filter
    if "dir_last_query" not in st.session_state:
        st.session_state["dir_last_query"] = ""
    if st.session_state["dir_last_query"] != query:
        st.session_state["dir_last_query"] = query
        st.session_state["dir_page"] = 0

    st.markdown("---")

    # Tabs
    tabs = st.tabs([
        "Directory",
        "India Map",
        "Coverage Report",
        "Source Registry",
        "Bug Tracker",
    ])

    with tabs[0]:
        _render_directory_tab(query, filters)

    with tabs[1]:
        _render_map_tab()

    with tabs[2]:
        _render_coverage_tab()

    with tabs[3]:
        _render_source_registry_tab()

    with tabs[4]:
        _render_bug_tracker_tab()

    # PDF export bar
    if _PDF_BAR:
        report  = get_coverage_report() if _ENGINE else {}
        p1_pct  = report.get("phase1", {}).get("pct", 0.0) if report else 0.0
        total   = report.get("grand_total", 0) if report else 0
        render_export_bar(
            "India Procurement Directory",
            content_fn=_pdf_content,
            kpis=[
                ("Total Entries",   str(total),    ""),
                ("Phase 1 Cover%",  f"{p1_pct:.1f}%", ""),
            ],
            orientation="landscape",
        )
