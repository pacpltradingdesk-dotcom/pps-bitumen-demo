"""
PPS Anantam — Share Center v5.0
=================================
Central hub for all sharing activities: Quick Share, Scheduled,
Templates, History, Contacts management.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).parent.parent.parent

# ── JSON file paths ──────────────────────────────────────────────────────────
_CONTACTS_FILE = ROOT / "tbl_contacts.json"
_SCHEDULES_FILE = ROOT / "share_schedules.json"
_TEMPLATES_FILE = ROOT / "share_templates.json"
_HISTORY_FILE = ROOT / "share_history.json"

# ── Engine imports (graceful fallback) ───────────────────────────────────────
try:
    from share_system import (
        format_message,
        share_whatsapp,
        share_telegram,
        share_email,
        get_share_history,
    )
    _SHARE_AVAILABLE = True
except ImportError:
    _SHARE_AVAILABLE = False

    def format_message(page_name, data=None, channel="whatsapp"):
        return f"[Share System unavailable] {page_name}"

    def share_whatsapp(phone, page_name, data=None):
        return {"success": False, "error": "share_system module not available"}

    def share_telegram(chat_id, page_name, data=None):
        return {"success": False, "error": "share_system module not available"}

    def share_email(to_email, page_name, data=None, subject=None):
        return {"success": False, "error": "share_system module not available"}

    def get_share_history(limit=50):
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  JSON helpers
# ═════════════════════════════════════════════════════════════════════════════

def _load_json(filepath, default=None):
    """Load a JSON file with safe fallback."""
    try:
        p = Path(filepath)
        if p.exists():
            raw = p.read_text(encoding="utf-8").strip()
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return default if default is not None else []


from . import save_json as _save_json  # shared helper


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


# ═════════════════════════════════════════════════════════════════════════════
#  Available pages list (for source selection)
# ═════════════════════════════════════════════════════════════════════════════

_SHAREABLE_PAGES = [
    "Command Center",
    "Live Market",
    "Pricing Calculator",
    "Sales Calendar",
    "CRM & Tasks",
    "Negotiation Tracker",
    "Communication Hub",
    "Logistics Ecosystem",
    "Market Intelligence",
    "Director Briefing",
    "Custom Report",
]


# ═════════════════════════════════════════════════════════════════════════════
#  RENDER
# ═════════════════════════════════════════════════════════════════════════════

def render():
    """Render the Share Center page."""

    # ── Page header ──────────────────────────────────────────────────────
    st.markdown(
        '<div class="pps-page-header"><div class="pps-page-title">'
        '\U0001f4e4 Share Center</div></div>',
        unsafe_allow_html=True,
    )

    if not _SHARE_AVAILABLE:
        st.warning(
            "Share system engine (`share_system.py`) is not available. "
            "Some features will run in preview mode."
        )

    # ── Tabs ─────────────────────────────────────────────────────────────
    tab_quick, tab_sched, tab_tpl, tab_hist, tab_contacts = st.tabs([
        "\u26a1 Quick Share",
        "\U0001f4c5 Scheduled",
        "\U0001f4dd Templates",
        "\U0001f4dc History",
        "\U0001f4c7 Contacts",
    ])

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 1 — Quick Share
    # ══════════════════════════════════════════════════════════════════════
    with tab_quick:
        st.subheader("Quick Share")
        st.caption("Select a page, choose recipients, and send instantly.")

        contacts = _load_json(_CONTACTS_FILE, [])

        # ── Source selection ─────────────────────────────────────────────
        col_src, col_chan = st.columns(2)
        with col_src:
            page_name = st.selectbox(
                "Data Source (Page)",
                options=_SHAREABLE_PAGES,
                key="qs_page",
            )
        with col_chan:
            channel = st.selectbox(
                "Channel",
                options=["WhatsApp", "Telegram", "Email"],
                key="qs_channel",
            )

        channel_key = channel.lower()

        # ── Recipient selection ──────────────────────────────────────────
        st.markdown("**Select Recipients**")
        contact_names = [c.get("name", "Unknown") for c in contacts]

        if contact_names:
            selected_contacts = st.multiselect(
                "From Contacts",
                options=contact_names,
                key="qs_recipients",
            )
        else:
            selected_contacts = []
            st.info("No contacts found in `tbl_contacts.json`. Add contacts in the Contacts tab.")

        # Manual entry
        manual_recipient = st.text_input(
            f"Or enter {channel} recipient manually",
            placeholder=(
                "Phone number (e.g. +919876543210)" if channel_key == "whatsapp"
                else "Chat ID (e.g. -100123456)" if channel_key == "telegram"
                else "Email address"
            ),
            key="qs_manual",
        )

        # ── Message preview ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Message Preview**")

        sample_data = {
            "summary": f"{page_name} — shared via PPS Share Center",
            "kpis": [
                {"label": "Source", "value": page_name},
                {"label": "Channel", "value": channel},
                {"label": "Sent At", "value": _now_ist()},
            ],
        }
        preview = format_message(page_name, sample_data, channel=channel_key)
        st.text_area("Formatted Message", value=preview, height=200, disabled=True, key="qs_preview")

        # ── Custom note ──────────────────────────────────────────────────
        custom_note = st.text_input(
            "Add a note (optional)",
            placeholder="e.g. Please review this report",
            key="qs_note",
        )

        # ── Send button ─────────────────────────────────────────────────
        st.markdown("---")
        if st.button("\U0001f680 Send Now", type="primary", use_container_width=True, key="qs_send"):
            # Build recipient list
            recipients = []
            for name in selected_contacts:
                for c in contacts:
                    if c.get("name") == name:
                        contact_val = c.get("contact", "") or c.get("email", "") or c.get("chat_id", "")
                        if contact_val:
                            recipients.append({"name": name, "address": contact_val})
                        break

            if manual_recipient.strip():
                recipients.append({"name": "Manual", "address": manual_recipient.strip()})

            if not recipients:
                st.error("Please select at least one recipient or enter one manually.")
            else:
                success_count = 0
                fail_count = 0
                if custom_note:
                    sample_data["summary"] = f"{page_name} — {custom_note}"

                for r in recipients:
                    try:
                        if channel_key == "whatsapp":
                            res = share_whatsapp(r["address"], page_name, sample_data)
                        elif channel_key == "telegram":
                            res = share_telegram(r["address"], page_name, sample_data)
                        else:
                            res = share_email(r["address"], page_name, sample_data)

                        if res.get("success"):
                            success_count += 1
                        else:
                            fail_count += 1
                    except Exception:
                        fail_count += 1

                if success_count:
                    st.success(f"Sent to {success_count} recipient(s) via {channel}.")
                if fail_count:
                    st.warning(f"Failed for {fail_count} recipient(s). Check History for details.")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 2 — Scheduled Shares
    # ══════════════════════════════════════════════════════════════════════
    with tab_sched:
        st.subheader("Scheduled Shares")
        st.caption("View and manage recurring/scheduled share tasks.")

        schedules = _load_json(_SCHEDULES_FILE, [])

        if not schedules:
            st.info("No scheduled shares found. Use Quick Share or the Share button on any page to schedule.")
        else:
            # Build display table
            display_rows = []
            for idx, s in enumerate(schedules):
                display_rows.append({
                    "#": idx + 1,
                    "Page": s.get("page_name", "—"),
                    "Channel": s.get("channel", "—"),
                    "Schedule Time": s.get("schedule_time", "—"),
                    "Recipients": ", ".join(s.get("recipients", [])) if isinstance(s.get("recipients"), list) else str(s.get("recipients", "—")),
                    "Status": s.get("status", "—"),
                    "Created": s.get("created_at", "—"),
                })

            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True,
            )

            # Delete schedule
            st.markdown("---")
            st.markdown("**Remove a Schedule**")
            sched_labels = [
                f"#{i+1} — {s.get('page_name', '?')} via {s.get('channel', '?')} at {s.get('schedule_time', '?')}"
                for i, s in enumerate(schedules)
            ]
            to_delete = st.selectbox("Select schedule to remove", options=sched_labels, key="sched_del_sel")
            if st.button("\U0001f5d1\ufe0f Delete Selected", key="sched_del_btn"):
                del_idx = sched_labels.index(to_delete)
                schedules.pop(del_idx)
                if _save_json(_SCHEDULES_FILE, schedules):
                    st.success("Schedule removed.")
                    st.rerun()
                else:
                    st.error("Failed to save changes.")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 3 — Templates
    # ══════════════════════════════════════════════════════════════════════
    with tab_tpl:
        st.subheader("Message Templates")
        st.caption("Save, load, and edit reusable share message templates.")

        templates = _load_json(_TEMPLATES_FILE, [])

        # ── Existing templates list ──────────────────────────────────────
        if templates:
            st.markdown("**Saved Templates**")
            for idx, tpl in enumerate(templates):
                with st.expander(f"\U0001f4c4 {tpl.get('name', f'Template {idx+1}')}", expanded=False):
                    st.markdown(f"**Channel:** {tpl.get('channel', 'Any')}")
                    st.markdown(f"**Created:** {tpl.get('created_at', '—')}")
                    st.text_area(
                        "Template Body",
                        value=tpl.get("body", ""),
                        height=150,
                        key=f"tpl_body_{idx}",
                        disabled=True,
                    )

                    col_use, col_edit, col_del = st.columns(3)
                    with col_use:
                        if st.button("Use Template", key=f"tpl_use_{idx}"):
                            st.session_state["qs_note"] = tpl.get("body", "")
                            st.info("Template loaded into Quick Share note. Switch to Quick Share tab.")

                    with col_edit:
                        if st.button("\u270f\ufe0f Edit", key=f"tpl_edit_{idx}"):
                            st.session_state[f"tpl_editing_{idx}"] = True

                    with col_del:
                        if st.button("\U0001f5d1\ufe0f Delete", key=f"tpl_del_{idx}"):
                            templates.pop(idx)
                            _save_json(_TEMPLATES_FILE, templates)
                            st.success("Template deleted.")
                            st.rerun()

                    # Inline edit mode
                    if st.session_state.get(f"tpl_editing_{idx}", False):
                        new_name = st.text_input("Name", value=tpl.get("name", ""), key=f"tpl_ename_{idx}")
                        new_channel = st.selectbox(
                            "Channel", ["Any", "WhatsApp", "Telegram", "Email"],
                            index=["Any", "WhatsApp", "Telegram", "Email"].index(tpl.get("channel", "Any")) if tpl.get("channel", "Any") in ["Any", "WhatsApp", "Telegram", "Email"] else 0,
                            key=f"tpl_echan_{idx}",
                        )
                        new_body = st.text_area("Body", value=tpl.get("body", ""), height=150, key=f"tpl_ebody_{idx}")
                        if st.button("\U0001f4be Save Changes", key=f"tpl_esave_{idx}"):
                            templates[idx]["name"] = new_name
                            templates[idx]["channel"] = new_channel
                            templates[idx]["body"] = new_body
                            templates[idx]["updated_at"] = _now_ist()
                            _save_json(_TEMPLATES_FILE, templates)
                            st.session_state[f"tpl_editing_{idx}"] = False
                            st.success("Template updated.")
                            st.rerun()
        else:
            st.info("No templates saved yet. Create one below.")

        # ── Create new template ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Create New Template**")

        new_tpl_name = st.text_input("Template Name", placeholder="e.g. Weekly Market Report", key="new_tpl_name")
        new_tpl_channel = st.selectbox("Channel", ["Any", "WhatsApp", "Telegram", "Email"], key="new_tpl_channel")
        new_tpl_body = st.text_area(
            "Message Body",
            placeholder="Enter your template message here...\nUse {page_name}, {date}, {time} as placeholders.",
            height=150,
            key="new_tpl_body",
        )

        if st.button("\U0001f4be Save Template", type="primary", key="save_new_tpl"):
            if not new_tpl_name.strip():
                st.error("Template name is required.")
            elif not new_tpl_body.strip():
                st.error("Template body cannot be empty.")
            else:
                templates.append({
                    "name": new_tpl_name.strip(),
                    "channel": new_tpl_channel,
                    "body": new_tpl_body.strip(),
                    "created_at": _now_ist(),
                })
                _save_json(_TEMPLATES_FILE, templates)
                st.success(f"Template '{new_tpl_name}' saved.")
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 4 — History
    # ══════════════════════════════════════════════════════════════════════
    with tab_hist:
        st.subheader("Share History")
        st.caption("Log of all shares sent from this dashboard.")

        history = _load_json(_HISTORY_FILE, [])

        # Also try the engine's get_share_history for merged view
        if _SHARE_AVAILABLE:
            try:
                engine_history = get_share_history(limit=100)
                if engine_history:
                    # Merge — deduplicate by id
                    existing_ids = {h.get("id") for h in history if "id" in h}
                    for eh in engine_history:
                        if eh.get("id") not in existing_ids:
                            history.append(eh)
            except Exception:
                pass

        if not history:
            st.info("No share history yet. Send something via Quick Share to see it here.")
        else:
            # Sort by timestamp descending
            try:
                history_sorted = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)
            except Exception:
                history_sorted = history

            # Filter controls
            col_fch, col_fst = st.columns(2)
            with col_fch:
                filter_channel = st.selectbox(
                    "Filter by Channel",
                    options=["All", "whatsapp", "telegram", "email", "pdf"],
                    key="hist_filter_ch",
                )
            with col_fst:
                filter_status = st.selectbox(
                    "Filter by Status",
                    options=["All", "queued", "sent", "fallback", "error", "generated", "scheduled"],
                    key="hist_filter_st",
                )

            # Apply filters
            filtered = history_sorted
            if filter_channel != "All":
                filtered = [h for h in filtered if h.get("channel", "").lower() == filter_channel]
            if filter_status != "All":
                filtered = [h for h in filtered if h.get("status", "").lower() == filter_status]

            # Display table
            display_rows = []
            for h in filtered[:100]:
                display_rows.append({
                    "Timestamp": h.get("timestamp", "—"),
                    "Channel": h.get("channel", "—"),
                    "Recipient": h.get("recipient", "—"),
                    "Page": h.get("page_name", "—"),
                    "Status": h.get("status", "—"),
                    "Error": h.get("error", ""),
                })

            if display_rows:
                st.dataframe(display_rows, use_container_width=True, hide_index=True)
                st.caption(f"Showing {len(display_rows)} of {len(filtered)} records.")
            else:
                st.info("No records match the selected filters.")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 5 — Contacts
    # ══════════════════════════════════════════════════════════════════════
    with tab_contacts:
        st.subheader("Share Contacts")
        st.caption("Manage recipient lists grouped by channel.")

        contacts = _load_json(_CONTACTS_FILE, [])

        if not contacts:
            st.info("No contacts found in `tbl_contacts.json`.")
        else:
            # Group by potential channel usage
            wa_contacts = [c for c in contacts if c.get("contact")]
            email_contacts = [c for c in contacts if c.get("email")]
            tg_contacts = [c for c in contacts if c.get("chat_id") or c.get("telegram_id")]

            # ── WhatsApp Contacts ────────────────────────────────────────
            st.markdown("### \U0001f4f1 WhatsApp Contacts")
            if wa_contacts:
                wa_rows = []
                for c in wa_contacts:
                    wa_rows.append({
                        "Name": c.get("name", "—"),
                        "Phone": c.get("contact", "—"),
                        "Type": c.get("type", "—"),
                        "Category": c.get("category", "—"),
                        "City": c.get("city", "—"),
                        "State": c.get("state", "—"),
                    })
                st.dataframe(wa_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("No contacts with phone numbers.")

            # ── Telegram Contacts ────────────────────────────────────────
            st.markdown("### \u2708\ufe0f Telegram Contacts")
            if tg_contacts:
                tg_rows = []
                for c in tg_contacts:
                    tg_rows.append({
                        "Name": c.get("name", "—"),
                        "Chat ID": c.get("chat_id", "") or c.get("telegram_id", "—"),
                        "Type": c.get("type", "—"),
                        "Category": c.get("category", "—"),
                    })
                st.dataframe(tg_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("No contacts with Telegram IDs. Add via the form below.")

            # ── Email Contacts ───────────────────────────────────────────
            st.markdown("### \u2709\ufe0f Email Contacts")
            if email_contacts:
                em_rows = []
                for c in email_contacts:
                    em_rows.append({
                        "Name": c.get("name", "—"),
                        "Email": c.get("email", "—"),
                        "Type": c.get("type", "—"),
                        "Category": c.get("category", "—"),
                    })
                st.dataframe(em_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("No contacts with email addresses. Add via the form below.")

        # ── Add new contact ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Add New Contact**")

        ac_col1, ac_col2 = st.columns(2)
        with ac_col1:
            new_name = st.text_input("Name", placeholder="e.g. Rahul Sharma", key="ac_name")
            new_type = st.selectbox("Type", ["customer", "supplier", "agent", "internal"], key="ac_type")
            new_category = st.text_input("Category", placeholder="e.g. Contractor - NHAI", key="ac_category")
        with ac_col2:
            new_phone = st.text_input("Phone (WhatsApp)", placeholder="+919876543210", key="ac_phone")
            new_email = st.text_input("Email", placeholder="name@company.com", key="ac_email")
            new_tg_id = st.text_input("Telegram Chat ID", placeholder="-100123456", key="ac_tgid")

        new_city = st.text_input("City", placeholder="e.g. Mumbai", key="ac_city")

        if st.button("\u2795 Add Contact", type="primary", key="ac_add"):
            if not new_name.strip():
                st.error("Contact name is required.")
            elif not (new_phone.strip() or new_email.strip() or new_tg_id.strip()):
                st.error("At least one contact method (Phone, Email, or Telegram ID) is required.")
            else:
                new_contact = {
                    "name": new_name.strip(),
                    "type": new_type,
                    "category": new_category.strip(),
                    "city": new_city.strip(),
                    "contact": new_phone.strip(),
                    "email": new_email.strip(),
                    "source": "share_center",
                    "imported_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
                }
                if new_tg_id.strip():
                    new_contact["chat_id"] = new_tg_id.strip()

                contacts.append(new_contact)
                if _save_json(_CONTACTS_FILE, contacts):
                    st.success(f"Contact '{new_name}' added.")
                    st.rerun()
                else:
                    st.error("Failed to save contact.")

        # ── Remove contact ───────────────────────────────────────────────
        if contacts:
            st.markdown("---")
            st.markdown("**Remove Contact**")
            contact_labels = [f"{c.get('name', '?')} ({c.get('type', '?')})" for c in contacts]
            to_remove = st.selectbox("Select contact to remove", options=contact_labels, key="ac_remove_sel")
            if st.button("\U0001f5d1\ufe0f Remove Contact", key="ac_remove_btn"):
                rm_idx = contact_labels.index(to_remove)
                removed_name = contacts[rm_idx].get("name", "?")
                contacts.pop(rm_idx)
                if _save_json(_CONTACTS_FILE, contacts):
                    st.success(f"Contact '{removed_name}' removed.")
                    st.rerun()
                else:
                    st.error("Failed to save changes.")
