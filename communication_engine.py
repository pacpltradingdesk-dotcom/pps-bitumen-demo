"""
PPS Anantam — Communication Hub Engine v1.0
=============================================
Auto-generates WhatsApp, Email, and Call scripts for sales team.
Templates are market-intelligent — prices, savings, and context auto-populated.

Communication Types:
  - offer: New pricing offer
  - followup: Deal follow-up
  - reactivation: Re-engage cold customer
  - tender_response: Tender/bid communication
  - payment_reminder: Payment follow-up
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytz

try:
    from business_context import (
        get_segment_info, get_segment_chatbot_script,
        get_payment_policy, get_segment_for_category,
    )
except ImportError:
    get_segment_info = None
    get_segment_chatbot_script = None
    get_payment_policy = None
    get_segment_for_category = None

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

COMM_LOG_FILE = BASE / "communication_log.json"


def _now() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def _fmt_inr(amount) -> str:
    """Format INR with Indian comma system."""
    if amount is None:
        return "N/A"
    try:
        amount = float(amount)
        if amount < 0:
            return f"-{_fmt_inr(-amount)}"
        s = f"{amount:,.0f}"
        integer_part = s.replace(",", "")
        if len(integer_part) <= 3:
            return f"\u20b9{integer_part}"
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        return f"\u20b9{','.join(groups)},{last3}"
    except (ValueError, TypeError):
        return str(amount)


def _load_json(path, default=None):
    if default is None:
        default = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# COMMUNICATION HUB
# ─────────────────────────────────────────────────────────────────────────────

class CommunicationHub:
    """WhatsApp, Email, and Call script generator for bitumen sales."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()
        self.company = "PPS Anantam"
        self.validity_hours = self.settings.get("quote_validity_hours", 24)
        self.payment_terms = self.settings.get("payment_default_terms", "100% Advance")

    # ─── WhatsApp Templates ──────────────────────────────────────────────────

    def whatsapp_offer(self, customer_name: str, city: str, grade: str,
                       quantity_mt: float, price_per_mt: float,
                       source: str = "", benefit_pct: float = 0) -> str:
        """Generate WhatsApp offer message."""
        benefit_line = ""
        if benefit_pct > 0:
            benefit_line = f"\nYour Benefit: *{benefit_pct}% cheaper* than market\n"

        return (
            f"*BITUMEN OFFER \u2014 {_today()}*\n"
            f"\ud83c\udfe2 {customer_name} | {city}\n"
            f"\n"
            f"\ud83c\udfd7\ufe0f Grade: *{grade}*\n"
            f"\ud83d\udce6 Qty: *{quantity_mt:.0f} MT*\n"
            f"\ud83d\udcb0 Rate: *{_fmt_inr(price_per_mt)}/MT* (Landed {city})\n"
            f"{benefit_line}"
            f"\n"
            f"\ud83d\ude9a Dispatch: Within 48 hours\n"
            f"\u23f3 Validity: {self.validity_hours} hours only\n"
            f"\ud83d\udcb3 Payment: {self.payment_terms}\n"
            f"\n"
            f"Reply *CONFIRM* to lock this price\n"
            f"\n"
            f"\u2014 {self.company}"
        )

    def whatsapp_followup(self, customer_name: str, reference: str = "",
                          days_since: int = 1) -> str:
        """Generate WhatsApp follow-up message."""
        return (
            f"Dear {customer_name},\n\n"
            f"Following up on our bitumen offer"
            f"{f' ({reference})' if reference else ''}.\n\n"
            f"The rate shared is still valid. Would you like to proceed?\n\n"
            f"We can dispatch within 48 hours of confirmation.\n\n"
            f"Please let us know.\n"
            f"\u2014 {self.company}"
        )

    def whatsapp_reactivation(self, customer_name: str, city: str,
                              new_price: float, old_price: float,
                              savings: float) -> str:
        """Generate WhatsApp message for reactivating cold customer."""
        return (
            f"Dear {customer_name},\n\n"
            f"Market prices have come down significantly.\n\n"
            f"We can now offer *VG-30 at {_fmt_inr(new_price)}/MT* landed {city}.\n"
            f"Your last rate was {_fmt_inr(old_price)}/MT.\n"
            f"\ud83d\udcb0 *You save {_fmt_inr(savings)}/MT*\n\n"
            f"This is a limited-time opportunity.\n"
            f"Reply *YES* for a formal quote.\n\n"
            f"\u2014 {self.company}"
        )

    def whatsapp_payment_reminder(self, customer_name: str, amount: float,
                                  invoice_ref: str = "", days_overdue: int = 0) -> str:
        """Generate WhatsApp payment reminder."""
        urgency = "Gentle reminder" if days_overdue < 7 else "Urgent request"
        return (
            f"Dear {customer_name},\n\n"
            f"{urgency}: Payment of {_fmt_inr(amount)} is pending"
            f"{f' ({days_overdue} days overdue)' if days_overdue > 0 else ''}.\n"
            f"{f'Ref: {invoice_ref}' if invoice_ref else ''}\n\n"
            f"Please arrange at the earliest.\n\n"
            f"Bank: ICICI Bank\n"
            f"A/C: 184105001402\n"
            f"IFSC: ICIC0001841\n\n"
            f"Thank you.\n"
            f"\u2014 {self.company}"
        )

    # ─── Email Templates ─────────────────────────────────────────────────────

    def email_offer(self, customer_name: str, city: str, grade: str,
                    quantity_mt: float, price_per_mt: float,
                    source: str = "", benefit_pct: float = 0) -> Dict[str, str]:
        """Generate email offer with subject + body."""
        subject = f"Bitumen {grade} Offer \u2014 {_fmt_inr(price_per_mt)}/MT Landed {city} | {self.company}"

        body = (
            f"Dear {customer_name},\n\n"
            f"We are pleased to offer the following bitumen supply for your {city} operations:\n\n"
            f"OFFER DETAILS:\n"
            f"  Product:     Bitumen {grade}\n"
            f"  Quantity:    {quantity_mt:.0f} MT\n"
            f"  Rate:        {_fmt_inr(price_per_mt)} per MT (Landed {city})\n"
            f"  Source:      {source if source else 'Best available'}\n"
            f"  HSN Code:    27132000\n"
            f"  GST:         18% (included in above rate)\n\n"
        )

        if benefit_pct > 0:
            body += f"  YOUR BENEFIT: {benefit_pct}% below current market rates\n\n"

        body += (
            f"TERMS & CONDITIONS:\n"
            f"  1. Payment:    {self.payment_terms}\n"
            f"  2. Dispatch:   Within 48 hours of payment realization\n"
            f"  3. Validity:   {self.validity_hours} hours from this email\n"
            f"  4. Delivery:   Ex-Terminal basis; freight included in above rate\n"
            f"  5. Transit:    Risk passes to buyer after loading\n"
            f"  6. Disputes:   Subject to Vadodara jurisdiction\n\n"
            f"Please confirm at your earliest to lock this rate.\n\n"
            f"Best regards,\n"
            f"PPS Anantam Corporation Pvt. Ltd.\n"
            f"Vadodara, Gujarat\n"
            f"GST: 24AAHCV1611L2ZD"
        )

        return {"subject": subject, "body": body}

    def email_followup(self, customer_name: str, original_date: str = "",
                       price: float = 0, city: str = "") -> Dict[str, str]:
        """Generate email follow-up."""
        subject = f"Follow-up: Bitumen Offer for {city} | {self.company}"
        body = (
            f"Dear {customer_name},\n\n"
            f"This is a follow-up to our bitumen offer"
            f"{f' dated {original_date}' if original_date else ''}.\n\n"
        )
        if price > 0:
            body += f"The offered rate of {_fmt_inr(price)}/MT is still available.\n\n"
        body += (
            f"We would appreciate your confirmation or any feedback.\n\n"
            f"Looking forward to your response.\n\n"
            f"Best regards,\n"
            f"{self.company}"
        )
        return {"subject": subject, "body": body}

    def email_reactivation(self, customer_name: str, city: str,
                           new_price: float, old_price: float,
                           savings: float) -> Dict[str, str]:
        """Generate reactivation email with price comparison."""
        subject = f"Prices Down! Bitumen VG30 at {_fmt_inr(new_price)}/MT for {city} | {self.company}"
        body = (
            f"Dear {customer_name},\n\n"
            f"We hope this finds you well. We noticed it's been a while since our last transaction "
            f"and wanted to share some excellent news.\n\n"
            f"Market prices have come down significantly:\n\n"
            f"  Your last rate:   {_fmt_inr(old_price)}/MT\n"
            f"  New offer rate:   {_fmt_inr(new_price)}/MT (Landed {city})\n"
            f"  YOUR SAVINGS:     {_fmt_inr(savings)}/MT\n\n"
            f"This is a limited-time opportunity as crude prices remain volatile.\n\n"
            f"We can dispatch within 48 hours of confirmation. Minimum order: 20 MT.\n\n"
            f"Looking forward to resuming our association.\n\n"
            f"Best regards,\n"
            f"PPS Anantam Corporation Pvt. Ltd.\n"
            f"Vadodara, Gujarat\n"
            f"GST: 24AAHCV1611L2ZD"
        )
        return {"subject": subject, "body": body}

    def email_payment_reminder(self, customer_name: str, amount: float,
                               invoice_ref: str = "", days_overdue: int = 0) -> Dict[str, str]:
        """Generate payment reminder email."""
        urgency = "Gentle Reminder" if days_overdue < 7 else "Urgent: Payment Overdue"
        subject = f"{urgency} — {_fmt_inr(amount)} Pending | {self.company}"
        body = (
            f"Dear {customer_name},\n\n"
            f"This is a {'gentle reminder' if days_overdue < 7 else 'follow-up'} regarding "
            f"the outstanding payment of {_fmt_inr(amount)}"
            f"{f' ({days_overdue} days overdue)' if days_overdue > 0 else ''}.\n"
        )
        if invoice_ref:
            body += f"\nInvoice Reference: {invoice_ref}\n"
        body += (
            f"\nKindly arrange the payment at your earliest convenience.\n\n"
            f"BANK DETAILS:\n"
            f"  Bank:    ICICI Bank\n"
            f"  A/C No:  184105001402\n"
            f"  IFSC:    ICIC0001841\n"
            f"  Name:    PPS Anantam Corporation Pvt. Ltd.\n\n"
            f"If the payment has already been made, please disregard this email "
            f"and share the transaction reference for our records.\n\n"
            f"Thank you for your prompt attention.\n\n"
            f"Best regards,\n"
            f"{self.company}"
        )
        return {"subject": subject, "body": body}

    def email_tender_response(self, authority_name: str, tender_ref: str,
                              grade: str, quantity_mt: float,
                              price_per_mt: float, delivery_location: str) -> Dict[str, str]:
        """Generate formal tender/bid response email."""
        subject = f"Bid Submission — {tender_ref} | Bitumen {grade} | {self.company}"
        body = (
            f"To,\n"
            f"The Procurement Officer,\n"
            f"{authority_name}\n\n"
            f"Subject: Bid Submission for {tender_ref}\n\n"
            f"Dear Sir/Madam,\n\n"
            f"With reference to your tender {tender_ref}, we are pleased to submit "
            f"our bid for the supply of bitumen as follows:\n\n"
            f"BID DETAILS:\n"
            f"  Product:        Bitumen {grade}\n"
            f"  Quantity:        {quantity_mt:.0f} MT\n"
            f"  Unit Rate:       {_fmt_inr(price_per_mt)} per MT\n"
            f"  Total Value:     {_fmt_inr(price_per_mt * quantity_mt)}\n"
            f"  HSN Code:        27132000\n"
            f"  GST:             18%\n"
            f"  Delivery:        {delivery_location}\n"
            f"  Dispatch:        Within 7 working days of PO\n\n"
            f"COMPANY DETAILS:\n"
            f"  Name:    PPS Anantam Corporation Pvt. Ltd.\n"
            f"  Address: Vadodara, Gujarat\n"
            f"  GST:     24AAHCV1611L2ZD\n\n"
            f"We confirm full compliance with the tender terms and conditions.\n\n"
            f"Thanking you,\n"
            f"For PPS Anantam Corporation Pvt. Ltd."
        )
        return {"subject": subject, "body": body}

    def email_director_report_template(self, briefing: dict) -> Dict[str, str]:
        """Generate HTML-formatted director daily report email."""
        yesterday = briefing.get("yesterday_summary", {})
        today_actions = briefing.get("today_actions", {})
        outlook = briefing.get("outlook", {})

        subject = f"Daily Intelligence Report — {briefing.get('date', _today())} | {self.company}"

        body = (
            f"DAILY INTELLIGENCE REPORT — {briefing.get('date', _today())}\n"
            f"{'=' * 50}\n\n"
            f"YESTERDAY SUMMARY:\n"
            f"  Deals Closed:        {yesterday.get('deals_closed', 0)}\n"
            f"  New Enquiries:       {yesterday.get('new_enquiries', 0)}\n"
            f"  Comms Sent:          {yesterday.get('communications_sent', 0)}\n"
            f"  Payments Received:   {_fmt_inr(yesterday.get('payments_received', 0))}\n"
            f"  Outstanding:         {_fmt_inr(yesterday.get('total_outstanding', 0))}\n\n"
            f"TODAY'S ACTIONS:\n"
        )
        for buyer in today_actions.get("buyers_to_call", [])[:5]:
            body += f"  - Call: {buyer.get('name', 'N/A')} ({buyer.get('city', '')})\n"
        for fu in today_actions.get("followups_due", [])[:5]:
            body += f"  - Follow-up: {fu.get('customer_name', fu.get('name', 'N/A'))}\n"

        if outlook:
            body += (
                f"\n15-DAY OUTLOOK:\n"
                f"  Demand Score:    {outlook.get('demand_score', {}).get('total', 'N/A')}/100\n"
                f"  Price Direction: {outlook.get('price_direction', {}).get('direction', 'N/A')}\n"
                f"  Strategy:        {outlook.get('stock_strategy', {}).get('action', 'N/A')}\n"
            )

        body += (
            f"\n{'=' * 50}\n"
            f"Generated by PPS Anantam Agentic AI Eco System\n"
            f"Vadodara, Gujarat | GST: 24AAHCV1611L2ZD"
        )
        return {"subject": subject, "body": body}

    def email_weekly_summary_template(self, summary: dict) -> Dict[str, str]:
        """Generate weekly summary email."""
        subject = f"Weekly Business Summary — {summary.get('week', _today())} | {self.company}"
        body = (
            f"WEEKLY BUSINESS SUMMARY\n"
            f"{'=' * 50}\n"
            f"Week: {summary.get('week', _today())}\n\n"
            f"DEAL PERFORMANCE:\n"
            f"  Total Deals:       {summary.get('total_deals', 0)}\n"
            f"  Revenue:           {_fmt_inr(summary.get('total_revenue', 0))}\n"
            f"  Avg Margin/MT:     {_fmt_inr(summary.get('avg_margin_per_mt', 0))}\n\n"
            f"MARKET MOVEMENT:\n"
            f"  Brent (Start):     ${summary.get('brent_start', 0):.2f}\n"
            f"  Brent (End):       ${summary.get('brent_end', 0):.2f}\n"
            f"  USD/INR:           {summary.get('fx_rate', 0):.2f}\n\n"
            f"CRM ACTIVITY:\n"
            f"  Communications:    {summary.get('total_comms', 0)}\n"
            f"  New Customers:     {summary.get('new_customers', 0)}\n"
            f"  Followups Done:    {summary.get('followups_done', 0)}\n\n"
            f"{'=' * 50}\n"
            f"Generated by PPS Anantam Agentic AI Eco System"
        )
        return {"subject": subject, "body": body}

    # ─── Call Scripts ────────────────────────────────────────────────────────

    def call_script_offer(self, customer_name: str, city: str, grade: str,
                          price: float, source: str = "",
                          savings: float = 0) -> str:
        """Generate structured call script for new offer."""
        objection_handling = (
            '   Price too high:\n'
            '     "This is our best landed cost including freight and GST. '
            'Compare with your current supplier\'s all-inclusive rate."\n\n'
            '   Need time to decide:\n'
            '     "I understand. However, this rate is valid for 24 hours only '
            'as crude prices are volatile. Shall I hold it for you?"\n\n'
            '   Competitor is cheaper:\n'
            '     "Could you share their rate? We can match or explain '
            'the quality/reliability difference."\n\n'
            '   Payment terms:\n'
            '     "Our standard is advance payment. For trusted partners, '
            'we can discuss 50-50 or PDC terms after 2-3 successful orders."'
        )

        result = (
            f"=== CALL SCRIPT: {customer_name} ({city}) ===\n\n"
            f"1. OPENING (30 sec):\n"
            f'   "Hello {customer_name}, this is [Your Name] from PPS Anantam, Vadodara. '
            f'How are you?"\n\n'
            f"2. MARKET CONTEXT (1 min):\n"
            f'   "I am calling because crude prices have moved favorably and we have '
            f'a very competitive {grade} rate available for {city} delivery."\n\n'
            f"3. OUR OFFER (1 min):\n"
            f'   "We can deliver {grade} at {_fmt_inr(price)} per MT landed {city}. '
            f'Source: {source if source else "our terminal"}."\n'
        )
        if savings > 0:
            result += (
                f'   "This is {_fmt_inr(savings)} per MT below current market rates."\n'
            )
        result += (
            f"\n4. HANDLE OBJECTIONS:\n{objection_handling}\n\n"
            f"5. CLOSE (30 sec):\n"
            f'   "Shall I send you a formal quotation on WhatsApp right now? '
            f'I can also prepare a detailed cost breakdown if needed."\n\n'
            f"6. NEXT STEPS:\n"
            f"   - If YES: Send WhatsApp quote immediately\n"
            f"   - If MAYBE: Schedule callback in 2 hours\n"
            f"   - If NO: Note reason, follow up in 1 week\n"
            f"=== END SCRIPT ==="
        )
        return result

    # ─── Segment-Specific Templates ──────────────────────────────────────────

    def whatsapp_offer_segmented(self, customer_name: str, city: str,
                                  grade: str, quantity_mt: float,
                                  price_per_mt: float, segment: str = "",
                                  source: str = "", benefit_pct: float = 0) -> str:
        """Generate segment-aware WhatsApp offer (Hindi/Gujarati/English)."""
        seg_info = get_segment_info(segment) if get_segment_info else None
        if not seg_info:
            return self.whatsapp_offer(customer_name, city, grade,
                                       quantity_mt, price_per_mt, source, benefit_pct)

        style = seg_info.get("communication_style", "formal_english")

        if "gujarati" in style:
            return self._wa_offer_gujarati(customer_name, city, grade,
                                           quantity_mt, price_per_mt, source)
        elif "hindi" in style or style == "casual_hindi":
            return self._wa_offer_hindi(customer_name, city, grade,
                                        quantity_mt, price_per_mt, source)
        # Default: English template
        return self.whatsapp_offer(customer_name, city, grade,
                                   quantity_mt, price_per_mt, source, benefit_pct)

    def _wa_offer_hindi(self, customer_name: str, city: str, grade: str,
                         quantity_mt: float, price_per_mt: float,
                         source: str = "") -> str:
        """Hindi WhatsApp offer for traders/contractors/transporters."""
        return (
            f"*BITUMEN OFFER — {_today()}*\n"
            f"🙏 Namaste {customer_name} ji,\n\n"
            f"Aaj ka best rate:\n"
            f"🏗️ Grade: *{grade}*\n"
            f"📦 Qty: *{quantity_mt:.0f} MT*\n"
            f"💰 Rate: *{_fmt_inr(price_per_mt)}/MT*"
            f"{f' (Landed {city})' if city else ''}\n"
            f"{f'📍 Source: {source}' + chr(10) if source else ''}"
            f"\n"
            f"🚚 Dispatch: 48 ghante mein\n"
            f"⏳ Rate validity: Sirf {self.validity_hours} ghante\n"
            f"💳 Payment: {self.payment_terms} (Advance only)\n\n"
            f"Rate lock karne ke liye *CONFIRM* reply karein\n\n"
            f"— PACPL | {self.company}\n"
            f"📞 +91 7795242424"
        )

    def _wa_offer_gujarati(self, customer_name: str, city: str, grade: str,
                            quantity_mt: float, price_per_mt: float,
                            source: str = "") -> str:
        """Gujarati WhatsApp offer for decanters/local buyers."""
        return (
            f"*BITUMEN OFFER — {_today()}*\n"
            f"🙏 Kem cho {customer_name} bhai,\n\n"
            f"Aaj no best rate:\n"
            f"🏗️ Grade: *{grade}*\n"
            f"📦 Qty: *{quantity_mt:.0f} MT*\n"
            f"💰 Rate: *{_fmt_inr(price_per_mt)}/MT*"
            f"{f' (Landed {city})' if city else ''}\n"
            f"{f'📍 Source: {source}' + chr(10) if source else ''}"
            f"\n"
            f"🚚 Dispatch: 48 kalak ma\n"
            f"⏳ Rate validity: Fakat {self.validity_hours} kalak\n"
            f"💳 Payment: {self.payment_terms} (Advance only)\n\n"
            f"Rate lock karva *CONFIRM* reply karo\n\n"
            f"— PACPL | {self.company}\n"
            f"📞 +91 7795242424"
        )

    def email_offer_segmented(self, customer_name: str, city: str, grade: str,
                               quantity_mt: float, price_per_mt: float,
                               segment: str = "", source: str = "",
                               benefit_pct: float = 0) -> Dict[str, str]:
        """Generate segment-aware email offer with bank details."""
        base = self.email_offer(customer_name, city, grade, quantity_mt,
                                price_per_mt, source, benefit_pct)

        # Append bank details from payment policy
        bank = {}
        if get_payment_policy:
            policy = get_payment_policy()
            bank = policy.get("bank_details_for_templates", {})

        bank_section = (
            f"\n\nBANK DETAILS FOR PAYMENT:\n"
            f"  Bank:      {bank.get('bank_name', 'ICICI Bank')}\n"
            f"  A/C No:    {bank.get('ac_no', '184105001402')}\n"
            f"  IFSC:      {bank.get('ifsc', 'ICIC0001841')}\n"
            f"  Name:      PPS Anantam Corporation Pvt. Ltd.\n"
            f"  Branch:    {bank.get('branch', 'Vadodara')}\n"
        )

        # Segment-specific closing
        seg_info = get_segment_info(segment) if get_segment_info else None
        if seg_info:
            style = seg_info.get("communication_style", "")
            if "hindi" in style:
                bank_section += "\nAapke vyapar ke liye dhanyavaad.\n"
            elif "gujarati" in style:
                bank_section += "\nTamara vyapar mate aabhar.\n"

        base["body"] = base["body"] + bank_section
        return base

    def call_script_segmented(self, customer_name: str, city: str, grade: str,
                               price: float, segment: str = "",
                               source: str = "", savings: float = 0) -> str:
        """Generate segment-specific call script with tailored objection handling."""
        seg_info = get_segment_info(segment) if get_segment_info else None
        script = get_segment_chatbot_script(segment) if get_segment_chatbot_script else None

        if not seg_info or not script:
            return self.call_script_offer(customer_name, city, grade,
                                          price, source, savings)

        label = seg_info.get("label", segment.replace("_", " ").title())
        style = seg_info.get("communication_style", "formal_english")

        # Opening based on communication style
        if "hindi" in style:
            opening = (
                f'   "Namaste {customer_name} ji, main Prince bol raha hoon '
                f'PPS Anantam / PACPL se, Vadodara se. Kaise hain aap?"'
            )
        elif "gujarati" in style:
            opening = (
                f'   "Kem cho {customer_name} bhai, hu Prince bolun chhu '
                f'PPS Anantam / PACPL thi, Vadodara thi. Kem chho?"'
            )
        else:
            opening = (
                f'   "Hello {customer_name}, this is Prince from PPS Anantam / PACPL, '
                f'Vadodara. How are you?"'
            )

        # Credit objection — STRICT NO CREDIT
        credit_objection = script.get("objection_credit",
            '"Sorry sir, hamari policy 100% Advance hai. Ek baar payment aaye, '
            '48 ghante mein material dispatch."')

        result = (
            f"=== CALL SCRIPT: {customer_name} ({city}) — {label} ===\n\n"
            f"1. OPENING (30 sec):\n{opening}\n\n"
            f"2. QUALIFICATION (1 min):\n"
            f"   {script.get('qualification', 'Ask about current requirement and volume.')}\n\n"
            f"3. PITCH (1.5 min):\n"
            f"   {script.get('pitch', f'We offer {grade} at competitive rates.')}\n"
            f'   "Rate: {_fmt_inr(price)} per MT landed {city}.'
            f'{f" Source: {source}." if source else ""}"\n'
        )
        if savings > 0:
            result += f'   "Yeh market se {_fmt_inr(savings)}/MT sasta hai."\n'

        result += (
            f"\n4. HANDLE OBJECTIONS:\n"
            f"   Price too high:\n"
            f'     "Sir, yeh all-inclusive landed rate hai — freight + GST sab included. '
            f'Apne current supplier ka total cost compare karein."\n\n'
            f"   Need credit:\n"
            f"     {credit_objection}\n\n"
            f"   Competitor cheaper:\n"
            f'     "Unka rate batayein, hum match karenge ya quality/reliability ka '
            f'difference explain karenge."\n\n'
            f"5. CLOSE (30 sec):\n"
            f"   {script.get('close', 'Shall I send a formal quote on WhatsApp?')}\n\n"
            f"6. NEXT STEPS:\n"
            f"   - If YES: Send WhatsApp quote immediately\n"
            f"   - If MAYBE: Schedule callback in 2 hours\n"
            f"   - If NO: Note reason, follow up in 1 week\n"
            f"=== END SCRIPT ==="
        )
        return result

    # ─── Follow-up Sequence Generator ────────────────────────────────────────

    def generate_followup_sequence(self, customer_name: str, city: str,
                                   price: float, grade: str = "VG30") -> List[dict]:
        """
        Generate 5-touch follow-up plan.

        Returns list of {day, channel, action, template_type}
        """
        return [
            {
                "day": 0,
                "channel": "WhatsApp",
                "action": f"Send initial offer to {customer_name}",
                "template_type": "offer",
                "status": "pending"
            },
            {
                "day": 1,
                "channel": "Call",
                "action": f"Follow-up call to {customer_name}",
                "template_type": "call_followup",
                "status": "pending"
            },
            {
                "day": 3,
                "channel": "Email",
                "action": f"Email with market update to {customer_name}",
                "template_type": "email_followup",
                "status": "pending"
            },
            {
                "day": 7,
                "channel": "WhatsApp",
                "action": f"WhatsApp check-in with {customer_name}",
                "template_type": "whatsapp_followup",
                "status": "pending"
            },
            {
                "day": 14,
                "channel": "WhatsApp",
                "action": f"New offer if price changed for {customer_name}",
                "template_type": "offer_refresh",
                "status": "pending"
            },
        ]

    # ─── CRM Automation Templates ────────────────────────────────────────────

    def whatsapp_festival_greeting(self, name: str, festival: str,
                                    language: str = "en") -> str:
        """Generate festival greeting for WhatsApp broadcast."""
        if language == "hi":
            return (
                f"🙏 Namaste {name} ji,\n\n"
                f"🎉 {festival} ki hardik shubhkamnayein!\n\n"
                f"{self.company} ki taraf se aapko aur aapke parivaar ko "
                f"{festival} ki dheron shubhkamnayein. 🪔✨\n\n"
                f"Aapke vyapar mein vriddhi aur samriddhi ki kamna karte hain.\n\n"
                f"🏢 {self.company}\nVadodara, Gujarat"
            )
        return (
            f"🙏 Dear {name},\n\n"
            f"🎉 Wishing you a very Happy {festival}!\n\n"
            f"May this festive season bring prosperity and success to "
            f"your business and happiness to your family. 🪔✨\n\n"
            f"Warm regards,\n🏢 {self.company}\nVadodara, Gujarat"
        )

    def email_festival_greeting(self, name: str, festival: str,
                                 language: str = "en") -> dict:
        """Generate festival greeting email. Returns {subject, body}."""
        subject = f"Happy {festival}! — Best Wishes from {self.company}"
        if language == "hi":
            body = (
                f"Respected {name} ji,\n\n"
                f"{festival} ki hardik shubhkamnayein!\n\n"
                f"{self.company} ki sampurna team ki or se aapko aur aapke "
                f"parivaar ko {festival} ki dheron shubhkamnayein.\n\n"
                f"Hum aapke saath vyaparik sambandh ko bahut mahatva dete hain "
                f"aur aane wale samay mein aur behtar seva dene ke liye tatpar hain.\n\n"
                f"Sadar,\n{self.company}\nVadodara, Gujarat"
            )
        else:
            body = (
                f"Dear {name},\n\n"
                f"On behalf of the entire team at {self.company}, "
                f"we wish you and your family a very Happy {festival}!\n\n"
                f"We value our business relationship with you and look forward "
                f"to continuing to serve your bitumen requirements with the "
                f"best quality and competitive pricing.\n\n"
                f"May this festive season bring prosperity and growth to your business.\n\n"
                f"Warm regards,\n{self.company}\nVadodara, Gujarat"
            )
        return {"subject": subject, "body": body}

    def whatsapp_price_update(self, name: str, grade: str,
                               old_price: float, new_price: float,
                               city: str = "") -> str:
        """Generate price update WhatsApp message."""
        direction = "📈 Increased" if new_price > old_price else "📉 Decreased"
        change = abs(new_price - old_price)
        pct = (change / old_price * 100) if old_price else 0
        loc = f" ({city})" if city else ""

        return (
            f"🔔 *PRICE UPDATE*{loc}\n\n"
            f"Dear {name},\n\n"
            f"*{grade}* price has {direction.lower()}:\n"
            f"  Old: {_fmt_inr(old_price)}/MT\n"
            f"  New: {_fmt_inr(new_price)}/MT\n"
            f"  Change: {direction} by {_fmt_inr(change)} ({pct:.1f}%)\n\n"
            f"📞 Contact us for best deals!\n"
            f"🏢 {self.company}"
        )

    def email_price_update(self, name: str,
                            prices: list[dict]) -> dict:
        """Generate price update email. prices: [{grade, old, new, city}]."""
        subject = f"Bitumen Price Update — {_today()} | {self.company}"
        lines = [f"Dear {name},\n",
                 "Please find the latest bitumen price updates:\n"]

        for p in prices:
            grade = p.get("grade", "")
            old_p = p.get("old", 0)
            new_p = p.get("new", 0)
            city = p.get("city", "")
            direction = "UP" if new_p > old_p else "DOWN"
            change = abs(new_p - old_p)
            lines.append(
                f"  {grade} ({city}): {_fmt_inr(old_p)} → {_fmt_inr(new_p)} "
                f"({direction} {_fmt_inr(change)})"
            )

        lines.extend([
            "",
            "Please contact us for competitive quotations on all grades.",
            "",
            f"Best regards,",
            f"{self.company}",
            "Vadodara, Gujarat",
        ])
        return {"subject": subject, "body": "\n".join(lines)}

    # ─── Communication Logging ───────────────────────────────────────────────

    def log_communication(self, customer_name: str, channel: str,
                          template_type: str, content_preview: str = "") -> None:
        """Log a sent communication."""
        log = _load_json(COMM_LOG_FILE, [])
        log.append({
            "customer_name": customer_name,
            "channel": channel,
            "template_type": template_type,
            "content_preview": content_preview[:200],
            "sent_at": _now(),
            "status": "sent"
        })
        if len(log) > 5000:
            log = log[-5000:]
        _save_json(COMM_LOG_FILE, log)

    def get_communication_history(self, customer_name: str = None,
                                  limit: int = 50) -> list:
        """Get communication log, optionally filtered by customer."""
        log = _load_json(COMM_LOG_FILE, [])
        if customer_name:
            log = [l for l in log if l.get("customer_name") == customer_name]
        return log[-limit:]


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE (for rotation_engine / price_watch_engine)
# ══════════════════════════════════════════════════════════════════════════════

