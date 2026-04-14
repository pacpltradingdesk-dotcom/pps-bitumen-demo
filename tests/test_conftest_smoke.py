"""Smoke test: tmp_db fixture produces an empty, correctly-shaped DB."""
from __future__ import annotations
import sqlite3


def test_tmp_db_fixture(tmp_db):
    conn = sqlite3.connect(tmp_db)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        expected = {"contacts", "customers", "suppliers",
                    "customer_profiles", "import_history"}
        assert expected.issubset(tables)
        for t in expected:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            assert n == 0
    finally:
        conn.close()
