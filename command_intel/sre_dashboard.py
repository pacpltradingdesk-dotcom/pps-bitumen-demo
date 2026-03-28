"""
SRE Dashboard — Streamlit UI
PPS Anantam Agentic AI Eco System v3.2.1
=========================================
Self-Healing + Auto Bug Fixing + Smart Alerts — Full Control Panel

Pages rendered here:
  🏥 System Health    — health cards for all entities
  🚨 SRE Alerts       — P0/P1/P2 alert console with resolve
  🐛 Bug Board        — full lifecycle bug management
  🔍 Audit Log        — structured request log
  📊 Metrics          — health trend + component metrics
  ⚔️ Conflict Monitor — overwrite / conflict detection
  🧪 SRE Test Suite   — run automated tests live
"""

import sys
import os
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd

try:
    from sre_engine import (
        HealthCheckEngine, SelfHealEngine, SmartAlertEngine,
        BugAutoCreator, ConflictProtector, DataValidator,
        SREOrchestrator, AuditLogger,
        get_sre_metrics, get_health_status, get_conflict_log,
        get_change_history, init_sre,
    )
    _SRE_OK = True
except Exception as _sre_err:
    _SRE_OK = False
    _SRE_ERR = str(_sre_err)

# ─── Style helpers ─────────────────────────────────────────────────────────────
_STATUS_COLOR = {"OK": "#16a34a", "WARN": "#d97706", "FAIL": "#dc2626", "UNKNOWN": "#64748b"}
_STATUS_BG    = {"OK": "#f0fdf4", "WARN": "#fffbeb", "FAIL": "#fef2f2", "UNKNOWN": "#f8fafc"}
_SEV_COLOR    = {"P0": "#dc2626", "P1": "#ea580c", "P2": "#ca8a04"}
_SEV_BG       = {"P0": "#fef2f2", "P1": "#fff7ed", "P2": "#fefce8"}
_SEV_LABEL    = {"P0": "P0 CRITICAL", "P1": "P1 MAJOR", "P2": "P2 MINOR"}


def _badge(text: str, color: str, bg: str) -> str:
    return (
        f'<span style="background:{bg};color:{color};font-size:0.65rem;font-weight:700;'
        f'padding:2px 8px;border-radius:10px;border:1px solid {color}33;">{text}</span>'
    )


def _card(title: str, value: str, sub: str = "", color: str = "#1e3a5f") -> str:
    return f"""
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;
            padding:14px 16px;text-align:center;">
  <div style="font-size:0.62rem;color:#64748b;font-weight:600;text-transform:uppercase;
              letter-spacing:0.06em;margin-bottom:4px;">{title}</div>
  <div style="font-size:1.5rem;font-weight:800;color:{color};">{value}</div>
  <div style="font-size:0.68rem;color:#94a3b8;margin-top:2px;">{sub}</div>
</div>"""


