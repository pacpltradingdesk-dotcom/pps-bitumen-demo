"""
Integrations & Connection Settings Dashboard
=============================================
Consolidated 7-tab dashboard for all external service integrations:
  1. Email (SMTP) — reuses email_setup_dashboard
  2. WhatsApp (360dialog) — reuses whatsapp_setup_dashboard
  3. Google Sheets / Excel — new
  4. Dashboard Sharing — new (share links)
  5. Client Chat — new
  6. Share Automation — new (scheduled sends)
  7. Connection Status — overview of all integrations
"""

import streamlit as st
import sys
import os
import json
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui_badges import display_badge

IST = timezone(timedelta(hours=5, minutes=30))


def render():
    display_badge("settings")
    st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
padding: 20px 25px; border-radius: 12px; margin-bottom: 20px;
box-shadow: 0 10px 30px rgba(15, 23, 42, 0.4);">
<div style="display:flex; align-items:center; gap:15px;">
<span style="font-size:2rem;">🔗</span>
<div>
<div style="font-size:1.3rem; font-weight:800; color:#e0e0e0;">
Integrations & Connection Settings
</div>
<div style="font-size:0.75rem; color:#94a3b8; letter-spacing:1px; text-transform:uppercase;">
Email • WhatsApp • Google Sheets • Sharing • Chat • Automation
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📧 Email (SMTP)",
        "📱 WhatsApp",
        "📊 Google Sheets",
        "🔗 Dashboard Sharing",
        "💬 Client Chat",
        "⏰ Share Automation",
        "🟢 Connection Status",
    ])

    with tab1:
        _render_email_tab()
    with tab2:
        _render_whatsapp_tab()
    with tab3:
        _render_google_sheets_tab()
    with tab4:
        _render_dashboard_sharing_tab()
    with tab5:
        _render_client_chat_tab()
    with tab6:
        _render_share_automation_tab()
    with tab7:
        _render_connection_status_tab()


# ── Tab 1: Email (SMTP) ─────────────────────────────────────────────────────

def _render_email_tab():
    st.markdown("### 📧 Email SMTP Configuration")
    st.caption("Configure SMTP server for sending emails, reports, and notifications.")

    try:
        from command_intel.email_setup_dashboard import render as render_email
        render_email()
    except Exception as e:
        st.warning(f"Email setup module not available: {e}")
        _render_email_fallback()


def _render_email_fallback():
    """Fallback email config if email_setup_dashboard fails."""
    from settings_engine import load_settings, save_settings
    settings = load_settings()

    col1, col2 = st.columns(2)
    with col1:
        enabled = st.toggle("Email Enabled", value=settings.get("email_enabled", False), key="_int_email_on")
        if enabled != settings.get("email_enabled"):
            settings["email_enabled"] = enabled
            save_settings(settings)
            st.rerun()
    with col2:
        rate = st.number_input("Rate Limit / Hour", value=settings.get("email_rate_limit_per_hour", 50),
                               min_value=1, max_value=500, key="_int_email_rate")
        if rate != settings.get("email_rate_limit_per_hour"):
            settings["email_rate_limit_per_hour"] = rate
            save_settings(settings)


# ── Tab 2: WhatsApp ──────────────────────────────────────────────────────────

def _render_whatsapp_tab():
    st.markdown("### 📱 WhatsApp Configuration")
    st.caption("Configure 360dialog API for WhatsApp Business messaging.")

    try:
        from command_intel.whatsapp_setup_dashboard import render as render_wa
        render_wa()
    except Exception as e:
        st.warning(f"WhatsApp setup module not available: {e}")
        _render_whatsapp_fallback()


def _render_whatsapp_fallback():
    """Fallback WhatsApp config."""
    from settings_engine import load_settings, save_settings
    settings = load_settings()

    enabled = st.toggle("WhatsApp Enabled", value=settings.get("whatsapp_enabled", False), key="_int_wa_on")
    if enabled != settings.get("whatsapp_enabled"):
        settings["whatsapp_enabled"] = enabled
        save_settings(settings)
        st.rerun()


# ── Tab 3: Google Sheets ─────────────────────────────────────────────────────

