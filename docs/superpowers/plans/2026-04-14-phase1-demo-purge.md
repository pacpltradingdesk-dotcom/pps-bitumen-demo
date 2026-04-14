# Phase 1 — Demo Purge + Real Data Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every demo/fake customer and placeholder from user-facing surfaces, sync the 25,667 real contacts from `tbl_contacts.json` into SQLite, import Prince's WhatsApp customer Excel, and ship a reusable import wizard at `/System/Import Wizard`.

**Architecture:** Add two tables (`customer_profiles`, `import_history`) via the existing versioned migration system (`_run_schema_migrations` in `database.py`). Build a pure-Python import engine (`contact_import_engine.py`) that the Streamlit wizard and a CLI script both consume. Purge demo data with a scripted find-and-replace that skips dev-only files. Rewire the handful of engines that read `sales_parties.json` to read the `customers` DB table instead.

**Tech Stack:** Python 3.12, SQLite (WAL mode, already configured), pandas, openpyxl (all in requirements.txt), pytest 8.3, Streamlit 1.31+, `streamlit.testing.v1` AppTest for journey regression.

**Spec:** `docs/superpowers/specs/2026-04-14-phase1-demo-purge-design.md`

---

## Guard-rails for every task

- Each task ends with an explicit commit. Never batch commits.
- Tests live in `tests/` (create the directory on first use). Pytest is already installed (8.3.0) but `pytest` is not in `requirements.txt` — add it in Task 1.
- Before any destructive step (delete file, truncate table, mass find-and-replace), the working tree is backed up to `.bak.archive/` and the baseline is tagged `pre-phase1-baseline`.
- `st.rerun()` is required after every `_save_config()` or DB-mutation that changes visible state. Follow this pattern even in new code.
- Indian commercial conventions: phone numbers stored as `+91XXXXXXXXXX` (no spaces, no dashes), GSTIN uppercase, monetary values as `DECIMAL(14,2)` equivalent (stored as REAL).
- Hinglish in user-facing strings is fine (matches existing codebase). English in code and docs.

---

## Task 0: Safety baseline

**Files:**
- Create: `.bak.archive/` (directory, gitignored)
- Create: `scripts/phase1_backup.sh` (portable; `phase1_backup.py` if Windows-only matters)
- Modify: `.gitignore` (add one line)

- [ ] **Step 1: Create the backup script**

Create `scripts/phase1_backup.py`:

```python
"""One-shot safety backup for Phase 1 migration.
Run before Task 1. Idempotent: second run overwrites with latest state."""
from __future__ import annotations
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / ".bak.archive"


def main() -> int:
    ARCHIVE.mkdir(exist_ok=True)
    targets = [
        "bitumen_dashboard.db",
        "tbl_contacts.json",
        "sales_parties.json",
        "purchase_parties.json",
    ]
    copied = 0
    for t in targets:
        src = ROOT / t
        if not src.exists():
            print(f"  [skip] {t} (missing)")
            continue
        dst = ARCHIVE / f"{t}.pre-phase1.bak"
        shutil.copy2(src, dst)
        copied += 1
        print(f"  [ok]   {t} -> {dst.relative_to(ROOT)}")

    # Tag the current commit as the baseline
    try:
        subprocess.run(["git", "tag", "-f", "pre-phase1-baseline"],
                       cwd=ROOT, check=True)
        print("  [ok]   git tag pre-phase1-baseline")
    except subprocess.CalledProcessError as e:
        print(f"  [warn] could not tag: {e}")
    print(f"Backed up {copied} file(s) to {ARCHIVE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Update `.gitignore`**

Append to `.gitignore`:

```
# Phase 1 backups
.bak.archive/
*.pre-phase1.bak
```

- [ ] **Step 3: Run the backup**

Run: `python scripts/phase1_backup.py`
Expected output:
```
  [ok]   bitumen_dashboard.db -> .bak.archive/bitumen_dashboard.db.pre-phase1.bak
  [ok]   tbl_contacts.json -> .bak.archive/tbl_contacts.json.pre-phase1.bak
  [ok]   sales_parties.json -> .bak.archive/sales_parties.json.pre-phase1.bak
  [ok]   purchase_parties.json -> .bak.archive/purchase_parties.json.pre-phase1.bak
  [ok]   git tag pre-phase1-baseline
Backed up 4 file(s) to D:\rahul\sirs project\pps-demo-live\.bak.archive
```

- [ ] **Step 4: Commit**

```bash
git add scripts/phase1_backup.py .gitignore
git commit -m "chore: Phase 1 safety baseline — backup script + tag"
```

---

## Task 1: Pin pytest in requirements

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add pytest to requirements.txt**

Append to `requirements.txt`:

```
# Testing (Phase 1 onward)
pytest>=8.3.0
```

- [ ] **Step 2: Verify install**

Run: `python -m pytest --version`
Expected: `pytest 8.3.0` or newer.

- [ ] **Step 3: Create the tests directory with an init**

Create empty `tests/__init__.py` (empty file) and `tests/conftest.py`:

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt tests/__init__.py tests/conftest.py
git commit -m "chore: add pytest to requirements + test fixtures"
```

---

## Task 2: Schema migration #8 — new tables

**Files:**
- Modify: `database.py` (one new migration function + one line in the `migrations` list)

- [ ] **Step 1: Add the migration function**

In `database.py`, just above `def _migration_007_vip_and_sms` (find that line), insert this function. If you cannot find it, search for `# SCHEMA MIGRATIONS` and append the function after the last `_migration_00N_*` function in that section:

```python
def _migration_008_phase1_import_tables(cur):
    """Phase 1: customer_profiles + import_history tables, imported_from on customers."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            company      TEXT,
            city         TEXT,
            state        TEXT,
            whatsapp     TEXT,
            email        TEXT,
            category     TEXT,
            notes        TEXT,
            source_file  TEXT,
            imported_at  TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name     TEXT NOT NULL,
            target_table  TEXT NOT NULL,
            rows_inserted INTEGER NOT NULL,
            rows_skipped  INTEGER NOT NULL,
            rows_errored  INTEGER NOT NULL,
            imported_at   TEXT NOT NULL,
            reverted      INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_profiles_name
        ON customer_profiles(name)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_import_history_imported_at
        ON import_history(imported_at DESC)
    """)
    # Add imported_from column to tables where it is missing
    for tbl in ("customers", "suppliers", "contacts"):
        try:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN imported_from TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
```

- [ ] **Step 2: Register the migration**

Find the `migrations = [...]` list inside `_run_schema_migrations()` (around line 1086) and add a new entry at the end, just after the `(7, ...)` line:

```python
            (8, "Phase 1: customer_profiles + import_history tables",
             _migration_008_phase1_import_tables),
```

- [ ] **Step 3: Run the migration**

Run: `python -c "from database import init_db; init_db(); print('ok')"`
Expected: prints `ok` with no exception.

- [ ] **Step 4: Verify tables exist**

Run:
```bash
python -c "
import sqlite3
c = sqlite3.connect('bitumen_dashboard.db')
for t in ('customer_profiles', 'import_history'):
    n = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {n} rows')
print('version:', c.execute('SELECT MAX(version) FROM _schema_version').fetchone()[0])
"
```
Expected:
```
customer_profiles: 0 rows
import_history: 0 rows
version: 8
```

- [ ] **Step 5: Commit**

```bash
git add database.py
git commit -m "feat(db): migration 8 — customer_profiles + import_history tables"
```

---

## Task 3: Import engine — parse + column mapping (TDD)

**Files:**
- Create: `tests/test_contact_import_engine.py` (first half)
- Create: `contact_import_engine.py` (skeleton + first two functions)

- [ ] **Step 1: Write failing tests for `parse_spreadsheet`**

Create `tests/test_contact_import_engine.py`:

