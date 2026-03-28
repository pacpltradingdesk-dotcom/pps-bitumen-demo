"""
PPS Anantam — Share Automation Engine v1.0
=============================================
Scheduled sharing of dashboard pages/sections via Email/WhatsApp.
Runs in background thread (follows email_engine scheduler pattern).

Supports daily, weekly, and monthly schedules with configurable
time, recipients, content type, and delivery channel.
"""

import os
import sys
import json
import time
import uuid
import threading
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(__file__))

IST = timezone(timedelta(hours=5, minutes=30))


class ShareAutomationEngine:
    """Manage scheduled share sends."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()

    def create_schedule(self, name: str, page_name: str, channel: str,
                        recipients: list, frequency: str,
                        time_ist: str = "09:00",
                        content_type: str = "pdf",
                        day_of_week: str = None,
                        day_of_month: int = None) -> int:
        """Create a new scheduled share. Returns schedule ID."""
        from database import insert_share_schedule
        data = {
            "schedule_name": name,
            "page_name": page_name,
            "content_type": content_type,
            "channel": channel,
            "recipients_json": json.dumps(recipients),
            "frequency": frequency,
            "day_of_week": day_of_week,
            "day_of_month": day_of_month,
            "time_ist": time_ist,
            "is_active": 1,
            "next_run": self._compute_next_run(frequency, time_ist, day_of_week, day_of_month),
            "run_count": 0,
            "created_by": "admin",
        }
        return insert_share_schedule(data)

    def update_schedule(self, schedule_id: int, data: dict):
        """Update an existing schedule."""
        from database import update_share_schedule
        update_share_schedule(schedule_id, data)

    def delete_schedule(self, schedule_id: int):
        """Deactivate a schedule."""
        from database import delete_share_schedule
        delete_share_schedule(schedule_id)

    def get_schedules(self, active_only: bool = True) -> list:
        """Get all schedules."""
        from database import get_share_schedules
        schedules = get_share_schedules(active_only)
        for s in schedules:
            if s.get("recipients_json"):
                try:
                    s["recipients"] = json.loads(s["recipients_json"])
                except Exception:
                    s["recipients"] = []
        return schedules

    def run_due_schedules(self) -> dict:
        """Check and execute any schedules that are due.
        Returns {"executed": N, "failed": N, "skipped": N}."""
        schedules = self.get_schedules(active_only=True)
        now = datetime.now(IST)
        now_str = now.strftime("%Y-%m-%d %H:%M")
        executed = 0
        failed = 0
        skipped = 0

        for s in schedules:
            next_run = s.get("next_run", "")
            if not next_run or next_run > now_str:
                skipped += 1
                continue

            ok = self._execute_schedule(s)
            sid = s["id"]

            # Update schedule
            new_next = self._compute_next_run(
                s["frequency"], s["time_ist"],
                s.get("day_of_week"), s.get("day_of_month"),
            )
            from database import update_share_schedule
            update_share_schedule(sid, {
                "last_run": now.strftime("%Y-%m-%d %H:%M:%S"),
                "next_run": new_next,
                "run_count": s.get("run_count", 0) + 1,
            })

            if ok:
                executed += 1
            else:
                failed += 1

        return {"executed": executed, "failed": failed, "skipped": skipped}

    def _execute_schedule(self, schedule: dict) -> bool:
        """Execute a single scheduled share. Returns True on success."""
        try:
            channel = schedule.get("channel", "email")
            content_type = schedule.get("content_type", "pdf")
            page_name = schedule.get("page_name", "Dashboard")
            recipients = schedule.get("recipients", [])
            schedule_name = schedule.get("schedule_name", "")

            if not recipients:
                return False

            # Build content based on type
            content = self._build_content(page_name, content_type)
            if not content:
                return False

            # Send via appropriate channel
            if channel in ("email", "both"):
                self._send_email(recipients, page_name, content, schedule_name)
            if channel in ("whatsapp", "both"):
                self._send_whatsapp(recipients, page_name, content, schedule_name)

            # Track
            self._track_send(schedule, len(recipients))
            return True
        except Exception:
            return False

    def _build_content(self, page_name: str, content_type: str) -> dict:
        """Build content for scheduled share."""
        try:
            from universal_action_engine import build_generic_context
            ctx = build_generic_context(page_name)
            if content_type == "pdf":
                from universal_action_engine import build_pdf_report
                pdf_bytes = build_pdf_report(ctx)
                return {"type": "pdf", "data": pdf_bytes, "context": ctx}
            else:
                from universal_action_engine import build_whatsapp_summary
                summary = build_whatsapp_summary(ctx)
                return {"type": "summary", "data": summary, "context": ctx}
        except Exception:
            return {"type": "summary", "data": f"Scheduled report: {page_name}", "context": None}

    def _send_email(self, recipients: list, page_name: str, content: dict, schedule_name: str):
        """Send email to recipients."""
        try:
            from ai_message_engine import AIMessageEngine
            ai = AIMessageEngine()
            for r in recipients:
                email = r.get("email", "")
                if not email:
                    continue
                msg = ai.generate_share_message(
                    "email",
                    {"section_title": page_name, "page_name": page_name},
                    recipient_name=r.get("name", ""),
                )
                from database import _insert_row, _now_ist
                _insert_row("email_queue", {
                    "to_email": email,
                    "subject": msg.get("subject", f"PPS Anantam — {page_name}"),
                    "body_html": msg.get("body", ""),
                    "body_text": msg.get("body", ""),
                    "email_type": "scheduled_share",
                    "status": "queued",
                    "created_at": _now_ist(),
                })
        except Exception:
            pass

    def _send_whatsapp(self, recipients: list, page_name: str, content: dict, schedule_name: str):
        """Send WhatsApp to recipients."""
        try:
            summary = content.get("data", "") if content.get("type") == "summary" else f"📊 Scheduled Report: {page_name}"
            from database import _insert_row, _now_ist
            for r in recipients:
                phone = r.get("whatsapp", "")
                if not phone:
                    continue
                _insert_row("whatsapp_queue", {
                    "to_number": phone,
                    "message_type": "session",
                    "session_text": summary[:4096],
                    "status": "queued",
                    "created_at": _now_ist(),
                })
        except Exception:
            pass

    def _track_send(self, schedule: dict, recipient_count: int):
        """Log scheduled send in comm_tracking."""
        try:
            from database import insert_comm_tracking
            insert_comm_tracking({
                "tracking_id": f"sched_{uuid.uuid4().hex[:8]}",
                "channel": schedule.get("channel", "email"),
                "action": "sent",
                "sender": "ShareAutomation",
                "recipient_name": f"{recipient_count} recipients",
                "page_name": schedule.get("page_name", ""),
                "content_type": schedule.get("content_type", "pdf"),
                "content_summary": f"Scheduled: {schedule.get('schedule_name', '')}",
                "delivery_status": "sent",
            })
        except Exception:
            pass

    def _compute_next_run(self, frequency: str, time_ist: str,
                          day_of_week: str = None, day_of_month: int = None) -> str:
        """Compute the next run datetime string."""
        now = datetime.now(IST)
        hour, minute = 9, 0
        if time_ist and ":" in time_ist:
            parts = time_ist.split(":")
            hour = int(parts[0])
            minute = int(parts[1])

        if frequency == "daily":
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
        elif frequency == "weekly":
            days_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                        "friday": 4, "saturday": 5, "sunday": 6}
            target_day = days_map.get((day_of_week or "monday").lower(), 0)
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        elif frequency == "monthly":
            dom = day_of_month or 1
            try:
                target = now.replace(day=dom, hour=hour, minute=minute, second=0, microsecond=0)
                if target <= now:
                    if now.month == 12:
                        target = target.replace(year=now.year + 1, month=1)
                    else:
                        target = target.replace(month=now.month + 1)
            except ValueError:
                target = now + timedelta(days=30)
        else:
            target = now + timedelta(days=1)

        return target.strftime("%Y-%m-%d %H:%M")


# ── Background Scheduler ─────────────────────────────────────────────────────

_share_scheduler_thread = None
_share_scheduler_running = False


def start_share_scheduler():
    """Start background scheduler for automated shares."""
    global _share_scheduler_thread, _share_scheduler_running
    if _share_scheduler_running:
        return

    def _loop():
        global _share_scheduler_running
        _share_scheduler_running = True
        while _share_scheduler_running:
            try:
                engine = ShareAutomationEngine()
                engine.run_due_schedules()
            except Exception:
                pass
            time.sleep(120)  # Check every 2 minutes

    _share_scheduler_thread = threading.Thread(target=_loop, daemon=True, name="ShareScheduler")
    _share_scheduler_thread.start()


def stop_share_scheduler():
    global _share_scheduler_running
    _share_scheduler_running = False
