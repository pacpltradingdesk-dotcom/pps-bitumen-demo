"""
ops_dashboard.py — Operations Monitoring Dashboard
====================================================
Worker status, source health, queue monitor, source registry, error log.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).parent.parent
NAVY = "#1e3a5f"
GOLD = "#c9a84c"
GREEN = "#2d6a4f"
FIRE = "#b85c38"


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def _status_badge(ok: bool, label_ok: str = "Running", label_fail: str = "Stopped") -> str:
    if ok:
        return f'<span style="background:{GREEN};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:600;">{label_ok}</span>'
    return f'<span style="background:{FIRE};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:600;">{label_fail}</span>'


def render():
    """Main render function for Ops Dashboard."""
    from ui_badges import display_badge
    display_badge("real-time")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{NAVY},#0d1b2e);padding:18px 24px;
                border-radius:10px;margin-bottom:16px;">
      <div style="font-size:1.2rem;font-weight:700;color:#ffffff;">🖥️ Operations Dashboard</div>
      <div style="font-size:0.8rem;color:{GOLD};margin-top:4px;">
        Workers, source health, queues, source registry, and error logs
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Workers", "Source Health", "Queue Monitor",
        "Source Registry", "Error Log",
    ])

    with tab1:
        _render_workers()
    with tab2:
        _render_source_health()
    with tab3:
        _render_queue_monitor()
    with tab4:
        _render_source_registry()
    with tab5:
        _render_error_log()


# ── Tab 1: Worker Status ─────────────────────────────────────────────────────

def _render_workers():
    st.subheader("Background Workers")

    workers = [
        {"name": "API Health Checker", "module": "api_manager", "flag": "_G_health", "interval": "30 min"},
        {"name": "SRE Self-Healing", "module": "sre_engine", "flag": "_sre_thread_started", "interval": "15 min"},
        {"name": "API Hub Scheduler", "module": "api_hub_engine", "flag": "_hub_scheduler_started", "interval": "60 min"},
        {"name": "Sync Engine", "module": "sync_engine", "flag": "_scheduler_running", "interval": "60 min"},
        {"name": "Email Queue Processor", "module": "email_engine", "flag": "_email_scheduler_running", "interval": "5 min"},
        {"name": "WhatsApp Queue Processor", "module": "whatsapp_engine", "flag": "_wa_scheduler_running", "interval": "2 min"},
        {"name": "News Fetcher", "module": "news_engine", "flag": "_bg_started", "interval": "10 min"},
        {"name": "AI Fallback Monitor", "module": "ai_fallback_engine", "flag": "_G", "interval": "5 min", "dict_key": "monitor_started"},
    ]

    rows_html = []
    for w in workers:
        # Try to check if the worker module's scheduler flag is True
        is_running = False
        try:
            import importlib
            mod = importlib.import_module(w["module"])
            flag_val = getattr(mod, w["flag"], False)
            if "dict_key" in w and isinstance(flag_val, dict):
                is_running = flag_val.get(w["dict_key"], False)
            else:
                is_running = bool(flag_val)
        except Exception:
            pass

        badge = _status_badge(is_running)
        rows_html.append(f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:8px 12px;color:#e2e8f0;font-weight:600;">{w['name']}</td>
          <td style="padding:8px 12px;">{badge}</td>
          <td style="padding:8px 12px;color:#94a3b8;font-size:0.85rem;">{w['interval']}</td>
          <td style="padding:8px 12px;color:#94a3b8;font-size:0.85rem;">{w['module']}</td>
        </tr>
        """)

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#0d1b2e;border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:{NAVY};">
          <th style="padding:8px 12px;text-align:left;color:#fff;font-size:0.8rem;">Worker</th>
          <th style="padding:8px 12px;text-align:left;color:#fff;font-size:0.8rem;">Status</th>
          <th style="padding:8px 12px;text-align:left;color:#fff;font-size:0.8rem;">Interval</th>
          <th style="padding:8px 12px;text-align:left;color:#fff;font-size:0.8rem;">Module</th>
        </tr>
      </thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    """, unsafe_allow_html=True)


# ── Tab 2: Source Health ──────────────────────────────────────────────────────

def _render_source_health():
    st.subheader("API Source Health")

    health_log = _load_json(BASE / "api_health_log.json", [])
    catalog = _load_json(BASE / "hub_catalog.json", {})

    # Get latest health per source
    sources = {}
    if isinstance(catalog, dict):
        for key, info in catalog.items():
            if isinstance(info, dict) and info.get("api_name"):
                sources[key] = {
                    "name": info.get("api_name", key),
                    "status": "Unknown",
                    "last_check": "N/A",
                    "records": 0,
                }

    # Overlay health log
    if isinstance(health_log, list):
        for entry in health_log[-50:]:
            src = entry.get("source", entry.get("api", ""))
            for key in sources:
                if key in str(src).lower() or sources[key]["name"].lower() in str(src).lower():
                    sources[key]["status"] = entry.get("status", "Unknown")
                    sources[key]["last_check"] = entry.get("timestamp", entry.get("checked_at", "N/A"))
                    sources[key]["records"] = entry.get("records", 0)

    if sources:
        cols = st.columns(3)
        for i, (key, info) in enumerate(sources.items()):
            with cols[i % 3]:
                status = info["status"]
                if status in ("ok", "OK", "success", "active"):
                    border_color = GREEN
                    status_label = "HEALTHY"
                elif status in ("warn", "warning", "slow"):
                    border_color = GOLD
                    status_label = "WARNING"
                else:
                    border_color = FIRE
                    status_label = status.upper()[:12]

                st.markdown(f"""
                <div style="background:#0d1b2e;border-left:4px solid {border_color};padding:10px 14px;
                            border-radius:0 8px 8px 0;margin-bottom:8px;">
                  <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;">{info['name'][:30]}</div>
                  <div style="font-size:0.75rem;color:{border_color};margin-top:2px;">{status_label}</div>
                  <div style="font-size:0.7rem;color:#64748b;margin-top:2px;">Last: {info['last_check']}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No source health data available. Run API Hub sync first.")


