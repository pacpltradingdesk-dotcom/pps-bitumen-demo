"""Regression: login_page must unpack _is_rate_limited()'s tuple.

Bug (found 20-Jul-2026): login_page.render_login used `elif _is_rate_limited(uname):`.
_is_rate_limited returns (locked, retry_after_sec). A non-empty tuple is ALWAYS
truthy, so `(False, 0)` read as "locked" — every login attempt on the live site
was rejected with "Too many failed attempts", for every user, forever. login()
was never reached, so no failed attempt was ever recorded and no PBKDF2 hash
upgrade could ever run.

Guard: the source must not branch on the bare call, and the not-locked tuple
must evaluate to "allowed".
"""
import ast
import inspect
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_not_locked_tuple_must_not_be_treated_as_locked():
    """(False, 0) means NOT locked — indexing [0] is the only correct read."""
    not_locked = (False, 0)
    assert bool(not_locked) is True, "sanity: a 2-tuple is always truthy"
    assert not_locked[0] is False, "element 0 carries the real answer"


def test_login_page_unpacks_rate_limit_tuple():
    """login_page.py must never branch on the bare _is_rate_limited(...) call."""
    src = (REPO / "login_page.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    offenders = []
    for node in ast.walk(tree):
        # An `if`/`elif` whose test IS the bare call: `if _is_rate_limited(x):`
        if isinstance(node, ast.If) and isinstance(node.test, ast.Call):
            fn = node.test.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name == "_is_rate_limited":
                offenders.append(node.lineno)

    assert not offenders, (
        f"login_page.py branches on the bare _is_rate_limited() tuple at line(s) "
        f"{offenders}. A non-empty tuple is always truthy, which locks out every "
        f"user permanently. Unpack it: `locked, retry = _is_rate_limited(u)`."
    )


def test_role_engine_rate_limit_still_returns_pair():
    """The contract this bug depends on — keep it explicit."""
    from role_engine import _is_rate_limited

    sig = inspect.signature(_is_rate_limited)
    assert len(sig.parameters) == 1
    result = _is_rate_limited("__definitely_not_a_real_user__")
    assert isinstance(result, tuple) and len(result) == 2, (
        "_is_rate_limited must return (locked, retry_after_sec); callers unpack it"
    )
    assert result[0] is False, "an unknown user is not locked out"
