"""
command_intel/ai_setup_dashboard.py — AI Setup & Workers Dashboard
===================================================================
Streamlit UI for AI environment, module registry, workers,
feature map, health tests, and re-test button.
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
    color_map = {
        "pass": _GREEN, "running": _GREEN, "active": _GREEN, "started": _GREEN,
        "degraded": _GOLD, "idle": _GOLD, "already_running": _GOLD, "starting": _GOLD,
        "fail": _RED, "stopped": _RED, "crashed": _RED, "error": _RED,
        "skipped": "#888", "not_tested": "#4a90d9", "N/A": "#888",
    }
    color = color_map.get(status, "#888")
    return f'<span style="color:{color};font-size:1.2em;">●</span>'


def _badge(text: str, fg: str, bg: str) -> str:
    return (f'<span style="background:{bg};color:{fg};padding:2px 8px;'
            f'border-radius:4px;font-size:0.78em;font-weight:600;">{text}</span>')


def _tier_badge(tier: str) -> str:
    if tier == "HIGH":
        return _badge("HIGH", "white", _GREEN)
    elif tier == "MEDIUM":
        return _badge("MEDIUM", _NAVY, _BG_YELLOW)
    else:
        return _badge("LOW", _ORANGE, _BG_YELLOW)


def render():
    """Main render function for AI Setup & Workers page."""
    # Header
    st.markdown(
        f'<div style="background:linear-gradient(135deg, {_NAVY}, #2c5282);'
        f'padding:18px 24px;border-radius:10px;margin-bottom:16px;">'
        f'<span style="color:white;font-size:1.3rem;font-weight:700;">'
        f'🤖 AI Setup & Workers</span>'
        f'<br><span style="color:{_GOLD};font-size:0.82rem;">'
        f'Environment detection, module registry, workers & health tests'
        f'</span></div>',
        unsafe_allow_html=True,
    )

    # Sections
    _render_environment()
    st.divider()
    _render_setup_actions()
    st.divider()
    _render_module_registry()
    st.divider()
    _render_workers()
    st.divider()
    _render_feature_map()
    st.divider()
    _render_proof_of_life()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ENVIRONMENT INFO
# ═══════════════════════════════════════════════════════════════════════════════

def _render_environment():
    st.markdown("### Environment")
    try:
        from ai_setup_engine import detect_environment, get_resource_tier
        env = detect_environment()
        tier = get_resource_tier(env)
    except Exception as e:
        st.error(f"Cannot detect environment: {e}")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OS", f"{env['os']}")
    c2.metric("RAM", f"{env['ram_gb']} GB")
    c3.metric("CPU Cores", f"{env['cpu_cores']}")
    c4.metric("Disk Free", f"{env['disk_free_gb']} GB")

    tier_html = _tier_badge(tier)
    gpu_text = f"GPU: {env['gpu_name']}" if env.get("gpu_available") else "No GPU detected"
    st.markdown(
        f'Resource Tier: {tier_html} &nbsp; | &nbsp; '
        f'Python: {env["python_version"]} &nbsp; | &nbsp; '
        f'{gpu_text}',
        unsafe_allow_html=True,
    )

    if env.get("venv_path"):
        st.markdown(
            f'<span style="font-size:0.75em;color:#666;">Venv: {env["venv_path"]}</span>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SETUP ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_setup_actions():
    st.markdown("### Setup Actions")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("🚀 Run Full Setup", use_container_width=True, type="primary"):
            with st.spinner("Running full AI setup (detect → install → Ollama → test)..."):
                try:
                    from ai_setup_engine import full_setup
                    report = full_setup()
                    st.session_state["_ai_setup_report"] = report
                    st.success(f"Setup complete! Tier: {report['tier']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Setup failed: {e}")

    with c2:
        if st.button("📦 Install Packages", use_container_width=True):
            with st.spinner("Installing packages..."):
                try:
                    from ai_setup_engine import install_packages, get_resource_tier
                    tier = get_resource_tier()
                    results = install_packages(tier)
                    installed = sum(1 for v in results.values() if v == "installed")
                    already = sum(1 for v in results.values() if v == "already")
                    st.success(f"Done: {installed} installed, {already} already present")
                except Exception as e:
                    st.error(f"Install failed: {e}")

    with c3:
        if st.button("🦙 Setup Ollama", use_container_width=True):
            with st.spinner("Setting up Ollama..."):
                try:
                    from ai_setup_engine import setup_ollama
                    result = setup_ollama()
                    if result["status"] == "running":
                        st.success(f"Ollama running! Models: {', '.join(result['models']) or 'pulling...'}")
                    else:
                        st.warning(result.get("details", "Ollama setup incomplete"))
                except Exception as e:
                    st.error(f"Ollama setup failed: {e}")

    with c4:
        if st.button("🔄 Re-test AI", use_container_width=True, type="primary"):
            with st.spinner("Running health tests on all AI modules..."):
                try:
                    from ai_setup_engine import run_health_tests
                    tests = run_health_tests()
                    st.session_state["_ai_health_tests"] = tests
                    passed = sum(1 for t in tests if t["status"] == "pass")
                    st.success(f"Tests complete: {passed}/{len(tests)} passed")
                    st.rerun()
                except Exception as e:
                    st.error(f"Health tests failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MODULE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

def _render_module_registry():
    st.markdown("### Module Registry")
    try:
        from ai_setup_engine import get_module_registry
        registry = get_module_registry()
    except Exception as e:
        st.error(f"Cannot load registry: {e}")
        return

    if not registry:
        st.info("No modules registered yet. Click 'Re-test AI' to populate the registry.")
        return

    # Summary
    passed = sum(1 for m in registry if m.get("health_test") == "pass")
    degraded = sum(1 for m in registry if m.get("health_test") == "degraded")
    failed = sum(1 for m in registry if m.get("health_test") == "fail")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Modules", len(registry))
    c2.metric("Passed", passed)
    c3.metric("Degraded", degraded)
    c4.metric("Failed", failed)

    # Table
    for m in registry:
        status = m.get("health_test", "not_tested")
        dot = _status_dot(status)

        if status == "pass":
            status_badge = _badge("PASS", _GREEN, _BG_GREEN)
        elif status == "degraded":
            status_badge = _badge("DEGRADED", _ORANGE, _BG_YELLOW)
        elif status == "fail":
            status_badge = _badge("FAIL", _RED, _BG_RED)
        else:
            status_badge = _badge("NOT TESTED", "#4a90d9", _BG_BLUE)

        error_text = ""
        if m.get("error_log"):
            error_text = f' · <span style="color:{_RED};font-size:0.72em;">{m["error_log"][:80]}</span>'

        st.markdown(
            f'{dot} **{m.get("display_name", m["name"])}** &nbsp; {status_badge} &nbsp; '
            f'<span style="font-size:0.78em;color:#555;">'
            f'Engine: {m.get("engine", "N/A")} · '
            f'Tested: {m.get("last_tested", "never")}</span>'
            f'{error_text}',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AI WORKERS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_workers():
    st.markdown("### AI Workers")

    try:
        from ai_workers import get_worker_status, start_workers, stop_workers, force_run
        from ai_setup_engine import get_resource_tier
    except Exception as e:
        st.error(f"Cannot load worker module: {e}")
        return

    # Control buttons
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("▶️ Start All Workers", use_container_width=True, type="primary"):
            tier = get_resource_tier()
            results = start_workers(tier)
            started = sum(1 for v in results.values() if v == "started")
            st.success(f"Started {started} workers (tier: {tier})")
            st.rerun()
    with c2:
        if st.button("⏹️ Stop All Workers", use_container_width=True):
            stop_workers()
            st.info("Workers stopping...")
            st.rerun()
    with c3:
        tier = get_resource_tier()
        st.markdown(
            f'<div style="padding:8px;text-align:center;">'
            f'Tier: {_tier_badge(tier)}</div>',
            unsafe_allow_html=True,
        )

    # Worker status list
    workers = get_worker_status()
    for w in workers:
        dot = _status_dot(w["status"])
        interval_min = w["interval"] // 60
        interval_text = f"{interval_min}m" if interval_min < 60 else f"{interval_min // 60}h"
        tier_text = f'Min tier: {w["min_tier"]}'

        error_text = ""
        if w.get("errors_24h", 0) > 0:
            error_text = f' · <span style="color:{_RED};">Errors: {w["errors_24h"]}</span>'

        cols = st.columns([6, 1])
        with cols[0]:
            st.markdown(
                f'{dot} **{w["display"]}** &nbsp; '
                f'<span style="font-size:0.78em;color:#555;">'
                f'Status: {w["status"]} · Interval: {interval_text} · '
                f'{tier_text} · Last: {w["last_run"]}</span>'
                f'{error_text}',
                unsafe_allow_html=True,
            )
        with cols[1]:
            if st.button("▶️", key=f"force_{w['name']}", help=f"Force run {w['display']}"):
                result = force_run(w["name"])
                if result.get("status") == "completed":
                    st.success(f"{w['display']} completed")
                else:
                    st.warning(f"{w['display']}: {result.get('error', 'unknown error')}")
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FEATURE-AI MAP
# ═══════════════════════════════════════════════════════════════════════════════

def _render_feature_map():
    st.markdown("### Feature → AI Connection Map")
    try:
        from ai_workers import get_feature_map
        fmap = get_feature_map()
    except Exception as e:
        st.error(f"Cannot load feature map: {e}")
        return

    if not fmap:
        st.info("No features mapped yet.")
        return

    for feature, info in fmap.items():
        status = info.get("overall_status", "unknown")
        dot = _status_dot(status)
        module_badge = _badge("loaded", _GREEN, _BG_GREEN) if info["module_loaded"] else _badge("missing", _RED, _BG_RED)

        worker_text = ""
        if info["worker"]:
            ws = info["worker_status"]
            worker_badge = _badge(ws, _GREEN if ws == "running" else _ORANGE,
                                  _BG_GREEN if ws == "running" else _BG_YELLOW)
            worker_text = f' · Worker: {worker_badge}'

        st.markdown(
            f'{dot} **{feature}** → '
            f'<span style="font-size:0.78em;">'
            f'Module: <code>{info["module"]}</code> {module_badge}'
            f'{worker_text}'
            f' · Page: {info.get("dashboard_page", "N/A")}</span>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. PROOF-OF-LIFE LOGS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_proof_of_life():
    st.markdown("### Proof-of-Life Logs")

    # Show last health test results
    tests = st.session_state.get("_ai_health_tests")
    if not tests:
        try:
            from ai_setup_engine import get_module_registry
            registry = get_module_registry()
            if registry:
                st.markdown(
                    f'<p style="font-size:0.82em;color:#666;">'
                    f'Showing data from module registry. Click "Re-test AI" for live results.</p>',
                    unsafe_allow_html=True,
                )
                for m in registry:
                    status = m.get("health_test", "not_tested")
                    dot = _status_dot(status)
                    st.markdown(
                        f'{dot} **{m.get("display_name", m["name"])}** — '
                        f'Engine: {m.get("engine", "N/A")} · '
                        f'Last tested: {m.get("last_tested", "never")}',
                        unsafe_allow_html=True,
                    )
                return
        except Exception:
            pass
        st.info("No health test data yet. Click 'Re-test AI' to run tests.")
        return

    st.markdown(
        f'<p style="font-size:0.82em;color:#666;">'
        f'Last health test results — {len(tests)} modules tested</p>',
        unsafe_allow_html=True,
    )

    for t in tests:
        dot = _status_dot(t["status"])

        if t["status"] == "pass":
            status_badge = _badge("PASS", _GREEN, _BG_GREEN)
        elif t["status"] == "degraded":
            status_badge = _badge("DEGRADED", _ORANGE, _BG_YELLOW)
        else:
            status_badge = _badge("FAIL", _RED, _BG_RED)

        time_badge = _badge(f'{t["response_ms"]}ms', _NAVY, _BG_BLUE)

        error_text = ""
        if t.get("error"):
            error_text = f'<br><span style="color:{_RED};font-size:0.72em;">Error: {t["error"][:100]}</span>'

        st.markdown(
            f'{dot} **{t["display_name"]}** &nbsp; {status_badge} &nbsp; {time_badge} &nbsp; '
            f'<span style="font-size:0.78em;color:#555;">'
            f'Engine: {t.get("engine_used", "N/A")} · '
            f'{t.get("details", "")}</span>'
            f'{error_text}',
            unsafe_allow_html=True,
        )
