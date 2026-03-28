"""
PPS Anantam — Drip Campaign Engine
=====================================
5-touch email drip campaign for customer nurturing.
Sequence: Day 0 → Day 3 → Day 7 → Day 14 → Day 30
"""
import os
import json
import datetime
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")

DRIP_SEQUENCE = [
    {"step": 1, "day": 0, "type": "intro", "subject": "Welcome to PPS Anantams — India's Bitumen Experts"},
    {"step": 2, "day": 3, "type": "rate_card", "subject": "Today's Bitumen Rates — Best Prices Guaranteed"},
    {"step": 3, "day": 7, "type": "case_study", "subject": "How We Saved ₹800/MT for a Gujarat Contractor"},
    {"step": 4, "day": 14, "type": "special_offer", "subject": "Exclusive Offer — Limited Time Rates for You"},
    {"step": 5, "day": 30, "type": "checkin", "subject": "Still Looking for Bitumen? We're Here to Help"},
]


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_table():
    """Create drip_campaigns table if not exists."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drip_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_city TEXT,
                customer_grade TEXT DEFAULT 'VG30',
                current_step INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                started_at TEXT,
                next_send_at TEXT,
                last_sent_at TEXT,
                completed_at TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def start_campaign(customer_name, customer_email, city="", grade="VG30"):
    """Start a new drip campaign for a customer."""
    _ensure_table()
    now = _now()
    conn = _get_conn()
    try:
        # Check if already active
        existing = conn.execute(
            "SELECT id FROM drip_campaigns WHERE customer_email = ? AND status = 'active'",
            (customer_email,)
        ).fetchone()
        if existing:
            return {"status": "exists", "message": f"Campaign already active for {customer_email}"}

        conn.execute("""
            INSERT INTO drip_campaigns (customer_name, customer_email, customer_city, customer_grade,
                                        current_step, status, started_at, next_send_at, created_at)
            VALUES (?, ?, ?, ?, 1, 'active', ?, ?, ?)
        """, (customer_name, customer_email, city, grade, now, now, now))
        conn.commit()
        return {"status": "started", "message": f"Drip campaign started for {customer_name}"}
    finally:
        conn.close()


def get_active_campaigns():
    """Get all active drip campaigns."""
    _ensure_table()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM drip_campaigns WHERE status = 'active' ORDER BY next_send_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_campaigns(limit=50):
    """Get all campaigns with status."""
    _ensure_table()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM drip_campaigns ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _generate_email_body(step_type, customer_name, city="", grade="VG30"):
    """Generate email body based on step type."""
    greeting = f"Dear {customer_name},"

    if step_type == "intro":
        return f"""{greeting}

Thank you for your interest in PPS Anantams Corporation — India's trusted bitumen trading partner since 2002.

We supply all grades of bitumen (VG30, VG10, VG40, CRMB, PMB) across India through:
• PSU Refineries (IOCL, HPCL, BPCL)
• Import Terminals (8 major ports)
• Decanter Plants

For the best rates to {city or 'your location'}, simply reply to this email or call us.

Best regards,
Prince P Shah
PPS Anantams Corporation Pvt Ltd
+91 7795242424 | Vadodara, Gujarat"""

    elif step_type == "rate_card":
        return f"""{greeting}

Here are today's indicative bitumen rates:

Grade: {grade}
• Bulk (Ex-Terminal): Rates vary by source location
• Drum (Delivered): Includes transport + packing

All rates: Ex-Terminal/Warehouse | GST 18% Extra | 100% Advance | 24hr Validity

For your exact landed cost to {city or 'your city'}, share:
1. Delivery location
2. Quantity (MT)
3. Bulk or Drum

We'll send a detailed quote within 30 minutes.

Best regards,
Prince P Shah | +91 7795242424"""

    elif step_type == "case_study":
        return f"""{greeting}

Here's how we helped a contractor save significantly on their bitumen costs:

Challenge: A road contractor in Gujarat needed 500 MT VG30 for an NHAI project but was paying premium rates from a single PSU source.

