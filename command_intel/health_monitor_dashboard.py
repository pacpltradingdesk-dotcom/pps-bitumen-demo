"""
Health Monitor Dashboard — Traffic Light System Health
======================================================
Real-time monitoring with Green/Yellow/Red/Blue traffic lights
for all 7 data categories, worker heartbeats, and fallback chain status.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge
import datetime


def render():
    display_badge("real-time")
    """Render the Health Monitor Dashboard with traffic lights."""

    st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(15, 23, 42, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">🏥</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Health Monitor — Traffic Light System
</div>
<div style="font-size:0.75rem; color:#94a3b8; letter-spacing:1px; text-transform:uppercase;">
24/7 Resilience • Fallback Chains • Worker Heartbeats • Data Confidence
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # ── Section 1: System Health Hero ─────────────────────────────────────
    _render_health_hero()

    st.markdown("---")

    # ── Section 2: Traffic Light Grid (7 data categories) ────────────────
    _render_traffic_lights()

    st.markdown("---")

    # ── Section 3: Worker Health Panel ────────────────────────────────────
    _render_worker_health()

    st.markdown("---")

    # ── Section 4: Fallback Chain Status ──────────────────────────────────
    _render_fallback_chains()

    st.markdown("---")

    # ── Section 5: Dead Letter Queue ──────────────────────────────────────
    _render_dlq_status()


def _render_health_hero():
    """Section 1: Large circular gauge with system health score."""
    st.markdown("### 🎯 System Health Score")

    try:
        from data_confidence_engine import compute_dashboard_confidence
        health = compute_dashboard_confidence()
        score = health.get("score", 0)
        color = health.get("color", "#94a3b8")
        label = health.get("label", "Unknown")
        degraded = health.get("degraded_sources", [])
    except Exception:
        score = 50
        color = "#f59e0b"
        label = "Unable to compute"
        degraded = []

    # Determine grade and icon
    if score >= 80:
        grade_icon = "🟢"
    elif score >= 60:
        grade_icon = "🟡"
    elif score >= 40:
        grade_icon = "🔴"
    else:
        grade_icon = "🔵"

    st.markdown(f"""
<div style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius:15px;
padding:30px; text-align:center; margin-bottom:15px;
box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
<div style="font-size:0.9rem; color:#94a3b8; font-weight:600; letter-spacing:2px;
text-transform:uppercase;">System Health Index</div>
<div style="position:relative; margin:20px auto; width:140px; height:140px;">
<svg viewBox="0 0 36 36" style="transform:rotate(-90deg);">
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
fill="none" stroke="#334155" stroke-width="2.5"/>
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
fill="none" stroke="{color}" stroke-width="2.5"
stroke-dasharray="{score}, 100" stroke-linecap="round"/>
</svg>
<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);">
<div style="font-size:2.2rem; font-weight:900; color:{color};">{score}</div>
<div style="font-size:0.6rem; color:#64748b;">/ 100</div>
</div>
</div>
<div style="font-size:1.2rem; font-weight:800; color:{color}; letter-spacing:1px;">
{grade_icon} {label}
</div>
{'<div style="font-size:0.7rem; color:#ef4444; margin-top:8px;">Degraded: ' + ', '.join(degraded) + '</div>' if degraded else ''}
</div>
""", unsafe_allow_html=True)


def _render_traffic_lights():
    """Section 2: Traffic light cards for each data category."""
    st.markdown("### 🚦 Data Source Traffic Lights")

    try:
        from resilience_config import FALLBACK_MATRIX, confidence_badge
    except ImportError:
        st.warning("Resilience config not available.")
        return

    # Get current status for each category
    try:
        from data_confidence_engine import get_all_confidences
        confs = {c.source_key: c for c in get_all_confidences()}
    except Exception:
        confs = {}

    # Map fallback categories to confidence keys
    _CAT_TO_CONF = {
        "crude_prices": "crude_prices",
        "fx_rates": "fx_rates",
        "weather": "weather",
        "news": "news_feed",
        "govt_data": None,
        "trade_data": "trade_imports",
        "system_time": None,
    }

    categories = list(FALLBACK_MATRIX.keys())

    # Render in 2 rows
    for row_start in range(0, len(categories), 4):
        row_cats = categories[row_start:row_start + 4]
        cols = st.columns(len(row_cats))
        for i, cat_key in enumerate(row_cats):
            cat = FALLBACK_MATRIX[cat_key]
            icon = cat.get("icon", "📊")
            label = cat.get("label", cat_key)

            # Get confidence info
            conf_key = _CAT_TO_CONF.get(cat_key)
            if conf_key and conf_key in confs:
                c = confs[conf_key]
                pct = c.confidence_score
                age = c.freshness_minutes
                source = c.provider
                if age < 60:
                    age_str = f"{age}m"
                elif age < 1440:
                    age_str = f"{age // 60}h"
                else:
                    age_str = f"{age // 1440}d"
            else:
                pct = cat["primary"].get("confidence", 50)
                age_str = "N/A"
                source = cat["primary"].get("label", "Unknown")

            # Determine traffic light color
            badge = confidence_badge(pct)
            dot = badge["emoji"]
            bg = badge["color"]

            # Determine active fallback level
            if pct >= 80:
                level = "Primary"
                levels_html = '<span style="color:#22c55e;">Primary</span> · <span style="color:#64748b;">Secondary</span> · <span style="color:#64748b;">Tertiary</span>'
            elif pct >= 60:
                level = "Secondary"
                levels_html = '<span style="color:#64748b;">Primary</span> · <span style="color:#f59e0b;">Secondary</span> · <span style="color:#64748b;">Tertiary</span>'
            elif pct >= 40:
                level = "Tertiary"
                levels_html = '<span style="color:#64748b;">Primary</span> · <span style="color:#64748b;">Secondary</span> · <span style="color:#ef4444;">Tertiary</span>'
            else:
                level = "Emergency"
                levels_html = '<span style="color:#3b82f6;">Emergency Fallback</span>'

            with cols[i]:
                st.markdown(f"""
