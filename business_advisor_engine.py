"""
PPS Anantam — Business Advisor Engine v1.0
============================================
Proactive AI business advisor that tells the trader:
  - WHAT / WHEN / FROM WHOM to buy
  - WHAT / WHEN / TO WHOM to sell
  - WHEN to hold inventory

Combines signals from:
  purchase_advisor_engine   — urgency index
  forward_strategy_engine   — 15-day outlook
  opportunity_engine        — trade opportunities
  calculation_engine        — landed costs + 3-tier offers
  ml_forecast_engine        — crude/FX forecasts
  market_intelligence_engine — 10-signal composite
  crm_engine                — customer relationship data
  ai_fallback_engine        — natural language generation

Author : PPS Anantam Engineering
Version: 1.0
"""
from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz

# ── Constants ─────────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent
ADVISORY_FILE = BASE / "ml_models" / "business_advisory.json"
LOG = logging.getLogger("business_advisor_engine")

# Ensure ml_models directory exists
ADVISORY_FILE.parent.mkdir(exist_ok=True)

# IOCL fortnightly revision dates (1st and 16th of each month)
_REVISION_DAYS = (1, 16)

# Seasonal demand map: month -> label
_SEASON_LABEL = {
    1: "Peak", 2: "Peak", 3: "Peak", 4: "Moderate",
    5: "Tapering", 6: "Monsoon", 7: "Monsoon", 8: "Monsoon",
    9: "Recovery", 10: "Ramp-up", 11: "Peak", 12: "Peak",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_ist() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _today() -> datetime.date:
    return datetime.datetime.now(IST).date()


def _load_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def _save_json(path: Path, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except (IOError, OSError) as exc:
        LOG.warning("Failed to save %s: %s", path.name, exc)


def _fmt_inr(amount) -> str:
    """Format amount with rupee symbol and Indian comma grouping."""
    if amount is None:
        return "N/A"
    try:
        amount = float(amount)
        if amount < 0:
            return f"-{_fmt_inr(-amount)}"
        s = f"{amount:,.2f}"
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
        return f"Rs.{formatted}.{decimal_part}"
    except (ValueError, TypeError):
        return str(amount)


# ── Lazy engine loaders (try/except for every dependency) ─────────────────────

def _get_purchase_advisor():
    try:
        from purchase_advisor_engine import PurchaseAdvisorEngine
        return PurchaseAdvisorEngine()
    except Exception:
        return None


def _get_forward_strategy():
    try:
        from forward_strategy_engine import ForwardStrategyEngine
        return ForwardStrategyEngine()
    except Exception:
        return None


def _get_opportunity_engine():
    try:
        from opportunity_engine import OpportunityEngine
        return OpportunityEngine()
    except Exception:
        return None


def _get_calculation_engine():
    try:
        from calculation_engine import BitumenCalculationEngine
        return BitumenCalculationEngine()
    except Exception:
        return None


def _get_market_intelligence():
    try:
        from market_intelligence_engine import MarketIntelligenceEngine
        return MarketIntelligenceEngine()
    except Exception:
        return None


def _get_crm():
    try:
        from crm_engine import IntelligentCRM
        return IntelligentCRM()
    except Exception:
        return None


def _get_customers_from_db() -> list:
    try:
        from database import get_all_customers
        return get_all_customers()
    except Exception:
        from customer_source import load_customers
        return load_customers()


def _get_suppliers_from_db() -> list:
    try:
        from database import get_all_suppliers
        return get_all_suppliers()
    except Exception:
        return []


def _forecast_crude() -> dict:
    try:
        from ml_forecast_engine import forecast_crude_price
        return forecast_crude_price(days_ahead=15)
    except Exception:
        return {}


def _forecast_fx() -> dict:
    try:
        from ml_forecast_engine import forecast_fx_rate
        return forecast_fx_rate(days_ahead=15)
    except Exception:
        return {}


def _ai_generate(prompt: str, context: str = "") -> str:
    """Generate natural language via the AI fallback engine."""
    try:
        from ai_fallback_engine import ask_with_fallback
        result = ask_with_fallback(prompt, context=context)
        return result.get("answer", "")
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# BUSINESS ADVISOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class BusinessAdvisor:
    """
    Proactive AI business advisor for bitumen commodity trading.

    Combines purchase urgency, forward strategy, opportunity scanning,
    landed cost analysis, ML forecasts, market intelligence, and CRM
    data into a unified daily intelligence brief.
    """

    def __init__(self):
        self._cached_signals: Optional[dict] = None

    # ── 1. DAILY INTELLIGENCE BRIEF ──────────────────────────────────────────

    def get_daily_intelligence_brief(self) -> dict:
        """
        Complete buy + sell + market + risk digest for the day.

        Returns
        -------
        dict with keys:
          buy_advisory, sell_advisory, timing_advisory,
          risk_summary, natural_language_brief, generated_at
        """
        buy = self.get_buy_advisory()
        sell = self.get_sell_advisory()
        timing = self.get_timing_advisory()
        risk = self._get_risk_summary()

        advisory_data = {
            "buy_advisory": buy,
            "sell_advisory": sell,
            "timing_advisory": timing,
            "risk_summary": risk,
            "generated_at": _now_ist(),
        }

        # Natural-language summary
        nl_brief = self._generate_nl_brief(advisory_data)
        advisory_data["natural_language_brief"] = nl_brief

        # Persist to disk
        self._persist(advisory_data)

        return advisory_data

    # ── 2. BUY ADVISORY ──────────────────────────────────────────────────────

    def get_buy_advisory(self) -> dict:
        """
        WHO to buy from, WHEN, HOW MUCH, and WHY.

        Returns
        -------
        dict with keys:
          sources, timing, quantity_mt, urgency, reasons, confidence
        """
        reasons: List[str] = []
        confidence = 0.5

        # --- Purchase urgency ---
        urgency_label = "HOLD"
        urgency_index = 50
        advisor = _get_purchase_advisor()
        if advisor:
            try:
                result = advisor.compute_urgency_index()
                urgency_index = result.get("urgency_index", 50)
                rec = result.get("recommendation", "HOLD")
                if "BUY NOW" in rec:
                    urgency_label = "BUY NOW"
                elif "PRE-BUY" in rec:
                    urgency_label = "PRE-BUY"
                elif "WAIT" in rec:
                    urgency_label = "WAIT"
                else:
                    urgency_label = "HOLD"
                reasons.append(f"Purchase urgency index: {urgency_index}/100 ({rec})")
                confidence = min(0.95, urgency_index / 100)
            except Exception as exc:
                LOG.debug("Purchase advisor failed: %s", exc)

        # --- Crude forecast direction ---
        crude_fc = _forecast_crude()
        crude_dir = crude_fc.get("direction", "STABLE")
        if crude_dir == "UP":
            reasons.append("Crude prices forecast to RISE -- lock in current rates")
            if urgency_label == "HOLD":
                urgency_label = "PRE-BUY"
        elif crude_dir == "DOWN":
            reasons.append("Crude prices forecast to FALL -- consider waiting")
            if urgency_label == "PRE-BUY":
                urgency_label = "HOLD"
        else:
            reasons.append("Crude prices forecast STABLE")

        # --- Market intelligence master signal ---
        mi = _get_market_intelligence()
        master_signal = {}
        if mi:
            try:
                all_signals = mi.compute_all_signals()
                self._cached_signals = all_signals
                master_signal = all_signals.get("master", {})
                market_dir = master_signal.get("market_direction", "SIDEWAYS")
                market_conf = master_signal.get("confidence", 50)
                reasons.append(
                    f"Market composite: {market_dir} ({market_conf}% confidence)"
                )
                action = master_signal.get("recommended_action", "")
                if action:
                    reasons.append(f"Market action: {action}")
            except Exception as exc:
                LOG.debug("Market intelligence failed: %s", exc)

        # --- Best sources (ranked by landed cost) ---
        sources: List[dict] = []
        calc = _get_calculation_engine()
        if calc:
            try:
                raw_sources = calc.find_best_sources(
                    "Ahmedabad", grade="VG30", load_type="Bulk", top_n=5
                )
                if raw_sources:
                    avg_landed = sum(
                        s.get("landed_cost", 0) for s in raw_sources
                    ) / len(raw_sources)
                    for s in raw_sources:
                        landed = s.get("landed_cost", 0)
                        savings = round(avg_landed - landed, 2) if avg_landed > landed else 0
                        sources.append({
                            "name": s.get("source", "Unknown"),
                            "source_type": s.get("source_type", ""),
                            "base_price": s.get("base_price", 0),
                            "freight": s.get("freight", 0),
                            "landed_inr": round(landed, 2),
                            "savings_vs_avg": round(savings, 2),
                        })
            except Exception as exc:
                LOG.debug("Calculation engine failed: %s", exc)

        # --- Quantity recommendation ---
        today = _today()
        month = today.month
        is_peak = month in (10, 11, 12, 1, 2, 3)
        if urgency_label == "BUY NOW" and is_peak:
            quantity_mt = 1000
        elif urgency_label == "BUY NOW":
            quantity_mt = 500
        elif urgency_label == "PRE-BUY":
            quantity_mt = 500 if is_peak else 300
        elif urgency_label == "HOLD":
            quantity_mt = 200
        else:
            quantity_mt = 0  # WAIT

        # --- Seasonal context ---
        season = _SEASON_LABEL.get(month, "Moderate")
        reasons.append(f"Season: {season} (Month {month})")

        return {
            "sources": sources,
            "timing": self._buy_timing_text(urgency_label, crude_dir),
            "quantity_mt": quantity_mt,
            "urgency": urgency_label,
            "urgency_index": urgency_index,
            "reasons": reasons,
            "confidence": round(confidence, 2),
            "crude_forecast_direction": crude_dir,
            "season": season,
            "generated_at": _now_ist(),
        }

    # ── 3. SELL ADVISORY ──────────────────────────────────────────────────────

    def get_sell_advisory(self) -> dict:
        """
        WHO to sell to, AT WHAT PRICE, and WHEN.

        Returns
        -------
        dict with keys:
          targets, call_script, timing
        """
        targets: List[dict] = []
        calc = _get_calculation_engine()

        # --- Load customers and classify by relationship ---
        customers = _get_customers_from_db()
        crm = _get_crm()

        for cust in customers:
            name = cust.get("name", "Unknown")
            city = cust.get("city", "")
            if not city:
                continue

            # Determine priority from CRM stage
            stage = cust.get("relationship_stage", "cold")
            days_since = cust.get("days_since_last_contact", 999)

            # Try CRM profile for more accurate stage
            if crm and days_since == 999:
                try:
                    profile = crm.get_customer_profile(name)
                    intel = profile.get("intelligence", {})
                    stage = intel.get("auto_relationship_stage", stage)
                    days_since = intel.get("days_since_last_contact", days_since)
                except Exception:
                    pass

            if stage == "hot":
                priority = "high"
            elif stage == "warm":
                priority = "medium"
            else:
                priority = "low"

            # Calculate 3-tier offers for this customer's city
            offer_agg = 0
            offer_bal = 0
            offer_pre = 0
            margin_per_mt = 0
            landed_cost = 0

            if calc:
                try:
                    sources = calc.find_best_sources(city, grade="VG30", top_n=1)
                    if sources:
                        landed_cost = sources[0].get("landed_cost", 0)
                        last_price = cust.get("last_purchase_price", 0)
                        offers = calc.generate_offer_prices(
                            landed_cost,
                            customer_last_price=last_price if last_price else None,
                        )
                        offer_agg = offers.get("aggressive", {}).get("price", 0)
                        offer_bal = offers.get("balanced", {}).get("price", 0)
                        offer_pre = offers.get("premium", {}).get("price", 0)
                        margin_per_mt = offers.get("aggressive", {}).get("margin", 0)
                except Exception:
                    pass

            targets.append({
                "name": name,
                "city": city,
                "relationship_stage": stage,
                "days_since_contact": days_since,
                "offer_aggressive": round(offer_agg, 2),
                "offer_balanced": round(offer_bal, 2),
                "offer_premium": round(offer_pre, 2),
                "landed_cost": round(landed_cost, 2),
                "margin_per_mt": round(margin_per_mt, 2),
                "priority": priority,
            })

        # Sort: high priority first, then by margin descending
        priority_order = {"high": 0, "medium": 1, "low": 2}
        targets.sort(
            key=lambda t: (priority_order.get(t["priority"], 3), -t["margin_per_mt"])
        )

        # --- Opportunity engine targets ---
        opp_engine = _get_opportunity_engine()
        if opp_engine:
            try:
                recs = opp_engine.get_todays_recommendations()
                buyers = recs.get("buyers_to_call", [])
                for buyer in buyers[:5]:
                    buyer_name = buyer.get("customer_name", "")
                    # Skip if already in targets
                    if any(t["name"] == buyer_name for t in targets):
                        continue
                    targets.append({
                        "name": buyer_name,
                        "city": buyer.get("customer_city", ""),
                        "relationship_stage": "reactivation",
                        "days_since_contact": 999,
                        "offer_aggressive": 0,
                        "offer_balanced": 0,
                        "offer_premium": 0,
                        "landed_cost": buyer.get("new_landed_cost", 0),
                        "margin_per_mt": buyer.get("estimated_margin_per_mt", 0),
                        "priority": "high",
                    })
            except Exception as exc:
                LOG.debug("Opportunity engine failed: %s", exc)

        # Keep top 15 targets
        targets = targets[:15]

        # --- Sell timing ---
        timing = self._sell_timing_text()

        # --- Call script ---
        call_script = self._generate_call_script(targets)

        return {
            "targets": targets,
            "call_script": call_script,
            "timing": timing,
            "total_targets": len(targets),
            "high_priority_count": sum(1 for t in targets if t["priority"] == "high"),
            "generated_at": _now_ist(),
        }

    # ── 4. TIMING ADVISORY ───────────────────────────────────────────────────

    def get_timing_advisory(self) -> dict:
        """
        Fortnightly revision tracker, price trend prediction,
        and optimal order placement window.

        Returns
        -------
        dict with keys:
          next_revision_date, expected_direction, order_window, confidence
        """
        today = _today()

        # --- Next IOCL revision date (1st or 16th) ---
        if today.day < 16:
            next_rev = today.replace(day=16)
        else:
            # Next month 1st
            if today.month == 12:
                next_rev = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_rev = today.replace(month=today.month + 1, day=1)

        days_to_rev = (next_rev - today).days

        # --- Expected direction from forward strategy ---
        expected_direction = "STABLE"
        strategy_confidence = 50.0
        fwd = _get_forward_strategy()
        if fwd:
            try:
                price_dir = fwd.calculate_price_direction()
                expected_direction = price_dir.get("direction", "STABLE")
                strategy_confidence = float(price_dir.get("confidence_pct", 50))
            except Exception as exc:
                LOG.debug("Forward strategy failed: %s", exc)

        # --- Crude forecast as secondary signal ---
        crude_fc = _forecast_crude()
        crude_dir = crude_fc.get("direction", "STABLE")
        crude_conf = float(crude_fc.get("confidence", 50))

        # Blend: 60% forward strategy + 40% crude forecast
        dir_map = {"UP": 1, "DOWN": -1, "STABLE": 0, "SIDEWAYS": 0}
        blended = (
            0.6 * dir_map.get(expected_direction, 0) +
            0.4 * dir_map.get(crude_dir, 0)
        )
        if blended > 0.2:
            final_direction = "UP"
        elif blended < -0.2:
            final_direction = "DOWN"
        else:
            final_direction = "STABLE"

        blended_confidence = round(
            0.6 * strategy_confidence + 0.4 * crude_conf, 1
        )

        # --- Optimal order window ---
        if final_direction == "UP":
            if days_to_rev <= 3:
                order_window = "ORDER TODAY -- prices expected to rise at next revision"
            else:
                order_window = (
                    f"Order within {min(days_to_rev, 5)} days -- "
                    f"prices trending UP before {next_rev.strftime('%Y-%m-%d')} revision"
                )
        elif final_direction == "DOWN":
            order_window = (
                f"Wait for revision on {next_rev.strftime('%Y-%m-%d')} -- "
                f"prices may drop (save {days_to_rev} days)"
            )
        else:
            order_window = (
                f"Normal timing -- next revision {next_rev.strftime('%Y-%m-%d')} "
                f"({days_to_rev} days away). No urgency."
            )

        return {
            "next_revision_date": next_rev.strftime("%Y-%m-%d"),
            "days_to_revision": days_to_rev,
            "expected_direction": final_direction,
            "forward_strategy_direction": expected_direction,
            "crude_forecast_direction": crude_dir,
            "order_window": order_window,
            "confidence": round(blended_confidence / 100, 2),
            "season": _SEASON_LABEL.get(today.month, "Moderate"),
            "generated_at": _now_ist(),
        }

    # ── 5. RISK SUMMARY (private) ────────────────────────────────────────────

    def _get_risk_summary(self) -> dict:
        """
        Assess supply, FX, credit, seasonal, and logistics risks.

        Returns
        -------
        dict of risk_type -> {level, description, mitigation}
        """
        risks: Dict[str, dict] = {}
        signals = self._cached_signals or {}

        # --- 1. Supply risk (from news + port signals) ---
        news_sig = signals.get("news", {})
        supply_risk_level = news_sig.get("supply_risk", "LOW")
        risks["supply"] = {
            "level": supply_risk_level.lower(),
            "description": self._supply_risk_description(supply_risk_level, news_sig),
            "mitigation": (
                "Diversify suppliers and maintain 15-day safety stock"
                if supply_risk_level == "HIGH"
                else "Monitor news alerts and maintain 7-day buffer stock"
                if supply_risk_level == "MEDIUM"
                else "Normal procurement schedule"
            ),
        }

        # --- 2. FX risk (from currency signal) ---
        currency_sig = signals.get("currency", {})
        fx_pressure = currency_sig.get("pressure", "LOW")
        fx_level = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(
            fx_pressure, "low"
        )
        fx_fc = _forecast_fx()
        fx_dir = fx_fc.get("direction", "STABLE")
        risks["fx"] = {
            "level": fx_level,
            "description": (
                f"USD/INR pressure: {fx_pressure}. "
                f"FX forecast: {fx_dir}. "
                f"Latest rate: {currency_sig.get('latest_usdinr', 'N/A')}"
            ),
            "mitigation": (
                "Consider forward cover or pre-buy to hedge FX exposure"
                if fx_level == "high"
                else "Monitor USD/INR; no hedging needed currently"
            ),
        }

        # --- 3. Credit risk (from CRM data) ---
        customers = _get_customers_from_db()
        overdue_count = sum(
            1 for c in customers
            if float(c.get("outstanding_inr", 0) or 0) > 0
        )
        credit_level = (
            "high" if overdue_count > 3
            else "medium" if overdue_count > 0
            else "low"
        )
        risks["credit"] = {
            "level": credit_level,
            "description": f"{overdue_count} customer(s) with outstanding amounts",
            "mitigation": (
                "Enforce 100% advance for new orders; follow up on overdue"
                if credit_level == "high"
                else "Standard payment terms; monitor receivables"
            ),
        }

        # --- 4. Seasonal risk ---
        month = _today().month
        season = _SEASON_LABEL.get(month, "Moderate")
        if season == "Monsoon":
            seasonal_level = "high"
            seasonal_desc = "Active monsoon -- construction demand severely reduced"
            seasonal_mit = "Reduce inventory to 5-day stock; focus on covered projects"
        elif season in ("Tapering", "Recovery"):
            seasonal_level = "medium"
            seasonal_desc = f"{season} season -- demand transitioning"
            seasonal_mit = "Adjust stock to 7-10 day levels"
        else:
            seasonal_level = "low"
            seasonal_desc = f"{season} season -- healthy construction activity"
            seasonal_mit = "Maintain 10-15 day stock for peak demand"

        risks["seasonal"] = {
            "level": seasonal_level,
            "description": seasonal_desc,
            "mitigation": seasonal_mit,
        }

        # --- 5. Logistics risk (from weather + ports signals) ---
        weather_sig = signals.get("weather", {})
        ports_sig = signals.get("ports", {})
        logistics_risk = weather_sig.get("logistics_risk", "LOW")
        port_risk = ports_sig.get("port_risk", "LOW")
        if logistics_risk == "HIGH" or port_risk == "HIGH":
            log_level = "high"
        elif logistics_risk == "MEDIUM" or port_risk == "MEDIUM":
            log_level = "medium"
        else:
            log_level = "low"

        affected_cities = weather_sig.get("affected_cities", [])
        congested_ports = ports_sig.get("congested_ports", [])
        risks["logistics"] = {
            "level": log_level,
            "description": (
                f"Road: {logistics_risk}. Port: {port_risk}. "
                f"Affected cities: {', '.join(affected_cities[:5]) or 'None'}. "
                f"Congested ports: {', '.join(congested_ports[:3]) or 'None'}"
            ),
            "mitigation": (
                "Plan alternate routes; allow 2-3 day delivery buffer"
                if log_level == "high"
                else "Normal logistics; monitor weather updates"
            ),
        }

        # --- Overall risk level ---
        risk_levels = [r["level"] for r in risks.values()]
        high_count = risk_levels.count("high")
        med_count = risk_levels.count("medium")
        if high_count >= 2:
            overall = "high"
        elif high_count >= 1 or med_count >= 3:
            overall = "medium"
        else:
            overall = "low"

        return {
            "risks": risks,
            "overall_level": overall,
            "high_risk_count": high_count,
            "generated_at": _now_ist(),
        }

    # ── 6. NATURAL LANGUAGE BRIEF (private) ───────────────────────────────────

    def _generate_nl_brief(self, advisory_data: dict) -> str:
        """
        Convert structured advisory data into a natural-language paragraph.
        Uses ai_fallback_engine when available, falls back to template.
        """
        buy = advisory_data.get("buy_advisory", {})
        sell = advisory_data.get("sell_advisory", {})
        timing = advisory_data.get("timing_advisory", {})
        risk = advisory_data.get("risk_summary", {})

        # --- Build context for AI generation ---
        context_parts = [
            f"Buy urgency: {buy.get('urgency', 'HOLD')}",
            f"Recommended quantity: {buy.get('quantity_mt', 0)} MT",
            f"Season: {buy.get('season', 'N/A')}",
            f"Crude forecast: {buy.get('crude_forecast_direction', 'STABLE')}",
            f"Sell targets: {sell.get('total_targets', 0)} customers",
            f"High-priority targets: {sell.get('high_priority_count', 0)}",
            f"Next price revision: {timing.get('next_revision_date', 'N/A')}",
            f"Expected price direction: {timing.get('expected_direction', 'STABLE')}",
            f"Order window: {timing.get('order_window', 'Normal timing')}",
            f"Overall risk: {risk.get('overall_level', 'low')}",
        ]

        # Add top source if available
        sources = buy.get("sources", [])
        if sources:
            top = sources[0]
            context_parts.append(
                f"Best source: {top.get('name', 'N/A')} at "
                f"{_fmt_inr(top.get('landed_inr', 0))}/MT landed"
            )

        context = "\n".join(context_parts)

        # --- Try AI generation ---
        # Inject business context for domain-accurate briefs
        biz_ctx = ""
        try:
            from business_context import get_business_context
            biz_ctx = "\n\n" + get_business_context("general")
        except Exception:
            pass

        prompt = (
            "You are a bitumen trading advisor for PPS Anantam Capital Pvt Ltd, "
            "Vadodara, Gujarat. "
            "Write a concise 3-4 sentence daily intelligence brief for the trader "
            "based on this data. Start with 'Today I recommend...' and include "
            "specific buy/sell/hold guidance with quantities and prices. "
            "Use Indian number formatting (Rs./MT). Be direct and actionable."
            f"{biz_ctx}"
        )

        ai_brief = _ai_generate(prompt, context)
        if ai_brief and len(ai_brief) > 50:
            return ai_brief

        # --- Template fallback ---
        return self._template_brief(buy, sell, timing, risk, sources)

    def _template_brief(
        self,
        buy: dict,
        sell: dict,
        timing: dict,
        risk: dict,
        sources: list,
    ) -> str:
        """Deterministic template-based brief when AI is unavailable."""
        urgency = buy.get("urgency", "HOLD")
        qty = buy.get("quantity_mt", 0)
        season = buy.get("season", "N/A")
        crude_dir = buy.get("crude_forecast_direction", "STABLE")
        rev_date = timing.get("next_revision_date", "N/A")
        exp_dir = timing.get("expected_direction", "STABLE")
        overall_risk = risk.get("overall_level", "low")
        n_targets = sell.get("total_targets", 0)
        hi_priority = sell.get("high_priority_count", 0)

        # Source info
        source_text = ""
        if sources:
            top = sources[0]
            source_text = (
                f" from {top.get('name', 'best available source')} "
                f"at {_fmt_inr(top.get('landed_inr', 0))}/MT landed Ahmedabad"
            )

        # Buy guidance
        if urgency == "BUY NOW":
            buy_text = (
                f"Today I recommend buying {qty} MT of VG-30{source_text} immediately. "
                f"Crude oil is trending {crude_dir} and the purchase urgency is high."
            )
        elif urgency == "PRE-BUY":
            buy_text = (
                f"Today I recommend pre-buying {qty} MT of VG-30{source_text} "
                f"within the next 5 days. Crude trend: {crude_dir}."
            )
        elif urgency == "WAIT":
            buy_text = (
                "Today I recommend holding off on procurement. "
                f"Crude is trending {crude_dir} and prices may soften."
            )
        else:
            buy_text = (
                f"Today I recommend maintaining current inventory ({qty} MT buffer). "
                f"Market is {crude_dir}, no urgency to act."
            )

        # Sell guidance
        sell_text = (
            f"On the sell side, {n_targets} customer targets identified "
            f"({hi_priority} high-priority). "
        )
        if hi_priority > 0:
            sell_text += "Prioritize calls to hot/warm contacts today."
        else:
            sell_text += "Focus on reactivation outreach."

        # Timing + risk
        timing_text = (
            f"Next IOCL revision: {rev_date} (expected {exp_dir}). "
            f"Season: {season}. Overall risk: {overall_risk}."
        )

        return f"{buy_text} {sell_text} {timing_text}"

    # ── HELPER METHODS ────────────────────────────────────────────────────────

    def _buy_timing_text(self, urgency: str, crude_dir: str) -> str:
        """Generate human-readable buy timing recommendation."""
        if urgency == "BUY NOW":
            return "Immediate -- place orders today before prices increase"
        elif urgency == "PRE-BUY":
            return "Within 5 days -- favorable window, crude trending " + crude_dir
        elif urgency == "WAIT":
            return "Delay 7-14 days -- prices expected to soften"
        return "Normal schedule -- no urgency, monitor daily"

    def _sell_timing_text(self) -> str:
        """Generate sell timing recommendation based on market conditions."""
        today = _today()
        month = today.month

        # Sell aggressively before expected price drops or during demand peaks
        if month in (10, 11, 12, 1, 2, 3):
            return (
                "Peak season -- push aggressively. Customers need supply for "
                "active road construction projects."
            )
        elif month in (6, 7, 8):
            return (
                "Monsoon slowdown -- focus on covered/indoor projects and "
                "government contracts with guaranteed offtake."
            )
        elif month in (4, 5):
            return (
                "Season tapering -- clear inventory before monsoon. "
                "Offer aggressive pricing to move stock."
            )
        return (
            "Post-monsoon recovery -- demand picking up. "
            "Good time to reactivate cold contacts."
        )

    def _generate_call_script(self, targets: list) -> str:
        """Generate a prioritized call script for today's targets."""
        if not targets:
            return "No targets identified for today."

        lines = ["--- TODAY'S CALL PRIORITY LIST ---", ""]
        for i, t in enumerate(targets[:10], 1):
            price_text = ""
            if t.get("offer_aggressive", 0) > 0:
                price_text = (
                    f" | Offer: {_fmt_inr(t['offer_aggressive'])}/MT (Aggressive) "
                    f"to {_fmt_inr(t['offer_premium'])}/MT (Premium)"
                )
            margin_text = ""
            if t.get("margin_per_mt", 0) > 0:
                margin_text = f" | Margin: {_fmt_inr(t['margin_per_mt'])}/MT"

            lines.append(
                f"{i}. [{t['priority'].upper()}] {t['name']} ({t['city']})"
                f"{price_text}{margin_text}"
            )
            if t.get("relationship_stage") == "hot":
                lines.append(f"   -> Active customer. Check for repeat order.")
            elif t.get("relationship_stage") == "warm":
                lines.append(
                    f"   -> Last contact {t.get('days_since_contact', '?')} days ago. "
                    f"Send updated offer."
                )
            elif t.get("relationship_stage") == "reactivation":
                lines.append(f"   -> Reactivation target. Lead with price advantage.")
            else:
                lines.append(f"   -> Cold contact. Reintroduce with market update.")
            lines.append("")

        return "\n".join(lines)

    def _supply_risk_description(self, level: str, news_sig: dict) -> str:
        """Build supply risk description from news signal data."""
        events = news_sig.get("events", [])
        if not events:
            return f"Supply risk: {level}. No significant supply disruptions detected."

        event_types = [e.get("type", "") for e in events[:3]]
        headlines = [e.get("headline", "")[:80] for e in events[:2]]

        desc = f"Supply risk: {level}. "
        if "refinery_shutdown" in event_types:
            desc += "Refinery shutdowns reported. "
        if "geopolitics" in event_types:
            desc += "Geopolitical tensions affecting crude supply. "
        if "port_disruption" in event_types:
            desc += "Port disruptions detected. "
        if headlines:
            desc += f"Key headline: {headlines[0]}"
        return desc

    # ── PERSISTENCE ───────────────────────────────────────────────────────────

    def _persist(self, advisory: dict) -> None:
        """Save latest advisory + append to rolling history."""
        try:
            history = []
            if ADVISORY_FILE.exists():
                data = _load_json(ADVISORY_FILE, {})
                if isinstance(data, dict):
                    history = data.get("history", [])

            # Compact history entry
            history.append({
                "timestamp": advisory.get("generated_at", _now_ist()),
                "buy_urgency": advisory.get("buy_advisory", {}).get("urgency", ""),
                "sell_targets": advisory.get("sell_advisory", {}).get("total_targets", 0),
                "expected_direction": advisory.get("timing_advisory", {}).get(
                    "expected_direction", ""
                ),
                "overall_risk": advisory.get("risk_summary", {}).get(
                    "overall_level", ""
                ),
            })

            # Keep last 90 entries
            history = history[-90:]

            _save_json(ADVISORY_FILE, {
                "latest": advisory,
                "history": history,
            })
        except Exception as exc:
            LOG.warning("Advisory persistence failed: %s", exc)

    def get_history(self) -> list:
        """Load historical advisory data."""
        data = _load_json(ADVISORY_FILE, {})
        if isinstance(data, dict):
            return data.get("history", [])
        return []

    def get_latest(self) -> dict:
        """Load the most recent advisory without recomputing."""
        data = _load_json(ADVISORY_FILE, {})
        if isinstance(data, dict):
            return data.get("latest", {})
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_daily_brief() -> dict:
    """Module-level shortcut for sync_engine integration."""
    advisor = BusinessAdvisor()
    return advisor.get_daily_intelligence_brief()


def get_buy_advisory() -> dict:
    """Quick accessor for buy-side guidance."""
    advisor = BusinessAdvisor()
    return advisor.get_buy_advisory()


def get_sell_advisory() -> dict:
    """Quick accessor for sell-side guidance."""
    advisor = BusinessAdvisor()
    return advisor.get_sell_advisory()


def get_timing_advisory() -> dict:
    """Quick accessor for timing/revision guidance."""
    advisor = BusinessAdvisor()
    return advisor.get_timing_advisory()


def get_advisor_status() -> dict:
    """Status report for AI module registry."""
    return {
        "engine": "BusinessAdvisor",
        "version": "1.0",
        "advisory_file": str(ADVISORY_FILE),
        "dependencies": [
            "purchase_advisor_engine",
            "forward_strategy_engine",
            "opportunity_engine",
            "calculation_engine",
            "ml_forecast_engine",
            "market_intelligence_engine",
            "crm_engine",
            "ai_fallback_engine",
        ],
    }