# ── Tab 3: Queue Monitor ─────────────────────────────────────────────────────

def _render_queue_monitor():
    st.subheader("Message Queue Monitor")

    ec1, ec2 = st.columns(2)

    with ec1:
        st.markdown(f"**📧 Email Queue**")
        try:
            from database import get_email_queue
            all_emails = get_email_queue(status=None, limit=10000)
            counts = {"pending": 0, "draft": 0, "sent": 0, "failed": 0}
            for e in (all_emails or []):
                s = e.get("status", "draft")
                counts[s] = counts.get(s, 0) + 1
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Pending", counts["pending"])
            mc2.metric("Draft", counts["draft"])
            mc3.metric("Sent", counts["sent"])
            mc4.metric("Failed", counts["failed"])

            # Process now button
            if st.button("Process Email Queue Now", key="ops_email_process"):
                try:
                    from email_engine import EmailEngine
                    ee = EmailEngine()
                    ee.process_queue()
                    st.success("Email queue processed.")
                except Exception as e:
                    st.error(f"Failed: {e}")
        except Exception:
            st.caption("Email queue not available.")

    with ec2:
        st.markdown(f"**💬 WhatsApp Queue**")
        try:
            from database import get_wa_queue
            all_wa = get_wa_queue(status=None, limit=10000)
            counts = {"pending": 0, "sent": 0, "delivered": 0, "read": 0, "failed": 0}
            for w in (all_wa or []):
                s = w.get("status", "pending")
                counts[s] = counts.get(s, 0) + 1
            wc1, wc2, wc3, wc4 = st.columns(4)
            wc1.metric("Pending", counts["pending"])
            wc2.metric("Sent", counts["sent"])
            wc3.metric("Delivered", counts["delivered"])
            wc4.metric("Failed", counts["failed"])

            if st.button("Process WA Queue Now", key="ops_wa_process"):
                try:
                    from whatsapp_engine import WhatsAppEngine
                    we = WhatsAppEngine()
                    we.process_queue()
                    st.success("WhatsApp queue processed.")
                except Exception as e:
                    st.error(f"Failed: {e}")
        except Exception:
            st.caption("WhatsApp queue not available.")


# ── Tab 4: Source Registry ────────────────────────────────────────────────────

