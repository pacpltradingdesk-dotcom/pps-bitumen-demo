"""
AS-A-USER end-to-end test — drives the REAL login form and REAL nav button
clicks (no session_state auth bypass), the way an actual user experiences the app.

Run: PYTHONIOENCODING=utf-8 .venv\\Scripts\\python.exe test_as_user.py
"""
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from streamlit.testing.v1 import AppTest

PASS, FAIL = "PASS", "FAIL"
results = []


def ss(at, key, default=None):
    """AppTest's session_state has no .get(); access safely via subscript."""
    return at.session_state[key] if key in at.session_state else default


def log(name, ok, detail=""):
    results.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail else ""))


def fresh():
    at = AppTest.from_file("dashboard.py", default_timeout=90)
    at.run()
    return at


def do_login(at, username, pin):
    """Drive the actual login form: fill username + pin, click Sign In."""
    if len(at.text_input) < 2:
        return at, "login form not rendered"
    at.text_input[0].set_value(username)
    at.text_input[1].set_value(pin)
    # The only button on the login screen is the Sign In submit button.
    at.button[0].click().run()
    return at, None


def page_crashed(at):
    return [e.value for e in at.error if "failed to load" in e.value.lower()]


# ════════════════════════════════════════════════════════════════════════
# PART 1 — Real login flow
# ════════════════════════════════════════════════════════════════════════
print("=" * 72)
print("PART 1 — LOGIN FLOW (driving the real form)")
print("=" * 72)

# 1a. admin/0000 — credentials printed on the login page itself
at = fresh()
at, err = do_login(at, "admin", "0000")
admin_in = bool(ss(at,"_auth_user"))
log("admin/0000 (advertised on login page) logs in", admin_in,
    "LOCKED OUT despite correct PIN — account is_active=0" if not admin_in else "ok")

# 1b. janki/1111 — active sales user
at = fresh()
at, err = do_login(at, "janki", "1111")
janki_in = bool(ss(at,"_auth_user"))
role = ss(at,"_auth_role")
log("janki/1111 (sales) logs in", janki_in, f"role={role}")

# 1c. wrong PIN is rejected with an error
at = fresh()
at, err = do_login(at, "janki", "9999")
rejected = not ss(at,"_auth_user")
has_err = any("invalid" in e.value.lower() for e in at.error)
log("janki/wrong-PIN is rejected", rejected and has_err,
    "no _auth_user + 'Invalid' error shown" if (rejected and has_err) else "NOT rejected!")


# ════════════════════════════════════════════════════════════════════════
# PART 2 — Real navigation tour as janki (sales), via button clicks
# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("PART 2 — NAV TOUR as janki (sales): clicking real top-bar + sidebar buttons")
print("=" * 72)

at = fresh()
at, _ = do_login(at, "janki", "1111")
if ss(at,"_welcome_pending"):
    at.session_state["_welcome_pending"] = False

# Top-bar module buttons the user can actually see
tnav_keys = [b.key for b in at.button
             if b.key and b.key.startswith("_tnav_")
             and b.key not in ("_tnav_more",)
             and not b.key.startswith("_tnav_ov_")]
print(f"  visible top-bar modules for sales: {len(tnav_keys)}")

visited, crashes = 0, 0
for tk in tnav_keys:
    btn = [b for b in at.button if b.key == tk]
    if not btn:
        continue
    btn[0].click().run()
    cur = ss(at,"selected_page")
    c = page_crashed(at)
    if c:
        crashes += 1
        log(f"click module {tk}", False, f"{cur}: {c[0][:60]}")
        at = fresh(); at, _ = do_login(at, "janki", "1111")  # recover
        continue
    visited += 1
    # Now click each sidebar feature button within this module
    feat_keys = [b.key for b in at.button
                 if b.key and b.key.startswith("_sidebar_feat_")]
    for fk in feat_keys:
        fb = [b for b in at.button if b.key == fk]
        if not fb:
            continue
        fb[0].click().run()
        cpg = ss(at,"selected_page")
        cc = page_crashed(at)
        if cc:
            crashes += 1
            log(f"sidebar page {cpg}", False, cc[0][:60])
        else:
            visited += 1

log(f"sales nav tour — {visited} pages reached via real clicks", crashes == 0,
    f"{crashes} crash(es)" if crashes else "every clickable page rendered clean")


# ════════════════════════════════════════════════════════════════════════
# PART 3 — RBAC: can a sales user reach an admin page, and what happens?
# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("PART 3 — RBAC: sales user deep-links to an admin page (User Management)")
print("=" * 72)

at = fresh()
at, _ = do_login(at, "janki", "1111")
at.session_state["_nav_goto"] = "👥 User Management"   # what an 'Open X' button fires
at.run()
crash = page_crashed(at)
denied = [e.value for e in at.error if "access denied" in e.value.lower() or "🔒" in e.value]
final = ss(at,"selected_page")
if crash:
    log("sales deep-link to admin page handled gracefully", False,
        f"CRASH instead of deny/redirect: {crash[0][:55]}")
elif denied:
    log("sales deep-link to admin page handled gracefully", True, "clean Access-denied shown")
else:
    log("sales deep-link to admin page handled gracefully", True,
        f"silently redirected to {final}")


# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
ok = sum(1 for _, o in results if o)
print(f"AS-A-USER RESULT: {ok}/{len(results)} checks passed")
for name, o in results:
    if not o:
        print(f"  FAILED: {name}")
sys.exit(0 if ok == len(results) else 1)
