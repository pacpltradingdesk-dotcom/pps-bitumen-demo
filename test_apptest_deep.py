"""
DEEP AppTest sweep — render every nav page through dashboard.py for a given role
and report, per page: hard exceptions, st.error crashes, in-app warnings, RBAC
access-denials (expected, not a bug), and render-richness (element count) to
catch silently-empty pages.

Usage: PYTHONIOENCODING=utf-8 .venv\\Scripts\\python.exe test_apptest_deep.py <role>
  role in {director, sales, operations, viewer}; default director.
Not a pytest file (prints a report + sys.exit code).
"""
import sys
import time
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from streamlit.testing.v1 import AppTest
from nav_config import MODULE_NAV, get_module_for_page

ROLE = (sys.argv[1] if len(sys.argv) > 1 else "director").strip().lower()
RICHNESS_FLOOR = 3  # pages rendering fewer top-level elements than this look empty


def collect_pages():
    pages, seen = [], set()
    for mod in MODULE_NAV.values():
        for tab in mod.get("tabs", []):
            p = tab.get("page")
            if p and p not in seen:
                seen.add(p)
                pages.append(p)
    return pages


def seed_auth(at, role):
    at.session_state["_auth_user"] = {"username": role, "name": role.title(), "role": role}
    at.session_state["_auth_role"] = role
    at.session_state["_auth_username"] = role
    at.session_state["_auth_last_activity"] = time.time()


def richness(at):
    """Proxy for 'did this page render real content' — count visible elements."""
    total = 0
    for kind in ("markdown", "title", "header", "subheader", "metric", "dataframe",
                 "table", "button", "selectbox", "text_input", "json", "text",
                 "info", "caption", "checkbox", "radio", "tabs", "expander"):
        try:
            total += len(getattr(at, kind))
        except Exception:
            pass
    return total


def run_page(page, role):
    at = AppTest.from_file("dashboard.py", default_timeout=60)
    seed_auth(at, role)
    at.session_state["selected_page"] = page
    at.session_state["_active_module"] = get_module_for_page(page)
    try:
        at.run()
    except Exception as e:
        return {"status": "EXCEPTION", "detail": f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}",
                "warns": [], "rich": 0}

    if at.exception:
        ex = at.exception[0]
        return {"status": "EXCEPTION", "detail": f"{getattr(ex,'exc_type','?')}: {getattr(ex,'message',ex)}",
                "warns": [], "rich": richness(at)}

    errs = [e.value for e in at.error]
    warns = [w.value for w in at.warning]
    rich = richness(at)

    # st.error has DUAL use here: real crashes AND red alert banners (SOS expiry,
    # high-risk supplier). Only treat it as a crash if it carries failure language.
    CRASH_KW = ("failed to load", "failed:", "traceback", "exception",
                "could not", "unable to", "no such", "not found:")
    denied = [e for e in errs if "access denied" in e.lower() or "🔒" in e]
    real_errs = [e for e in errs
                 if e not in denied and any(k in e.lower() for k in CRASH_KW)]

    if real_errs:
        status = "ERROR"
        detail = " | ".join(real_errs[:3])
    elif denied:
        status = "DENIED"
        detail = denied[0][:80]
    elif rich < RICHNESS_FLOOR:
        status = "THIN"
        detail = f"only {rich} elements rendered — possibly empty/broken"
    else:
        status = "OK"
        detail = ""
    return {"status": status, "detail": detail, "warns": warns, "rich": rich}


def main():
    pages = collect_pages()
    print(f"DEEP AppTest sweep — role={ROLE!r} — {len(pages)} pages")
    print("=" * 72)
    buckets = {"OK": [], "DENIED": [], "THIN": [], "ERROR": [], "EXCEPTION": []}
    all_warns = {}
    for i, page in enumerate(pages, 1):
        r = run_page(page, ROLE)
        buckets[r["status"]].append((page, r["detail"]))
        for w in r["warns"]:
            all_warns[w] = all_warns.get(w, 0) + 1
        flag = "" if r["status"] == "OK" else f"  -> {r['detail']}"
        print(f"[{i:>2}/{len(pages)}] {r['status']:<9} rich={r['rich']:>3}  {page}{flag}")

    print("=" * 72)
    print(f"role={ROLE}: OK={len(buckets['OK'])} DENIED={len(buckets['DENIED'])} "
          f"THIN={len(buckets['THIN'])} ERROR={len(buckets['ERROR'])} EXCEPTION={len(buckets['EXCEPTION'])}")

    for cat in ("EXCEPTION", "ERROR", "THIN"):
        if buckets[cat]:
            print(f"\n--- {cat} ---")
            for page, detail in buckets[cat]:
                print(f"  [{cat}] {page}: {detail}")

    if all_warns:
        print(f"\n--- IN-APP WARNINGS ({len(all_warns)} unique) ---")
        for w, n in sorted(all_warns.items(), key=lambda x: -x[1]):
            print(f"  x{n}: {w[:100]}")

    # Only hard failures fail the run; DENIED/THIN are informational.
    bad = len(buckets["EXCEPTION"]) + len(buckets["ERROR"])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