def _render_source_registry():
    st.subheader("Data Source Registry")

    try:
        from database import (
            get_all_sources, insert_source_registry, update_source_registry, delete_source_registry
        )

        sources = get_all_sources()

        if sources:
            df = pd.DataFrame(sources)
            display_cols = [
                c for c in ["id", "source_key", "source_name", "category", "status",
                            "refresh_minutes", "last_success", "error_count"]
                if c in df.columns
            ]
            st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

            # Edit/Delete
            for src in sources:
                with st.expander(f"⚙️ {src['source_name']} ({src['source_key']})"):
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        new_status = st.selectbox(
                            "Status", ["active", "disabled", "failing"],
                            index=["active", "disabled", "failing"].index(src.get("status", "active")),
                            key=f"sr_status_{src['id']}",
                        )
                        new_refresh = st.number_input(
                            "Refresh (minutes)", value=src.get("refresh_minutes", 60),
                            min_value=5, max_value=1440,
                            key=f"sr_refresh_{src['id']}",
                        )
                    with sc2:
                        if st.button("Update", key=f"sr_update_{src['id']}"):
                            update_source_registry(src["id"], {
                                "status": new_status,
                                "refresh_minutes": new_refresh,
                            })
                            st.success("Source updated.")
                            st.rerun()
                        if st.button("Delete", key=f"sr_delete_{src['id']}", type="secondary"):
                            delete_source_registry(src["id"])
                            st.success("Source deleted.")
                            st.rerun()
        else:
            st.info("No sources in registry. Add sources below or seed from API Hub catalog.")

            # Seed from hub_catalog.json
            if st.button("Seed from API Hub Catalog", type="primary", key="sr_seed"):
                catalog = _load_json(BASE / "hub_catalog.json", {})
                count = 0
                if isinstance(catalog, dict):
                    for key, info in catalog.items():
                        if isinstance(info, dict) and info.get("api_name"):
                            try:
                                insert_source_registry({
                                    "source_key": key,
                                    "source_name": info.get("api_name", key),
                                    "category": info.get("category", "General"),
                                    "provider": info.get("provider", ""),
                                    "api_url": info.get("base_url", ""),
                                    "auth_type": info.get("auth_type", "none"),
                                    "status": "active",
                                    "refresh_minutes": 60,
                                })
                                count += 1
                            except Exception:
                                pass
                st.success(f"Seeded {count} sources from API Hub catalog.")
                st.rerun()

        # Add new source
        st.markdown("---")
        st.markdown("**Add New Source**")
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            new_key = st.text_input("Source Key", key="sr_new_key", placeholder="e.g. custom_rss")
            new_name = st.text_input("Source Name", key="sr_new_name")
        with ac2:
            new_cat = st.text_input("Category", key="sr_new_cat", placeholder="News, Market, etc.")
            new_url = st.text_input("API URL", key="sr_new_url")
        with ac3:
            new_auth = st.selectbox("Auth Type", ["none", "api_key", "oauth"], key="sr_new_auth")
            new_refresh = st.number_input("Refresh (min)", value=60, min_value=5, key="sr_new_refresh")

        if st.button("Add Source", type="primary", key="sr_add_btn"):
            if new_key and new_name:
                try:
                    insert_source_registry({
                        "source_key": new_key.strip(),
                        "source_name": new_name.strip(),
                        "category": new_cat.strip(),
                        "api_url": new_url.strip(),
                        "auth_type": new_auth,
                        "refresh_minutes": new_refresh,
                        "status": "active",
                    })
                    st.success(f"Source '{new_name}' added.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Source key and name are required.")

    except ImportError:
        st.error("database module not available.")


# ── Tab 5: Error Log ─────────────────────────────────────────────────────────

def _render_error_log():
    st.subheader("Error & Alert Log")

    # Load error logs
    errors = _load_json(BASE / "api_error_log.json", [])
    alerts = _load_json(BASE / "sre_alerts.json", [])

    # Combine and sort
    combined = []
    for e in (errors if isinstance(errors, list) else []):
        combined.append({
            "source": "API Error",
            "severity": e.get("severity", "ERROR"),
            "message": e.get("message", e.get("error", str(e))),
            "timestamp": e.get("timestamp", e.get("created_at", "")),
            "details": e.get("details", e.get("stack_trace", "")),
        })
    for a in (alerts if isinstance(alerts, list) else []):
        combined.append({
            "source": "SRE Alert",
            "severity": a.get("priority", a.get("severity", "P2")),
            "message": a.get("title", a.get("message", str(a))),
            "timestamp": a.get("created_at", a.get("timestamp", "")),
            "details": a.get("description", a.get("details", "")),
        })

    # Sort by timestamp descending
    combined.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    if combined:
        # Filter
        severity_filter = st.selectbox(
            "Filter by severity",
            ["All", "P0", "P1", "P2", "ERROR", "WARN"],
            key="ops_err_filter",
        )
        if severity_filter != "All":
            combined = [c for c in combined if severity_filter.lower() in str(c.get("severity", "")).lower()]

        # Display (limit to 100)
        for entry in combined[:100]:
            sev = str(entry.get("severity", "")).upper()
            if "P0" in sev or "CRIT" in sev:
                border_color = "#dc2626"
            elif "P1" in sev or "ERROR" in sev:
                border_color = FIRE
            elif "P2" in sev or "WARN" in sev:
                border_color = GOLD
            else:
                border_color = "#64748b"

            with st.expander(f"[{entry.get('timestamp', 'N/A')[:19]}] {sev} — {entry.get('message', '')[:80]}"):
                st.markdown(f"**Source:** {entry.get('source', 'N/A')}")
                st.markdown(f"**Severity:** {sev}")
                st.markdown(f"**Time:** {entry.get('timestamp', 'N/A')}")
                if entry.get("details"):
                    st.code(str(entry["details"])[:2000], language=None)
    else:
        st.success("No errors or alerts. System is healthy.")
