"""
PPS Anantam — AI Message Creation Engine v1.0
===============================================
Auto-generates WhatsApp, Email, and share messages using AI,
with fallback to template-based generation when AI is unavailable.

Uses existing ai_fallback_engine for AI generation,
falls back to CommunicationHub templates.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(__file__))

IST = timezone(timedelta(hours=5, minutes=30))


class AIMessageEngine:
    """Generate context-aware messages for sharing dashboard content."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()

    def generate_share_message(self, channel: str, content_context: dict,
                               recipient_name: str = "",
                               tone: str = None) -> dict:
        """Generate a share message for any channel.

        Parameters
        ----------
        channel : str — "email" or "whatsapp"
        content_context : dict — {"section_title", "page_name", "summary", "kpis", ...}
        recipient_name : str — Name of recipient (optional)
        tone : str — "professional", "friendly", "formal" (defaults to settings)

        Returns
        -------
        dict — {"subject": str, "body": str, "editable": True}
        """
        tone = tone or self.settings.get("ai_message_tone", "professional")

        # Try AI generation first
        ai_result = self._try_ai_generation(channel, content_context, recipient_name, tone)
        if ai_result:
            return ai_result

        # Fallback to template-based generation
        return self._template_fallback(channel, content_context, recipient_name, tone)

    def _try_ai_generation(self, channel, context, recipient, tone) -> dict:
        """Try generating message using AI engine. Returns None on failure."""
        try:
            from ai_fallback_engine import ask_with_fallback
        except ImportError:
            return None

        prompt = self._build_prompt(channel, context, recipient, tone)
        try:
            result = ask_with_fallback(prompt, context="")
            answer = result.get("answer", "")
            if answer and len(answer) > 20:
                return self._parse_ai_response(answer, channel)
        except Exception:
            pass
        return None

    def _build_prompt(self, channel, context, recipient, tone) -> str:
        """Build AI prompt for message generation."""
        section = context.get("section_title", "Dashboard Report")
        page = context.get("page_name", "")
        summary = context.get("summary", "")
        kpis = context.get("kpis", [])

        kpi_text = ""
        if kpis:
            kpi_lines = [f"- {k[0]}: {k[1]}" for k in kpis[:5]]
            kpi_text = "\nKey metrics:\n" + "\n".join(kpi_lines)

        greeting = f"Dear {recipient}," if recipient else "Dear Sir/Madam,"

        return f"""Generate a {tone} {channel} message for sharing a dashboard section.

Section: {section}
Page: {page}
Summary: {summary or 'Business intelligence dashboard report'}{kpi_text}

Requirements:
- Start with: {greeting}
- {tone.title()} tone for B2B bitumen trading context
- Brief (3-5 lines for WhatsApp, 5-8 lines for email)
- Include mention of key data/metrics if provided
- End with professional sign-off from PPS Anantam

Format:
SUBJECT: [email subject line]
BODY: [message body]"""

    def _parse_ai_response(self, answer, channel) -> dict:
        """Parse AI response into subject + body."""
        subject = ""
        body = answer.strip()

        if "SUBJECT:" in answer:
            parts = answer.split("BODY:", 1)
            if len(parts) == 2:
                subject_part = parts[0].replace("SUBJECT:", "").strip()
                body = parts[1].strip()
                subject = subject_part[:100]

        if not subject:
            subject = "PPS Anantam — Dashboard Report"

        # Trim WhatsApp messages to 4096 chars
        if channel == "whatsapp" and len(body) > 4000:
            body = body[:3990] + "..."

        return {"subject": subject, "body": body, "editable": True}

    def _template_fallback(self, channel, context, recipient, tone) -> dict:
        """Generate message using templates when AI is unavailable."""
        section = context.get("section_title", "Dashboard Report")
        page = context.get("page_name", "PPS Anantam Dashboard")
        now = datetime.now(IST).strftime("%d-%b-%Y %H:%M IST")
        greeting = f"Dear {recipient}," if recipient else "Dear Sir/Madam,"

        kpis = context.get("kpis", [])
        kpi_text = ""
        if kpis:
            kpi_lines = [f"• {k[0]}: {k[1]}" for k in kpis[:5]]
            kpi_text = "\n\nKey Metrics:\n" + "\n".join(kpi_lines)

        if channel == "whatsapp":
            body = (
                f"{greeting}\n\n"
                f"Sharing: *{section}*\n"
                f"From: {page}\n"
                f"Generated: {now}"
                f"{kpi_text}\n\n"
                f"Please review the attached report.\n\n"
                f"Regards,\nPPS Anantam\nVadodara, Gujarat"
            )
            return {"subject": "", "body": body, "editable": True}

        else:  # email
            subject = f"PPS Anantam — {section}"
            body = (
                f"{greeting}\n\n"
                f"Please find attached the latest report from our dashboard.\n\n"
                f"Section: {section}\n"
                f"Page: {page}\n"
                f"Generated: {now}"
                f"{kpi_text}\n\n"
                f"This report contains the latest market intelligence and analysis "
                f"for your review.\n\n"
                f"Please do not hesitate to contact us for any clarification.\n\n"
                f"Best regards,\n"
                f"PPS Anantam\n"
                f"Vadodara, Gujarat\n"
                f"+91-XXXXXXXXXX"
            )
            return {"subject": subject, "body": body, "editable": True}

    def generate_quick_summary(self, content_context: dict) -> str:
        """Generate a quick text summary of content for sharing."""
        section = content_context.get("section_title", "Report")
        kpis = content_context.get("kpis", [])
        now = datetime.now(IST).strftime("%d-%b-%Y %H:%M IST")

        lines = [f"📊 {section} — {now}"]
        for k in kpis[:5]:
            lines.append(f"• {k[0]}: {k[1]}")
        lines.append("\n— PPS Anantam Dashboard")
        return "\n".join(lines)
