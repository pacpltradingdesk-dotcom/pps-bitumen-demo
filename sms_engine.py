"""
SMS Engine — Fast2SMS Integration for Transactional & Promotional SMS
======================================================================
Queue-based SMS sending via Fast2SMS API (free tier: 100 SMS/day).
Follows the same pattern as email_engine.py and whatsapp_engine.py.

PPS Anantam Capital Pvt Ltd — Communication v1.0
"""

from __future__ import annotations

import datetime
import json
import logging
import re
import threading
import time
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger("sms_engine")

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None


def _slog(action: str, details: str = "", level: str = "info"):
    """Structured log to both stdlib logger and dashboard_log."""
    getattr(logger, level)(f"{action}: {details}" if details else action)
    if _dlog:
        getattr(_dlog, level)("sms_engine", action, details)


try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

FAST2SMS_API_URL = "https://www.fast2sms.com/dev/bulkV2"


# ==============================================================================
# SMS VALIDATION
# ==============================================================================

_INDIAN_MOBILE = re.compile(r"^(\+?91)?[6-9]\d{9}$")


def validate_mobile(number: str) -> tuple:
    """Validate and normalize Indian mobile number. Returns (valid, normalized)."""
    if not number:
        return False, ""
    cleaned = re.sub(r"[\s\-\(\)]+", "", str(number))
    if not _INDIAN_MOBILE.match(cleaned):
        return False, ""
    # Extract last 10 digits
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) >= 10:
        return True, digits[-10:]
    return False, ""


# ==============================================================================
# SMS ENGINE
# ==============================================================================