```python
"""Unit tests for contact_import_engine — Phase 1."""
from __future__ import annotations
import pandas as pd
import pytest
from pathlib import Path

from contact_import_engine import (
    parse_spreadsheet,
    suggest_column_mapping,
)


# ── parse_spreadsheet ──────────────────────────────────────────────

def test_parse_csv(tmp_path: Path):
    csv = tmp_path / "sample.csv"
    csv.write_text("name,city,phone\nAsha,Pune,9876543210\n",
                   encoding="utf-8")
    df = parse_spreadsheet(csv)
    assert list(df.columns) == ["name", "city", "phone"]
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Asha"


def test_parse_xlsx(tmp_path: Path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["name", "city", "phone"])
    ws.append(["Asha", "Pune", "9876543210"])
    xlsx = tmp_path / "sample.xlsx"
    wb.save(xlsx)

    df = parse_spreadsheet(xlsx)
    assert list(df.columns) == ["name", "city", "phone"]
    assert df.iloc[0]["phone"] == "9876543210" or df.iloc[0]["phone"] == 9876543210


def test_parse_rejects_unsupported(tmp_path: Path):
    txt = tmp_path / "not-a-sheet.txt"
    txt.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_spreadsheet(txt)


# ── suggest_column_mapping ─────────────────────────────────────────

def test_mapping_direct_match():
    m = suggest_column_mapping(
        ["name", "city", "phone"],
        target_schema=["name", "city", "phone", "email"],
    )
    assert m == {"name": "name", "city": "city", "phone": "phone"}


def test_mapping_alias_party_name():
    m = suggest_column_mapping(
        ["Party Name", "Mobile", "GST No."],
        target_schema=["name", "phone", "gstin"],
    )
    assert m == {"name": "Party Name", "phone": "Mobile", "gstin": "GST No."}


def test_mapping_case_insensitive():
    m = suggest_column_mapping(["NAME", "CITY"], target_schema=["name", "city"])
    assert m == {"name": "NAME", "city": "CITY"}


def test_mapping_missing_target_omitted():
    m = suggest_column_mapping(["name"], target_schema=["name", "phone"])
    assert "phone" not in m
```

- [ ] **Step 2: Run the tests — confirm they fail with ImportError**

Run: `python -m pytest tests/test_contact_import_engine.py -v`
Expected: `ImportError: cannot import name 'parse_spreadsheet' from 'contact_import_engine'` (or module not found).

- [ ] **Step 3: Implement `parse_spreadsheet` + `suggest_column_mapping`**

Create `contact_import_engine.py`:

```python
"""
Contact Import Engine — Phase 1
================================
Pure-Python module (no Streamlit). Parses Excel/CSV, suggests column
mappings against a target DB schema, validates rows, deduplicates
against the live DB, commits imports inside a single transaction, and
supports reverting any committed import by its import_history id.
"""
from __future__ import annotations

import datetime as _dt
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd


# ═══════════════════════════════════════════════════════════════════
# Known column aliases — case-insensitive, substring-friendly
# ═══════════════════════════════════════════════════════════════════

_ALIASES: dict[str, tuple[str, ...]] = {
    "name":    ("name", "party name", "customer name", "supplier name",
                "client name", "contact name", "full name"),
    "company": ("company", "company name", "organisation", "organization",
                "firm"),
    "phone":   ("phone", "mobile", "mobile no", "mobile number",
                "contact", "contact no", "contact number", "whatsapp"),
    "email":   ("email", "email id", "e-mail", "mail id"),
    "gstin":   ("gstin", "gst", "gst no", "gst no.", "gst number",
                "gst_number", "gstin no"),
    "city":    ("city", "town", "location"),
    "state":   ("state", "region"),
    "address": ("address", "addr", "full address"),
    "category": ("category", "type", "party type", "segment"),
    "notes":   ("notes", "remark", "remarks", "comments"),
}


def _norm(s: str) -> str:
    """Lowercase, strip, collapse whitespace and punctuation."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").strip().lower())


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def parse_spreadsheet(path: str | Path) -> pd.DataFrame:
    """Read .xlsx or .csv into a DataFrame. Raises ValueError on anything else."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(p, dtype=str).fillna("")
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(p, dtype=str).fillna("")
    raise ValueError(f"Unsupported file type: {suffix} (expected .csv or .xlsx)")


def suggest_column_mapping(source_cols: Iterable[str],
                           target_schema: Iterable[str]) -> dict[str, str]:
    """Map target field names to the best source column name.

    Matching order:
      1. Exact match (case-insensitive, punctuation-normalised).
      2. Alias match from _ALIASES.
      3. Substring match (target name appears in source name).

    Returns a dict `{target_field: source_col}` for fields that matched.
    Target fields with no match are omitted.
    """
    source_list = list(source_cols)
    source_norm = {_norm(c): c for c in source_list}
    result: dict[str, str] = {}

    for target in target_schema:
        target_key = _norm(target)
        # 1. exact normalised match
        if target_key in source_norm:
            result[target] = source_norm[target_key]
            continue
        # 2. alias match
        for alias in _ALIASES.get(target, ()):
            if _norm(alias) in source_norm:
                result[target] = source_norm[_norm(alias)]
                break
        if target in result:
            continue
        # 3. substring match
        for norm_src, orig_src in source_norm.items():
            if target_key and target_key in norm_src:
                result[target] = orig_src
                break
    return result
```

- [ ] **Step 4: Run the tests — confirm they pass**

Run: `python -m pytest tests/test_contact_import_engine.py -v`
Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_contact_import_engine.py contact_import_engine.py
git commit -m "feat(import): parse_spreadsheet + suggest_column_mapping with tests"
```

---

## Task 4: Import engine — validation + dedupe (TDD)

**Files:**
- Modify: `tests/test_contact_import_engine.py` (append)
- Modify: `contact_import_engine.py` (append two functions)

- [ ] **Step 1: Append failing tests for validation and dedupe**

Append to `tests/test_contact_import_engine.py`:

```python
# ── validate_rows ──────────────────────────────────────────────────

from contact_import_engine import validate_rows, dedupe_against_db


def test_validate_keeps_good_rows():
    df = pd.DataFrame([
        {"name": "Asha", "phone": "9876543210", "gstin": ""},
        {"name": "Bhavesh", "phone": "+919876543211", "gstin": "24AAHCV1611L2ZD"},
    ])
    valid, invalid = validate_rows(df, "customers")
    assert len(valid) == 2
    assert len(invalid) == 0


def test_validate_drops_missing_name():
    df = pd.DataFrame([
        {"name": "", "phone": "9876543210"},
        {"name": "Asha", "phone": "9876543210"},
    ])
    valid, invalid = validate_rows(df, "customers")
    assert len(valid) == 1
    assert len(invalid) == 1
    assert invalid.iloc[0]["_reason"] == "missing name"


def test_validate_flags_bad_gstin():
    df = pd.DataFrame([
        {"name": "Asha", "phone": "9876543210", "gstin": "NOT-A-GSTIN"},
    ])
    valid, invalid = validate_rows(df, "customers")
    assert len(valid) == 0
    assert "gstin" in invalid.iloc[0]["_reason"].lower()


def test_validate_normalises_phone():
    df = pd.DataFrame([{"name": "Asha", "phone": "+91 98765-43210"}])
    valid, _ = validate_rows(df, "customers")
    assert valid.iloc[0]["phone"] == "+919876543210"


# ── dedupe_against_db ──────────────────────────────────────────────

def test_dedupe_skip_exact_match(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "INSERT INTO customers(name, contact) VALUES(?, ?)",
        ("Asha", "+919876543210"))
    conn.commit()
    conn.close()

    df = pd.DataFrame([
        {"name": "Asha", "phone": "+919876543210"},
        {"name": "Bhavesh", "phone": "+919876543211"},
    ])
    fresh = dedupe_against_db(df, "customers", strategy="skip", db_path=tmp_db)
    assert len(fresh) == 1
    assert fresh.iloc[0]["name"] == "Bhavesh"