_hub = None

def _get_hub() -> CommunicationHub:
    global _hub
    if _hub is None:
        _hub = CommunicationHub()
    return _hub


def generate_outreach_message(name: str, company: str, channel: str,
                               segment: str = "", city: str = "") -> str:
    """Generate a daily outreach message for rotation engine (segment-aware)."""
    hub = _get_hub()
    display_name = name or company or "Sir/Madam"
    if channel == "whatsapp":
        if segment:
            return hub.whatsapp_offer_segmented(
                customer_name=display_name, grade="VG30",
                price_per_mt=0, city=city, quantity_mt=0, segment=segment)
        return hub.whatsapp_offer(customer_name=display_name, grade="VG30",
                                   price_per_mt=0, city="", quantity_mt=0)
    elif channel == "email":
        if segment:
            result = hub.email_offer_segmented(
                customer_name=display_name, grade="VG30",
                price_per_mt=0, city=city, quantity_mt=0, segment=segment)
        else:
            result = hub.email_offer(customer_name=display_name, grade="VG30",
                                      price_per_mt=0, city="", quantity_mt=0)
        return result.get("body", "")
    return ""


def generate_festival_greeting(name: str, festival: str,
                                language: str = "en",
                                channel: str = "whatsapp") -> str:
    """Generate festival greeting for rotation engine."""
    hub = _get_hub()
    if channel == "whatsapp":
        return hub.whatsapp_festival_greeting(name, festival, language)
    elif channel == "email":
        result = hub.email_festival_greeting(name, festival, language)
        return result.get("body", "")
    return ""


