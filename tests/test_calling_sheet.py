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


def test_calling_sheet_is_sales_gated():
    # Lives in the Price & Info (viewer) module for prominence, but a per-tab
    # role override keeps it sales-only so operations/viewer can't open it.
    import importlib, nav_config
    importlib.reload(nav_config)
    assert nav_config.PAGE_ROLE_MAP["\U0001f4de Daily Calling Sheet"] == "sales"
    # other Price & Info pages stay viewer-level
    assert nav_config.PAGE_ROLE_MAP["\U0001f4cb Director Briefing"] == "viewer"


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


def test_create_sheet_coerces_non_string_owner_name(monkeypatch):
    # Regression: dashboard passed the _auth_user dict as owner_name -> SQLite
    # "binding parameter ... type 'dict' is not supported". Engine must coerce.
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    sid = eng.create_sheet("rahul", {"username": "rahul", "role": "director"},
                           "2026-06-26", "S", "f.csv",
                           [{"lead_name": "A", "phone": "1"}])
    assert isinstance(sid, int) and sid > 0
    assert eng.get_sheet(sid)["owner_name"] == "rahul"  # fell back to username


def test_add_rows_appends_to_existing_sheet(monkeypatch):
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    sid = eng.create_sheet("rahul", "Rahul", "2026-06-26", "S", "f.csv",
                           [{"lead_name": "A", "phone": "1"}])
    assert eng.sheet_summary(sid)["total"] == 1
    added = eng.add_rows(sid, "rahul",
                         [{"lead_name": "B", "phone": "2"},
                          {"lead_name": "C", "phone": "3"}])
    assert added == 2
    assert eng.sheet_summary(sid)["total"] == 3       # merged, not a new sheet
    assert eng.get_sheet(sid)["total_rows"] == 3
    names = [r["lead_name"] for r in eng.get_rows(sid)]
    assert names == ["A", "B", "C"]


def test_delete_sheet_owner_guard(monkeypatch):
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    sid = eng.create_sheet("rahul", "Rahul", "2026-06-26", "S", "f.csv",
                           [{"lead_name": "A", "phone": "1"}])
    assert eng.get_sheet(sid) is not None
    # wrong owner cannot delete
    assert eng.delete_sheet(sid, owner_username="someone_else") is False
    assert eng.get_sheet(sid) is not None
    # correct owner deletes sheet + its rows
    assert eng.delete_sheet(sid, owner_username="rahul") is True
    assert eng.get_sheet(sid) is None
    assert eng.get_rows(sid) == []


def test_excel_multi_sheet_pick(monkeypatch):
    import io as _io
    import pandas as pd
    import calling_sheet_engine as eng
    bio = _io.BytesIO()
    with pd.ExcelWriter(bio) as w:
        pd.DataFrame({"x": [1]}).to_excel(w, sheet_name="README", index=False)
        pd.DataFrame({"Person Name": ["A"], "Phone Number": ["9812345678"],
                      "Company Name": ["Co"], "City": ["Pune"]}
                     ).to_excel(w, sheet_name="Hot Leads", index=False)
    data = bio.getvalue()
    assert eng.excel_sheet_names(data, "f.xlsx") == ["README", "Hot Leads"]
    assert eng.excel_sheet_names(b"a,b\n1,2", "f.csv") == []  # csv -> no sheets
    df = eng.parse_file(data, "f.xlsx", sheet_name="Hot Leads")
    assert "Person Name" in df.columns and len(df) == 1
    m = eng.detect_columns(list(df.columns))
    assert m["lead_name"] == "Person Name" and m["phone"] == "Phone Number"


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


def test_carry_over_no_duplicate_leads_across_multiple_days(monkeypatch):
    # Regression: a never-called lead stays Pending on every intermediate day,
    # so carrying day1->day2->day3 must NOT produce 2 copies on day3.
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    eng.create_sheet("r", "R", "2026-06-24", "D1", "f.csv",
                     [{"lead_name": "A", "phone": "111"}])
    eng.carry_over_pending("r", "R", "2026-06-25")
    eng.carry_over_pending("r", "R", "2026-06-26")
    d26 = [s for s in eng.list_sheets("r") if s["sheet_date"] == "2026-06-26"][0]
    assert len(eng.get_rows(d26["id"])) == 1   # one copy, not two
    assert eng.carry_over_pending("r", "R", "2026-06-26") == 0  # still idempotent


def test_team_summary(monkeypatch):
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    eng.create_sheet("rep1", "Rep One", "2026-06-26", "S1", "a.csv",
                     [{"lead_name": "A", "phone": "1"}])
    eng.create_sheet("rep2", "Rep Two", "2026-06-26", "S2", "b.csv",
                     [{"lead_name": "B", "phone": "2"}])
    allrows = eng.team_summary()
    assert len(allrows) == 2
    owners = {r["owner_username"] for r in allrows}
    assert owners == {"rep1", "rep2"}
    assert "total" in allrows[0] and "pct_called" in allrows[0]
    only1 = eng.team_summary("rep1")
    assert len(only1) == 1 and only1[0]["owner_username"] == "rep1"


def test_delete_row_and_keeps_total_in_sync(monkeypatch):
    """delete_row removes one lead and decrements the sheet's total_rows."""
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    sid = eng.create_sheet("rep1", "Rep One", "2026-06-29", "S", "", [
        {"lead_name": "A", "phone": "1"}, {"lead_name": "B", "phone": "2"}])
    rows = eng.get_rows(sid)
    assert len(rows) == 2
    assert eng.delete_row(rows[0]["id"]) is True
    assert len(eng.get_rows(sid)) == 1
    assert eng.get_sheet(sid)["total_rows"] == 1
    # deleting a non-existent row is a no-op, returns False
    assert eng.delete_row(999999) is False


def test_update_row_can_edit_identity_columns(monkeypatch):
    """Excel-like editing: lead_name/phone/company are now editable, not just outcome."""
    database, path = _fresh_db(monkeypatch)
    import calling_sheet_engine as eng
    importlib.reload(eng)
    sid = eng.create_sheet("rep1", "Rep One", "2026-06-29", "S", "", [
        {"lead_name": "Old Name", "phone": "1", "company": "OldCo"}])
    rid = eng.get_rows(sid)[0]["id"]
    eng.update_row(rid, {"lead_name": "New Name", "phone": "9999",
                         "company": "NewCo", "remark": "edited"})
    r = eng.get_rows(sid)[0]
    assert r["lead_name"] == "New Name"
    assert r["phone"] == "9999"
    assert r["company"] == "NewCo"
    assert r["remark"] == "edited"
