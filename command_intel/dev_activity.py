"""
PPS Anantams Logistics AI
Development & System Activity Tab v1.0
=======================================
Reads all 4 log files maintained by api_manager.py and renders a
comprehensive, filterable audit dashboard.

Sections:
  1. Live System Status (metrics)
  2. Recent Development Activity (DEV_LOG)
  3. API Additions & Removals (DEV_LOG filtered)
  4. System Updates & Model Changes (CHANGE_LOG)
  5. Deployment Logs (DEV_LOG filtered)
  6. Pending Fixes (ERROR_LOG — status Open)
  7. Auto-Healing Actions Taken (CHANGE_LOG — trigger Auto)
  8. Health Pulse (HEALTH_LOG — last N)
  9. Manual Change Request (write to CHANGE_LOG from UI)

All timestamps displayed in IST (DD-MM-YYYY HH:MM:SS).
"""

import streamlit as st
import pandas as pd
import datetime

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(x): pass

try:
    from api_manager import (
        get_error_log, get_change_log, get_dev_log, get_health_log,
        record_manual_change, run_all_health_checks, ts_str,
    )
    AM_AVAILABLE = True
except ImportError:
    AM_AVAILABLE = False
    def get_error_log(n=100): return []
    def get_change_log(n=200): return []
    def get_dev_log(n=100): return []
    def get_health_log(n=200): return []
    def ts_str(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR MAP
# ─────────────────────────────────────────────────────────────────────────────

SEVERITY_COLOR = {
    "P0": "#dc2626",   # red-600
    "P1": "#ea580c",   # orange-600
    "P2": "#ca8a04",   # yellow-600
    "P3": "#16a34a",   # green-600
}

STATUS_ICON = {
    "Completed": "✅",
    "Active": "🟢",
    "Deployed": "🚀",
    "Running": "⚙️",
    "Pending": "🕐",
    "Open": "🔴",
    "Auto-Fixed": "🔧",
    "Suppressed": "⚫",
    "FAIL": "❌",
    "OK": "🟢",
    "Alert": "🚨",
}

ACTIVITY_COLOR = {
    "API Added": "#22c55e",
    "API Removed": "#ef4444",
    "Model Change": "#3b82f6",
    "Health Check": "#8b5cf6",
    "Auto-Repair": "#f59e0b",
    "System Start": "#06b6d4",
    "Alert": "#dc2626",
    "Deployment": "#10b981",
    "Bug Fix": "#6366f1",
    "Manual Log": "#64748b",
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _df(records: list, cols: list = None) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if cols:
        existing = [c for c in cols if c in df.columns]
        df = df[existing]
    return df


def _color_status(val):
    color = SEVERITY_COLOR.get(val, "#475569")
    return f"color:{color}; font-weight:bold"


def _section_header(icon: str, title: str, count: int = None, color: str = "#3b82f6"):
    count_badge = f' <span style="background:{color};color:#fff;border-radius:9px;padding:1px 8px;font-size:0.8rem">{count}</span>' if count is not None else ""
    st.markdown(
        f'<div style="border-left:4px solid {color};padding:6px 12px;margin:14px 0 8px 0;'
        f'background:linear-gradient(90deg,{color}18,transparent)">'
        f'<span style="font-size:1.05rem;font-weight:700">{icon} {title}</span>{count_badge}</div>',
        unsafe_allow_html=True,
    )


def _stat_card(col, label: str, value, delta: str = "", color: str = "#3b82f6"):
    col.markdown(
        f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);border-left:4px solid {color};'
        f'border-radius:10px;padding:14px 16px;text-align:center;">'
        f'<div style="color:#94a3b8;font-size:0.78rem">{label}</div>'
        f'<div style="color:#f8fafc;font-size:1.6rem;font-weight:800">{value}</div>'
        f'<div style="color:{color};font-size:0.78rem">{delta}</div></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS (rendered inside the tab, not global sidebar)
# ─────────────────────────────────────────────────────────────────────────────

def _build_filters(dev_log: list, err_log: list, change_log: list):
    with st.expander("🔍 Filters & Controls", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)

        # Date range
        today = datetime.date.today()
        from_date = fc1.date_input("From Date", value=today - datetime.timedelta(days=30))
        to_date   = fc2.date_input("To Date",   value=today)

        # Activity types (from dev log)
        all_types = sorted({r.get("activity_type", "") for r in dev_log} | {"All"})
        sel_type  = fc3.selectbox("Activity Type", ["All"] + [t for t in all_types if t != "All"])

        # Department
        all_depts = sorted({r.get("department", "") for r in dev_log} | {"All"})
        sel_dept  = fc4.selectbox("Department", ["All"] + [d for d in all_depts if d != "All"])

        fc5, fc6 = st.columns(2)
        # Severity (error log)
        sel_sev   = fc5.selectbox("Severity (Errors)", ["All", "P0", "P1", "P2", "P3"])
        # Auto vs Manual (change log)
        sel_trig  = fc6.selectbox("Change Trigger", ["All", "Auto", "Manual", "Development"])

    return from_date, to_date, sel_type, sel_dept, sel_sev, sel_trig


def _filter_by_date(records: list, from_date, to_date) -> list:
    """Filter records by datetime_ist field (format: DD-MM-YYYY HH:MM:SS IST)."""
    out = []
    for r in records:
        ts = r.get("datetime_ist", "")
        try:
            d = datetime.datetime.strptime(ts[:10], "%Y-%m-%d").date()
            if from_date <= d <= to_date:
                out.append(r)
        except Exception:
            out.append(r)  # include if unparseable
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SECTION RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _render_live_status(dev_log, err_log, health_log, change_log):
    """Section 1 — Live System Status KPI cards."""
    _section_header("⚡", "Live System Status", color="#06b6d4")

    open_errors   = [e for e in err_log   if e.get("status") == "Open"]
    auto_fixes    = [e for e in err_log   if e.get("status") == "Auto-Fixed"]
    health_ok     = [h for h in health_log if h.get("status") == "OK"]
    health_fail   = [h for h in health_log if h.get("status") == "FAIL"]
    total_health  = len(health_ok) + len(health_fail)
    health_pct    = round(len(health_ok) / total_health * 100) if total_health > 0 else 0
    pending_fixes = [e for e in err_log if e.get("status") in ("Open", "Pending")]
    api_adds      = [d for d in dev_log  if d.get("activity_type") == "API Added"]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _stat_card(c1, "API Health",      f"{health_pct}%",          "Last health run",       "#22c55e")
    _stat_card(c2, "Open Errors",     len(open_errors),           "Require manual fix",    "#ef4444")
    _stat_card(c3, "Auto-Healed",     len(auto_fixes),            "Auto-repair successful","#f59e0b")
    _stat_card(c4, "Pending Fixes",   len(pending_fixes),         "In error log",          "#8b5cf6")
    _stat_card(c5, "APIs Registered", len(api_adds) or "25",      "In registry",           "#3b82f6")
    _stat_card(c6, "Change Events",   len(change_log),            "Audit records",         "#10b981")

    st.markdown(
        f'<div style="text-align:right;color:#64748b;font-size:0.78rem;margin-top:4px">'
        f'Last refresh: {ts_str()}</div>', unsafe_allow_html=True
    )


def _render_dev_activity(dev_log, filters):
    """Section 2 — Recent Development Activity."""
    from_date, to_date, sel_type, sel_dept, *_ = filters

    filtered = _filter_by_date(dev_log, from_date, to_date)
    if sel_type != "All":
        filtered = [r for r in filtered if r.get("activity_type") == sel_type]
    if sel_dept != "All":
        filtered = [r for r in filtered if r.get("department") == sel_dept]

    _section_header("🛠️", "Recent Development Activity", count=len(filtered), color="#3b82f6")

    if not filtered:
        st.info("No development activity records match the current filters.")
        return

    for rec in filtered[:50]:
        atype   = rec.get("activity_type", "Unknown")
        color   = ACTIVITY_COLOR.get(atype, "#64748b")
        status  = rec.get("status", "")
        icon    = STATUS_ICON.get(status, "📌")
        ts      = rec.get("datetime_ist", "")
        comp    = rec.get("component", "")

        st.markdown(
            f'<div style="border-left:3px solid {color};padding:8px 12px;margin-bottom:6px;'
            f'background:#0f172a;border-radius:0 8px 8px 0;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span style="color:{color};font-weight:700;font-size:0.85rem">[{atype}]</span>'
            f'<span style="color:#94a3b8;font-size:0.75rem">{ts}</span></div>'
            f'<div style="color:#f8fafc;font-size:0.92rem;margin:2px 0">{icon} <b>{rec.get("title","")}</b></div>'
            f'<div style="color:#94a3b8;font-size:0.82rem">{rec.get("description","")}'
            f'{"  •  Comp: "+comp if comp else ""}</div></div>',
            unsafe_allow_html=True,
        )


def _render_api_changes(dev_log, filters):
    """Section 3 — API Additions & Removals."""
    from_date, to_date, *_ = filters
    filtered = _filter_by_date(dev_log, from_date, to_date)
    api_recs  = [r for r in filtered if r.get("activity_type") in ("API Added", "API Removed")]

    _section_header("🔌", "API Additions & Removals", count=len(api_recs), color="#22c55e")

    if not api_recs:
        st.info("No API addition/removal events in the selected period.")
        return

    df = _df(api_recs, ["datetime_ist", "activity_type", "title", "description", "component", "status"])
    if not df.empty:
        def color_api_type(val):
            if val == "API Added":   return "color:#22c55e;font-weight:bold"
            if val == "API Removed": return "color:#ef4444;font-weight:bold"
            return ""
        styled = df.style.applymap(color_api_type, subset=["activity_type"])
        st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_system_updates(change_log, filters):
    """Section 4 — System Updates & Model Changes."""
    from_date, to_date, sel_type, sel_dept, _, sel_trig = filters
    filtered = _filter_by_date(change_log, from_date, to_date)
    if sel_trig != "All":
        filtered = [r for r in filtered if r.get("trigger") == sel_trig]

    _section_header("🔄", "System Updates & Model Changes (Audit Trail)", count=len(filtered), color="#8b5cf6")

    if not filtered:
        st.info("No change log records match the current filters.")
        return

    df = _df(filtered, [
        "datetime_ist", "component", "what_changed",
        "old_value", "new_value", "reason", "trigger",
        "affected_tab", "affected_api", "user_id",
    ])
    if not df.empty:
        def color_trigger(val):
            if val == "Auto":        return "color:#f59e0b;font-weight:bold"
            if val == "Manual":      return "color:#3b82f6;font-weight:bold"
            if val == "Development": return "color:#22c55e;font-weight:bold"
            return ""
        styled = df.style.applymap(color_trigger, subset=["trigger"])
        st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_pending_fixes(err_log, filters):
    """Section 5 — Pending Fixes (Open Errors)."""
    from_date, to_date, _, __, sel_sev, ___ = filters
    filtered = _filter_by_date(err_log, from_date, to_date)
    filtered = [r for r in filtered if r.get("status") in ("Open", "Pending")]
    if sel_sev != "All":
        filtered = [r for r in filtered if r.get("severity") == sel_sev]

    _section_header("🚨", "Pending Fixes — Open Error Backlog", count=len(filtered), color="#ef4444")

    if not filtered:
        st.success("✅ No open errors in this period. System is healthy.")
        return

    # P0 critical banner
    p0 = [r for r in filtered if r.get("severity") == "P0"]
    if p0:
        st.error(f"🔴 CRITICAL: {len(p0)} P0 (production-blocking) errors require immediate attention!")

    df = _df(filtered, [
        "datetime_ist", "severity", "api_id", "component",
        "error_type", "message", "root_cause", "resolution_notes", "manual_required",
    ])
    if not df.empty:
        styled = df.style.applymap(_color_status, subset=["severity"])
        st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_auto_healing(err_log, change_log, filters):
    """Section 6 — Auto-Healing Actions Taken."""
    from_date, to_date, *_ = filters
    err_fixed    = _filter_by_date(err_log, from_date, to_date)
    err_fixed    = [r for r in err_fixed if r.get("auto_fixed") is True]
    change_auto  = _filter_by_date(change_log, from_date, to_date)
    change_auto  = [r for r in change_auto if r.get("trigger") == "Auto"]

    _section_header("🔧", "Auto-Healing Actions", count=len(err_fixed)+len(change_auto), color="#f59e0b")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Auto-Fixed Errors**")
        if not err_fixed:
            st.info("No auto-fixed errors in this period.")
        else:
            df = _df(err_fixed, ["datetime_ist", "api_id", "error_type", "resolution_notes"])
            st.dataframe(df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Auto Repair / Fallback Switches**")
        if not change_auto:
            st.info("No automatic fallback or repair events in this period.")
        else:
            df = _df(change_auto, ["datetime_ist", "component", "what_changed", "new_value", "reason"])
            st.dataframe(df, use_container_width=True, hide_index=True)


def _render_health_pulse(health_log, filters):
    """Section 7 — Health Pulse."""
    from_date, to_date, *_ = filters
    filtered = _filter_by_date(health_log, from_date, to_date)

    _section_header("💓", "Health Pulse — API Response Monitor", count=len(filtered), color="#06b6d4")

    if not filtered:
        st.info("No health log records in this period. Run a health check first.")
        return

    df = _df(filtered, ["datetime_ist", "api_id", "status", "latency_ms", "http_code", "error_detail", "action_taken"])

    if df.empty:
        return

    # Summary metrics
    ok_count   = len([r for r in filtered if r.get("status") == "OK"])
    fail_count = len(filtered) - ok_count
    avg_lat    = int(sum(r.get("latency_ms", 0) for r in filtered) / len(filtered)) if filtered else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Successful Pings", ok_count)
    m2.metric("Failed Pings",     fail_count)
    m3.metric("Avg Latency",      f"{avg_lat} ms")

    def color_health_status(val):
        if val == "OK":   return "color:#22c55e;font-weight:bold"
        if val == "FAIL": return "color:#ef4444;font-weight:bold"
        return ""

    if "status" in df.columns:
        styled = df.style.applymap(color_health_status, subset=["status"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def _render_manual_log():
    """Section 8 — Manual Change Request Form."""
    _section_header("📝", "Manual Change Request", color="#64748b")

    st.caption("Log a manual change, configuration update, or note directly to the audit trail.")

    with st.form("manual_change_form"):
        f1, f2 = st.columns(2)
        component = f1.text_input("Component / Module", placeholder="e.g. feasibility_engine.py")
        tab       = f2.text_input("Affected Tab",       placeholder="e.g. Feasibility Calculator")
        what      = st.text_input("What was changed?",  placeholder="e.g. Transport rate updated")
        f3, f4    = st.columns(2)
        old_val   = f3.text_input("Old Value",          placeholder="e.g. ₹5.5/km")
        new_val   = f4.text_input("New Value",          placeholder="e.g. ₹6.0/km")
        reason    = st.text_area("Reason / Notes",      placeholder="Why was this changed? Who approved?")
        user      = st.text_input("Your Name / ID",     placeholder="e.g. Ramesh Kumar")
        submitted = st.form_submit_button("📤 Submit to Audit Trail")

    if submitted:
        if AM_AVAILABLE and component and what:
            record_manual_change(
                component=component, what=what, old_val=old_val or "Not specified",
                new_val=new_val or "Not specified", reason=reason or "No reason given",
                tab=tab or "Unspecified", user=user or "Dashboard User",
            )
            st.success(f"✅ Change logged to audit trail at {ts_str()}")
        elif not component or not what:
            st.warning("Please fill in at least 'Component' and 'What was changed'.")
        else:
            st.info("api_manager not available — log entry cannot be saved in this session.")


def _render_run_health_check():
    """Inline health check runner."""
    _section_header("🏃", "Run System Health Check Now", color="#10b981")

    st.caption("Triggers a live ping to all 25 registered APIs and updates the health log.")

    col_btn, col_res = st.columns([1, 3])
    with col_btn:
        run_btn = st.button("🚀 Run Full Health Check", type="primary")

    with col_res:
        if run_btn:
            if AM_AVAILABLE:
                with st.spinner("Pinging all APIs... this may take 20–40 seconds."):
                    summary, results = run_all_health_checks(force=True)
                st.success(
                    f"✅ Health check complete — {summary['healthy']}/{summary['total']} APIs healthy "
                    f"({summary['health_pct']}%) at {summary['timestamp']}"
                )
                if summary["failed"] > 0:
                    failed_apis = [wid for wid, r in results.items() if not r["ok"]]
                    st.warning(f"⚠️ Failed APIs: {', '.join(failed_apis)}")
            else:
                st.warning("api_manager module not available. Cannot run health check.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render():
    display_badge("live")

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
padding:20px 24px;border-radius:12px;margin-bottom:20px;
border-left:5px solid #3b82f6;">
<div style="font-size:1.5rem;font-weight:900;color:#f8fafc;">
⚙️ Development & System Activity
</div>
<div style="color:#94a3b8;font-size:0.9rem;margin-top:4px">
Full audit trail of API changes, auto-repairs, errors, deployments, and system events.
All timestamps in IST (Asia/Kolkata). Data persists across sessions in JSON log files.
</div>
</div>
""", unsafe_allow_html=True)

    # ── Load all logs ────────────────────────────────────────────────────────
    dev_log    = get_dev_log(500)
    err_log    = get_error_log(1000)
    change_log = get_change_log(2000)
    health_log = get_health_log(2000)

    # ── Filters ──────────────────────────────────────────────────────────────
    filters = _build_filters(dev_log, err_log, change_log)

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
        "⚡ Status",
        "🛠️ Dev Activity",
        "🔌 API Changes",
        "🔄 System Updates",
        "🚨 Pending Fixes",
        "🔧 Auto-Healing",
        "💓 Health Pulse",
        "📝 Log Change",
        "🏃 Run Health Check",
    ])

    with t1:
        _render_live_status(dev_log, err_log, health_log, change_log)

    with t2:
        _render_dev_activity(dev_log, filters)

    with t3:
        _render_api_changes(dev_log, filters)

    with t4:
        _render_system_updates(change_log, filters)

    with t5:
        _render_pending_fixes(err_log, filters)

    with t6:
        _render_auto_healing(err_log, change_log, filters)

    with t7:
        _render_health_pulse(health_log, filters)

    with t8:
        _render_manual_log()

    with t9:
        _render_run_health_check()

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="color:#475569;font-size:0.78rem;text-align:center">'
        'PPS Anantam Logistics • API Intelligence System v3.2 • '
        'Logs stored in: api_error_log.json | api_change_log.json | api_dev_log.json | api_health_log.json'
        '</div>',
        unsafe_allow_html=True,
    )
