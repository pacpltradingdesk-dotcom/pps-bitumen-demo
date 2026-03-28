"""
PPS Anantam — Recipient Selector Component v1.0
==================================================
Reusable Streamlit component for selecting recipients from:
- CRM contacts (customers/suppliers)
- Recipient lists (from database)
- Manual entry
- Groups (all clients, all suppliers, team)

Usage:
    from recipient_selector import render_recipient_selector
    recipients = render_recipient_selector("my_key", channel="email")
    # Returns: [{"name": "John", "email": "j@x.com", "whatsapp": ""}, ...]
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))


def render_recipient_selector(key_prefix: str, channel: str = "email",
                              allow_multiple: bool = True) -> list:
    """Render inline recipient selector. Returns list of {name, email, whatsapp}.

    Parameters
    ----------
    key_prefix : str — Unique key prefix for Streamlit widgets
    channel : str — "email" or "whatsapp"
    allow_multiple : bool — Allow multiple recipient selection
    """
    import streamlit as st

    mode = st.radio(
        "Select recipients",
        ["From CRM", "Recipient List", "Enter Manually", "Groups"],
        horizontal=True,
        key=f"{key_prefix}_mode",
    )

    if mode == "From CRM":
        return _render_crm_selector(key_prefix, channel, allow_multiple)
    elif mode == "Recipient List":
        return _render_list_selector(key_prefix, channel)
    elif mode == "Enter Manually":
        return _render_manual_entry(key_prefix, channel)
    else:
        return _render_group_selector(key_prefix, channel)


def _render_crm_selector(key_prefix: str, channel: str, allow_multiple: bool) -> list:
    """Select from customers/suppliers in database."""
    import streamlit as st

    contacts = _load_crm_contacts()
    if not contacts:
        st.caption("No contacts found in CRM. Add customers/suppliers first.")
        return []

    contact_type = st.radio(
        "Contact type",
        ["All", "Customers", "Suppliers"],
        horizontal=True,
        key=f"{key_prefix}_crm_type",
    )

    if contact_type == "Customers":
        filtered = [c for c in contacts if c.get("type") == "customer"]
    elif contact_type == "Suppliers":
        filtered = [c for c in contacts if c.get("type") == "supplier"]
    else:
        filtered = contacts

    # Build display options
    options = []
    for c in filtered:
        addr = c.get("email", "") if channel == "email" else c.get("whatsapp", "")
        if addr:
            options.append(f"{c['name']} ({addr})")

    if not options:
        st.caption(f"No contacts with {channel} address found.")
        return []

    if allow_multiple:
        selected = st.multiselect(
            f"Select {channel} recipients",
            options,
            key=f"{key_prefix}_crm_sel",
        )
    else:
        sel = st.selectbox(
            f"Select {channel} recipient",
            [""] + options,
            key=f"{key_prefix}_crm_sel",
        )
        selected = [sel] if sel else []

    # Map back to contact dicts
    result = []
    for s in selected:
        for c in filtered:
            addr = c.get("email", "") if channel == "email" else c.get("whatsapp", "")
            if f"{c['name']} ({addr})" == s:
                result.append({"name": c["name"], "email": c.get("email", ""), "whatsapp": c.get("whatsapp", "")})
                break
    return result


def _render_list_selector(key_prefix: str, channel: str) -> list:
    """Select from existing recipient lists."""
    import streamlit as st

    try:
        from database import get_recipient_lists
        lists = get_recipient_lists(list_type=channel)
        if not lists:
            lists = get_recipient_lists()
    except Exception:
        lists = []

    if not lists:
        st.caption("No recipient lists found. Create one in Email/WhatsApp Setup.")
        return []

    list_names = [rl["list_name"] for rl in lists]
    selected_list = st.selectbox(
        "Select recipient list",
        [""] + list_names,
        key=f"{key_prefix}_list_sel",
    )

    if not selected_list:
        return []

    for rl in lists:
        if rl["list_name"] == selected_list:
            try:
                import json
                recipients = json.loads(rl.get("recipients", "[]"))
                if recipients:
                    st.caption(f"📋 {len(recipients)} recipients in this list")
                return recipients
            except Exception:
                return []
    return []


def _render_manual_entry(key_prefix: str, channel: str) -> list:
    """Manual text input for emails/phones."""
    import streamlit as st

    if channel == "email":
        placeholder = "john@example.com, jane@example.com"
        label = "Enter email addresses (comma-separated)"
    else:
        placeholder = "9876543210, 9123456789"
        label = "Enter phone numbers (comma-separated)"

    text = st.text_area(
        label,
        placeholder=placeholder,
        key=f"{key_prefix}_manual",
        height=80,
    )

    if not text:
        return []

    entries = [e.strip() for e in text.split(",") if e.strip()]
    result = []
    for entry in entries:
        if channel == "email":
            result.append({"name": entry.split("@")[0], "email": entry, "whatsapp": ""})
        else:
            # Normalize phone number
            phone = entry.replace("+91", "").replace("-", "").replace(" ", "")
            if len(phone) == 10:
                phone = "91" + phone
            result.append({"name": phone, "email": "", "whatsapp": phone})

    if result:
        st.caption(f"✅ {len(result)} recipient(s) entered")
    return result


def _render_group_selector(key_prefix: str, channel: str) -> list:
    """Quick group selection: all clients, all suppliers, team."""
    import streamlit as st

    group = st.radio(
        "Select group",
        ["All Customers", "All Suppliers", "All Contacts", "Team Members"],
        key=f"{key_prefix}_group",
    )

    contacts = _load_crm_contacts()

    if group == "All Customers":
        filtered = [c for c in contacts if c.get("type") == "customer"]
    elif group == "All Suppliers":
        filtered = [c for c in contacts if c.get("type") == "supplier"]
    elif group == "Team Members":
        filtered = _load_team_members()
    else:
        filtered = contacts

    # Filter by channel availability
    addr_key = "email" if channel == "email" else "whatsapp"
    result = [
        {"name": c["name"], "email": c.get("email", ""), "whatsapp": c.get("whatsapp", "")}
        for c in filtered
        if c.get(addr_key)
    ]

    if result:
        st.caption(f"📋 {len(result)} recipients in group '{group}'")
    else:
        st.caption(f"No contacts with {channel} address in '{group}'")
    return result


def _load_crm_contacts() -> list:
    """Load all contacts from CRM (customers + suppliers)."""
    contacts = []
    try:
        from database import _select_all
        customers = _select_all("customers", where="is_active = 1")
        for c in customers:
            contacts.append({
                "name": c.get("name", ""),
                "email": c.get("email", ""),
                "whatsapp": c.get("whatsapp_number", ""),
                "contact": c.get("contact", ""),
                "type": "customer",
                "city": c.get("city", ""),
            })
        suppliers = _select_all("suppliers", where="is_active = 1")
        for s in suppliers:
            contacts.append({
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "whatsapp": s.get("whatsapp_number", ""),
                "contact": s.get("contact", ""),
                "type": "supplier",
                "city": s.get("city", ""),
            })
    except Exception:
        pass
    return contacts


def _load_team_members() -> list:
    """Load team members from users table."""
    try:
        from database import _select_all
        users = _select_all("users", where="is_active = 1")
        return [
            {
                "name": u.get("display_name", u.get("username", "")),
                "email": u.get("email", ""),
                "whatsapp": u.get("whatsapp_number", ""),
                "type": "team",
            }
            for u in users
        ]
    except Exception:
        return []
