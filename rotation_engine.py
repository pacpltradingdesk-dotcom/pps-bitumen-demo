"""
Rotation Engine — Daily Outreach + Festival Broadcasts
=======================================================
Manages automated daily contact rotation (2,400/day from 24K pool)
and festival broadcast campaigns for all opted-in contacts.

Classes:
  - ContactRotationEngine: Daily batch selection, priority scoring, execution
  - FestivalBroadcastEngine: Festival detection, message prep, staggered sends

PPS Anantam Capital Pvt Ltd — CRM Automation v1.0
"""

from __future__ import annotations

import datetime
import json
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger("rotation_engine")

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None


def _slog(action: str, details: str = "", level: str = "info"):
    """Structured log to both stdlib logger and dashboard_log."""
    getattr(logger, level)(f"{action}: {details}" if details else action)
    if _dlog:
        getattr(_dlog, level)("rotation_engine", action, details)


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT ROTATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════


class ContactRotationEngine:
    """
    Selects and executes daily outreach batches from the contacts pool.

    Algorithm:
      1. Retry failed contacts from previous days
      2. Contacts not reached in 7+ days, sorted by rotation_priority DESC
      3. Fill remaining from oldest last_contact_date
    """

    def __init__(self):
        self._settings = self._load_settings()

    def _load_settings(self) -> dict:
        try:
            from settings_engine import load_settings
            return load_settings()
        except Exception:
            return {}

    @property
    def daily_count(self) -> int:
        return self._settings.get("daily_rotation_count", 2400)

    @property
    def min_gap_days(self) -> int:
        return self._settings.get("rotation_min_gap_days", 7)

    @property
    def channels(self) -> list:
        return self._settings.get("rotation_channels", ["whatsapp", "email"])

    def select_daily_batch(self, date: Optional[str] = None) -> list[dict]:
        """
        Pick up to daily_count contacts for today's outreach.

        Returns list of contact dicts with assigned channel.
        """
        try:
            from database import get_contacts_for_rotation
        except ImportError:
            logger.error("database module not available")
            return []

        if date is None:
            date = datetime.date.today().strftime("%Y-%m-%d")

        # Get priority-sorted batch from DB
        batch = get_contacts_for_rotation(
            limit=self.daily_count,
            min_gap_days=self.min_gap_days,
        )

        # Assign channels
        result = []
        for contact in batch:
            assigned = self._assign_channel(contact)
            contact["assigned_channel"] = assigned
            result.append(contact)

        return result

    def _assign_channel(self, contact: dict) -> str:
        """Assign best communication channel for this contact."""
        wa_opted = contact.get("whatsapp_opted_in", 0)
        mobile = (contact.get("mobile1") or "").strip()
        email = (contact.get("email") or "").strip()
        email_opted = contact.get("email_opted_in", 1)

        if "whatsapp" in self.channels and wa_opted and mobile:
            return "whatsapp"
        elif "email" in self.channels and email_opted and email:
            return "email"
        elif mobile:
            return "call"
        return "skip"

    def compute_rotation_priority(self, contact: dict) -> float:
        """
        Compute rotation priority score for a contact.

        Factors:
          - lifetime_value_inr (higher = more priority)
          - relationship_score (higher = more priority)
          - days_since_contact (more days = higher urgency)
          - buyer_seller_tag (buyers get slight boost)
        """
        ltv = float(contact.get("lifetime_value_inr", 0) or 0)
        rel_score = float(contact.get("relationship_score", 0) or 0)
        tag = contact.get("buyer_seller_tag", "unknown")

        # Days since last contact
        last_date = contact.get("last_contact_date", "")
        days_gap = 999
        if last_date:
            try:
                last_dt = datetime.datetime.strptime(last_date, "%Y-%m-%d").date()
                days_gap = (datetime.date.today() - last_dt).days
            except Exception:
                pass

        # Weighted score
        priority = 0.0
        priority += min(ltv / 100000, 10.0) * 0.25      # LTV component (max 2.5)
        priority += min(rel_score / 10, 10.0) * 0.20     # Relationship (max 2.0)
        priority += min(days_gap / 30, 10.0) * 0.35      # Urgency (max 3.5)
        priority += (1.5 if tag == "buyer" else
                     1.0 if tag == "both" else
                     0.5 if tag == "seller" else 0.0) * 0.20  # Tag (max 0.3)

        return round(priority, 3)

    def execute_rotation(self, batch: list[dict], date: Optional[str] = None) -> dict:
        """
        Execute the daily rotation: queue messages via email/whatsapp engines.

        Returns: {total, sent, failed, skipped, channels: {whatsapp: N, email: N, call: N}}
        """
        if date is None:
            date = datetime.date.today().strftime("%Y-%m-%d")

        stats = {"total": len(batch), "sent": 0, "failed": 0, "skipped": 0,
                 "channels": {"whatsapp": 0, "email": 0, "call": 0}}

        for contact in batch:
            channel = contact.get("assigned_channel", "skip")

            if channel == "skip":
                stats["skipped"] += 1
                continue

            try:
                success = self._send_outreach(contact, channel, date)
                if success:
                    stats["sent"] += 1
                    stats["channels"][channel] = stats["channels"].get(channel, 0) + 1
                    self._log_rotation(contact, date, channel, "sent")
                    self._update_last_contacted(contact, date, channel)
                else:
                    stats["failed"] += 1
                    self._log_rotation(contact, date, channel, "failed")
            except Exception as e:
                stats["failed"] += 1
                self._log_rotation(contact, date, channel, "error", str(e))
                logger.error(f"Rotation send error for {contact.get('name')}: {e}")

        return stats

    def _send_outreach(self, contact: dict, channel: str, date: str) -> bool:
        """Send a single outreach message via the appropriate engine."""
        name = contact.get("name", "")
        company = contact.get("company_name", "")
        city = contact.get("city", "")
        category = contact.get("category", "")

        # Detect segment from contact category
        segment = ""
        try:
            from business_context import get_segment_for_category
            from settings_engine import load_settings
            if load_settings().get("segment_aware_templates", True) and category:
                segment = get_segment_for_category(category)
        except ImportError:
            pass

        if channel == "whatsapp":
            try:
                from whatsapp_engine import queue_message
                mobile = contact.get("mobile1", "")
                if not mobile:
                    return False
                msg = self._build_outreach_message(name, company, "whatsapp",
                                                    segment=segment, city=city)
                queue_message(to=mobile, template="daily_outreach_v1",
                              body=msg, contact_name=name)
                return True
            except Exception as e:
                logger.error(f"WhatsApp send failed: {e}")
                return False

        elif channel == "email":
            try:
                from email_engine import queue_email
                email = contact.get("email", "")
                if not email:
                    return False
                subject = f"Bitumen Market Update - {company or name}"
                body = self._build_outreach_message(name, company, "email",
                                                     segment=segment, city=city)
                queue_email(to=email, subject=subject, body=body,
                            email_type="outreach")
                return True
            except Exception as e:
                logger.error(f"Email send failed: {e}")
                return False

        return False

    def _build_outreach_message(self, name: str, company: str,
                                 channel: str, segment: str = "",
                                 city: str = "") -> str:
        """Build personalized outreach message (segment-aware)."""
        try:
            from communication_engine import generate_outreach_message
            return generate_outreach_message(name, company, channel,
                                              segment=segment, city=city)
        except Exception:
            pass

        # Fallback simple message
        greeting = f"Dear {name}," if name else "Dear Sir/Madam,"
        return (
            f"{greeting}\n\n"
            f"Greetings from PPS Anantam / PACPL!\n\n"
            f"We would like to share the latest bitumen market update with you. "
            f"Please feel free to reach out for competitive pricing on all grades "
            f"(VG30, VG10, VG40, CRMB, PMB).\n\n"
            f"Payment: 100% Advance | Dispatch within 48 hours\n\n"
            f"Best regards,\nPPS Anantam Corporation Pvt Ltd\n"
            f"Contact: +91 7795242424"
        )

    def _log_rotation(self, contact: dict, date: str, channel: str,
                      status: str, error: str = "") -> None:
        try:
            from database import insert_rotation_log
            insert_rotation_log(
                contact_id=contact.get("id", 0),
                rotation_date=date,
                channel=channel,
                status=status,
                message_type="daily_outreach",
                error_message=error,
            )
        except Exception:
            pass

    def _update_last_contacted(self, contact: dict, date: str,
                                channel: str) -> None:
        try:
            from database import update_contact_last_contacted
            update_contact_last_contacted(
                contact_id=contact.get("id", 0),
                date=date,
                channel=channel,
            )
        except Exception:
            pass

    def get_rotation_progress(self, date: Optional[str] = None) -> dict:
        """Get progress stats for a given rotation date."""
        if date is None:
            date = datetime.date.today().strftime("%Y-%m-%d")
        try:
            from database import get_rotation_stats
            return get_rotation_stats(date)
        except Exception:
            return {"date": date, "total": 0, "sent": 0,
                    "failed": 0, "pending": 0}

    def retry_failed(self, date: Optional[str] = None) -> dict:
        """Re-queue failed contacts from a specific date."""
        if date is None:
            date = datetime.date.today().strftime("%Y-%m-%d")

        max_retries = self._settings.get("rotation_retry_max_attempts", 3)

        try:
            from database import _get_conn
            conn = _get_conn()
            failed = conn.execute(
                """SELECT DISTINCT contact_id FROM contact_rotation_log
                   WHERE rotation_date = ? AND status IN ('failed', 'error')
                   GROUP BY contact_id
                   HAVING COUNT(*) < ?""",
                (date, max_retries)
            ).fetchall()

            if not failed:
                return {"retried": 0, "message": "No failed contacts to retry"}

            from database import get_all_contacts
            all_contacts = {c["id"]: c for c in get_all_contacts()
                           if isinstance(c.get("id"), int)}

            retry_batch = []
            for row in failed:
                cid = row[0]
                if cid in all_contacts:
                    c = all_contacts[cid]
                    c["assigned_channel"] = self._assign_channel(c)
                    retry_batch.append(c)

            if retry_batch:
                result = self.execute_rotation(retry_batch, date)
                return {"retried": len(retry_batch), "result": result}
            return {"retried": 0, "message": "No contacts found for retry"}
        except Exception as e:
            return {"retried": 0, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# FESTIVAL BROADCAST ENGINE
# ══════════════════════════════════════════════════════════════════════════════


class FestivalBroadcastEngine:
    """
    Detects upcoming festivals from sales_calendar.py and executes
    staggered broadcast campaigns to all opted-in contacts.
    """

    def __init__(self):
        self._settings = self._load_settings()

    def _load_settings(self) -> dict:
        try:
            from settings_engine import load_settings
            return load_settings()
        except Exception:
            return {}

    def get_upcoming_festivals(self, days_ahead: int = 7) -> list[dict]:
        """Get festivals coming up within days_ahead days."""
        try:
            from sales_calendar import get_festivals, get_upcoming_festivals
        except ImportError:
            return []

        try:
            # Try the specific function first
            upcoming = get_upcoming_festivals(days=days_ahead)
            if upcoming:
                return upcoming
        except Exception:
            pass

        try:
            all_festivals = get_festivals()
            today = datetime.date.today()
            upcoming = []
            for f in all_festivals:
                fdate = None
                date_str = f.get("date", "")
                for fmt in ("%Y-%m-%d", "%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        fdate = datetime.datetime.strptime(date_str, fmt).date()
                        break
                    except Exception:
                        continue
                if fdate and 0 <= (fdate - today).days <= days_ahead:
                    f["parsed_date"] = fdate.isoformat()
                    upcoming.append(f)
            return upcoming
        except Exception:
            return []

    def prepare_festival_messages(self, festival_name: str,
                                  festival_date: str) -> dict:
        """
        Prepare personalized festival messages for all opted-in contacts.

        Returns: {broadcast_id, festival, total_contacts, messages: [...]}
        """
        try:
            from database import get_contacts_for_broadcast
        except ImportError:
            return {"error": "database module not available"}

        contacts = get_contacts_for_broadcast()
        broadcast_id = f"fest_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        messages = []
        for contact in contacts:
            name = contact.get("name", "")
            lang = contact.get("preferred_language", "en")
            channel = self._pick_broadcast_channel(contact)

            msg_text = self._build_festival_message(
                name, festival_name, festival_date, lang, channel
            )

            messages.append({
                "contact_id": contact.get("id"),
                "name": name,
                "channel": channel,
                "to": (contact.get("mobile1", "") if channel == "whatsapp"
                       else contact.get("email", "")),
                "message": msg_text,
                "language": lang,
            })

        # Log broadcast
        try:
            from database import insert_festival_broadcast
            insert_festival_broadcast(
                festival_name=festival_name,
                festival_date=festival_date,
                total_contacts=len(messages),
            )
        except Exception:
            pass

        return {
            "broadcast_id": broadcast_id,
            "festival": festival_name,
            "date": festival_date,
            "total_contacts": len(messages),
            "messages": messages,
        }

    def execute_festival_broadcast(self, prepared: dict) -> dict:
        """
        Execute a prepared festival broadcast with staggered sending.

        Returns: {sent_whatsapp, sent_email, failed, total}
        """
        messages = prepared.get("messages", [])
        batch_size = self._settings.get("whatsapp_stagger_batch_size", 1000)
        stagger_delay = self._settings.get("whatsapp_stagger_delay_minutes", 60)

        stats = {"sent_whatsapp": 0, "sent_email": 0, "failed": 0,
                 "total": len(messages)}

        for i, msg in enumerate(messages):
            # Stagger: pause after each batch_size messages
            if i > 0 and i % batch_size == 0:
                logger.info(f"Stagger pause at message {i}/{len(messages)}")
                time.sleep(min(stagger_delay * 60, 300))  # Cap at 5 min in code

            channel = msg.get("channel", "skip")
            to = msg.get("to", "")
            text = msg.get("message", "")

            if not to:
                stats["failed"] += 1
                continue

            try:
                if channel == "whatsapp":
                    from whatsapp_engine import queue_message
                    queue_message(to=to, template="festival_greeting_v1",
                                  body=text, contact_name=msg.get("name", ""))
                    stats["sent_whatsapp"] += 1
                elif channel == "email":
                    from email_engine import queue_email
                    queue_email(to=to,
                                subject=f"Happy {prepared.get('festival', 'Festival')}!",
                                body=text, email_type="festival")
                    stats["sent_email"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"Festival broadcast send error: {e}")

        # Update broadcast record
        try:
            from database import update_festival_broadcast, get_festival_broadcasts
            broadcasts = get_festival_broadcasts()
            if broadcasts:
                latest = broadcasts[-1]
                update_festival_broadcast(
                    broadcast_id=latest.get("id", 0),
                    status="completed",
                    sent_whatsapp=stats["sent_whatsapp"],
                    sent_email=stats["sent_email"],
                    failed=stats["failed"],
                )
        except Exception:
            pass

        return stats

    def _pick_broadcast_channel(self, contact: dict) -> str:
        """Pick the best channel for broadcasting to this contact."""
        channels = self._settings.get("festival_broadcast_channels",
                                       ["whatsapp", "email"])
        wa_opted = contact.get("whatsapp_opted_in", 0)
        mobile = (contact.get("mobile1") or "").strip()
        email = (contact.get("email") or "").strip()
        email_opted = contact.get("email_opted_in", 1)

        if "whatsapp" in channels and wa_opted and mobile:
            return "whatsapp"
        elif "email" in channels and email_opted and email:
            return "email"
        return "skip"

    def _build_festival_message(self, name: str, festival: str,
                                 date: str, language: str,
                                 channel: str) -> str:
        """Build personalized festival greeting message."""
        try:
            from communication_engine import generate_festival_greeting
            return generate_festival_greeting(name, festival, language, channel)
        except Exception:
            pass

        # Fallback
        greeting = f"Dear {name}," if name else "Dear Valued Partner,"
        if language == "hi":
            return (
                f"{greeting}\n\n"
                f"{festival} ki hardik shubhkamnayein!\n\n"
                f"PPS Anantam Capital Pvt Ltd ki or se aapko aur aapke "
                f"parivaar ko {festival} ki dheron shubhkamnayein.\n\n"
                f"Sadar,\nPPS Anantam Capital Pvt Ltd"
            )
        return (
            f"{greeting}\n\n"
            f"Wishing you and your family a very Happy {festival}!\n\n"
            f"May this festive season bring prosperity and joy to your "
            f"business and family.\n\n"
            f"Warm regards,\nPPS Anantam Capital Pvt Ltd"
        )

    def get_broadcast_status(self, broadcast_id: Optional[int] = None) -> dict:
        """Get status of a festival broadcast."""
        try:
            from database import get_festival_broadcasts
            broadcasts = get_festival_broadcasts()
            if broadcast_id:
                for b in broadcasts:
                    if b.get("id") == broadcast_id:
                        return b
            elif broadcasts:
                return broadcasts[-1]
        except Exception:
            pass
        return {"status": "unknown"}


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND SCHEDULER
# ══════════════════════════════════════════════════════════════════════════════

_scheduler_running = False
_scheduler_thread: Optional[threading.Thread] = None


def start_rotation_scheduler():
    """Start the background rotation scheduler daemon thread."""
    global _scheduler_running, _scheduler_thread
    if _scheduler_running:
        return

    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True,
                                          name="rotation_scheduler")
    _scheduler_thread.start()
    logger.info("Rotation scheduler started")


def stop_rotation_scheduler():
    """Stop the background scheduler."""
    global _scheduler_running
    _scheduler_running = False
    logger.info("Rotation scheduler stopped")


def _scheduler_loop():
    """Main scheduler loop — checks every 60 seconds for triggers."""
    global _scheduler_running
    last_rotation_date = None
    last_festival_check = None

    while _scheduler_running:
        try:
            from settings_engine import load_settings
            settings = load_settings()
        except Exception:
            time.sleep(60)
            continue

        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")

        # ── Daily rotation trigger ──
        if settings.get("daily_rotation_enabled", False):
            rotation_time = settings.get("daily_rotation_time", "09:00")
            try:
                target_h, target_m = map(int, rotation_time.split(":"))
            except Exception:
                target_h, target_m = 9, 0

            if (now.hour == target_h and now.minute >= target_m
                    and last_rotation_date != today):
                try:
                    engine = ContactRotationEngine()
                    batch = engine.select_daily_batch(today)
                    if batch:
                        result = engine.execute_rotation(batch, today)
                        logger.info(f"Daily rotation completed: {result}")
                    last_rotation_date = today
                except Exception as e:
                    logger.error(f"Daily rotation error: {e}")

        # ── Festival broadcast trigger ──
        if settings.get("festival_broadcast_enabled", False):
            days_ahead = settings.get("festival_broadcast_days_ahead", 1)
            check_hour = 6  # Check at 6 AM

            if (now.hour == check_hour
                    and last_festival_check != today):
                try:
                    engine = FestivalBroadcastEngine()
                    upcoming = engine.get_upcoming_festivals(days_ahead=days_ahead)
                    for fest in upcoming:
                        fname = fest.get("name", fest.get("festival", ""))
                        fdate = fest.get("parsed_date", fest.get("date", ""))
                        if fname:
                            prepared = engine.prepare_festival_messages(fname, fdate)
                            if prepared.get("messages"):
                                result = engine.execute_festival_broadcast(prepared)
                                logger.info(f"Festival broadcast '{fname}': {result}")
                    last_festival_check = today
                except Exception as e:
                    logger.error(f"Festival broadcast error: {e}")

        # Retry failed
        if settings.get("rotation_retry_failed", True) and last_rotation_date == today:
            try:
                engine = ContactRotationEngine()
                retry_result = engine.retry_failed(today)
                if retry_result.get("retried", 0) > 0:
                    logger.info(f"Retry result: {retry_result}")
            except Exception:
                pass

        time.sleep(60)


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════


def get_rotation_status() -> dict:
    """Get current rotation engine status."""
    engine = ContactRotationEngine()
    today = datetime.date.today().strftime("%Y-%m-%d")
    progress = engine.get_rotation_progress(today)

    try:
        from database import get_contacts_count
        counts = get_contacts_count()
    except Exception:
        counts = {}

    return {
        "scheduler_running": _scheduler_running,
        "today": today,
        "progress": progress,
        "daily_target": engine.daily_count,
        "total_contacts": counts.get("total", 0),
        "active_contacts": counts.get("active", 0),
        "settings": {
            "rotation_enabled": engine._settings.get("daily_rotation_enabled", False),
            "festival_enabled": engine._settings.get("festival_broadcast_enabled", False),
            "channels": engine.channels,
        }
    }


def trigger_manual_rotation() -> dict:
    """Manually trigger a rotation cycle (for UI button)."""
    engine = ContactRotationEngine()
    today = datetime.date.today().strftime("%Y-%m-%d")
    batch = engine.select_daily_batch(today)
    if not batch:
        return {"status": "no_contacts", "message": "No contacts available for rotation"}
    result = engine.execute_rotation(batch, today)
    return {"status": "completed", "result": result}


def trigger_manual_festival_broadcast(festival_name: str,
                                       festival_date: str) -> dict:
    """Manually trigger a festival broadcast (for UI button)."""
    engine = FestivalBroadcastEngine()
    prepared = engine.prepare_festival_messages(festival_name, festival_date)
    if not prepared.get("messages"):
        return {"status": "no_contacts", "message": "No opted-in contacts found"}
    result = engine.execute_festival_broadcast(prepared)
    return {"status": "completed", "result": result}
