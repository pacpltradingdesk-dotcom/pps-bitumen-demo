"""
whatsapp_setup_dashboard.py — Full WhatsApp Configuration UI
==============================================================
Replaces the inline WhatsApp Engine page block in dashboard.py.
6 tabs: API Config | Templates | Send Message | Delivery Log | Opt-In | Rate Limits
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


def render():
    """Main render function for WhatsApp Setup page."""
    from ui_badges import display_badge
    display_badge("real-time")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{GREEN},#1a4731);padding:18px 24px;
                border-radius:10px;margin-bottom:16px;">
      <div style="font-size:1.2rem;font-weight:700;color:#ffffff;">💬 WhatsApp Engine Setup</div>
      <div style="font-size:0.8rem;color:{GOLD};margin-top:4px;">
        360dialog API configuration, templates, delivery logs, and opt-in management
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "API Config", "Templates", "Send Message",
        "Delivery Log", "Opt-In Management", "Rate Limits",
    ])

    with tab1:
        _render_api_config()
    with tab2:
        _render_templates()
    with tab3:
        _render_send_message()
    with tab4:
        _render_delivery_log()
    with tab5:
        _render_opt_in()
    with tab6:
        _render_rate_limits()


# ── Tab 1: API Configuration ─────────────────────────────────────────────────

def _render_api_config():
    st.subheader("360dialog API Configuration")
    try:
        from whatsapp_engine import WhatsAppCredentialManager
        wcm = WhatsAppCredentialManager()
        creds = wcm.load_credentials()

        c1, c2 = st.columns(2)
        with c1:
            api_key = st.text_input(
                "360dialog API Key", value=creds.get("api_key", ""),
                type="password", key="ws_api_key",
            )
            st.text_input(
                "API Base URL",
                value=creds.get("api_base_url", "https://waba.360dialog.io/v1"),
                key="ws_api_url",
                disabled=True,
            )
        with c2:
            phone_id = st.text_input(
                "Phone Number ID", value=creds.get("phone_number_id", ""),
                key="ws_phone_id",
            )
            st.markdown("**Webhook URL**")
            st.code("https://your-domain.com/webhook/whatsapp", language=None)

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("Save & Test Connection", type="primary", key="ws_save_api"):
                wcm.save_credentials(api_key, phone_id, webhook_url="", business_name="PPS Anantam")
                st.success("WhatsApp credentials saved.")
                test_ok, test_msg = wcm.test_connection()
                if test_ok:
                    st.success(f"Connection test passed: {test_msg}")
                else:
                    st.error(f"Connection test failed: {test_msg}")

        # Status card
        st.markdown("---")
        from settings_engine import get as gs
        enabled = gs("whatsapp_enabled", False)
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
        st.error("whatsapp_engine module not available.")


# ── Tab 2: Templates ─────────────────────────────────────────────────────────

def _render_templates():
    st.subheader("WhatsApp Message Templates")
    try:
        from whatsapp_engine import WhatsAppTemplateManager
        wtm = WhatsAppTemplateManager()
        templates = wtm.load_templates()

        if templates:
            for tname, tdata in templates.items():
                with st.expander(f"📝 {tname} ({tdata.get('language', 'en')})"):
                    tc1, tc2 = st.columns(2)
                    with tc1:
                        st.write(f"**Namespace:** {tdata.get('namespace', 'N/A')}")
                        st.write(f"**Business Action:** {tdata.get('business_action', 'N/A')}")
                    with tc2:
                        params = tdata.get("parameters", [])
                        st.write(f"**Parameters:** {', '.join(params) if params else 'None'}")
                        st.write(f"**Status:** Approved")
        else:
            st.info("No templates registered. Configure templates in WhatsApp Business Manager.")

        st.caption("Templates are managed via 360dialog WhatsApp Business Manager portal.")

    except ImportError:
        st.error("whatsapp_engine module not available.")


# ── Tab 3: Send Message ──────────────────────────────────────────────────────

def _render_send_message():
    st.subheader("Send WhatsApp Message")
    try:
        from whatsapp_engine import WhatsAppEngine
        we = WhatsAppEngine()

        to_number = st.text_input(
            "Phone Number (Indian mobile)", placeholder="9876543210", key="ws_send_to",
        )

        mode = st.radio("Mode", ["Template Message", "Session Text"], horizontal=True, key="ws_send_mode")

        if mode == "Template Message":
            try:
                from whatsapp_engine import WhatsAppTemplateManager
                wtm = WhatsAppTemplateManager()
                tmpl_names = list(wtm.load_templates().keys())
            except Exception:
                tmpl_names = ["bitumen_offer_v1", "bitumen_followup_v1", "payment_reminder_v1", "price_drop_alert_v1"]

            tmpl = st.selectbox("Template", tmpl_names, key="ws_send_tmpl")
            params_str = st.text_input("Parameters (comma-separated)", key="ws_send_params")

            if st.button("Queue Template Message", type="primary", key="ws_send_tmpl_btn"):
                if to_number:
                    params = [p.strip() for p in params_str.split(",") if p.strip()] if params_str else []
                    qid = we.queue_message(to_number, "template", template_name=tmpl, template_params=params)
                    st.success(f"Template message queued (ID: {qid})")
                else:
                    st.warning("Enter a phone number.")
        else:
            text = st.text_area("Message Text", height=150, key="ws_send_text")
            if st.button("Queue Session Message", type="primary", key="ws_send_sess_btn"):
                if to_number and text:
                    qid = we.queue_message(to_number, "session", session_text=text)
                    st.success(f"Session message queued (ID: {qid})")
                else:
                    st.warning("Enter phone number and message text.")

    except ImportError:
        st.error("whatsapp_engine module not available.")


# ── Tab 4: Delivery Log ──────────────────────────────────────────────────────

def _render_delivery_log():
    st.subheader("WhatsApp Delivery Log")
    try:
        from database import get_wa_queue

        c1, c2 = st.columns(2)
        with c1:
            status_filter = st.selectbox(
                "Filter by status",
                ["all", "pending", "sent", "delivered", "read", "failed"],
                key="ws_log_status",
            )
        with c2:
            limit = st.number_input("Show last", value=50, min_value=10, max_value=500, key="ws_log_limit")

        queue = get_wa_queue(
            status=None if status_filter == "all" else status_filter,
            limit=int(limit),
        )
        if queue:
            df = pd.DataFrame(queue)
            display_cols = [
                c for c in ["id", "to_number", "message_type", "template_name", "status",
                            "created_at", "sent_at", "wa_message_id", "retry_count"]
                if c in df.columns
            ]
            st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

            # Stats
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Total", len(queue))
            sc2.metric("Delivered", sum(1 for q in queue if q.get("status") == "delivered"))
            sc3.metric("Read", sum(1 for q in queue if q.get("status") == "read"))
            sc4.metric("Failed", sum(1 for q in queue if q.get("status") == "failed"))

            # Export
            if st.button("Export Log as CSV", key="ws_log_export"):
                import csv, io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=display_cols or list(queue[0].keys()))
                writer.writeheader()
                for row in queue:
                    writer.writerow({k: row.get(k, "") for k in (display_cols or list(row.keys()))})
                st.download_button(
                    "📥 Download CSV",
                    data=output.getvalue().encode("utf-8-sig"),
                    file_name="whatsapp_log.csv",
                    mime="text/csv",
                    key="ws_log_dl",
                )
        else:
            st.info("No messages in queue.")

    except ImportError:
        st.error("database module not available.")


# ── Tab 5: Opt-In Management ─────────────────────────────────────────────────

def _render_opt_in():
    st.subheader("WhatsApp Opt-In Management")
    st.info("Manage phone numbers that have opted in to receive WhatsApp messages. "
            "Required for compliance with WhatsApp Business Policy.")

    # Store opt-in in session state for now (can migrate to DB later)
    if "_wa_opt_in_list" not in st.session_state:
        st.session_state["_wa_opt_in_list"] = []

    opt_in_list = st.session_state["_wa_opt_in_list"]

    # Display current list
    if opt_in_list:
        df = pd.DataFrame(opt_in_list)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No opted-in numbers registered.")

    # Add number
    st.markdown("**Add Opt-In Number**")
    oc1, oc2 = st.columns(2)
    with oc1:
        opt_name = st.text_input("Contact Name", key="ws_optin_name")
    with oc2:
        opt_phone = st.text_input("Phone Number", key="ws_optin_phone", placeholder="9876543210")

    if st.button("Add to Opt-In List", type="primary", key="ws_optin_add"):
        if opt_name and opt_phone:
            opt_in_list.append({
                "name": opt_name,
                "phone": opt_phone,
                "opted_in_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
            })
            st.session_state["_wa_opt_in_list"] = opt_in_list
            st.success(f"Added {opt_name} ({opt_phone}) to opt-in list.")
            st.rerun()
        else:
            st.warning("Enter name and phone number.")


# ── Tab 6: Rate Limits ───────────────────────────────────────────────────────

def _render_rate_limits():
    st.subheader("WhatsApp Rate Limits")
    try:
        from settings_engine import load_settings, save_settings
        sett = load_settings()

        c1, c2 = st.columns(2)
        with c1:
            sett["whatsapp_rate_limit_per_minute"] = st.number_input(
                "Max messages per minute",
                value=sett.get("whatsapp_rate_limit_per_minute", 20),
                min_value=1, max_value=100,
                key="ws_rate_min",
            )
        with c2:
            sett["whatsapp_rate_limit_per_day"] = st.number_input(
                "Max messages per day",
                value=sett.get("whatsapp_rate_limit_per_day", 1000),
                min_value=10, max_value=10000,
                key="ws_rate_day",
            )

        sett["whatsapp_session_message_enabled"] = st.toggle(
            "Allow session messages (within 24h window)",
            value=sett.get("whatsapp_session_message_enabled", True),
            key="ws_rate_session",
        )

        # Current usage (from queue)
        st.markdown("---")
        st.markdown("**Current Usage**")
        try:
            from database import get_wa_queue
            today_sent = [
                q for q in get_wa_queue(status="sent", limit=10000)
                if q.get("sent_at", "").startswith(datetime.now(IST).strftime("%Y-%m-%d"))
            ]
            uc1, uc2 = st.columns(2)
            uc1.metric("Sent Today", len(today_sent))
            uc2.metric("Remaining Today", max(0, sett.get("whatsapp_rate_limit_per_day", 1000) - len(today_sent)))
        except Exception:
            st.caption("Unable to load usage stats.")

        if st.button("Save Rate Limit Settings", type="primary", key="ws_rate_save"):
            save_settings(sett)
            st.success("Rate limit settings saved.")

    except ImportError:
        st.error("settings_engine module not available.")
