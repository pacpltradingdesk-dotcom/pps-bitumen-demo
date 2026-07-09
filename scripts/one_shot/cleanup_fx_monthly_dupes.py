"""One-shot: dedupe monthly-average rows in tbl_fx_rates.json.

The rbi_fx_historical connector used to re-APPEND all ~13 monthly-average rows
on every run (fresh date_time each time), flooding the table with stale-month
duplicates and evicting live-spot rows via the max_records trim. The connector
now upserts (see govt_connectors.upsert_period_records); this script repairs
the already-polluted file: keeps the LATEST row per (period_label, pair),
keeps every non-period (live spot) row, preserves order.

Run from repo root (works on the VPS too):
    python scripts/one_shot/cleanup_fx_monthly_dupes.py
Writes a .bak backup next to the file before saving.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FX_PATH = ROOT / "tbl_fx_rates.json"


def dedupe_monthly(rows: list) -> list:
    latest_idx: dict = {}
    for i, r in enumerate(rows):
        if isinstance(r, dict) and r.get("period_label"):
            latest_idx[(r.get("period_label"), r.get("pair"))] = i
    keep = set(latest_idx.values())
    return [
        r for i, r in enumerate(rows)
        if not (isinstance(r, dict) and r.get("period_label")) or i in keep
    ]


def main() -> int:
    if not FX_PATH.exists():
        print(f"SKIP: {FX_PATH} not found")
        return 0
    rows = json.loads(FX_PATH.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        print("SKIP: unexpected structure (not a list)")
        return 1

    before_monthly = sum(1 for r in rows if isinstance(r, dict) and r.get("period_label"))
    cleaned = dedupe_monthly(rows)
    after_monthly = sum(1 for r in cleaned if isinstance(r, dict) and r.get("period_label"))

    if len(cleaned) == len(rows):
        print(f"OK: no duplicates ({before_monthly} monthly rows, {len(rows)} total)")
        return 0

    shutil.copy2(FX_PATH, FX_PATH.with_suffix(".json.bak"))
    FX_PATH.write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"CLEANED: {len(rows)} -> {len(cleaned)} rows "
        f"(monthly {before_monthly} -> {after_monthly}); backup: {FX_PATH.name}.bak"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
