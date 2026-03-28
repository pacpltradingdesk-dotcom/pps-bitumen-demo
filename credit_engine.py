"""
PPS Anantam — Credit Limit & Aging Engine
============================================
Customer credit tracking, aging buckets, and overdue alerts.
"""
import os
import sqlite3
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_table():
    """Create credit_limits table if not exists."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS credit_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_id TEXT,
                credit_limit REAL DEFAULT 0,
                outstanding REAL DEFAULT 0,
                last_payment_date TEXT,
                last_payment_amount REAL DEFAULT 0,
                days_outstanding INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                risk_level TEXT DEFAULT 'low',
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_all_credits():
    """Get all customer credit records."""
    ensure_table()
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM credit_limits ORDER BY outstanding DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_overdue_customers(days_threshold=60):
    """Get customers overdue beyond threshold."""
    ensure_table()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM credit_limits WHERE days_outstanding > ? AND outstanding > 0 ORDER BY days_outstanding DESC",
            (days_threshold,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def set_credit_limit(customer_name, credit_limit, customer_id=None):
    """Set or update credit limit for a customer."""
    ensure_table()
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT id FROM credit_limits WHERE customer_name = ?", (customer_name,)).fetchone()
        if existing:
            conn.execute("UPDATE credit_limits SET credit_limit = ?, updated_at = ? WHERE customer_name = ?",
                         (credit_limit, _now(), customer_name))
        else:
            conn.execute("""
                INSERT INTO credit_limits (customer_name, customer_id, credit_limit, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (customer_name, customer_id, credit_limit, _now(), _now()))
        conn.commit()
    finally:
        conn.close()


def record_payment(customer_name, amount):
    """Record a payment and reduce outstanding."""
    ensure_table()
    conn = _get_conn()
    try:
        conn.execute("""
            UPDATE credit_limits SET
                outstanding = MAX(0, outstanding - ?),
                last_payment_date = ?,
                last_payment_amount = ?,
                updated_at = ?
            WHERE customer_name = ?
        """, (amount, _now(), amount, _now(), customer_name))
        conn.commit()
    finally:
        conn.close()


def add_outstanding(customer_name, amount):
    """Add to outstanding balance."""
    ensure_table()
    conn = _get_conn()
    try:
        conn.execute("""
            UPDATE credit_limits SET outstanding = outstanding + ?, updated_at = ? WHERE customer_name = ?
        """, (amount, _now(), customer_name))
        conn.commit()
    finally:
        conn.close()


def get_aging_summary():
    """Get aging bucket summary."""
    ensure_table()
    records = get_all_credits()
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    bucket_amounts = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}

    for r in records:
        days = r.get("days_outstanding", 0)
        amt = r.get("outstanding", 0)
        if days <= 30:
            buckets["0-30"] += 1; bucket_amounts["0-30"] += amt
        elif days <= 60:
            buckets["31-60"] += 1; bucket_amounts["31-60"] += amt
        elif days <= 90:
            buckets["61-90"] += 1; bucket_amounts["61-90"] += amt
        else:
            buckets["90+"] += 1; bucket_amounts["90+"] += amt

    return {"counts": buckets, "amounts": bucket_amounts}


def get_mock_credits():
    """Generate mock credit data for demo."""
    import random
    customers = ["Ashoka Buildcon", "L&T Roads", "NCC Ltd", "Dilip Buildcon", "Gayatri Projects",
                 "PNC Infratech", "Sadbhav Engineering", "IRB Infra", "KNR Constructions", "HG Infra"]
    records = []
    for i, cust in enumerate(customers):
        limit = random.choice([500000, 1000000, 2000000, 5000000])
        outstanding = random.randint(0, int(limit * 1.2))
        days = random.randint(0, 120)
        risk = "critical" if days > 90 else "high" if days > 60 else "medium" if days > 30 else "low"
        records.append({
            "id": i + 1, "customer_name": cust, "credit_limit": limit,
            "outstanding": outstanding, "days_outstanding": days,
            "last_payment_date": (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d"),
            "last_payment_amount": random.randint(50000, 500000),
            "risk_level": risk, "status": "active",
        })
    return records
