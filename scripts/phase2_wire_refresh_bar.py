"""Wire render_refresh_bar() into the 14 Daily Core pages' render() fns.

Idempotent: skips any file that already imports refresh_bar.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (file_path, page_key, render_fn_name)
TARGETS: list[tuple[str, str, str]] = [
    ("pages/home/command_center.py",          "command_center",     "render"),
    ("pages/home/live_market.py",             "live_market",        "render"),
    ("pages/home/opportunities.py",           "opportunities",      "render"),
    ("pages/pricing/pricing_calculator.py",   "pricing_calculator", "render"),
    ("command_intel/price_prediction.py",     "price_prediction",   "render"),
    ("pages/sales/crm_tasks.py",              "crm_tasks",          "render"),
    ("pages/sales/negotiation.py",            "negotiation",        "render"),
    ("command_intel/daily_log_panel.py",      "daily_log",          "render"),
    ("command_intel/news_dashboard.py",       "news",               "render"),
    ("command_intel/market_signals_dashboard.py", "market_signals", "render"),
    ("pages/intelligence/telegram_analyzer.py", "telegram_analyzer","render"),
    ("command_intel/document_management.py",  "documents",          "render_purchase_order"),
    ("command_intel/director_dashboard.py",   "director_brief",     "render"),
    ("pages/system/settings_page.py",         "settings",           "render"),
]

INSERT_TEMPLATE = (
    "    # Phase 2: standardized refresh bar (clears caches + reruns)\n"
    "    try:\n"
    "        from components.refresh_bar import render_refresh_bar\n"
    "        render_refresh_bar({page_key!r})\n"
    "    except Exception:\n"
    "        pass\n"
)


def wire_file(rel_path: str, page_key: str, fn_name: str) -> str:
    """Return status string: 'wired' | 'skip-already' | 'skip-not-found' | 'error'."""
    p = ROOT / rel_path
    if not p.exists():
        return "skip-not-found"
    src = p.read_text(encoding="utf-8")

    # Idempotence guard: only skip if THIS page_key already wired.
    marker = f"render_refresh_bar({page_key!r})"
    marker_dq = f'render_refresh_bar("{page_key}")'
    if marker in src or marker_dq in src:
        return "skip-already"

    # Find the target `def fn_name(...):\n` line — allow args + type hints
    pattern = re.compile(
        rf"^(?P<decl>def\s+{re.escape(fn_name)}\s*\([^)]*\)[^:]*:)[ \t]*\n",
        re.MULTILINE,
    )
    m = pattern.search(src)
    if not m:
        return f"skip-not-found (no {fn_name}())"

    # Insertion happens immediately after the def line, but SKIP over any
    # docstring that starts on the next non-blank line.
    insert_at = m.end()
    # Peek ahead: if the very next non-blank line starts with ''' or \"\"\",
    # advance past the closing quote.
    tail = src[insert_at:]
    ds_match = re.match(r"[ \t]*(?P<q>\"\"\"|''')", tail)
    if ds_match:
        q = ds_match.group("q")
        closing = tail.find(q, ds_match.end())
        if closing != -1:
            # advance to the end of that line
            end_line = tail.find("\n", closing) + 1
            insert_at += end_line

    new_src = src[:insert_at] + INSERT_TEMPLATE.format(page_key=page_key) + src[insert_at:]
    p.write_text(new_src, encoding="utf-8")
    return "wired"


def main() -> int:
    print(f"Wiring {len(TARGETS)} Daily Core pages…")
    results: dict[str, int] = {}
    for rel, key, fn in TARGETS:
        status = wire_file(rel, key, fn)
        results[status] = results.get(status, 0) + 1
        print(f"  [{status:18s}] {rel}  ({key})")
    print()
    for k, v in sorted(results.items()):
        print(f"  {k}: {v}")
    return 0 if "error" not in results else 1


if __name__ == "__main__":
    sys.exit(main())
