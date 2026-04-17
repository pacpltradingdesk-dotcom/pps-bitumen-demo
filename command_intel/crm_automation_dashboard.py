"""
CRM Automation Dashboard — 6-Tab Streamlit Interface
=====================================================
Manages: Contacts, Daily Rotation, Festival Broadcasts,
Price Broadcasts, AI Auto-Reply, and Automation Settings.

PPS Anantam Capital Pvt Ltd — CRM Automation v1.0
"""

from __future__ import annotations

try:
    from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
except ImportError:
    import sys as _sys
    import os as _os
    _sys.path.append(_os.path.dirname(_os.path.dirname(__file__)))
    try:
        from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
    except Exception:
        pass

import datetime
import json
import streamlit as st


def render_crm_automation():
    """Main entry point for the CRM Automation dashboard page."""

    st.header("🤖 CRM Automation & Outreach")
    st.caption("Manage 24K contacts, daily rotation, festival broadcasts, price alerts, and AI auto-reply.")

    tabs = st.tabs([
        "👥 Contacts",
        "🔄 Daily Rotation",
        "🎉 Festival Broadcasts",
        "💰 Price Broadcasts",
        "🤖 AI Auto-Reply",
        "⚙️ Settings",
        "🧠 AI Providers",
    ])

    with tabs[0]:
        _render_contacts_tab()
    with tabs[1]:
        _render_rotation_tab()
    with tabs[2]:
        _render_festival_tab()
    with tabs[3]:
        _render_price_tab()
    with tabs[4]:
        _render_ai_reply_tab()
    with tabs[5]:
        _render_settings_tab()
    with tabs[6]:
        _render_ai_providers_tab()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: CONTACTS
# ══════════════════════════════════════════════════════════════════════════════


