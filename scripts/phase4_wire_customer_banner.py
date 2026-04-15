"""Wire navigation_engine.render_active_context_strip() into the 14
Daily Core pages — right after the Phase 2 refresh_bar block.

Idempotent.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS: list[str] = [
    "pages/home/command_center.py",
    "pages/home/live_market.py",
    "pages/home/opportunities.py",
    "pages/pricing/pricing_calculator.py",
    "command_intel/price_prediction.py",
    "pages/sales/crm_tasks.py",
    "pages/sales/negotiation.py",
    "command_intel/daily_log_panel.py",
    "command_intel/news_dashboard.py",
    "command_intel/market_signals_dashboard.py",
    "pages/intelligence/telegram_analyzer.py",
    "command_intel/document_management.py",
    "command_intel/director_dashboard.py",
    "pages/system/settings_page.py",
]

# The Phase 2 block we anchor to, per file:
PHASE2_ANCHOR = re.compile(
    r"(    # Phase 2: standardized refresh bar.*?\n"
    r"    try:\n"
    r"        from components\.refresh_bar import render_refresh_bar\n"
    r"        render_refresh_bar\([^)]+\)\n"
    r"    except Exception:\n"
    r"        pass\n)",
    re.DOTALL,
)

PHASE4_BLOCK = (
    "    # Phase 4: active customer banner — shows persistent customer context\n"
    "    try:\n"
    "        from navigation_engine import render_active_context_strip\n"
    "        render_active_context_strip()\n"
    "    except Exception:\n"
    "        pass\n"
)


def wire_file(rel_path: str) -> str:
    p = ROOT / rel_path
    if not p.exists():
        return "skip-not-found"
    src = p.read_text(encoding="utf-8")

    if "render_active_context_strip" in src:
        return "skip-already"

    m = PHASE2_ANCHOR.search(src)
    if not m:
        return "skip-no-phase2-anchor"

    # Insert the Phase 4 block immediately after the Phase 2 block
    new_src = src[:m.end()] + PHASE4_BLOCK + src[m.end():]
    p.write_text(new_src, encoding="utf-8")
    return "wired"


def main() -> int:
    print(f"Wiring customer banner into {len(TARGETS)} Daily Core pages…")
    counts: dict[str, int] = {}
    for rel in TARGETS:
        status = wire_file(rel)
        counts[status] = counts.get(status, 0) + 1
        print(f"  [{status:25s}] {rel}")
    print()
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
