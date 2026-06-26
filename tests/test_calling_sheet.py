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


def test_create_and_read_sheet(monkeypatch):
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)  # pick up patched DB_PATH via database module
    rows = [
        {"lead_name": "Ashoka Buildcon", "phone": "9812345678",
         "company": "Ashoka", "city": "Pune", "extra": {"zone": "West"}},
        {"lead_name": "L&T Roads", "phone": "9800000000",
         "company": "L&T", "city": "Mumbai", "extra": {}},
    ]
    sid = eng.create_sheet("rahul", "Rahul", "2026-06-26",
                           "Test Sheet", "leads.csv", rows)
    assert isinstance(sid, int) and sid > 0

    sheet = eng.get_sheet(sid)
    assert sheet["owner_username"] == "rahul"
    assert sheet["total_rows"] == 2

    got = eng.get_rows(sid)
    assert len(got) == 2
    assert got[0]["call_status"] == "Pending"
    assert got[0]["extra"] == {"zone": "West"}   # JSON round-trips to dict

    sheets = eng.list_sheets("rahul")
    assert len(sheets) == 1 and sheets[0]["id"] == sid
    assert eng.list_sheets("someone_else") == []


def test_detect_columns():
    import calling_sheet_engine as eng
    m = eng.detect_columns(["Customer Name", "Mobile No", "Firm", "Town", "Notes"])
    assert m["lead_name"] == "Customer Name"
    assert m["phone"] == "Mobile No"
    assert m["company"] == "Firm"
    assert m["city"] == "Town"


def test_normalize_rows_puts_unmapped_in_extra():
    import pandas as pd
    import calling_sheet_engine as eng
    df = pd.DataFrame([
        {"Customer Name": "ABC", "Mobile No": "9811111111", "Region": "West"},
        {"Customer Name": "", "Mobile No": "", "Region": "East"},  # empty -> skip
    ])
    m = eng.detect_columns(list(df.columns))
    rows = eng.normalize_rows(df, m)
    assert len(rows) == 1
    assert rows[0]["lead_name"] == "ABC"
    assert rows[0]["phone"] == "9811111111"
    assert rows[0]["extra"]["Region"] == "West"


def test_update_row_and_summary(monkeypatch):
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    sid = eng.create_sheet("rahul", "Rahul", "2026-06-26", "S", "f.csv", [
        {"lead_name": "A", "phone": "1"}, {"lead_name": "B", "phone": "2"},
    ])
    r0 = eng.get_rows(sid)[0]
    eng.update_row(r0["id"], {"call_status": "Connected",
                              "outcome": "Interested", "remark": "keen"})
    updated = [r for r in eng.get_rows(sid) if r["id"] == r0["id"]][0]
    assert updated["call_status"] == "Connected"
    assert updated["outcome"] == "Interested"
    assert updated["remark"] == "keen"
    assert updated["called_at"]  # stamped

    s = eng.sheet_summary(sid)
    assert s["total"] == 2
    assert s["called"] == 1
    assert s["pending"] == 1
    assert s["connected"] == 1
    assert s["conversions"] == 1


def test_carry_over(monkeypatch):
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    # yesterday: 2 rows, mark one Connected
    sid_y = eng.create_sheet("rahul", "Rahul", "2026-06-25", "Y", "y.csv", [
        {"lead_name": "A", "phone": "1"}, {"lead_name": "B", "phone": "2"},
    ])
    a = eng.get_rows(sid_y)[0]
    eng.update_row(a["id"], {"call_status": "Connected"})

    n = eng.carry_over_pending("rahul", "Rahul", "2026-06-26")
    assert n == 1  # only the pending one (B) carried

    today = [s for s in eng.list_sheets("rahul") if s["sheet_date"] == "2026-06-26"][0]
    trows = eng.get_rows(today["id"])
    assert len(trows) == 1
    assert trows[0]["lead_name"] == "B"
    assert trows[0]["carried_from_row_id"] is not None

    # idempotent: running again carries nothing new
    assert eng.carry_over_pending("rahul", "Rahul", "2026-06-26") == 0
