"""
Headless AppTest sweep — render every nav page through dashboard.py with an
authenticated (director) session and report any page that crashes.

Run: .venv\\Scripts\\python.exe test_apptest_sweep.py
Not a pytest file (prints a report + sys.exit code).
"""
import sys
import time
import traceback

# Windows console defaults to cp1252, which can't print emoji page names.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from streamlit.testing.v1 import AppTest
from nav_config import MODULE_NAV, get_module_for_page


def collect_pages():
    pages, seen = [], set()
    for mod in MODULE_NAV.values():
        for tab in mod.get("tabs", []):
            p = tab.get("page")
            if p and p not in seen:
                seen.add(p)
                pages.append(p)
    return pages


def seed_auth(at):
    """Set the session_state keys role_engine/login_page require to pass the gate."""
    at.session_state["_auth_user"] = {"username": "admin", "name": "Admin", "role": "director"}
    at.session_state["_auth_role"] = "director"
    at.session_state["_auth_username"] = "admin"
    at.session_state["_auth_last_activity"] = time.time()


def run_page(page):
    """Return (status, detail). status in {OK, EXCEPTION, ERROR}."""
    at = AppTest.from_file("dashboard.py", default_timeout=60)
    seed_auth(at)
    at.session_state["selected_page"] = page
    # Mirror real navigation: clicking a nav item always sets BOTH the page and
    # its owning module. Without this they desync and the top bar renders twice.
    at.session_state["_active_module"] = get_module_for_page(page)
    try:
        at.run()
    except Exception as e:  # uncaught crash during render
        return "EXCEPTION", f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}"

    if at.exception:
        ex = at.exception[0]
        return "EXCEPTION", f"{getattr(ex, 'exc_type', '?')}: {getattr(ex, 'message', ex)}"

    # Soft crashes: _safe_render wraps handlers and emits st.error "... failed to load"
    bad = [e.value for e in at.error
           if "failed to load" in e.value.lower() or "traceback" in e.value.lower()]
    if bad:
        return "ERROR", " | ".join(bad[:3])
    return "OK", ""


def main():
    pages = collect_pages()
    print(f"AppTest sweep over {len(pages)} nav pages\n" + "=" * 70)
    ok, problems = 0, []
    for i, page in enumerate(pages, 1):
        status, detail = run_page(page)
        if status == "OK":
            ok += 1
            print(f"[{i:>2}/{len(pages)}] OK   {page}")
        else:
            problems.append((page, status, detail))
            print(f"[{i:>2}/{len(pages)}] {status:<9} {page}\n        -> {detail}")

    print("=" * 70)
    print(f"RESULT: {ok}/{len(pages)} pages rendered clean, {len(problems)} problem(s)")
    if problems:
        print("\n--- PROBLEM PAGES ---")
        for page, status, detail in problems:
            print(f"  [{status}] {page}: {detail}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
