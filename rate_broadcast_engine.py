"""
PPS Anantam — Rate Broadcast Engine
=======================================
Personalized rate broadcasting via WhatsApp + Email.
Triggers: Auto 9 AM daily, IOCL/HPCL revision, Manual.
Segments by: City, Grade, VIP Tier.
"""
import os
import json
import sqlite3
import datetime
import uuid
import threading
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VIP_STAGGER_MINUTES = {"platinum": 0, "gold": 1, "silver": 2, "standard": 3}


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
            CREATE TABLE IF NOT EXISTS broadcast_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id TEXT UNIQUE,
                trigger_type TEXT,
                segment_filter TEXT,
                total_recipients INTEGER DEFAULT 0,
                wa_sent INTEGER DEFAULT 0,
                wa_delivered INTEGER DEFAULT 0,
                wa_failed INTEGER DEFAULT 0,
                email_sent INTEGER DEFAULT 0,
                email_delivered INTEGER DEFAULT 0,
                email_failed INTEGER DEFAULT 0,
                message_template TEXT,
                created_at TEXT,
                completed_at TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_broadcast_contacts(city_filter=None, grade_filter=None, vip_filter=None):
    """Load contacts from all sources, apply filters, return sorted by VIP tier."""
    contacts = []

    # Source 1: tbl_contacts.json
    try:
        with open(os.path.join(BASE_DIR, "tbl_contacts.json"), "r", encoding="utf-8") as f:
            json_contacts = json.load(f)
        for c in json_contacts:
            contacts.append({
                "name": c.get("name", ""),
                "phone": c.get("contact", ""),
                "email": "",
                "city": c.get("city", ""),
                "state": c.get("state", ""),
                "category": c.get("category", ""),
                "grade": "VG30",
                "vip_tier": "standard",
                "wa_opted_in": True,
            })
    except Exception:
        pass

    # Source 2: SQLite customers table
    try:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM customers").fetchall()
        conn.close()
        for r in rows:
            r = dict(r)
            contacts.append({
                "name": r.get("name", r.get("company_name", "")),
                "phone": r.get("mobile1", r.get("mobile2", "")),
                "email": r.get("email", ""),
                "city": r.get("city", ""),
                "state": r.get("state", ""),
                "category": r.get("category", ""),
                "grade": r.get("preferred_grade", "VG30") or "VG30",
                "vip_tier": (r.get("vip_tier", "standard") or "standard").lower(),
                "wa_opted_in": bool(r.get("whatsapp_opted_in", 1)),
            })
    except Exception:
        pass

    # Source 3: SQLite contacts table
    try:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM contacts").fetchall()
        conn.close()
        for r in rows:
            r = dict(r)
            contacts.append({
                "name": r.get("name", r.get("company_name", "")),
                "phone": r.get("mobile1", r.get("phone", "")),
                "email": r.get("email", ""),
                "city": r.get("city", ""),
                "state": r.get("state", ""),
                "category": r.get("category", ""),
                "grade": "VG30",
                "vip_tier": "standard",
                "wa_opted_in": True,
            })
    except Exception:
        pass

    # Deduplicate by phone
    seen_phones = set()
    unique = []
    for c in contacts:
        phone = (c.get("phone") or "").strip().replace(" ", "")
        if phone and phone not in seen_phones:
            seen_phones.add(phone)
            unique.append(c)
        elif not phone and c.get("email"):
            unique.append(c)

    # Apply filters
    filtered = unique
    if city_filter and "All" not in city_filter:
        filtered = [c for c in filtered if c.get("city") in city_filter]
    if grade_filter and "All" not in grade_filter:
        filtered = [c for c in filtered if c.get("grade") in grade_filter]
    if vip_filter and "All" not in vip_filter:
        filtered = [c for c in filtered if c.get("vip_tier") in [v.lower() for v in vip_filter]]

    # Sort by VIP tier priority
    tier_order = {"platinum": 0, "gold": 1, "silver": 2, "standard": 3}
    filtered.sort(key=lambda c: tier_order.get(c.get("vip_tier", "standard"), 3))

    return filtered


def calculate_personalized_rate(city, grade="VG30", load_type="Bulk"):
    """Get landed cost for a specific city and grade."""
    try:
        from calculation_engine import get_engine
        sources = get_engine().find_best_sources(city, grade=grade, load_type=load_type, top_n=1)
        if sources:
            return {
                "landed_cost": sources[0].get("landed_cost", 0),
                "source": sources[0].get("source", ""),
                "base_price": sources[0].get("base_price", 0),
            }
    except Exception:
        pass

    # Fallback: use live_prices.json
    try:
        with open(os.path.join(BASE_DIR, "live_prices.json"), "r") as f:
            lp = json.load(f)
        key = f"DRUM_KANDLA_{grade}" if grade else "DRUM_KANDLA_VG30"
        drum_price = lp.get(key, lp.get("DRUM_KANDLA_VG30", 35500))
        bulk_price = drum_price - 2000
        return {"landed_cost": bulk_price if load_type == "Bulk" else drum_price, "source": "Market Rate", "base_price": bulk_price}
    except Exception:
        return {"landed_cost": 35000, "source": "Default", "base_price": 33000}