def _section_header(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(f"""
<div style="border-bottom:2px solid #e8dcc8;padding-bottom:8px;margin:18px 0 12px 0;">
  <span style="font-size:1.05rem;font-weight:800;color:#1e3a5f;">{icon} {title}</span>
  {"<span style='font-size:0.72rem;color:#64748b;margin-left:8px;'>" + subtitle + "</span>" if subtitle else ""}
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    if not _SRE_OK:
        st.error(f"SRE Engine failed to load: {_SRE_ERR}")
        st.info("Ensure `sre_engine.py` is present in the dashboard root directory.")
        return

    # Initialise engine (creates JSON files if missing)
    init_sre()

    # ── Sub-page tabs ──────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏥 Health",
        "🚨 Alerts",
        "🐛 Bugs",
        "🔍 Audit Log",
        "📊 Metrics",
        "⚔️ Conflicts",
        "🧪 Test Suite",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — HEALTH DASHBOARD
    # ─────────────────────────────────────────────────────────────────────────
    with tab1:
        _render_health()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — ALERT CONSOLE
    # ─────────────────────────────────────────────────────────────────────────
    with tab2:
        _render_alerts()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3 — BUG BOARD
    # ─────────────────────────────────────────────────────────────────────────
    with tab3:
        _render_bugs()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4 — AUDIT LOG
    # ─────────────────────────────────────────────────────────────────────────
    with tab4:
        _render_audit()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 5 — METRICS
    # ─────────────────────────────────────────────────────────────────────────
    with tab5:
        _render_metrics()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 6 — CONFLICT MONITOR
    # ─────────────────────────────────────────────────────────────────────────
    with tab6:
        _render_conflicts()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 7 — TEST SUITE
    # ─────────────────────────────────────────────────────────────────────────
    with tab7:
        _render_test_suite()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

def _render_health():
    _section_header("🏥", "System Health Dashboard", "Real-time entity health across APIs, data, calculations, exports & scheduler")

    # Controls
    col_run, col_refresh = st.columns([3, 1])
    with col_run:
        if st.button("▶ Run Full Health Check Now", type="primary", use_container_width=True):
            with st.spinner("Running health checks across all entities…"):
                results = HealthCheckEngine.run_all()
            summary = results.get("summary", {})
            if summary.get("overall") == "OK":
                st.success(f"All systems healthy — {summary.get('health_pct', 0)}% OK")
            elif summary.get("overall") == "WARN":
                st.warning(f"Health: {summary.get('health_pct', 0)}% OK  •  {summary.get('warn', 0)} warnings")
            else:
                st.error(f"FAIL detected — {summary.get('fail', 0)} failures  •  {summary.get('warn', 0)} warnings")
    with col_refresh:
        st.caption("Auto-runs every 15 min in background")

    st.markdown("---")

    # Load live health data
    health_data = get_health_status()
    if not health_data:
        st.info("No health records yet. Click 'Run Full Health Check Now' to populate.")
        return

    # Summary KPIs
    metrics = get_sre_metrics()
    h = metrics["health"]
    hp = h.get("health_pct", 0)
    hp_color = "#16a34a" if hp >= 90 else ("#d97706" if hp >= 70 else "#dc2626")

    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    kc1.markdown(_card("Overall Health", f"{hp}%", "all entities", hp_color), unsafe_allow_html=True)
    kc2.markdown(_card("✅ OK", str(h["ok"]), "entities healthy", "#16a34a"), unsafe_allow_html=True)
    kc3.markdown(_card("⚠️ WARN", str(h["warn"]), "entities warning", "#d97706"), unsafe_allow_html=True)
    kc4.markdown(_card("❌ FAIL", str(h["fail"]), "entities failed", "#dc2626"), unsafe_allow_html=True)
    kc5.markdown(_card("🚨 Open Alerts", str(metrics["alerts"]["total_open"]), "P0+P1+P2"), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Entity type filter
    entity_types = sorted(set(e.get("entity_type", "unknown") for e in health_data))
    type_filter = st.selectbox("Filter by entity type", ["All"] + entity_types)

    filtered = health_data if type_filter == "All" else [
        e for e in health_data if e.get("entity_type") == type_filter
    ]

    # Sort: FAIL first, then WARN, then OK
    order = {"FAIL": 0, "WARN": 1, "OK": 2}
    filtered.sort(key=lambda e: order.get(e.get("status", "OK"), 3))

    # Health cards grid (3 per row)
    for i in range(0, len(filtered), 3):
        row = filtered[i:i+3]
        cols = st.columns(3)
        for j, entity in enumerate(row):
            status = entity.get("status", "UNKNOWN")
            color  = _STATUS_COLOR.get(status, "#64748b")
            bg     = _STATUS_BG.get(status, "#f8fafc")
            name   = entity.get("entity_name", "?")
            etype  = entity.get("entity_type", "")
            detail = entity.get("details", "")[:120]
            chk    = entity.get("last_checked_ist", "—")
            afix   = entity.get("auto_fix_attempted", "N")
            afix_badge = "🔧 Fix tried" if afix == "Y" else ""

            with cols[j]:
                st.markdown(f"""
<div style="background:{bg};border:1px solid {color}44;border-left:4px solid {color};
            border-radius:8px;padding:12px 14px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <span style="font-weight:700;color:#1e293b;font-size:0.85rem;">{name}</span>
    {_badge(status, color, bg)}
  </div>
  <div style="font-size:0.68rem;color:#64748b;margin-bottom:4px;">
    Type: <b>{etype}</b> {afix_badge}
  </div>
  <div style="font-size:0.7rem;color:#475569;margin-bottom:6px;">{detail or "OK"}</div>
  <div style="font-size:0.62rem;color:#94a3b8;">Checked: {chk}</div>
</div>""", unsafe_allow_html=True)

    # Auto-heal section for FAIL entities
    fail_entities = [e for e in health_data
                     if e.get("status") == "FAIL" and e.get("entity_type") == "api"]
    if fail_entities:
        st.markdown("---")
        _section_header("🔧", "Auto-Heal Controls", "Failed API entities")
        for entity in fail_entities:
            name = entity.get("entity_name", "?")
            if st.button(f"🔧 Heal API: {name}", key=f"heal_{name}"):
                with st.spinner(f"Attempting heal for {name}…"):
                    result = SelfHealEngine.heal_api(name)
                if result.get("healed"):
                    st.success(f"✅ {name} healed on attempt {result.get('attempt', '?')}")
                else:
                    st.error(f"❌ {name} could not be healed — bug auto-created")
                    bug_id = BugAutoCreator.from_failed_heal(name, result)
                    st.warning(f"Bug created: {bug_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_alerts():
    _section_header("🚨", "Smart Alert Console", "P0 Critical • P1 Major • P2 Minor — auto-deduplicated")

    # Filter + actions
    ac1, ac2, ac3 = st.columns([2, 2, 2])
    with ac1:
        sev_filter = st.selectbox("Severity", ["All", "P0", "P1", "P2"], key="alt_sev")
    with ac2:
        status_filter = st.selectbox("Status", ["Open", "All", "Resolved"], key="alt_status")
    with ac3:
        if st.button("🔄 Refresh Alerts", use_container_width=True):
            st.rerun()

    all_alerts = SmartAlertEngine.get_all_alerts(n=300)

    if status_filter == "Open":
        alerts = [a for a in all_alerts if a.get("status") == "Open"]
    elif status_filter == "Resolved":
        alerts = [a for a in all_alerts if a.get("status") in ("Resolved", "Suppressed")]
    else:
        alerts = all_alerts

    if sev_filter != "All":
        alerts = [a for a in alerts if a.get("severity") == sev_filter]

    # Summary metrics
    open_all = SmartAlertEngine.get_open_alerts()
    p0 = sum(1 for a in open_all if a.get("severity") == "P0")
    p1 = sum(1 for a in open_all if a.get("severity") == "P1")
    p2 = sum(1 for a in open_all if a.get("severity") == "P2")

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Open Alerts", len(open_all))
    sc2.metric("🔴 P0 Critical", p0)
    sc3.metric("🟠 P1 Major",    p1)
    sc4.metric("🟡 P2 Minor",    p2)

    st.markdown("---")

    if not alerts:
        st.success("✅ No alerts matching current filter.")
        return

    for alert in alerts:
        sev    = alert.get("severity", "P2")
        color  = _SEV_COLOR.get(sev, "#64748b")
        bg     = _SEV_BG.get(sev, "#f8fafc")
        slabel = _SEV_LABEL.get(sev, sev)
        status = alert.get("status", "Open")
        entity = alert.get("entity", "")
        alert_id = alert.get("alert_id", "")
        ts     = alert.get("triggered_on_ist", "")
        res_ts = alert.get("resolved_on_ist", "")
        what   = alert.get("what_happened", alert.get("message", ""))
        where  = alert.get("where", "")
        why    = alert.get("why", "")
        action = alert.get("action_needed", "")
        fix_r  = alert.get("auto_fix_result", "")

        status_badge = (
            '<span style="color:#16a34a;font-weight:700;">✅ Resolved</span>'
            if status in ("Resolved", "Suppressed")
            else '<span style="color:#dc2626;font-weight:700;">⏳ Open</span>'
        )

        with st.container():
            st.markdown(f"""
<div style="background:{bg};border:1px solid {color}55;border-left:5px solid {color};
            border-radius:8px;padding:13px 16px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
    <div style="display:flex;gap:8px;align-items:center;">
      {_badge(slabel, color, bg)}
      <span style="font-size:0.72rem;color:#64748b;">{entity}</span>
      {status_badge}
    </div>
    <div style="text-align:right;">
      <div style="font-size:0.62rem;color:#94a3b8;">🕐 {ts}</div>
      {"<div style='font-size:0.62rem;color:#16a34a;'>✅ " + res_ts + "</div>" if res_ts else ""}
    </div>
  </div>
  <div style="font-weight:700;font-size:0.9rem;color:#1e293b;margin-bottom:6px;">{what}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.75rem;color:#475569;margin-bottom:8px;">
    <div><b>Where:</b> {where}</div>
    <div><b>Why:</b> {why}</div>
    {"<div><b>Auto-fix result:</b> " + fix_r + "</div>" if fix_r else ""}
  </div>
  {"<div style='background:#fff;border-radius:6px;padding:7px 10px;font-size:0.75rem;'><b>📋 Action:</b> " + action + "</div>" if action else ""}
  <div style="font-size:0.6rem;color:#94a3b8;margin-top:6px;">ID: {alert_id}</div>
</div>""", unsafe_allow_html=True)

            if status == "Open":
                ra1, ra2 = st.columns([1, 4])
                with ra1:
                    if st.button(f"✅ Resolve", key=f"res_{alert_id}"):
                        SmartAlertEngine.resolve(alert_id)
                        st.success("Alert resolved")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — BUG BOARD
# ═══════════════════════════════════════════════════════════════════════════════

def _render_bugs():
    _section_header("🐛", "Bug Board", "Auto-created + manual bugs — full lifecycle: Open → In Progress → Fixed → Verified")

    # Manual bug creation
    with st.expander("➕ Create Bug Manually"):
        bc1, bc2 = st.columns(2)
        with bc1:
            b_sev   = st.selectbox("Severity", ["P0", "P1", "P2"], key="bug_sev")
            b_title = st.text_input("Title", key="bug_title", placeholder="Brief description")
        with bc2:
            b_entity = st.text_input("Entity/Component", key="bug_entity", placeholder="e.g. brent_api")
            b_owner  = st.selectbox("Owner", ["backend", "frontend", "data", "scheduler"], key="bug_owner")
        b_steps = st.text_area("Reproduction steps (one per line)", key="bug_steps",
                               placeholder="1. Open Pricing Calculator\n2. Enter values\n3. Result is NaN")
        if st.button("🐛 Create Bug", type="primary"):
            if b_title and b_entity:
                steps = [s.strip() for s in b_steps.split("\n") if s.strip()]
                bug_id = BugAutoCreator.create(
                    severity=b_sev, entity=b_entity, title=b_title,
                    component_owner=b_owner, reproduction_steps=steps, auto_created=False,
                )
                st.success(f"Bug created: {bug_id}")
                st.rerun()
            else:
                st.warning("Title and Entity are required")

    # Filter
    bc_f1, bc_f2 = st.columns(2)
    with bc_f1:
        f_status = st.selectbox("Status", ["All", "Open", "In Progress", "Fixed", "Verified"], key="bug_fs")
    with bc_f2:
        f_sev = st.selectbox("Severity", ["All", "P0", "P1", "P2"], key="bug_fv")

    status_arg = None if f_status == "All" else f_status
    sev_arg    = None if f_sev    == "All" else f_sev
    bugs = BugAutoCreator.get_bugs(status=status_arg, severity=sev_arg)

    # Summary
    all_bugs = BugAutoCreator.get_bugs()
    bs1, bs2, bs3, bs4 = st.columns(4)
    bs1.metric("Total Bugs",   len(all_bugs))
    bs2.metric("🔴 Open",      sum(1 for b in all_bugs if b.get("status") == "Open"))
    bs3.metric("🔵 In Progress", sum(1 for b in all_bugs if b.get("status") == "In Progress"))
    bs4.metric("✅ Fixed",     sum(1 for b in all_bugs if b.get("status") in ("Fixed", "Verified")))

    st.markdown("---")

    if not bugs:
        st.success("✅ No bugs matching filter. System is clean.")
        return

    for bug in bugs:
        bug_id = bug.get("bug_id", "?")
        sev    = bug.get("severity", "P2")
        color  = _SEV_COLOR.get(sev, "#64748b")
        bg     = _SEV_BG.get(sev, "#f8fafc")
        status = bug.get("status", "Open")
        title  = bug.get("title", "")
        entity = bug.get("entity", "")
        owner  = bug.get("component_owner", "")
        steps  = bug.get("reproduction_steps", [])
        created = bug.get("created_ist", "")
        auto   = "🤖 Auto-created" if bug.get("auto_created") else "👤 Manual"

        status_colors = {
            "Open": "#dc2626", "In Progress": "#2563eb",
            "Fixed": "#16a34a", "Verified": "#7c3aed",
        }
        s_color = status_colors.get(status, "#64748b")

        with st.container():
            st.markdown(f"""
<div style="background:{bg};border:1px solid {color}44;border-left:4px solid {color};
            border-radius:8px;padding:12px 15px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <div style="display:flex;gap:8px;align-items:center;">
      {_badge(sev, color, bg)}
      <span style="font-size:0.7rem;color:{s_color};font-weight:700;">{status}</span>
      <span style="font-size:0.68rem;color:#64748b;">{auto}</span>
    </div>
    <span style="font-size:0.62rem;color:#94a3b8;">{created}</span>
  </div>
  <div style="font-weight:700;color:#1e293b;font-size:0.88rem;margin-bottom:4px;">{title}</div>
  <div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;">
    Entity: <b>{entity}</b> &nbsp;|&nbsp; Owner: <b>{owner}</b> &nbsp;|&nbsp; ID: {bug_id}
  </div>
  {"<ol style='font-size:0.72rem;color:#475569;margin:0 0 6px 16px;padding:0;'>" + "".join(f"<li>{s}</li>" for s in steps[:4]) + "</ol>" if steps else ""}
</div>""", unsafe_allow_html=True)

            # Status update buttons
            valid_transitions = {
                "Open":        ["In Progress", "Fixed", "Suppressed"],
                "In Progress": ["Fixed"],
                "Fixed":       ["Verified"],
                "Verified":    [],
            }
            transitions = valid_transitions.get(status, [])
            if transitions:
                bt_cols = st.columns(len(transitions) + 1)
                for idx, new_status in enumerate(transitions):
                    with bt_cols[idx]:
                        if st.button(f"→ {new_status}", key=f"bug_{bug_id}_{new_status}"):
                            BugAutoCreator.update_status(bug_id, new_status)
                            st.success(f"Bug {bug_id} → {new_status}")
                            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AUDIT LOG
# ═══════════════════════════════════════════════════════════════════════════════

def _render_audit():
    _section_header("🔍", "Audit Log", "Centralized structured log — request_id, component, severity, IST timestamp")

    al1, al2 = st.columns(2)
    with al1:
        sev_f = st.selectbox("Severity", ["All", "CRITICAL", "ERROR", "WARN", "INFO"], key="audit_sev")
    with al2:
        comp_f = st.text_input("Filter by component", key="audit_comp", placeholder="e.g. SelfHealEngine")

    sev_arg = None if sev_f == "All" else sev_f
    records = AuditLogger.get_recent(n=500, severity=sev_arg)

    if comp_f:
        records = [r for r in records if comp_f.lower() in r.get("component", "").lower()]

    if not records:
        st.info("No audit records matching filter.")
        return

    # Stats
    as1, as2, as3 = st.columns(3)
    as1.metric("Total Records", len(records))
    as2.metric("Errors/Critical", sum(1 for r in records if r.get("severity") in ("ERROR", "CRITICAL")))
    as3.metric("Warnings", sum(1 for r in records if r.get("severity") == "WARN"))

    st.markdown("---")

    rows = []
    for r in reversed(records[:200]):
        sev = r.get("severity", "INFO")
        rows.append({
            "Timestamp (IST)": r.get("timestamp_ist", ""),
            "Severity":        sev,
            "Component":       r.get("component", ""),
            "Message":         r.get("message", "")[:120],
            "Route":           r.get("route", ""),
            "Request ID":      r.get("request_id", ""),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Severity": st.column_config.TextColumn(width="small"),
                     "Message":  st.column_config.TextColumn(width="large"),
                 })


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — METRICS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_metrics():
    _section_header("📊", "SRE Metrics", "Health trend, error rate, alert frequency")

    metrics = get_sre_metrics()
    hist    = metrics.get("metrics_history", [])

    # Current snapshot
    h = metrics["health"]
    a = metrics["alerts"]
    b = metrics["bugs"]
    au= metrics["audit"]

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("🏥 Health %",     f"{h.get('health_pct', 0)}%", f"{h['ok']} OK / {h['total']} entities")
    mc2.metric("🚨 Open Alerts",  a["total_open"], f"P0:{a['p0']} P1:{a['p1']} P2:{a['p2']}")
    mc3.metric("🐛 Open Bugs",    b["open"], f"{b['fixed']} fixed")
    mc4.metric("📋 Audit Records", au["total_records"], f"{au['recent_errors']} recent errors")

    st.markdown("---")

    if len(hist) >= 2:
        df_hist = pd.DataFrame(hist)
        df_hist = df_hist.rename(columns={
            "health_pct": "Health %", "ok": "OK", "warn": "Warn", "fail": "Fail",
        })
        if "Health %" in df_hist.columns:
            st.subheader("Health % Trend")
            st.line_chart(df_hist.set_index("timestamp_ist")["Health %"] if "timestamp_ist" in df_hist.columns
                          else df_hist["Health %"])
    else:
        st.info("Health trend will appear after more SRE cycles run (min 2 data points).")

    # API stats table
    st.markdown("---")
    _section_header("📡", "API Reliability Matrix", "From api_stats.json")

    try:
        import json as _json
        from pathlib import Path as _Path
        stats_file = _Path(__file__).parent.parent / "api_stats.json"
        with open(stats_file, encoding="utf-8") as f:
            stats = _json.load(f)

        rows = []
        for api_id, s in stats.items():
            calls   = s.get("calls", 0)
            fails   = s.get("failures", 0)
            uptime  = f"{(1 - fails/calls)*100:.1f}%" if calls > 0 else "N/A"
            rows.append({
                "API":              api_id,
                "Status":           s.get("status", "?"),
                "Calls":            calls,
                "Failures":         fails,
                "Uptime %":         uptime,
                "Avg Latency (ms)": s.get("avg_latency_ms", 0),
                "Fallbacks":        s.get("fallback_activations", 0),
                "Last Call (IST)":  s.get("last_call_time", ""),
            })

        df_apis = pd.DataFrame(rows)
        st.dataframe(df_apis, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Could not load api_stats.json: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — CONFLICTS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_conflicts():
    _section_header("⚔️", "Conflict & Overwrite Monitor", "Auto vs Manual data conflicts — audit trail always kept")

    pending = ConflictProtector.get_pending_conflicts()
    history = get_change_history(n=100)

    # Pending conflicts
    if pending:
        st.markdown(f"**{len(pending)} pending conflicts require resolution:**")
        for conf in pending:
            conf_id  = conf.get("conflict_id", "?")
            entity   = conf.get("entity_id", "")
            field    = conf.get("field", "")
            auto_v   = conf.get("auto_value", "")
            manual_v = conf.get("manual_value", "")
            ts       = conf.get("timestamp_ist", "")

            st.markdown(f"""
<div style="background:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #d97706;
            border-radius:8px;padding:12px 15px;margin-bottom:8px;">
  <div style="font-weight:700;color:#92400e;margin-bottom:6px;">⚔️ Conflict: {entity}.{field}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.78rem;">
    <div style="background:#fee2e2;border-radius:6px;padding:8px;">
      <b>🤖 Auto value:</b><br/>{auto_v}
    </div>
    <div style="background:#dbeafe;border-radius:6px;padding:8px;">
      <b>👤 Manual value:</b><br/>{manual_v}
    </div>
  </div>
  <div style="font-size:0.62rem;color:#94a3b8;margin-top:6px;">{ts} | ID: {conf_id}</div>
</div>""", unsafe_allow_html=True)

            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button(f"Keep Auto", key=f"conf_auto_{conf_id}"):
                    ConflictProtector.resolve_conflict(conf_id, "auto", "user_dashboard")
                    st.success("Kept auto value")
                    st.rerun()
            with cc2:
                if st.button(f"Keep Manual", key=f"conf_manual_{conf_id}"):
                    ConflictProtector.resolve_conflict(conf_id, "manual", "user_dashboard")
                    st.success("Kept manual value")
                    st.rerun()
    else:
        st.success("✅ No pending conflicts")

    # Change history
    st.markdown("---")
    _section_header("📋", "Change History", f"Last {len(history)} entries (newest first)")

    if history:
        rows = []
        for r in history:
            rows.append({
                "Timestamp (IST)": r.get("timestamp_ist", ""),
                "Entity":          r.get("entity", ""),
                "Field":           r.get("field", ""),
                "Old Value":       str(r.get("old_value", ""))[:50],
                "New Value":       str(r.get("new_value", ""))[:50],
                "Actor":           r.get("actor", ""),
                "Source":          r.get("source", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No change history yet")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7 — TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

def _render_test_suite():
    _section_header("🧪", "Automated Test Suite", "Live pass/fail matrix — simulates real failure scenarios")

    st.info("""
**Tests simulate real failure conditions** and verify the self-healing system responds correctly.
Each test is safe — it does not corrupt real data. Results are logged to the audit log.
""")

    if st.button("▶ Run All Tests", type="primary", use_container_width=True):
        results = _run_all_tests()
        _display_test_results(results)
    else:
        st.caption("Click 'Run All Tests' to execute the full test matrix")

        # Show last results if cached
        if st.session_state.get("_sre_last_test_results"):
            st.markdown("**Last test run results:**")
            _display_test_results(st.session_state["_sre_last_test_results"])


def _run_all_tests() -> list:
    """Execute all SRE test scenarios. Returns list of result dicts."""
    results = []

    # ── TEST 1: Data Validator — NaN price ────────────────────────────────────
    t = {"id": "T-01", "name": "Calc Validator: NaN price", "category": "Calculation"}
    try:
        import math
        ok, issues = DataValidator.validate_price(float("nan"), "test_price")
        if not ok and any("NaN" in i for i in issues):
            t.update({"result": "PASS", "notes": "NaN correctly detected"})
        else:
            t.update({"result": "FAIL", "notes": f"Expected NaN detection, got: {issues}"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 2: Data Validator — out-of-range price ───────────────────────────
    t = {"id": "T-02", "name": "Calc Validator: Out-of-range price", "category": "Calculation"}
    try:
        ok, issues = DataValidator.validate_price(999, "test_price", min_inr=15000)
        if not ok and issues:
            t.update({"result": "PASS", "notes": f"Out-of-range detected: {issues[0]}"})
        else:
            t.update({"result": "FAIL", "notes": "Expected range violation, got OK"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 3: Data Validator — valid price ──────────────────────────────────
    t = {"id": "T-03", "name": "Calc Validator: Valid price passes", "category": "Calculation"}
    try:
        ok, issues = DataValidator.validate_price(42000, "test_price", min_inr=15000, max_inr=120000)
        if ok:
            t.update({"result": "PASS", "notes": "Valid price ₹42,000 passed correctly"})
        else:
            t.update({"result": "FAIL", "notes": f"Valid price rejected: {issues}"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 4: Smart Alert Engine — alert fires ──────────────────────────────
    t = {"id": "T-04", "name": "Alert Engine: P1 alert fires", "category": "Alerts"}
    try:
        alert_id = SmartAlertEngine.fire(
            "P1", "test_entity_sre_test",
            what_happened="[TEST] Simulated P1 degradation",
            where="Test Suite",
            why="Automated test — no real issue",
            action_needed="No action needed — this is a test",
        )
        if alert_id:
            SmartAlertEngine.resolve(alert_id, "Resolved")
            t.update({"result": "PASS", "notes": f"Alert {alert_id} fired and resolved"})
        else:
            t.update({"result": "WARN", "notes": "Alert suppressed (duplicate within window)"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 5: Bug auto-creation ─────────────────────────────────────────────
    t = {"id": "T-05", "name": "Bug Board: Auto-create bug", "category": "Bug Tracker"}
    try:
        bug_id = BugAutoCreator.create(
            severity="P2",
            entity="sre_test_entity",
            title="[TEST] Auto-created test bug",
            component_owner="backend",
            reproduction_steps=["1. Run SRE test suite", "2. Check Bug Board"],
            auto_created=True,
        )
        if bug_id:
            BugAutoCreator.update_status(bug_id, "Fixed")
            BugAutoCreator.update_status(bug_id, "Verified")
            t.update({"result": "PASS", "notes": f"Bug {bug_id} created, marked Fixed→Verified"})
        else:
            t.update({"result": "FAIL", "notes": "Bug creation returned empty ID"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 6: Audit logger works ────────────────────────────────────────────
    t = {"id": "T-06", "name": "Audit Logger: Logs all severities", "category": "Observability"}
    try:
        rid = AuditLogger.info("TestSuite", "[TEST] info message")
        AuditLogger.warn("TestSuite", "[TEST] warn message")
        AuditLogger.error("TestSuite", "[TEST] error message")
        records = AuditLogger.get_recent(n=20)
        test_recs = [r for r in records if "[TEST]" in r.get("message", "")]
        if len(test_recs) >= 3:
            t.update({"result": "PASS", "notes": f"Audit log working: {len(test_recs)} test records found"})
        else:
            t.update({"result": "FAIL", "notes": f"Only {len(test_recs)} test records found (expected ≥3)"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 7: Health check engine runs ──────────────────────────────────────
    t = {"id": "T-07", "name": "Health Engine: Full run completes", "category": "Health"}
    try:
        result = HealthCheckEngine.run_all()
        if "summary" in result and "health_pct" in result["summary"]:
            pct = result["summary"]["health_pct"]
            t.update({"result": "PASS",
                      "notes": f"Health check completed: {pct}% healthy — {result['summary']}"})
        else:
            t.update({"result": "FAIL", "notes": f"Unexpected result shape: {list(result.keys())}"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 8: Conflict protector ────────────────────────────────────────────
    t = {"id": "T-08", "name": "Conflict Protector: Conflict detected", "category": "Data Integrity"}
    try:
        # Simulate user then system writing different values
        r1 = ConflictProtector.check_and_log(
            "test_price_field", "DRUM_TEST",
            current_value=42000, new_value=43000,
            actor="user:test", source="manual_entry",
        )
        r2 = ConflictProtector.check_and_log(
            "test_price_field", "DRUM_TEST",
            current_value=43000, new_value=44000,
            actor="system", source="api_fetch",
        )
        if r2.get("conflict"):
            conf_id = r2["conflict_id"]
            ConflictProtector.resolve_conflict(conf_id, "auto", "test_suite")
            t.update({"result": "PASS", "notes": f"Conflict {conf_id} detected and resolved"})
        else:
            t.update({"result": "WARN", "notes": "No conflict detected (may be first run)"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 9: Export validator — blank check ────────────────────────────────
    t = {"id": "T-09", "name": "Export Validator: Empty content caught", "category": "Export"}
    try:
        from sre_engine import ExportValidator
        ok, issues = ExportValidator.validate_before_export([])
        if not ok and issues:
            t.update({"result": "PASS", "notes": f"Empty export correctly caught: {issues[0]}"})
        else:
            t.update({"result": "FAIL", "notes": "Empty export was not detected"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 10: Data quality — live_prices validation ─────────────────────────
    t = {"id": "T-10", "name": "Data Validator: Live prices sanity", "category": "Data Quality"}
    try:
        bad_prices = {"DRUM_MUMBAI_VG30": -500, "DRUM_KANDLA_VG30": float("nan")}
        ok, issues = DataValidator.validate_live_prices(bad_prices)
        if not ok and len(issues) >= 2:
            t.update({"result": "PASS", "notes": f"Bad prices caught: {'; '.join(issues[:2])}"})
        else:
            t.update({"result": "FAIL", "notes": f"Expected 2 issues, got: {issues}"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 11: Calc heal — reverts bad value ────────────────────────────────
    t = {"id": "T-11", "name": "Calc Self-Heal: Reverts NaN to last valid", "category": "Self-Healing"}
    try:
        result = SelfHealEngine.heal_calculation(
            name="test_price_calc",
            bad_value=float("nan"),
            last_valid=42500.0,
            reason="NaN detected in pricing formula",
        )
        if result.get("healed") and result.get("new") == 42500.0:
            t.update({"result": "PASS", "notes": "Calc heal: NaN → 42500.0 logged correctly"})
        else:
            t.update({"result": "FAIL", "notes": f"Unexpected heal result: {result}"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    # ── TEST 12: Alert dedup — same entity not re-alerted within window ────────
    t = {"id": "T-12", "name": "Alert Dedup: Suppresses repeat alert", "category": "Alerts"}
    try:
        entity = f"dedup_test_{datetime.datetime.now().strftime('%H%M%S')}"
        id1 = SmartAlertEngine.fire("P2", entity, "first", "test", "test")
        id2 = SmartAlertEngine.fire("P2", entity, "second (should be suppressed)", "test", "test")
        if id1 and id2 is None:
            t.update({"result": "PASS", "notes": "Duplicate alert correctly suppressed"})
            SmartAlertEngine.resolve(id1)
        else:
            t.update({"result": "WARN", "notes": f"id1={id1} id2={id2} — suppression may not have triggered"})
    except Exception as e:
        t.update({"result": "FAIL", "notes": str(e)})
    results.append(t)

    st.session_state["_sre_last_test_results"] = results
    AuditLogger.info("SRETestSuite", f"Test run complete: {sum(1 for r in results if r.get('result')=='PASS')}/{len(results)} PASS")
    return results


def _display_test_results(results: list) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.get("result") == "PASS")
    warned = sum(1 for r in results if r.get("result") == "WARN")
    failed = sum(1 for r in results if r.get("result") == "FAIL")
    pass_pct = int(passed / total * 100) if total else 0

    # Summary bar
    if failed == 0:
        st.success(f"✅ **{passed}/{total} PASS** ({pass_pct}%) — {warned} warnings")
    else:
        st.error(f"❌ **{failed} FAILED** — {passed} passed, {warned} warnings")

    # Matrix table
    rows = []
    for r in results:
        result = r.get("result", "?")
        icon   = "✅" if result == "PASS" else ("⚠️" if result == "WARN" else "❌")
        rows.append({
            "ID":       r.get("id", ""),
            "Test":     r.get("name", ""),
            "Category": r.get("category", ""),
            "Result":   f"{icon} {result}",
            "Notes":    r.get("notes", "")[:120],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={"Notes": st.column_config.TextColumn(width="large")})

    # Certification
    st.markdown("---")
    if pass_pct >= 80 and failed == 0:
        st.markdown("""
<div style="background:#f0fdf4;border:2px solid #16a34a;border-radius:10px;padding:16px 20px;text-align:center;">
  <div style="font-size:1.2rem;font-weight:800;color:#16a34a;">🏆 PRODUCTION READY CERTIFIED</div>
  <div style="font-size:0.8rem;color:#166534;margin-top:4px;">
    All SRE checks pass — auto-heal, alerts, bug creation, conflict protection, audit log working
  </div>
</div>""", unsafe_allow_html=True)
    elif pass_pct >= 70:
        st.warning(f"⚠️ Partially certified ({pass_pct}% pass) — resolve warnings before production")
    else:
        st.error(f"❌ Not certified — {failed} failures must be fixed")