<div style="background:white; border-radius:10px; padding:14px;
border-left:5px solid {bg}; box-shadow:0 2px 8px rgba(0,0,0,0.08);
min-height:160px;">
<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
<span style="font-size:1.2rem;">{icon}</span>
<span style="font-weight:700; color:#1e293b; font-size:0.85rem;">{label}</span>
</div>
<div style="font-size:0.7rem; color:#64748b; margin-bottom:4px;">Source: {source}</div>
<div style="display:flex; justify-content:space-between; margin:8px 0;">
<span style="background:{bg}15; color:{bg}; padding:2px 8px; border-radius:4px;
font-size:0.75rem; font-weight:600;">{dot} {pct}%</span>
<span style="font-size:0.7rem; color:#94a3b8;">Age: {age_str}</span>
</div>
<div style="font-size:0.65rem; color:#475569; margin-top:6px;">
{levels_html}
</div>
</div>
""", unsafe_allow_html=True)


def _render_worker_health():
    """Section 3: Worker heartbeat status panel."""
    st.markdown("### 💓 Worker Heartbeat Status")

    try:
        from resilience_manager import HeartbeatMonitor
        workers = HeartbeatMonitor.get_status()
    except Exception:
        workers = []

    if not workers:
        st.caption("No workers registered with HeartbeatMonitor yet. Workers register on first run cycle.")
        return

    cols = st.columns(min(4, len(workers)))
    for i, w in enumerate(workers):
        with cols[i % len(cols)]:
            name = w["name"]
            status = w["status"]
            age = w["last_beat_sec_ago"]
            restarts = w["restart_count_hour"]

            if status == "alive":
                s_color = "#22c55e"
                s_icon = "🟢"
                s_label = "Alive"
            elif status == "restarted":
                s_color = "#f59e0b"
                s_icon = "🟡"
                s_label = "Restarted"
            else:
                s_color = "#ef4444"
                s_icon = "🔴"
                s_label = "Dead"

            if age < 60:
                age_str = f"{age}s ago"
            elif age < 3600:
                age_str = f"{age // 60}m ago"
            else:
                age_str = f"{age // 3600}h ago"

            st.markdown(f"""