def _render_google_sheets_tab():
    st.markdown("### 📊 Google Sheets / Excel Data Link")
    st.caption("Connect Google Sheets to sync external data into your dashboard.")

    from settings_engine import load_settings, save_settings
    settings = load_settings()

    # Enable toggle
    enabled = st.toggle(
        "Google Sheets Integration Enabled",
        value=settings.get("google_sheets_enabled", False),
        key="_int_gs_enabled",
    )
    if enabled != settings.get("google_sheets_enabled"):
        settings["google_sheets_enabled"] = enabled
        save_settings(settings)
        st.rerun()

    if not enabled:
        st.info("Enable Google Sheets integration to connect external spreadsheets.")
        return

    # Service account upload
    st.markdown("#### Service Account Key")
    st.caption("Upload the JSON key file from Google Cloud Console → IAM → Service Accounts")

    uploaded = st.file_uploader(
        "Upload Service Account JSON",
        type=["json"],
        key="_int_gs_upload",
    )
    if uploaded:
        try:
            sa_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_sa_key.json")
            with open(sa_path, "wb") as f:
                f.write(uploaded.getvalue())
            settings["google_sheets_service_account_path"] = sa_path
            save_settings(settings)
            st.success(f"Service account key saved.")
        except Exception as e:
            st.error(f"Failed to save key: {e}")

    sa_path = settings.get("google_sheets_service_account_path", "")
    if sa_path and os.path.exists(sa_path):
        st.success(f"Service account key: {os.path.basename(sa_path)}")

        # Test connection
        if st.button("🔌 Test Connection", key="_int_gs_test"):
            try:
                from google_sheets_engine import GoogleSheetsEngine
                engine = GoogleSheetsEngine()
                ok, msg = engine.test_connection()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            except Exception as e:
                st.error(f"Test failed: {e}")
    else:
        st.warning("No service account key configured. Upload the JSON file above.")

    st.markdown("---")

    # Linked sheets
    st.markdown("#### Linked Sheets")

    try:
        from google_sheets_engine import GoogleSheetsEngine
        engine = GoogleSheetsEngine()
        sheets = engine.get_linked_sheets()
    except Exception:
        sheets = []

    if sheets:
        for s in sheets:
            if not s.get("is_active", True):
                continue
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{s.get('name', 'Untitled')}**")
                st.caption(f"Mode: {s.get('sync_mode', 'manual')} | Last: {s.get('last_sync', 'Never')} | Rows: {s.get('rows_synced', 0)}")
            with col2:
                status_color = "#22c55e" if s.get("last_status") == "success" else "#f59e0b"
                st.markdown(f'<span style="color:{status_color};">●</span> {s.get("last_status", "never")}', unsafe_allow_html=True)
            with col3:
                if st.button("🔄 Sync", key=f"_gs_sync_{s.get('id')}"):
                    result = engine.sync_sheet_to_json(s["url"], s["output_file"], s.get("worksheet"))
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])
                    st.rerun()

    # Add new sheet link
    with st.expander("➕ Link New Sheet", expanded=not sheets):
        gs_name = st.text_input("Sheet Name", placeholder="e.g., Supplier Prices", key="_gs_new_name")
        gs_url = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...", key="_gs_new_url")
        gs_output = st.text_input("Output JSON File", value="linked_sheet_data.json", key="_gs_new_output")
        gs_worksheet = st.text_input("Worksheet Name (blank = first sheet)", key="_gs_new_ws")
        gs_mode = st.selectbox("Sync Mode", ["manual", "auto"], key="_gs_new_mode")
        gs_refresh = st.selectbox("Refresh Interval", [15, 30, 60, 360, 1440], format_func=lambda x: f"{x} minutes", key="_gs_new_refresh")

        if st.button("🔗 Link Sheet", key="_gs_new_link") and gs_name and gs_url:
            try:
                from google_sheets_engine import GoogleSheetsEngine
                eng = GoogleSheetsEngine()
                eng.add_sheet_link(gs_name, gs_url, gs_output, gs_mode, gs_refresh, gs_worksheet or None)
                st.success(f"Sheet '{gs_name}' linked successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to link sheet: {e}")


# ── Tab 4: Dashboard Sharing ─────────────────────────────────────────────────

def _render_dashboard_sharing_tab():
    st.markdown("### 🔗 Dashboard Access & Link Sharing")
    st.caption("Generate shareable links with permissions, expiry, and usage tracking.")

    from settings_engine import load_settings, save_settings
    settings = load_settings()

    enabled = st.toggle(
        "Share Links Enabled",
        value=settings.get("share_links_enabled", True),
        key="_int_sl_enabled",
    )
    if enabled != settings.get("share_links_enabled"):
        settings["share_links_enabled"] = enabled
        save_settings(settings)

    if not enabled:
        st.info("Enable share links to generate shareable dashboard URLs.")
        return

    col1, col2 = st.columns(2)
    with col1:
        expiry = st.number_input(
            "Default Expiry (hours)",
            value=settings.get("share_links_default_expiry_hours", 48),
            min_value=1, max_value=720,
            key="_int_sl_expiry",
        )
        if expiry != settings.get("share_links_default_expiry_hours"):
            settings["share_links_default_expiry_hours"] = expiry
            save_settings(settings)
    with col2:
        require_pwd = st.toggle(
            "Require Password",
            value=settings.get("share_links_require_password", False),
            key="_int_sl_pwd",
        )
        if require_pwd != settings.get("share_links_require_password"):
            settings["share_links_require_password"] = require_pwd
            save_settings(settings)

    st.markdown("---")

    # Active links
    st.markdown("#### Active Share Links")
    try:
        from database import get_all_share_links
        links = get_all_share_links(active_only=True)
    except Exception:
        links = []

    if links:
        for link in links:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"**{link.get('page_name', 'Unknown')}**")
                st.caption(f"Token: `{link.get('link_token', '')}`")
            with col2:
                st.metric("Views", link.get("view_count", 0))
            with col3:
                exp = link.get("expires_at", "")
                now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
                if exp and exp < now:
                    st.markdown('<span style="color:#ef4444;">Expired</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="color:#22c55e;">Active</span>', unsafe_allow_html=True)
            with col4:
                if st.button("🗑️", key=f"_sl_deact_{link['id']}"):
                    from database import deactivate_share_link
                    deactivate_share_link(link["id"])
                    st.rerun()
    else:
        st.caption("No active share links. Use the Share button on any page to generate one.")


