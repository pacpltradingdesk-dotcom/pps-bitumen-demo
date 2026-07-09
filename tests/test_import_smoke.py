"""Every app module must import without crashing.

A module that dies at import (syntax error, missing dependency, bad top-level
code) takes its whole page down with a blank/broken screen — and with this
codebase's try/except-everywhere style, often silently. This smoke test
imports every root engine, command_intel dashboard and pages module in a
separate subprocess (so scheduler threads or streamlit side effects can't
leak into the test run) and fails with the module name + error.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Entry scripts and one-off utilities — not importable-by-design.
EXCLUDE = {"dashboard.py", "showcase_standalone.py", "streamlit_app.py",
           "auto_patcher.py", "smart_inspect.py"}
EXCLUDE_PREFIXES = ("test_", "debug_", "add_", "fix_", "verify_", "convert_",
                    "inspect_", "generate_", "migrate_", "new ")

SCAN = [("", "*.py"), ("command_intel", "*.py"), ("components", "*.py"),
        ("pages/home", "*.py"), ("pages/sales", "*.py"),
        ("pages/pricing", "*.py"), ("pages/system", "*.py"),
        ("pages/intelligence", "*.py"), ("pages/logistics", "*.py")]

_RUNNER = r"""
import importlib, sys, warnings
warnings.filterwarnings("ignore")
failures = []
for name in sys.argv[1:]:
    try:
        importlib.import_module(name)
    except Exception as exc:
        failures.append(f"{name}: {type(exc).__name__}: {exc}")
if failures:
    print("\n".join(failures))
    sys.exit(1)
"""


def _module_names() -> list[str]:
    names = []
    for d, pat in SCAN:
        for f in sorted((ROOT / d).glob(pat) if d else ROOT.glob(pat)):
            if f.name in EXCLUDE or f.name.startswith(EXCLUDE_PREFIXES):
                continue
            if f.stem == "__init__":
                continue
            names.append(f"{d.replace('/', '.')}.{f.stem}" if d else f.stem)
    return names


def test_all_app_modules_import_cleanly():
    names = _module_names()
    assert len(names) > 100, f"scan looks broken — only {len(names)} modules found"
    # One subprocess for the whole batch keeps runtime sane; daemon threads
    # started by imports die with the subprocess.
    import os
    env = dict(os.environ, PYTHONUTF8="1")   # match the UTF-8 Linux prod box
    proc = subprocess.run(
        [sys.executable, "-c", _RUNNER, *names],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
        encoding="utf-8", errors="replace", env=env,
        stdin=subprocess.DEVNULL,   # pytest on Windows has no usable stdin handle
    )
    assert proc.returncode == 0, (
        "Modules failed to import:\n" + (proc.stdout or proc.stderr)
    )
