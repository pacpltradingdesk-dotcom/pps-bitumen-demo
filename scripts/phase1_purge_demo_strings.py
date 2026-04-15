"""Replace hardcoded demo placeholder strings across the codebase.

SKIPS: generate_pdf_demos.py, docs/, tests/, scripts/, __pycache__/, .git/
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"docs", "tests", "scripts", "__pycache__", ".git",
             "demo_pdfs", ".bak.archive"}
SKIP_FILES = {"generate_pdf_demos.py"}

# (needle, replacement) — both strings appear inside quotes in source.
REPLACEMENTS: list[tuple[str, str]] = [
    # Placeholder strings shown to the user inside st.text_input placeholders
    ("e.g. L&T Construction", "e.g. customer name"),
    ("e.g. Shree Ganesh Infra", "e.g. customer name"),
    ("e.g. Highway Builders", "e.g. customer name"),
    # Example inline text in business knowledge — replace with a generic label
    ("A salesperson talking to L&T Construction", "A salesperson talking to a major contractor"),
    # Placeholder city hardcoding
    ('"L&T Construction": "Mumbai"', '# placeholder removed — load live from DB'),
]


def process(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text
    for needle, rep in REPLACEMENTS:
        text = text.replace(needle, rep)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def main() -> int:
    changed = []
    for p in ROOT.rglob("*.py"):
        rel_parts = set(p.relative_to(ROOT).parts)
        if rel_parts & SKIP_DIRS or p.name in SKIP_FILES:
            continue
        if process(p):
            changed.append(str(p.relative_to(ROOT)))
    print(f"Modified {len(changed)} files:")
    for c in changed:
        print(f"  - {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
