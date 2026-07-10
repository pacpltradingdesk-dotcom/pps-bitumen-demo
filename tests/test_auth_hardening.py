"""Round-2 auth hardening tests: PBKDF2 hashing, lazy upgrade, throttle, token TTL."""
import hashlib
import time
from pathlib import Path

import pytest

import role_engine as re


def _legacy_sha256(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def test_hash_pin_emits_pbkdf2_format():
    h = re.hash_pin("1234")
    parts = h.split("$")
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) == re._PBKDF2_ITERATIONS
    assert len(parts) == 4


def test_hash_pin_uses_distinct_salts():
    assert re.hash_pin("1234") != re.hash_pin("1234")


def test_verify_pin_roundtrip_pbkdf2():
    h = re.hash_pin("4321")
    valid, needs_upgrade = re.verify_pin("4321", h)
    assert valid is True
    assert needs_upgrade is False


def test_verify_pin_rejects_wrong_pin_pbkdf2():
    h = re.hash_pin("4321")
    valid, needs_upgrade = re.verify_pin("0000", h)
    assert valid is False
    assert needs_upgrade is False


def test_verify_pin_accepts_legacy_and_flags_upgrade():
    valid, needs_upgrade = re.verify_pin("1234", _legacy_sha256("1234"))
    assert valid is True
    assert needs_upgrade is True


def test_verify_pin_rejects_wrong_pin_legacy():
    valid, needs_upgrade = re.verify_pin("9999", _legacy_sha256("1234"))
    assert valid is False
    assert needs_upgrade is False


def test_verify_pin_empty_stored():
    assert re.verify_pin("1234", "") == (False, False)


def test_is_legacy_hash():
    assert re._is_legacy_hash(_legacy_sha256("1234")) is True
    assert re._is_legacy_hash(re.hash_pin("1234")) is False


import sys
import types


@pytest.fixture
def fake_streamlit(monkeypatch):
    st = types.ModuleType("streamlit")
    st.session_state = {}
    st.query_params = {}
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def test_login_upgrades_legacy_hash(fake_streamlit, monkeypatch):
    captured = []

    user = {
        "id": 7, "username": "bob", "role": "sales", "is_active": 1,
        "display_name": "Bob", "pin_hash": _legacy_sha256("1234"),
    }

    import database
    monkeypatch.setattr(database, "get_user_by_username", lambda u: dict(user), raising=False)
    monkeypatch.setattr(database, "update_user", lambda i, d: captured.append((i, d)), raising=False)
    monkeypatch.setattr(database, "insert_audit_log", lambda d: None, raising=False)
    monkeypatch.setattr(re, "_is_rate_limited", lambda u: (False, 0))
    monkeypatch.setattr(re, "_clear_failed_attempts", lambda u: None)

    assert re.login("bob", "1234") is True

    pin_updates = [d for (_i, d) in captured if "pin_hash" in d]
    assert pin_updates, "expected a pin_hash upgrade write"
    assert pin_updates[-1]["pin_hash"].startswith("pbkdf2_sha256$")


def test_login_wrong_pin_no_upgrade(fake_streamlit, monkeypatch):
    captured = []
    user = {
        "id": 7, "username": "bob", "role": "sales", "is_active": 1,
        "display_name": "Bob", "pin_hash": _legacy_sha256("1234"),
    }
    import database
    monkeypatch.setattr(database, "get_user_by_username", lambda u: dict(user), raising=False)
    monkeypatch.setattr(database, "update_user", lambda i, d: captured.append((i, d)), raising=False)
    monkeypatch.setattr(database, "insert_audit_log", lambda d: None, raising=False)
    monkeypatch.setattr(re, "_is_rate_limited", lambda u: (False, 0))
    recorded = []
    monkeypatch.setattr(re, "_record_failed_attempt", lambda u: recorded.append(u))

    assert re.login("bob", "0000") is False
    assert not any("pin_hash" in d for (_i, d) in captured)
    assert recorded == ["bob"]


def test_throttle_tier_5():
    now = 1_000_000.0
    ts = [now - i for i in range(5)]  # 5 fails within seconds
    locked, retry = re._evaluate_throttle(ts, now)
    assert locked is True
    assert 0 < retry <= 300


def test_throttle_tier_10():
    now = 1_000_000.0
    ts = [now - i * 60 for i in range(10)]  # 10 fails within 9 min
    locked, retry = re._evaluate_throttle(ts, now)
    assert locked is True
    assert 300 < retry <= 1800


def test_throttle_tier_15():
    now = 1_000_000.0
    ts = [now - i * 120 for i in range(15)]  # 15 fails within 28 min
    locked, retry = re._evaluate_throttle(ts, now)
    assert locked is True
    assert 1800 < retry <= 7200


def test_throttle_below_threshold():
    now = 1_000_000.0
    ts = [now - i for i in range(4)]  # only 4 fails
    assert re._evaluate_throttle(ts, now) == (False, 0)


def test_throttle_stale_attempts_ignored():
    now = 1_000_000.0
    ts = [now - 400 - i for i in range(5)]  # 5 fails, all older than 5-min window
    assert re._evaluate_throttle(ts, now) == (False, 0)


def test_token_ttl_default(monkeypatch):
    import settings_engine
    monkeypatch.setattr(settings_engine, "get", lambda k, d=None: d, raising=False)
    assert re._get_token_ttl_minutes() == 720


def test_token_ttl_honors_setting(monkeypatch):
    import settings_engine
    monkeypatch.setattr(
        settings_engine, "get",
        lambda k, d=None: 480 if k == "rbac_token_ttl_min" else d, raising=False)
    assert re._get_token_ttl_minutes() == 480


def test_theme_injects_referrer_meta():
    root = Path(__file__).resolve().parents[1]
    src = (root / "theme.py").read_text(encoding="utf-8")
    assert "name=\"referrer\"" in src or "name='referrer'" in src
    assert "no-referrer" in src


def test_nginx_referrer_and_logformat():
    root = Path(__file__).resolve().parents[1]
    src = (root / "deploy" / "hostinger_setup.sh").read_text(encoding="utf-8")
    assert 'Referrer-Policy "no-referrer"' in src
    assert "pps_noqs" in src


def test_add_sales_users_no_plaintext_pin_and_uses_verify():
    root = Path(__file__).resolve().parents[1]
    src = (root / "add_sales_users.py").read_text(encoding="utf-8")
    assert "PIN={u['pin']}" not in src
    assert "PIN: {u['pin']}" not in src
    assert "verify_pin(" in src
    assert 'rec["pin_hash"] == hash_pin(' not in src
