try:
    from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    try:
        from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
    except:
        pass
"""
PPS Anantam — Auto WhatsApp Engine v1.0 (360dialog)
=====================================================
360dialog WhatsApp Business API integration for automated
template messages, session messages, and broadcasts.

Message Types:
  1. Template Messages (HSM) — Pre-approved, anytime
  2. Session Messages — Free-form within 24h window
  3. Broadcasts — Template to multiple recipients
"""

import json
import re
import threading
import time
import datetime
import base64
from pathlib import Path
from typing import Dict, List, Tuple

import pytz

try:
    import requests
except ImportError:
    requests = None

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None

DIALOG360_API_BASE = "https://waba.360dialog.io/v1"
INDIAN_MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")


# ─── Phone Number Validation ────────────────────────────────────────────────

def validate_indian_mobile(number: str) -> Tuple[bool, str]:
    """
    Validate and normalize Indian mobile number.
    Accepts: 9876543210, +919876543210, 919876543210, 09876543210
    Returns: (is_valid, normalized_number_with_91_prefix)
    """
    if not number:
        return False, ""
    cleaned = re.sub(r"[\s\-\(\)\+]", "", str(number))
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]
    if cleaned.startswith("91") and len(cleaned) == 12:
        core = cleaned[2:]
    elif len(cleaned) == 10:
        core = cleaned
    else:
        return False, ""

    if INDIAN_MOBILE_REGEX.match(core):
        return True, f"91{core}"
    return False, ""


def format_whatsapp_number(number: str) -> str:
    """Convert Indian mobile to WhatsApp format: 919876543210."""
    valid, normalized = validate_indian_mobile(number)
    return normalized if valid else ""


# ─── Credential Management ──────────────────────────────────────────────────

class WhatsAppCredentialManager:
    """Stores 360dialog credentials with Fernet encryption (fallback: base64)."""

    CONFIG_FILE = BASE / "whatsapp_config.json"

    @classmethod
    def save_credentials(cls, api_key: str, phone_number_id: str,
                         webhook_url: str = "",
                         business_name: str = "PPS Anantam") -> None:
        key_encoded = base64.b64encode(api_key.encode()).decode()
        key_format = "base64"
        try:
            from vault_engine import encrypt_value
            key_encoded = encrypt_value(api_key)
            key_format = "fernet"
        except (ImportError, Exception):
            pass
        config = {
            "api_key": key_encoded,
            "api_key_format": key_format,
            "phone_number_id": phone_number_id,
            "webhook_url": webhook_url,
            "business_name": business_name,
        }
        with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        # Cache decrypted creds in session so they survive within current run
        try:
            from cloud_secrets import remember_in_session
            sess_block = {**config, "api_key": api_key}  # decrypted in session
            remember_in_session("whatsapp", sess_block)
        except Exception:
            pass

    @classmethod
    def load_credentials(cls) -> dict:
        # Cloud-resilient: prefer st.secrets["whatsapp"] / env vars
        try:
            from cloud_secrets import get_secret_block, remember_in_session
            block = get_secret_block("whatsapp", env_keys={
                "api_key":          "WHATSAPP_API_KEY",
                "phone_number_id":  "WHATSAPP_PHONE_NUMBER_ID",
                "webhook_url":      "WHATSAPP_WEBHOOK_URL",
                "business_name":    "WHATSAPP_BUSINESS_NAME",
            })
            if block.get("api_key"):
                remember_in_session("whatsapp", block)
                return block
        except Exception:
            pass

        if not cls.CONFIG_FILE.exists():
            return {}
        try:
            with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            if config.get("api_key"):
                fmt = config.get("api_key_format", "base64")
                if fmt == "fernet":
                    try:
                        from vault_engine import decrypt_value
                        config["api_key"] = decrypt_value(config["api_key"])
                    except Exception:
                        config["api_key"] = ""
                else:
                    config["api_key"] = base64.b64decode(config["api_key"]).decode()
                    # Auto-migrate to Fernet
                    try:
                        cls.save_credentials(
                            config["api_key"], config.get("phone_number_id", ""),
                            config.get("webhook_url", ""), config.get("business_name", "PPS Anantam"),
                        )
                    except Exception:
                        pass
            config.pop("api_key_format", None)
            return config
        except (json.JSONDecodeError, IOError, Exception):
            return {}

    @classmethod
    def test_connection(cls) -> Tuple[bool, str]:
        creds = cls.load_credentials()
        if not creds.get("api_key"):
            return False, "WhatsApp API key not configured"
        if not requests:
            return False, "requests library not installed"
        try:
            resp = requests.get(
                f"{DIALOG360_API_BASE}/configs/about",
                headers={"D360-API-KEY": creds["api_key"]},
                timeout=10)
            if resp.status_code == 200:
                return True, "Connected successfully"
            return False, f"API returned {resp.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)[:100]}"


