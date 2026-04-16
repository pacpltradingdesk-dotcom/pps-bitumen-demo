"""
Duplicate function scanner.

Walks every .py file in the repo (excluding .venv, __pycache__, .worktrees,
.pytest_cache) and groups top-level function definitions by (name, body-hash).
Reports any group that appears in 2+ files — those are candidate duplicates.

Body-hash uses ast.dump with attributes stripped so that whitespace, line
numbers, and doc-only differences are ignored; the code logic must be
identical to match.

Run:  python presentation/duplicate_scan.py
"""
from __future__ import annotations
import ast
import hashlib
import sys
from pathlib import Path
from collections import defaultdict


ROOT = Path(__file__).parent.parent
EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".worktrees", ".git", "node_modules"}


def _iter_py_files() -> list[Path]:
    files = []
    for p in ROOT.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        files.append(p)
    return files


def _body_hash(node: ast.FunctionDef) -> str:
    # Drop docstring node if it's the first expression, so a comment-only
    # difference isn't flagged as different code.
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    # Also ignore arg defaults' line numbers by using annotate_fields + no attrs.
    dumped = "\n".join(ast.dump(b, annotate_fields=True, include_attributes=False) for b in body)
    args = ast.dump(node.args, annotate_fields=True, include_attributes=False)
    return hashlib.sha256((args + "|" + dumped).encode()).hexdigest()[:12]


def scan() -> dict[tuple[str, str], list[tuple[Path, int, int]]]:
    """Return {(fn_name, body_hash): [(path, lineno, body_lines), ...]}."""
    groups: dict[tuple[str, str], list[tuple[Path, int, int]]] = defaultdict(list)
    for p in _iter_py_files():
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Skip trivial bodies (just pass / single return) — too noisy.
                body_len = len(node.body)
                if body_len <= 1:
                    continue
                h = _body_hash(node)
                groups[(node.name, h)].append((p.relative_to(ROOT), node.lineno, body_len))
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and len(sub.body) > 1:
                        h = _body_hash(sub)
                        groups[(f"{node.name}.{sub.name}", h)].append((p.relative_to(ROOT), sub.lineno, len(sub.body)))
    return groups


def main() -> int:
    groups = scan()
    dup_groups = [(k, v) for k, v in groups.items() if len(v) >= 2]
    # Sort by (-dup count, name) so the biggest copy-paste offenders show first.
    dup_groups.sort(key=lambda kv: (-len(kv[1]), kv[0][0]))

    if not dup_groups:
        print("No duplicate functions detected.")
        return 0

    print(f"Found {len(dup_groups)} duplicate-function groups\n")
    total_copies = 0
    for (name, h), locs in dup_groups:
        print(f"  {name}  (hash {h}, body-len ~{locs[0][2]} stmts, {len(locs)} copies)")
        for p, ln, _ in locs:
            print(f"    {p}:{ln}")
        total_copies += len(locs) - 1  # one is the "original"
        print()
    print(f"Total redundant copies: {total_copies}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
