"""Repo-wide guard: no `from <local_module> import <name>` may reference a
name that doesn't exist in that module.

Why this test exists (09-07-2026): TWO user-facing features were silently
dead for months because of phantom imports swallowed by try/except —
`feasibility_engine.get_psu_prices` (Live PSU Rates section always showed
"auto-fetch not available") and `sales_calendar.get_festivals` (festival
greetings always returned []). A phantom import never crashes; it just kills
the feature quietly. This test makes the whole class impossible to ship.

Uses AST (not regex) so multiline imports, aliases and comments can't create
false positives.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

SCAN_DIRS = ["", "command_intel", "components", "pages/home", "pages/sales",
             "pages/pricing", "pages/system", "pages/intelligence",
             "pages/logistics", "quotation_system"]

# One-off/utility scripts excluded — they aren't part of the running app.
EXCLUDE_PREFIXES = ("test_", "debug_", "add_", "fix_", "verify_", "convert_",
                    "inspect_", "generate_", "migrate_")


def _local_modules() -> dict:
    return {p.stem: p for p in ROOT.glob("*.py")}


def _exported_names(path: Path, cache: dict) -> set:
    """Top-level defs/classes/assignments (incl. tuple targets) of a module."""
    if path in cache:
        return cache[path]
    names: set = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        cache[path] = names
        return names
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    names.update(e.id for e in t.elts if isinstance(e, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, (ast.If, ast.Try)):
            # names defined in top-level try/except or if/else blocks
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(sub.name)
                elif isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            names.add(t.id)
                elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for a in sub.names:
                        names.add((a.asname or a.name).split(".")[0])
    cache[path] = names
    return names


def test_no_phantom_local_imports():
    local = _local_modules()
    cache: dict = {}
    problems = []

    for d in SCAN_DIRS:
        for f in sorted((ROOT / d).glob("*.py") if d else ROOT.glob("*.py")):
            if f.name.startswith(EXCLUDE_PREFIXES):
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError as exc:
                problems.append(f"{f.relative_to(ROOT)}: SYNTAX ERROR {exc}")
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level:
                    continue
                mod = (node.module or "").split(".")[0]
                if mod not in local or local[mod] == f:
                    continue
                exported = _exported_names(local[mod], cache)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if alias.name not in exported:
                        problems.append(
                            f"{f.relative_to(ROOT)}:{node.lineno}: "
                            f"from {mod} import {alias.name} — NOT FOUND in {mod}.py"
                        )

    assert not problems, (
        "Phantom imports found (feature will silently die at runtime):\n  "
        + "\n  ".join(problems)
    )
