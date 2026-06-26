# Daily Calling Sheet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let each sales rep upload a daily calling sheet (Excel/CSV), work it (call status, remark, outcome, follow-up date per row), keep a separate sheet per day with carry-over of un-called rows, and keep a permanent per-user record; directors get team oversight.

**Architecture:** New pure-logic `calling_sheet_engine.py` (parse + CRUD + carry-over + summaries via DB low-level helpers, no Streamlit), new `command_intel/calling_sheet_dashboard.py` (Streamlit page, sub-tabs Upload/Today/History/Team), two new SQLite tables registered in `database.py`, one new page wired into the Sales module nav + `dashboard.py` routing.

**Tech Stack:** Python 3.x, Streamlit 1.57, pandas 3.0, SQLite (`bitumen_dashboard.db`), pytest. Excel parsing via pandas + openpyxl.

## Global Constraints

- DB is `bitumen_dashboard.db`. NEVER hardcode table/column names outside `database.py` registration + the engine constants. Route all writes through `_insert_row`/`_update_row` (they validate against `_VALID_TABLES`) or the engine's bulk helper.
- A new table MUST be added to BOTH `_TABLES` (dict, DDL) AND `_VALID_TABLES` (set) in `database.py`, else `_insert_row`/`_update_row` raise.
- Current user id: `st.session_state.get("_auth_username")`. Current role: `role_engine.get_current_role()` (levels: director/admin=4, sales=3, operations=2, viewer=1).
- RBAC for the page is automatic via `nav_config.MODULE_ROLE_MAP["🧾 Sales"] == "sales"`. Within the page, rep (`sales`) sees only `owner_username == current`; `director` may select any user and see the Team tab.
- Engine has NO `import streamlit`. UI never writes raw SQL.
- Conventional commits; attribution disabled. NEVER commit runtime JSON (`tbl_*.json`, `hub_cache.json`, `live_prices.json`, `bitumen_dashboard.db*`). Only commit `.py` / `.md`.
- Status values (single source, engine constants):
  `CALL_STATUSES = ["Pending", "Connected", "No answer", "Busy", "Switched off", "Wrong number", "Callback"]`
  `OUTCOMES = ["", "Interested", "Quote requested", "Not interested", "Follow-up", "Deal"]`
- Run tests from `D:/rahul/company/pacpl/sirs project/pps-demo-live`. Tests must create their own temp DB or use the engine against a temp sqlite file — NEVER mutate the live `bitumen_dashboard.db`.

---

### Task 1: Register the two tables in database.py

**Files:**
- Modify: `database.py` (`_TABLES` dict ~line 206, `_INDEXES` list ~line 945, `_VALID_TABLES` set ~line 1393)
- Test: `tests/test_calling_sheet.py`

**Interfaces:**
- Produces: tables `calling_sheets` and `calling_sheet_rows` (created by `init_db()`), registered in `_VALID_TABLES`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_calling_sheet.py`:

```python
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
```

- [ ] **Step 2: Confirm `DB_PATH` is the attribute `_get_conn` uses**

Run: `grep -nE "DB_PATH|def _get_conn|def init_db" database.py | head`
Expected: a module-level `DB_PATH = ...` and `_get_conn()` opens `sqlite3.connect(DB_PATH)`. If the attribute name differs (e.g. `_DB_PATH`), update the test's `monkeypatch.setattr` target accordingly before running.

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_calling_sheet.py -q`
Expected: FAIL (`calling_sheets` not in tables / not in `_VALID_TABLES`).

- [ ] **Step 4: Add the two DDL entries to `_TABLES`**

In `database.py`, inside the `_TABLES = { ... }` dict (after an existing entry, e.g. after `"daily_logs"`), add:

```python
    "calling_sheets": """
        CREATE TABLE IF NOT EXISTS calling_sheets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_username  TEXT NOT NULL,
            owner_name      TEXT,
            sheet_date      TEXT NOT NULL,
            title           TEXT,
            source_filename TEXT,
            total_rows      INTEGER DEFAULT 0,
            created_at      TEXT,
            updated_at      TEXT
        )
    """,
    "calling_sheet_rows": """
        CREATE TABLE IF NOT EXISTS calling_sheet_rows (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id            INTEGER NOT NULL,
            owner_username      TEXT NOT NULL,
            lead_name           TEXT,
            phone               TEXT,
            company             TEXT,
            city                TEXT,
            extra               TEXT,
            call_status         TEXT DEFAULT 'Pending',
            outcome             TEXT DEFAULT '',
            remark              TEXT DEFAULT '',
            followup_date       TEXT,
            called_at           TEXT,
            carried_from_row_id INTEGER,
            created_at          TEXT,
            updated_at          TEXT
        )
    """,
```

