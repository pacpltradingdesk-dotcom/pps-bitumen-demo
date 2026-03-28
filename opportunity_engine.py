"""
PPS Anantam — Opportunity Discovery Engine v1.0
=================================================
Auto-discovers profitable opportunities from market changes.
Runs daily via sync_engine + on-demand.

Opportunity Types:
  1. price_drop_reactivation — Old customers become profitable at new prices
  2. new_viable_city — New cities become viable due to cost changes
  3. cheapest_route_change — Best supplier/port shifted
  4. tender_match — New tenders matching our capabilities
"""

import json
import datetime
from pathlib import Path
from typing import List, Dict, Optional

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

OPPORTUNITIES_FILE = BASE / "opportunities.json"


def _now_ist() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


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
# OPPORTUNITY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class OpportunityEngine:
    """Auto-discovers profitable opportunities from market changes."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()
        self.min_margin = self.settings.get("margin_min_per_mt", 500)

    def scan_all_opportunities(self) -> List[dict]:
        """Master scanner — runs daily + on price change."""
        opportunities = []
        opportunities += self._scan_price_drop_reactivations()
        opportunities += self._scan_new_viable_cities()
        opportunities += self._scan_cheapest_route_changes()
        opportunities += self._scan_tender_matches()

        # Save to file with deduplication
        existing = _load_json(OPPORTUNITIES_FILE, [])
        # Build set of existing keys (type + customer_name + customer_city) to avoid duplicates
        existing_keys = set()
        for ex in existing:
            key = (ex.get("type", ""), ex.get("customer_name", ""), ex.get("customer_city", ""))
            existing_keys.add(key)
        # Only add truly new opportunities
        for opp in opportunities:
            key = (opp.get("type", ""), opp.get("customer_name", ""), opp.get("customer_city", ""))
            if key not in existing_keys:
                existing.append(opp)
                existing_keys.add(key)
        # Keep max 1000
        if len(existing) > 1000:
            existing = existing[-1000:]
        _save_json(OPPORTUNITIES_FILE, existing)

        return opportunities

    def _scan_price_drop_reactivations(self) -> List[dict]:
        """
        When price drops >5%, find old customers who were lost due to price.

        Logic:
        1. Get current landed cost for each city
        2. Compare with each customer's last_purchase_price
        3. If new_landed + margin < customer_last_price -> OPPORTUNITY
        4. Rank by margin potential
        """
        opportunities = []
        try:
            from calculation_engine import BitumenCalculationEngine
            calc = BitumenCalculationEngine()

            # Load customers from database or JSON fallback
            customers = self._load_customers()

            for cust in customers:
                cust_name = cust.get("name", "Unknown")
                last_price = cust.get("last_purchase_price") or cust.get("last_deal_price")
                city = cust.get("city", "")
                if not last_price or not city or last_price <= 0:
                    continue

                # Get current best landed cost for this city
                try:
                    sources = calc.find_best_sources(city, grade="VG30", load_type="Bulk", top_n=1)
                    if not sources:
                        continue
                    best = sources[0]
                    current_landed = best.get("landed_cost", 0)
                except Exception:
                    continue

                # Check if we can now offer better price than their last purchase
                offer_price = current_landed + self.min_margin
                if offer_price < last_price:
                    savings = round(last_price - offer_price, 2)
                    margin = round(offer_price - current_landed, 2)
                    benefit_pct = round((savings / last_price) * 100, 1)

                    opp = {
                        "type": "price_drop_reactivation",
                        "title": f"Reactivate {cust_name} — Save {_fmt_inr(savings)}/MT",
                        "description": (
                            f"Current landed cost to {city}: {_fmt_inr(current_landed)}/MT. "
                            f"Customer's last price: {_fmt_inr(last_price)}/MT. "
                            f"We can offer {_fmt_inr(offer_price)}/MT with {_fmt_inr(margin)}/MT margin. "
                            f"Customer saves {benefit_pct}%."
                        ),
                        "customer_name": cust_name,
                        "customer_city": city,
                        "estimated_margin_per_mt": margin,
                        "estimated_volume_mt": cust.get("avg_monthly_demand_mt", 100),
                        "estimated_value_inr": round(offer_price * cust.get("avg_monthly_demand_mt", 100), 2),
                        "trigger_reason": "Price change makes customer profitable again",
                        "old_landed_cost": last_price,
                        "new_landed_cost": current_landed,
                        "savings_per_mt": savings,
                        "recommended_action": f"Call {cust_name}, offer {_fmt_inr(offer_price)}/MT landed {city}",
                        "best_source": best.get("source", ""),
                        "priority": "P0" if savings > 1000 else "P1" if savings > 500 else "P2",
                        "status": "new",
                        "valid_until": (datetime.datetime.now(IST) + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
                        "created_at": _now_ist(),
                    }

                    # Generate communication templates
                    try:
                        templates = self.generate_communication(opp)
                        opp.update(templates)
                    except Exception:
                        pass

                    opportunities.append(opp)

        except Exception:
            pass

        # Sort by savings (highest first)
        opportunities.sort(key=lambda x: x.get("savings_per_mt", 0), reverse=True)
        return opportunities[:20]  # Top 20

    def _scan_new_viable_cities(self) -> List[dict]:
        """
        When freight or base price changes, new cities may become viable.

        Logic:
        1. For each major city in India
        2. Calculate current landed cost
        3. If landed_cost + margin < typical market rate -> NEW MARKET opportunity
        """
        opportunities = []
        try:
            from calculation_engine import BitumenCalculationEngine
            calc = BitumenCalculationEngine()

            # Major cities to check
            cities = [
                "Ahmedabad", "Mumbai", "Delhi", "Chennai", "Kolkata",
                "Hyderabad", "Bengaluru", "Pune", "Jaipur", "Lucknow",
                "Indore", "Bhopal", "Vadodara", "Surat", "Nagpur",
                "Patna", "Ranchi", "Bhubaneswar", "Guwahati", "Chandigarh",
                "Visakhapatnam", "Kochi", "Mangalore", "Raipur", "Dehradun"
            ]

            # Typical market rate benchmark (average bitumen rate in India)
            market_rate = 45000  # ₹/MT approximate

            for city in cities:
                try:
                    sources = calc.find_best_sources(city, grade="VG30", load_type="Bulk", top_n=1)
                    if not sources:
                        continue
                    best = sources[0]
                    landed = best.get("landed_cost", 0)
                    if landed <= 0:
                        continue

                    offer = landed + self.min_margin
                    if offer < market_rate * 0.95:  # 5% below market
                        savings = round(market_rate - offer, 2)
                        opportunities.append({
                            "type": "new_viable_city",
                            "title": f"New Market: {city} — {_fmt_inr(savings)}/MT below market",
                            "description": (
                                f"Best source for {city}: {best['source']} at {_fmt_inr(landed)}/MT landed. "
                                f"Market rate ~{_fmt_inr(market_rate)}/MT. "
                                f"Opportunity to enter at {_fmt_inr(offer)}/MT."
                            ),
                            "customer_city": city,
                            "best_source": best.get("source", ""),
                            "estimated_margin_per_mt": self.min_margin,
                            "new_landed_cost": landed,
                            "savings_per_mt": savings,
                            "priority": "P1",
                            "status": "new",
                            "created_at": _now_ist(),
                        })
                except Exception:
                    continue

        except Exception:
            pass

        return opportunities[:10]

    def _scan_cheapest_route_changes(self) -> List[dict]:
        """
        When source prices change, the cheapest supplier/port may shift.
        Compare current best source vs last known best for each destination.
        """
        opportunities = []
        try:
            from calculation_engine import BitumenCalculationEngine
            calc = BitumenCalculationEngine()

            # Load active customer destinations
            customers = self._load_customers()
            seen_cities = set()

            for cust in customers:
                city = cust.get("city", "")
                if not city or city in seen_cities:
                    continue
                seen_cities.add(city)

                try:
                    sources = calc.find_best_sources(city, grade="VG30", top_n=3)
                    if len(sources) >= 2:
                        best = sources[0]
                        second = sources[1]
                        savings = round(second["landed_cost"] - best["landed_cost"], 2)

                        if savings > 200:  # Meaningful savings
                            opportunities.append({
                                "type": "cheapest_route_change",
                                "title": f"Route Optimization: {city} — Save {_fmt_inr(savings)}/MT",
                                "description": (
                                    f"Best source: {best['source']} at {_fmt_inr(best['landed_cost'])}/MT. "
                                    f"Next best: {second['source']} at {_fmt_inr(second['landed_cost'])}/MT. "
                                    f"Savings: {_fmt_inr(savings)}/MT."
                                ),
                                "customer_city": city,
                                "best_source": best.get("source", ""),
                                "new_landed_cost": best.get("landed_cost", 0),
                                "old_landed_cost": second.get("landed_cost", 0),
                                "savings_per_mt": savings,
                                "priority": "P2",
                                "status": "new",
                                "created_at": _now_ist(),
                            })
                except Exception:
                    continue

        except Exception:
            pass

        return opportunities[:10]

    def _scan_tender_matches(self) -> List[dict]:
        """Match new tenders/projects from directory with our capabilities."""
        opportunities = []
        try:
            dir_orgs = _load_json(BASE / "tbl_dir_orgs.json", [])
            for org in dir_orgs[:20]:  # Check recent entries
                if org.get("category", "").lower() in ["nhai", "state highway", "pwd"]:
                    opportunities.append({
                        "type": "tender_match",
                        "title": f"Tender: {org.get('name', 'Unknown')} — {org.get('state', '')}",
                        "description": (
                            f"Organization: {org.get('name')}. "
                            f"State: {org.get('state', '')}. "
                            f"Category: {org.get('category', '')}. "
                            f"Potential bitumen demand for road projects."
                        ),
                        "customer_city": org.get("city", ""),
                        "priority": "P1",
                        "status": "new",
                        "created_at": _now_ist(),
                    })
        except Exception:
            pass

        return opportunities[:5]

    def _load_customers(self) -> list:
        """Load customers from database or JSON fallback."""
        try:
            from database import get_all_customers
            return get_all_customers()
        except Exception:
            pass
        # Fallback to JSON
        return _load_json(BASE / "sales_parties.json", [])

    def generate_communication(self, opportunity: dict) -> dict:
        """Auto-generate WhatsApp, Email, Call script for an opportunity."""
        cust_name = opportunity.get("customer_name", "Sir/Madam")
        city = opportunity.get("customer_city", "your city")
        savings = opportunity.get("savings_per_mt", 0)
        new_price = opportunity.get("new_landed_cost", 0) + self.min_margin
        source = opportunity.get("best_source", "our terminal")

        whatsapp = (
            f"*BITUMEN OFFER — {datetime.datetime.now(IST).strftime('%Y-%m-%d')}*\n"
            f"Dear {cust_name},\n\n"
            f"Grade: VG-30 Bulk\n"
            f"Rate: {_fmt_inr(new_price)}/MT (Landed {city})\n"
            f"Source: {source}\n\n"
            f"Your Benefit: Save {_fmt_inr(savings)}/MT vs market\n\n"
            f"Dispatch: Within 48 hours\n"
            f"Validity: 24 hours only\n\n"
            f"Reply *CONFIRM* to lock this price\n\n"
            f"— PPS Anantam"
        )

        email_subject = f"Special Bitumen Offer — {_fmt_inr(new_price)}/MT Landed {city}"
        email_body = (
            f"Dear {cust_name},\n\n"
            f"We have a competitive bitumen offer for your {city} operations:\n\n"
            f"Product: Bitumen VG-30 (Bulk)\n"
            f"Rate: {_fmt_inr(new_price)} per MT (Landed {city})\n"
            f"Source: {source}\n"
            f"Your Savings: {_fmt_inr(savings)} per MT compared to prevailing rates\n\n"
            f"Terms:\n"
            f"  - Payment: 100% Advance\n"
            f"  - Dispatch: Within 48 hours of payment\n"
            f"  - Validity: 24 hours from this email\n"
            f"  - GST: 18% as applicable\n\n"
            f"Please confirm at your earliest to lock this price.\n\n"
            f"Best regards,\n"
            f"PPS Anantam\n"
            f"Vadodara, Gujarat"
        )

        call_script = (
            f"--- CALL SCRIPT ---\n"
            f"1. OPENING (30 sec):\n"
            f'   "Hello {cust_name}, this is [Name] from PPS Anantam. How are you?"\n\n'
            f"2. MARKET CONTEXT (1 min):\n"
            f'   "I\'m calling because crude prices have moved favorably and we have a very '
            f'competitive rate available for {city} delivery."\n\n'
            f"3. OUR OFFER (1 min):\n"
            f'   "We can deliver VG-30 at {_fmt_inr(new_price)} per MT landed {city}. '
            f'This is {_fmt_inr(savings)} below the current market rate. '
            f'Source: {source}."\n\n'
            f"4. HANDLE OBJECTIONS:\n"
            f'   If "Price too high": "This is our best landed cost. The saving vs market is {_fmt_inr(savings)}/MT."\n'
            f'   If "Need time": "This rate is valid for 24 hours only as crude is volatile."\n'
            f'   If "Competitor cheaper": "Can you share the rate? We match or explain the difference."\n\n'
            f"5. CLOSE (30 sec):\n"
            f'   "Shall I send you a formal quotation on WhatsApp right now?"'
        )

        return {
            "whatsapp_template": whatsapp,
            "email_template": email_body,
            "email_subject": email_subject,
            "call_script": call_script,
        }

    def get_todays_recommendations(self) -> dict:
        """
        AI-selected target lists for today.

        Returns: {
            buyers_to_call: top 10 by opportunity score,
            suppliers_to_negotiate: top 5 by price advantage,
            followups_due: overdue tasks,
            reactivation_targets: cold customers with new opportunity
        }
        """
        opportunities = _load_json(OPPORTUNITIES_FILE, [])
        new_opps = [o for o in opportunities if o.get("status") == "new"]

        # Buyers to call (from reactivation opportunities)
        buyers_to_call = [
            o for o in new_opps
            if o.get("type") == "price_drop_reactivation"
        ][:10]

        # Reactivation targets
        reactivation_targets = [
            o for o in new_opps
            if o.get("type") in ("price_drop_reactivation", "new_viable_city")
        ][:5]

        # Load CRM tasks for followups
        followups_due = []
        try:
            tasks = _load_json(BASE / "crm_tasks.json", [])
            followups_due = [
                t for t in tasks
                if t.get("status") == "Pending"
            ][:10]
        except Exception:
            pass

        return {
            "buyers_to_call": buyers_to_call,
            "suppliers_to_negotiate": [],  # Populated when supplier deals tracked
            "followups_due": followups_due,
            "reactivation_targets": reactivation_targets,
            "total_new_opportunities": len(new_opps),
        }


def get_all_opportunities(status: str = None) -> list:
    """Load all opportunities, optionally filtered by status."""
    opps = _load_json(OPPORTUNITIES_FILE, [])
    if status:
        opps = [o for o in opps if o.get("status") == status]
    return opps


def mark_opportunity_status(index: int, new_status: str) -> bool:
    """Update opportunity status (new -> contacted -> converted -> expired)."""
    opps = _load_json(OPPORTUNITIES_FILE, [])
    if 0 <= index < len(opps):
        opps[index]["status"] = new_status
        if new_status == "contacted":
            opps[index]["contacted_at"] = _now_ist()
        _save_json(OPPORTUNITIES_FILE, opps)
        return True
    return False


def _fmt_inr(amount) -> str:
    """Format amount in Indian numbering system with decimals."""
    if amount is None:
        return "N/A"
    try:
        amount = float(amount)
        if amount < 0:
            return f"-{_fmt_inr(-amount)}"
        s = f"{amount:,.2f}"
        # Convert to Indian grouping: 1,23,45,678.00
        parts = s.split(".")
        decimal_part = parts[1] if len(parts) > 1 else "00"
        integer_part = parts[0].replace(",", "")
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
        return f"\u20b9{formatted}.{decimal_part}"
    except (ValueError, TypeError):
        return str(amount)
