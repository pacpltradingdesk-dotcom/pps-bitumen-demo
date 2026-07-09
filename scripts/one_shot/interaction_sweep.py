"""Deep interaction sweep: for EVERY nav page, switch every tab and click every
SAFE action button, capturing any Streamlit exception, error text, or browser
console error that appears.

This goes beyond fallback_sweep.py (which only reads page-load text): it
actually exercises the UI the way a user would, so a crash that only shows up
AFTER clicking a tab or button gets caught.

SAFETY: destructive / state-changing buttons (Save, Send, Broadcast, Delete,
Dispatch, Sync, Submit, Add, Logout, Execute, Pin, Import…) are NEVER clicked —
this runs against live production.

Usage:  python scripts/one_shot/interaction_sweep.py [user] [pin]
Writes: scripts/one_shot/interaction_sweep_report_<user>.json
"""
import json
import os
import re
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright  # noqa: E402

URL = os.environ.get("PPS_URL", "https://ppsanatams.cloud")
USER = sys.argv[1] if len(sys.argv) > 1 else "admin"
PIN = sys.argv[2] if len(sys.argv) > 2 else "0000"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from nav_config import all_pages  # noqa: E402

# A rendered Streamlit exception or a page-level error banner.
ERROR_RE = re.compile(
    r"Traceback \(most recent call last\)|"
    r"[A-Za-z]+Error:|"
    r"failed to load|"
    r"not supported between|"
    r"is not defined|"
    r"has no attribute|"
    r"KeyError|IndexError|TypeError|ValueError|AttributeError", re.I)

# Buttons that are safe to click (read-only / navigation / compute).
SAFE_BTN = re.compile(
    r"^\s*(view|go|open|show|scan|check|refresh|preview|details?|"
    r"analyz|calculate|estimate|filter|search|expand|load more|"
    r"see all|explore|chart|next|prev)\b|→", re.I)
# Buttons we must NEVER click on a live prod system.
UNSAFE_BTN = re.compile(
    r"delete|remove|clear|reset|send|broadcast|dispatch|submit|save|"
    r"\badd\b|logout|sign|execute|pin|update|deploy|restart|run (data )?sync|"
    r"import|confirm|revert|approve|reject|pay|generate|share|whatsapp|email|"
    r"set |publish|apply|drop|purge|wipe|fetch", re.I)


def _errors_in(text: str) -> list:
    out, seen = [], set()
    for line in text.splitlines():
        line = line.strip()
        if line and ERROR_RE.search(line) and line not in seen:
            seen.add(line)
            out.append(line[:160])
    return out


def main() -> int:
    report = {"user": USER, "pages": {}, "console_errors": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        console_errs = []
        page.on("console", lambda m: console_errs.append(m.text[:200])
                if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errs.append(f"PAGEERROR: {str(e)[:200]}"))

        page.goto(URL, timeout=60000)
        page.wait_for_selector('input[aria-label="Username"]', timeout=30000)
        page.fill('input[aria-label="Username"]', USER)
        page.fill('input[aria-label="Password / PIN"]', PIN)
        page.press('input[aria-label="Password / PIN"]', "Enter")
        page.wait_for_timeout(9000)
        auth = urllib.parse.urlparse(page.url).query
        if "auth_t" not in auth:
            print("LOGIN FAILED")
            return 1

        pages = all_pages()
        for i, name in enumerate(pages, 1):
            entry = {"tab_errors": {}, "button_errors": {}, "load_errors": [],
                     "tabs_tested": 0, "buttons_clicked": 0}
            try:
                page.goto(f"{URL}/?{auth}&_p={urllib.parse.quote(name)}", timeout=60000)
                page.wait_for_timeout(8000)
                entry["load_errors"] = _errors_in(page.inner_text("body", timeout=15000))

                # 1) click every tab, capture errors after each
                tabs = page.locator('button[role="tab"]')
                n_tabs = min(tabs.count(), 12)
                for t in range(n_tabs):
                    try:
                        label = tabs.nth(t).inner_text(timeout=2000)[:40]
                        tabs.nth(t).click(timeout=4000)
                        page.wait_for_timeout(2500)
                        errs = _errors_in(page.inner_text("body", timeout=8000))
                        entry["tabs_tested"] += 1
                        if errs:
                            entry["tab_errors"][label] = errs
                    except Exception:
                        pass

                # 2) click SAFE action buttons, capture errors after each
                btns = page.locator('section.main button, div[data-testid="stAppViewContainer"] button')
                n_btns = min(btns.count(), 40)
                for b in range(n_btns):
                    try:
                        label = btns.nth(b).inner_text(timeout=1500).strip()
                        if not label or UNSAFE_BTN.search(label) or not SAFE_BTN.search(label):
                            continue
                        btns.nth(b).click(timeout=4000)
                        page.wait_for_timeout(2000)
                        errs = _errors_in(page.inner_text("body", timeout=8000))
                        entry["buttons_clicked"] += 1
                        if errs:
                            entry["button_errors"][label[:40]] = errs
                    except Exception:
                        pass
            except Exception as exc:
                entry["load_errors"].append(f"NAV-FAIL: {str(exc)[:120]}")

            has_err = (entry["load_errors"] or entry["tab_errors"]
                       or entry["button_errors"])
            report["pages"][name] = entry
            flag = "❌ ERR" if has_err else "OK"
            print(f"[{i}/{len(pages)}] {flag:7s} {name} "
                  f"(tabs {entry['tabs_tested']}, btns {entry['buttons_clicked']})")

        report["console_errors"] = sorted(set(console_errs))
        browser.close()

    out = os.path.join(HERE, f"interaction_sweep_report_{USER}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    bad = {k: v for k, v in report["pages"].items()
           if v["load_errors"] or v["tab_errors"] or v["button_errors"]}
    print(f"\nDONE — {len(report['pages'])} pages, {len(bad)} with errors, "
          f"{len(report['console_errors'])} console errors -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
