"""
role_engine.py — Role-Based Access Control (RBAC) for PPS Anantam Dashboard
============================================================================
PIN-based auth with 4 roles: Director, Sales, Operations, Viewer.
Session-based via Streamlit session_state. RBAC off by default.
Includes session timeout, failed-login rate-limiting, and page-level gating.

Usage:
    from role_engine import render_login_form, get_current_role, check_role
    if not render_login_form():
        st.stop()  # not authenticated
    if check_role("sales"):
        # show send buttons
"""

import hashlib
import time
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Role Privilege Levels ─────────────────────────────────────────────────────

ROLES = {"director": 4, "admin": 4, "sales": 3, "operations": 2, "viewer": 1}
ROLE_LABELS = {
    "director": "Director",
    "admin": "Director",  # legacy alias
    "sales": "Sales",
    "operations": "Operations",
    "viewer": "Viewer",
}

# ── Rate Limiting State ──────────────────────────────────────────────────────

_failed_attempts: dict[str, list[float]] = {}  # username → [timestamps]
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW = 300  # 5 minutes


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def hash_pin(pin: str) -> str:
    """SHA-256 hash of PIN string."""
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def _is_rate_limited(username: str) -> bool:
    """Check if username has exceeded failed login attempts."""
    key = username.lower().strip()
    now = time.time()
    attempts = _failed_attempts.get(key, [])
    # Prune old attempts outside window
    attempts = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    _failed_attempts[key] = attempts
    return len(attempts) >= _RATE_LIMIT_MAX


def _record_failed_attempt(username: str):
    """Record a failed login attempt."""
    key = username.lower().strip()
    if key not in _failed_attempts:
        _failed_attempts[key] = []
    _failed_attempts[key].append(time.time())


def _clear_failed_attempts(username: str):
    """Clear failed attempts on successful login."""
    key = username.lower().strip()
    _failed_attempts.pop(key, None)


# ── Session Timeout ──────────────────────────────────────────────────────────

def _get_session_timeout_minutes() -> int:
    """Get session timeout from settings."""
    try:
        from settings_engine import get as get_setting
        return int(get_setting("rbac_session_timeout_min", 30))
    except Exception:
        return 30


def _check_session_timeout() -> bool:
    """Check if current session has timed out. Returns True if still valid."""
    try:
        import streamlit as st
        last_activity = st.session_state.get("_auth_last_activity")
        if not last_activity:
            return True  # no tracking yet
        timeout_min = _get_session_timeout_minutes()
        elapsed = time.time() - last_activity
        if elapsed > timeout_min * 60:
            # Session expired — auto-logout
            logout()
            return False
        return True
    except Exception:
        return True


def _touch_session():
    """Update last activity timestamp."""
    try:
        import streamlit as st
        st.session_state["_auth_last_activity"] = time.time()
    except Exception:
        pass


# ── Core Auth Functions ───────────────────────────────────────────────────────

def init_roles():
    """Create default director user (PIN: 0000) if users table is empty.
    Also migrates legacy 'admin' role to 'director'."""
    try:
        from database import get_all_users, insert_user, update_user
        users = get_all_users()
        if not users:
            insert_user({
                "username": "admin",
                "display_name": "Director",
                "role": "director",
                "pin_hash": hash_pin("0000"),
                "is_active": 1,
            })
        else:
            # Migrate legacy 'admin' role → 'director'
            for u in users:
                if u.get("role") == "admin":
                    try:
                        update_user(u["id"], {"role": "director"})
                    except Exception:
                        pass
    except Exception:
        pass


def login(username: str, pin: str) -> bool:
    """Validate credentials and set session_state."""
    username = username.strip().lower()

    # Rate limiting check
    if _is_rate_limited(username):
        return False

    try:
        import streamlit as st
        from database import get_user_by_username, update_user
        user = get_user_by_username(username)
        if user and user.get("is_active") and user.get("pin_hash") == hash_pin(pin):
            # Normalize legacy admin role
            role = user.get("role", "viewer")
            if role == "admin":
                role = "director"
            st.session_state["_auth_user"] = dict(user)
            st.session_state["_auth_role"] = role
            st.session_state["_auth_username"] = user["username"]
            st.session_state["_auth_display"] = user.get("display_name") or user["username"]
            st.session_state["_auth_last_activity"] = time.time()
            update_user(user["id"], {"last_login": _now_ist()})
            _clear_failed_attempts(username)
            # Audit log
            try:
                from database import insert_audit_log
                insert_audit_log({
                    "user_id": user["id"],
                    "username": user["username"],
                    "action": "login",
                    "resource": "dashboard",
                })
            except Exception:
                pass
            return True
        else:
            _record_failed_attempt(username)
    except Exception:
        pass
    return False


def logout():
    """Clear auth from session_state."""
    try:
        import streamlit as st
        username = st.session_state.get("_auth_username", "")
        for key in ["_auth_user", "_auth_role", "_auth_username",
                     "_auth_display", "_auth_last_activity"]:
            st.session_state.pop(key, None)
        # Audit log
        try:
            from database import insert_audit_log
            insert_audit_log({"username": username, "action": "logout", "resource": "dashboard"})
        except Exception:
            pass
    except Exception:
        pass


