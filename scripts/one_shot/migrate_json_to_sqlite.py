"""
PPS Anantam — JSON to SQLite Migration Script v1.0
====================================================
Migrates all JSON data files into the SQLite database.
Run: python migrate_json_to_sqlite.py

Migrates:
  purchase_parties.json  -> suppliers table
  sales_parties.json     -> customers table
  tbl_crude_prices.json  -> price_history table
  tbl_fx_rates.json      -> fx_history table
  crm_tasks.json         -> (kept in JSON for now, CRM table later)

JSON files are kept as backup (not deleted).
"""

import json
import datetime
from pathlib import Path

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent


def _now():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _load_json(filename):
    path = BASE / filename
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  WARNING: Could not load {filename}: {e}")
    return []


def migrate():
    """Run full migration from JSON to SQLite."""
    print("=" * 60)
    print("PPS Anantam — JSON to SQLite Migration")
    print("=" * 60)
    print()

    # Initialize database
    print("1. Initializing database...")
    from database import init_db, insert_supplier, insert_customer, insert_price_history, insert_fx_rate
    init_db()
    print("  Database initialized: bitumen_dashboard.db")
    print()

    # Migrate suppliers
    print("2. Migrating purchase_parties.json -> suppliers...")
    suppliers = _load_json("purchase_parties.json")
    supplier_count = 0
    for s in suppliers:
        try:
            insert_supplier({
                "name": s.get("name", ""),
                "category": s.get("type", ""),
                "city": s.get("city", ""),
                "contact": s.get("contact", ""),
                "gstin": s.get("gstin", ""),
                "notes": s.get("details", ""),
                "marked_for_purchase": 1 if s.get("marked_for_purchase") else 0,
                "is_active": 1,
                "created_at": _now(),
                "updated_at": _now(),
            })
            supplier_count += 1
        except Exception as e:
            pass  # Skip duplicates
    print(f"  Migrated {supplier_count} suppliers")

    # Migrate customers
    print("3. Migrating sales_parties.json -> customers...")
    customers = _load_json("sales_parties.json")
    customer_count = 0
    for c in customers:
        try:
            insert_customer({
                "name": c.get("name", ""),
                "category": c.get("category", ""),
                "city": c.get("city", ""),
                "state": c.get("state", ""),
                "contact": c.get("contact", ""),
                "gstin": c.get("gstin", ""),
                "address": c.get("address", ""),
                "is_active": 1 if c.get("active", True) else 0,
                "created_at": _now(),
                "updated_at": _now(),
            })
            customer_count += 1
        except Exception as e:
            pass
    print(f"  Migrated {customer_count} customers")

    # Migrate crude prices
    print("4. Migrating tbl_crude_prices.json -> price_history...")
    crude_prices = _load_json("tbl_crude_prices.json")
    if crude_prices:
        price_records = []
        for p in crude_prices:
            price_records.append({
                "date_time": p.get("date_time", ""),
                "benchmark": p.get("benchmark", ""),
                "price": p.get("price", 0),
                "currency": p.get("currency", "USD/bbl"),
                "source": p.get("source", ""),
                "validated": 1,
            })
        insert_price_history(price_records)
        print(f"  Migrated {len(price_records)} price records")
    else:
        print("  No crude price data to migrate")

    # Migrate FX rates
    print("5. Migrating tbl_fx_rates.json -> fx_history...")
    fx_rates = _load_json("tbl_fx_rates.json")
    fx_count = 0
    for fx in fx_rates:
        try:
            insert_fx_rate({
                "date_time": fx.get("date_time", ""),
                "from_currency": fx.get("from_currency", "USD"),
                "to_currency": fx.get("to_currency", "INR"),
                "rate": fx.get("rate", 0),
                "source": fx.get("source", ""),
            })
            fx_count += 1
        except Exception:
            pass
    print(f"  Migrated {fx_count} FX rate records")

    # Summary
    print()
    print("=" * 60)
    print("Migration Summary:")
    print(f"  Suppliers: {supplier_count}")
    print(f"  Customers: {customer_count}")
    print(f"  Price History: {len(crude_prices) if crude_prices else 0}")
    print(f"  FX History: {fx_count}")
    print()
    print("JSON files preserved as backup (not deleted).")
    print("Database: bitumen_dashboard.db")
    print("=" * 60)

    # Verify
    print()
    print("Verifying...")
    from database import get_dashboard_stats
    stats = get_dashboard_stats()
    print(f"  DB Suppliers: {stats.get('total_suppliers', 0)}")
    print(f"  DB Customers: {stats.get('total_customers', 0)}")
    print(f"  DB Deals: {stats.get('total_deals', 0)}")
    print("  Migration complete!")


if __name__ == "__main__":
    migrate()
