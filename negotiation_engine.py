"""
PPS Anantam — Negotiation Assistant Engine v1.0
================================================
AI-powered deal negotiation support.
Prepares complete briefing packs for sales team before customer calls.

Provides:
  - Customer profile summary
  - Best landed cost calculation
  - 3-tier offer pricing
  - Objection handling
  - Competitor comparison
  - Walk-away price
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent


def _fmt_inr(amount) -> str:
    try:
        amount = float(amount)
        integer_part = str(int(abs(amount)))
        if len(integer_part) <= 3:
            formatted = integer_part
        else:
            last3 = integer_part[-3:]
            remaining = integer_part[:-3]
            groups = []
            while remaining:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            formatted = ",".join(groups) + "," + last3
        sign = "-" if amount < 0 else ""
        return f"{sign}\u20b9{formatted}"
    except (ValueError, TypeError):
        return str(amount)


# ─── Objection Library ───────────────────────────────────────────────────────

OBJECTION_LIBRARY = {
    "price_too_high": {
        "objection": "Your price is too high",
        "short_reply": "This is our best landed cost including all charges. Let me break down the cost for you.",
        "detailed_reply": (
            "Our price includes GST, freight, and all handling. When you compare "
            "the total landed cost vs competitors, you'll find we're competitive. "
            "We also offer quality assurance from PSU/verified refineries, "
            "GPS-tracked delivery, and consistent supply."
        ),
        "confidence_booster": (
            "We supply to L&T, Dilip Buildcon, and other Tier-1 contractors. "
            "They trust us for quality and reliability."
        ),
    },
    "competitor_cheaper": {
        "objection": "Your competitor is offering lower",
        "short_reply": "Can you share the rate? Let me compare our landed cost breakdown.",
        "detailed_reply": (
            "Often the quoted rate excludes GST, freight, or handling. "
            "Our rate is fully inclusive. Also verify: Is it from a PSU refinery? "
            "Is it tested/certified? What's the delivery timeline? "
            "We guarantee dispatch within 48 hours."
        ),
        "confidence_booster": "Our supply chain is direct from source — no middleman markup.",
    },
    "payment_terms": {
        "objection": "We need credit terms",
        "short_reply": "We start with advance, and after 2-3 orders, we can discuss PDC/30-day terms.",
        "detailed_reply": (
            "For first orders, 100% advance ensures best pricing. "
            "After building a relationship (2-3 successful orders), "
            "we offer: 50% advance + 50% at delivery, or 30-day credit "
            "with PDC. This protects both sides."
        ),
        "confidence_booster": "Most of our regular customers enjoy flexible terms after initial orders.",
    },
    "quality_concern": {
        "objection": "How can I trust the quality?",
        "short_reply": "All material comes from verified refineries with test certificates.",
        "detailed_reply": (
            "We source from IOCL, BPCL, HPCL, MRPL, and verified import terminals. "
            "Every load comes with: (1) Refinery test certificate, "
            "(2) BIS certification for VG grades, (3) Loading slip with quantity verification. "
            "We can share sample test reports if needed."
        ),
        "confidence_booster": "Zero quality complaints in our supply history.",
    },
    "delivery_delay": {
        "objection": "We need immediate delivery",
        "short_reply": "We dispatch within 48 hours. For urgent orders, 24-hour dispatch is possible.",
        "detailed_reply": (
            "Our standard dispatch is within 48 hours of payment confirmation. "
            "For pre-qualified customers with advance payment, we can do 24-hour dispatch. "
            "We use GPS-tracked tankers so you can monitor delivery in real-time."
        ),
        "confidence_booster": "90%+ on-time delivery rate across all our dispatches.",
    },
    "need_time": {
        "objection": "Let me think about it / Need time",
        "short_reply": "I understand. This rate is valid for 24 hours as crude is volatile.",
        "detailed_reply": (
            "Crude prices change daily, so our pricing is time-bound. "
            "I can hold this rate for 24 hours. If crude moves up tomorrow, "
            "the rate may change. Shall I send you a WhatsApp quote "
            "so you can decide at your convenience?"
        ),
        "confidence_booster": "Many customers appreciate our transparency on pricing validity.",
    },
}


# ─── Negotiation Assistant ───────────────────────────────────────────────────

class NegotiationAssistant:
    """AI-powered deal negotiation support."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()
        self.min_margin = self.settings.get("margin_min_per_mt", 500)

    def prepare_negotiation_brief(self, customer_name: str, city: str,
                                  grade: str = "VG30", quantity_mt: float = 100,
                                  customer_last_price: float = None) -> dict:
        """
        Complete negotiation briefing pack.

        Returns: {
            customer_profile,
            market_context,
            our_best_cost,
            offer_tiers (aggressive/balanced/premium),
            client_benefit_analysis,
            objection_responses,
            walk_away_price,
            closing_strategy
        }
        """
        brief = {
            "generated_at": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
            "customer_name": customer_name,
            "city": city,
            "grade": grade,
            "quantity_mt": quantity_mt,
        }

        # 1. Customer Profile
        brief["customer_profile"] = self._get_customer_profile(customer_name)

        # 2. Best Landed Cost
        cost_data = self._get_best_cost(city, grade)
        brief["our_best_cost"] = cost_data

        # 3. Offer Tiers
        landed = cost_data.get("landed_cost", 0) if cost_data else 0
        if landed > 0:
            brief["offer_tiers"] = self._generate_offers(landed, customer_last_price)
            brief["walk_away_price"] = {
                "price": landed + self.min_margin,
                "label": f"Minimum acceptable: {_fmt_inr(landed + self.min_margin)}/MT",
                "margin": self.min_margin,
            }
        else:
            brief["offer_tiers"] = None
            brief["walk_away_price"] = None

        # 4. Client Benefit
        if customer_last_price and customer_last_price > 0 and landed > 0:
            offer = landed + self.min_margin
            savings = customer_last_price - offer
            benefit_pct = round((savings / customer_last_price) * 100, 1)
            brief["client_benefit"] = {
                "last_price": customer_last_price,
                "our_offer": offer,
                "savings_per_mt": round(savings, 2),
                "benefit_pct": benefit_pct,
                "total_savings": round(savings * quantity_mt, 2),
                "narrative": (
                    f"Customer saves {_fmt_inr(savings)}/MT ({benefit_pct}%) "
                    f"vs their last purchase of {_fmt_inr(customer_last_price)}/MT. "
                    f"Total savings on {quantity_mt:.0f} MT = {_fmt_inr(savings * quantity_mt)}."
                ) if savings > 0 else (
                    f"Our offer is {_fmt_inr(abs(savings))}/MT above customer's last price. "
                    f"Justify with quality, reliability, and delivery speed."
                )
            }
        else:
            brief["client_benefit"] = None

        # 5. Objection Handling (top 3 most likely)
        brief["objection_handling"] = self._get_likely_objections(customer_name, city)

        # 6. Market Context
        brief["market_context"] = self._get_market_context()

        # 7. Closing Strategy
        brief["closing_strategy"] = self._get_closing_strategy(brief)

        return brief

    def _get_customer_profile(self, customer_name: str) -> dict:
        """Fetch customer intelligence."""
        try:
            from database import get_all_customers
            customers = get_all_customers()
            for c in customers:
                if c.get("name", "").lower() == customer_name.lower():
                    return {
                        "name": c.get("name"),
                        "city": c.get("city"),
                        "category": c.get("category"),
                        "relationship": c.get("relationship_stage", "unknown"),
                        "last_price": c.get("last_purchase_price"),
                        "last_date": c.get("last_purchase_date"),
                        "monthly_demand": c.get("expected_monthly_demand"),
                        "credit_terms": c.get("credit_terms"),
                        "outstanding": c.get("outstanding_inr", 0),
                    }
        except Exception:
            pass

        # Fallback: check customers DB (Phase 1 — was sales_parties.json)
        try:
            from customer_source import load_customers
            parties = load_customers()
            for p in parties:
                if p.get("name", "").lower() == customer_name.lower():
                    return {
                        "name": p.get("name"),
                        "city": p.get("city"),
                        "category": p.get("category"),
                        "relationship": "unknown",
                    }
        except Exception:
            pass

        return {"name": customer_name, "relationship": "new"}

    def _get_best_cost(self, city: str, grade: str) -> dict:
        """Get best landed cost for city."""
        try:
            from calculation_engine import BitumenCalculationEngine
            calc = BitumenCalculationEngine()
            sources = calc.find_best_sources(city, grade=grade, top_n=3)
            if sources:
                best = sources[0]
                return {
                    "source": best.get("source"),
                    "source_type": best.get("source_type"),
                    "base_price": best.get("base_price"),
                    "distance_km": best.get("distance_km"),
                    "freight": best.get("freight"),
                    "landed_cost": best.get("landed_cost"),
                    "alternatives": sources[1:3],
                }
        except Exception:
            pass

        # Fallback estimate
        return {
            "source": "Market average",
            "landed_cost": 42000,
            "note": "Using estimated market average. Update live prices for accuracy."
        }

    def _generate_offers(self, landed_cost: float, customer_last_price: float = None) -> dict:
        """Generate 3-tier offer prices."""
        try:
            from calculation_engine import BitumenCalculationEngine
            calc = BitumenCalculationEngine()
            return calc.generate_offer_prices(landed_cost, customer_last_price)
        except Exception:
            pass

        # Manual calculation
        aggressive = landed_cost + self.min_margin
        balanced = landed_cost + self.min_margin * 1.6
        premium = landed_cost + self.min_margin * 2.4
        return {
            "aggressive": {"price": round(aggressive), "margin": self.min_margin, "label": "Best Price"},
            "balanced": {"price": round(balanced), "margin": round(self.min_margin * 1.6), "label": "Recommended"},
            "premium": {"price": round(premium), "margin": round(self.min_margin * 2.4), "label": "Premium"},
        }

    def _get_likely_objections(self, customer_name: str, city: str) -> list:
        """Return top 3 most likely objections with responses."""
        # Default likely objections for new customers
        likely_keys = ["price_too_high", "payment_terms", "need_time"]

        return [
            {
                "objection": OBJECTION_LIBRARY[k]["objection"],
                "short_reply": OBJECTION_LIBRARY[k]["short_reply"],
                "detailed_reply": OBJECTION_LIBRARY[k]["detailed_reply"],
                "confidence_booster": OBJECTION_LIBRARY[k]["confidence_booster"],
            }
            for k in likely_keys
            if k in OBJECTION_LIBRARY
        ]

    def _get_market_context(self) -> dict:
        """Get current market snapshot for negotiation context."""
        context = {
            "brent_usd": None,
            "usdinr": None,
            "trend": "stable",
            "narrative": "",
        }
        try:
            crude_data = json.loads((BASE / "tbl_crude_prices.json").read_text(encoding="utf-8"))
            if crude_data:
                latest = [r for r in crude_data if r.get("benchmark") == "Brent"]
                if latest:
                    context["brent_usd"] = latest[-1].get("price")

            fx_data = json.loads((BASE / "tbl_fx_rates.json").read_text(encoding="utf-8"))
            if fx_data:
                latest_fx = [r for r in fx_data if "USD" in str(r.get("from_currency", ""))]
                if latest_fx:
                    context["usdinr"] = latest_fx[-1].get("rate")
        except Exception:
            pass

        brent = context["brent_usd"]
        usdinr = context["usdinr"]
        if brent:
            if brent > 80:
                context["trend"] = "rising"
                context["narrative"] = (
                    f"Crude at ${brent}/bbl (above ₹ 80 resistance). "
                    f"Bitumen prices likely to firm up. Good time for customer to lock price."
                )
            elif brent < 70:
                context["trend"] = "falling"
                context["narrative"] = (
                    f"Crude at ${brent}/bbl (below ₹ 70). "
                    f"Prices may soften further but current offer is competitive."
                )
            else:
                context["trend"] = "stable"
                context["narrative"] = (
                    f"Crude at ${brent}/bbl (stable range). "
                    f"Good time for steady procurement."
                )

        return context

    def _get_closing_strategy(self, brief: dict) -> dict:
        """Recommend closing approach based on brief data."""
        strategies = []

        # Value close — lead with savings if available (most compelling)
        if brief.get("client_benefit") and brief["client_benefit"].get("savings_per_mt", 0) > 0:
            savings = brief["client_benefit"]["savings_per_mt"]
            strategies.append({
                "technique": "Value Close",
                "script": f"You save {_fmt_inr(savings)}/MT — that's real money on every load.",
            })

        # Urgency close
        strategies.append({
            "technique": "Time Urgency",
            "script": f"This rate is valid for {self.settings.get('quote_validity_hours', 24)} hours only as crude is volatile.",
        })

        # Relationship close
        strategies.append({
            "technique": "Relationship Start",
            "script": "Start with a trial order. If satisfied, we build long-term partnership with better terms.",
        })

        # Fear of missing out
        strategies.append({
            "technique": "FOMO",
            "script": "We have limited availability at this rate. Other contractors are already confirming.",
        })

        return {
            "recommended": strategies[0] if strategies else None,
            "alternatives": strategies[1:],
        }


def get_full_objection_library() -> dict:
    """Return the complete objection library for UI display."""
    return OBJECTION_LIBRARY
