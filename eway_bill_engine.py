"""
PPS Anantam — E-Way Bill Engine
==================================
Generate, track, and manage e-way bills for bitumen shipments.
"""
import os
import sqlite3
import datetime
import random

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_table():
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS eway_bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_no TEXT UNIQUE,
                so_id TEXT,
                from_gstin TEXT,
                to_gstin TEXT,
                from_city TEXT,
                to_city TEXT,
                vehicle_no TEXT,
                hsn_code TEXT DEFAULT '27132000',
                value REAL,
                distance_km INTEGER,
                valid_from TEXT,
                valid_until TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def generate_bill_no():
    """Generate unique e-way bill number."""
    return f"EWB{datetime.datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"


def create_eway_bill(data):
    """Create a new e-way bill."""
    ensure_table()
    bill_no = data.get("bill_no") or generate_bill_no()
    valid_from = data.get("valid_from") or _now()
    distance = data.get("distance_km", 500)
    # Validity: 1 day per 200km (GST rule)
    days = max(1, (distance // 200) + 1)
    valid_until = data.get("valid_until") or (
        datetime.datetime.now() + datetime.timedelta(days=days)
    ).strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO eway_bills (bill_no, so_id, from_gstin, to_gstin, from_city, to_city,
                                    vehicle_no, hsn_code, value, distance_km, valid_from, valid_until, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (bill_no, data.get("so_id"), data.get("from_gstin", "24AAHCV1611L2ZD"),
              data.get("to_gstin", ""), data.get("from_city", "Vadodara"),
              data.get("to_city", ""), data.get("vehicle_no", ""),
              data.get("hsn_code", "27132000"), data.get("value", 0),
              distance, valid_from, valid_until, _now()))
        conn.commit()
        return {"status": "created", "bill_no": bill_no, "valid_until": valid_until}
    finally:
        conn.close()


def get_all_bills(status=None):
    ensure_table()
    conn = _get_conn()
    try:
        if status:
            rows = conn.execute("SELECT * FROM eway_bills WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM eway_bills ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_expiring_bills(hours=12):
    """Get bills expiring within N hours."""
    ensure_table()
    threshold = (datetime.datetime.now() + datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT * FROM eway_bills WHERE status = 'active' AND valid_until <= ? AND valid_until > ?
        """, (threshold, _now())).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def expire_bills():
    """Mark expired bills."""
    ensure_table()
    conn = _get_conn()
    try:
        conn.execute("UPDATE eway_bills SET status = 'expired' WHERE status = 'active' AND valid_until < ?", (_now(),))
        conn.commit()
    finally:
        conn.close()


def get_mock_bills():
    """Generate mock e-way bill data."""
    cities = ["Ahmedabad", "Mumbai", "Pune", "Delhi", "Chennai", "Vadodara", "Surat", "Jaipur"]
    vehicles = ["GJ05AB1234", "MH12CD5678", "RJ14EF9012", "DL01GH3456", "TN09IJ7890"]
    bills = []
    for i in range(15):
        now = datetime.datetime.now()
        created = now - datetime.timedelta(days=random.randint(0, 30))
        valid_days = random.randint(1, 5)
        valid_until = created + datetime.timedelta(days=valid_days)
        status = "expired" if valid_until < now else "active"
        bills.append({
            "id": i + 1, "bill_no": f"EWB{created.strftime('%Y%m%d')}{random.randint(1000, 9999)}",
            "from_city": random.choice(["Vadodara", "Kandla", "Mumbai"]),
            "to_city": random.choice(cities), "vehicle_no": random.choice(vehicles),
            "hsn_code": "27132000", "value": random.randint(500000, 5000000),
            "distance_km": random.randint(100, 1500),
            "valid_from": created.strftime("%Y-%m-%d"), "valid_until": valid_until.strftime("%Y-%m-%d %H:%M"),
            "status": status, "created_at": created.strftime("%Y-%m-%d %H:%M"),
            "from_gstin": "24AAHCV1611L2ZD", "to_gstin": f"27{''.join([str(random.randint(0,9)) for _ in range(10)])}",
        })
    return bills
