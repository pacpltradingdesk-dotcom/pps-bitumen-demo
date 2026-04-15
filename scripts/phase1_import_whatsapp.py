"""Task 16 — Programmatic import of Prince's WhatsApp customer profile Excel.

Reads the 'All Bitumen Contacts' sheet from
../Bitumen_Customer_Profile_WhatsApp.xlsx, maps columns, validates,
dedupes and commits to the customer_profiles table.

Run from project root:
    python scripts/phase1_import_whatsapp.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from contact_import_engine import (
    validate_rows, dedupe_against_db, commit_import
)


def main() -> int:
    # Try several candidate locations (repo root, repo parent, worktree parent…)
    candidates = [
        ROOT / "Bitumen_Customer_Profile_WhatsApp.xlsx",
        ROOT.parent / "Bitumen_Customer_Profile_WhatsApp.xlsx",
        ROOT.parent.parent / "Bitumen_Customer_Profile_WhatsApp.xlsx",
        ROOT.parent.parent.parent / "Bitumen_Customer_Profile_WhatsApp.xlsx",
    ]
    src = next((p for p in candidates if p.exists()), candidates[0])
    if not src.exists():
        print(f"[fatal] source Excel not found: {src}")
        return 1

    print(f"[ok] reading {src}")
    df = pd.read_excel(src, sheet_name="All Bitumen Contacts", dtype=str)
    df = df.fillna("")
    print(f"[ok] loaded {len(df)} rows from 'All Bitumen Contacts'")

    rename = {
        "Name": "name",
        "Company": "company",
        "Category": "category",
        "WhatsApp Phone": "phone",
        "Email": "email",
        "City": "city",
        "State": "state",
        "Remark": "notes",
    }
    df = df.rename(columns=rename)
    keep = [c for c in ["name", "company", "phone", "email",
                        "city", "state", "category", "notes"]
            if c in df.columns]
    df = df[keep]

    valid, invalid = validate_rows(df, "customer_profiles")
    print(f"[ok] validated: {len(valid)} good, {len(invalid)} flagged")

    fresh = dedupe_against_db(valid, "customer_profiles",
                              strategy="skip",
                              db_path=ROOT / "bitumen_dashboard.db")
    print(f"[ok] after dedupe: {len(fresh)} rows to insert")

    if fresh.empty:
        print("[done] nothing new to import")
        return 0

    result = commit_import(fresh, "customer_profiles",
                           source_file="Bitumen_Customer_Profile_WhatsApp.xlsx",
                           db_path=ROOT / "bitumen_dashboard.db")
    print(f"[done] inserted {result['inserted']} rows "
          f"(import_history id = {result['import_history_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