- [ ] **Step 5: Add indexes to `_INDEXES`**

Find the `_INDEXES = [ ... ]` list (the block with `CREATE INDEX IF NOT EXISTS idx_...` strings, ~line 945) and add:

```python
    "CREATE INDEX IF NOT EXISTS idx_calling_sheets_owner ON calling_sheets(owner_username, sheet_date);",
    "CREATE INDEX IF NOT EXISTS idx_calling_rows_sheet   ON calling_sheet_rows(sheet_id);",
    "CREATE INDEX IF NOT EXISTS idx_calling_rows_owner   ON calling_sheet_rows(owner_username, call_status);",
```

- [ ] **Step 6: Register both names in `_VALID_TABLES`**

In the `_VALID_TABLES = { ... }` set, add a line:

```python
    # Daily Calling Sheet
    "calling_sheets", "calling_sheet_rows",
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_calling_sheet.py -q`
Expected: PASS (2 passed).

- [ ] **Step 8: Commit**

```bash
git add database.py tests/test_calling_sheet.py
git commit -m "feat(calling-sheet): register calling_sheets + calling_sheet_rows tables"
```

---

### Task 2: Engine constants + sheet/row CRUD

**Files:**
- Create: `calling_sheet_engine.py`
- Test: `tests/test_calling_sheet.py` (append)

**Interfaces:**
- Consumes: `database._insert_row(table, data)->int`, `database._update_row(table, id, data)`, `database._select_all(table, where, params, order)->list`, `database._get_conn()`, `database._now_ist()->str`.
- Produces:
  - `CALL_STATUSES: list[str]`, `OUTCOMES: list[str]`, `CORE_FIELDS = ["lead_name","phone","company","city"]`
  - `create_sheet(owner_username:str, owner_name:str, sheet_date:str, title:str, source_filename:str, rows:list[dict]) -> int` (returns sheet_id; bulk-inserts rows; sets `total_rows`)
  - `get_sheet(sheet_id:int) -> dict | None`
  - `list_sheets(owner_username:str|None=None, limit:int=200) -> list[dict]` (newest first by sheet_date)
  - `get_rows(sheet_id:int) -> list[dict]`
  - each row dict has keys: id, sheet_id, owner_username, lead_name, phone, company, city, extra(dict), call_status, outcome, remark, followup_date, called_at, carried_from_row_id

- [ ] **Step 1: Write the failing test (append to tests/test_calling_sheet.py)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_calling_sheet.py::test_create_and_read_sheet -q`
Expected: FAIL (`No module named calling_sheet_engine`).

- [ ] **Step 3: Create `calling_sheet_engine.py`**

```python
"""
PPS Anantam — Daily Calling Sheet Engine
=========================================
Pure logic for the calling-sheet worklist: CRUD, parsing, carry-over, summaries.
No Streamlit imports — fully unit-testable. All DB access goes through database.py
low-level helpers (which validate table names against _VALID_TABLES).
"""
import json
from database import (
    _insert_row, _update_row, _select_all, _get_conn, _now_ist,
)

CALL_STATUSES = ["Pending", "Connected", "No answer", "Busy",
                 "Switched off", "Wrong number", "Callback"]
OUTCOMES = ["", "Interested", "Quote requested", "Not interested",
            "Follow-up", "Deal"]
CORE_FIELDS = ["lead_name", "phone", "company", "city"]


def _loads(val):
    if not val:
        return {}
    try:
        return json.loads(val)
    except Exception:
        return {}


def _row_out(r: dict) -> dict:
    r = dict(r)
    r["extra"] = _loads(r.get("extra"))
    return r


def create_sheet(owner_username, owner_name, sheet_date, title,
                 source_filename, rows):
    """Create a calling_sheets record + bulk-insert its rows. Returns sheet_id."""
    now = _now_ist()
    sheet_id = _insert_row("calling_sheets", {
        "owner_username": owner_username,
        "owner_name": owner_name or owner_username,
        "sheet_date": sheet_date,
        "title": title or f"Calling Sheet {sheet_date}",
        "source_filename": source_filename or "",
        "total_rows": len(rows),
        "created_at": now,
        "updated_at": now,
    })
    _bulk_insert_rows(sheet_id, owner_username, rows)
    return sheet_id


