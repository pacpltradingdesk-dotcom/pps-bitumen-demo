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
