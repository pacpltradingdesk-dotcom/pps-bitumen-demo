"""
command_intel/system_control_center.py — System Control Center UI
=================================================================
9-section Streamlit dashboard for full system monitoring & control.
Vastu Design System: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import streamlit as st

# ── Vastu Design System Colors ────────────────────────────────────────────────
_NAVY = "#1e3a5f"
_GOLD = "#c9a84c"
_GREEN = "#2d6a4f"
_RED = "#721c24"
_ORANGE = "#a04000"
_BG_GREEN = "#d4edda"
_BG_YELLOW = "#fff3cd"
_BG_RED = "#f8d7da"
_BG_BLUE = "#d6e9f8"


def _status_dot(status: str) -> str:
    """Return colored status dot HTML."""
    color_map = {
        "running": _GREEN, "healthy": _GREEN, "ok": _GREEN, "standby": _GOLD,
        "stopped": _ORANGE, "degraded": _ORANGE, "down": _RED, "unavailable": _RED,
        "error": _RED, "not_loaded": "#888", "unknown": "#888", "idle": "#888",
    }
    color = color_map.get(status, "#888")
    return f'<span style="color:{color};font-size:1.2em;">●</span>'


def _badge(text: str, fg: str, bg: str) -> str:
    return (f'<span style="background:{bg};color:{fg};padding:2px 8px;'
            f'border-radius:4px;font-size:0.78em;font-weight:600;">{text}</span>')


def render():
    """Main render function for System Control Center."""
    # Header
    st.markdown(
        f'<div style="background:linear-gradient(135deg, {_NAVY}, #2c5282);'
        f'padding:18px 24px;border-radius:10px;margin-bottom:16px;">'
        f'<span style="color:white;font-size:1.3rem;font-weight:700;">🎛️ System Control Center</span>'
        f'<br><span style="color:{_GOLD};font-size:0.82rem;">'
        f'Full system monitoring, health scoring & master controls</span></div>',
        unsafe_allow_html=True,
    )

    # Top health score card
    _render_health_summary_top()

    # 9-section tabs
    tabs = st.tabs([
        "🧠 AI Models",
        "🌐 API Status",
        "🔄 Data Flow",
        "⚙️ Workers",
        "📤 Output",
        "🚨 Error Log",
        "📊 Health Score",
        "🔘 Switches",
        "🔒 Security",
    ])

    with tabs[0]:
        _render_ai_models()
    with tabs[1]:
        _render_api_connections()
    with tabs[2]:
        _render_data_flow()
    with tabs[3]:
        _render_workers()
    with tabs[4]:
        _render_output_monitoring()
    with tabs[5]:
        _render_error_log()
    with tabs[6]:
        _render_health_score()
    with tabs[7]:
        _render_master_switches()
    with tabs[8]:
        _render_security()


# ═══════════════════════════════════════════════════════════════════════════════
# TOP HEALTH SUMMARY BAR
# ═══════════════════════════════════════════════════════════════════════════════

def _render_health_summary_top():
    try:
        from system_control_engine import get_system_health_score
        health = get_system_health_score()
        score = health["score"]
        grade = health["grade"]

        if score >= 75:
            bg, fg = _BG_GREEN, _GREEN
        elif score >= 50:
            bg, fg = _BG_YELLOW, _ORANGE
        else:
            bg, fg = _BG_RED, _RED

        st.markdown(
            f'<div style="background:{bg};color:{fg};padding:10px 20px;'
            f'border-radius:8px;margin-bottom:12px;display:flex;'
            f'justify-content:space-between;align-items:center;">'
            f'<span style="font-size:1.1em;font-weight:700;">System Health: {score}/100 (Grade {grade})</span>'
            f'<span style="font-size:0.82em;">{health["timestamp"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.warning(f"Health score unavailable: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# A. AI MODELS STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_ai_models():
    try:
        from system_control_engine import get_ai_models_status
        models = get_ai_models_status()
    except Exception as e:
        st.error(f"Cannot load AI models status: {e}")
        return

    if not models:
        st.info("No AI models detected.")
        return

    # Action buttons row
    c1, c2, c3 = st.columns([2, 2, 4])
    with c1:
        if st.button("🔄 Re-test All", key="scc_retest_all", use_container_width=True):
            with st.spinner("Running health tests on all AI modules..."):
                try:
                    from ai_setup_engine import run_health_tests
                    tests = run_health_tests()
                    passed = sum(1 for t in tests if t["status"] == "pass")
                    st.success(f"Tests complete: {passed}/{len(tests)} passed")
                    st.rerun()
                except Exception as e:
                    st.error(f"Health tests failed: {e}")
    with c2:
        if st.button("🤖 AI Setup Page →", key="scc_goto_ai_setup", use_container_width=True):
            st.session_state['selected_page'] = "🤖 AI Setup & Workers"
            st.rerun()

    running = sum(1 for m in models if m["status"] == "running")
    standby = sum(1 for m in models if m["status"] == "standby")
    st.markdown(
        f'<p style="font-size:0.85em;color:#666;">'
        f'Total: {len(models)} · Running: {running} · Standby: {standby}</p>',
        unsafe_allow_html=True,
    )

    for m in models:
        dot = _status_dot(m["status"])
        cost_badge = _badge("FREE", _GREEN, _BG_GREEN) if m.get("cost") == "FREE" else _badge("PAID", _RED, _BG_RED)
        st.markdown(
            f'{dot} **{m["name"]}** &nbsp; {cost_badge} &nbsp; '
            f'<span style="font-size:0.78em;color:#555;">'
            f'Type: {m["type"]} · Status: {m["status"]} · {m.get("version", "")}</span>',
            unsafe_allow_html=True,
        )

    # Compact feature map
    st.markdown("#### Feature → AI Connection")
    try:
        from ai_workers import get_feature_map
        fmap = get_feature_map()
        for feature, info in fmap.items():
            dot = _status_dot(info.get("overall_status", "unknown"))
            st.markdown(
                f'{dot} <span style="font-size:0.82em;">'
                f'**{feature}** → <code>{info["module"]}</code></span>',
                unsafe_allow_html=True,
            )
    except Exception:
        st.info("Feature map not available. Run AI Setup first.")


# ═══════════════════════════════════════════════════════════════════════════════
# B. API CONNECTION STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_api_connections():
    try:
        from system_control_engine import get_api_connections_status
        conns = get_api_connections_status()
    except Exception as e:
        st.error(f"Cannot load API status: {e}")
        return

    if not conns:
        st.info("No API connections detected.")
        return

    # Summary metrics
    healthy = sum(1 for c in conns if c["status"] == "healthy")
    cols = st.columns(3)
    cols[0].metric("Total APIs", len(conns))
    cols[1].metric("Healthy", healthy)
    cols[2].metric("Issues", len(conns) - healthy)

    # Cards
    card_cols = st.columns(min(3, len(conns)))
    for i, conn in enumerate(conns):
        with card_cols[i % len(card_cols)]:
            dot = _status_dot(conn["status"])
            latency = conn.get("latency_ms", 0)
            if latency < 500:
                lat_color = _GREEN
            elif latency < 2000:
                lat_color = _ORANGE
            else:
                lat_color = _RED

            st.markdown(
                f'<div style="border:1px solid #ddd;border-radius:8px;padding:10px;margin:4px 0;">'
                f'{dot} <strong>{conn["name"]}</strong><br>'
                f'<span style="color:{lat_color};font-size:0.78em;">{latency}ms</span> · '
                f'<span style="font-size:0.78em;">Health: {conn.get("health_pct", 0)}%</span><br>'
                f'<span style="font-size:0.72em;color:#888;">Last sync: {conn.get("last_sync", "N/A")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# C. DATA FLOW DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════

def _render_data_flow():
    try:
        from system_control_engine import get_data_flow_status
        flow = get_data_flow_status()
        stages = flow["stages"]
    except Exception as e:
        st.error(f"Cannot load data flow: {e}")
        return

    st.markdown(
        f'<p style="font-size:0.82em;color:#666;">Data pipeline end-to-end status</p>',
        unsafe_allow_html=True,
    )

    # Render as horizontal pipeline
    stage_cols = st.columns(len(stages))
    for i, stage in enumerate(stages):
        with stage_cols[i]:
            dot = _status_dot(stage["status"])
            st.markdown(
                f'<div style="text-align:center;border:1px solid #ddd;border-radius:8px;'
                f'padding:8px 4px;min-height:100px;">'
                f'<div style="font-size:1.5em;">{stage["icon"]}</div>'
                f'{dot}<br>'
                f'<strong style="font-size:0.75em;">{stage["name"]}</strong><br>'
                f'<span style="font-size:0.68em;color:#666;">{stage["detail"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Arrow indicators between stages
    arrow_html = ""
    for i in range(len(stages) - 1):
        arrow_html += f'<span style="color:{_NAVY};font-weight:bold;margin:0 8px;">→</span>'
    st.markdown(
        f'<div style="text-align:center;margin:-8px 0 8px 0;font-size:1.3em;">'
        f'{arrow_html}</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# D. WORKER STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_workers():
    try:
        from system_control_engine import get_worker_status
        workers = get_worker_status()
    except Exception as e:
        st.error(f"Cannot load worker status: {e}")
        return

    if not workers:
        st.info("No workers detected.")
        return

    running = sum(1 for w in workers if w["status"] == "running")
    st.markdown(
        f'<p style="font-size:0.85em;color:#666;">'
        f'{running}/{len(workers)} workers active</p>',
        unsafe_allow_html=True,
    )

    # Table-style display
    for w in workers:
        dot = _status_dot(w["status"])
        st.markdown(
            f'{dot} **{w["name"]}** &nbsp; '
            f'<span style="font-size:0.78em;color:#555;">'
            f'Schedule: {w["schedule"]} · Status: {w["status"]} · '
            f'Last: {w["last_run"]} · Errors: {w["errors_24h"]}</span>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# E. OUTPUT MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

def _render_output_monitoring():
    try:
        from system_control_engine import get_output_monitoring
        output = get_output_monitoring()
    except Exception as e:
        st.error(f"Cannot load output monitoring: {e}")
        return

    cols = st.columns(4)
    cols[0].metric("📧 Emails Today", output.get("emails_today", 0))
    cols[1].metric("📱 WhatsApp Today", output.get("whatsapp_today", 0))
    cols[2].metric("📄 PDFs Today", output.get("pdfs_today", 0))
    cols[3].metric("📊 Reports Today", output.get("reports_today", 0))

    total = sum(output.values())
    if total == 0:
        st.info("No output generated today yet.")
    else:
        st.success(f"Total output items today: {total}")


# ═══════════════════════════════════════════════════════════════════════════════
# F. ERROR LOG VIEWER
# ═══════════════════════════════════════════════════════════════════════════════

def _render_error_log():
    try:
        from system_control_engine import get_error_log
        errors = get_error_log(50)
    except Exception as e:
        st.error(f"Cannot load error log: {e}")
        return

    if not errors:
        st.success("No errors in recent logs.")
        return

    # Severity filter
    severities = sorted(set(e.get("severity", "ERROR") for e in errors))
    selected = st.multiselect("Filter by severity", severities, default=severities,
                              key="scc_error_severity")

    filtered = [e for e in errors if e.get("severity") in selected]
    st.markdown(f'<p style="font-size:0.82em;color:#666;">Showing {len(filtered)} of {len(errors)} entries</p>',
                unsafe_allow_html=True)

    for e in filtered[:30]:
        sev = e.get("severity", "ERROR")
        if sev == "CRITICAL":
            sev_badge = _badge("CRITICAL", "white", _RED)
        elif sev == "ERROR":
            sev_badge = _badge("ERROR", _RED, _BG_RED)
        else:
            sev_badge = _badge("WARN", _ORANGE, _BG_YELLOW)

        st.markdown(
            f'{sev_badge} &nbsp; '
            f'<span style="font-size:0.78em;color:#333;">'
            f'<strong>{e.get("source", "")}</strong> · {e.get("time", "")} · '
            f'{e.get("message", "")[:120]}</span>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# G. HEALTH SCORE BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════════

def _render_health_score():
    try:
        from system_control_engine import get_system_health_score
        health = get_system_health_score()
    except Exception as e:
        st.error(f"Cannot load health score: {e}")
        return

    score = health["score"]
    grade = health["grade"]
    breakdown = health["breakdown"]

    # Main score
    if score >= 75:
        color = _GREEN
    elif score >= 50:
        color = _ORANGE
    else:
        color = _RED

    st.markdown(
        f'<div style="text-align:center;padding:20px;">'
        f'<span style="font-size:3em;font-weight:800;color:{color};">{score}</span>'
        f'<span style="font-size:1.5em;color:{color};"> / 100</span><br>'
        f'<span style="font-size:1.2em;font-weight:700;color:{color};">Grade {grade}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Breakdown
    st.markdown("### Score Breakdown")
    labels = {
        "api_health": ("🌐 API Health", 30),
        "data_freshness": ("📦 Data Freshness", 25),
        "ai_readiness": ("🧠 AI Readiness", 20),
        "worker_uptime": ("⚙️ Worker Uptime", 15),
        "error_rate": ("🚨 Error Rate", 10),
    }

    for key, (label, weight) in labels.items():
        val = breakdown.get(key, 0)
        bar_color = _GREEN if val >= 75 else (_ORANGE if val >= 50 else _RED)
        st.markdown(
            f'{label} &nbsp; <strong>{val}%</strong> &nbsp; '
            f'<span style="font-size:0.72em;color:#888;">(weight: {weight}%)</span>',
            unsafe_allow_html=True,
        )
        st.progress(val / 100)


# ═══════════════════════════════════════════════════════════════════════════════
# H. MASTER SWITCHES
# ═══════════════════════════════════════════════════════════════════════════════

def _render_master_switches():
    try:
        from system_control_engine import get_master_switches, set_master_switch
        switches = get_master_switches()
    except Exception as e:
        st.error(f"Cannot load master switches: {e}")
        return

    st.markdown(
        f'<p style="font-size:0.82em;color:#666;">'
        f'Toggle system features. Changes take effect immediately.</p>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, (key, switch) in enumerate(switches.items()):
        with cols[i % 2]:
            new_val = st.toggle(
                switch["label"],
                value=switch["enabled"],
                key=f"scc_switch_{key}",
            )
            if new_val != switch["enabled"]:
                set_master_switch(key, new_val)
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# I. SECURITY STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_security():
    try:
        from system_control_engine import get_security_status
        sec = get_security_status()
    except Exception as e:
        st.error(f"Cannot load security status: {e}")
        return

    items = [
        ("🔒 SSL/HTTPS", sec.get("ssl_enabled", False), sec.get("ssl_note", "")),
        ("🔐 Login Protection", sec.get("login_protection", False), "RBAC-based access control"),
        ("👥 RBAC Enabled", sec.get("rbac_enabled", False), "Role-based access control"),
        ("💾 Backup Status", sec.get("backup_status") == "ok", f"Last: {sec.get('last_backup', 'N/A')}"),
    ]

    for label, enabled, note in items:
        dot = _status_dot("ok" if enabled else "degraded")
        status_text = _badge("Active", _GREEN, _BG_GREEN) if enabled else _badge("Inactive", _ORANGE, _BG_YELLOW)
        st.markdown(
            f'{dot} **{label}** &nbsp; {status_text} &nbsp; '
            f'<span style="font-size:0.75em;color:#888;">{note}</span>',
            unsafe_allow_html=True,
        )