def generate_wa_message(customer, rates, trigger_type="manual"):
    """Generate personalized WhatsApp message."""
    name = customer.get("name", "Sir/Madam")
    city = customer.get("city", "your city")
    grade = customer.get("grade", "VG30")
    today = datetime.date.today().strftime("%d %b %Y")

    bulk = rates.get("bulk", {}).get("landed_cost", 0)
    drum = rates.get("drum", {}).get("landed_cost", 0)

    header = "⚡ PRICE REVISION ALERT" if trigger_type == "price_revision" else "🔵 PPS Anantams — Rate Update"

    msg = f"""{header}
━━━━━━━━━━━━━━━━━━━
📅 {today}

Dear {name},

Your rates for {city}:
{grade} Bulk: ₹{bulk:,.0f}/MT
{grade} Drum: ₹{drum:,.0f}/MT"""

    if trigger_type == "price_revision":
        msg += "\n\n⚡ Prices revised — Act now!"

    msg += f"""
━━━━━━━━━━━━━━━━━━━
100% Advance | 24hr Validity
Ex-Terminal | GST 18% Extra

📞 +91 7795242424
PPS Anantams Corporation Pvt Ltd"""

    return msg


def generate_email_html(customer, rates, trigger_type="manual"):
    """Generate personalized HTML email."""
    name = customer.get("name", "Sir/Madam")
    city = customer.get("city", "your city")
    grade = customer.get("grade", "VG30")
    today = datetime.date.today().strftime("%d %b %Y")

    bulk = rates.get("bulk", {}).get("landed_cost", 0)
    drum = rates.get("drum", {}).get("landed_cost", 0)
    source = rates.get("bulk", {}).get("source", "")

    alert_banner = '<div style="background:#DC2626;color:#fff;padding:8px;text-align:center;font-weight:700;border-radius:8px 8px 0 0;">⚡ PRICE REVISION ALERT</div>' if trigger_type == "price_revision" else ""

    html = f"""<div style="font-family:Inter,-apple-system,sans-serif;max-width:600px;margin:0 auto;">
{alert_banner}
<div style="background:#1E1B4B;color:#fff;padding:24px;text-align:center;{'border-radius:8px 8px 0 0;' if trigger_type != 'price_revision' else ''}">
<h2 style="margin:0;font-size:1.3rem;">PPS Anantams Corporation</h2>
<p style="color:#C7D2FE;margin:4px 0 0;">Daily Rate Update — {today}</p>
</div>
<div style="background:#fff;padding:24px;border:1px solid #E2E8F0;">
<p>Dear <strong>{name}</strong>,</p>
<p>Here are today's bitumen rates for <strong>{city}</strong>:</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
<tr style="background:#F8FAFC;"><th style="padding:10px;text-align:left;border-bottom:2px solid #E2E8F0;">Grade</th><th style="padding:10px;text-align:right;border-bottom:2px solid #E2E8F0;">Rate (₹/MT)</th></tr>
<tr><td style="padding:10px;border-bottom:1px solid #F3F4F6;">{grade} Bulk</td><td style="padding:10px;text-align:right;font-weight:700;color:#059669;border-bottom:1px solid #F3F4F6;">₹{bulk:,.0f}</td></tr>
<tr><td style="padding:10px;border-bottom:1px solid #F3F4F6;">{grade} Drum</td><td style="padding:10px;text-align:right;font-weight:700;color:#059669;border-bottom:1px solid #F3F4F6;">₹{drum:,.0f}</td></tr>
</table>
<p style="font-size:0.85rem;color:#6B7280;">Source: {source} | Ex-Terminal/Warehouse | GST 18% Extra</p>
<div style="text-align:center;margin:20px 0;">
<a href="https://wa.me/917795242424?text=Hi%20PPS%2C%20I%20need%20{grade}%20quote%20for%20{city}" style="background:#4F46E5;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:700;">Request Quote</a>
</div>
</div>
<div style="background:#F8FAFC;padding:16px;text-align:center;font-size:0.75rem;color:#6B7280;border:1px solid #E2E8F0;border-top:none;border-radius:0 0 8px 8px;">
100% Advance | 24hr Validity | HSN 27132000<br>
PPS Anantams Corporation Pvt Ltd | +91 7795242424 | Vadodara, Gujarat
</div>
</div>"""
    return html