<div style="background:white; border-radius:8px; padding:10px; text-align:center;
border-bottom:3px solid {s_color}; box-shadow:0 2px 6px rgba(0,0,0,0.06);
margin-bottom:8px;">
<div style="font-size:1rem;">{s_icon}</div>
<div style="font-weight:600; font-size:0.75rem; color:#1e293b; margin:4px 0;">{name}</div>
<div style="font-size:0.65rem; color:#64748b;">Last beat: {age_str}</div>
<div style="font-size:0.6rem; color:{s_color}; font-weight:600;">{s_label}</div>
{'<div style="font-size:0.6rem; color:#f59e0b;">Restarts: ' + str(restarts) + '/hr</div>' if restarts > 0 else ''}
</div>
""", unsafe_allow_html=True)


def _render_fallback_chains():
    """Section 4: Visual fallback chain for each category."""
    st.markdown("### 🔗 Fallback Chain Status")

    try:
        from resilience_config import FALLBACK_MATRIX
    except ImportError:
        st.warning("Resilience config not available.")
        return

    for cat_key, cat in FALLBACK_MATRIX.items():
        icon = cat.get("icon", "📊")
        label = cat.get("label", cat_key)

        levels = []
        for level_name in ("primary", "secondary", "tertiary", "emergency"):
            entry = cat.get(level_name, {})
            if not entry:
                continue
            conf = entry.get("confidence", 50)
            src_label = entry.get("label", entry.get("source", ""))
            requires_key = entry.get("requires_key", False)

            # Check if key is configured
            key_status = ""
            if requires_key:
                try:
                    from settings_engine import get as sg
                    key_setting = entry.get("key_setting", "")
                    if key_setting and sg(key_setting, ""):
                        key_status = "🔑"
                    else:
                        key_status = "🔒"
                except Exception:
                    key_status = "🔒"

            if conf >= 80:
                dot_color = "#22c55e"
            elif conf >= 60:
                dot_color = "#f59e0b"
            elif conf >= 40:
                dot_color = "#ef4444"
            else:
                dot_color = "#3b82f6"

            levels.append(
                f'<span style="background:{dot_color}15; color:{dot_color}; '
                f'padding:3px 10px; border-radius:4px; font-size:0.7rem; font-weight:600; '
                f'border:1px solid {dot_color}40;">'
                f'{level_name.title()} {key_status}: {src_label} ({conf}%)</span>'
            )

        chain_html = ' <span style="color:#94a3b8;">→</span> '.join(levels)

        st.markdown(f"""
<div style="background:#f8fafc; border-radius:8px; padding:10px 14px; margin-bottom:8px;">
<div style="font-weight:600; font-size:0.8rem; color:#1e293b; margin-bottom:6px;">
{icon} {label}
</div>
<div style="overflow-x:auto; white-space:nowrap;">
{chain_html}
</div>
</div>
""", unsafe_allow_html=True)


def _render_dlq_status():
    """Section 5: Dead Letter Queue status."""
    st.markdown("### 📬 Dead Letter Queue")

    try:
        from resilience_manager import DeadLetterQueue
        stats = DeadLetterQueue.get_stats()
        queue = DeadLetterQueue.get_queue()
    except Exception:
        stats = {"total": 0, "pending": 0}
        queue = []

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Jobs", stats.get("total", 0))
    with c2:
        st.metric("Pending Retry", stats.get("pending", 0))
    with c3:
        st.metric("Queue File", "dead_letter_queue.json")

    if queue:
        with st.expander(f"View Queue ({len(queue)} items)", expanded=False):
            for job in queue[-10:]:
                status = job.get("status", "pending")
                s_color = "#f59e0b" if status == "pending" else "#22c55e" if status == "completed" else "#ef4444"
                st.markdown(
                    f'<div style="background:#f8fafc; padding:6px 10px; border-radius:4px; '
                    f'margin-bottom:4px; border-left:3px solid {s_color}; font-size:0.75rem;">'
                    f'<strong>{job.get("job_type", "?")}</strong> — '
                    f'Attempt {job.get("attempt", 0)}/{job.get("max_retries", 3)} — '
                    f'{job.get("error", "")[:80]} — '
                    f'<span style="color:{s_color};">{status}</span></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.success("Queue is empty — all jobs processed successfully.")
