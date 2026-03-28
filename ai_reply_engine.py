"""
AI Reply Engine — Intelligent Auto-Reply for WhatsApp Incoming Messages
========================================================================
Classifies incoming WhatsApp messages, builds context from live prices
and contact history, generates appropriate replies using AI fallback chain.

Intent Classification:
  - buyer_inquiry: Wants to buy bitumen / needs quote
  - seller_offer: Offering to sell / supply bitumen
  - price_check: Asking current price
  - stock_check: Asking about availability
  - general: General greeting / info
  - complaint: Service complaint
  - unknown: Cannot classify (escalate to human)

PPS Anantam Capital Pvt Ltd — CRM Automation v1.0
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ai_reply_engine")

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None


def _slog(action: str, details: str = "", level: str = "info"):
    """Structured log to both stdlib logger and dashboard_log."""
    getattr(logger, level)(f"{action}: {details}" if details else action)
    if _dlog:
        getattr(_dlog, level)("ai_reply_engine", action, details)


BASE = Path(__file__).parent

# ── Intent patterns (rule-based fallback) ────────────────────────────────────

_INTENT_PATTERNS = {
    "price_inquiry": [
        r"\b(price|rate|cost|kya\s+rate|kitna|bhav|daam)\b",
        r"\b(current|today|latest|live)\b.*\b(price|rate)\b",
    ],
    "availability_check": [
        r"\b(stock|availability|available|in\s+stock|ready)\b",
        r"\b(kab|when|delivery|dispatch)\b.*\b(available|ready|possible)\b",
    ],
    "order_placement": [
        r"\b(order|confirm|book|lock|proceed|chalao)\b.*\b(bitumen|vg|mt|ton)\b",
        r"\b(buy|purchase|need|require|want)\b.*\b(bitumen|vg\s*\d|crmb|pmb)\b",
        r"\b(quote|quotation|offer|rate)\b.*\b(send|give|share|provide)\b",
    ],
    "complaint": [
        r"\b(complaint|issue|problem|quality|defect|bad|poor)\b",
        r"\b(not\s+satisfied|disappointed|wrong|damaged)\b",
    ],
    "market_info": [
        r"\b(market|trend|crude|forecast|outlook|prediction)\b",
        r"\b(brent|wti|opec|refinery)\b.*\b(update|news|status)\b",
    ],
    "transport_inquiry": [
        r"\b(transport|truck|tanker|freight|vehicle|loading)\b",
        r"\b(shipping|logistics|route|delivery\s+time)\b",
    ],
    "technical_query": [
        r"\b(specification|spec|test|viscosity|penetration|bis|grade)\b",
        r"\b(pmb|crmb|emulsion)\b.*\b(spec|test|quality)\b",
    ],
    "new_contact": [
        r"\b(new|introduce|first\s+time|referral|recommended)\b",
        r"\b(who\s+are\s+you|company\s+details|about\s+you)\b",
    ],
    "festival_greeting": [
        r"\b(diwali|holi|eid|happy|festival|wish|greeting|navratri|rakhi)\b",
        r"\b(good\s+morning|good\s+evening|namaste|namaskar)\b",
        r"\b(thank|thanks|dhanyavaad|shukriya)\b",
    ],
    "regional_hindi": [
        r"\b(ji|sahab|bhai|seth)\b.*\b(chahiye|batao|bolo)\b",
    ],
    # Legacy aliases for backward compatibility
    "buyer_inquiry": [
        r"\b(buy|purchase|need|require|want|looking\s+for|order)\b.*\b(bitumen|vg\s*\d|crmb|pmb|emulsion)\b",
    ],
    "seller_offer": [
        r"\b(sell|supply|offer|available)\b.*\b(bitumen|vg\s*\d|crmb|pmb)\b",
        r"\b(we\s+have|in\s+stock|ready\s+to\s+dispatch)\b.*\b(bitumen|vg|mt|ton)\b",
    ],
}

# Compile patterns
_COMPILED_PATTERNS = {
    intent: [re.compile(p, re.IGNORECASE) for p in patterns]
    for intent, patterns in _INTENT_PATTERNS.items()
}


# ══════════════════════════════════════════════════════════════════════════════
# AI REPLY ENGINE
# ══════════════════════════════════════════════════════════════════════════════


class AIReplyEngine:
    """Processes incoming WhatsApp messages and generates AI-powered replies."""

    def __init__(self):
        self._settings = self._load_settings()

    def _load_settings(self) -> dict:
        try:
            from settings_engine import load_settings
            return load_settings()
        except Exception:
            return {}

    @property
    def confidence_threshold(self) -> float:
        return self._settings.get("ai_auto_reply_confidence_threshold", 0.7)

    @property
    def escalate_unsure(self) -> bool:
        return self._settings.get("ai_auto_reply_escalate_unsure", True)

    @property
    def languages(self) -> list:
        return self._settings.get("ai_auto_reply_languages", ["en", "hi"])

    def classify_message(self, text: str, from_number: str = "") -> dict:
        """
        Classify intent of incoming message.

        Returns: {intent, confidence, language, details}
        """
        if not text or not text.strip():
            return {"intent": "unknown", "confidence": 0.0,
                    "language": "en", "details": "Empty message"}

        # Detect language
        language = self._detect_language(text)

        # Try AI classification first
        ai_result = self._classify_with_ai(text)
        if ai_result and ai_result.get("confidence", 0) >= 0.6:
            ai_result["language"] = language
            return ai_result

        # Fallback to rule-based classification
        return self._classify_with_rules(text, language)

    def _detect_language(self, text: str) -> str:
        """Detect language: Hindi, Gujarati, Tamil, Telugu, Marathi, or English."""
        # Count characters in specific Unicode script ranges
        counts = {"hi": 0, "gu": 0, "ta": 0, "te": 0, "mr": 0}
        for c in text:
            cp = ord(c)
            if 0x0A80 <= cp <= 0x0AFF:   # Gujarati
                counts["gu"] += 1
            elif 0x0B80 <= cp <= 0x0BFF:  # Tamil
                counts["ta"] += 1
            elif 0x0C00 <= cp <= 0x0C7F:  # Telugu
                counts["te"] += 1
            elif 0x0900 <= cp <= 0x097F:  # Devanagari (Hindi/Marathi)
                counts["hi"] += 1

        text_len = max(len(text), 1)
        threshold = 0.2

        # Gujarati, Tamil, Telugu have distinct scripts
        if counts["gu"] > text_len * threshold:
            return "gu"
        if counts["ta"] > text_len * threshold:
            return "ta"
        if counts["te"] > text_len * threshold:
            return "te"

        # Devanagari could be Hindi or Marathi
        if counts["hi"] > text_len * threshold:
            # Check for Marathi-specific words
            marathi_words = {"aahe", "kay", "mala", "tumhi", "kasa", "nahi",
                             "hoy", "dya", "ghya", "sangitale"}
            words = set(text.lower().split())
            if len(words & marathi_words) >= 2:
                return "mr"
            return "hi"

        # Check for romanized Hindi words
        hindi_words = {"hai", "hain", "kya", "kitna", "chahiye", "dena",
                       "lena", "bhav", "maal", "paisa", "rupee", "ji",
                       "acha", "theek", "nahi", "haan", "kab", "kaise"}
        words = set(text.lower().split())
        if len(words & hindi_words) >= 2:
            return "hi"

        return "en"

    def _classify_with_ai(self, text: str) -> Optional[dict]:
        """Classify using AI fallback engine (routed to whatsapp_reply)."""
        try:
            from ai_fallback_engine import ask_routed, ask_with_fallback
        except ImportError:
            return None

        prompt = (
            "Classify this WhatsApp message from a bitumen business contact. "
            "Respond with ONLY a JSON object: "
            '{"intent": "<one of: buyer_inquiry, seller_offer, price_check, '
            'stock_check, general, complaint, unknown>", '
            '"confidence": <0.0 to 1.0>}\n\n'
            f'Message: "{text[:500]}"'
        )

        try:
            try:
                result = ask_routed(prompt, context="", task_type="whatsapp_reply")
            except Exception:
                result = ask_with_fallback(prompt, context="")
            if result.get("error") == "all_failed":
                return None
            answer = result.get("answer", "")
            # Parse JSON from answer
            start = answer.find("{")
            end = answer.rfind("}")
            if start >= 0 and end > start:
                parsed = json.loads(answer[start:end + 1])
                return {
                    "intent": parsed.get("intent", "unknown"),
                    "confidence": float(parsed.get("confidence", 0.5)),
                    "language": "en",
                    "details": f"AI classified via {result.get('provider', 'unknown')}",
                }
        except Exception as e:
            logger.error(f"AI classification error: {e}")

        return None

    def _classify_with_rules(self, text: str, language: str) -> dict:
        """Rule-based intent classification using regex patterns."""
        best_intent = "unknown"
        best_score = 0
        match_count = {}

        for intent, patterns in _COMPILED_PATTERNS.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches > 0:
                match_count[intent] = matches
                if matches > best_score:
                    best_score = matches
                    best_intent = intent

        confidence = min(0.4 + (best_score * 0.2), 0.85) if best_score > 0 else 0.1

        return {
            "intent": best_intent,
            "confidence": confidence,
            "language": language,
            "details": f"Rule-based: {match_count}" if match_count else "No pattern match",
        }

    def build_context(self, contact: Optional[dict],
                      classification: dict) -> dict:
        """
        Build context for reply generation.
        Pulls from business_context + live_prices.json + contact history.
        """
        context = {
            "intent": classification.get("intent", "unknown"),
            "language": classification.get("language", "en"),
            "prices": {},
            "contact_name": "",
            "contact_company": "",
            "last_interaction": "",
            "business_context": "",
        }

        # Determine segment from contact category
        segment = ""
        if contact:
            category = contact.get("category", "")
            if category:
                try:
                    from business_context import get_segment_for_category
                    segment = get_segment_for_category(category)
                except Exception:
                    pass
        context["segment"] = segment

        # Load business context based on intent + segment
        try:
            from business_context import get_business_context
            intent = classification.get("intent", "general")
            scope_map = {
                "price_inquiry": "pricing",
                "availability_check": "logistics",
                "order_placement": "buyer_inquiry",
                "complaint": "general",
                "market_info": "general",
                "transport_inquiry": "logistics",
                "technical_query": "buyer_inquiry",
                "new_contact": "general",
                "festival_greeting": "general",
                "regional_hindi": "general",
                # Legacy intents
                "buyer_inquiry": "buyer_inquiry",
                "seller_offer": "seller_offer",
                "price_check": "pricing",
                "stock_check": "logistics",
                "general": "general",
            }
            scope = scope_map.get(intent, "general")
            context["business_context"] = get_business_context(scope, segment=segment)
        except Exception:
            pass

        # Load current prices
        try:
            prices_file = BASE / "live_prices.json"
            if prices_file.exists():
                with open(prices_file, "r", encoding="utf-8") as f:
                    context["prices"] = json.load(f)
        except Exception:
            pass

        # Add contact info
        if contact:
            context["contact_name"] = contact.get("name", "")
            context["contact_company"] = contact.get("company_name", "")
            context["last_interaction"] = contact.get("last_contact_date", "")

        return context

    def generate_reply(self, message: str, contact: Optional[dict],
                       classification: dict) -> dict:
        """
        Generate reply for classified message.

        Returns: {reply_text, auto_send, escalate, confidence, intent}
        """
        intent = classification.get("intent", "unknown")
        confidence = classification.get("confidence", 0.0)
        language = classification.get("language", "en")

        # Build context
        ctx = self.build_context(contact, classification)
        name = ctx.get("contact_name") or "Sir/Madam"

        # Determine if we should auto-send or escalate
        auto_send = confidence >= self.confidence_threshold
        escalate = not auto_send and self.escalate_unsure

        # Try AI generation for complex intents
        if intent in ("buyer_inquiry", "seller_offer", "complaint"):
            ai_reply = self._generate_with_ai(message, ctx)
            if ai_reply:
                return {
                    "reply_text": ai_reply,
                    "auto_send": auto_send,
                    "escalate": escalate,
                    "confidence": confidence,
                    "intent": intent,
                }

        # Fallback to template-based replies
        reply = self._template_reply(intent, name, language, ctx)

        return {
            "reply_text": reply,
            "auto_send": auto_send,
            "escalate": escalate,
            "confidence": confidence,
            "intent": intent,
        }

    def _generate_with_ai(self, message: str, context: dict) -> Optional[str]:
        """Generate contextual reply using AI fallback engine (routed to whatsapp_reply)."""
        try:
            from ai_fallback_engine import ask_routed, ask_with_fallback
        except ImportError:
            return None

        name = context.get("contact_name") or "the customer"
        intent = context.get("intent", "")
        lang = context.get("language", "en")

        # Build price context string
        price_info = ""
        prices = context.get("prices", {})
        if isinstance(prices, dict):
            for grade, val in list(prices.items())[:5]:
                if isinstance(val, (int, float)):
                    price_info += f"  {grade}: Rs {val}/MT\n"
                elif isinstance(val, dict):
                    price_info += f"  {grade}: {json.dumps(val)[:80]}\n"

        biz_ctx = context.get("business_context", "")
        lang_label = {"hi": "Hindi (Romanized)", "gu": "Gujarati", "mr": "Marathi",
                      "ta": "Tamil", "te": "Telugu"}.get(lang, "English")

        # Inject segment-specific chatbot script if available
        segment_ctx = ""
        segment = context.get("segment", "")
        if segment:
            try:
                from business_context import get_segment_chatbot_script
                script = get_segment_chatbot_script(segment)
                if script:
                    segment_ctx = "\nSEGMENT-SPECIFIC SCRIPT:\n"
                    for k, v in script.items():
                        segment_ctx += f"  {k}: {v}\n"
            except Exception:
                pass

        prompt = (
            f"You are a sales assistant for PPS Anantam Capital Pvt Ltd (PACPL).\n"
            f"Owner: Prince P Shah (PPS), 24 years exp, Commission Agent.\n"
            f"STRICT RULE: Payment 100% Advance only. NEVER offer credit.\n\n"
            f"{biz_ctx}\n{segment_ctx}\n"
            f"Customer Name: {name}\n"
            f"Segment: {segment or 'unknown'}\n"
            f"Intent: {intent}\n"
            f"Language: {lang_label}\n"
            f"Current Prices:\n{price_info or '  Not available'}\n\n"
            f"Customer Message: \"{message[:500]}\"\n\n"
            f"Write a short, professional WhatsApp reply (max 200 words). "
            f"Use the segment-specific script style and tone if available. "
            f"NEVER offer credit. Always state advance payment. "
            f"Be helpful, include relevant price info if asked. "
            f"If complaint, escalate to PPS sir within 30 minutes. "
            f"If you cannot answer, say you will connect them with our team."
        )

        try:
            try:
                result = ask_routed(prompt, context="", task_type="whatsapp_reply")
            except Exception:
                result = ask_with_fallback(prompt, context="")
            if result.get("error") != "all_failed":
                return result.get("answer", "")[:1000]
        except Exception as e:
            logger.error(f"AI reply generation error: {e}")

        return None

    def _template_reply(self, intent: str, name: str,
                         language: str, context: dict) -> str:
        """Generate template-based reply based on intent and language."""
        if language == "hi":
            return self._template_reply_hi(intent, name, context)
        elif language in ("gu", "mr", "ta", "te"):
            return self._template_reply_regional(intent, name, language, context)
        return self._template_reply_en(intent, name, context)

    def _template_reply_en(self, intent: str, name: str,
                            context: dict) -> str:
        """English template replies."""
        if intent == "buyer_inquiry":
            return (
                f"Dear {name},\n\n"
                f"Thank you for your interest in our bitumen products! "
                f"We offer VG30, VG10, VG40, CRMB-55, CRMB-60, PMB and Emulsion.\n\n"
                f"Please share your requirements (grade, quantity, delivery location) "
                f"and we will send you our best quotation within the hour.\n\n"
                f"Regards,\nPPS Anantam Capital Pvt Ltd"
            )
        elif intent == "price_check":
            return (
                f"Dear {name},\n\n"
                f"Thank you for your price inquiry. Our team will share the "
                f"latest prices for your required grade and location shortly.\n\n"
                f"Please specify the grade (VG30/VG10/VG40/CRMB/PMB) and "
                f"delivery city for accurate pricing.\n\n"
                f"Regards,\nPPS Anantam Capital"
            )
        elif intent == "stock_check":
            return (
                f"Dear {name},\n\n"
                f"Thank you for checking stock availability. We maintain "
                f"regular supplies at all major ports.\n\n"
                f"Please share the grade and quantity needed, and we will "
                f"confirm availability and dispatch timeline.\n\n"
                f"Regards,\nPPS Anantam Capital"
            )
        elif intent == "seller_offer":
            return (
                f"Dear {name},\n\n"
                f"Thank you for your supply offer. Our procurement team "
                f"will review and get back to you shortly.\n\n"
                f"Please share: Grade, Quantity (MT), Origin, FOB/CFR price.\n\n"
                f"Regards,\nPPS Anantam Capital"
            )
        elif intent == "complaint":
            return (
                f"Dear {name},\n\n"
                f"We are sorry to hear about your concern. Your feedback is "
                f"important to us.\n\n"
                f"Our team has been notified and will reach out to you within "
                f"2 hours to resolve this matter.\n\n"
                f"Regards,\nPPS Anantam Capital"
            )
        elif intent == "general":
            return (
                f"Dear {name},\n\n"
                f"Thank you for reaching out to PPS Anantam Capital!\n\n"
                f"How can we assist you today? We deal in all grades of "
                f"bitumen — VG30, VG10, VG40, CRMB, PMB, and Emulsion.\n\n"
                f"Regards,\nPPS Anantam Capital"
            )
        else:
            return (
                f"Dear {name},\n\n"
                f"Thank you for your message. Our team will review and "
                f"respond shortly.\n\n"
                f"Regards,\nPPS Anantam Capital Pvt Ltd"
            )

    def _template_reply_hi(self, intent: str, name: str,
                            context: dict) -> str:
        """Hindi (Romanized) template replies."""
        if intent == "buyer_inquiry":
            return (
                f"Namaste {name} ji,\n\n"
                f"Aapki bitumen ki zarurat ke liye dhanyavaad! "
                f"Hum VG30, VG10, VG40, CRMB, PMB aur Emulsion mein deal karte hain.\n\n"
                f"Kripya apni requirement batayein (grade, quantity, delivery location) "
                f"— hum 1 ghante mein best quotation bhejenge.\n\n"
                f"Dhanyavaad,\nPPS Anantam Capital"
            )
        elif intent == "price_check":
            return (
                f"Namaste {name} ji,\n\n"
                f"Price inquiry ke liye dhanyavaad. Hamari team jaldi hi "
                f"latest rates share karegi.\n\n"
                f"Kripya grade (VG30/VG10/VG40/CRMB/PMB) aur delivery city batayein.\n\n"
                f"Dhanyavaad,\nPPS Anantam Capital"
            )
        elif intent == "general":
            return (
                f"Namaste {name} ji,\n\n"
                f"PPS Anantam Capital mein aapka swagat hai!\n\n"
                f"Aaj hum aapki kya seva kar sakte hain? Hum bitumen ke "
                f"sabhi grades mein deal karte hain.\n\n"
                f"Dhanyavaad,\nPPS Anantam Capital"
            )
        else:
            return (
                f"Namaste {name} ji,\n\n"
                f"Aapke message ke liye dhanyavaad. Hamari team jaldi "
                f"aapse sampark karegi.\n\n"
                f"Dhanyavaad,\nPPS Anantam Capital Pvt Ltd"
            )

    def _template_reply_regional(self, intent: str, name: str,
                                   language: str, context: dict) -> str:
        """Template replies for Gujarati, Marathi, Tamil, Telugu (Romanized)."""
        # Greetings by language
        greetings = {
            "gu": ("Namaskar", "Aabhar", "Tamari"),
            "mr": ("Namaskar", "Dhanyavaad", "Tumchi"),
            "ta": ("Vanakkam", "Nandri", "Ungal"),
            "te": ("Namaskaram", "Dhanyavaadalu", "Mee"),
        }
        hello, thanks, your = greetings.get(language, ("Hello", "Thank you", "Your"))

        if intent == "buyer_inquiry":
            return (
                f"{hello} {name} ji,\n\n"
                f"{thanks}! {your} bitumen requirement ke liye hum ready hain. "
                f"Hum VG30, VG10, VG40, CRMB, PMB aur Emulsion supply karte hain.\n\n"
                f"Please apni requirement batayein — grade, quantity, delivery city.\n"
                f"Hum 1 hour mein best price bhejenge.\n\n"
                f"{thanks},\nPPS Anantam Capital Pvt Ltd"
            )
        elif intent == "price_check":
            return (
                f"{hello} {name} ji,\n\n"
                f"Price enquiry ke liye {thanks.lower()}. "
                f"Hamari team latest rates share karegi.\n\n"
                f"Grade aur city batayein please.\n\n"
                f"{thanks},\nPPS Anantam Capital Pvt Ltd"
            )
        elif intent == "general":
            return (
                f"{hello} {name} ji,\n\n"
                f"PPS Anantam Capital mein aapka swagat hai!\n"
                f"Aaj hum aapki kaise madad kar sakte hain?\n\n"
                f"{thanks},\nPPS Anantam Capital Pvt Ltd"
            )
        else:
            return (
                f"{hello} {name} ji,\n\n"
                f"Aapke message ke liye {thanks.lower()}. "
                f"Hamari team jaldi aapse contact karegi.\n\n"
                f"{thanks},\nPPS Anantam Capital Pvt Ltd"
            )

    def process_incoming_messages(self) -> dict:
        """
        Batch process unhandled incoming WhatsApp messages.

        Returns: {processed, auto_replied, escalated, errors}
        """
        stats = {"processed": 0, "auto_replied": 0, "escalated": 0, "errors": 0}

        if not self._settings.get("ai_auto_reply_enabled", False):
            return {**stats, "status": "disabled"}

        # Get unprocessed incoming messages
        try:
            from database import _get_conn
            conn = _get_conn()
            messages = conn.execute(
                """SELECT * FROM wa_incoming
                   WHERE processed = 0
                   ORDER BY created_at ASC LIMIT 50"""
            ).fetchall()
            if not messages:
                return {**stats, "status": "no_messages"}
            cols = [d[0] for d in conn.execute(
                "SELECT * FROM wa_incoming LIMIT 0").description]
        except Exception:
            # wa_incoming table may not exist yet
            return {**stats, "status": "no_incoming_table"}

        for row_tuple in messages:
            msg = dict(zip(cols, row_tuple))
            text = msg.get("message_text", "")
            from_number = msg.get("from_number", "")

            if not text.strip():
                continue

            stats["processed"] += 1

            try:
                # Look up contact
                contact = self._find_contact(from_number)

                # Classify
                classification = self.classify_message(text, from_number)

                # Generate reply
                reply = self.generate_reply(text, contact, classification)

                if reply.get("auto_send"):
                    # Send auto-reply
                    self._send_reply(from_number, reply["reply_text"],
                                      contact)
                    stats["auto_replied"] += 1
                elif reply.get("escalate"):
                    # Create CRM task for human follow-up
                    self._escalate_to_human(from_number, text,
                                             classification, contact)
                    stats["escalated"] += 1

                # Mark as processed
                try:
                    conn.execute(
                        "UPDATE wa_incoming SET processed = 1 WHERE id = ?",
                        (msg.get("id"),))
                    conn.commit()
                except Exception:
                    pass

            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Process message from {from_number}: {e}")

        return {**stats, "status": "completed"}

    def _find_contact(self, phone_number: str) -> Optional[dict]:
        """Find contact by phone number."""
        try:
            from database import search_contacts
            results = search_contacts(phone_number)
            return results[0] if results else None
        except Exception:
            return None

    def _send_reply(self, to_number: str, reply_text: str,
                     contact: Optional[dict]) -> None:
        """Send auto-reply via WhatsApp."""
        try:
            from whatsapp_engine import WhatsAppEngine
            wa = WhatsAppEngine()
            wa.queue_message(
                to_number=to_number,
                session_text=reply_text,
                message_type="session",
                auto_send=True,
            )
        except Exception as e:
            logger.error(f"Failed to send reply to {to_number}: {e}")

    def _escalate_to_human(self, from_number: str, message: str,
                            classification: dict, contact: Optional[dict]) -> None:
        """Create a CRM task for human follow-up."""
        try:
            from crm_engine import add_task
            name = (contact.get("name") if contact
                    else f"WhatsApp {from_number}")
            note = (
                f"AI Auto-Reply Escalation\n"
                f"From: {from_number}\n"
                f"Intent: {classification.get('intent', '?')} "
                f"(confidence: {classification.get('confidence', 0):.0%})\n"
                f"Message: {message[:300]}"
            )
            add_task(
                client_name=name,
                task_type="Call",
                due_date_str=(datetime.date.today() +
                              datetime.timedelta(days=0)).strftime("%Y-%m-%d"),
                priority="High",
                note=note,
                automated=True,
            )
        except Exception as e:
            logger.error(f"Failed to escalate: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ══════════════════════════════════════════════════════════════════════════════


def get_ai_reply_status() -> dict:
    """Get current AI reply engine status."""
    engine = AIReplyEngine()
    return {
        "enabled": engine._settings.get("ai_auto_reply_enabled", False),
        "confidence_threshold": engine.confidence_threshold,
        "escalate_unsure": engine.escalate_unsure,
        "languages": engine.languages,
    }


def process_pending_replies() -> dict:
    """Process any pending incoming messages (for scheduler)."""
    engine = AIReplyEngine()
    return engine.process_incoming_messages()


def test_classify(text: str) -> dict:
    """Test message classification (for UI testing)."""
    engine = AIReplyEngine()
    return engine.classify_message(text)


def test_reply(text: str, contact_name: str = "") -> dict:
    """Test reply generation (for UI testing)."""
    engine = AIReplyEngine()
    classification = engine.classify_message(text)
    contact = {"name": contact_name} if contact_name else None
    return engine.generate_reply(text, contact, classification)
