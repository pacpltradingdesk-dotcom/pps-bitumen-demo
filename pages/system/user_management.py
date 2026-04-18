"""
User Management — Director-only dedicated page.
4 tabs: Users list, Add User, Audit Log, Policies.
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from database import (
    delete_user,
    get_all_users,
    get_audit_logs,
    get_user_by_username,
    insert_audit_log,
    insert_user,
    update_user,
)
from role_engine import check_role, hash_pin

ROLES = ["director", "sales", "operations", "viewer"]
ROLE_LABELS = {
    "director": "👑 Director",
    "sales": "🤝 Sales",
    "operations": "⚙️ Operations",
    "viewer": "👁️ Viewer",
}
ROLE_DESCRIPTIONS = {
    "director": "Full access — all pages, user management, settings",
    "sales": "Create quotes, manage CRM, send WA/Email, view pricing",
    "operations": "View-only on sales; edit logistics, PO, delivery",
    "viewer": "Read-only — dashboards, reports, no edits",
}


def _audit(action: str, resource: str = "user_management", details: str = ""):
    try:
        insert_audit_log({
            "username": st.session_state.get("_auth_username", "admin"),
            "user_id": (st.session_state.get("_auth_user") or {}).get("id"),
            "action": action,
            "resource": resource,
            "details": details,
        })
    except Exception:
        pass


def render():
    st.markdown("# 👥 User Management")
    st.caption("Create, edit, and audit user accounts. Director-only.")

    if not check_role("director"):
        st.error("🔒 Director access required for user management.")
        st.info("Contact your administrator to request access.")
        return

    tabs = st.tabs(["👤 Users", "➕ Add User", "📜 Audit Log", "⚙️ Policies"])

    with tabs[0]:
        _render_users_tab()
    with tabs[1]:
        _render_add_user_tab()
    with tabs[2]:
        _render_audit_tab()
    with tabs[3]:
        _render_policies_tab()


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Users list + per-row actions
# ════════════════════════════════════════════════════════════════════════════

def _render_users_tab():
    users = get_all_users()

    # KPI row
    active = sum(1 for u in users if u.get("is_active"))
    directors = sum(1 for u in users if u.get("role") == "director" and u.get("is_active"))
    inactive = len(users) - active
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Users", len(users))
    k2.metric("Active", active)
    k3.metric("Directors", directors)
    k4.metric("Inactive", inactive)

    st.divider()

    # Filters
    f1, f2, f3 = st.columns([2, 2, 3])
    with f1:
        role_filter = st.multiselect("Role", ROLES, default=ROLES, key="_um_role_f")
    with f2:
        status_filter = st.radio("Status", ["All", "Active", "Inactive"],
                                 horizontal=True, key="_um_status_f")
    with f3:
        search = st.text_input("🔍 Search by name / username / email",
                               key="_um_search")

    filtered = []
    for u in users:
        if u.get("role") not in role_filter:
            continue
        is_act = bool(u.get("is_active"))
        if status_filter == "Active" and not is_act:
            continue
        if status_filter == "Inactive" and is_act:
            continue
        if search:
            s = search.lower()
            hay = " ".join(str(u.get(k, "") or "").lower()
                           for k in ("username", "display_name", "email", "whatsapp_number"))
            if s not in hay:
                continue
        filtered.append(u)

    st.caption(f"Showing {len(filtered)} of {len(users)} users.")

    if not filtered:
        st.info("No users match the current filters.")
        return

    # Render each user as an expandable card
    for u in filtered:
        _render_user_row(u)


def _render_user_row(u: dict):
    status_badge = "🟢 Active" if u.get("is_active") else "⚫ Inactive"
    role_label = ROLE_LABELS.get(u.get("role"), u.get("role", "?"))
    last_login = u.get("last_login") or "Never"

    with st.expander(
        f"**{u.get('display_name') or u.get('username')}** · "
        f"`{u.get('username')}` · {role_label} · {status_badge}",
        expanded=False,
    ):
        ic1, ic2, ic3 = st.columns(3)
        ic1.caption(f"📧 Email: {u.get('email') or '—'}")
        ic2.caption(f"📱 WhatsApp: {u.get('whatsapp_number') or '—'}")
        ic3.caption(f"🕓 Last login: {last_login}")

        # Edit form
        with st.form(f"_um_edit_{u['id']}", border=False):
            ec1, ec2 = st.columns(2)
            with ec1:
                new_display = st.text_input("Display Name",
                                            value=u.get("display_name") or "",
                                            key=f"_um_disp_{u['id']}")
                new_email = st.text_input("Email",
                                          value=u.get("email") or "",
                                          key=f"_um_email_{u['id']}")
            with ec2:
                new_role = st.selectbox(
                    "Role", ROLES,
                    index=ROLES.index(u.get("role", "viewer")) if u.get("role") in ROLES else 3,
                    key=f"_um_role_{u['id']}",
                    format_func=lambda r: ROLE_LABELS.get(r, r),
                )
                new_wa = st.text_input("WhatsApp (+91…)",
                                       value=u.get("whatsapp_number") or "",
                                       key=f"_um_wa_{u['id']}")
            new_pin = st.text_input("Reset PIN (leave empty to keep unchanged)",
                                    type="password",
                                    key=f"_um_pin_{u['id']}",
                                    placeholder="Minimum 4 digits")
            save_clicked = st.form_submit_button("💾 Save Changes", type="primary",
                                                 use_container_width=True)
            if save_clicked:
                updates = {}
                if new_display != (u.get("display_name") or ""):
                    updates["display_name"] = new_display.strip()
                if new_email != (u.get("email") or ""):
                    updates["email"] = new_email.strip() or None
                if new_wa != (u.get("whatsapp_number") or ""):
                    updates["whatsapp_number"] = new_wa.strip() or None
                if new_role != u.get("role"):
                    updates["role"] = new_role
                if new_pin.strip():
                    if len(new_pin.strip()) < 4:
                        st.error("PIN must be at least 4 digits.")
                        st.stop()
                    updates["pin_hash"] = hash_pin(new_pin.strip())
                if updates:
                    try:
                        update_user(u["id"], updates)
                        _audit("user_update", f"user:{u['username']}",
                               details=f"fields: {list(updates.keys())}")
                        st.success(f"Updated '{u.get('username')}'.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
                else:
                    st.info("No changes to save.")

        # Action buttons — Activate/Deactivate + Delete
        ac1, ac2 = st.columns(2)
        current_act = bool(u.get("is_active"))
        with ac1:
            toggle_label = "⚫ Deactivate" if current_act else "🟢 Reactivate"
            if st.button(toggle_label, key=f"_um_tog_{u['id']}",
                         use_container_width=True,
                         disabled=(current_act and u.get("role") == "director"
                                   and _count_active_directors() <= 1)):
                try:
                    update_user(u["id"], {"is_active": 0 if current_act else 1})
                    _audit("user_deactivate" if current_act else "user_activate",
                           f"user:{u['username']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
        with ac2:
            self_id = (st.session_state.get("_auth_user") or {}).get("id")
            is_self = (self_id == u["id"])
            if st.button("🗑️ Delete permanently", key=f"_um_del_{u['id']}",
                         use_container_width=True, type="secondary",
                         disabled=is_self,
                         help="Cannot delete your own account" if is_self else None):
                st.session_state[f"_um_confirm_del_{u['id']}"] = True
                st.rerun()
            if st.session_state.get(f"_um_confirm_del_{u['id']}"):
                st.warning(f"⚠️ Confirm delete **{u.get('username')}** — this cannot be undone.")
                cc1, cc2 = st.columns(2)
                if cc1.button("Yes, delete", key=f"_um_delyes_{u['id']}",
                              type="primary", use_container_width=True):
                    try:
                        ok = delete_user(u["id"])
                        if ok:
                            _audit("user_delete", f"user:{u['username']}")
                            st.success(f"Deleted {u.get('username')}.")
                        else:
                            st.error("Delete failed — user not found.")
                    except ValueError as ve:
                        st.error(str(ve))
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
                    st.session_state.pop(f"_um_confirm_del_{u['id']}", None)
                    st.rerun()
                if cc2.button("Cancel", key=f"_um_delno_{u['id']}",
                              use_container_width=True):
                    st.session_state.pop(f"_um_confirm_del_{u['id']}", None)
                    st.rerun()


def _count_active_directors() -> int:
    try:
        return sum(1 for u in get_all_users()
                   if u.get("role") == "director" and u.get("is_active"))
    except Exception:
        return 1


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Add new user
# ════════════════════════════════════════════════════════════════════════════

def _render_add_user_tab():
    st.markdown("### ➕ Create New User")
    st.caption("All users authenticate with a PIN (4-8 digits). Username is lowercase and unique.")

    with st.form("_um_add_form", border=True):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Username *", placeholder="e.g. rahul",
                                     help="Lowercase, no spaces. Used to log in.")
            display_name = st.text_input("Display Name *", placeholder="e.g. Rahul Mehta")
            email = st.text_input("Email", placeholder="user@example.com")
        with c2:
            role = st.selectbox("Role *", ROLES,
                                format_func=lambda r: ROLE_LABELS.get(r, r))
            st.caption(ROLE_DESCRIPTIONS.get(role, ""))
            whatsapp = st.text_input("WhatsApp (+91…)", placeholder="+919876543210")
            pin = st.text_input("PIN * (4-8 digits)", type="password",
                                placeholder="Choose a PIN")

        submitted = st.form_submit_button("Create User", type="primary",
                                          use_container_width=True)
        if submitted:
            errors = []
            u = (username or "").strip().lower()
            if not u:
                errors.append("Username required.")
            elif " " in u or not u.replace("_", "").replace(".", "").isalnum():
                errors.append("Username must be lowercase letters / digits / . / _ only.")
            if not display_name.strip():
                errors.append("Display name required.")
            p = (pin or "").strip()
            if not p or not p.isdigit() or not (4 <= len(p) <= 8):
                errors.append("PIN must be 4-8 digits.")
            if u and get_user_by_username(u):
                errors.append(f"Username '{u}' already exists.")

            if errors:
                for e in errors:
                    st.error(e)
                return

            try:
                new_id = insert_user({
                    "username": u,
                    "display_name": display_name.strip(),
                    "role": role,
                    "pin_hash": hash_pin(p),
                    "email": (email or "").strip() or None,
                    "whatsapp_number": (whatsapp or "").strip() or None,
                    "is_active": 1,
                })
                _audit("user_create", f"user:{u}",
                       details=f"role={role}")
                st.success(f"✅ User '{u}' created (id {new_id}). They can log in with their PIN now.")
            except Exception as e:
                st.error(f"Create failed: {e}")

    st.divider()
    with st.expander("📥 Bulk import from CSV"):
        st.caption("CSV columns: `username, display_name, role, pin, email, whatsapp_number`")
        sample = "username,display_name,role,pin,email,whatsapp_number\nrahul,Rahul M,sales,1234,rahul@pps.com,+919876543210\npriya,Priya K,operations,5678,,"
        st.code(sample, language="csv")
        up = st.file_uploader("Upload CSV", type=["csv"], key="_um_bulk_csv")
        if up and st.button("Import", key="_um_bulk_import", type="primary"):
            try:
                df = pd.read_csv(up)
                required = {"username", "display_name", "role", "pin"}
                if not required.issubset(df.columns):
                    st.error(f"Missing columns. Required: {required}")
                    return
                created, skipped = 0, 0
                skipped_reasons = []
                for _, row in df.iterrows():
                    uname = str(row["username"]).strip().lower()
                    if not uname or get_user_by_username(uname):
                        skipped += 1
                        skipped_reasons.append(f"{uname}: duplicate or empty")
                        continue
                    role_val = str(row["role"]).strip().lower()
                    if role_val not in ROLES:
                        skipped += 1
                        skipped_reasons.append(f"{uname}: invalid role {role_val}")
                        continue
                    pin_val = str(row["pin"]).strip()
                    if not pin_val.isdigit() or not (4 <= len(pin_val) <= 8):
                        skipped += 1
                        skipped_reasons.append(f"{uname}: invalid PIN")
                        continue
                    insert_user({
                        "username": uname,
                        "display_name": str(row["display_name"]).strip() or uname,
                        "role": role_val,
                        "pin_hash": hash_pin(pin_val),
                        "email": str(row.get("email", "") or "").strip() or None,
                        "whatsapp_number": str(row.get("whatsapp_number", "") or "").strip() or None,
                        "is_active": 1,
                    })
                    created += 1
                _audit("user_bulk_import", details=f"created={created}, skipped={skipped}")
                st.success(f"✅ Imported {created} users. Skipped {skipped}.")
                if skipped_reasons:
                    with st.expander(f"Skipped details ({skipped})"):
                        for r in skipped_reasons:
                            st.caption(f"• {r}")
            except Exception as e:
                st.error(f"Import failed: {e}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Audit Log
# ════════════════════════════════════════════════════════════════════════════

def _render_audit_tab():
    st.markdown("### 📜 Audit Log")
    st.caption("Every login, logout, and user change is recorded here.")

    logs = get_audit_logs(limit=1000)
    if not logs:
        st.info("No audit events recorded yet.")
        return

    df = pd.DataFrame(logs)
    # Normalize columns
    for col in ("created_at", "username", "action", "resource", "details"):
        if col not in df.columns:
            df[col] = ""

    # Filters
    f1, f2, f3 = st.columns([2, 2, 2])
    with f1:
        actions = sorted(df["action"].dropna().unique().tolist())
        action_f = st.multiselect("Action", actions, default=actions, key="_um_audit_act")
    with f2:
        users = sorted(df["username"].dropna().unique().tolist())
        user_f = st.multiselect("User", users, default=users, key="_um_audit_usr")
    with f3:
        days = st.number_input("Last N days", min_value=1, max_value=365, value=30,
                               key="_um_audit_days")

    cutoff = (_dt.datetime.now() - _dt.timedelta(days=int(days))).strftime("%Y-%m-%d")
    try:
        df = df[df["created_at"].astype(str) >= cutoff]
    except Exception:
        pass
    df = df[df["action"].isin(action_f) & df["username"].isin(user_f)]

    st.caption(f"Showing {len(df)} events (from {len(logs)} total).")

    display_cols = [c for c in ("created_at", "username", "action", "resource", "details")
                    if c in df.columns]
    st.dataframe(df[display_cols].sort_values("created_at", ascending=False),
                 use_container_width=True, hide_index=True, height=450)

    # Export
    csv = df[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button("📥 Export filtered log as CSV", data=csv,
                       file_name=f"pps_audit_{_dt.date.today()}.csv",
                       mime="text/csv", key="_um_audit_dl")


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — Policies & session
# ════════════════════════════════════════════════════════════════════════════

def _render_policies_tab():
    st.markdown("### ⚙️ Access Policies")

    try:
        from settings_engine import get as _gs, save_settings as _ss_save, load_settings as _ss_load
    except Exception as e:
        st.error(f"Settings engine unavailable: {e}")
        return

    current = _ss_load()

    st.markdown("#### 🔒 Session & RBAC")
    p1, p2 = st.columns(2)
    with p1:
        rbac_on = st.toggle("RBAC Enabled (enforce role checks)",
                            value=bool(current.get("rbac_enabled", False)),
                            key="_um_rbac_tog",
                            help="When off, all users have full access. Enable to enforce role restrictions.")
        timeout = st.number_input("Session timeout (minutes)",
                                   min_value=5, max_value=1440,
                                   value=int(current.get("rbac_session_timeout_min", 1440)),
                                   step=5, key="_um_timeout")
    with p2:
        max_fails = st.number_input("Max failed login attempts",
                                     min_value=3, max_value=20,
                                     value=int(current.get("rbac_max_failed_attempts", 5)),
                                     key="_um_maxfails")
        lockout = st.number_input("Lockout duration (minutes)",
                                   min_value=1, max_value=60,
                                   value=int(current.get("rbac_lockout_min", 5)),
                                   key="_um_lockout")

    if st.button("💾 Save policies", type="primary", key="_um_save_policies"):
        try:
            current["rbac_enabled"] = bool(rbac_on)
            current["rbac_session_timeout_min"] = int(timeout)
            current["rbac_max_failed_attempts"] = int(max_fails)
            current["rbac_lockout_min"] = int(lockout)
            _ss_save(current)
            _audit("policy_update",
                   details=f"rbac={rbac_on}, timeout={timeout}m, maxfails={max_fails}, lockout={lockout}m")
            st.success("✅ Policies saved. Changes apply on next login.")
        except Exception as e:
            st.error(f"Save failed: {e}")

    st.divider()

    st.markdown("#### 👁️ Role Permissions Matrix")
    st.caption("What each role can do. Permissions are hardcoded — change via code only.")
    mat = pd.DataFrame({
        "Feature": ["View Dashboards", "Create Quotes & POs", "Edit Customer Data",
                    "Send WhatsApp / Email", "Access Settings", "Manage Users",
                    "View Audit Log", "Reset Anyone's PIN"],
        "Viewer": ["✅", "❌", "❌", "❌", "❌", "❌", "❌", "❌"],
        "Operations": ["✅", "✅", "✅", "❌", "❌", "❌", "❌", "❌"],
        "Sales": ["✅", "✅", "✅", "✅", "❌", "❌", "❌", "❌"],
        "Director": ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅"],
    })
    st.dataframe(mat, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("#### 📊 Current Session")
    auth = st.session_state.get("_auth_user") or {}
    s1, s2, s3 = st.columns(3)
    s1.metric("Logged in as", auth.get("username", "?"))
    s2.metric("Role", ROLE_LABELS.get(auth.get("role"), auth.get("role", "?")))
    last_act = st.session_state.get("_auth_last_activity")
    if last_act:
        mins_since = int((_dt.datetime.now().timestamp() - last_act) / 60)
        s3.metric("Idle time", f"{mins_since} min")
