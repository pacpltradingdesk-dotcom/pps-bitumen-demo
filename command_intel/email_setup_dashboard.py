"""
email_setup_dashboard.py — Full Email Configuration UI
=======================================================
Replaces the inline Email Engine page block in dashboard.py.
5 tabs: SMTP Config | Recipient Lists | Send Email | Delivery Log | Schedule
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
NAVY = "#1e3a5f"
GOLD = "#c9a84c"
GREEN = "#2d6a4f"


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def render():
    """Main render function for Email Setup page."""
    from ui_badges import display_badge
    display_badge("real-time")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{NAVY},#2c4f7c);padding:18px 24px;
                border-radius:10px;margin-bottom:16px;">
      <div style="font-size:1.2rem;font-weight:700;color:#ffffff;">📧 Email Engine Setup</div>
      <div style="font-size:0.8rem;color:{GOLD};margin-top:4px;">
        SMTP configuration, recipient lists, delivery logs, and scheduled reports
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "SMTP Config", "Recipient Lists", "Send Email", "Delivery Log", "Schedule"
    ])

    with tab1:
        _render_smtp_config()
    with tab2:
        _render_recipient_lists()
    with tab3:
        _render_send_email()
    with tab4:
        _render_delivery_log()
    with tab5:
        _render_schedule()


# ── Tab 1: SMTP Configuration ────────────────────────────────────────────────

def _render_smtp_config():
    st.subheader("SMTP Configuration")
    try:
        from email_engine import EmailCredentialManager
        ecm = EmailCredentialManager()
        creds = ecm.load_credentials()

        c1, c2 = st.columns(2)
        with c1:
            smtp_host = st.text_input("SMTP Host", value=creds.get("smtp_host", "smtp.gmail.com"), key="es_smtp_host")
            smtp_port = st.number_input("SMTP Port", value=int(creds.get("smtp_port", 587)), key="es_smtp_port")
            smtp_user = st.text_input("Username / Email", value=creds.get("username", ""), key="es_smtp_user")
        with c2:
            smtp_pass = st.text_input("Password / App Password", type="password", key="es_smtp_pass")
            smtp_from = st.text_input("From Name", value=creds.get("from_name", "PPS Anantam"), key="es_smtp_from")
            smtp_from_email = st.text_input("From Email", value=creds.get("from_email", ""), key="es_smtp_from_email")

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("Save & Test SMTP", type="primary", key="es_save_smtp"):
                ecm.save_credentials(smtp_host, int(smtp_port), smtp_user, smtp_pass, smtp_from, smtp_from_email)
                st.success("SMTP credentials saved.")
                test_ok, test_msg = ecm.test_connection()
                if test_ok:
                    st.success(f"Connection test passed: {test_msg}")
                else:
                    st.error(f"Connection test failed: {test_msg}")

        # Status card
        st.markdown("---")
        from settings_engine import get as gs
        enabled = gs("email_enabled", False)
        status_color = GREEN if enabled else "#dc2626"
        status_text = "ENABLED" if enabled else "DISABLED"
        st.markdown(f"""
        <div style="background:#0d1b2e;border-left:4px solid {status_color};padding:12px 16px;
                    border-radius:0 8px 8px 0;margin-top:8px;">
          <span style="color:{status_color};font-weight:700;">{status_text}</span>
          <span style="color:#94a3b8;font-size:0.85rem;"> — Toggle in Settings page</span>
        </div>
        """, unsafe_allow_html=True)

    except ImportError:
        st.error("email_engine module not available.")


# ── Tab 2: Recipient Lists ───────────────────────────────────────────────────

def _render_recipient_lists():
    st.subheader("Recipient Lists")
    try:
        from database import get_recipient_lists, insert_recipient_list, update_recipient_list, delete_recipient_list

        lists = get_recipient_lists()
        if lists:
            for rl in lists:
                with st.expander(f"📋 {rl['list_name']} ({rl.get('list_type', 'email')})"):
                    try:
                        recips = json.loads(rl.get("recipients", "[]"))
                    except (json.JSONDecodeError, TypeError):
                        recips = []
                    if recips:
                        df = pd.DataFrame(recips)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No recipients in this list.")

                    dc1, dc2 = st.columns(2)
                    with dc1:
                        # Add recipient to this list
                        new_name = st.text_input("Name", key=f"rl_add_name_{rl['id']}")
                        new_email = st.text_input("Email", key=f"rl_add_email_{rl['id']}")
                        new_wa = st.text_input("WhatsApp", key=f"rl_add_wa_{rl['id']}")
                        if st.button("Add Recipient", key=f"rl_add_btn_{rl['id']}"):
                            if new_name and (new_email or new_wa):
                                recips.append({"name": new_name, "email": new_email, "whatsapp": new_wa})
                                update_recipient_list(rl["id"], {"recipients": json.dumps(recips)})
                                st.success(f"Added {new_name}.")
                                st.rerun()
                    with dc2:
                        if st.button("Delete List", key=f"rl_del_{rl['id']}", type="secondary"):
                            delete_recipient_list(rl["id"])
                            st.success(f"List '{rl['list_name']}' deleted.")
                            st.rerun()
        else:
            st.info("No recipient lists created yet.")

        st.markdown("---")
        st.markdown("**Create New List**")
        nc1, nc2 = st.columns(2)
        with nc1:
            new_list_name = st.text_input("List Name", key="rl_new_name", placeholder="e.g. Director, Internal Team")
        with nc2:
            new_list_type = st.selectbox("Type", ["email", "whatsapp", "both"], key="rl_new_type")
        if st.button("Create List", type="primary", key="rl_create_btn"):
            if new_list_name:
                insert_recipient_list({
                    "list_name": new_list_name.strip(),
                    "list_type": new_list_type,
                    "recipients": "[]",
                    "created_by": "admin",
                })
                st.success(f"List '{new_list_name}' created.")
                st.rerun()
            else:
                st.warning("Enter a list name.")

    except ImportError:
        st.error("database module not available.")


# ── Tab 3: Send Email ─────────────────────────────────────────────────────────

def _render_send_email():
    st.subheader("Compose & Queue Email")
    try:
        from email_engine import EmailEngine
        ee = EmailEngine()

        c1, c2 = st.columns(2)
        with c1:
            to_email = st.text_input("To Email", key="es_send_to")
            subject = st.text_input("Subject", key="es_send_subj")
        with c2:
            email_type = st.selectbox(
                "Email Type",
                ["offer", "followup", "reactivation", "payment_reminder", "report", "custom"],
                key="es_send_type",
            )
            cc = st.text_input("CC (optional)", key="es_send_cc")

        body = st.text_area("Body (HTML supported)", height=200, key="es_send_body")

        if st.button("Queue Email", type="primary", key="es_send_btn"):
            if to_email and subject and body:
                qid = ee.queue_email(to_email, subject, body, email_type=email_type, cc=cc or None)
                st.success(f"Email queued (ID: {qid}). Will be sent in next processing cycle.")
            else:
                st.warning("Fill To, Subject, and Body.")

    except ImportError:
        st.error("email_engine module not available.")


# ── Tab 4: Delivery Log ──────────────────────────────────────────────────────

def _render_delivery_log():
    st.subheader("Email Delivery Log")
    try:
        from database import get_email_queue

        c1, c2 = st.columns(2)
        with c1:
            status_filter = st.selectbox(
                "Filter by status",
                ["all", "pending", "draft", "sent", "failed"],
                key="es_log_status",
            )
        with c2:
            limit = st.number_input("Show last", value=50, min_value=10, max_value=500, key="es_log_limit")

        queue = get_email_queue(
            status=None if status_filter == "all" else status_filter,
            limit=int(limit),
        )
        if queue:
            df = pd.DataFrame(queue)
            display_cols = [
                c for c in ["id", "to_email", "subject", "email_type", "status", "created_at", "sent_at", "retry_count"]
                if c in df.columns
            ]
            st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

            # Stats
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Total", len(queue))
            sc2.metric("Sent", sum(1 for q in queue if q.get("status") == "sent"))
            sc3.metric("Failed", sum(1 for q in queue if q.get("status") == "failed"))
            sc4.metric("Pending", sum(1 for q in queue if q.get("status") == "pending"))

            # Export log
            if st.button("Export Log as CSV", key="es_log_export"):
                import csv
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=display_cols or list(queue[0].keys()))
                writer.writeheader()
                for row in queue:
                    writer.writerow({k: row.get(k, "") for k in (display_cols or list(row.keys()))})
                st.download_button(
                    "📥 Download CSV",
                    data=output.getvalue().encode("utf-8-sig"),
                    file_name="email_log.csv",
                    mime="text/csv",
                    key="es_log_dl",
                )
        else:
            st.info("No emails in queue.")

    except ImportError:
        st.error("database module not available.")


# ── Tab 5: Schedule ───────────────────────────────────────────────────────────

def _render_schedule():
    st.subheader("Scheduled Reports")
    try:
        from settings_engine import load_settings, save_settings
        sett = load_settings()

        st.markdown("**Daily Director Report**")
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            sett["email_director_report_enabled"] = st.toggle(
                "Enable Daily Report", value=sett.get("email_director_report_enabled", False),
                key="es_sched_dir_en",
            )
        with dc2:
            sett["email_director_report_time"] = st.text_input(
                "Time (HH:MM IST)", value=sett.get("email_director_report_time", "08:30"),
                key="es_sched_dir_time",
            )
        with dc3:
            sett["email_director_report_to"] = st.text_input(
                "Recipient Email", value=sett.get("email_director_report_to", ""),
                key="es_sched_dir_to",
            )

        st.markdown("---")
        st.markdown("**Weekly Summary Report**")
        wc1, wc2, wc3, wc4 = st.columns(4)
        with wc1:
            sett["email_weekly_summary_enabled"] = st.toggle(
                "Enable Weekly Summary", value=sett.get("email_weekly_summary_enabled", False),
                key="es_sched_wk_en",
            )
        with wc2:
            sett["email_weekly_summary_day"] = st.selectbox(
                "Day",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(
                    sett.get("email_weekly_summary_day", "Monday")
                ),
                key="es_sched_wk_day",
            )
        with wc3:
            sett["email_weekly_summary_time"] = st.text_input(
                "Time (HH:MM IST)", value=sett.get("email_weekly_summary_time", "09:00"),
                key="es_sched_wk_time",
            )
        with wc4:
            sett["email_weekly_summary_to"] = st.text_input(
                "Recipient", value=sett.get("email_weekly_summary_to", ""),
                key="es_sched_wk_to",
            )

        st.markdown("---")
        if st.button("Save Schedule Settings", type="primary", key="es_sched_save"):
            save_settings(sett)
            st.success("Schedule settings saved.")

    except ImportError:
        st.error("settings_engine module not available.")