def _render_contacts_tab():
    """Contacts overview with search, filter, stats."""
    try:
        from database import get_contacts_count, get_all_contacts, search_contacts
    except ImportError:
        st.error("Database module not available. Run database initialization first.")
        return

    # Stats row
    counts = get_contacts_count()
    by_type = counts.get("by_type", {})
    cols = st.columns(5)
    cols[0].metric("Total Contacts", counts.get("total", 0))
    cols[1].metric("Customers", by_type.get("customer", 0))
    cols[2].metric("Prospects", by_type.get("prospect", 0))
    cols[3].metric("Suppliers", by_type.get("supplier", 0))
    cols[4].metric("WhatsApp Opted-In", counts.get("whatsapp_opted_in", 0))

    st.divider()

    # Search
    col1, col2, col3 = st.columns([3, 2, 2])
    search_term = col1.text_input("Search contacts", placeholder="Name, company, mobile, email...")
    category_filter = col2.selectbox("Category", ["All"] + _get_categories())
    tag_filter = col3.selectbox("Buyer/Seller", ["All", "buyer", "seller", "both", "unknown"])

    if search_term:
        results = search_contacts(search_term)
    else:
        results = get_all_contacts(active_only=True)

    # Apply filters
    if category_filter != "All":
        results = [c for c in results if c.get("category") == category_filter]
    if tag_filter != "All":
        results = [c for c in results if c.get("buyer_seller_tag") == tag_filter]

    st.write(f"Showing {len(results)} contacts")

    if results:
        # Display as dataframe
        import pandas as pd
        display_cols = ["name", "company_name", "category", "buyer_seller_tag",
                        "city", "state", "mobile1", "email", "last_contact_date"]
        rows = []
        for c in results[:100]:  # Limit display
            rows.append({col: c.get(col, "") for col in display_cols})
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

        if len(results) > 100:
            st.info(f"Showing first 100 of {len(results)} contacts. Use search to narrow down.")

    # Import button
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📥 Run Contact Migration", help="Migrate JSON contacts to SQLite"):
            with st.spinner("Migrating contacts..."):
                try:
                    from migrate_contacts_to_sqlite import main as run_migration
                    result = run_migration()
                    st.success(f"Migration complete: {result.get('total_migrated', 0)} migrated, "
                               f"{result.get('final_count', 0)} total contacts")
                except Exception as e:
                    st.error(f"Migration error: {e}")
    with col_b:
        st.caption("Use the Contact Importer page to bulk import from Excel/CSV/PDF.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: DAILY ROTATION
# ══════════════════════════════════════════════════════════════════════════════


def _render_rotation_tab():
    """Daily rotation progress, 10-day calendar, manual trigger."""
    try:
        from rotation_engine import (
            get_rotation_status, trigger_manual_rotation, ContactRotationEngine
        )
    except ImportError:
        st.error("Rotation engine not available.")
        return

    status = get_rotation_status()
    progress = status.get("progress", {})

    # Progress metrics
    cols = st.columns(5)
    cols[0].metric("Today's Target", status.get("daily_target", 2400))
    cols[1].metric("Sent", progress.get("sent", 0))
    cols[2].metric("Failed", progress.get("failed", 0))
    cols[3].metric("Pending", progress.get("pending", 0))
    cols[4].metric("Total Contacts", status.get("active_contacts", 0))

    # Progress bar
    target = status.get("daily_target", 2400)
    sent = progress.get("sent", 0)
    pct = min(sent / max(target, 1), 1.0)
    st.progress(pct, text=f"{sent}/{target} contacts reached ({pct*100:.0f}%)")

    # Status indicators
    settings = status.get("settings", {})
    col1, col2, col3 = st.columns(3)
    col1.write(f"**Rotation:** {'🟢 Enabled' if settings.get('rotation_enabled') else '🔴 Disabled'}")
    col2.write(f"**Festival:** {'🟢 Enabled' if settings.get('festival_enabled') else '🔴 Disabled'}")
    col3.write(f"**Scheduler:** {'🟢 Running' if status.get('scheduler_running') else '🔴 Stopped'}")

    st.divider()

    # Manual trigger
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶️ Trigger Manual Rotation", type="primary"):
            with st.spinner("Running rotation..."):
                result = trigger_manual_rotation()
                if result.get("status") == "completed":
                    r = result.get("result", {})
                    st.success(f"Rotation complete: sent={r.get('sent',0)} "
                               f"failed={r.get('failed',0)} skipped={r.get('skipped',0)}")
                else:
                    st.warning(result.get("message", "No contacts available"))
    with col_b:
        if st.button("🔁 Retry Failed"):
            with st.spinner("Retrying failed contacts..."):
                engine = ContactRotationEngine()
                result = engine.retry_failed()
                st.info(f"Retried: {result.get('retried', 0)} contacts")

    # 10-day history
    st.subheader("10-Day Rotation History")
    try:
        from database import get_rotation_stats
        history = []
        for i in range(10):
            date = (datetime.date.today() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            stats = get_rotation_stats(date)
            history.append({
                "Date": date,
                "Sent": stats.get("sent", 0),
                "Failed": stats.get("failed", 0),
                "Total": stats.get("total", 0),
            })
        import pandas as pd
        df = pd.DataFrame(history)
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        st.info("No rotation history available yet.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: FESTIVAL BROADCASTS
# ══════════════════════════════════════════════════════════════════════════════


def _render_festival_tab():
    """Festival broadcast management."""
    try:
        from rotation_engine import FestivalBroadcastEngine, trigger_manual_festival_broadcast
    except ImportError:
        st.error("Festival broadcast engine not available.")
        return

    engine = FestivalBroadcastEngine()

    # Upcoming festivals
    st.subheader("Upcoming Festivals (Next 30 Days)")
    upcoming = engine.get_upcoming_festivals(days_ahead=30)
    if upcoming:
        for fest in upcoming:
            fname = fest.get("name", fest.get("festival", "Unknown"))
            fdate = fest.get("parsed_date", fest.get("date", ""))
            col1, col2, col3 = st.columns([3, 2, 2])
            col1.write(f"**{fname}**")
            col2.write(f"📅 {fdate}")
            if col3.button(f"Send Broadcast", key=f"fest_{fname}"):
                with st.spinner(f"Broadcasting {fname}..."):
                    result = trigger_manual_festival_broadcast(fname, fdate)
                    if result.get("status") == "completed":
                        r = result.get("result", {})
                        st.success(f"Broadcast sent: WA={r.get('sent_whatsapp',0)} "
                                   f"Email={r.get('sent_email',0)} Failed={r.get('failed',0)}")
                    else:
                        st.warning(result.get("message", "No contacts found"))
    else:
        st.info("No festivals in the next 30 days.")

    # Broadcast history
    st.divider()
    st.subheader("Broadcast History")
    try:
        from database import get_festival_broadcasts
        broadcasts = get_festival_broadcasts()
        if broadcasts:
            import pandas as pd
            df = pd.DataFrame(broadcasts[-20:])
            display_cols = [c for c in ["festival_name", "festival_date", "broadcast_status",
                                        "total_contacts", "sent_whatsapp", "sent_email",
                                        "failed_count", "created_at"] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No broadcast history yet.")
    except Exception:
        st.info("Festival broadcast table not initialized yet.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: PRICE BROADCASTS
# ══════════════════════════════════════════════════════════════════════════════


def _render_price_tab():
    """Price watch and broadcast management."""
    try:
        from price_watch_engine import get_price_watch_status, manual_price_check, PriceWatchEngine
    except ImportError:
        st.error("Price watch engine not available.")
        return

    status = get_price_watch_status()

    # Status metrics
    cols = st.columns(4)
    cols[0].metric("Price Items Tracked", status.get("current_prices_count", 0))
    cols[1].metric("Cached Items", status.get("cached_prices_count", 0))
    cols[2].metric("Change Threshold", f"{status.get('threshold_pct', 2.0)}%")
    cols[3].write(f"**Broadcast:** {'🟢 Enabled' if status.get('broadcast_enabled') else '🔴 Disabled'}")

    st.divider()

    # Manual check
    if st.button("🔍 Check Prices Now", type="primary"):
        with st.spinner("Checking for price changes..."):
            result = manual_price_check()
            changes = result.get("changes_found", 0)
            if changes > 0:
                st.success(f"Found {changes} significant price changes!")
                for c in result.get("changes", []):
                    direction = "📈" if c["direction"] == "up" else "📉"
                    st.write(f"  {direction} **{c['grade']}** ({c.get('city','')}): "
                             f"{format_inr(c['old_value'])} → {format_inr(c['new_value'])} "
                             f"({c['change_pct']:+.1f}%)")
                br = result.get("broadcast_result")
                if br:
                    st.info(f"Broadcast: WA={br.get('sent_whatsapp',0)} "
                            f"Email={br.get('sent_email',0)} to {br.get('total_contacts',0)} contacts")
            else:
                st.info("No significant price changes detected.")

    # Price change history
    st.divider()
    st.subheader("Recent Price Changes")
    try:
        engine = PriceWatchEngine()
        history = engine.get_price_history(limit=30)
        if history:
            import pandas as pd
            df = pd.DataFrame(history)
            display_cols = [c for c in ["price_key", "old_value", "new_value",
                                        "change_pct", "broadcast_sent", "changed_at"]
                            if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No price change history yet.")
    except Exception:
        st.info("Price update log not initialized yet.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: AI AUTO-REPLY
# ══════════════════════════════════════════════════════════════════════════════


def _render_ai_reply_tab():
    """AI auto-reply management and testing."""
    try:
        from ai_reply_engine import get_ai_reply_status, test_classify, test_reply, process_pending_replies
    except ImportError:
        st.error("AI reply engine not available.")
        return

    status = get_ai_reply_status()

    # Status
    cols = st.columns(4)
    cols[0].write(f"**Status:** {'🟢 Enabled' if status.get('enabled') else '🔴 Disabled'}")
    cols[1].metric("Confidence Threshold", f"{status.get('confidence_threshold', 0.7):.0%}")
    cols[2].write(f"**Escalate Unsure:** {'Yes' if status.get('escalate_unsure') else 'No'}")
    cols[3].write(f"**Languages:** {', '.join(status.get('languages', ['en']))}")

    st.divider()

    # Process pending
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚡ Process Pending Messages"):
            with st.spinner("Processing incoming messages..."):
                result = process_pending_replies()
                st.write(f"**Status:** {result.get('status', '?')}")
                st.write(f"Processed: {result.get('processed', 0)} | "
                         f"Auto-replied: {result.get('auto_replied', 0)} | "
                         f"Escalated: {result.get('escalated', 0)} | "
                         f"Errors: {result.get('errors', 0)}")

    # Test area
    st.divider()
    st.subheader("Test AI Classification & Reply")

    tcol1, tcol2 = st.columns([2, 1])
    with tcol1:
        test_text = st.text_area(
            "Enter a test message",
            placeholder="e.g., 'I need 500 MT VG30 bitumen delivered to Mumbai'",
            height=80,
        )
    with tcol2:
        test_name = st.text_input("Contact name (optional)", value="Test Contact")

    if st.button("🧪 Test Classification") and test_text:
        classification = test_classify(test_text)
        reply = test_reply(test_text, test_name)

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Classification:**")
            st.json(classification)
        with col2:
            st.write("**Generated Reply:**")
            st.text_area("Reply Preview", value=reply.get("reply_text", ""),
                         height=200, disabled=True, key="reply_preview")
            auto = "✅ Auto-send" if reply.get("auto_send") else "⚠️ Escalate to human"
            st.write(f"**Action:** {auto} (confidence: {reply.get('confidence', 0):.0%})")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════


def _render_settings_tab():
    """CRM Automation settings management."""
    try:
        from settings_engine import load_settings, update
    except ImportError:
        st.error("Settings engine not available.")
        return

    settings = load_settings()

    st.subheader("Daily Rotation")
    col1, col2, col3 = st.columns(3)
    rotation_enabled = col1.toggle("Enable Daily Rotation",
                                    value=settings.get("daily_rotation_enabled", False),
                                    key="rot_enable")
    rotation_count = col2.number_input("Contacts per Day",
                                        value=settings.get("daily_rotation_count", 2400),
                                        min_value=100, max_value=50000, step=100,
                                        key="rot_count")
    rotation_time = col3.text_input("Rotation Time (HH:MM)",
                                     value=settings.get("daily_rotation_time", "09:00"),
                                     key="rot_time")

    col4, col5 = st.columns(2)
    cycle_days = col4.number_input("Rotation Cycle (days)",
                                    value=settings.get("rotation_cycle_days", 10),
                                    min_value=1, max_value=60, key="rot_cycle")
    min_gap = col5.number_input("Min Gap Between Contacts (days)",
                                 value=settings.get("rotation_min_gap_days", 7),
                                 min_value=1, max_value=30, key="rot_gap")

    st.divider()
    st.subheader("Festival Broadcasts")
    col1, col2, col3 = st.columns(3)
    fest_enabled = col1.toggle("Enable Festival Broadcasts",
                                value=settings.get("festival_broadcast_enabled", False),
                                key="fest_enable")
    fest_time = col2.text_input("Broadcast Time",
                                 value=settings.get("festival_broadcast_time", "07:00"),
                                 key="fest_time")
    fest_days = col3.number_input("Days Ahead",
                                   value=settings.get("festival_broadcast_days_ahead", 1),
                                   min_value=0, max_value=7, key="fest_days")

    st.divider()
    st.subheader("Price Broadcasts")
    col1, col2, col3 = st.columns(3)
    price_enabled = col1.toggle("Enable Price Broadcasts",
                                 value=settings.get("price_broadcast_enabled", False),
                                 key="price_enable")
    price_threshold = col2.number_input("Change Threshold (%)",
                                         value=settings.get("price_change_threshold_pct", 2.0),
                                         min_value=0.5, max_value=20.0, step=0.5,
                                         key="price_thresh")
    price_interval = col3.number_input("Check Interval (min)",
                                        value=settings.get("price_watch_interval_minutes", 5),
                                        min_value=1, max_value=60, key="price_int")

    st.divider()
    st.subheader("AI Auto-Reply")
    col1, col2, col3 = st.columns(3)
    ai_enabled = col1.toggle("Enable AI Auto-Reply",
                              value=settings.get("ai_auto_reply_enabled", False),
                              key="ai_enable")
    ai_confidence = col2.slider("Confidence Threshold",
                                 min_value=0.3, max_value=1.0,
                                 value=settings.get("ai_auto_reply_confidence_threshold", 0.7),
                                 step=0.05, key="ai_conf")
    ai_escalate = col3.toggle("Escalate Unsure Messages",
                               value=settings.get("ai_auto_reply_escalate_unsure", True),
                               key="ai_escalate")

    st.divider()
    st.subheader("WhatsApp Limits")
    col1, col2, col3 = st.columns(3)
    wa_fest_limit = col1.number_input("Festival Mode Daily Limit",
                                       value=settings.get("whatsapp_festival_mode_limit", 24000),
                                       min_value=1000, max_value=100000, step=1000,
                                       key="wa_fest")
    wa_batch = col2.number_input("Stagger Batch Size",
                                  value=settings.get("whatsapp_stagger_batch_size", 1000),
                                  min_value=100, max_value=10000, step=100,
                                  key="wa_batch")
    wa_delay = col3.number_input("Stagger Delay (min)",
                                  value=settings.get("whatsapp_stagger_delay_minutes", 60),
                                  min_value=5, max_value=120, step=5,
                                  key="wa_delay")

    st.divider()
    st.subheader("SendGrid (Bulk Email Fallback)")
    col1, col2 = st.columns(2)
    sg_enabled = col1.toggle("Enable SendGrid",
                              value=settings.get("sendgrid_enabled", False),
                              key="sg_enable")
    sg_limit = col2.number_input("Daily Send Limit",
                                  value=settings.get("sendgrid_daily_limit", 10000),
                                  min_value=100, max_value=100000, step=1000,
                                  key="sg_limit")

    st.divider()
    st.subheader("SMS Engine (Fast2SMS)")
    col1, col2 = st.columns(2)
    sms_enabled = col1.toggle("Enable SMS",
                               value=settings.get("sms_enabled", False),
                               key="sms_enable")
    sms_limit = col2.number_input("Daily SMS Limit",
                                   value=settings.get("sms_daily_limit", 100),
                                   min_value=10, max_value=10000, step=10,
                                   key="sms_limit")

    st.divider()
    st.subheader("Privacy & DPDP Compliance")
    col1, col2 = st.columns(2)
    dpdp_enabled = col1.toggle("Enable DPDP Compliance",
                                value=settings.get("dpdp_compliance_enabled", True),
                                key="dpdp_enable")
    consent_req = col2.toggle("Require Consent for Broadcasts",
                               value=settings.get("consent_required_for_broadcast", True),
                               key="dpdp_consent")

    st.divider()
    st.subheader("AI Calling (Placeholder)")
    col1, col2 = st.columns(2)
    call_enabled = col1.toggle("Enable AI Calling",
                                value=settings.get("ai_calling_enabled", False),
                                key="call_enable")
    call_provider = col2.selectbox("Provider",
                                    ["none", "vapi", "bland", "exotel"],
                                    index=["none", "vapi", "bland", "exotel"].index(
                                        settings.get("ai_calling_provider", "none")),
                                    key="call_prov")
    if call_enabled and call_provider == "none":
        st.warning("Select an AI calling provider to enable this feature.")

    st.divider()
    st.subheader("Translation (Bhashini)")
    col1, col2 = st.columns(2)
    bhashini_on = col1.toggle("Enable Bhashini Translation",
                               value=settings.get("bhashini_enabled", False),
                               key="bhashini_enable")
    if bhashini_on:
        col2.info("Languages: en, hi, gu, mr, ta, te")

    # ── Owner & Company Identity ──────────────────────────────────────────
    st.divider()
    st.subheader("Owner & Company Identity")
    col1, col2, col3 = st.columns(3)
    owner_name_val = col1.text_input("Owner Name",
                                      value=settings.get("owner_name", "PRINCE P SHAH"),
                                      key="owner_name_input")
    owner_mobile_val = col2.text_input("Owner Mobile",
                                        value=settings.get("owner_mobile", "+91 7795242424"),
                                        key="owner_mobile_input")
    owner_email_val = col3.text_input("Owner Email",
                                       value=settings.get("owner_email", "princepshah@gmail.com"),
                                       key="owner_email_input")
    col4, col5 = st.columns(2)
    trade_name_val = col4.text_input("Company Trade Name",
                                      value=settings.get("company_trade_name", "PACPL"),
                                      key="trade_name_input")
    seg_templates = col5.toggle("Segment-Aware Templates",
                                 value=settings.get("segment_aware_templates", True),
                                 key="seg_templates_toggle")

    # ── Price Factor Thresholds ───────────────────────────────────────────
    st.divider()
    st.subheader("Price Factor Thresholds (%)")
    col1, col2, col3, col4 = st.columns(4)
    pf_crude = col1.number_input("Crude Oil %", value=float(settings.get("pf_crude_threshold_pct", 3.0)),
                                  min_value=0.5, max_value=20.0, step=0.5, key="pf_crude")
    pf_fx = col2.number_input("USD/INR %", value=float(settings.get("pf_fx_threshold_pct", 1.0)),
                               min_value=0.5, max_value=10.0, step=0.5, key="pf_fx")
    pf_conf = col3.number_input("Conference %", value=float(settings.get("pf_conference_threshold_pct", 2.0)),
                                 min_value=0.5, max_value=10.0, step=0.5, key="pf_conf")
    pf_psu = col4.number_input("PSU Price %", value=float(settings.get("pf_psu_threshold_pct", 1.5)),
                                min_value=0.5, max_value=10.0, step=0.5, key="pf_psu")

    # ── Daily Automation Schedule ─────────────────────────────────────────
    st.divider()
    st.subheader("Daily Automation Schedule")
    col1, col2, col3 = st.columns(3)
    sched_price = col1.text_input("Price Gathering",
                                   value=settings.get("schedule_price_gathering_time", "05:00"),
                                   key="sched_price")
    sched_brief = col2.text_input("PPS Daily Brief",
                                   value=settings.get("schedule_daily_brief_time", "06:30"),
                                   key="sched_brief")
    sched_fest = col3.text_input("Festival Check",
                                  value=settings.get("schedule_festival_check_time", "07:00"),
                                  key="sched_fest")
    col4, col5, col6 = st.columns(3)
    sched_broadcast = col4.text_input("Daily Broadcast",
                                       value=settings.get("schedule_daily_broadcast_time", "09:00"),
                                       key="sched_broadcast")
    sched_alerts = col5.text_input("Price Alerts",
                                    value=settings.get("schedule_price_alerts_time", "18:00"),
                                    key="sched_alerts")
    sched_report = col6.text_input("Daily Report",
                                    value=settings.get("schedule_daily_report_time", "21:00"),
                                    key="sched_report")

    # Save button
    st.divider()
    if st.button("Save All Settings", type="primary"):
        updates = {
            "daily_rotation_enabled": rotation_enabled,
            "daily_rotation_count": rotation_count,
            "daily_rotation_time": rotation_time,
            "rotation_cycle_days": cycle_days,
            "rotation_min_gap_days": min_gap,
            "festival_broadcast_enabled": fest_enabled,
            "festival_broadcast_time": fest_time,
            "festival_broadcast_days_ahead": fest_days,
            "price_broadcast_enabled": price_enabled,
            "price_change_threshold_pct": price_threshold,
            "price_watch_interval_minutes": price_interval,
            "ai_auto_reply_enabled": ai_enabled,
            "ai_auto_reply_confidence_threshold": ai_confidence,
            "ai_auto_reply_escalate_unsure": ai_escalate,
            "whatsapp_festival_mode_limit": wa_fest_limit,
            "whatsapp_stagger_batch_size": wa_batch,
            "whatsapp_stagger_delay_minutes": wa_delay,
            "sendgrid_enabled": sg_enabled,
            "sendgrid_daily_limit": sg_limit,
            "sms_enabled": sms_enabled,
            "sms_daily_limit": sms_limit,
            "dpdp_compliance_enabled": dpdp_enabled,
            "consent_required_for_broadcast": consent_req,
            "ai_calling_enabled": call_enabled,
            "ai_calling_provider": call_provider,
            "bhashini_enabled": bhashini_on,
            # Owner & Company Identity
            "owner_name": owner_name_val,
            "owner_mobile": owner_mobile_val,
            "owner_email": owner_email_val,
            "company_trade_name": trade_name_val,
            "segment_aware_templates": seg_templates,
            # Price Factor Thresholds
            "pf_crude_threshold_pct": pf_crude,
            "pf_fx_threshold_pct": pf_fx,
            "pf_conference_threshold_pct": pf_conf,
            "pf_psu_threshold_pct": pf_psu,
            # Daily Automation Schedule
            "schedule_price_gathering_time": sched_price,
            "schedule_daily_brief_time": sched_brief,
            "schedule_festival_check_time": sched_fest,
            "schedule_daily_broadcast_time": sched_broadcast,
            "schedule_price_alerts_time": sched_alerts,
            "schedule_daily_report_time": sched_report,
        }
        for key, value in updates.items():
            update(key, value)
        st.success("All CRM automation settings saved!")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def _get_categories() -> list[str]:
    """Get contact categories from settings."""
    try:
        from settings_engine import load_settings
        return load_settings().get("contact_categories", [
            "Importer", "Exporter", "Trader", "Dealer",
            "Decanter Unit", "Commission Agent",
            "Truck Transporter", "Tanker Transporter",
        ])
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7: AI PROVIDERS — Multi-AI Configuration & Health
# ══════════════════════════════════════════════════════════════════════════════

def _render_ai_providers_tab():
    """AI Provider configuration: API keys, enable/disable, health, PII filter."""
    from settings_engine import load_settings, save_settings, get_api_key_secure

    settings = load_settings()

    st.subheader("Multi-AI Provider Stack")
    st.caption(
        "9-provider fallback chain: Ollama > HuggingFace > GPT4All > "
        "Groq > Gemini > Mistral > DeepSeek > OpenAI > Claude"
    )

    # ── Live Health Display ────────────────────────────────────────────────
    st.markdown("#### Provider Health Status")
    try:
        from ai_fallback_engine import get_provider_status
        statuses = get_provider_status()
        for s in statuses:
            health = s.get("health", {})
            sr = health.get("success_rate", 100)
            disabled = health.get("is_disabled", False)
            if disabled:
                color = "red"
                badge = "DISABLED"
            elif not s.get("ready"):
                color = "gray"
                badge = "NOT READY"
            elif sr < 50:
                color = "red"
                badge = f"{sr}%"
            elif sr < 80:
                color = "orange"
                badge = f"{sr}%"
            else:
                color = "green"
                badge = f"{sr}%"

            active = " **[ACTIVE]**" if s.get("is_active") else ""
            st.markdown(
                f"{s['icon']} **{s['name']}** — {s['type']} | "
                f":{color}[{badge}]{active}"
            )
            if s.get("last_error"):
                st.caption(f"  Last error: {s['last_error'][:80]}")
    except Exception:
        st.info("AI provider status unavailable.")

    st.divider()

    # ── API Keys ──────────────────────────────────────────────────────────
    st.markdown("#### API Keys (Free Tier)")
    col1, col2 = st.columns(2)

    with col1:
        groq_key = st.text_input("Groq API Key", value="••••" if get_api_key_secure("groq_api_key") else "",
                                  type="password", key="ai_groq_key",
                                  help="https://console.groq.com/keys")
        gemini_key = st.text_input("Gemini API Key", value="••••" if get_api_key_secure("gemini_api_key") else "",
                                    type="password", key="ai_gemini_key",
                                    help="https://aistudio.google.com/apikey")
        mistral_key = st.text_input("Mistral API Key", value="••••" if get_api_key_secure("mistral_api_key") else "",
                                     type="password", key="ai_mistral_key",
                                     help="https://console.mistral.ai/api-keys")

    with col2:
        deepseek_key = st.text_input("DeepSeek API Key", value="••••" if get_api_key_secure("deepseek_api_key") else "",
                                      type="password", key="ai_deepseek_key",
                                      help="Research ONLY — no customer data sent")
        brevo_key = st.text_input("Brevo Email API Key", value="••••" if get_api_key_secure("brevo_api_key") else "",
                                   type="password", key="ai_brevo_key",
                                   help="300 emails/day free — https://app.brevo.com")
        elevenlabs_key = st.text_input("ElevenLabs API Key", value="••••" if get_api_key_secure("elevenlabs_api_key") else "",
                                        type="password", key="ai_elevenlabs_key",
                                        help="Voice TTS stub")

    st.divider()

    # ── Provider Enable/Disable ───────────────────────────────────────────
    st.markdown("#### Provider Toggles")
    c1, c2, c3, c4 = st.columns(4)
    groq_en = c1.checkbox("Groq Enabled", value=settings.get("ai_provider_groq_enabled", True), key="ai_en_groq")
    gemini_en = c2.checkbox("Gemini Enabled", value=settings.get("ai_provider_gemini_enabled", True), key="ai_en_gemini")
    mistral_en = c3.checkbox("Mistral Enabled", value=settings.get("ai_provider_mistral_enabled", True), key="ai_en_mistral")
    deepseek_en = c4.checkbox("DeepSeek Enabled", value=settings.get("ai_provider_deepseek_enabled", True), key="ai_en_deepseek")

    # ── PII Filter ────────────────────────────────────────────────────────
    st.markdown("#### DeepSeek PII Filter")
    pii_filter = st.checkbox(
        "Strip customer PII before sending to DeepSeek (recommended)",
        value=settings.get("ai_deepseek_pii_filter", True),
        key="ai_pii_filter",
        help="Removes phone numbers, emails, PAN, GSTIN, Aadhaar, and customer names"
    )
    if not pii_filter:
        st.warning("PII filter disabled — customer data will be sent to DeepSeek servers.")

    # ── Health Monitoring Settings ────────────────────────────────────────
    st.markdown("#### Auto-Health Settings")
    hc1, hc2, hc3 = st.columns(3)
    auto_disable_threshold = hc1.number_input(
        "Auto-disable error threshold (%)", min_value=10, max_value=100,
        value=settings.get("ai_provider_auto_disable_threshold", 50), key="ai_health_thresh")
    cooldown_min = hc2.number_input(
        "Cooldown after disable (min)", min_value=1, max_value=120,
        value=settings.get("ai_provider_cooldown_minutes", 15), key="ai_health_cooldown")
    health_interval = hc3.number_input(
        "Health check interval (sec)", min_value=60, max_value=3600,
        value=settings.get("ai_provider_health_check_interval", 300), key="ai_health_interval")

    # ── Save Button ───────────────────────────────────────────────────────
    if st.button("Save AI Provider Settings", type="primary", key="save_ai_providers"):
        updates = {
            "ai_provider_groq_enabled": groq_en,
            "ai_provider_gemini_enabled": gemini_en,
            "ai_provider_mistral_enabled": mistral_en,
            "ai_provider_deepseek_enabled": deepseek_en,
            "ai_deepseek_pii_filter": pii_filter,
            "ai_provider_auto_disable_threshold": auto_disable_threshold,
            "ai_provider_cooldown_minutes": cooldown_min,
            "ai_provider_health_check_interval": health_interval,
        }

        # Save API keys to vault if provided (not the masked "••••")
        try:
            from vault_engine import set_secret, _HAS_CRYPTOGRAPHY
            vault_ok = _HAS_CRYPTOGRAPHY
        except (ImportError, Exception):
            vault_ok = False

        key_map = {
            "groq_api_key": groq_key,
            "gemini_api_key": gemini_key,
            "mistral_api_key": mistral_key,
            "deepseek_api_key": deepseek_key,
            "brevo_api_key": brevo_key,
            "elevenlabs_api_key": elevenlabs_key,
        }
        for setting_key, val in key_map.items():
            if val and val != "••••":
                if vault_ok:
                    set_secret(f"settings_{setting_key}", val)
                else:
                    updates[setting_key] = val

        settings.update(updates)
        save_settings(settings)
        st.success("AI Provider settings saved!")
        st.rerun()
