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
        # NOTE: real contacts table uses mobile1 (not phone)
        cur = conn.execute("""
            INSERT INTO customers (name, category, city, state,
                                   contact, gstin, imported_from)
            SELECT name, category, city, state, mobile1, gstin,
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