# ── Tab 5: Client Chat ───────────────────────────────────────────────────────

def _render_client_chat_tab():
    st.markdown("### 💬 Client Chat System")
    st.caption("Direct messaging with clients. Messages stored locally in SQLite.")

    from settings_engine import load_settings, save_settings
    settings = load_settings()

    enabled = st.toggle(
        "Client Chat Enabled",
        value=settings.get("chat_enabled", False),
        key="_int_chat_enabled",
    )
    if enabled != settings.get("chat_enabled"):
        settings["chat_enabled"] = enabled
        save_settings(settings)
        st.rerun()

    if not enabled:
        st.info("Enable Client Chat to start messaging with customers directly from the dashboard.")
        return

    # Chat settings
    col1, col2 = st.columns(2)
    with col1:
        max_len = st.number_input(
            "Max Message Length",
            value=settings.get("chat_max_message_length", 2000),
            min_value=100, max_value=10000,
            key="_int_chat_maxlen",
        )
        if max_len != settings.get("chat_max_message_length"):
            settings["chat_max_message_length"] = max_len
            save_settings(settings)

    st.markdown("---")

    # Render chat panel
    try:
        from chat_engine import render_chat_panel
        render_chat_panel()
    except Exception as e:
        st.error(f"Chat engine failed to load: {e}")


# ── Tab 6: Share Automation ──────────────────────────────────────────────────

def _render_share_automation_tab():
    st.markdown("### ⏰ Share Automation — Scheduled Sends")
    st.caption("Set up daily, weekly, or monthly automated report sharing via Email/WhatsApp.")

    from settings_engine import load_settings, save_settings
    settings = load_settings()

    enabled = st.toggle(
        "Share Automation Enabled",
        value=settings.get("share_automation_enabled", False),
        key="_int_sa_enabled",
    )
    if enabled != settings.get("share_automation_enabled"):
        settings["share_automation_enabled"] = enabled
        save_settings(settings)

    if not enabled:
        st.info("Enable Share Automation to schedule recurring report sends.")
        return

    # Existing schedules
    try:
        from share_automation_engine import ShareAutomationEngine
        engine = ShareAutomationEngine()
        schedules = engine.get_schedules()
    except Exception:
        schedules = []

    if schedules:
        st.markdown("#### Active Schedules")
        for s in schedules:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"**{s.get('schedule_name', 'Untitled')}**")
                rcpt = s.get("recipients", [])
                st.caption(f"{s.get('page_name', '')} → {s.get('channel', '')} | {s.get('frequency', '')} at {s.get('time_ist', '')} | {len(rcpt)} recipients")
            with col2:
                st.metric("Runs", s.get("run_count", 0))
            with col3:
                st.caption(f"Next: {s.get('next_run', 'N/A')}")
            with col4:
                if st.button("🗑️", key=f"_sa_del_{s['id']}"):
                    engine.delete_schedule(s["id"])
                    st.rerun()

    st.markdown("---")

    # Create new schedule
    with st.expander("➕ Create New Schedule", expanded=not schedules):
        sa_name = st.text_input("Schedule Name", placeholder="e.g., Daily Director Report", key="_sa_new_name")
        sa_page = st.text_input("Page/Section Name", placeholder="e.g., Director Briefing", key="_sa_new_page")
        sa_channel = st.selectbox("Channel", ["email", "whatsapp", "both"], key="_sa_new_ch")
        sa_freq = st.selectbox("Frequency", ["daily", "weekly", "monthly"], key="_sa_new_freq")
        sa_time = st.text_input("Time (IST, HH:MM)", value="09:00", key="_sa_new_time")

        sa_dow = None
        sa_dom = None
        if sa_freq == "weekly":
            sa_dow = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="_sa_new_dow")
        elif sa_freq == "monthly":
            sa_dom = st.number_input("Day of Month", value=1, min_value=1, max_value=28, key="_sa_new_dom")

        sa_content = st.selectbox("Content Type", ["pdf", "summary"], key="_sa_new_content")

        # Recipients
        st.markdown("**Recipients:**")
        from recipient_selector import render_recipient_selector
        sa_recipients = render_recipient_selector("_sa_new", channel="email" if sa_channel != "whatsapp" else "whatsapp")

        if st.button("✅ Create Schedule", key="_sa_new_create") and sa_name and sa_page:
            if not sa_recipients:
                st.error("Please select at least one recipient.")
            else:
                try:
                    from share_automation_engine import ShareAutomationEngine
                    eng = ShareAutomationEngine()
                    eng.create_schedule(
                        sa_name, sa_page, sa_channel, sa_recipients,
                        sa_freq, sa_time, sa_content, sa_dow, sa_dom,
                    )
                    st.success(f"Schedule '{sa_name}' created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")