def _bulk_insert_rows(sheet_id, owner_username, rows):
    """Insert many rows efficiently in one connection."""
    if not rows:
        return
    now = _now_ist()
    payload = []
    for r in rows:
        payload.append((
            sheet_id, owner_username,
            (r.get("lead_name") or "").strip(),
            (r.get("phone") or "").strip(),
            (r.get("company") or "").strip(),
            (r.get("city") or "").strip(),
            json.dumps(r.get("extra") or {}, ensure_ascii=False),
            r.get("call_status") or "Pending",
            r.get("outcome") or "",
            r.get("remark") or "",
            r.get("followup_date"),
            r.get("called_at"),
            r.get("carried_from_row_id"),
            now, now,
        ))
    conn = _get_conn()
    try:
        conn.executemany(
            """INSERT INTO calling_sheet_rows
               (sheet_id, owner_username, lead_name, phone, company, city, extra,
                call_status, outcome, remark, followup_date, called_at,
                carried_from_row_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            payload,
        )
        conn.commit()
    finally:
        conn.close()


def get_sheet(sheet_id):
    rows = _select_all("calling_sheets", where="id = ?", params=(sheet_id,))
    return rows[0] if rows else None


def list_sheets(owner_username=None, limit=200):
    if owner_username:
        rows = _select_all("calling_sheets", where="owner_username = ?",
                           params=(owner_username,),
                           order="sheet_date DESC, id DESC")
    else:
        rows = _select_all("calling_sheets",
                           order="sheet_date DESC, id DESC")
    return rows[:limit]


def get_rows(sheet_id):
    rows = _select_all("calling_sheet_rows", where="sheet_id = ?",
                       params=(sheet_id,), order="id ASC")
    return [_row_out(r) for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_calling_sheet.py::test_create_and_read_sheet -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add calling_sheet_engine.py tests/test_calling_sheet.py
git commit -m "feat(calling-sheet): engine sheet/row CRUD + constants"
```

---

### Task 3: Upload parsing + column auto-detect

**Files:**
- Modify: `calling_sheet_engine.py`
- Test: `tests/test_calling_sheet.py` (append)

**Interfaces:**
- Consumes: pandas (`import pandas as pd`).
- Produces:
  - `detect_columns(columns: list[str]) -> dict` — maps each of `lead_name/phone/company/city` to a source column name or `None`, using case/space-insensitive synonyms.
  - `parse_file(file_bytes: bytes, filename: str) -> pandas.DataFrame` — reads csv/xls/xlsx into a DataFrame (all columns as strings).
  - `normalize_rows(df, mapping: dict) -> list[dict]` — returns row dicts with `lead_name/phone/company/city` from mapped columns and everything else under `extra`. Skips rows where both lead_name and phone are empty.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_calling_sheet.py -k "detect or normalize" -q`
Expected: FAIL (`module 'calling_sheet_engine' has no attribute 'detect_columns'`).

- [ ] **Step 3: Implement parsing in `calling_sheet_engine.py`**

Add at top: `import io` and `import pandas as pd`. Append:

```python
_SYNONYMS = {
    "lead_name": ["name", "customer name", "customer", "client", "lead",
                  "party", "firm name", "contact name", "contact"],
    "phone": ["phone", "mobile", "mobile no", "mobile number", "contact no",
              "number", "phone no", "cell", "whatsapp", "ph"],
    "company": ["company", "firm", "organisation", "organization", "business",
                "company name", "firm name"],
    "city": ["city", "town", "location", "place", "district", "region", "area"],
}


def _norm(s):
    return "".join(str(s).lower().split())


def detect_columns(columns):
    avail = {c: _norm(c) for c in columns}
    mapping = {f: None for f in CORE_FIELDS}
    used = set()
    for field in CORE_FIELDS:
        for syn in _SYNONYMS[field]:
            target = _norm(syn)
            for col, ncol in avail.items():
                if col in used:
                    continue
                if ncol == target or target in ncol or ncol in target:
                    mapping[field] = col
                    used.add(col)
                    break
            if mapping[field]:
                break
    return mapping


def parse_file(file_bytes, filename):
    name = (filename or "").lower()
    bio = io.BytesIO(file_bytes)
    if name.endswith(".csv"):
        df = pd.read_csv(bio, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(bio, dtype=str)
    df = df.fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_rows(df, mapping):
    out = []
    core_cols = {v for v in mapping.values() if v}
    for _, row in df.iterrows():
        rec = {f: (str(row[mapping[f]]).strip() if mapping[f] else "")
               for f in CORE_FIELDS}
        if not rec["lead_name"] and not rec["phone"]:
            continue
        extra = {c: str(row[c]).strip() for c in df.columns
                 if c not in core_cols and str(row[c]).strip()}
        rec["extra"] = extra
        out.append(rec)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_calling_sheet.py -k "detect or normalize" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add calling_sheet_engine.py tests/test_calling_sheet.py
git commit -m "feat(calling-sheet): file parsing + column auto-detect + normalize"
```

---

### Task 4: Row update + per-sheet summary

**Files:**
- Modify: `calling_sheet_engine.py`
- Test: `tests/test_calling_sheet.py` (append)

**Interfaces:**
- Produces:
  - `update_row(row_id:int, data:dict) -> None` — updates allowed fields only (`call_status,outcome,remark,followup_date`); stamps `called_at` (now) when status moves off "Pending"; stamps `updated_at`.
  - `sheet_summary(sheet_id:int) -> dict` with keys: `total, called, pending, connected, conversions, pct_called` (conversions = outcome in {Interested, Quote requested, Deal, Follow-up}).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_calling_sheet.py::test_update_row_and_summary -q`
Expected: FAIL (`has no attribute 'update_row'`).

- [ ] **Step 3: Implement**

Append to `calling_sheet_engine.py`:

```python
_EDITABLE = {"call_status", "outcome", "remark", "followup_date"}
_CONVERSION_OUTCOMES = {"Interested", "Quote requested", "Deal", "Follow-up"}


def update_row(row_id, data):
    clean = {k: v for k, v in data.items() if k in _EDITABLE}
    if not clean:
        return
    now = _now_ist()
    if clean.get("call_status") and clean["call_status"] != "Pending":
        clean["called_at"] = now
    clean["updated_at"] = now
    _update_row("calling_sheet_rows", row_id, clean)


def sheet_summary(sheet_id):
    rows = get_rows(sheet_id)
    total = len(rows)
    pending = sum(1 for r in rows if (r.get("call_status") or "Pending") == "Pending")
    called = total - pending
    connected = sum(1 for r in rows if r.get("call_status") == "Connected")
    conversions = sum(1 for r in rows if r.get("outcome") in _CONVERSION_OUTCOMES)
    return {
        "total": total, "called": called, "pending": pending,
        "connected": connected, "conversions": conversions,
        "pct_called": round(called / total * 100, 1) if total else 0.0,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_calling_sheet.py::test_update_row_and_summary -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add calling_sheet_engine.py tests/test_calling_sheet.py
git commit -m "feat(calling-sheet): row update + per-sheet summary"
```

---

### Task 5: Carry-over of pending rows

**Files:**
- Modify: `calling_sheet_engine.py`
- Test: `tests/test_calling_sheet.py` (append)

**Interfaces:**
- Produces:
  - `get_or_create_today_sheet(owner_username, owner_name, sheet_date) -> int` — returns existing sheet id for that (user, date) or creates an empty one.
  - `carry_over_pending(owner_username, owner_name, target_date) -> int` — copies the user's `Pending` rows from sheets with `sheet_date < target_date` into the target-date sheet (created if needed), skipping rows already carried (dedupe via `carried_from_row_id`). Returns number carried.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_calling_sheet.py::test_carry_over -q`
Expected: FAIL (`has no attribute 'carry_over_pending'`).

- [ ] **Step 3: Implement**

Append to `calling_sheet_engine.py`:

```python
def get_or_create_today_sheet(owner_username, owner_name, sheet_date):
    existing = _select_all(
        "calling_sheets", where="owner_username = ? AND sheet_date = ?",
        params=(owner_username, sheet_date), order="id DESC")
    if existing:
        return existing[0]["id"]
    return create_sheet(owner_username, owner_name, sheet_date,
                        f"Calling Sheet {sheet_date}", "", [])


def carry_over_pending(owner_username, owner_name, target_date):
    # already-carried source ids in the target date (dedupe)
    target_rows = _select_all(
        "calling_sheet_rows",
        where="owner_username = ? AND sheet_id IN "
              "(SELECT id FROM calling_sheets WHERE owner_username = ? AND sheet_date = ?)",
        params=(owner_username, owner_username, target_date))
    already = {r.get("carried_from_row_id") for r in target_rows
              if r.get("carried_from_row_id")}
    # pending rows from earlier dates
    pend = _select_all(
        "calling_sheet_rows",
        where="owner_username = ? AND call_status = 'Pending' AND sheet_id IN "
              "(SELECT id FROM calling_sheets WHERE owner_username = ? AND sheet_date < ?)",
        params=(owner_username, owner_username, target_date), order="id ASC")
    fresh = [r for r in pend if r["id"] not in already]
    if not fresh:
        return 0
    target_sid = get_or_create_today_sheet(owner_username, owner_name, target_date)
    new_rows = []
    for r in fresh:
        new_rows.append({
            "lead_name": r.get("lead_name"), "phone": r.get("phone"),
            "company": r.get("company"), "city": r.get("city"),
            "extra": _loads(r.get("extra")),
            "carried_from_row_id": r["id"],
        })
    _bulk_insert_rows(target_sid, owner_username, new_rows)
    # keep total_rows accurate
    cur = get_rows(target_sid)
    _update_row("calling_sheets", target_sid,
                {"total_rows": len(cur), "updated_at": _now_ist()})
    return len(new_rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_calling_sheet.py::test_carry_over -q`
Expected: PASS.

- [ ] **Step 5: Run the full engine test file**

Run: `python -m pytest tests/test_calling_sheet.py -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add calling_sheet_engine.py tests/test_calling_sheet.py
git commit -m "feat(calling-sheet): carry-over of pending rows (dedup + idempotent)"
```

---

### Task 6: Team summary (director oversight)

**Files:**
- Modify: `calling_sheet_engine.py`
- Test: `tests/test_calling_sheet.py` (append)

**Interfaces:**
- Produces:
  - `team_summary(owner_username=None) -> list[dict]` — one entry per sheet (optionally filtered to a user), each `{sheet_id, owner_username, owner_name, sheet_date, title, **sheet_summary fields}`, newest first. Used by the director Team tab.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_calling_sheet.py::test_team_summary -q`
Expected: FAIL (`has no attribute 'team_summary'`).

- [ ] **Step 3: Implement**

Append to `calling_sheet_engine.py`:

```python
def team_summary(owner_username=None):
    sheets = list_sheets(owner_username=owner_username)
    out = []
    for s in sheets:
        summ = sheet_summary(s["id"])
        out.append({
            "sheet_id": s["id"], "owner_username": s["owner_username"],
            "owner_name": s.get("owner_name"), "sheet_date": s["sheet_date"],
            "title": s.get("title"), **summ,
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_calling_sheet.py::test_team_summary -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add calling_sheet_engine.py tests/test_calling_sheet.py
git commit -m "feat(calling-sheet): team summary for director oversight"
```

---

### Task 7: Dashboard page — Upload tab

**Files:**
- Create: `command_intel/calling_sheet_dashboard.py`
- Test: manual (Streamlit UI) — covered by headless sweep in Task 11.

**Interfaces:**
- Consumes: `calling_sheet_engine` (all functions), `role_engine.get_current_role`, `st.session_state["_auth_username"]/["_auth_user"]`.
- Produces: `render() -> None` (page entry), `_current_user() -> tuple[str,str]` helper, `_render_upload(user, name)`.

- [ ] **Step 1: Create the file with the page shell + Upload tab**

```python
"""
PPS Anantam — Daily Calling Sheet (Sales)
Upload a daily calling sheet, work it (status/remark/outcome/follow-up per row),
keep a separate sheet per day with carry-over, full per-user record. Director
sees all reps + a Team tab.
"""
import datetime
import streamlit as st
import calling_sheet_engine as eng


def _current_user():
    u = st.session_state.get("_auth_username") or "unknown"
    name = st.session_state.get("_auth_user") or u
    return u, name


def _is_director():
    try:
        from role_engine import get_current_role
        return get_current_role() in ("director", "admin")
    except Exception:
        return False


def _today():
    return datetime.date.today().strftime("%Y-%m-%d")


def _render_upload(user, name):
    st.subheader("📤 Upload calling sheet")
    up = st.file_uploader("Excel or CSV", type=["csv", "xls", "xlsx"],
                          key="cs_upload")
    if not up:
        st.info("Apni daily calling sheet (Excel/CSV) upload karo. "
                "Columns auto-detect ho jaayenge.")
        return
    try:
        df = eng.parse_file(up.getvalue(), up.name)
    except Exception as e:
        st.error(f"File padhne me dikkat: {e}")
        return
    if df.empty:
        st.warning("Sheet khaali hai.")
        return

    cols = list(df.columns)
    detected = eng.detect_columns(cols)
    st.caption(f"{len(df)} rows mile. Columns map karo:")
    opts = ["(none)"] + cols
    c1, c2, c3, c4 = st.columns(4)
    mapping = {}
    for col_box, field, label in [
        (c1, "lead_name", "Name"), (c2, "phone", "Phone"),
        (c3, "company", "Company"), (c4, "city", "City")]:
        with col_box:
            default = detected.get(field) or "(none)"
            idx = opts.index(default) if default in opts else 0
            pick = st.selectbox(label, opts, index=idx, key=f"cs_map_{field}")
            mapping[field] = None if pick == "(none)" else pick

    sheet_date = st.date_input("Sheet date", value=datetime.date.today(),
                               key="cs_date").strftime("%Y-%m-%d")
    st.dataframe(df.head(10), use_container_width=True)

    if st.button("✅ Save this sheet", type="primary", key="cs_save"):
        rows = eng.normalize_rows(df, mapping)
        if not rows:
            st.error("Koi valid row nahi (name/phone dono khaali).")
            return
        sid = eng.create_sheet(user, name, sheet_date, up.name, up.name, rows)
        st.success(f"Sheet saved — {len(rows)} leads. Ab 'Today's Calls' tab me kaam karo.")
        st.session_state["cs_active_sheet"] = sid


def render():
    st.header("📞 Daily Calling Sheet")
    st.caption("Apni daily calling list upload karo, har call pe remark/status/outcome "
               "set karo. Har din ki alag sheet, poora record save rehta hai.")
    user, name = _current_user()
    tabs = ["📤 Upload", "📋 Today's Calls", "🗂️ History"]
    if _is_director():
        tabs.append("👥 Team")
    selected = st.tabs(tabs)
    with selected[0]:
        _render_upload(user, name)
    with selected[1]:
        st.info("Today's Calls — Task 8 me aayega.")
    with selected[2]:
        st.info("History — Task 9 me aayega.")
    if _is_director():
        with selected[3]:
            st.info("Team — Task 10 me aayega.")
```

- [ ] **Step 2: Smoke-import the module**

Run: `python -c "import command_intel.calling_sheet_dashboard as d; print('import ok', hasattr(d,'render'))"`
Expected: `import ok True` (Streamlit cache warnings are fine).

- [ ] **Step 3: Commit**

```bash
git add command_intel/calling_sheet_dashboard.py
git commit -m "feat(calling-sheet): dashboard shell + Upload tab"
```

---

### Task 8: Dashboard — Today's Calls (editable worklist)

**Files:**
- Modify: `command_intel/calling_sheet_dashboard.py`

**Interfaces:**
- Consumes: `eng.list_sheets`, `eng.get_rows`, `eng.update_row`, `eng.sheet_summary`, `eng.get_or_create_today_sheet`, `eng.CALL_STATUSES`, `eng.OUTCOMES`.
- Produces: `_render_today(user, name)`.

- [ ] **Step 1: Implement `_render_today` and wire it in**

Add this function and replace the Today's Calls tab body (`st.info("Today's Calls ...")`) with `_render_today(user, name)`.

```python
import pandas as pd  # add to imports at top


def _render_today(user, name):
    st.subheader("📋 Today's calls")
    today = _today()
    sheets = [s for s in eng.list_sheets(user) if s["sheet_date"] == today]
    if not sheets:
        st.info("Aaj ki koi sheet nahi. Upload tab se sheet daalo, ya History se "
                "carry-over karo.")
        if st.button("➕ Create empty sheet for today", key="cs_mk_today"):
            eng.get_or_create_today_sheet(user, name, today)
            st.rerun()
        return
    # pick sheet (usually one; allow choosing if multiple)
    labels = {f'{s["title"]} (#{s["id"]})': s["id"] for s in sheets}
    chosen = st.selectbox("Sheet", list(labels.keys()), key="cs_today_pick")
    sid = labels[chosen]

    summ = eng.sheet_summary(sid)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", summ["total"])
    m2.metric("Called", f'{summ["called"]} ({summ["pct_called"]}%)')
    m3.metric("Connected", summ["connected"])
    m4.metric("Conversions", summ["conversions"])

    rows = eng.get_rows(sid)
    if not rows:
        st.info("Is sheet me koi lead nahi.")
        return
    df = pd.DataFrame([{
        "id": r["id"], "Name": r["lead_name"], "Phone": r["phone"],
        "Company": r["company"], "Status": r["call_status"] or "Pending",
        "Outcome": r["outcome"] or "", "Remark": r["remark"] or "",
        "Follow-up": r["followup_date"] or "",
    } for r in rows])

    edited = st.data_editor(
        df, key="cs_editor", use_container_width=True, hide_index=True,
        disabled=["id", "Name", "Phone", "Company"],
        column_config={
            "id": None,  # hidden
            "Status": st.column_config.SelectboxColumn(options=eng.CALL_STATUSES),
            "Outcome": st.column_config.SelectboxColumn(options=eng.OUTCOMES),
            "Remark": st.column_config.TextColumn(),
            "Follow-up": st.column_config.TextColumn(help="YYYY-MM-DD"),
        })

    if st.button("💾 Save changes", type="primary", key="cs_save_today"):
        before = {r["id"]: r for r in rows}
        n = 0
        for _, er in edited.iterrows():
            rid = int(er["id"])
            b = before.get(rid, {})
            new = {
                "call_status": er["Status"], "outcome": er["Outcome"],
                "remark": er["Remark"],
                "followup_date": er["Follow-up"] or None,
            }
            if (new["call_status"] != (b.get("call_status") or "Pending")
                    or new["outcome"] != (b.get("outcome") or "")
                    or new["remark"] != (b.get("remark") or "")
                    or (new["followup_date"] or "") != (b.get("followup_date") or "")):
                eng.update_row(rid, new)
                n += 1
        st.success(f"{n} rows updated.")
        st.rerun()
```

- [ ] **Step 2: Smoke-import**

Run: `python -c "import command_intel.calling_sheet_dashboard as d; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add command_intel/calling_sheet_dashboard.py
git commit -m "feat(calling-sheet): Today's Calls editable worklist + save"
```

---

### Task 9: Dashboard — History tab

**Files:**
- Modify: `command_intel/calling_sheet_dashboard.py`

**Interfaces:**
- Consumes: `eng.list_sheets`, `eng.sheet_summary`, `eng.get_rows`.
- Produces: `_render_history(user)`.

- [ ] **Step 1: Implement `_render_history` and wire it into the History tab**

```python
def _render_history(user):
    st.subheader("🗂️ Past sheets")
    sheets = eng.list_sheets(user)
    if not sheets:
        st.info("Abhi koi sheet nahi.")
        return
    table = []
    for s in sheets:
        summ = eng.sheet_summary(s["id"])
        table.append({
            "Date": s["sheet_date"], "Title": s["title"],
            "Total": summ["total"], "Called": summ["called"],
            "% Called": summ["pct_called"], "Conversions": summ["conversions"],
            "id": s["id"],
        })
    import pandas as pd
    st.dataframe(pd.DataFrame(table).drop(columns=["id"]),
                 use_container_width=True, hide_index=True)
    ids = {f'{t["Date"]} — {t["Title"]} (#{t["id"]})': t["id"] for t in table}
    pick = st.selectbox("Open a sheet", list(ids.keys()), key="cs_hist_pick")
    rows = eng.get_rows(ids[pick])
    st.dataframe(pd.DataFrame([{
        "Name": r["lead_name"], "Phone": r["phone"], "Company": r["company"],
        "Status": r["call_status"], "Outcome": r["outcome"],
        "Remark": r["remark"], "Follow-up": r["followup_date"] or "",
    } for r in rows]), use_container_width=True, hide_index=True)
```

Replace the History tab body (`st.info("History ...")`) with `_render_history(user)`.

- [ ] **Step 2: Smoke-import**

Run: `python -c "import command_intel.calling_sheet_dashboard as d; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add command_intel/calling_sheet_dashboard.py
git commit -m "feat(calling-sheet): History tab (per-user past sheets)"
```

---

### Task 10: Dashboard — Carry-over button + Team tab

**Files:**
- Modify: `command_intel/calling_sheet_dashboard.py`

**Interfaces:**
- Consumes: `eng.carry_over_pending`, `eng.team_summary`.
- Produces: `_render_team()`; carry-over button added to `_render_today`.

- [ ] **Step 1: Add a carry-over button at the top of `_render_today`**

Immediately after `today = _today()` in `_render_today`, add:

```python
    if st.button("⬇️ Pull pending leads from previous days", key="cs_carry"):
        n = eng.carry_over_pending(user, name, today)
        st.success(f"{n} pending leads carried into today." if n
                   else "Koi pending lead nahi mila.")
        st.rerun()
```

- [ ] **Step 2: Implement `_render_team` and wire it into the Team tab**

```python
def _render_team():
    st.subheader("👥 Team calling activity")
    rollup = eng.team_summary()
    if not rollup:
        st.info("Abhi kisi rep ki koi sheet nahi.")
        return
    reps = sorted({r["owner_username"] for r in rollup})
    pick = st.selectbox("Rep", ["(All)"] + reps, key="cs_team_rep")
    data = rollup if pick == "(All)" else [r for r in rollup
                                           if r["owner_username"] == pick]
    import pandas as pd
    st.dataframe(pd.DataFrame([{
        "Rep": r["owner_name"] or r["owner_username"], "Date": r["sheet_date"],
        "Title": r["title"], "Total": r["total"], "Called": r["called"],
        "% Called": r["pct_called"], "Connected": r["connected"],
        "Conversions": r["conversions"],
    } for r in data]), use_container_width=True, hide_index=True)
```

Replace the Team tab body (`st.info("Team ...")`) with `_render_team()`.

- [ ] **Step 3: Smoke-import**

Run: `python -c "import command_intel.calling_sheet_dashboard as d; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add command_intel/calling_sheet_dashboard.py
git commit -m "feat(calling-sheet): carry-over button + director Team tab"
```

---

### Task 11: Nav wiring + headless sweep + deploy

**Files:**
- Modify: `nav_config.py` (Sales module `tabs` list, ~line 42)
- Modify: `dashboard.py` (page routing dict, ~line 730)

**Interfaces:**
- Page string: `"📞 Daily Calling Sheet"` (must match exactly in nav + routing).

- [ ] **Step 1: Add the page to the Sales module nav**

In `nav_config.py`, inside `"🧾 Sales"` → `"tabs": [...]`, add after the "Daily Log" entry:

```python
            {"label": "Calling Sheet", "page": "📞 Daily Calling Sheet", "star": True, "pill": ("NEW", "emerald")},
```

- [ ] **Step 2: Add the routing entry in `dashboard.py`**

In the page-dispatch dict (where other pages map to `_safe_render(...)`, near `"📓 Daily Log"`), add:

```python
    "📞 Daily Calling Sheet": lambda: _safe_render(
        lambda: __import__("command_intel.calling_sheet_dashboard", fromlist=["render"]).render(),
        "Daily Calling Sheet"),
```

- [ ] **Step 3: Verify the page is registered + reachable for sales/director only**

Run:
```bash
python -c "
import nav_config as n
print('in PAGE_ROLE_MAP:', n.PAGE_ROLE_MAP.get('📞 Daily Calling Sheet'))
"
```
Expected: `in PAGE_ROLE_MAP: sales` (so sales+director allowed, operations/viewer blocked).

- [ ] **Step 4: Headless render sweep for all 4 roles**

Run:
```bash
python test_apptest_deep.py director > sweep_director.log 2>&1; grep -E "Daily Calling Sheet|ERROR|EXCEPTION" sweep_director.log | head
python test_apptest_deep.py sales > sweep_sales.log 2>&1; grep -E "Daily Calling Sheet|ERROR|EXCEPTION" sweep_sales.log | head
```
Expected: the Calling Sheet page renders as OK (not ERROR/EXCEPTION) for director & sales; DENIED for operations/viewer is acceptable. Delete the `sweep_*.log` files after.

- [ ] **Step 5: Run the full calling-sheet unit tests once more**

Run: `python -m pytest tests/test_calling_sheet.py -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add nav_config.py dashboard.py
git commit -m "feat(calling-sheet): wire page into Sales nav + routing"
```

- [ ] **Step 7: Deploy (after confirming with Rahul)**

```bash
git push origin main
ssh root@82.112.231.3 '/usr/local/bin/pps-autodeploy.sh'
ssh root@82.112.231.3 'cd /opt/pps-bitumen && git log -1 --oneline && systemctl is-active pps-bitumen.service'
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://ppsanatams.cloud/
```
Expected: VPS HEAD = latest, service active, HTTP 200. (Confirm before pushing — production is client-facing.)

---

## Self-Review notes

- **Spec coverage:** upload+auto-detect (T3,T7) · per-call status/remark/outcome/followup (T4,T8) · daily separate sheet (T2,T7) · carry-over (T5,T10) · per-user records/history (T2,T9) · director team view (T6,T10) · RBAC own-vs-all (Global Constraints + T11 nav role map) · testing (T1–T6 pytest, T11 sweep). All covered.
- **No placeholders:** every code/test step is complete.
- **Type consistency:** engine names (`create_sheet`, `get_rows`, `update_row`, `sheet_summary`, `carry_over_pending`, `team_summary`, `detect_columns`, `parse_file`, `normalize_rows`, `get_or_create_today_sheet`) used identically across tasks and dashboard.
- **Note for executor:** confirm `database.DB_PATH` attribute name in Task 1 Step 2 before running tests; if different, adjust the monkeypatch target in all tests.