def generate_price_update_message(name: str, grade: str,
                                   old_price: float, new_price: float,
                                   city: str = "",
                                   channel: str = "whatsapp") -> str:
    """Generate price update message for price_watch_engine."""
    hub = _get_hub()
    if channel == "whatsapp":
        return hub.whatsapp_price_update(name, grade, old_price, new_price, city)
    elif channel == "email":
        result = hub.email_price_update(name, [{"grade": grade, "old": old_price,
                                                 "new": new_price, "city": city}])
        return result.get("body", "")
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# AI CALLING STUB (Placeholder for VAPI / Bland.ai / Exotel)
# ══════════════════════════════════════════════════════════════════════════════


def initiate_ai_call(contact: dict, script: str,
                     language: str = "en") -> dict:
    """
    Placeholder for AI-powered calling.

    When a provider (VAPI/Bland/Exotel) is configured, this will:
    1. Generate a conversation script using business_context
    2. Initiate an outbound call via the provider API
    3. Record the call outcome in CRM

    Returns: {status, message, provider, call_id}
    """
    try:
        from settings_engine import load_settings
        settings = load_settings()
        if not settings.get("ai_calling_enabled", False):
            return {"status": "disabled", "message": "AI calling not enabled in settings"}

        provider = settings.get("ai_calling_provider", "none")
        if provider == "none":
            return {"status": "not_configured",
                    "message": "No AI calling provider selected. "
                               "Configure in Settings > AI Calling (VAPI/Bland/Exotel)."}
    except Exception:
        pass

    return {
        "status": "not_implemented",
        "message": "AI calling provider integration coming soon. "
                   "Configure your preferred provider (VAPI/Bland.ai/Exotel) "
                   "in Settings to enable automated calls.",
        "provider": "none",
        "call_id": None,
    }


