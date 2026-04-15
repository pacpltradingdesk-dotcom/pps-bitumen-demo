"""Replacement source for the old sales_parties.json file.

All engines that used to read sales_parties.json now import load_customers()
from this module, which queries the customers table.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

_DB = Path(__file__).resolve().parent / "bitumen_dashboard.db"


def load_customers() -> list[dict]:
    """Return the current customers list as dicts — compatible with the
    old sales_parties.json schema (keys: name, category, city, state,
    contact, gstin, address).
    """
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, category, city, state, contact, "
            "gstin, address FROM customers"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