def execute_broadcast(city_filter=None, grade_filter=None, vip_filter=None, trigger_type="manual"):
    """Main broadcast function — segment → personalize → queue WA + Email."""
    ensure_table()
    broadcast_id = f"BC_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    contacts = get_broadcast_contacts(city_filter, grade_filter, vip_filter)
    if not contacts:
        return {"status": "no_contacts", "broadcast_id": broadcast_id, "total": 0}

    # Log broadcast start
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO broadcast_log (broadcast_id, trigger_type, segment_filter, total_recipients, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'sending')
        """, (broadcast_id, trigger_type,
              json.dumps({"city": city_filter, "grade": grade_filter, "vip": vip_filter}),
              len(contacts), _now()))
        conn.commit()
    finally:
        conn.close()

    wa_sent, wa_failed, email_sent, email_failed = 0, 0, 0, 0

    for customer in contacts:
        city = customer.get("city", "")
        grade = customer.get("grade", "VG30")

        # Calculate personalized rates
        bulk_rate = calculate_personalized_rate(city, grade, "Bulk")
        drum_rate = calculate_personalized_rate(city, grade, "Drum")
        rates = {"bulk": bulk_rate, "drum": drum_rate}

        # Send WhatsApp
        phone = (customer.get("phone") or "").strip().replace(" ", "")
        if phone and customer.get("wa_opted_in", True):
            try:
                msg = generate_wa_message(customer, rates, trigger_type)
                try:
                    from whatsapp_engine import queue_message
                    queue_message(phone, msg, customer.get("name", ""))
                except Exception:
                    pass
                wa_sent += 1
            except Exception:
                wa_failed += 1

        # Send Email
        email = (customer.get("email") or "").strip()
        if email and "@" in email:
            try:
                subject = f"PPS Anantams — {grade} Rates for {city} ({datetime.date.today().strftime('%d %b')})"
                html = generate_email_html(customer, rates, trigger_type)
                try:
                    from email_engine import queue_email
                    queue_email(email, customer.get("name", ""), subject, html, "rate_broadcast")
                except Exception:
                    pass
                email_sent += 1
            except Exception:
                email_failed += 1

    # Update broadcast log
    conn = _get_conn()
    try:
        conn.execute("""
            UPDATE broadcast_log SET wa_sent=?, wa_failed=?, email_sent=?, email_failed=?,
                                     completed_at=?, status='completed'
            WHERE broadcast_id=?
        """, (wa_sent, wa_failed, email_sent, email_failed, _now(), broadcast_id))
        conn.commit()
    finally:
        conn.close()

    return {
        "status": "completed",
        "broadcast_id": broadcast_id,
        "total": len(contacts),
        "wa_sent": wa_sent, "wa_failed": wa_failed,
        "email_sent": email_sent, "email_failed": email_failed,
    }


def on_price_revision(revision_data):
    """Triggered when competitor revises price. Auto-broadcasts to affected region."""
    region = revision_data.get("region", "")
    competitor = revision_data.get("competitor", "")
    grade = revision_data.get("grade", "VG30")

    # Map region to cities (approximate)
    region_cities = {
        "North": ["Delhi", "Lucknow", "Jaipur", "Chandigarh", "Bhopal"],
        "West": ["Mumbai", "Ahmedabad", "Pune", "Vadodara", "Surat", "Nashik"],
        "South": ["Chennai", "Bangalore", "Hyderabad", "Kochi", "Coimbatore"],
        "East": ["Kolkata", "Patna", "Bhubaneswar", "Guwahati", "Ranchi"],
    }
    cities = region_cities.get(region, None)

    result = execute_broadcast(
        city_filter=cities,
        grade_filter=[grade] if grade else None,
        trigger_type="price_revision",
    )
    return result


def get_broadcast_history(limit=30):
    """Get recent broadcast history."""
    ensure_table()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM broadcast_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_broadcast_stats(broadcast_id):
    """Get stats for a specific broadcast."""
    ensure_table()
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM broadcast_log WHERE broadcast_id = ?", (broadcast_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── Background Scheduler ──────────────────────────────────────────────────

_scheduler_running = False


def _morning_broadcast_loop():
    """Background thread: check every 60 seconds if it's 9:00 AM, then broadcast."""
    global _scheduler_running
    last_sent_date = None

    while _scheduler_running:
        now = datetime.datetime.now()
        today = now.date()

        # Check if it's 9:00 AM and haven't sent today
        if now.hour == 9 and now.minute < 2 and last_sent_date != today:
            try:
                from settings_engine import get as gs
                if gs("rate_broadcast_auto_morning", True):
                    execute_broadcast(trigger_type="scheduled")
                    last_sent_date = today
            except Exception:
                execute_broadcast(trigger_type="scheduled")
                last_sent_date = today

        time.sleep(60)


def start_scheduler():
    """Start the morning broadcast scheduler."""
    global _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True
    t = threading.Thread(target=_morning_broadcast_loop, daemon=True, name="rate_broadcast_scheduler")
    t.start()


def stop_scheduler():
    """Stop the scheduler."""
    global _scheduler_running
    _scheduler_running = False