def generate_rate_card_message():
    """Generate a WhatsApp-ready rate card message with today's prices."""
    import json
    import os
    import datetime

    base_dir = os.path.dirname(os.path.abspath(__file__))
    today = datetime.date.today().strftime("%d %b %Y")

    # Load live prices
    rates = {}
    try:
        with open(os.path.join(base_dir, "live_prices.json"), "r") as f:
            lp = json.load(f)
        rates = {
            "VG30 Bulk": lp.get("DRUM_KANDLA_VG30", 35500) - 2000,
            "VG30 Drum": lp.get("DRUM_KANDLA_VG30", 35500),
            "VG10 Bulk": lp.get("DRUM_MUMBAI_VG10", 38000) - 2000,
            "VG10 Drum": lp.get("DRUM_MUMBAI_VG10", 38000),
        }
    except Exception:
        rates = {"VG30 Bulk": 34000, "VG30 Drum": 36000, "VG10 Bulk": 35000, "VG10 Drum": 37000}

    # Format rates
    rate_lines = ""
    for grade, price in rates.items():
        rate_lines += f"{grade}: ₹{price:,}/MT\n"

    msg = f"""PPS Anantams - Today's Rates
━━━━━━━━━━━━━━━━━━━
📅 {today}

{rate_lines}━━━━━━━━━━━━━━━━━━━
100% Advance | 24hr Validity
Ex-Terminal | GST 18% Extra

📞 Call: +91 7795242424
💬 WhatsApp: wa.me/917795242424
━━━━━━━━━━━━━━━━━━━
PPS Anantams Corporation Pvt Ltd
Vadodara, Gujarat"""

    return msg


def get_rate_card_wa_link():
    """Get a wa.me link with pre-filled rate card message."""
    import urllib.parse
    msg = generate_rate_card_message()
    encoded = urllib.parse.quote(msg)
    return f"https://wa.me/?text={encoded}"
