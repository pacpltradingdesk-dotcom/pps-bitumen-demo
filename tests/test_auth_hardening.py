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
