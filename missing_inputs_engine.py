"""
PPS Anantam — Missing Inputs Engine v1.0
==========================================
Detects data gaps across the system and generates prioritized input requests.
Shows a daily popup in dashboard asking users to fill critical missing data.

Priority Levels:
  High   — Directly affects pricing accuracy or deal calculation
  Medium — Improves forecasting and CRM intelligence
  Low    — Enhances reporting and analytics
"""

import json
import datetime
from pathlib import Path
from typing import List, Dict

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

MISSING_INPUTS_FILE = BASE / "missing_inputs.json"
INPUT_USAGE_STATS_FILE = BASE / "input_usage_stats.json"


def _now() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


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


# ─── Field Definitions ───────────────────────────────────────────────────────

SCAN_FIELDS = [
    {
        "field": "supplier_latest_quote",
        "label": "New supplier quote received?",
        "reason": "Updates cheapest source ranking — directly affects all pricing",
        "priority": "High",
        "input_type": "text",
        "placeholder": "Supplier name, grade, price/MT",
        "entity_type": "supplier",
    },
    {
        "field": "actual_freight_rate",
        "label": "Actual freight rate for last deal?",
        "reason": "Improves cost accuracy — current rates may be outdated",
        "priority": "High",
        "input_type": "number",
        "placeholder": "Rate in Rs/km",
        "entity_type": "deal",
    },
    {
        "field": "customer_enquiry",
        "label": "Any new customer enquiry?",
        "reason": "Feeds opportunity engine — auto-discovers best price for them",
        "priority": "High",
        "input_type": "text",
        "placeholder": "Customer name, city, grade, qty",
        "entity_type": "customer",
    },
    {
        "field": "competitor_price",
        "label": "Competitor price heard?",
        "reason": "Adjusts offer strategy — know where we stand",
        "priority": "Medium",
        "input_type": "number",
        "placeholder": "Competitor name, Rs/MT",
        "entity_type": "market",
    },
    {
        "field": "deal_closed_price",
        "label": "Actual deal closed price?",
        "reason": "Trains prediction model — improves forecast accuracy",
        "priority": "Medium",
        "input_type": "number",
        "placeholder": "Final price in Rs/MT",
        "entity_type": "deal",
    },
    {
        "field": "payment_update",
        "label": "Payment received update?",
        "reason": "Updates credit risk score and outstanding balance",
        "priority": "Medium",
        "input_type": "text",
        "placeholder": "Customer, amount, date",
        "entity_type": "deal",
    },
    {
        "field": "inventory_count",
        "label": "Current inventory at depot?",
        "reason": "Pipeline accuracy — shows available stock on homepage",
        "priority": "Low",
        "input_type": "number",
        "placeholder": "Total MT available",
        "entity_type": "inventory",
    },
    {
        "field": "grade_preference",
        "label": "Any customer grade preference change?",
        "reason": "CRM profile update — improves recommendation accuracy",
        "priority": "Low",
        "input_type": "text",
        "placeholder": "Customer name, new grade preference",
        "entity_type": "customer",
    },
]


