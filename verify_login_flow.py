"""End-to-end login simulation for the 3 new sales users."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Streamlit needs a fake session_state for non-runtime calls
import streamlit as st
class _FakeSession(dict):
    def __getattr__(self, k): return self.get(k)
    def __setattr__(self, k, v): self[k] = v
st.session_state = _FakeSession()

from role_engine import login, logout
from settings_engine import get as get_setting

rbac_on = bool(get_setting("rbac_enabled", False))

CASES = [
    ("janki",  "1111", "sales"),
    ("renuka", "2222", "sales"),
    ("riya",   "3333", "sales"),
    ("janki",  "9999", None),    # wrong PIN — must fail
    ("ghost",  "0000", None),    # non-existent — must fail
]

print("=" * 70)
print(f"LOGIN FLOW VERIFICATION  (rbac_enabled = {rbac_on})")
print("=" * 70)
if not rbac_on:
    print("  ⚠  RBAC currently DISABLED in settings.json — login() still validates")
    print("     credentials & writes _auth_role to session_state, but page-gate")
    print("     functions short-circuit to 'director'. Reading session_state")
    print("     directly to verify what login() actually wrote.")
    print()

for user, pin, expected_role in CASES:
    st.session_state.clear()
    ok = login(user, pin)
    # Read what login() actually persisted (independent of RBAC short-circuit)
    actual_role = st.session_state.get("_auth_role") if ok else None
    actual_user = st.session_state.get("_auth_username") if ok else None
    expected_ok = expected_role is not None
    pass_fail = "✅" if (ok == expected_ok and actual_role == expected_role) else "❌"

    if expected_ok:
        gate_str = f"  session._auth_username='{actual_user}'  ._auth_role='{actual_role}'"
    else:
        gate_str = "  (blocked, as expected)"

    print(f"  {pass_fail} login('{user}', '{pin}') → ok={ok}{gate_str}")
    logout()

print()
print("Expected: first 3 ✅ ok=True with _auth_role='sales', last 2 ✅ blocked (ok=False)")
print("=" * 70)
