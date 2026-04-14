"""Shared pytest fixtures for Phase 1 tests."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pytest


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Fresh SQLite DB with the Phase 1 schema applied."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, company_name TEXT, contact_type TEXT,
            category TEXT, buyer_seller_tag TEXT, city TEXT, state TEXT,
            phone TEXT, email TEXT, gstin TEXT,
            imported_from TEXT
        );
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, category TEXT, city TEXT, state TEXT,
            contact TEXT, gstin TEXT, address TEXT, imported_from TEXT
        );
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, category TEXT, city TEXT, state TEXT,
            contact TEXT, gstin TEXT, pan TEXT, imported_from TEXT
        );
        CREATE TABLE customer_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, company TEXT, city TEXT, state TEXT,
            whatsapp TEXT, email TEXT, category TEXT, notes TEXT,
            source_file TEXT, imported_at TEXT NOT NULL
        );
        CREATE TABLE import_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL, target_table TEXT NOT NULL,
            rows_inserted INTEGER NOT NULL,
            rows_skipped INTEGER NOT NULL,
            rows_errored INTEGER NOT NULL,
            imported_at TEXT NOT NULL,
            reverted INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()
    return db_path