# ─── 360dialog API Client ───────────────────────────────────────────────────

class Dialog360Client:
    """Low-level 360dialog WhatsApp Business API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = DIALOG360_API_BASE
        self.session = None
        if requests:
            self.session = requests.Session()
            self.session.headers.update({
                "D360-API-KEY": api_key,
                "Content-Type": "application/json"
            })

    def send_template_message(self, to: str, template_name: str,
                              language_code: str = "en",
                              parameters: list = None) -> dict:
        """Send a pre-approved template message."""
        if not self.session:
            return {"success": False, "error": "requests not available"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            }
        }
        if parameters:
            payload["template"]["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in parameters]
            }]
        try:
            resp = self.session.post(f"{self.base_url}/messages",
                                     json=payload, timeout=30)
            data = resp.json()
            if resp.status_code in (200, 201):
                msg_id = ""
                if "messages" in data and data["messages"]:
                    msg_id = data["messages"][0].get("id", "")
                return {"success": True, "message_id": msg_id, "error": ""}
            return {"success": False, "message_id": "",
                    "error": data.get("error", {}).get("message", str(data)[:200])}
        except Exception as e:
            return {"success": False, "message_id": "", "error": str(e)[:200]}

    def send_text_message(self, to: str, text: str) -> dict:
        """Send a free-form text message (session messages only)."""
        if not self.session:
            return {"success": False, "error": "requests not available"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        try:
            resp = self.session.post(f"{self.base_url}/messages",
                                     json=payload, timeout=30)
            data = resp.json()
            if resp.status_code in (200, 201):
                msg_id = ""
                if "messages" in data and data["messages"]:
                    msg_id = data["messages"][0].get("id", "")
                return {"success": True, "message_id": msg_id, "error": ""}
            return {"success": False, "message_id": "",
                    "error": data.get("error", {}).get("message", str(data)[:200])}
        except Exception as e:
            return {"success": False, "message_id": "", "error": str(e)[:200]}

    def get_templates(self) -> list:
        """Fetch approved templates from 360dialog."""
        if not self.session:
            return []
        try:
            resp = self.session.get(f"{self.base_url}/configs/templates", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("waba_templates", data) if isinstance(data, dict) else data
        except Exception:
            pass
        return []

    def get_about(self) -> dict:
        """Get account info — connection test."""
        if not self.session:
            return {}
        try:
            resp = self.session.get(f"{self.base_url}/configs/about", timeout=10)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}


# ─── Template Manager ────────────────────────────────────────────────────────

class WhatsAppTemplateManager:
    """Maps business actions to 360dialog approved templates."""

    TEMPLATES_FILE = BASE / "whatsapp_templates.json"

    DEFAULT_TEMPLATES = {
        "offer_template": {
            "name": "bitumen_offer_v1",
            "language": "en",
            "parameters": ["customer_name", "grade", "price_per_mt",
                           "city", "quantity_mt", "validity_hours"],
            "category": "MARKETING",
        },
        "followup_template": {
            "name": "bitumen_followup_v1",
            "language": "en",
            "parameters": ["customer_name", "reference", "price_per_mt",
                           "dispatch_timeline"],
            "category": "MARKETING",
        },
        "payment_reminder_template": {
            "name": "payment_reminder_v1",
            "language": "en",
            "parameters": ["customer_name", "amount", "invoice_ref",
                           "bank_name", "account_no", "ifsc"],
            "category": "UTILITY",
        },
        "reactivation_template": {
            "name": "price_drop_alert_v1",
            "language": "en",
            "parameters": ["customer_name", "new_price", "old_price",
                           "savings", "city"],
            "category": "MARKETING",
        },
        "festival_greeting_v1": {
            "name": "festival_greeting_v1",
            "language": "en",
            "parameters": ["customer_name", "festival_name"],
            "category": "MARKETING",
        },
        "price_update_v1": {
            "name": "price_update_v1",
            "language": "en",
            "parameters": ["customer_name", "grade", "old_price",
                           "new_price", "change_pct"],
            "category": "UTILITY",
        },
        "daily_outreach_v1": {
            "name": "daily_outreach_v1",
            "language": "en",
            "parameters": ["customer_name", "company_name"],
            "category": "MARKETING",
        },
    }

    @classmethod
    def load_templates(cls) -> dict:
        if cls.TEMPLATES_FILE.exists():
            try:
                with open(cls.TEMPLATES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return dict(cls.DEFAULT_TEMPLATES)

    @classmethod
    def save_templates(cls, templates: dict) -> None:
        with open(cls.TEMPLATES_FILE, "w", encoding="utf-8") as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)

    @classmethod
    def get_template_for_action(cls, action: str) -> dict:
        templates = cls.load_templates()
        return templates.get(action, {})


# ─── WhatsApp Engine ─────────────────────────────────────────────────────────

class WhatsAppEngine:
    """High-level WhatsApp automation engine."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()
        self.credentials = WhatsAppCredentialManager.load_credentials()
        self.client = None
        if self.credentials.get("api_key") and requests:
            self.client = Dialog360Client(self.credentials["api_key"])

    def _now(self) -> str:
        return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    # ─── Queue Management ────────────────────────────────────────────────

    def queue_message(self, to_number: str, message_type: str,
                      template_name: str = None, template_params: list = None,
                      session_text: str = None, customer_id: int = None,
                      deal_id: int = None, auto_send: bool = False,
                      scheduled_at: str = None, broadcast_id: str = None) -> int:
        """Validate phone and insert into queue. Returns queue_id."""
        valid, normalized = validate_indian_mobile(to_number)
        if not valid:
            return -1

        from database import insert_wa_queue
        status = "pending" if auto_send else "draft"
        return insert_wa_queue({
            "to_number": normalized,
            "message_type": message_type,
            "template_name": template_name,
            "template_params": json.dumps(template_params) if template_params else None,
            "session_text": session_text,
            "customer_id": customer_id,
            "deal_id": deal_id,
            "broadcast_id": broadcast_id,
            "status": status,
            "scheduled_at": scheduled_at,
        })

    def process_queue(self) -> dict:
        """Process pending WhatsApp messages. Returns {sent, failed, skipped}."""
        if not self.client:
            return {"sent": 0, "failed": 0, "skipped": 0}

        from database import get_wa_queue, update_wa_status
        results = {"sent": 0, "failed": 0, "skipped": 0}
        now = self._now()

        pending = get_wa_queue(status="pending", limit=100)
        sent_this_minute = 0
        rate_limit = self.settings.get("whatsapp_rate_limit_per_minute", 20)
        daily_limit = self.settings.get("whatsapp_rate_limit_per_day", 1000)

        # Festival mode: increase daily limit for broadcast days
        if self._is_festival_mode():
            daily_limit = self.settings.get("whatsapp_festival_mode_limit", 24000)

        # Check daily send count
        today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
        all_today = get_wa_queue(status=None, limit=daily_limit + 100)
        sent_today = sum(1 for m in all_today
                         if m.get("status") == "sent" and
                         (m.get("sent_at") or "")[:10] == today)
        if sent_today >= daily_limit:
            return {"sent": 0, "failed": 0, "skipped": len(pending)}

        for item in pending:
            if sent_this_minute >= rate_limit:
                results["skipped"] += len(pending) - sent_this_minute
                break

            if item.get("scheduled_at") and item["scheduled_at"] > now:
                results["skipped"] += 1
                continue

            if item.get("retry_count", 0) >= item.get("max_retries", 3):
                update_wa_status(item["id"], "failed",
                                 error_message="Max retries exceeded")
                results["failed"] += 1
                continue

            update_wa_status(item["id"], "sending")

            if item["message_type"] == "template" and item.get("template_name"):
                params = json.loads(item["template_params"]) if item.get("template_params") else None
                result = self.client.send_template_message(
                    to=item["to_number"],
                    template_name=item["template_name"],
                    parameters=params)
            elif item["message_type"] == "session" and item.get("session_text"):
                # Check session window
                from database import get_active_wa_session
                session = get_active_wa_session(item["to_number"])
                if session:
                    result = self.client.send_text_message(
                        to=item["to_number"], text=item["session_text"])
                else:
                    # Fallback to template
                    update_wa_status(item["id"], "failed",
                                     error_message="Session expired, use template")
                    results["failed"] += 1
                    continue
            else:
                update_wa_status(item["id"], "failed",
                                 error_message="Invalid message type or missing content")
                results["failed"] += 1
                continue

            if result.get("success"):
                update_wa_status(item["id"], "sent",
                                 wa_message_id=result.get("message_id", ""),
                                 sent_at=now)
                self._log_to_communications(
                    item.get("customer_id"),
                    item.get("session_text") or item.get("template_name", ""),
                    item.get("template_name", ""), "sent")
                results["sent"] += 1
                sent_this_minute += 1
            else:
                update_wa_status(
                    item["id"], "pending",
                    error_message=result.get("error", "Unknown error"),
                    retry_count=item.get("retry_count", 0) + 1)
                results["failed"] += 1

        return results

    def approve_message(self, queue_id: int) -> bool:
        from database import update_wa_status
        update_wa_status(queue_id, "pending")
        return True

    def cancel_message(self, queue_id: int) -> bool:
        from database import update_wa_status
        update_wa_status(queue_id, "cancelled")
        return True

    # ─── Template Message Sending ────────────────────────────────────────

    def send_offer(self, customer_name: str, phone: str, city: str,
                   grade: str, quantity_mt: float, price_per_mt: float,
                   customer_id: int = None, auto_send: bool = False) -> int:
        tmpl = WhatsAppTemplateManager.get_template_for_action("offer_template")
        validity = self.settings.get("quote_validity_hours", 24)
        params = [customer_name, grade, f"{price_per_mt:.0f}",
                  city, f"{quantity_mt:.0f}", str(validity)]
        return self.queue_message(
            to_number=phone, message_type="template",
            template_name=tmpl.get("name", "bitumen_offer_v1"),
            template_params=params, customer_id=customer_id,
            auto_send=auto_send)

    def send_followup(self, customer_name: str, phone: str,
                      reference: str = "", price: float = 0,
                      customer_id: int = None) -> int:
        tmpl = WhatsAppTemplateManager.get_template_for_action("followup_template")
        params = [customer_name, reference or "our recent offer",
                  f"{price:.0f}" if price else "as quoted", "48 hours"]
        return self.queue_message(
            to_number=phone, message_type="template",
            template_name=tmpl.get("name", "bitumen_followup_v1"),
            template_params=params, customer_id=customer_id, auto_send=True)

    def send_payment_reminder(self, customer_name: str, phone: str,
                              amount: float, invoice_ref: str = "",
                              customer_id: int = None) -> int:
        tmpl = WhatsAppTemplateManager.get_template_for_action("payment_reminder_template")
        params = [customer_name, f"{amount:.0f}", invoice_ref or "N/A",
                  "ICICI Bank", "184105001402", "ICIC0001841"]
        auto = self.settings.get("whatsapp_auto_send_payment_reminder", False)
        return self.queue_message(
            to_number=phone, message_type="template",
            template_name=tmpl.get("name", "payment_reminder_v1"),
            template_params=params, customer_id=customer_id, auto_send=auto)

    def send_reactivation(self, customer_name: str, phone: str, city: str,
                          new_price: float, old_price: float,
                          savings: float, customer_id: int = None) -> int:
        tmpl = WhatsAppTemplateManager.get_template_for_action("reactivation_template")
        params = [customer_name, f"{new_price:.0f}", f"{old_price:.0f}",
                  f"{savings:.0f}", city]
        auto = self.settings.get("whatsapp_auto_send_reactivation", False)
        return self.queue_message(
            to_number=phone, message_type="template",
            template_name=tmpl.get("name", "price_drop_alert_v1"),
            template_params=params, customer_id=customer_id, auto_send=auto)

    # ─── Session Messages ────────────────────────────────────────────────

    def send_session_message(self, phone: str, text: str,
                             customer_id: int = None) -> int:
        if not self.settings.get("whatsapp_session_message_enabled", True):
            return -1
        return self.queue_message(
            to_number=phone, message_type="session",
            session_text=text, customer_id=customer_id, auto_send=True)

    # ─── Broadcasts ──────────────────────────────────────────────────────

    def broadcast_template(self, phone_numbers: list, template_name: str,
                           template_params_list: list,
                           broadcast_name: str = "") -> dict:
        """Send same template to multiple recipients."""
        import uuid
        broadcast_id = broadcast_name or str(uuid.uuid4())[:8]
        queued = 0
        invalid = 0
        for i, phone in enumerate(phone_numbers):
            valid, _ = validate_indian_mobile(phone)
            if not valid:
                invalid += 1
                continue
            params = template_params_list[i] if i < len(template_params_list) else []
            self.queue_message(
                to_number=phone, message_type="template",
                template_name=template_name, template_params=params,
                broadcast_id=broadcast_id, auto_send=False)
            queued += 1
        return {"total": len(phone_numbers), "queued": queued,
                "invalid": invalid, "broadcast_id": broadcast_id}

    def broadcast_price_announcement(self, phone_numbers: list,
                                      grade: str, price: float,
                                      effective_date: str = "") -> dict:
        """Broadcast price announcement to multiple customers."""
        params_list = [[grade, f"{format_inr(price)}", effective_date or "today"]] * len(phone_numbers)
        return self.broadcast_template(
            phone_numbers=phone_numbers,
            template_name="price_drop_alert_v1",
            template_params_list=params_list,
            broadcast_name=f"price_{grade}_{effective_date or 'today'}")

    # ─── Smart Trigger Handlers ──────────────────────────────────────────

    def on_opportunity_scan(self, opportunities: list) -> int:
        """Queue WhatsApp offers for reactivation opportunities."""
        if not self.settings.get("whatsapp_enabled"):
            return 0
        if not self.settings.get("whatsapp_auto_send_reactivation"):
            return 0
        count = 0
        for opp in opportunities:
            if opp.get("type") != "price_drop_reactivation":
                continue
            phone = opp.get("customer_contact", "")
            if not phone:
                continue
            self.send_reactivation(
                customer_name=opp.get("customer_name", ""),
                phone=phone, city=opp.get("customer_city", ""),
                new_price=opp.get("new_landed_cost", 0),
                old_price=opp.get("old_landed_cost", 0),
                savings=opp.get("savings_per_mt", 0),
                customer_id=opp.get("customer_id"))
            count += 1
        return count

    def on_payment_overdue(self, overdue_deals: list) -> int:
        """Queue WhatsApp payment reminders for overdue deals."""
        if not self.settings.get("whatsapp_enabled"):
            return 0
        if not self.settings.get("whatsapp_auto_send_payment_reminder"):
            return 0
        count = 0
        for deal in overdue_deals:
            days = deal.get("days_overdue", 0)
            if days not in (7, 14, 30):
                continue
            phone = deal.get("customer_contact", "")
            if not phone:
                continue
            self.send_payment_reminder(
                customer_name=deal.get("customer_name", ""),
                phone=phone, amount=deal.get("outstanding", 0),
                invoice_ref=deal.get("deal_number", ""),
                customer_id=deal.get("customer_id"))
            count += 1
        return count

    # ─── Webhook Handler ─────────────────────────────────────────────────

    def handle_webhook(self, payload: dict) -> None:
        """Process incoming webhook from 360dialog."""
        if not payload:
            return
        statuses = payload.get("statuses", [])
        for status in statuses:
            self.handle_delivery_status(status)
        messages = payload.get("messages", [])
        for msg in messages:
            self.handle_incoming_message(msg)

    def handle_delivery_status(self, status_update: dict) -> None:
        """Update queue status based on delivery receipt."""
        wa_id = status_update.get("id", "")
        status = status_update.get("status", "")
        if not wa_id or not status:
            return
        from database import get_wa_queue, update_wa_status
        items = get_wa_queue(limit=500)
        for item in items:
            if item.get("wa_message_id") == wa_id:
                now = self._now()
                if status == "delivered":
                    update_wa_status(item["id"], "delivered", delivered_at=now)
                elif status == "read":
                    update_wa_status(item["id"], "read", read_at=now)
                elif status == "failed":
                    error = status_update.get("errors", [{}])[0].get("title", "")
                    update_wa_status(item["id"], "failed", error_message=error)
                break

    def handle_incoming_message(self, message: dict) -> None:
        """Log incoming message and open session window."""
        from_number = message.get("from", "")
        text = message.get("text", {}).get("body", "") if message.get("type") == "text" else ""
        wa_id = message.get("id", "")
        if from_number:
            from database import insert_wa_incoming, upsert_wa_session
            insert_wa_incoming({
                "from_number": from_number,
                "message_type": message.get("type", "text"),
                "message_text": text,
                "wa_message_id": wa_id,
            })
            upsert_wa_session(from_number, last_message=text[:200])

    # ─── Festival Mode ────────────────────────────────────────────────────

    def _is_festival_mode(self) -> bool:
        """Check if today is a festival day (enables higher rate limits)."""
        try:
            from sales_calendar import get_festivals
            today = datetime.datetime.now(IST).date()
            for f in get_festivals():
                date_str = f.get("date", "")
                for fmt in ("%Y-%m-%d", "%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        fdate = datetime.datetime.strptime(date_str, fmt).date()
                        if fdate == today:
                            return True
                        break
                    except Exception:
                        continue
        except Exception:
            pass
        return False

    # ─── Connection Status ───────────────────────────────────────────────

    def get_connection_status(self) -> dict:
        """Return current connection status."""
        if not self.credentials.get("api_key"):
            return {"connected": False, "status_color": "red",
                    "message": "Not configured"}
        connected, message = WhatsAppCredentialManager.test_connection()
        return {
            "connected": connected,
            "status_color": "green" if connected else "red",
            "message": message,
            "phone_number_id": self.credentials.get("phone_number_id", ""),
            "business_name": self.credentials.get("business_name", ""),
        }

    # ─── Delivery Stats ──────────────────────────────────────────────────

    def get_delivery_stats(self, days: int = 30) -> dict:
        """Return delivery statistics."""
        from database import get_wa_queue
        all_items = get_wa_queue(limit=5000)
        cutoff = (datetime.datetime.now(IST) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        recent = [m for m in all_items if (m.get("created_at") or "") >= cutoff]
        return {
            "total": len(recent),
            "sent": sum(1 for m in recent if m.get("status") == "sent"),
            "delivered": sum(1 for m in recent if m.get("status") == "delivered"),
            "read": sum(1 for m in recent if m.get("status") == "read"),
            "failed": sum(1 for m in recent if m.get("status") == "failed"),
            "pending": sum(1 for m in recent if m.get("status") == "pending"),
        }

    # ─── Logging ─────────────────────────────────────────────────────────

    def _log_to_communications(self, customer_id, content,
                                template_used, status):
        if not customer_id:
            return
        try:
            from database import log_communication
            log_communication({
                "customer_id": customer_id,
                "channel": "whatsapp",
                "direction": "outbound",
                "content": content[:500],
                "template_used": template_used,
                "status": status,
            })
        except Exception:
            pass


# ─── DPDP Opt-Out Handler ─────────────────────────────────────────────────────


def handle_whatsapp_opt_out(from_number: str) -> dict:
    """
    Process STOP/unsubscribe message from WhatsApp contact.
    Updates contacts table: whatsapp_opted_in = 0.

    Returns: {success, contact_name, message}
    """
    valid, normalized = validate_indian_mobile(from_number)
    if not valid:
        return {"success": False, "message": "Invalid number"}

    try:
        from database import _get_conn
        conn = _get_conn()

        # Find contact by mobile
        row = conn.execute(
            "SELECT id, name FROM contacts WHERE mobile1 = ? OR mobile2 = ?",
            (normalized, normalized)
        ).fetchone()

        if row:
            conn.execute(
                "UPDATE contacts SET whatsapp_opted_in = 0, "
                "updated_at = datetime('now') WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            conn.close()
            return {
                "success": True,
                "contact_name": row["name"],
                "message": f"Opt-out processed for {row['name']}",
            }
        else:
            conn.close()
            return {"success": False, "message": "Contact not found"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def check_message_for_opt_out(message_text: str) -> bool:
    """Check if incoming message is an opt-out request."""
    if not message_text:
        return False
    text = message_text.strip().upper()
    opt_out_keywords = {"STOP", "UNSUBSCRIBE", "OPT OUT", "OPTOUT",
                        "CANCEL", "REMOVE ME", "BAND KARO", "NAHI CHAHIYE"}
    return text in opt_out_keywords or any(kw in text for kw in opt_out_keywords)


# ─── Scheduler ───────────────────────────────────────────────────────────────

_wa_scheduler_thread = None
_wa_scheduler_running = False
_wa_scheduler_lock = threading.Lock()


def _wa_scheduler_loop():
    """Background loop: process WhatsApp queue every 2 minutes."""
    global _wa_scheduler_running
    while _wa_scheduler_running:
        try:
            engine = WhatsAppEngine()
            engine.process_queue()
        except Exception:
            pass
        for _ in range(120):
            if not _wa_scheduler_running:
                break
            time.sleep(1)


def start_whatsapp_scheduler():
    """Start background WhatsApp scheduler."""
    global _wa_scheduler_thread, _wa_scheduler_running
    with _wa_scheduler_lock:
        if _wa_scheduler_thread and _wa_scheduler_thread.is_alive():
            return
        _wa_scheduler_running = True
        _wa_scheduler_thread = threading.Thread(
            target=_wa_scheduler_loop, daemon=True, name="WhatsAppScheduler")
        _wa_scheduler_thread.start()


def stop_whatsapp_scheduler():
    """Stop background WhatsApp scheduler."""
    global _wa_scheduler_running
    _wa_scheduler_running = False
