"""
PPS Anantam — Auto Email Engine v1.0
======================================
SMTP-based email sending with queue, scheduling, templates,
delivery tracking, and smart triggers.

Email Types:
  1. new_offer        — Quote auto-send to customer
  2. followup         — Day 3 follow-up sequence email
  3. reactivation     — Price-drop reactivation
  4. payment_reminder — At 7, 14, 30 days overdue
  5. tender_response  — Formal bid submission
  6. director_report  — Daily 8:30 AM IST
  7. weekly_summary   — Monday 9 AM IST recap
"""

import smtplib
import ssl
import json
import base64
import threading
import time
import re
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Tuple

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ─── Credential Management ──────────────────────────────────────────────────

class EmailCredentialManager:
    """Stores SMTP credentials with Fernet encryption (fallback: base64 legacy)."""

    CONFIG_FILE = BASE / "email_config.json"

    @classmethod
    def save_credentials(cls, smtp_host: str, smtp_port: int,
                         username: str, password: str,
                         from_name: str, from_email: str,
                         signature_html: str = "",
                         cc_default: str = "",
                         bcc_default: str = "") -> None:
        # Encrypt password via vault if available, else base64 legacy
        pw_encoded = base64.b64encode(password.encode()).decode()
        pw_format = "base64"
        try:
            from vault_engine import encrypt_value
            pw_encoded = encrypt_value(password)
            pw_format = "fernet"
        except (ImportError, Exception):
            pass
        config = {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "username": username,
            "password": pw_encoded,
            "password_format": pw_format,
            "from_name": from_name,
            "from_email": from_email,
            "signature_html": signature_html,
            "cc_default": cc_default,
            "bcc_default": bcc_default,
        }
        with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_credentials(cls) -> dict:
        if not cls.CONFIG_FILE.exists():
            return {}
        try:
            with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            if config.get("password"):
                fmt = config.get("password_format", "base64")
                if fmt == "fernet":
                    try:
                        from vault_engine import decrypt_value
                        config["password"] = decrypt_value(config["password"])
                    except Exception:
                        config["password"] = ""
                else:
                    # Legacy base64 — decode + auto-migrate to Fernet
                    config["password"] = base64.b64decode(config["password"]).decode()
                    try:
                        cls.save_credentials(
                            config.get("smtp_host", ""), config.get("smtp_port", 587),
                            config.get("username", ""), config["password"],
                            config.get("from_name", ""), config.get("from_email", ""),
                            config.get("signature_html", ""),
                            config.get("cc_default", ""), config.get("bcc_default", ""),
                        )
                    except Exception:
                        pass
            config.pop("password_format", None)
            return config
        except (json.JSONDecodeError, IOError, Exception):
            return {}

    @classmethod
    def test_connection(cls) -> Tuple[bool, str]:
        creds = cls.load_credentials()
        if not creds.get("smtp_host"):
            return False, "SMTP not configured"
        try:
            ctx = ssl.create_default_context()
            port = creds.get("smtp_port", 587)
            if port == 465:
                server = smtplib.SMTP_SSL(creds["smtp_host"], port, context=ctx, timeout=10)
            else:
                server = smtplib.SMTP(creds["smtp_host"], port, timeout=10)
                server.starttls(context=ctx)
            server.login(creds["username"], creds["password"])
            server.quit()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)[:100]}"


# ─── Email Engine ────────────────────────────────────────────────────────────

