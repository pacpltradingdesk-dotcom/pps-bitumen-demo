"""
PPS Anantam — NHAI Tender Engine
====================================
Track and manage NHAI/MoRTH road project tenders for bitumen demand estimation.
"""
import os
import sqlite3
import datetime
import random

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")

BITUMEN_PER_KM_MT = 45  # Average bitumen consumption per km of highway


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
            CREATE TABLE IF NOT EXISTS tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT,
                title TEXT,
                authority TEXT DEFAULT 'NHAI',
                state TEXT,
                district TEXT,
                road_length_km REAL,
                estimated_bitumen_mt REAL,
                deadline TEXT,
                value_cr REAL,
                status TEXT DEFAULT 'open',
                source_url TEXT,
                notes TEXT,
                fetched_at TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def add_tender(data):
    ensure_table()
    length = data.get("road_length_km", 0)
    bitumen = data.get("estimated_bitumen_mt") or (length * BITUMEN_PER_KM_MT)
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO tenders (tender_id, title, authority, state, district, road_length_km,
                                 estimated_bitumen_mt, deadline, value_cr, status, source_url, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.get("tender_id", f"NHAI/{datetime.datetime.now().strftime('%Y')}/{random.randint(1000,9999)}"),
              data.get("title", ""), data.get("authority", "NHAI"),
              data.get("state", ""), data.get("district", ""),
              length, bitumen, data.get("deadline", ""),
              data.get("value_cr", 0), data.get("status", "open"),
              data.get("source_url", ""), data.get("notes", ""), _now()))
        conn.commit()
    finally:
        conn.close()


def get_tenders(status=None, state=None):
    ensure_table()
    conn = _get_conn()
    try:
        query = "SELECT * FROM tenders WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if state:
            query += " AND state = ?"
            params.append(state)
        query += " ORDER BY deadline ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_mock_tenders():
    """Generate realistic mock tender data."""
    states = ["Uttar Pradesh", "Rajasthan", "Maharashtra", "Madhya Pradesh", "Gujarat",
              "Karnataka", "Tamil Nadu", "Bihar", "Andhra Pradesh", "Telangana",
              "Haryana", "Punjab", "Odisha", "West Bengal", "Chhattisgarh"]
    authorities = ["NHAI", "MoRTH", "State PWD", "NHIDCL"]
    titles = [
        "4-lane Highway Construction", "6-lane Expressway Widening",
        "2-lane with paved shoulder", "Bridge + Approach Road",
        "Bypass Road Construction", "Ring Road Development",
        "Rural Road Upgradation (PMGSY)", "Urban Flyover + Connector",
    ]
    tenders = []
    for i in range(25):
        state = random.choice(states)
        length = random.randint(10, 200)
        deadline = (datetime.datetime.now() + datetime.timedelta(days=random.randint(-30, 90))).strftime("%Y-%m-%d")
        status = "closed" if random.random() < 0.3 else "open"
        tenders.append({
            "id": i + 1,
            "tender_id": f"NHAI/2026/{random.randint(1000, 9999)}",
            "title": f"{random.choice(titles)} — {state}",
            "authority": random.choice(authorities),
            "state": state,
            "district": f"District-{random.randint(1, 30)}",
            "road_length_km": length,
            "estimated_bitumen_mt": length * BITUMEN_PER_KM_MT,
            "deadline": deadline,
            "value_cr": round(random.uniform(50, 2000), 1),
            "status": status,
        })
    return tenders