# ── Tab 7: Connection Status ─────────────────────────────────────────────────

def _render_connection_status_tab():
    st.markdown("### 🟢 Connection Status — All Integrations")

    from settings_engine import load_settings
    settings = load_settings()

    integrations = [
        {
            "name": "Email (SMTP)",
            "icon": "📧",
            "enabled_key": "email_enabled",
            "test_fn": _test_email,
        },
        {
            "name": "WhatsApp (360dialog)",
            "icon": "📱",
            "enabled_key": "whatsapp_enabled",
            "test_fn": _test_whatsapp,
        },
        {
            "name": "Google Sheets",
            "icon": "📊",
            "enabled_key": "google_sheets_enabled",
            "test_fn": _test_google_sheets,
        },
        {
            "name": "Share Links",
            "icon": "🔗",
            "enabled_key": "share_links_enabled",
            "test_fn": None,
        },
        {
            "name": "Client Chat",
            "icon": "💬",
            "enabled_key": "chat_enabled",
            "test_fn": None,
        },
        {
            "name": "Share Automation",
            "icon": "⏰",
            "enabled_key": "share_automation_enabled",
            "test_fn": None,
        },
    ]

    cols = st.columns(3)
    for i, intg in enumerate(integrations):
        with cols[i % 3]:
            enabled = settings.get(intg["enabled_key"], False)
            status_color = "#22c55e" if enabled else "#94a3b8"
            status_label = "Enabled" if enabled else "Disabled"
            status_dot = "🟢" if enabled else "⚫"

            st.markdown(f"""
<div style="background:white; border-radius:10px; padding:16px;
border-left:4px solid {status_color}; box-shadow:0 2px 8px rgba(0,0,0,0.06);
margin-bottom:12px; min-height:120px;">
<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
<span style="font-size:1.3rem;">{intg['icon']}</span>
<span style="font-weight:700; font-size:0.9rem; color:#1e293b;">{intg['name']}</span>
</div>
<div style="font-size:0.8rem; color:{status_color}; font-weight:600;">
{status_dot} {status_label}
</div>
</div>
""", unsafe_allow_html=True)

            if intg.get("test_fn") and enabled:
                if st.button(f"🔌 Test", key=f"_cs_test_{intg['enabled_key']}"):
                    ok, msg = intg["test_fn"]()
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    # Stats
    st.markdown("---")
    st.markdown("#### Quick Stats")
    col1, col2, col3 = st.columns(3)
    try:
        from database import get_all_share_links, get_share_schedules
        with col1:
            links = get_all_share_links(active_only=True)
            st.metric("Active Share Links", len(links))
        with col2:
            scheds = get_share_schedules(active_only=True)
            st.metric("Active Schedules", len(scheds))
        with col3:
            from database import get_comm_stats
            stats = get_comm_stats(days=7)
            st.metric("Messages (7 days)", stats.get("total", 0))
    except Exception:
        st.caption("Stats unavailable.")


def _test_email() -> tuple:
    try:
        from email_engine import EmailCredentialManager
        creds = EmailCredentialManager()
        if creds.get_credentials():
            return True, "SMTP credentials configured."
        return False, "No SMTP credentials found."
    except Exception as e:
        return False, str(e)


def _test_whatsapp() -> tuple:
    try:
        from whatsapp_engine import WhatsAppCredentialManager
        creds = WhatsAppCredentialManager()
        if creds.get_credentials():
            return True, "WhatsApp API credentials configured."
        return False, "No WhatsApp credentials found."
    except Exception as e:
        return False, str(e)


def _test_google_sheets() -> tuple:
    try:
        from google_sheets_engine import GoogleSheetsEngine
        engine = GoogleSheetsEngine()
        return engine.test_connection()
    except Exception as e:
        return False, str(e)
