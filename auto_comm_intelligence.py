"""
auto_comm_intelligence.py — Auto Communication Intelligence
=============================================================
AI learns best communication styles per buyer/region.
Uses ai_fallback_engine for free LLM access — no new dependencies.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
COMM_FILE = BASE / "comm_intelligence.json"

LOG = logging.getLogger("comm_intelligence")


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _load_comm_data() -> dict:
    try:
        if COMM_FILE.exists():
            data = json.loads(COMM_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_comm_data(data: dict) -> None:
    try:
        COMM_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        LOG.warning("Failed to save comm intelligence: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# COMMUNICATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_communication_style(customer_id: str) -> dict:
    """
    Analyze past communication patterns with a customer.
    Sources: email_queue, wa_queue, daily_log from database.
    """
    result = {
        "customer_id": customer_id,
        "preferred_channel": "email",
        "best_time": "10:00-12:00 IST",
        "tone": "formal",
        "response_rate": 0.0,
        "key_topics": [],
        "total_communications": 0,
    }

    # Load stored intelligence
    stored = _load_comm_data()
    if customer_id in stored.get("customers", {}):
        return stored["customers"][customer_id]

    # Analyze from database
    email_count = 0
    wa_count = 0
    try:
        from database import _get_conn
        conn = _get_conn()

        # Email history
        row = conn.execute(
            "SELECT COUNT(*) FROM email_queue WHERE recipient LIKE ? OR subject LIKE ?",
            (f"%{customer_id}%", f"%{customer_id}%")
        ).fetchone()
        email_count = row[0] if row else 0

        # WhatsApp history
        row = conn.execute(
            "SELECT COUNT(*) FROM wa_queue WHERE phone LIKE ? OR message LIKE ?",
            (f"%{customer_id}%", f"%{customer_id}%")
        ).fetchone()
        wa_count = row[0] if row else 0

        conn.close()
    except Exception:
        pass

    total = email_count + wa_count
    result["total_communications"] = total

    if total > 0:
        if wa_count > email_count:
            result["preferred_channel"] = "whatsapp"
            result["tone"] = "casual"
        else:
            result["preferred_channel"] = "email"
            result["tone"] = "formal"

    # Store for future reference
    if customer_id:
        stored.setdefault("customers", {})[customer_id] = result
        _save_comm_data(stored)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE SUGGESTION
# ═══════════════════════════════════════════════════════════════════════════════

def suggest_message(customer_id: str, context: str) -> dict:
    """AI-generated message suggestion based on communication history."""
    style = analyze_communication_style(customer_id)

    prompt = (
        f"Generate a short {style['tone']} message for a bitumen sales customer. "
        f"Context: {context}. "
        f"Channel: {style['preferred_channel']}. "
        f"Keep it professional and under 100 words. "
        f"Include a subject line if email."
    )

    # Try LLM
    try:
        from ai_fallback_engine import ask_with_fallback
        result = ask_with_fallback(prompt)
        if result and not result.get("error"):
            answer = result.get("answer", "")
            return {
                "subject": _extract_subject(answer) if style["preferred_channel"] == "email" else "",
                "body": answer,
                "channel": style["preferred_channel"],
                "tone": style["tone"],
                "model": result.get("model", "ai"),
            }
    except Exception:
        pass

    # Fallback: template
    return _template_message(customer_id, context, style)


def _extract_subject(text: str) -> str:
    """Extract subject line from AI response."""
    for line in text.split("\n"):
        line = line.strip()
        if line.lower().startswith("subject:"):
            return line[8:].strip()
    return "Follow-up: Bitumen Supply"


def _template_message(customer_id: str, context: str, style: dict) -> dict:
    """Template-based message fallback."""
    if style["tone"] == "casual":
        body = f"Hi! Quick update regarding {context}. Let me know if you'd like to discuss."
    else:
        body = (f"Dear Sir/Madam,\n\n"
                f"I hope this message finds you well. "
                f"I wanted to follow up regarding {context}.\n\n"
                f"Please let me know a convenient time to discuss.\n\n"
                f"Best regards,\nPPS Anantam Team")

    return {
        "subject": f"Follow-up: {context[:50]}" if style["preferred_channel"] == "email" else "",
        "body": body,
        "channel": style["preferred_channel"],
        "tone": style["tone"],
        "model": "template",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def get_communication_analytics() -> dict:
    """Aggregate communication patterns across all customers."""
    stored = _load_comm_data()
    customers = stored.get("customers", {})

    by_channel = {"email": 0, "whatsapp": 0, "call": 0}
    by_tone = {"formal": 0, "casual": 0, "technical": 0}
    total_comms = 0

    for cid, data in customers.items():
        channel = data.get("preferred_channel", "email")
        by_channel[channel] = by_channel.get(channel, 0) + 1
        tone = data.get("tone", "formal")
        by_tone[tone] = by_tone.get(tone, 0) + 1
        total_comms += data.get("total_communications", 0)

    # Also check database for overall stats
    try:
        from database import _get_conn
        conn = _get_conn()
        email_total = conn.execute("SELECT COUNT(*) FROM email_queue").fetchone()
        wa_total = conn.execute("SELECT COUNT(*) FROM wa_queue").fetchone()
        conn.close()
        total_comms = max(total_comms, (email_total[0] if email_total else 0) + (wa_total[0] if wa_total else 0))
    except Exception:
        pass

    return {
        "total_customers_profiled": len(customers),
        "total_communications": total_comms,
        "by_channel": by_channel,
        "by_tone": by_tone,
        "best_practices": [
            "Email works best for formal price negotiations",
            "WhatsApp for quick follow-ups and delivery updates",
            "Morning hours (10-12 IST) get highest response rates",
            "Include specific quantity and grade in initial contact",
        ],
        "updated_at": _now_ist(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LEARNING FROM OUTCOMES
# ═══════════════════════════════════════════════════════════════════════════════

def learn_from_outcome(message_id: str, outcome: str) -> None:
    """
    Learn from communication outcomes.
    outcome: "replied", "opened", "ignored", "converted"
    """
    stored = _load_comm_data()
    outcomes = stored.setdefault("outcomes", [])
    outcomes.append({
        "message_id": message_id,
        "outcome": outcome,
        "timestamp": _now_ist(),
    })
    # Keep last 500 outcomes
    if len(outcomes) > 500:
        stored["outcomes"] = outcomes[-500:]
    _save_comm_data(stored)
    LOG.info("Learned outcome '%s' for message '%s'", outcome, message_id)