class SMSEngine:
    """Queue-based SMS engine using Fast2SMS API."""

    def __init__(self):
        self._settings = self._load_settings()
        self._lock = threading.Lock()
        self._send_count = 0
        self._send_count_reset = datetime.datetime.now(IST)

    def _load_settings(self) -> dict:
        try:
            from settings_engine import load_settings
            return load_settings()
        except Exception:
            return {}

    @property
    def api_key(self) -> str:
        return self._settings.get("fast2sms_api_key", "")

    @property
    def enabled(self) -> bool:
        return bool(self._settings.get("sms_enabled", False) and self.api_key)

    @property
    def daily_limit(self) -> int:
        return self._settings.get("sms_daily_limit", 100)

    # ── Direct Send ──────────────────────────────────────────────────────────

    def send_sms(self, to_number: str, message: str,
                 sms_type: str = "transactional") -> dict:
        """
        Send a single SMS via Fast2SMS API.

        Args:
            to_number: Indian mobile number
            message: SMS body (max 160 chars for single, 480 for multi-part)
            sms_type: 'transactional' or 'promotional'

        Returns: {success, message_id, error}
        """
        if not self.enabled:
            return {"success": False, "error": "SMS not enabled or API key missing"}

        valid, normalized = validate_mobile(to_number)
        if not valid:
            return {"success": False, "error": f"Invalid number: {to_number}"}

        # Rate limit check
        if not self._check_rate_limit():
            return {"success": False, "error": "Daily SMS limit reached"}

        try:
            result = self._call_fast2sms(normalized, message, sms_type)
            if result.get("success"):
                with self._lock:
                    self._send_count += 1
            return result
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return {"success": False, "error": str(e)}

    def _call_fast2sms(self, number: str, message: str,
                       sms_type: str) -> dict:
        """Call Fast2SMS bulk V2 API."""
        # Route: 'q' = transactional (DLT), 'v3' = promotional
        route = "q" if sms_type == "transactional" else "v3"

        params = {
            "route": route,
            "message": message[:480],
            "language": "english",
            "flash": 0,
            "numbers": number,
        }

        data = json.dumps(params).encode("utf-8")
        headers = {
            "authorization": self.api_key,
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            FAST2SMS_API_URL,
            data=data,
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        if result.get("return"):
            return {
                "success": True,
                "message_id": result.get("request_id", ""),
                "provider": "fast2sms",
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Unknown Fast2SMS error"),
            }

    def _check_rate_limit(self) -> bool:
        now = datetime.datetime.now(IST)
        with self._lock:
            # Reset daily counter at midnight
            if now.date() != self._send_count_reset.date():
                self._send_count = 0
                self._send_count_reset = now
            return self._send_count < self.daily_limit

    # ── Queue Management ─────────────────────────────────────────────────────

    def queue_sms(self, to_number: str, message: str,
                  sms_type: str = "transactional",
                  scheduled_time: str = None) -> int:
        """Insert SMS into queue. Returns queue_id or -1 on error."""
        valid, normalized = validate_mobile(to_number)
        if not valid:
            return -1

        try:
            from database import _get_conn
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO sms_queue (to_number, message, sms_type, status,
                   scheduled_time, created_at)
                   VALUES (?, ?, ?, 'pending', ?, datetime('now'))""",
                (normalized, message[:480], sms_type, scheduled_time)
            )
            conn.commit()
            queue_id = cur.lastrowid
            conn.close()
            return queue_id
        except Exception as e:
            logger.error(f"SMS queue insert error: {e}")
            return -1

    def process_queue(self) -> dict:
        """Process pending SMS from queue. Returns {sent, failed, skipped}."""
        if not self.enabled:
            return {"sent": 0, "failed": 0, "skipped": 0, "reason": "disabled"}

        results = {"sent": 0, "failed": 0, "skipped": 0}
        now = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

        try:
            from database import _get_conn
            conn = _get_conn()
            rows = conn.execute(
                """SELECT * FROM sms_queue
                   WHERE status = 'pending'
                   AND (scheduled_time IS NULL OR scheduled_time <= ?)
                   ORDER BY created_at ASC LIMIT 50""",
                (now,)
            ).fetchall()

            if not rows:
                conn.close()
                return results

            cols = [d[0] for d in conn.execute(
                "SELECT * FROM sms_queue LIMIT 0").description]

            for row_tuple in rows:
                row = dict(zip(cols, row_tuple))
                sms_id = row["id"]

                # Rate limit check
                if not self._check_rate_limit():
                    results["skipped"] += 1
                    continue

                result = self.send_sms(
                    row["to_number"], row["message"], row.get("sms_type", "transactional")
                )

                if result.get("success"):
                    conn.execute(
                        "UPDATE sms_queue SET status = 'sent', sent_at = ? WHERE id = ?",
                        (now, sms_id)
                    )
                    results["sent"] += 1
                else:
                    retry_count = row.get("retry_count", 0) + 1
                    new_status = "failed" if retry_count >= 3 else "pending"
                    conn.execute(
                        "UPDATE sms_queue SET status = ?, error_message = ?, "
                        "retry_count = ? WHERE id = ?",
                        (new_status, result.get("error", "")[:200], retry_count, sms_id)
                    )
                    results["failed"] += 1

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"SMS queue processing error: {e}")

        return results

    # ── Stats ────────────────────────────────────────────────────────────────

    def get_sms_stats(self) -> dict:
        """Get SMS queue statistics."""
        stats = {
            "enabled": self.enabled,
            "daily_limit": self.daily_limit,
            "sent_today": 0,
            "pending": 0,
            "failed": 0,
        }

        try:
            from database import _get_conn
            conn = _get_conn()
            today = datetime.datetime.now(IST).strftime("%Y-%m-%d")

            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM sms_queue WHERE status = 'sent' "
                "AND sent_at LIKE ?", (f"{today}%",)
            ).fetchone()
            stats["sent_today"] = row["cnt"] if row else 0

            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM sms_queue WHERE status = 'pending'"
            ).fetchone()
            stats["pending"] = row["cnt"] if row else 0

            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM sms_queue WHERE status = 'failed'"
            ).fetchone()
            stats["failed"] = row["cnt"] if row else 0

            conn.close()
        except Exception:
            pass

        return stats


    # ── SMS Template Generator ─────────────────────────────────────────────────

    def generate_sms_text(self, template: str, name: str = "",
                          grade: str = "", price: float = 0,
                          city: str = "", **kwargs) -> str:
        """
        Generate SMS text from predefined templates.

        Templates: price_update, offer, dispatch, festival, payment_reminder
        Returns SMS text (max 160 chars for single SMS).
        """
        display = name or "Sir"

        if template == "price_update":
            old_price = kwargs.get("old_price", 0)
            direction = "UP" if price > old_price else "DOWN"
            return (
                f"PACPL: {grade} price {direction} to Rs{price:.0f}/MT"
                f"{f' ({city})' if city else ''}. "
                f"Call 7795242424 for best rate. -PPS Anantam"
            )[:160]

        elif template == "offer":
            return (
                f"PACPL: Dear {display}, {grade} available at Rs{price:.0f}/MT"
                f"{f' landed {city}' if city else ''}. "
                f"Valid 24hrs. 100% Advance. "
                f"Reply YES or call 7795242424. -PPS Anantam"
            )[:160]

        elif template == "dispatch":
            qty = kwargs.get("qty", 0)
            vehicle = kwargs.get("vehicle_no", "")
            return (
                f"PACPL: Dear {display}, {qty:.0f}MT {grade} dispatched"
                f"{f' via {vehicle}' if vehicle else ''}. "
                f"ETA {city} 24-48hrs. -PPS Anantam"
            )[:160]

        elif template == "festival":
            festival = kwargs.get("festival", "")
            return (
                f"PACPL: Dear {display}, Happy {festival}! "
                f"Wishing you prosperity & growth. "
                f"For bitumen needs call 7795242424. -PPS Anantam"
            )[:160]

        elif template == "payment_reminder":
            amount = kwargs.get("amount", 0)
            return (
                f"PACPL: Dear {display}, payment of Rs{amount:.0f} pending. "
                f"Pls remit to ICICI A/C 184105001402 IFSC ICIC0001841. "
                f"-PPS Anantam"
            )[:160]

        return f"PACPL: Dear {display}, contact 7795242424 for bitumen enquiry. -PPS Anantam"


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


def send_sms(to_number: str, message: str,
             sms_type: str = "transactional") -> dict:
    """Quick send SMS without creating engine instance."""
    engine = SMSEngine()
    return engine.send_sms(to_number, message, sms_type)


def queue_sms(to_number: str, message: str,
              sms_type: str = "transactional",
              scheduled_time: str = None) -> int:
    """Quick queue SMS."""
    engine = SMSEngine()
    return engine.queue_sms(to_number, message, sms_type, scheduled_time)


def get_sms_stats() -> dict:
    """Quick stats."""
    engine = SMSEngine()
    return engine.get_sms_stats()