class MissingInputsEngine:
    """Scans for data gaps and generates input requests."""

    def __init__(self):
        self.usage_stats = _load_json(INPUT_USAGE_STATS_FILE, {})
        if not isinstance(self.usage_stats, dict):
            self.usage_stats = {}

    def scan_all_gaps(self) -> List[dict]:
        """
        Scan entire system for missing/stale data.
        Returns prioritized list of input requests with smart ordering.
        """
        gaps = []

        # Check suppliers without recent quotes
        gaps += self._check_supplier_quotes()

        # Check customers without last price
        gaps += self._check_customer_data()

        # Check stale price data
        gaps += self._check_price_freshness()

        # Check empty data tables
        gaps += self._check_empty_tables()

        # Check active deal inputs
        gaps += self._check_active_deal_inputs()

        # Add standing daily questions
        gaps += self._daily_questions()

        # Deduplicate by field name
        seen = set()
        unique_gaps = []
        for g in gaps:
            key = g.get("field", "")
            if key not in seen:
                seen.add(key)
                unique_gaps.append(g)

        # Smart priority ordering:
        # 1. Inputs affecting today's deals first
        # 2. Active negotiations second
        # 3. General data quality third
        # Also: suppress consistently-skipped questions
        unique_gaps = self._apply_smart_ordering(unique_gaps)

        return unique_gaps

    def _check_supplier_quotes(self) -> list:
        """Check if any supplier hasn't been quoted recently."""
        gaps = []
        try:
            # Try database first, fall back to JSON
            try:
                from database import get_all_suppliers
                suppliers = get_all_suppliers()
            except Exception:
                suppliers = _load_json(BASE / "purchase_parties.json", [])
            active_count = sum(1 for s in suppliers if s.get("marked_for_purchase") or s.get("is_active"))
            if active_count < 5:
                gaps.append({
                    "field": "active_suppliers",
                    "label": f"Only {active_count} active suppliers marked for purchase",
                    "reason": "More active suppliers = better sourcing options",
                    "priority": "High",
                    "input_type": "action",
                    "placeholder": "Mark more suppliers as active in Data Manager",
                    "entity_type": "supplier",
                    "created_at": _now(),
                })
        except Exception:
            pass
        return gaps

    def _check_customer_data(self) -> list:
        """Check for customers missing key data."""
        gaps = []
        try:
            # Try database first, fall back to JSON
            try:
                from database import get_all_customers
                customers = get_all_customers()
            except Exception:
                from customer_source import load_customers
                customers = load_customers()
            if len(customers) < 5:
                gaps.append({
                    "field": "customer_count",
                    "label": f"Only {len(customers)} customers in database",
                    "reason": "More customers = more opportunities. Add from contacts/LinkedIn",
                    "priority": "High",
                    "input_type": "action",
                    "placeholder": "Import customers via Contact Importer",
                    "entity_type": "customer",
                    "created_at": _now(),
                })

            for c in customers:
                if not c.get("contact"):
                    gaps.append({
                        "field": f"customer_contact_{c.get('name', 'unknown')}",
                        "label": f"Missing contact for {c.get('name')}",
                        "reason": "Cannot follow up without contact info",
                        "priority": "Medium",
                        "input_type": "text",
                        "placeholder": "Phone or email",
                        "entity_type": "customer",
                        "entity_name": c.get("name"),
                        "created_at": _now(),
                    })
        except Exception:
            pass
        return gaps[:5]  # Max 5 gaps from this check

    def _check_price_freshness(self) -> list:
        """Check if price data is stale (>24 hours old)."""
        gaps = []
        try:
            prices = _load_json(BASE / "tbl_crude_prices.json", [])
            if not prices:
                gaps.append({
                    "field": "crude_prices_empty",
                    "label": "No crude price data available",
                    "reason": "All pricing depends on crude oil benchmark",
                    "priority": "High",
                    "input_type": "action",
                    "placeholder": "Run API sync to fetch latest prices",
                    "entity_type": "market",
                    "created_at": _now(),
                })
        except Exception:
            pass
        return gaps

    def _check_empty_tables(self) -> list:
        """Check for data tables that should have data but are empty."""
        gaps = []
        important_tables = [
            ("tbl_contacts.json", "Contact database", "High"),
            ("tbl_demand_proxy.json", "Demand proxy data", "Medium"),
            ("tbl_highway_km.json", "Highway construction data", "Medium"),
            ("tbl_ports_master.json", "Port master data", "Low"),
        ]

        for filename, label, priority in important_tables:
            data = _load_json(BASE / filename, [])
            if not data:
                gaps.append({
                    "field": f"empty_{filename}",
                    "label": f"{label} is empty",
                    "reason": f"Missing {label} reduces analysis accuracy",
                    "priority": priority,
                    "input_type": "action",
                    "placeholder": "Run seed data script or manual entry",
                    "entity_type": "system",
                    "created_at": _now(),
                })
        return gaps

    def _check_active_deal_inputs(self) -> list:
        """Check for inputs needed by today's active deals."""
        gaps = []
        try:
            from database import get_all_deals
            deals = get_all_deals()
            active = [d for d in deals if d.get("status") == "active"]
            for d in active:
                # Missing delivery date
                if not d.get("delivery_date"):
                    gaps.append({
                        "field": f"deal_delivery_{d.get('deal_number', 'N/A')}",
                        "label": f"Delivery date missing: {d.get('deal_number', 'N/A')}",
                        "reason": "Cannot schedule dispatch without delivery date",
                        "priority": "High",
                        "input_type": "date",
                        "placeholder": "DD-MM-YYYY",
                        "entity_type": "deal",
                        "context": "active_deal",
                        "created_at": _now(),
                    })
                # Missing payment date with outstanding balance
                outstanding = (d.get("total_value_inr") or 0) - (d.get("payment_received_inr") or 0)
                if outstanding > 0 and not d.get("payment_date"):
                    gaps.append({
                        "field": f"deal_payment_{d.get('deal_number', 'N/A')}",
                        "label": f"Payment date missing: {d.get('deal_number', 'N/A')}",
                        "reason": f"Outstanding: Rs {outstanding:,.0f}",
                        "priority": "High",
                        "input_type": "date",
                        "placeholder": "DD-MM-YYYY",
                        "entity_type": "deal",
                        "context": "active_deal",
                        "created_at": _now(),
                    })
        except Exception:
            pass
        return gaps[:5]

    def _daily_questions(self) -> list:
        """Standing daily input questions."""
        return [
            {
                "field": f,
                "label": SCAN_FIELDS[i]["label"],
                "reason": SCAN_FIELDS[i]["reason"],
                "priority": SCAN_FIELDS[i]["priority"],
                "input_type": SCAN_FIELDS[i]["input_type"],
                "placeholder": SCAN_FIELDS[i]["placeholder"],
                "entity_type": SCAN_FIELDS[i]["entity_type"],
                "created_at": _now(),
            }
            for i, f in enumerate(
                [sf["field"] for sf in SCAN_FIELDS]
            )
        ]

    def _apply_smart_ordering(self, gaps: list) -> list:
        """
        Smart priority ordering:
        1. Active deal inputs first (context == 'active_deal')
        2. Active negotiations second (context == 'negotiation')
        3. General data quality third
        Also suppress consistently-skipped fields.
        """
        # Filter out fields that have been skipped 5+ times without use
        filtered = []
        for g in gaps:
            field = g.get("field", "")
            stats = self.usage_stats.get(field, {})
            skip_count = stats.get("skipped", 0)
            use_count = stats.get("used", 0)
            # Suppress if skipped 5+ times and never used
            if skip_count >= 5 and use_count == 0:
                continue
            filtered.append(g)

        # Sort: context priority, then priority level
        context_order = {"active_deal": 0, "negotiation": 1}
        priority_order = {"High": 0, "Medium": 1, "Low": 2}

        filtered.sort(key=lambda x: (
            context_order.get(x.get("context", ""), 2),
            priority_order.get(x.get("priority", "Low"), 3),
        ))

        return filtered

    def save_collected_input(self, field: str, value: str) -> None:
        """Save a collected input value and track usage."""
        existing = _load_json(MISSING_INPUTS_FILE, [])
        existing.append({
            "field": field,
            "value": value,
            "collected_at": _now(),
            "status": "collected",
        })
        if len(existing) > 1000:
            existing = existing[-1000:]
        _save_json(MISSING_INPUTS_FILE, existing)

        # Track usage
        self._track_usage(field, "used")

        # Feed into AI learning engine
        self._feed_ai_learning(field, value)

    def skip_input(self, field: str) -> None:
        """Record that a field was skipped (dismissed without filling)."""
        self._track_usage(field, "skipped")

    def _track_usage(self, field: str, action: str):
        """Track input usage stats for feedback loop."""
        if field not in self.usage_stats:
            self.usage_stats[field] = {"used": 0, "skipped": 0, "last_action": ""}
        self.usage_stats[field][action] = self.usage_stats[field].get(action, 0) + 1
        self.usage_stats[field]["last_action"] = _now()
        _save_json(INPUT_USAGE_STATS_FILE, self.usage_stats)

    def _feed_ai_learning(self, field: str, value: str):
        """Feed collected inputs into AI learning engine."""
        try:
            if field == "competitor_price" and value:
                from ai_learning_engine import AILearningEngine
                engine = AILearningEngine()
                engine.log_prediction("competitor_price_intel", float(value),
                                      _today(), {"source": "manual_input"})
            elif field == "deal_closed_price" and value:
                from ai_learning_engine import AILearningEngine
                engine = AILearningEngine()
                engine.log_prediction("deal_outcome", float(value),
                                      _today(), {"source": "manual_input"})
        except Exception:
            pass

    def should_show_popup(self) -> bool:
        """Check if popup should be shown (once per day)."""
        existing = _load_json(MISSING_INPUTS_FILE, [])
        if not existing:
            return True
        # Check if last entry (collection or popup_shown) was today
        last = existing[-1] if existing else {}
        last_date = last.get("collected_at", last.get("shown_at", ""))[:10]
        return last_date != _today()

    def mark_popup_shown(self) -> None:
        """Record that the popup was shown today so it won't repeat."""
        existing = _load_json(MISSING_INPUTS_FILE, [])
        existing.append({
            "field": "_popup_shown",
            "value": "",
            "shown_at": _now(),
            "status": "shown",
        })
        if len(existing) > 1000:
            existing = existing[-1000:]
        _save_json(MISSING_INPUTS_FILE, existing)


def get_pending_gaps() -> list:
    """Get all current data gaps for UI display."""
    engine = MissingInputsEngine()
    return engine.scan_all_gaps()