def get_current_role() -> str:
    """Return current user role. Returns 'director' if RBAC is disabled."""
    try:
        from settings_engine import get as get_setting
        if not get_setting("rbac_enabled", False):
            return "director"
    except Exception:
        return "director"
    try:
        import streamlit as st
        # Check session timeout
        if not _check_session_timeout():
            return "viewer"
        _touch_session()
        return st.session_state.get("_auth_role", "viewer")
    except Exception:
        return "viewer"


def get_current_username() -> str:
    """Return current authenticated username."""
    try:
        import streamlit as st
        return st.session_state.get("_auth_username", "system")
    except Exception:
        return "system"


def check_role(required_role: str) -> bool:
    """Check if current user has at least the required role level."""
    current = get_current_role()
    return ROLES.get(current, 0) >= ROLES.get(required_role, 0)


def require_role(required_role: str) -> bool:
    """Gate function. If user lacks role, shows warning and returns False."""
    if check_role(required_role):
        return True
    try:
        import streamlit as st
        st.warning(f"Access restricted. Requires '{ROLE_LABELS.get(required_role, required_role)}' role or higher.")
    except Exception:
        pass
    return False


def check_page_access(page: str) -> bool:
    """Check if current user can access a given page (via PAGE_ROLE_MAP)."""
    try:
        from nav_config import PAGE_ROLE_MAP
        required = PAGE_ROLE_MAP.get(page, "viewer")
        return check_role(required)
    except ImportError:
        return True


# ── Streamlit UI Components ───────────────────────────────────────────────────

def render_login_form() -> bool:
    """
    Render login form if RBAC is enabled and user not authenticated.
    Returns True if auth OK or RBAC disabled.
    """
    try:
        from settings_engine import get as get_setting
        if not get_setting("rbac_enabled", False):
            return True
    except Exception:
        return True

    import streamlit as st

    # Check session timeout for existing sessions
    if st.session_state.get("_auth_user"):
        if _check_session_timeout():
            _touch_session()
            return True
        else:
            st.info("Session expired. Please login again.")

    st.markdown("""
    <div style="max-width:420px;margin:80px auto;padding:30px 36px;
                background:#0d1b2e;border:1px solid #1e3a5f;border-radius:12px;">
      <div style="text-align:center;margin-bottom:18px;">
        <span style="font-size:2rem;">🏛️</span><br>
        <span style="font-size:1.1rem;font-weight:700;color:#c9a84c;">PPS Anantam</span><br>
        <span style="font-size:0.75rem;color:#94a3b8;">Agentic AI Eco System — Login</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        username = st.text_input("Username", key="_rbac_user", placeholder="admin")
        pin = st.text_input("PIN", type="password", key="_rbac_pin", placeholder="Enter PIN")
        if st.button("Login", type="primary", key="_rbac_login_btn", use_container_width=True):
            uname = username.strip().lower()
            if _is_rate_limited(uname):
                st.error("Too many failed attempts. Please wait 5 minutes.")
            elif login(username, pin):
                st.rerun()
            else:
                st.error("Invalid username or PIN.")
    return False


def render_user_management():
    """Admin-only user management panel (for Settings page)."""
    import streamlit as st

    if not check_role("director"):
        st.warning("Director access required for user management.")
        return

    from database import get_all_users, insert_user, update_user

    st.markdown("#### User Management")
    users = get_all_users()
    if users:
        import pandas as pd
        df = pd.DataFrame(users)
        display_cols = [c for c in ["id", "username", "display_name", "role", "is_active", "last_login"] if c in df.columns]
        st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**Add New User**")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        new_user = st.text_input("Username", key="_um_new_user")
    with ac2:
        new_name = st.text_input("Display Name", key="_um_new_name")
    with ac3:
        new_role = st.selectbox("Role", ["viewer", "operations", "sales", "director"], key="_um_new_role")
    new_pin = st.text_input("PIN (4+ digits)", type="password", key="_um_new_pin")
    if st.button("Create User", type="primary", key="_um_create_btn"):
        if new_user and new_pin and len(new_pin) >= 4:
            try:
                insert_user({
                    "username": new_user.strip().lower(),
                    "display_name": new_name.strip() or new_user.strip(),
                    "role": new_role,
                    "pin_hash": hash_pin(new_pin),
                    "is_active": 1,
                })
                st.success(f"User '{new_user}' created.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")
        else:
            st.warning("Username and PIN (4+ digits) required.")

    st.markdown("---")
    st.markdown("**Reset User PIN**")
    rc1, rc2 = st.columns(2)
    with rc1:
        reset_user = st.text_input("Username to reset", key="_um_reset_user")
    with rc2:
        reset_pin = st.text_input("New PIN", type="password", key="_um_reset_pin")
    if st.button("Reset PIN", key="_um_reset_btn"):
        if reset_user and reset_pin and len(reset_pin) >= 4:
            from database import get_user_by_username
            u = get_user_by_username(reset_user.strip().lower())
            if u:
                update_user(u["id"], {"pin_hash": hash_pin(reset_pin)})
                st.success(f"PIN reset for '{reset_user}'.")
            else:
                st.warning("User not found.")