class EmailEngine:
    """SMTP email engine with queue, rate limiting, and delivery tracking."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()
        self.credentials = EmailCredentialManager.load_credentials()
        self.rate_limit_per_hour = self.settings.get("email_rate_limit_per_hour", 50)
        self._send_count = 0
        self._send_count_reset = datetime.datetime.now(IST)
        self._lock = threading.Lock()

    # ─── Core Sending ────────────────────────────────────────────────────

    def send_email(self, to_email: str, subject: str, body_html: str,
                   body_text: str = "", cc: str = "", bcc: str = "") -> dict:
        """Send a single email via SMTP. Returns {success, message_id, error}."""
        if not self.credentials.get("smtp_host"):
            return {"success": False, "message_id": "", "error": "SMTP not configured"}

        if not EMAIL_REGEX.match(to_email):
            return {"success": False, "message_id": "", "error": f"Invalid email: {to_email}"}

        if not self._check_rate_limit():
            return {"success": False, "message_id": "", "error": "Rate limit exceeded"}

        try:
            msg = self._build_mime_message(to_email, subject, body_html,
                                           body_text, cc, bcc)
            ctx = ssl.create_default_context()
            port = self.credentials.get("smtp_port", 587)

            if port == 465:
                server = smtplib.SMTP_SSL(self.credentials["smtp_host"], port,
                                          context=ctx, timeout=30)
            else:
                server = smtplib.SMTP(self.credentials["smtp_host"], port, timeout=30)
                server.starttls(context=ctx)

            server.login(self.credentials["username"], self.credentials["password"])

            recipients = [to_email]
            if cc:
                recipients += [c.strip() for c in cc.split(",") if c.strip()]
            if bcc:
                recipients += [b.strip() for b in bcc.split(",") if b.strip()]

            server.sendmail(self.credentials.get("from_email", self.credentials["username"]),
                            recipients, msg.as_string())
            message_id = msg.get("Message-ID", "")
            server.quit()

            with self._lock:
                self._send_count += 1

            return {"success": True, "message_id": message_id, "error": ""}
        except Exception as e:
            return {"success": False, "message_id": "", "error": str(e)[:200]}

    def send_email_sendgrid(self, to_email: str, subject: str,
                             body_html: str, body_text: str = "") -> dict:
        """Send email via SendGrid HTTP API. Returns {success, message_id, error}."""
        try:
            from settings_engine import get_api_key_secure, load_settings
            settings = load_settings()
            api_key = get_api_key_secure("sendgrid_api_key")
            if not api_key:
                return {"success": False, "message_id": "",
                        "error": "SendGrid API key not configured"}

            from_email = settings.get("sendgrid_from_email") or self.credentials.get(
                "from_email", self.credentials.get("username", ""))
            from_name = settings.get("sendgrid_from_name", "PPS Anantam")

            import urllib.request
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email, "name": from_name},
                "subject": subject,
                "content": [],
            }
            if body_text:
                payload["content"].append({"type": "text/plain", "value": body_text})
            if body_html:
                payload["content"].append({"type": "text/html", "value": body_html})
            if not payload["content"]:
                payload["content"].append({"type": "text/plain", "value": subject})

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=30)
            msg_id = resp.headers.get("X-Message-Id", "")
            return {"success": True, "message_id": msg_id, "error": ""}
        except Exception as e:
            return {"success": False, "message_id": "", "error": str(e)[:200]}

    def send_email_brevo(self, to_email: str, subject: str,
                          body_html: str, body_text: str = "") -> dict:
        """Send email via Brevo (Sendinblue) HTTP API. Free: 300 emails/day."""
        try:
            from settings_engine import get_api_key_secure
            api_key = get_api_key_secure("brevo_api_key")
            if not api_key:
                return {"success": False, "message_id": "",
                        "error": "Brevo API key not configured"}

            from_email = self.credentials.get(
                "from_email", self.credentials.get("username", ""))
            from_name = self.credentials.get("from_name", "PPS Anantam")

            import urllib.request
            payload = {
                "sender": {"name": from_name, "email": from_email},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": body_html or f"<p>{body_text or subject}</p>",
            }
            if body_text:
                payload["textContent"] = body_text

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=data,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode("utf-8"))
            msg_id = result.get("messageId", "")
            return {"success": True, "message_id": msg_id, "error": ""}
        except Exception as e:
            return {"success": False, "message_id": "", "error": str(e)[:200]}

    def send_email_auto(self, to_email: str, subject: str,
                         body_html: str, body_text: str = "",
                         cc: str = "", bcc: str = "") -> dict:
        """Auto-select: SMTP first, SendGrid second, Brevo third."""
        # Try SMTP first
        result = self.send_email(to_email, subject, body_html, body_text, cc, bcc)
        if result.get("success"):
            return result

        # If rate limited or SMTP failed, try SendGrid
        try:
            from settings_engine import load_settings
            if load_settings().get("sendgrid_enabled"):
                sg_result = self.send_email_sendgrid(to_email, subject,
                                                      body_html, body_text)
                if sg_result.get("success"):
                    return sg_result
        except Exception:
            pass

        # Third fallback: Brevo
        try:
            from settings_engine import get_api_key_secure
            if get_api_key_secure("brevo_api_key"):
                brevo_result = self.send_email_brevo(to_email, subject,
                                                      body_html, body_text)
                if brevo_result.get("success"):
                    return brevo_result
        except Exception:
            pass

        return result  # Return original SMTP error

    def _check_rate_limit(self) -> bool:
        now = datetime.datetime.now(IST)
        with self._lock:
            if (now - self._send_count_reset).total_seconds() > 3600:
                self._send_count = 0
                self._send_count_reset = now
            return self._send_count < self.rate_limit_per_hour

    def _build_mime_message(self, to_email, subject, body_html,
                            body_text, cc, bcc) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        from_name = self.credentials.get("from_name", "PPS Anantam")
        from_email = self.credentials.get("from_email", self.credentials.get("username", ""))
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        sig = self.credentials.get("signature_html", "")
        if sig:
            body_html = body_html + f"\n<br><br>{sig}"

        # DPDP compliance: append unsubscribe footer
        body_html = self._append_unsubscribe_footer(body_html, to_email)
        if body_text:
            body_text = self._append_unsubscribe_footer_text(body_text)

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        return msg

    def _append_unsubscribe_footer(self, body_html: str, to_email: str) -> str:
        """Append DPDP-compliant unsubscribe footer to HTML emails."""
        try:
            from settings_engine import load_settings
            settings = load_settings()
            if not settings.get("dpdp_compliance_enabled", True):
                return body_html
        except Exception:
            return body_html

        footer_text = (
            '<br><hr style="border:none;border-top:1px solid #ccc;margin:20px 0">'
            '<p style="font-size:11px;color:#888;text-align:center">'
            'You are receiving this email because you are a valued business contact of '
            'PPS Anantam Capital Pvt Ltd. '
            'To unsubscribe from future communications, reply with "STOP" or '
            f'email <a href="mailto:unsubscribe@ppsanantam.com?subject=Unsubscribe&body={to_email}">'
            'unsubscribe@ppsanantam.com</a>.'
            '</p>'
        )
        return body_html + footer_text

    def _append_unsubscribe_footer_text(self, body_text: str) -> str:
        """Append DPDP unsubscribe footer to plain text emails."""
        try:
            from settings_engine import load_settings
            if not load_settings().get("dpdp_compliance_enabled", True):
                return body_text
        except Exception:
            return body_text

        return body_text + (
            "\n\n---\n"
            "You are receiving this email because you are a valued business contact "
            "of PPS Anantam Capital Pvt Ltd. "
            "To unsubscribe, reply with STOP."
        )

    # ─── Queue Management ────────────────────────────────────────────────

    def queue_email(self, to_email: str, subject: str, body_html: str,
                    body_text: str = "", email_type: str = "manual",
                    scheduled_at: str = None, customer_id: int = None,
                    deal_id: int = None, auto_send: bool = False,
                    cc: str = "", bcc: str = "") -> int:
        """Insert email into queue. Returns queue_id."""
        from database import insert_email_queue
        status = "pending" if auto_send else "draft"
        return insert_email_queue({
            "to_email": to_email,
            "cc": cc or self.credentials.get("cc_default", ""),
            "bcc": bcc or self.credentials.get("bcc_default", ""),
            "subject": subject,
            "body_html": body_html,
            "body_text": body_text,
            "email_type": email_type,
            "customer_id": customer_id,
            "deal_id": deal_id,
            "status": status,
            "max_retries": self.settings.get("email_max_retries", 3),
            "scheduled_at": scheduled_at,
        })

    def process_queue(self) -> dict:
        """Process pending/scheduled emails. Returns {sent, failed, skipped}."""
        from database import get_email_queue, update_email_status
        results = {"sent": 0, "failed": 0, "skipped": 0}
        now = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

        pending = get_email_queue(status="pending", limit=100)
        for item in pending:
            # Skip if scheduled for future
            if item.get("scheduled_at") and item["scheduled_at"] > now:
                results["skipped"] += 1
                continue

            # Skip if max retries exceeded
            if item.get("retry_count", 0) >= item.get("max_retries", 3):
                update_email_status(item["id"], "failed",
                                    error_message="Max retries exceeded")
                results["failed"] += 1
                continue

            update_email_status(item["id"], "sending")
            result = self.send_email_auto(
                to_email=item["to_email"],
                subject=item["subject"],
                body_html=item.get("body_html", ""),
                body_text=item.get("body_text", ""),
                cc=item.get("cc", ""),
                bcc=item.get("bcc", ""),
            )

            if result["success"]:
                update_email_status(item["id"], "sent",
                                    smtp_message_id=result["message_id"],
                                    sent_at=now)
                self._log_to_communications(
                    item.get("customer_id"), item["subject"],
                    item.get("body_text", "")[:200],
                    item.get("email_type", ""), "sent")
                results["sent"] += 1
            else:
                update_email_status(
                    item["id"], "pending",
                    error_message=result["error"],
                    retry_count=item.get("retry_count", 0) + 1)
                results["failed"] += 1

        return results

    def approve_draft(self, queue_id: int) -> bool:
        """Change status from draft to pending."""
        from database import update_email_status
        update_email_status(queue_id, "pending")
        return True

    def cancel_email(self, queue_id: int) -> bool:
        """Cancel a queued email."""
        from database import update_email_status
        update_email_status(queue_id, "cancelled")
        return True

    # ─── Template-Based Sending ──────────────────────────────────────────

    def send_offer_email(self, customer_name: str, customer_email: str,
                         city: str, grade: str, quantity_mt: float,
                         price_per_mt: float, source: str = "",
                         benefit_pct: float = 0, customer_id: int = None,
                         auto_send: bool = False,
                         segment: str = "") -> int:
        """Queue an offer email using CommunicationHub template (segment-aware)."""
        from communication_engine import CommunicationHub
        hub = CommunicationHub()
        if segment:
            email = hub.email_offer_segmented(customer_name, city, grade,
                                              quantity_mt, price_per_mt,
                                              segment, source, benefit_pct)
        else:
            email = hub.email_offer(customer_name, city, grade, quantity_mt,
                                    price_per_mt, source, benefit_pct)
        return self.queue_email(
            to_email=customer_email, subject=email["subject"],
            body_html=email["body"].replace("\n", "<br>"),
            body_text=email["body"], email_type="offer",
            customer_id=customer_id, auto_send=auto_send)

    def send_followup_email(self, customer_name: str, customer_email: str,
                            city: str = "", original_date: str = "",
                            price: float = 0, customer_id: int = None) -> int:
        """Queue a follow-up email."""
        from communication_engine import CommunicationHub
        hub = CommunicationHub()
        email = hub.email_followup(customer_name, original_date, price, city)
        return self.queue_email(
            to_email=customer_email, subject=email["subject"],
            body_html=email["body"].replace("\n", "<br>"),
            body_text=email["body"], email_type="followup",
            customer_id=customer_id, auto_send=True)

    def send_reactivation_email(self, customer_name: str, customer_email: str,
                                city: str, new_price: float, old_price: float,
                                savings: float, customer_id: int = None) -> int:
        """Queue a reactivation email."""
        from communication_engine import CommunicationHub
        hub = CommunicationHub()
        email = hub.email_reactivation(customer_name, city, new_price,
                                       old_price, savings)
        auto = self.settings.get("email_auto_send_reactivation", False)
        return self.queue_email(
            to_email=customer_email, subject=email["subject"],
            body_html=email["body"].replace("\n", "<br>"),
            body_text=email["body"], email_type="reactivation",
            customer_id=customer_id, auto_send=auto)

    def send_payment_reminder(self, customer_name: str, customer_email: str,
                              amount: float, invoice_ref: str = "",
                              days_overdue: int = 0,
                              customer_id: int = None) -> int:
        """Queue a payment reminder email."""
        from communication_engine import CommunicationHub
        hub = CommunicationHub()
        email = hub.email_payment_reminder(customer_name, amount,
                                           invoice_ref, days_overdue)
        auto = self.settings.get("email_auto_send_payment_reminder", False)
        return self.queue_email(
            to_email=customer_email, subject=email["subject"],
            body_html=email["body"].replace("\n", "<br>"),
            body_text=email["body"], email_type="payment_reminder",
            customer_id=customer_id, auto_send=auto)

    # ─── Automated Reports ───────────────────────────────────────────────

    def generate_director_report(self) -> dict:
        """Generate director report content. Returns {subject, body_html}."""
        today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
        subject = f"Daily Director Report — {today} | PPS Anantam"

        parts = [f"<h2>Director Daily Report — {today}</h2>"]

        try:
            from database import get_dashboard_stats
            stats = get_dashboard_stats()
            parts.append("<h3>Dashboard Summary</h3><ul>")
            parts.append(f"<li>Active Customers: {stats.get('total_customers', 0)}</li>")
            parts.append(f"<li>Active Suppliers: {stats.get('total_suppliers', 0)}</li>")
            parts.append(f"<li>Total Deals: {stats.get('total_deals', 0)}</li>")
            parts.append(f"<li>Open Opportunities: {stats.get('open_opportunities', 0)}</li>")
            parts.append("</ul>")
        except Exception:
            parts.append("<p>Dashboard stats unavailable</p>")

        try:
            crude_data = json.loads((BASE / "tbl_crude_prices.json").read_text(encoding="utf-8"))
            brent = [r for r in crude_data if r.get("benchmark") == "Brent"]
            if brent:
                latest = brent[-1]
                parts.append(f"<h3>Market</h3><p>Brent: ${latest.get('price', 'N/A')}/bbl</p>")
        except Exception:
            pass

        try:
            from crm_engine import IntelligentCRM
            crm = IntelligentCRM()
            targets = crm.get_todays_targets()
            buyers = targets.get("buyers_to_call", [])[:5]
            if buyers:
                parts.append("<h3>Today's Priority Calls</h3><ol>")
                for b in buyers:
                    parts.append(f"<li>{b.get('name', 'Unknown')} — {b.get('reason', '')}</li>")
                parts.append("</ol>")
        except Exception:
            pass

        parts.append(f"<hr><p style='color:#888;font-size:0.9em;'>Auto-generated by PPS Anantam Agentic AI Eco System</p>")
        body_html = "\n".join(parts)
        return {"subject": subject, "body_html": body_html}

    def generate_weekly_summary(self) -> dict:
        """Generate weekly summary content. Returns {subject, body_html}."""
        today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
        subject = f"Weekly Summary — {today} | PPS Anantam"
        parts = [f"<h2>Weekly Summary — {today}</h2>"]

        try:
            from database import get_dashboard_stats, get_email_queue, get_wa_queue
            stats = get_dashboard_stats()
            parts.append("<h3>Business Overview</h3><ul>")
            parts.append(f"<li>Deals: {stats.get('total_deals', 0)}</li>")
            parts.append(f"<li>Opportunities: {stats.get('open_opportunities', 0)}</li>")
            parts.append("</ul>")

            emails_sent = len(get_email_queue(status="sent", limit=500))
            parts.append(f"<h3>Communications</h3><p>Emails sent this period: {emails_sent}</p>")
        except Exception:
            pass

        parts.append(f"<hr><p style='color:#888;'>Auto-generated by PPS Anantam</p>")
        return {"subject": subject, "body_html": "\n".join(parts)}

    def send_director_report(self) -> int:
        """Generate and queue director report."""
        report = self.generate_director_report()
        to = self.settings.get("email_director_report_to", "")
        if not to:
            return -1
        return self.queue_email(
            to_email=to, subject=report["subject"],
            body_html=report["body_html"], email_type="director_report",
            auto_send=True)

    def send_weekly_summary(self) -> int:
        """Generate and queue weekly summary."""
        report = self.generate_weekly_summary()
        to = self.settings.get("email_weekly_summary_to", "")
        if not to:
            return -1
        return self.queue_email(
            to_email=to, subject=report["subject"],
            body_html=report["body_html"], email_type="weekly_summary",
            auto_send=True)

    # ─── Smart Trigger Handlers ──────────────────────────────────────────

    def on_opportunity_scan(self, opportunities: list) -> int:
        """Queue reactivation emails for price-drop opportunities."""
        if not self.settings.get("email_enabled"):
            return 0
        if not self.settings.get("email_auto_send_reactivation"):
            return 0
        count = 0
        for opp in opportunities:
            if opp.get("type") != "price_drop_reactivation":
                continue
            customer_email = opp.get("customer_email", "")
            if not customer_email or not EMAIL_REGEX.match(customer_email):
                continue
            # Dedup: check if already queued today
            from database import get_email_queue
            today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
            existing = get_email_queue(status=None, limit=1000)
            already = any(
                e.get("email_type") == "reactivation"
                and e.get("to_email") == customer_email
                and e.get("created_at", "")[:10] == today
                for e in existing
            )
            if already:
                continue
            self.send_reactivation_email(
                customer_name=opp.get("customer_name", ""),
                customer_email=customer_email,
                city=opp.get("customer_city", ""),
                new_price=opp.get("new_landed_cost", 0),
                old_price=opp.get("old_landed_cost", 0),
                savings=opp.get("savings_per_mt", 0),
                customer_id=opp.get("customer_id"))
            count += 1
        return count

    def on_payment_overdue(self, overdue_deals: list) -> int:
        """Queue payment reminders for overdue deals at 7/14/30 day milestones."""
        if not self.settings.get("email_enabled"):
            return 0
        if not self.settings.get("email_auto_send_payment_reminder"):
            return 0
        count = 0
        for deal in overdue_deals:
            days = deal.get("days_overdue", 0)
            if days not in (7, 14, 30):
                continue
            customer_email = deal.get("customer_email", "")
            if not customer_email:
                continue
            amount = deal.get("outstanding", 0)
            if amount <= 0:
                continue
            self.send_payment_reminder(
                customer_name=deal.get("customer_name", ""),
                customer_email=customer_email,
                amount=amount,
                invoice_ref=deal.get("deal_number", ""),
                days_overdue=days,
                customer_id=deal.get("customer_id"))
            count += 1
        return count

    # ─── Delivery Stats ──────────────────────────────────────────────────

    def get_delivery_stats(self, days: int = 30) -> dict:
        """Return delivery statistics for the last N days."""
        from database import get_email_queue
        all_items = get_email_queue(limit=5000)
        cutoff = (datetime.datetime.now(IST) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        recent = [e for e in all_items if (e.get("created_at") or "") >= cutoff]
        return {
            "total": len(recent),
            "sent": sum(1 for e in recent if e.get("status") == "sent"),
            "failed": sum(1 for e in recent if e.get("status") == "failed"),
            "pending": sum(1 for e in recent if e.get("status") == "pending"),
            "draft": sum(1 for e in recent if e.get("status") == "draft"),
        }

    # ─── Logging ─────────────────────────────────────────────────────────

    def _log_to_communications(self, customer_id, subject, content,
                                template_used, status):
        """Log to database communications table."""
        if not customer_id:
            return
        try:
            from database import log_communication
            log_communication({
                "customer_id": customer_id,
                "channel": "email",
                "direction": "outbound",
                "subject": subject,
                "content": content[:500],
                "template_used": template_used,
                "status": status,
            })
        except Exception:
            pass


# ─── Scheduler ───────────────────────────────────────────────────────────────

_email_scheduler_thread = None
_email_scheduler_running = False
_email_scheduler_lock = threading.Lock()


def _email_scheduler_loop():
    """Background loop: process queue every 5 min, send scheduled reports."""
    global _email_scheduler_running
    while _email_scheduler_running:
        try:
            engine = EmailEngine()
            engine.process_queue()

            now = datetime.datetime.now(IST)
            time_str = now.strftime("%H:%M")

            # Director report
            if engine.settings.get("email_director_report_enabled"):
                target_time = engine.settings.get("email_director_report_time", "08:30")
                if time_str == target_time:
                    engine.send_director_report()

            # Weekly summary (Monday)
            if engine.settings.get("email_weekly_summary_enabled"):
                target_day = engine.settings.get("email_weekly_summary_day", "Monday")
                target_time = engine.settings.get("email_weekly_summary_time", "09:00")
                if now.strftime("%A") == target_day and time_str == target_time:
                    engine.send_weekly_summary()
        except Exception:
            pass

        # Sleep 5 minutes in small chunks
        for _ in range(300):
            if not _email_scheduler_running:
                break
            time.sleep(1)


def start_email_scheduler():
    """Start background email scheduler (daemon thread)."""
    global _email_scheduler_thread, _email_scheduler_running
    with _email_scheduler_lock:
        if _email_scheduler_thread and _email_scheduler_thread.is_alive():
            return
        _email_scheduler_running = True
        _email_scheduler_thread = threading.Thread(
            target=_email_scheduler_loop, daemon=True, name="EmailScheduler")
        _email_scheduler_thread.start()


def stop_email_scheduler():
    """Stop background email scheduler."""
    global _email_scheduler_running
    _email_scheduler_running = False