Solution: We compared prices across 3 refineries, 2 import terminals, and 1 decanter plant to find the best landed cost.

Result: Saved ₹800/MT — total savings of ₹4,00,000 on a single order.

We can do the same for your {city or ''} requirement. Our AI-powered pricing engine compares all available sources in real-time.

Interested? Reply or call +91 7795242424.

Best regards,
Prince P Shah"""

    elif step_type == "special_offer":
        return f"""{greeting}

We have a limited-time offer for you:

Special rates available on {grade} grade bitumen for {city or 'select locations'}.
• Competitive pricing below current market rates
• Immediate dispatch available
• All documentation (GST invoice, E-way bill, weighment slip)

This offer is valid for 48 hours. Don't miss out!

To avail: Reply with your quantity or call +91 7795242424.

Best regards,
Prince P Shah | PPS Anantams"""

    elif step_type == "checkin":
        return f"""{greeting}

It's been a while since we connected. We wanted to check in and see if you have any upcoming bitumen requirements.

What's new at PPS Anantams:
• Real-time AI pricing — get the best rates instantly
• New import terminal partnerships — more source options
• Faster delivery network — 3-5 day delivery across India

Whenever you need bitumen, we're just a call away.

Best regards,
Prince P Shah
+91 7795242424 | princepshah@gmail.com"""

    return f"{greeting}\n\nThank you for your interest. Contact us at +91 7795242424.\n\nBest regards,\nPrince P Shah"


def process_due_campaigns():
    """Process all campaigns that are due for sending. Call this periodically."""
    _ensure_table()
    now = datetime.datetime.now()
    conn = _get_conn()
    processed = 0

    try:
        campaigns = conn.execute(
            "SELECT * FROM drip_campaigns WHERE status = 'active' AND next_send_at <= ?",
            (now.strftime("%Y-%m-%d %H:%M:%S"),)
        ).fetchall()

        for camp in campaigns:
            camp = dict(camp)
            step = camp["current_step"]

            # Find current step config
            step_config = None
            for s in DRIP_SEQUENCE:
                if s["step"] == step:
                    step_config = s
                    break

            if not step_config:
                # All steps done
                conn.execute("UPDATE drip_campaigns SET status = 'completed', completed_at = ? WHERE id = ?",
                             (_now(), camp["id"]))
                conn.commit()
                continue

            # Generate and queue email
            body = _generate_email_body(
                step_config["type"],
                camp["customer_name"],
                camp.get("customer_city", ""),
                camp.get("customer_grade", "VG30"),
            )

            try:
                conn.execute("""
                    INSERT INTO email_queue (recipient_email, recipient_name, subject, body,
                                            email_type, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'queued', ?)
                """, (
                    camp["customer_email"],
                    camp["customer_name"],
                    step_config["subject"],
                    body,
                    f"drip_{step_config['type']}",
                    _now(),
                ))
            except Exception:
                pass

            # Move to next step
            next_step = step + 1
            if next_step > len(DRIP_SEQUENCE):
                conn.execute("UPDATE drip_campaigns SET status = 'completed', completed_at = ?, last_sent_at = ? WHERE id = ?",
                             (_now(), _now(), camp["id"]))
            else:
                next_config = DRIP_SEQUENCE[next_step - 1]
                next_send = (now + datetime.timedelta(days=next_config["day"] - step_config["day"])).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("""
                    UPDATE drip_campaigns SET current_step = ?, next_send_at = ?, last_sent_at = ? WHERE id = ?
                """, (next_step, next_send, _now(), camp["id"]))

            conn.commit()
            processed += 1

    finally:
        conn.close()

    return {"processed": processed}


def stop_campaign(campaign_id):
    """Stop an active campaign."""
    _ensure_table()
    conn = _get_conn()
    try:
        conn.execute("UPDATE drip_campaigns SET status = 'stopped' WHERE id = ?", (campaign_id,))
        conn.commit()
    finally:
        conn.close()
