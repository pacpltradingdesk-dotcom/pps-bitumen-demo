import os, sqlite3, tempfile, importlib
import pytest


def _fresh_db(monkeypatch):
    """Point database.py at a temp DB file and init schema."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    import database
    monkeypatch.setattr(database, "DB_PATH", tmp.name, raising=False)
    # _get_conn reads DB_PATH at call time
    database.init_db()
    return database, tmp.name


def test_calling_tables_created(monkeypatch):
    database, path = _fresh_db(monkeypatch)
    con = sqlite3.connect(path)
    tables = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "calling_sheets" in tables
    assert "calling_sheet_rows" in tables
    cols_sheets = {c[1] for c in con.execute("PRAGMA table_info(calling_sheets)")}
    assert {"owner_username", "sheet_date", "title", "total_rows"} <= cols_sheets
    cols_rows = {c[1] for c in con.execute("PRAGMA table_info(calling_sheet_rows)")}
    assert {"sheet_id", "owner_username", "lead_name", "phone", "call_status",
            "outcome", "remark", "followup_date", "extra",
            "carried_from_row_id"} <= cols_rows
    con.close()


def test_calling_tables_in_valid_tables():
    import database
    assert "calling_sheets" in database._VALID_TABLES
    assert "calling_sheet_rows" in database._VALID_TABLES
