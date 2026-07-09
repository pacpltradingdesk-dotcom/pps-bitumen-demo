"""Full-dashboard sweep: open EVERY nav page and flag error/fallback/demo text.

Usage:  python scripts/one_shot/fallback_sweep.py [user] [pin]
Writes: scripts/one_shot/fallback_sweep_report.json (+ .txt summary)

Detects the bug classes found in the 09-07-2026 audits:
  - hard errors surfaced by page try/excepts ("failed to load", Traceback)
  - silent-fallback messages ("not available", "Using static", "unavailable")
  - demo residue ("(Sample)", "Salesman A", "coming soon", "placeholder")
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

SUSPECT = [
    ("ERROR",   r"failed to load|Traceback|ModuleNotFoundError|AttributeError:"
                r"|ImportError|NameError|TypeError:|KeyError:|ValueError:"
                r"|not supported between"),
    ("FALLBACK", r"not available|unavailable|Using static|could not (load|fetch)"
                 r"|auto-fetch|feature.{0,12}disabled"),
    ("DEMO",    r"\(Sample\)|sample data|Salesman [AB]|Manager [AB]|coming soon"
                r"|placeholder|lorem ipsum|dummy data|mock data"),
]
SUSPECT_RE = [(label, re.compile(pat, re.I)) for label, pat in SUSPECT]

# Known-honest strings that match the patterns above but are correct UX.
ALLOWLIST = [
    "hidden (visible to admin/director)",
    "No data available",              # legit empty states
    "Abhi tak koi entry nahi",
]


def flag(text: str) -> list:
    hits = []
    for line in text.splitlines():
        line = line.strip()
        if not line or any(a in line for a in ALLOWLIST):
            continue
        for label, rex in SUSPECT_RE:
            if rex.search(line):
                hits.append({"type": label, "line": line[:160]})
                break
    # dedup lines
    seen, out = set(), []
    for h in hits:
        if h["line"] not in seen:
            seen.add(h["line"])
            out.append(h)
    return out


def main() -> int:
    report = {"user": USER, "pages": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.goto(URL, timeout=60000)
        page.wait_for_selector('input[aria-label="Username"]', timeout=30000)
        page.fill('input[aria-label="Username"]', USER)
        page.fill('input[aria-label="Password / PIN"]', PIN)
        page.press('input[aria-label="Password / PIN"]', "Enter")
        page.wait_for_timeout(9000)
        auth = urllib.parse.urlparse(page.url).query  # auth_t=...
        if "auth_t" not in auth:
            print("LOGIN FAILED")
            return 1

        pages = all_pages()
        for i, name in enumerate(pages, 1):
            q = urllib.parse.quote(name)
            try:
                page.goto(f"{URL}/?{auth}&_p={q}", timeout=60000)
                page.wait_for_timeout(9000)
                body = page.inner_text("body", timeout=15000)
            except Exception as exc:
                report["pages"][name] = {"status": "NAV-FAIL", "error": str(exc)[:120]}
                print(f"[{i}/{len(pages)}] NAV-FAIL {name}")
                continue
            # confirm we actually landed (breadcrumb or page title in body)
            plain = name.split(" ", 1)[-1]
            landed = plain.lower() in body.lower()
            hits = flag(body)
            status = "FLAGGED" if hits else ("OK" if landed else "UNVERIFIED")
            report["pages"][name] = {"status": status, "landed": landed,
                                     "hits": hits}
            print(f"[{i}/{len(pages)}] {status:10s} {name} ({len(hits)} hits)")
        browser.close()

    out = os.path.join(HERE, f"fallback_sweep_report_{USER}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    flagged = {k: v for k, v in report["pages"].items() if v.get("hits")}
    print(f"\nDONE — {len(report['pages'])} pages, {len(flagged)} flagged -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
