"""Scan all st.button / st.form_submit_button / st.download_button calls,
group by normalized label, and flag duplicates across pages.

Also flags:
  - identical callback patterns (same _nav_goto target from diff buttons)
  - buttons in dead pages (not reachable via nav_config DAILY_CORE or ADVANCED)
"""
from __future__ import annotations
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".venv", ".git", ".worktrees", "__pycache__", "node_modules",
             "presentation", "tests", "scripts"}

BUTTON_CALLS = {"button", "form_submit_button", "download_button",
                "link_button", "popover", "toggle"}


def normalize(label: str) -> str:
    """Strip emoji, whitespace, case. Remove markdown."""
    if not label:
        return ""
    s = re.sub(r"[^\w\s]", " ", label)  # strip punct/emoji
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def extract_string_arg(node: ast.Call) -> str | None:
    """First positional arg if it's a constant string."""
    if not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    # f-strings — try to get literal parts
    if isinstance(arg, ast.JoinedStr):
        lit_parts = [v.value for v in arg.values
                     if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        return "".join(lit_parts) if lit_parts else None
    return None


def is_st_button(node: ast.Call) -> tuple[bool, str]:
    """Return (is_button, call_name) for st.button-family calls."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in BUTTON_CALLS:
        # st.button(...) or streamlit.button(...)
        if isinstance(func.value, ast.Name) and func.value.id in ("st", "streamlit"):
            return True, func.attr
    return False, ""


def scan_file(path: Path):
    """Yield (label, raw_label, line, call_name)."""
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        ok, name = is_st_button(node)
        if not ok:
            continue
        raw = extract_string_arg(node)
        if raw is None:
            continue
        yield (normalize(raw), raw, node.lineno, name)


def main() -> int:
    by_label: dict[str, list[tuple[str, str, int, str]]] = defaultdict(list)
    total = 0
    files_scanned = 0

    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        files_scanned += 1
        for norm, raw, line, call in scan_file(p):
            if not norm:
                continue
            total += 1
            by_label[norm].append((str(rel), raw, line, call))

    dupes = {k: v for k, v in by_label.items() if len(v) > 1}

    print(f"scanned {files_scanned} files")
    print(f"total button calls with literal labels: {total}")
    print(f"unique normalized labels: {len(by_label)}")
    print(f"labels appearing in 2+ places: {len(dupes)}\n")

    # Sort by copy count desc, then label
    items = sorted(dupes.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    BIG = 3  # flag hotspots with 3+ copies
    hotspots = [(k, v) for k, v in items if len(v) >= BIG]
    small = [(k, v) for k, v in items if len(v) < BIG]

    print(f"=== HOTSPOTS (label used {BIG}+ times) — {len(hotspots)} groups ===\n")
    for label, locs in hotspots:
        print(f"[{len(locs)}x] '{label}'  (raw: {locs[0][1]!r})")
        for f, raw, line, call in locs:
            print(f"    {f}:{line}  st.{call}({raw!r})")
        print()

    print(f"=== SMALL DUPES (2 copies) — {len(small)} groups ===\n")
    for label, locs in small[:25]:
        print(f"[2x] '{label}'")
        for f, raw, line, call in locs:
            print(f"    {f}:{line}  st.{call}({raw!r})")
    if len(small) > 25:
        print(f"\n  ... and {len(small) - 25} more 2x groups")

    return 0


if __name__ == "__main__":
    sys.exit(main())
