"""
Migrate Contacts to SQLite — One-Time Migration Script
=======================================================
Reads tbl_contacts.json (66 contacts) + customers (3) + suppliers (63)
from existing stores and inserts into the unified SQLite 'contacts' table.

Usage:
  python migrate_contacts_to_sqlite.py
"""

import json
import sys
import os
import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database import (
    init_db, upsert_contact, get_all_contacts,
    _get_conn,
)
from pathlib import Path

BASE = Path(__file__).parent
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")


def _load_json(filename: str) -> list[dict]:
    fp = BASE / filename
    if not fp.exists():
        return []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def migrate_json_contacts() -> dict:
    """Migrate tbl_contacts.json records to SQLite contacts table."""
    records = _load_json("tbl_contacts.json")
    migrated = 0
    skipped = 0
    errors = []

    for r in records:
        try:
            name = (r.get("person_name") or r.get("name")
                    or r.get("company_name") or "").strip()
            if not name:
                skipped += 1
                continue

            row = {
                "name": name,
                "company_name": r.get("company_name", ""),
                "contact_type": "prospect",
                "category": r.get("category_type", r.get("category", "")),
                "buyer_seller_tag": r.get("buyer_seller_tag", "unknown"),
                "city": r.get("city", ""),
                "state": r.get("state", ""),
                "address": r.get("address", ""),
                "pincode": r.get("pincode", ""),
                "mobile1": r.get("mobile1", r.get("phone", "")),
                "mobile2": r.get("mobile2", ""),
                "email": r.get("email1", r.get("email", "")),
                "gstin": r.get("gstin", ""),
                "pan": r.get("pan", ""),
                "source": "json_migration",
                "notes": r.get("notes", ""),
                "is_active": 1,
            }
            upsert_contact(row)
            migrated += 1
        except Exception as e:
            errors.append(f"{r.get('person_name', '?')}: {e}")

    return {"source": "tbl_contacts.json", "total": len(records),
            "migrated": migrated, "skipped": skipped, "errors": errors}


def migrate_customers() -> dict:
    """Migrate SQLite customers table records to contacts table."""
    migrated = 0
    skipped = 0
    errors = []

    try:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM customers").fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM customers LIMIT 0").description]
    except Exception as e:
        return {"source": "customers", "total": 0, "migrated": 0,
                "skipped": 0, "errors": [str(e)]}

    for row_tuple in rows:
        r = dict(zip(cols, row_tuple))
        try:
            name = (r.get("name") or r.get("company_name") or "").strip()
            if not name:
                skipped += 1
                continue

            contact = {
                "name": name,
                "company_name": r.get("company_name", name),
                "contact_type": "customer",
                "category": "Buyer",
                "buyer_seller_tag": "buyer",
                "city": r.get("city", ""),
                "state": r.get("state", ""),
                "address": r.get("address", ""),
                "pincode": "",
                "mobile1": r.get("phone", r.get("mobile", "")),
                "mobile2": "",
                "email": r.get("email", ""),
                "gstin": r.get("gstin", ""),
                "pan": "",
                "source": "customer_migration",
                "notes": f"Customer ID: {r.get('id', '')}",
                "is_active": 1,
                "customer_id": r.get("id"),
            }
            upsert_contact(contact)
            migrated += 1
        except Exception as e:
            errors.append(f"Customer {r.get('name', '?')}: {e}")

    return {"source": "customers", "total": len(rows),
            "migrated": migrated, "skipped": skipped, "errors": errors}


def migrate_suppliers() -> dict:
    """Migrate SQLite suppliers table records to contacts table."""
    migrated = 0
    skipped = 0
    errors = []

    try:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM suppliers").fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM suppliers LIMIT 0").description]
    except Exception as e:
        return {"source": "suppliers", "total": 0, "migrated": 0,
                "skipped": 0, "errors": [str(e)]}

    for row_tuple in rows:
        r = dict(zip(cols, row_tuple))
        try:
            name = (r.get("name") or r.get("company_name") or "").strip()
            if not name:
                skipped += 1
                continue

            contact = {
                "name": name,
                "company_name": r.get("company_name", name),
                "contact_type": "supplier",
                "category": r.get("category", "Supplier"),
                "buyer_seller_tag": "seller",
                "city": r.get("city", ""),
                "state": r.get("state", ""),
                "address": r.get("address", ""),
                "pincode": "",
                "mobile1": r.get("phone", r.get("mobile", "")),
                "mobile2": "",
                "email": r.get("email", ""),
                "gstin": r.get("gstin", ""),
                "pan": "",
                "source": "supplier_migration",
                "notes": f"Supplier ID: {r.get('id', '')}",
                "is_active": 1,
                "supplier_id": r.get("id"),
            }
            upsert_contact(contact)
            migrated += 1
        except Exception as e:
            errors.append(f"Supplier {r.get('name', '?')}: {e}")

    return {"source": "suppliers", "total": len(rows),
            "migrated": migrated, "skipped": skipped, "errors": errors}


def main():
    print("=" * 60)
    print("  Contact Migration to SQLite")
    print("=" * 60)

    # Ensure DB is initialized with new tables
    init_db()
    print("  Database initialized (contacts table ready)")

    # Check existing count
    existing = get_all_contacts(active_only=False)
    print(f"  Existing contacts in SQLite: {len(existing)}")

    results = []

    # 1. Migrate JSON contacts
    r1 = migrate_json_contacts()
    results.append(r1)
    print(f"\n  [JSON Contacts] total={r1['total']} migrated={r1['migrated']} "
          f"skipped={r1['skipped']} errors={len(r1['errors'])}")

    # 2. Migrate customers
    r2 = migrate_customers()
    results.append(r2)
    print(f"  [Customers]     total={r2['total']} migrated={r2['migrated']} "
          f"skipped={r2['skipped']} errors={len(r2['errors'])}")

    # 3. Migrate suppliers
    r3 = migrate_suppliers()
    results.append(r3)
    print(f"  [Suppliers]     total={r3['total']} migrated={r3['migrated']} "
          f"skipped={r3['skipped']} errors={len(r3['errors'])}")

    # Final count
    final = get_all_contacts(active_only=False)
    total_migrated = sum(r["migrated"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)

    print(f"\n  TOTAL: migrated={total_migrated} errors={total_errors}")
    print(f"  Final SQLite contact count: {len(final)}")
    print("=" * 60)

    # Print any errors
    for r in results:
        if r["errors"]:
            print(f"\n  Errors from {r['source']}:")
            for e in r["errors"][:10]:
                print(f"    - {e}")

    return {"total_migrated": total_migrated, "total_errors": total_errors,
            "final_count": len(final)}


if __name__ == "__main__":
    main()