def test_dedupe_whitespace_insensitive(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.execute("INSERT INTO customers(name, contact) VALUES(?, ?)",
                 ("Asha  Gupta", "+919876543210"))
    conn.commit()
    conn.close()

    df = pd.DataFrame([{"name": "asha gupta", "phone": "+919876543210"}])
    fresh = dedupe_against_db(df, "customers", strategy="skip", db_path=tmp_db)
    assert len(fresh) == 0
```

- [ ] **Step 2: Run tests — confirm they fail**

Run: `python -m pytest tests/test_contact_import_engine.py -v`
Expected: 7 pass (from Task 3), 6 new ones fail with ImportError.

- [ ] **Step 3: Append validation + dedupe to the engine**

Append to `contact_import_engine.py`:

```python
# ═══════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}Z[0-9A-Z]{1}$")


def _normalise_phone(raw: str) -> str:
    """Strip spaces/dashes, keep leading + and digits only."""
    if not raw:
        return ""
    s = str(raw).strip()
    out = "+" if s.startswith("+") else ""
    out += re.sub(r"\D", "", s)
    return out


def validate_rows(df: pd.DataFrame, target_table: str
                  ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split df into (valid, invalid). Invalid rows carry a `_reason` column."""
    valid_rows: list[dict] = []
    invalid_rows: list[dict] = []

    for _, row in df.iterrows():
        record = {k: ("" if pd.isna(v) else str(v).strip())
                  for k, v in row.items()}

        reason = None
        # Required
        if not record.get("name"):
            reason = "missing name"

        # Phone — normalise if present
        if "phone" in record:
            record["phone"] = _normalise_phone(record["phone"])

        # GSTIN — validate if present, else allow blank
        gst = record.get("gstin", "").upper()
        if gst and not _GSTIN_RE.match(gst):
            reason = reason or "invalid gstin format"
        if gst:
            record["gstin"] = gst

        if reason:
            record["_reason"] = reason
            invalid_rows.append(record)
        else:
            valid_rows.append(record)

    return (pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(),
            pd.DataFrame(invalid_rows) if invalid_rows else pd.DataFrame())


# ═══════════════════════════════════════════════════════════════════
# Dedupe
# ═══════════════════════════════════════════════════════════════════

# Which column holds the phone in each table (customers uses `contact`)
_PHONE_COL = {
    "customers": "contact",
    "suppliers": "contact",
    "contacts":  "phone",
    "customer_profiles": "whatsapp",
}


def _dedupe_key(name: str, phone: str) -> str:
    return f"{_norm(name)}|{_normalise_phone(phone)}"


def dedupe_against_db(df: pd.DataFrame, target_table: str,
                      strategy: str = "skip",
                      db_path: str | Path = "bitumen_dashboard.db"
                      ) -> pd.DataFrame:
    """Return rows that should be inserted, according to strategy.

    strategy:
      - 'skip'      → drop rows whose (name, phone) already exists.
      - 'overwrite' → keep all rows; caller must issue INSERT OR REPLACE.
      - 'merge'     → same as overwrite for now; merge happens during commit.
    """
    if df.empty:
        return df

    phone_col = _PHONE_COL.get(target_table, "phone")
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT name, {phone_col} FROM {target_table}"
        ).fetchall()
    finally:
        conn.close()
    existing = {_dedupe_key(n or "", p or "") for n, p in rows}

    if strategy in ("overwrite", "merge"):
        return df.copy()

    mask = []
    for _, r in df.iterrows():
        key = _dedupe_key(r.get("name", ""), r.get("phone", ""))
        mask.append(key not in existing)
    return df[pd.Series(mask, index=df.index)].copy()
```

- [ ] **Step 4: Run tests — confirm they pass**

Run: `python -m pytest tests/test_contact_import_engine.py -v`
Expected: 13 tests pass.

- [ ] **Step 5: Commit**

```bash
git add contact_import_engine.py tests/test_contact_import_engine.py
git commit -m "feat(import): validate_rows + dedupe_against_db with tests"
```

---

## Task 5: Import engine — commit + revert (TDD)

**Files:**
- Modify: `tests/test_contact_import_engine.py` (append)
- Modify: `contact_import_engine.py` (append commit_import + revert_import)

- [ ] **Step 1: Append failing tests**

Append to `tests/test_contact_import_engine.py`:

```python
# ── commit_import ──────────────────────────────────────────────────

from contact_import_engine import commit_import, revert_import


def test_commit_inserts_rows_and_history(tmp_db):
    import sqlite3
    df = pd.DataFrame([
        {"name": "Asha", "phone": "+919876543210", "city": "Pune"},
        {"name": "Bhavesh", "phone": "+919876543211", "city": "Nagpur"},
    ])
    result = commit_import(df, "customers", source_file="test.csv",
                           db_path=tmp_db)
    assert result["inserted"] == 2
    assert result["skipped"] == 0

    conn = sqlite3.connect(tmp_db)
    n = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    assert n == 2
    n_hist = conn.execute("SELECT COUNT(*) FROM import_history").fetchone()[0]
    assert n_hist == 1
    conn.close()


def test_commit_rollback_on_failure(tmp_db):
    """A row with a NULL name should NOT corrupt the DB — whole batch rolls back."""
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.execute("CREATE UNIQUE INDEX ux_customers_name ON customers(name)")
    conn.execute("INSERT INTO customers(name) VALUES('Asha')")
    conn.commit()
    conn.close()

    df = pd.DataFrame([
        {"name": "Bhavesh", "phone": "+919876543211"},
        {"name": "Asha", "phone": "+919876543210"},  # UNIQUE violation
    ])
    with pytest.raises(sqlite3.IntegrityError):
        commit_import(df, "customers", source_file="test.csv",
                      db_path=tmp_db)

    conn = sqlite3.connect(tmp_db)
    n = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    assert n == 1  # only the pre-existing Asha — Bhavesh was rolled back
    n_hist = conn.execute("SELECT COUNT(*) FROM import_history").fetchone()[0]
    assert n_hist == 0  # no history row for a rolled-back commit
    conn.close()


# ── revert_import ──────────────────────────────────────────────────

def test_revert_removes_inserted_rows(tmp_db):
    import sqlite3
    df = pd.DataFrame([
        {"name": "Asha", "phone": "+919876543210"},
        {"name": "Bhavesh", "phone": "+919876543211"},
    ])
    result = commit_import(df, "customers", source_file="test.csv",
                           db_path=tmp_db)
    import_id = result["import_history_id"]

    removed = revert_import(import_id, db_path=tmp_db)
    assert removed == 2

    conn = sqlite3.connect(tmp_db)
    n = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    assert n == 0
    reverted = conn.execute(
        "SELECT reverted FROM import_history WHERE id = ?",
        (import_id,)
    ).fetchone()[0]
    assert reverted == 1
    conn.close()
```

- [ ] **Step 2: Run tests — confirm they fail**

Run: `python -m pytest tests/test_contact_import_engine.py -v`
Expected: 13 pass, 3 new ones fail with ImportError.

- [ ] **Step 3: Append commit + revert to the engine**

Append to `contact_import_engine.py`:

```python
# ═══════════════════════════════════════════════════════════════════
# Commit + Revert
# ═══════════════════════════════════════════════════════════════════

# Which column in each target table holds the phone number
_INSERT_MAP: dict[str, dict[str, str]] = {
    "customers":         {"name": "name", "phone": "contact",
                          "city": "city", "state": "state",
                          "gstin": "gstin", "address": "address",
                          "category": "category"},
    "suppliers":         {"name": "name", "phone": "contact",
                          "city": "city", "state": "state",
                          "gstin": "gstin", "category": "category"},
    "contacts":          {"name": "name", "phone": "phone",
                          "city": "city", "state": "state",
                          "email": "email", "category": "category"},
    "customer_profiles": {"name": "name", "company": "company",
                          "phone": "whatsapp", "email": "email",
                          "city": "city", "state": "state",
                          "category": "category", "notes": "notes"},
}


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=5, minutes=30)))\
        .strftime("%Y-%m-%dT%H:%M:%S%z")


def commit_import(df: pd.DataFrame, target_table: str,
                  source_file: str,
                  db_path: str | Path = "bitumen_dashboard.db") -> dict:
    """Insert rows and write an import_history row. Single transaction.

    Raises sqlite3.IntegrityError (or other sqlite3 errors) on failure —
    the DB is rolled back and no history row is written.

    Returns {inserted, skipped, errors, import_history_id}.
    """
    if target_table not in _INSERT_MAP:
        raise ValueError(f"Unknown target table: {target_table}")

    mapping = _INSERT_MAP[target_table]
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN")
        inserted = 0
        for _, row in df.iterrows():
            cols = ["imported_from"]
            vals = [source_file]
            for src_key, db_col in mapping.items():
                if src_key in row and row[src_key] not in ("", None):
                    cols.append(db_col)
                    vals.append(row[src_key])
            placeholders = ", ".join(["?"] * len(vals))
            conn.execute(
                f"INSERT INTO {target_table} ({', '.join(cols)}) "
                f"VALUES ({placeholders})",
                vals,
            )
            inserted += 1

        cur = conn.execute(
            "INSERT INTO import_history "
            "(file_name, target_table, rows_inserted, rows_skipped, "
            " rows_errored, imported_at) VALUES (?, ?, ?, ?, ?, ?)",
            (source_file, target_table, inserted, 0, 0, _now_iso()),
        )
        import_id = cur.lastrowid
        conn.commit()
        return {
            "inserted": inserted,
            "skipped": 0,
            "errors": 0,
            "import_history_id": import_id,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def revert_import(import_history_id: int,
                  db_path: str | Path = "bitumen_dashboard.db") -> int:
    """Delete rows inserted by the given import; mark history reverted.

    Returns the number of rows removed.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN")
        row = conn.execute(
            "SELECT file_name, target_table, reverted "
            "FROM import_history WHERE id = ?",
            (import_history_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"import_history id {import_history_id} not found")
        file_name, target_table, already = row
        if already:
            conn.rollback()
            return 0
        cur = conn.execute(
            f"DELETE FROM {target_table} WHERE imported_from = ?",
            (file_name,),
        )
        removed = cur.rowcount
        conn.execute(
            "UPDATE import_history SET reverted = 1 WHERE id = ?",
            (import_history_id,),
        )
        conn.commit()
        return removed
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_contact_import_engine.py -v`
Expected: 16 tests pass.

- [ ] **Step 5: Commit**

```bash
git add contact_import_engine.py tests/test_contact_import_engine.py
git commit -m "feat(import): commit_import + revert_import with transaction safety"
```

---

## Task 6: CLI to sync tbl_contacts.json into contacts DB

**Files:**
- Create: `scripts/phase1_sync_contacts.py`

- [ ] **Step 1: Write the sync script**

Create `scripts/phase1_sync_contacts.py`:

```python
"""One-shot: sync tbl_contacts.json (25K rows) into the contacts DB table.
Idempotent via dedupe. Run from project root:
    python scripts/phase1_sync_contacts.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from contact_import_engine import (
    validate_rows, dedupe_against_db, commit_import
)


def main() -> int:
    src = ROOT / "tbl_contacts.json"
    if not src.exists():
        print(f"[fatal] {src} not found — aborting.")
        return 1

    raw = json.loads(src.read_text(encoding="utf-8"))
    print(f"[ok] loaded {len(raw)} rows from tbl_contacts.json")

    # Normalise column names to engine's canonical vocabulary
    df = pd.DataFrame(raw)
    col_map = {
        "contact": "phone",
        "gstin": "gstin",
        "name": "name",
        "city": "city",
        "state": "state",
        "category": "category",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    valid, invalid = validate_rows(df, "contacts")
    print(f"[ok] validated: {len(valid)} good, {len(invalid)} flagged")

    fresh = dedupe_against_db(valid, "contacts", strategy="skip",
                              db_path=ROOT / "bitumen_dashboard.db")
    print(f"[ok] after dedupe: {len(fresh)} rows to insert")

    if fresh.empty:
        print("[done] nothing new to import")
        return 0

    result = commit_import(fresh, "contacts",
                           source_file="tbl_contacts.json",
                           db_path=ROOT / "bitumen_dashboard.db")
    print(f"[done] inserted {result['inserted']} rows "
          f"(import_history id = {result['import_history_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the sync**

Run: `python scripts/phase1_sync_contacts.py`
Expected: rows reported, `inserted >= 25000 - 132` (the 132 that were already there are skipped by dedupe).

- [ ] **Step 3: Verify row count in DB**

Run:
```bash
python -c "
import sqlite3
n = sqlite3.connect('bitumen_dashboard.db').execute(
    'SELECT COUNT(*) FROM contacts').fetchone()[0]
print(f'contacts now: {n}')
"
```
Expected: at least 25,000 (could be higher if some duplicates in the source file expand differently after dedup).

- [ ] **Step 4: Commit**

```bash
git add scripts/phase1_sync_contacts.py
git commit -m "feat(import): CLI sync — tbl_contacts.json → contacts DB"
```

---

## Task 7: Promote contractor contacts into customers

**Files:**
- Create: `scripts/phase1_promote_customers.py`

- [ ] **Step 1: Write the promotion script**

Create `scripts/phase1_promote_customers.py`:

```python
"""Promote rows from contacts into customers when category implies contractor/buyer.

Rule: category LIKE '%contractor%' OR buyer_seller_tag = 'buyer'
Writes its own import_history row (source_file = 'promote:contacts->customers')
so it can be reverted.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from contact_import_engine import _now_iso  # reuse IST formatter


def main() -> int:
    db = ROOT / "bitumen_dashboard.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("BEGIN")

        # Wipe demo customers first — they have NULL imported_from,
        # matching the three seeded rows only (not real imports).
        cur = conn.execute(
            "DELETE FROM customers WHERE imported_from IS NULL"
        )
        wiped = cur.rowcount

        # Promote matching contacts
        cur = conn.execute("""
            INSERT INTO customers (name, category, city, state,
                                   contact, gstin, imported_from)
            SELECT name, category, city, state, phone, gstin,
                   'promote:contacts->customers'
            FROM contacts
            WHERE (LOWER(COALESCE(category, '')) LIKE '%contractor%'
                   OR LOWER(COALESCE(buyer_seller_tag, '')) = 'buyer')
              AND name IS NOT NULL AND name != ''
        """)
        promoted = cur.rowcount

        # Write one history row
        conn.execute(
            "INSERT INTO import_history "
            "(file_name, target_table, rows_inserted, rows_skipped, "
            " rows_errored, imported_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("promote:contacts->customers", "customers",
             promoted, 0, 0, _now_iso()),
        )
        conn.commit()
        print(f"[ok] wiped {wiped} demo customer(s)")
        print(f"[ok] promoted {promoted} contacts into customers")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"[fatal] rolled back: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `python scripts/phase1_promote_customers.py`
Expected: wipes 3 demo rows (the seeded ones), promotes some N contractors.

- [ ] **Step 3: Verify**

Run:
```bash
python -c "
import sqlite3
c = sqlite3.connect('bitumen_dashboard.db')
# demo names should be gone
for n in ('L&T Construction (Hyderabad)',):
    row = c.execute('SELECT COUNT(*) FROM customers WHERE name=?',(n,)).fetchone()
    print(f'{n}: {row[0]}')
print('total customers:', c.execute('SELECT COUNT(*) FROM customers').fetchone()[0])
"
```
Expected: `L&T Construction (Hyderabad): 0` and total customers > 0.

- [ ] **Step 4: Commit**

```bash
git add scripts/phase1_promote_customers.py
git commit -m "feat(import): promote contractor contacts into customers + wipe demo rows"
```

---

## Task 8: Purge `sales_parties.json` references

**Files:**
- Modify: `business_advisor_engine.py:164`
- Modify: `crm_engine.py:406-410`
- Modify: `missing_inputs_engine.py:216`
- Modify: `negotiation_engine.py:233`
- Modify: `opportunity_engine.py:323`
- Modify: `recommendation_engine.py:225`
- Modify: `party_master.py:64`
- Modify: `seed_data.py:49-88`

- [ ] **Step 1: Add a shared helper for reading customers from DB**

Create `customer_source.py`:

```python
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
```

- [ ] **Step 2: Replace each engine's `sales_parties.json` read**

For each of these files, replace the `sales_parties.json` read with `from customer_source import load_customers; parties = load_customers()`:

In `business_advisor_engine.py`, find:
```python
        return _load_json(BASE / "sales_parties.json", [])
```
Replace with:
```python
        from customer_source import load_customers
        return load_customers()
```

Apply the same mechanical swap in:
- `crm_engine.py` (replace both the fallback block at ~406-410 — remove the try/except around the JSON read, call load_customers() directly)
- `missing_inputs_engine.py:216` — swap the `_load_json(BASE / "sales_parties.json", [])` call
- `negotiation_engine.py:233` — replace the try/except JSON read with a `load_customers()` call
- `opportunity_engine.py:323` — swap the `_load_json` call
- `recommendation_engine.py:225` — swap the `_load_json` call

In `party_master.py`, remove the `SALES_PARTY_FILE = "sales_parties.json"` constant and anywhere it is read, replace with `load_customers()` from `customer_source`. If any code _writes_ to the file, remove the write (the DB is now the source of truth).

In `seed_data.py`, replace the body of `seed_contacts()` with:

```python
def seed_contacts():
    """Deprecated — contacts are now loaded from tbl_contacts.json via
    scripts/phase1_sync_contacts.py. This stub is kept for compatibility
    with callers in __main__ and should be removed in Phase 2."""
    print("seed_contacts: no-op (Phase 1 — see scripts/phase1_sync_contacts.py)")
```

- [ ] **Step 3: Verify no remaining references**

Run:
```bash
python -c "
import pathlib
hits = []
for p in pathlib.Path('.').rglob('*.py'):
    if '__pycache__' in str(p) or 'generate_pdf_demos' in str(p):
        continue
    if 'sales_parties.json' in p.read_text(encoding='utf-8', errors='ignore'):
        hits.append(str(p))
print('remaining:', hits)
"
```
Expected: only `scripts/phase1_backup.py` (which lists it as a backup target — acceptable) and `comprehensive_audit.py` / `full_audit_suite.py` (audit scripts that list known paths — acceptable dev-only).

- [ ] **Step 4: Smoke-test the app still starts**

Run:
```bash
python -c "
import business_advisor_engine, crm_engine, missing_inputs_engine
import negotiation_engine, opportunity_engine, recommendation_engine
import party_master, seed_data
print('all engines import cleanly')
"
```
Expected: prints the success line, no ImportError.

- [ ] **Step 5: Commit**

```bash
git add customer_source.py business_advisor_engine.py crm_engine.py \
        missing_inputs_engine.py negotiation_engine.py opportunity_engine.py \
        recommendation_engine.py party_master.py seed_data.py
git commit -m "refactor: route customer reads through customer_source (DB-backed)"
```

---

## Task 9: Delete sales_parties.json and mock_data.py

**Files:**
- Delete: `sales_parties.json`
- Delete: `mock_data.py`
- Delete: `add_mock_customers.py` (scan first)

- [ ] **Step 1: Scan `add_mock_customers.py`**

Run: `head -30 add_mock_customers.py`
Expected: a script that seeds demo customers. If it references anything else (a module you have not audited), pause and audit.

- [ ] **Step 2: Audit `mock_data.py` callers**

Run:
```bash
python -c "
import pathlib
hits = []
for p in pathlib.Path('.').rglob('*.py'):
    if '__pycache__' in str(p):
        continue
    txt = p.read_text(encoding='utf-8', errors='ignore')
    if 'import mock_data' in txt or 'from mock_data' in txt:
        hits.append(str(p))
print(hits)
"
```
Expected: zero hits, OR a short list. If there are hits, open each and remove the import before deleting (any call would be demo-only).

- [ ] **Step 3: Delete the files**

```bash
git rm sales_parties.json mock_data.py add_mock_customers.py
```

- [ ] **Step 4: Smoke-test imports**

Run: `python -c "import dashboard; print('ok')"`
Expected: `ok`, no ImportError about mock_data.

If ImportError — a previously-unfound caller exists. Open it, remove the reference, repeat.

- [ ] **Step 5: Commit**

```bash
git commit -m "chore: delete sales_parties.json + mock_data.py + add_mock_customers.py"
```

---

## Task 10: Purge hardcoded demo strings in UI placeholders

**Files:**
- Create: `scripts/phase1_purge_demo_strings.py`
- Modify (via the script): ~12 files

- [ ] **Step 1: Write the purge script**

Create `scripts/phase1_purge_demo_strings.py`:

```python
"""Replace hardcoded demo placeholder strings across the codebase.

SKIPS: generate_pdf_demos.py, docs/, tests/, scripts/, __pycache__/, .git/
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"docs", "tests", "scripts", "__pycache__", ".git",
             "demo_pdfs", ".bak.archive"}
SKIP_FILES = {"generate_pdf_demos.py"}

# (needle, replacement) — both strings appear inside quotes in source.
REPLACEMENTS: list[tuple[str, str]] = [
    # Placeholder strings shown to the user inside st.text_input placeholders
    ("e.g. L&T Construction", "e.g. customer name"),
    ("e.g. Shree Ganesh Infra", "e.g. customer name"),
    ("e.g. Highway Builders", "e.g. customer name"),
    # Example inline text in business knowledge — replace with a generic label
    ("A salesperson talking to L&T Construction", "A salesperson talking to a major contractor"),
    # Placeholder city hardcoding
    ('"L&T Construction": "Mumbai"', '# placeholder removed — load live from DB'),
]


def process(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text
    for needle, rep in REPLACEMENTS:
        text = text.replace(needle, rep)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def main() -> int:
    changed = []
    for p in ROOT.rglob("*.py"):
        rel_parts = set(p.relative_to(ROOT).parts)
        if rel_parts & SKIP_DIRS or p.name in SKIP_FILES:
            continue
        if process(p):
            changed.append(str(p.relative_to(ROOT)))
    print(f"Modified {len(changed)} files:")
    for c in changed:
        print(f"  - {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the purge**

Run: `python scripts/phase1_purge_demo_strings.py`
Expected: reports 5-12 modified files (typical).

- [ ] **Step 3: Handle the hardcoded contractor dict in `demand_analytics.py`**

Open `command_intel/demand_analytics.py`. Around line 16 there is a hardcoded list:

```python
    CONTRACTORS = [
        {"name": "L&T Construction", ...},
        ...
    ]
```

Replace the whole hardcoded block with a live query. Find the `CONTRACTORS = [` line and replace the list literal (up to its closing `]`) with a function call:

```python
def _load_contractors():
    """Load contractors from the customers table (category contains 'contractor')."""
    import sqlite3
    conn = sqlite3.connect(Path(__file__).resolve().parent.parent / "bitumen_dashboard.db")
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT name, city, state, category "
            "FROM customers "
            "WHERE LOWER(COALESCE(category,'')) LIKE '%contractor%' "
            "ORDER BY name LIMIT 50"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


CONTRACTORS = _load_contractors()
```

(If the original list had fields beyond name/city/state/category, include them in the SELECT. Open the original block first to confirm.)

- [ ] **Step 4: Handle the hardcoded buyer in `supply_chain.py`**

Open `command_intel/supply_chain.py` around line 52 and remove the `"buyer": "L&T Construction"` line. Replace with:

```python
            "buyer": "",  # populated from deals.customer_id at render time
```

- [ ] **Step 5: Fix the `Rohan Kumar` comment in navigation_engine.py**

Open `navigation_engine.py:974` and change the example inside the docstring from `Rohan Kumar · Pune · VG30` to `<Customer Name> · <City> · <Grade>`. This is cosmetic — still counts toward the zero-demo-string grep.

- [ ] **Step 6: Verify the grep check**

Run:
```bash
python -c "
import pathlib
forbidden = ['L&T Construction', 'Rohan Kumar', 'Shree Ganesh', 'Highway Builders']
hits = []
for p in pathlib.Path('.').rglob('*.py'):
    rel = str(p)
    if any(x in rel for x in ['__pycache__','generate_pdf_demos','tests/','docs/','scripts/','.bak.archive']):
        continue
    txt = p.read_text(encoding='utf-8', errors='ignore')
    for needle in forbidden:
        if needle in txt:
            hits.append((str(p.relative_to('.')), needle))
for h in hits: print(h)
print('total:', len(hits))
"
```
Expected: `total: 0`.

- [ ] **Step 7: Commit**

```bash
git add scripts/phase1_purge_demo_strings.py \
        command_intel/demand_analytics.py command_intel/supply_chain.py \
        navigation_engine.py \
        $(git diff --name-only)
git commit -m "refactor: purge demo placeholder strings + hardcoded contractor list"
```

---

## Task 11: Import wizard — skeleton + Step 1 (upload)

**Files:**
- Create: `pages/system/import_wizard.py`

- [ ] **Step 1: Write the wizard skeleton**

Create `pages/system/import_wizard.py`:

```python
"""Import Wizard — 5-step flow for Excel/CSV → DB.

Steps:
  1  Upload        (file picker)
  2  Map columns   (auto-suggested, user-overridable)
  3  Classify      (target table + category tag)
  4  Preview       (validation + dedupe + first 20 rows)
  5  Commit        (progress + summary)

State lives in st.session_state["_iw"] — a dict keyed by step number.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from contact_import_engine import (
    parse_spreadsheet, suggest_column_mapping,
    validate_rows, dedupe_against_db, commit_import,
)

TARGETS = [
    ("customers", "Customer — Contractor / Buyer"),
    ("suppliers", "Supplier — Refinery / Importer"),
    ("contacts",  "Contact — General directory"),
    ("customer_profiles", "Customer profile — WhatsApp data"),
]
TARGET_SCHEMAS = {
    "customers":         ["name", "phone", "city", "state", "gstin",
                          "address", "category"],
    "suppliers":         ["name", "phone", "city", "state", "gstin",
                          "category"],
    "contacts":          ["name", "phone", "email", "city", "state",
                          "category"],
    "customer_profiles": ["name", "company", "phone", "email", "city",
                          "state", "category", "notes"],
}


def _iw() -> dict:
    return st.session_state.setdefault("_iw", {"step": 1})


def _set_step(n: int):
    _iw()["step"] = n


def render():
    st.markdown("## 📥 Import Wizard")
    st.caption("Excel / CSV → SQLite. Dedupe, preview, commit, revert — all inside.")

    step = _iw()["step"]
    cols = st.columns(5)
    for i, label in enumerate(["Upload", "Map", "Classify", "Preview", "Commit"]):
        with cols[i]:
            active = i + 1 == step
            color = "#4F46E5" if active else "#9CA3AF"
            st.markdown(
                f"<div style='text-align:center;color:{color};font-weight:"
                f"{'700' if active else '400'};font-size:0.9rem;'>"
                f"{'●' if active else '○'} {i+1}. {label}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("---")

    if step == 1:
        _step1_upload()
    elif step == 2:
        _step2_map()
    elif step == 3:
        _step3_classify()
    elif step == 4:
        _step4_preview()
    elif step == 5:
        _step5_commit()


# ── Step 1: Upload ─────────────────────────────────────────────────

def _step1_upload():
    st.subheader("Step 1 — Upload Excel or CSV")
    up = st.file_uploader("Drop a .xlsx or .csv file",
                          type=["xlsx", "xls", "csv"],
                          key="_iw_file")
    if up is None:
        st.info("Tip: first row must be column headers.")
        return

    # Persist to a temp path so subsequent steps can re-read
    suffix = Path(up.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(up.getvalue())
    tmp.close()

    try:
        df = parse_spreadsheet(tmp.name)
    except ValueError as e:
        st.error(str(e))
        return

    st.success(f"✅ Loaded `{up.name}` — **{len(df)} rows × {len(df.columns)} cols**")
    with st.expander("Preview first 5 rows"):
        st.dataframe(df.head(5), use_container_width=True)

    _iw().update({
        "file_name": up.name,
        "tmp_path":  tmp.name,
        "source_cols": list(df.columns),
    })
    if st.button("Next → Map columns", type="primary"):
        _set_step(2)
        st.rerun()
```

- [ ] **Step 2: Add a nav entry**

Find `nav_config.py` and add the import wizard to the System module. Open `nav_config.py`, locate the System module's page list, and add an entry `{"key": "import_wizard", "label": "📥 Import Wizard", "path": "pages.system.import_wizard"}` (follow whatever exact shape the file uses — look at an existing entry first).

If `nav_config.py` uses a dispatch dict (e.g. `PAGE_DISPATCH`), also register the page there so it is reachable.

- [ ] **Step 3: Smoke-test the page renders**

Run: `python -c "from pages.system import import_wizard; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add pages/system/import_wizard.py nav_config.py
git commit -m "feat(wizard): Step 1 upload + nav registration"
```

---

## Task 12: Import wizard — Steps 2-3 (map + classify)

**Files:**
- Modify: `pages/system/import_wizard.py` (append two functions)

- [ ] **Step 1: Append Step 2 (Map) and Step 3 (Classify)**

Append to `pages/system/import_wizard.py`:

```python
# ── Step 2: Map columns ────────────────────────────────────────────

def _step2_map():
    st.subheader("Step 2 — Map columns")
    state = _iw()
    source_cols = state.get("source_cols", [])
    if not source_cols:
        st.error("No file loaded — restart from Step 1.")
        if st.button("← Back to Upload"):
            _set_step(1)
            st.rerun()
        return

    target_table = state.get("target_table", "customers")
    schema = TARGET_SCHEMAS[target_table]
    suggested = suggest_column_mapping(source_cols, schema)

    st.caption(f"Target table: **{target_table}** — assign a source column to each field.")
    chosen: dict[str, str] = {}
    for field in schema:
        default = suggested.get(field, "")
        options = [""] + source_cols
        idx = options.index(default) if default in options else 0
        chosen[field] = st.selectbox(
            f"**{field}**"
            + ("  _(required)_" if field == "name" else ""),
            options, index=idx, key=f"_iw_map_{field}"
        )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            _set_step(1)
            st.rerun()
    with c2:
        if st.button("Next → Classify", type="primary"):
            if not chosen.get("name"):
                st.warning("`name` is required — pick a source column.")
            else:
                state["mapping"] = {k: v for k, v in chosen.items() if v}
                _set_step(3)
                st.rerun()


# ── Step 3: Classify (target + category) ───────────────────────────

def _step3_classify():
    st.subheader("Step 3 — Classify")
    state = _iw()

    current = state.get("target_table", "customers")
    labels = [lbl for _, lbl in TARGETS]
    keys   = [k   for k, _   in TARGETS]
    idx    = keys.index(current) if current in keys else 0

    picked_label = st.radio("Import these rows as", labels, index=idx)
    picked_key   = keys[labels.index(picked_label)]

    category = st.text_input(
        "Default category tag (optional)",
        value=state.get("category", ""),
        placeholder="e.g. Contractor, Trader, Refinery",
        help="Applied to rows whose category column is blank.",
    )
    dedupe_strategy = st.radio(
        "If a row already exists in the DB (same name + phone)",
        ["skip", "overwrite", "merge"],
        index=["skip", "overwrite", "merge"].index(
            state.get("dedupe_strategy", "skip")
        ),
        horizontal=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            _set_step(2)
            st.rerun()
    with c2:
        if st.button("Next → Preview", type="primary"):
            state.update({
                "target_table": picked_key,
                "category": category.strip(),
                "dedupe_strategy": dedupe_strategy,
            })
            _set_step(4)
            st.rerun()
```

- [ ] **Step 2: Smoke-test**

Run: `python -c "from pages.system import import_wizard; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add pages/system/import_wizard.py
git commit -m "feat(wizard): Steps 2-3 — map columns + classify"
```

---

## Task 13: Import wizard — Steps 4-5 (preview + commit)

**Files:**
- Modify: `pages/system/import_wizard.py` (append two functions + helper)

- [ ] **Step 1: Append Steps 4 and 5**

Append to `pages/system/import_wizard.py`:

```python
# ── Step 4: Preview ────────────────────────────────────────────────

def _step4_preview():
    st.subheader("Step 4 — Preview & clean")
    state = _iw()
    try:
        df = parse_spreadsheet(state["tmp_path"])
    except Exception as e:
        st.error(f"Could not re-read file: {e}")
        return

    # Apply mapping: rename source → canonical target fields
    inverse = {src: tgt for tgt, src in state["mapping"].items()}
    df = df.rename(columns=inverse)[list(state["mapping"].keys())]

    # Default category if blank
    if state.get("category") and "category" in df.columns:
        df["category"] = df["category"].replace("", state["category"])

    valid, invalid = validate_rows(df, state["target_table"])
    fresh = dedupe_against_db(
        valid, state["target_table"], strategy=state["dedupe_strategy"]
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Valid", len(valid))
    m2.metric("Invalid", len(invalid))
    m3.metric("Fresh (after dedupe)", len(fresh))

    with st.expander(f"Preview first 20 of {len(fresh)} rows to insert",
                     expanded=True):
        st.dataframe(fresh.head(20), use_container_width=True)

    if len(invalid):
        with st.expander(f"⚠️ {len(invalid)} invalid row(s)"):
            st.dataframe(invalid, use_container_width=True)

    state["fresh_count"] = len(fresh)
    state["invalid_count"] = len(invalid)
    # Stash fresh to a temp parquet so Step 5 does not re-compute
    fresh_path = Path(state["tmp_path"]).with_suffix(".fresh.parquet")
    fresh.to_parquet(fresh_path)
    state["fresh_path"] = str(fresh_path)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            _set_step(3)
            st.rerun()
    with c2:
        disabled = len(fresh) == 0
        if st.button("Commit import →", type="primary", disabled=disabled):
            _set_step(5)
            st.rerun()
    if disabled:
        st.caption("Nothing to commit — change dedupe strategy or upload a different file.")


# ── Step 5: Commit ─────────────────────────────────────────────────

def _step5_commit():
    st.subheader("Step 5 — Commit import")
    state = _iw()

    import pandas as pd
    fresh = pd.read_parquet(state["fresh_path"])
    with st.spinner(f"Inserting {len(fresh)} rows into "
                    f"{state['target_table']}…"):
        try:
            result = commit_import(
                fresh, state["target_table"],
                source_file=state["file_name"],
            )
        except Exception as e:
            st.error(f"Import failed — rolled back. Reason: {e}")
            if st.button("← Back to Preview"):
                _set_step(4)
                st.rerun()
            return

    st.success(f"✅ Inserted **{result['inserted']}** rows "
               f"(import_history id = {result['import_history_id']})")
    st.balloons()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Open Contacts Directory"):
            from navigation_engine import navigate_to
            navigate_to("contacts_directory_dashboard")
    with c2:
        if st.button("Start another import"):
            st.session_state.pop("_iw", None)
            _set_step(1)
            st.rerun()
```

- [ ] **Step 2: Smoke-test end-to-end programmatically**

Run:
```bash
python - <<'EOF'
import tempfile, pandas as pd
from pathlib import Path
from contact_import_engine import parse_spreadsheet, commit_import

# Make a tiny CSV
csv = Path(tempfile.mkdtemp()) / "wizard_smoke.csv"
csv.write_text("name,phone,city\nAsha,+919876543210,Pune\n",
               encoding="utf-8")

df = parse_spreadsheet(csv)
result = commit_import(df, "contacts", source_file=csv.name)
print(result)
EOF
```
Expected: `{'inserted': 1, 'skipped': 0, 'errors': 0, 'import_history_id': <N>}`

- [ ] **Step 3: Revert the smoke test**

Run:
```bash
python -c "
from contact_import_engine import revert_import
import sqlite3
c = sqlite3.connect('bitumen_dashboard.db')
last = c.execute(
    'SELECT id FROM import_history WHERE file_name=\"wizard_smoke.csv\" '
    'ORDER BY id DESC LIMIT 1').fetchone()
c.close()
print('reverted:', revert_import(last[0]))
"
```
Expected: `reverted: 1`.

- [ ] **Step 4: Commit**

```bash
git add pages/system/import_wizard.py
git commit -m "feat(wizard): Steps 4-5 — preview, validate, dedupe, commit"
```

---

## Task 14: Import history dashboard

**Files:**
- Create: `pages/system/import_history.py`

- [ ] **Step 1: Write the history page**

Create `pages/system/import_history.py`:

```python
"""Import History — view past imports, revert the most recent."""
from __future__ import annotations
import sqlite3
from pathlib import Path

import streamlit as st
import pandas as pd

from contact_import_engine import revert_import

DB = Path(__file__).resolve().parent.parent.parent / "bitumen_dashboard.db"


def _load() -> pd.DataFrame:
    conn = sqlite3.connect(DB)
    try:
        return pd.read_sql_query(
            "SELECT id, imported_at, file_name, target_table, "
            "rows_inserted, rows_skipped, rows_errored, reverted "
            "FROM import_history ORDER BY id DESC LIMIT 50",
            conn,
        )
    finally:
        conn.close()


def render():
    st.markdown("## 🗂️ Import History")
    st.caption("Last 50 imports. Revert removes the rows inserted by that import.")

    df = _load()
    if df.empty:
        st.info("No imports yet — try the Import Wizard.")
        return

    for _, r in df.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 2, 1])
            with c1:
                reverted_badge = " · 🔁 reverted" if r["reverted"] else ""
                st.markdown(
                    f"**{r['file_name']}** → `{r['target_table']}`{reverted_badge}"
                )
                st.caption(f"{r['imported_at']} · id={r['id']}")
            with c2:
                st.metric("Inserted", int(r["rows_inserted"]))
            with c3:
                disabled = bool(r["reverted"])
                if st.button("Revert", key=f"_rev_{r['id']}",
                             disabled=disabled, type="secondary"):
                    with st.spinner("Reverting…"):
                        try:
                            n = revert_import(int(r["id"]))
                            st.success(f"Removed {n} row(s)")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
```

- [ ] **Step 2: Register in nav**

In `nav_config.py`, add the import_history page under System module the same way you did for import_wizard in Task 11.

- [ ] **Step 3: Smoke-test**

Run: `python -c "from pages.system import import_history; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add pages/system/import_history.py nav_config.py
git commit -m "feat(wizard): import history dashboard with revert"
```

---

## Task 15: Wire Daily Core pages to real DB reads

**Files:**
- Modify: `pages/pricing/pricing_calculator.py`
- Modify: `pages/sales/negotiation.py`
- Modify: `pages/sales/comm_hub.py`
- Modify: `pages/sales/crm_tasks.py`
- Modify: `pages/home/opportunities.py`

(Most of these already consume `customer_source.load_customers()` after Task 8. This task is a scan pass to catch remaining hardcoded dropdowns or demo defaults.)

- [ ] **Step 1: Scan each file for demo lists**

Run:
```bash
grep -n "options=\[\"[A-Z]" pages/pricing/pricing_calculator.py \
                            pages/sales/negotiation.py \
                            pages/sales/comm_hub.py \
                            pages/sales/crm_tasks.py \
                            pages/home/opportunities.py
```
Expected: lists of literal customer names (if any).

For each hit, replace the literal list with a DB fetch:

```python
from customer_source import load_customers
_options = [c["name"] for c in load_customers()]
if not _options:
    st.warning("No customers in DB yet — open /System/Import Wizard to add.")
    _options = [""]
```

- [ ] **Step 2: Empty-state on Command Center**

Open `pages/home/command_center.py`. Where KPIs are rendered (search for "Active Deals", "Pending Tasks"), wrap the display so that if the DB returns 0/None, the card shows "—" instead of a misleading zero. Example pattern:

```python
active = _get_active_deal_count()  # returns int or None
display = "—" if not active else str(active)
st.metric("Active Deals", display)
```

- [ ] **Step 3: Smoke-test**

Run: `python -c "from pages.home import command_center; from pages.sales import crm_tasks, comm_hub, negotiation; from pages.pricing import pricing_calculator; from pages.home import opportunities; print('ok')"`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add pages/
git commit -m "refactor: Daily Core pages use live DB reads + empty-states"
```

---

## Task 16: Import Prince's WhatsApp customer profile Excel

**Files:**
- Use: `../Bitumen_Customer_Profile_WhatsApp.xlsx`

- [ ] **Step 1: Copy the Excel into the project folder for the wizard**

Run: `cp "../Bitumen_Customer_Profile_WhatsApp.xlsx" ./`

- [ ] **Step 2: Open the wizard in Streamlit**

Run: `streamlit run dashboard.py`
Then: log in → System → Import Wizard

- [ ] **Step 3: Walk through the 5 steps**

1. Upload `Bitumen_Customer_Profile_WhatsApp.xlsx`
2. Map columns — accept suggestions or adjust
3. Classify — target = **Customer profile — WhatsApp data**, dedupe = skip
4. Preview — eyeball first 20 rows
5. Commit — wait for the ✅ summary

- [ ] **Step 4: Verify rows landed**

Run:
```bash
python -c "
import sqlite3
n = sqlite3.connect('bitumen_dashboard.db').execute(
    'SELECT COUNT(*) FROM customer_profiles').fetchone()[0]
print(f'customer_profiles: {n} rows')
"
```
Expected: a positive count (whatever the Excel had).

- [ ] **Step 5: Commit (but not the Excel)**

```bash
git rm Bitumen_Customer_Profile_WhatsApp.xlsx  # if it accidentally got staged
git commit --allow-empty -m "chore: Prince's WhatsApp customer profile imported via wizard"
```

The customer data is now in `bitumen_dashboard.db`. The Excel stays out of the repo (it is user data, not code).

---

## Task 17: Regression — existing AppTest journeys must still pass

**Files:**
- Run-only; no code changes unless a journey breaks.

- [ ] **Step 1: Locate existing AppTest journey scripts**

Run: `grep -rn "AppTest" --include="*.py" tests/ scripts/ *.py 2>/dev/null | head`
Expected: existing journey test files listed (morning-intel, sales-flow, deal-to-dispatch).

- [ ] **Step 2: Run them**

Run: `python -m pytest tests/ -v -k "journey"`
Expected: 3 journey tests pass, 0 errors, 0 failures.

If any fail, the failure must be investigated and fixed before proceeding.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 4: Commit if any fix was required**

Only commit if Step 2 or 3 needed a fix. Message: `fix: journey X regression after Phase 1 migration`.

---

## Task 18: Acceptance — final grep gate

**Files:**
- Run-only.

- [ ] **Step 1: Zero-demo-strings grep**

Run:
```bash
python -c "
import pathlib
forbidden = ['L&T Construction', 'Rohan Kumar', 'Shree Ganesh',
             'Highway Builders', '\"sales_parties.json\"']
skip_markers = ['__pycache__', 'generate_pdf_demos', 'tests/',
                'docs/', 'scripts/', '.bak.archive', 'comprehensive_audit',
                'full_audit_suite']
hits = []
for p in pathlib.Path('.').rglob('*.py'):
    rel = str(p)
    if any(m in rel for m in skip_markers):
        continue
    txt = p.read_text(encoding='utf-8', errors='ignore')
    for needle in forbidden:
        if needle in txt:
            hits.append((rel, needle))
for h in hits: print(h)
print('total:', len(hits))
"
```
Expected: `total: 0`.

- [ ] **Step 2: Counts sanity check**

Run:
```bash
python -c "
import sqlite3
c = sqlite3.connect('bitumen_dashboard.db')
for t in ('contacts', 'customers', 'suppliers', 'customer_profiles', 'import_history'):
    n = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {n}')
"
```
Expected: `contacts ≥ 25000`, `customers > 0`, `suppliers = 63`, `customer_profiles > 0`, `import_history ≥ 2` (at least the main sync + wizard run).

- [ ] **Step 3: Prince signs off**

Open the deployed app. Walk Daily Core pages in order:
Command Center → Live Market → Opportunities → Pricing Calculator → Price Prediction → CRM Tasks → Negotiation → Daily Log → News → Market Signals → Telegram Analyzer → Documents → Director Brief → Settings.

For each: no fake names visible, either real data or "—" / empty-state.

- [ ] **Step 4: Final commit**

```bash
git commit --allow-empty -m "phase-1: demo purge + real data sync — complete"
git tag phase-1-complete
```

---

## Deferred to later phases

- Live refresh / auto-polling component — Phase 2.
- Nav simplification (80 pages → Daily Core + Advanced drawer) — Phase 3.
- Per-page UX pass (active-customer banner, last-updated strip, empty states, share buttons) — Phase 4.

---

## Self-review

**Spec coverage — every section has a task:**

- Goals 1–5 → Tasks 7, 6, 16, 11-14, 15
- Non-goals → explicitly deferred above
- Done criteria → Task 18
- Data audit table → Tasks 7, 8, 9, 10
- Import wizard design → Tasks 11-13
- Import engine spec → Tasks 3-5
- Schema changes → Task 2
- Migration sequence → Tasks 0 through 16 in order
- Code touchpoints → Tasks 8-10, 15
- Error handling (rollback, invalid rows, mid-crash) → Tasks 5, 13
- Testing → Tasks 3-5 (unit), 17 (journey regression), 18 (final gate)
- Rollback strategy → Task 0 (backup), import_history revert (Tasks 5, 14, 16)

**Placeholder scan:** No TBDs, no "add appropriate error handling", no "similar to Task N". Every code step shows code.

**Type consistency:** `commit_import` signature `(df, target_table, source_file, db_path=...)` is consistent across Tasks 5, 6, 7, 13, 16. `revert_import(import_history_id, db_path=...)` consistent across Tasks 5, 13, 14. Column mapping returns `dict[str, str]` target→source consistently. The `_iw()` dict keys (`step`, `tmp_path`, `source_cols`, `mapping`, `target_table`, `category`, `dedupe_strategy`, `fresh_path`, `file_name`) are introduced in Task 11 and referenced consistently in Tasks 12-13.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-14-phase1-demo-purge.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
