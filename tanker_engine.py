"""
PPS Anantam — Tanker Tracking Engine
=======================================
Track bulk tanker/truck positions, ETA, and delivery status.
"""
import os
import sqlite3
import datetime
import random
import math

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")
AVG_SPEED_KMPH = 40  # Average road speed for tankers


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
            CREATE TABLE IF NOT EXISTS tankers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_no TEXT,
                driver_name TEXT,
                driver_phone TEXT,
                source TEXT,
                destination TEXT,
                customer TEXT,
                grade TEXT DEFAULT 'VG30',
                qty_mt REAL,
                status TEXT DEFAULT 'loading',
                departed_at TEXT,
                eta TEXT,
                delivered_at TEXT,
                lat REAL,
                lng REAL,
                distance_km REAL,
                last_updated TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def calculate_eta(distance_km, departed_at=None):
    """Calculate ETA based on distance and average speed."""
    hours = distance_km / AVG_SPEED_KMPH
    departure = departed_at or datetime.datetime.now()
    if isinstance(departure, str):
        departure = datetime.datetime.strptime(departure, "%Y-%m-%d %H:%M:%S")
    return (departure + datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a)) * 1.3  # 1.3 road factor


def add_tanker(data):
    ensure_table()
    distance = data.get("distance_km", 500)
    eta = calculate_eta(distance) if data.get("status") == "in_transit" else ""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO tankers (vehicle_no, driver_name, driver_phone, source, destination,
                                 customer, grade, qty_mt, status, departed_at, eta, distance_km, last_updated, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data.get("vehicle_no"), data.get("driver_name"), data.get("driver_phone"),
              data.get("source"), data.get("destination"), data.get("customer"),
              data.get("grade", "VG30"), data.get("qty_mt", 20),
              data.get("status", "loading"), data.get("departed_at"), eta,
              distance, _now(), _now()))
        conn.commit()
    finally:
        conn.close()


def update_status(tanker_id, status, lat=None, lng=None):
    ensure_table()
    conn = _get_conn()
    try:
        if status == "delivered":
            conn.execute("UPDATE tankers SET status = ?, delivered_at = ?, last_updated = ? WHERE id = ?",
                         (status, _now(), _now(), tanker_id))
        elif lat and lng:
            conn.execute("UPDATE tankers SET status = ?, lat = ?, lng = ?, last_updated = ? WHERE id = ?",
                         (status, lat, lng, _now(), tanker_id))
        else:
            conn.execute("UPDATE tankers SET status = ?, last_updated = ? WHERE id = ?",
                         (status, _now(), tanker_id))
        conn.commit()
    finally:
        conn.close()


def get_all_tankers(status=None):
    ensure_table()
    conn = _get_conn()
    try:
        if status:
            rows = conn.execute("SELECT * FROM tankers WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tankers ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_delayed_tankers(hours_threshold=4):
    """Get tankers past their ETA by threshold hours."""
    ensure_table()
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM tankers WHERE status = 'in_transit' AND eta IS NOT NULL").fetchall()
        delayed = []
        now = datetime.datetime.now()
        for r in rows:
            try:
                eta = datetime.datetime.strptime(r["eta"], "%Y-%m-%d %H:%M")
                if now > eta + datetime.timedelta(hours=hours_threshold):
                    d = dict(r)
                    d["hours_delayed"] = round((now - eta).total_seconds() / 3600, 1)
                    delayed.append(d)
            except Exception:
                pass
        return delayed
    finally:
        conn.close()


def get_mock_tankers():
    """Generate mock tanker data."""
    sources = ["Kandla Terminal", "Mumbai Refinery", "IOCL Vadodara", "Mundra Import", "Vizag HPCL"]
    destinations = ["Ahmedabad", "Pune", "Delhi", "Jaipur", "Bhopal", "Lucknow", "Chennai", "Hyderabad"]
    customers = ["Ashoka Buildcon", "L&T Roads", "NCC Ltd", "Dilip Buildcon", "IRB Infra"]
    vehicles = ["GJ05AB1234", "MH12CD5678", "RJ14EF9012", "DL01GH3456", "TN09IJ7890",
                "GJ06KL2345", "MH04MN6789", "UP32OP0123", "KA01QR4567"]
    statuses = ["loading", "in_transit", "in_transit", "in_transit", "delivered", "delayed"]

    # Approximate city coordinates
    city_coords = {
        "Ahmedabad": (23.02, 72.57), "Pune": (18.52, 73.85), "Delhi": (28.61, 77.21),
        "Jaipur": (26.91, 75.79), "Bhopal": (23.26, 77.41), "Lucknow": (26.85, 80.95),
        "Chennai": (13.08, 80.27), "Hyderabad": (17.38, 78.49), "Mumbai": (19.08, 72.88),
        "Vadodara": (22.31, 73.19), "Kandla": (23.03, 70.22), "Mundra": (22.84, 69.72),
        "Vizag": (17.69, 83.22),
    }

    tankers = []
    for i in range(12):
        src = random.choice(sources)
        dest = random.choice(destinations)
        status = random.choice(statuses)
        departed = (datetime.datetime.now() - datetime.timedelta(hours=random.randint(2, 48))).strftime("%Y-%m-%d %H:%M:%S")
        distance = random.randint(200, 1500)
        eta = calculate_eta(distance, departed)

        # Get approximate coordinates
        dest_coords = city_coords.get(dest, (22.0, 73.0))
        if status in ["in_transit", "delayed"]:
            lat = dest_coords[0] + random.uniform(-2, 2)
            lng = dest_coords[1] + random.uniform(-2, 2)
        else:
            lat, lng = dest_coords

        tankers.append({
            "id": i + 1, "vehicle_no": random.choice(vehicles),
            "driver_name": f"Driver {i+1}", "driver_phone": f"+91 98765{random.randint(10000,99999)}",
            "source": src, "destination": dest, "customer": random.choice(customers),
            "grade": random.choice(["VG30", "VG10"]), "qty_mt": random.choice([20, 25, 30]),
            "status": status, "departed_at": departed, "eta": eta,
            "distance_km": distance, "lat": lat, "lng": lng, "last_updated": _now(),
        })
    return tankers
