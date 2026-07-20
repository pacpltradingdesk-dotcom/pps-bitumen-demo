"""Permanent guard against the tuple-truthiness auth bug (20-Jul-2026).

login_page.render_login did `elif _is_rate_limited(uname):`. _is_rate_limited
returns a 2-tuple, and a non-empty tuple is ALWAYS truthy, so (False, 0) read
as "locked". Every login on the live site was rejected with a plausible-looking
"Too many failed attempts" for 10 days. No crash, no warning, no type error.

Three layers of defence, one per test group below:
  1. the result types define __bool__, so the bare call means the SAFE thing
  2. no module anywhere may branch on a bare call to these functions
  3. there is exactly one login UI, so a fix cannot land on an unreachable copy
"""
import ast
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]

# Functions whose bare 2-tuple result was (or would be) a silent always-true.
TUPLE_RESULT_FUNCS = {"_is_rate_limited", "verify_pin", "_evaluate_throttle"}

SKIP_PARTS = {"__pycache__", ".venv", "etc", "node_modules", ".git"}


def _python_files():
    for p in REPO.rglob("*.py"):
        if not SKIP_PARTS.isdisjoint(p.parts):
            continue
        yield p


# ── Layer 1: the types defend themselves ─────────────────────────────────────

def test_rate_limit_is_falsy_when_not_locked():
    from role_engine import RateLimit

    assert not RateLimit(False, 0), "not-locked must be falsy"
    assert RateLimit(True, 300), "locked must be truthy"
    # still a plain tuple for every existing caller
    locked, retry = RateLimit(True, 300)
    assert (locked, retry) == (True, 300)
    assert RateLimit(False, 0) == (False, 0)


def test_pin_check_is_falsy_when_invalid():
    """A bare `if verify_pin(...)` must never accept a wrong password."""
    from role_engine import PinCheck

    assert not PinCheck(False, False), "invalid PIN must be falsy — else auth bypass"
    assert PinCheck(True, False), "valid PIN must be truthy"
    valid, needs_upgrade = PinCheck(True, True)
    assert (valid, needs_upgrade) == (True, True)


def test_real_functions_return_self_defending_types():
    from role_engine import PinCheck, RateLimit, _evaluate_throttle, _is_rate_limited, verify_pin

    assert isinstance(_is_rate_limited("__no_such_user__"), RateLimit)
    assert isinstance(_evaluate_throttle([], 0.0), RateLimit)
    assert isinstance(verify_pin("x", ""), PinCheck)
    # the exact shape that broke production
    assert not _is_rate_limited("__no_such_user__"), "unknown user must not read as locked"
    assert not verify_pin("wrong", ""), "empty stored hash must not read as valid"


# ── Layer 2: nobody may branch on the bare call ──────────────────────────────

def test_no_module_branches_on_bare_tuple_call():
    offenders = []
    for path in _python_files():
        # tests assert on these results deliberately (that is what Layer 1 checks)
        if "tests" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            tests = []
            if isinstance(node, (ast.If, ast.While, ast.IfExp)):
                tests = [node.test]
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                tests = [node.operand]
            elif isinstance(node, ast.BoolOp):
                tests = list(node.values)
            for t in tests:
                if not isinstance(t, ast.Call):
                    continue
                name = getattr(t.func, "id", None) or getattr(t.func, "attr", None)
                if name in TUPLE_RESULT_FUNCS:
                    rel = path.relative_to(REPO)
                    offenders.append(f"{rel}:{t.lineno} branches on bare {name}()")

    assert not offenders, (
        "Branching on the bare call hides which field is being tested:\n  "
        + "\n  ".join(offenders)
        + "\nUnpack it — `locked, retry = _is_rate_limited(u)` — or read the field."
    )


# ── Layer 3: exactly one login UI ────────────────────────────────────────────

def test_only_one_module_renders_a_login_form():
    """A second login form is how the 09-Jul fix shipped to an unreachable copy."""
    renderers = []
    for path in _python_files():
        if "tests" in path.parts or "presentation" in path.parts:
            continue
        # browser-driving harnesses type credentials but are not app UI
        if path.name.startswith(("browser_test", "debug_", "verify_", "add_")):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if 'type="password"' not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        # AST, not substring: `render_login()` also contains "login("
        calls_login = any(
            isinstance(n, ast.Call) and getattr(n.func, "id", None) == "login"
            for n in ast.walk(tree)
        )
        if calls_login:
            renderers.append(str(path.relative_to(REPO)))

    assert renderers == ["login_page.py"], (
        f"Expected login_page.py to be the only login UI, found: {renderers}. "
        "Duplicate login forms let a fix land on the copy nobody sees."
    )


@pytest.mark.parametrize("caller", ["dashboard.py", "role_engine.py"])
def test_login_gates_route_through_the_single_form(caller):
    """Both gates must reach login_page.render_login, directly or by delegation."""
    text = (REPO / caller).read_text(encoding="utf-8", errors="ignore")
    assert "render_login" in text, f"{caller} lost its login gate"
