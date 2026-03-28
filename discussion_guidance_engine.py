"""
PPS Anantam — Discussion Guidance Engine v1.0
===============================================
3-Mode AI-Powered Discussion Brief Generator for Bitumen Trading.

Generates structured, data-backed conversation briefs for:
  1. Supplier mode   — International cargo sellers (FOB, freight, loading, ports)
  2. Importer mode   — Indian buyers (demand, pricing tiers, delivery, payment)
  3. Local Trader mode — District distributors (local demand, transport, margins)

Each guide is pre-filled from CRM/database, enriched with live market data
(crude prices, freight benchmarks, port congestion, demand forecasts), and
includes ready-to-send WhatsApp drafts and AI-enhanced talking points.

Author : PPS Anantam Engineering
Version: 1.0
"""

from __future__ import annotations

import json
import logging
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz

# ── Logging ──────────────────────────────────────────────────────────────────
LOG = logging.getLogger("discussion_guidance_engine")

# ── Constants ────────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

# Business rules (defaults — overridden from settings when available)
_DEFAULT_MIN_MARGIN = 500
_DEFAULT_BALANCED_ADD = 800
_DEFAULT_PREMIUM_ADD = 1200
_DEFAULT_GST_PCT = 18
_DEFAULT_CUSTOMS_PCT = 2.5
_DEFAULT_BULK_RATE_KM = 5.5
_DEFAULT_DRUM_RATE_KM = 6.0
_DEFAULT_QUOTE_VALIDITY_HOURS = 24
_DEFAULT_PAYMENT_TERMS = "100% Advance"
_HSN_CODE = "27132000"

# ── Safe imports ─────────────────────────────────────────────────────────────

try:
    from settings_engine import load_settings
except ImportError:
    def load_settings() -> dict:
        return {}

try:
    from calculation_engine import BitumenCalculationEngine
except ImportError:
    BitumenCalculationEngine = None  # type: ignore[misc,assignment]

try:
    from negotiation_engine import NegotiationAssistant, OBJECTION_LIBRARY
except ImportError:
    NegotiationAssistant = None  # type: ignore[misc,assignment]
    OBJECTION_LIBRARY = {}

try:
    from communication_engine import CommunicationHub
except ImportError:
    CommunicationHub = None  # type: ignore[misc,assignment]

try:
    from crm_engine import IntelligentCRM
except ImportError:
    IntelligentCRM = None  # type: ignore[misc,assignment]

try:
    import ml_forecast_engine
except ImportError:
    ml_forecast_engine = None  # type: ignore[assignment]

try:
    from market_intelligence_engine import MarketIntelligenceEngine
except ImportError:
    MarketIntelligenceEngine = None  # type: ignore[misc,assignment]

try:
    import maritime_intelligence_engine as maritime_intel_engine
except ImportError:
    try:
        import maritime_intel_engine  # type: ignore[no-redef]
    except ImportError:
        maritime_intel_engine = None  # type: ignore[assignment]

try:
    from ai_fallback_engine import ask_with_fallback
except ImportError:
    ask_with_fallback = None  # type: ignore[assignment]

try:
    from database import get_all_customers, get_all_suppliers, get_all_deals
except ImportError:
    def get_all_customers() -> list:
        return []

    def get_all_suppliers() -> list:
        return []

    def get_all_deals() -> list:
        return []


# ── Helper utilities ─────────────────────────────────────────────────────────

def _now() -> str:
    """Current IST timestamp string."""
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def _fmt_inr(amount: Any) -> str:
    """Format INR with Indian comma system (lakhs/crores)."""
    if amount is None:
        return "N/A"
    try:
        amount = float(amount)
        if amount < 0:
            return f"-{_fmt_inr(-amount)}"
        integer_part = str(int(abs(amount)))
        if len(integer_part) <= 3:
            formatted = integer_part
        else:
            last3 = integer_part[-3:]
            remaining = integer_part[:-3]
            groups: list[str] = []
            while remaining:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            formatted = ",".join(groups) + "," + last3
        return f"\u20b9{formatted}"
    except (ValueError, TypeError):
        return str(amount)


def _load_json(path: Path, default: Any = None) -> Any:
    """Safely load JSON file."""
    if default is None:
        default = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def _get_settings() -> dict:
    """Load settings with fallback."""
    try:
        return load_settings()
    except Exception:
        return {}


def _get_market_context() -> dict:
    """Fetch current crude + FX snapshot for discussion context."""
    context: Dict[str, Any] = {
        "brent_usd": None,
        "usdinr": None,
        "trend": "stable",
        "narrative": "",
    }
    try:
        crude_data = _load_json(BASE / "tbl_crude_prices.json")
        if crude_data:
            brent_records = [r for r in crude_data if r.get("benchmark") == "Brent"]
            if brent_records:
                context["brent_usd"] = brent_records[-1].get("price")
    except Exception:
        pass

    try:
        fx_data = _load_json(BASE / "tbl_fx_rates.json")
        if fx_data:
            usd_records = [r for r in fx_data if "USD" in str(r.get("from_currency", ""))]
            if usd_records:
                context["usdinr"] = usd_records[-1].get("rate")
    except Exception:
        pass

    brent = context["brent_usd"]
    usdinr = context["usdinr"]
    if brent:
        if brent > 80:
            context["trend"] = "rising"
            context["narrative"] = (
                f"Crude at ${brent}/bbl (above ₹ 80 resistance). "
                f"Bitumen prices likely to firm up. Lock prices now."
            )
        elif brent < 70:
            context["trend"] = "falling"
            context["narrative"] = (
                f"Crude at ${brent}/bbl (below ₹ 70). "
                f"Prices may soften further. Good time to negotiate lower FOB."
            )
        else:
            context["trend"] = "stable"
            context["narrative"] = (
                f"Crude at ${brent}/bbl (stable range). "
                f"Market is balanced. Focus on freight and logistics advantages."
            )
    if usdinr:
        context["narrative"] += f" USD/INR at {usdinr}."

    return context


def _get_crude_forecast() -> dict:
    """Get crude price forecast from ml_forecast_engine."""
    if ml_forecast_engine is None:
        return {"direction": "STABLE", "confidence": 50, "model": "unavailable"}
    try:
        return ml_forecast_engine.forecast_crude_price(days_ahead=30)
    except Exception:
        return {"direction": "STABLE", "confidence": 50, "model": "fallback"}


def _get_customer_from_db(name: str) -> dict:
    """Lookup a customer by name from database."""
    try:
        customers = get_all_customers()
        for c in customers:
            if c.get("name", "").lower() == name.lower():
                return c
    except Exception:
        pass
    return {}


def _get_supplier_from_db(name: str) -> dict:
    """Lookup a supplier by name from database."""
    try:
        suppliers = get_all_suppliers()
        for s in suppliers:
            if s.get("name", "").lower() == name.lower():
                return s
    except Exception:
        pass
    return {}


def _get_crm_profile(name: str) -> dict:
    """Get full CRM profile if IntelligentCRM is available."""
    if IntelligentCRM is None:
        return {}
    try:
        crm = IntelligentCRM()
        return crm.get_customer_profile(name)
    except Exception:
        return {}


def _get_maritime_summary() -> dict:
    """Get cached or refreshed maritime intelligence summary."""
    # First try loading cached data
    cached = _load_json(BASE / "tbl_maritime_intel.json", {})
    if isinstance(cached, dict) and cached.get("summary"):
        return cached

    # Try refreshing
    if maritime_intel_engine is not None:
        try:
            return maritime_intel_engine.refresh_maritime_intel()
        except Exception:
            pass

    return cached if isinstance(cached, dict) else {}


def _get_objections_for_mode(mode: str) -> list:
    """Return relevant objection responses based on discussion mode."""
    if not OBJECTION_LIBRARY:
        return []

    mode_objection_keys = {
        "supplier": ["price_too_high", "payment_terms", "delivery_delay"],
        "importer": ["price_too_high", "competitor_cheaper", "payment_terms", "quality_concern"],
        "trader": ["price_too_high", "competitor_cheaper", "need_time", "quality_concern"],
    }

    keys = mode_objection_keys.get(mode, ["price_too_high", "payment_terms", "need_time"])
    results = []
    for k in keys:
        obj = OBJECTION_LIBRARY.get(k)
        if obj:
            results.append({
                "objection": obj["objection"],
                "response": obj["detailed_reply"],
                "confidence_booster": obj.get("confidence_booster", ""),
            })
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class DiscussionGuide:
    """
    3-Mode Discussion Guidance System for Bitumen Trading.

    Modes:
      - supplier  : International cargo seller discussions
      - importer  : Indian buyer discussions
      - trader    : Local district distributor discussions

    Each mode generates a comprehensive, data-backed brief with
    talking points, objection handling, pricing targets, and
    ready-to-send WhatsApp messages.
    """

    MODE_SUPPLIER = "supplier"
    MODE_IMPORTER = "importer"
    MODE_TRADER = "trader"

    _VALID_MODES = {MODE_SUPPLIER, MODE_IMPORTER, MODE_TRADER}

    def __init__(self) -> None:
        self.settings = _get_settings()
        self.min_margin = float(self.settings.get("margin_min_per_mt", _DEFAULT_MIN_MARGIN))
        self.balanced_add = float(self.settings.get("margin_balanced_add", _DEFAULT_BALANCED_ADD))
        self.premium_add = float(self.settings.get("margin_premium_add", _DEFAULT_PREMIUM_ADD))
        self.gst_pct = float(self.settings.get("gst_rate_pct", _DEFAULT_GST_PCT))
        self.customs_pct = float(self.settings.get("customs_duty_pct", _DEFAULT_CUSTOMS_PCT))
        self.bulk_rate_km = float(self.settings.get("bulk_rate_per_km", _DEFAULT_BULK_RATE_KM))
        self.drum_rate_km = float(self.settings.get("drum_rate_per_km", _DEFAULT_DRUM_RATE_KM))
        self.quote_validity = int(self.settings.get("quote_validity_hours", _DEFAULT_QUOTE_VALIDITY_HOURS))
        self.payment_terms = self.settings.get("payment_default_terms", _DEFAULT_PAYMENT_TERMS)
        self.company = "PPS Anantam"

        # Lazy-loaded engines
        self._calc: Optional[Any] = None
        self._comm: Optional[Any] = None

    def _get_calc(self) -> Any:
        """Lazy-load BitumenCalculationEngine."""
        if self._calc is None and BitumenCalculationEngine is not None:
            try:
                self._calc = BitumenCalculationEngine()
            except Exception:
                pass
        return self._calc

    def _get_comm(self) -> Any:
        """Lazy-load CommunicationHub."""
        if self._comm is None and CommunicationHub is not None:
            try:
                self._comm = CommunicationHub()
            except Exception:
                pass
        return self._comm

    # ── Main entry point ─────────────────────────────────────────────────────

    def prepare_discussion(self, mode: str, party_info: dict) -> dict:
        """
        Main entry point. Routes to mode-specific guide generator.

        Parameters
        ----------
        mode       : One of 'supplier', 'importer', 'trader'.
        party_info : Dict with party details (name, city, state, etc.).

        Returns
        -------
        dict — Comprehensive discussion guide tailored to the mode.
        """
        if mode not in self._VALID_MODES:
            return {
                "error": f"Invalid mode '{mode}'. Use: {', '.join(sorted(self._VALID_MODES))}",
                "generated_at": _now(),
            }

        party_info = dict(party_info)  # defensive copy
        party_info.setdefault("name", "Unknown Party")

        base = {
            "mode": mode,
            "party_name": party_info["name"],
            "generated_at": _now(),
            "quote_validity_hours": self.quote_validity,
            "payment_terms": self.payment_terms,
        }

        try:
            if mode == self.MODE_SUPPLIER:
                guide = self._supplier_guide(party_info)
            elif mode == self.MODE_IMPORTER:
                guide = self._importer_guide(party_info)
            else:
                guide = self._trader_guide(party_info)
        except Exception as exc:
            LOG.error("Discussion guide generation failed for mode=%s: %s", mode, exc)
            guide = {"error": str(exc)}

        base.update(guide)
        return base

    # ══════════════════════════════════════════════════════════════════════════
    #  MODE 1: SUPPLIER GUIDE — International Cargo Sellers
    # ══════════════════════════════════════════════════════════════════════════

    def _supplier_guide(self, supplier_info: dict) -> dict:
        """
        Build a discussion guide for talking to an international supplier.

        party_info keys:
          name            : Supplier company name
          country         : Origin country (optional)
          target_quantity_mt : Desired cargo quantity (optional)
          target_fob      : Target FOB price USD/MT (optional)
        """
        name = supplier_info.get("name", "Supplier")
        country = supplier_info.get("country", "")
        target_qty = float(supplier_info.get("target_quantity_mt", 5000))
        target_fob = supplier_info.get("target_fob")

        # ── 1. Pre-fill from database/CRM ────────────────────────────────────
        db_supplier = _get_supplier_from_db(name)
        crm_profile = _get_crm_profile(name)
        last_contact = crm_profile.get("intelligence", {}).get("days_since_last_contact", "N/A")
        last_price = crm_profile.get("intelligence", {}).get("last_price")

        # ── 2. Live market data ──────────────────────────────────────────────
        market = _get_market_context()
        crude_forecast = _get_crude_forecast()
        maritime = _get_maritime_summary()
        maritime_summary = maritime.get("summary", {}) if isinstance(maritime, dict) else {}

        # ── 3. Current FOB/CFR benchmarks ────────────────────────────────────
        calc = self._get_calc()
        market_fob = 380.0  # default
        if calc:
            try:
                intl_cost = calc.calculate_international_landed_cost({
                    "fob_usd": 380,
                    "freight_usd": 35,
                    "usdinr": float(market.get("usdinr") or 83.25),
                })
                market_fob = intl_cost.get("fob_usd", 380)
            except Exception:
                pass

        target_fob_val = float(target_fob) if target_fob else round(market_fob * 0.95, 2)
        floor_fob = round(market_fob * 0.90, 2)

        # ── 4. Freight options from maritime data ────────────────────────────
        freight_options: list[dict] = []
        if maritime_intel_engine is not None:
            try:
                routes = getattr(maritime_intel_engine, "ROUTES", [])
                for route in routes:
                    origin = route.get("from", "")
                    if country and country.lower() not in origin.lower():
                        # Skip routes from other origin countries unless no country filter
                        pass
                    freight_options.append({
                        "route": f"{route['from']} -> {route['to']}",
                        "rate_usd_mt": route.get("avg_cost_usd_mt", 0),
                        "transit_days": route.get("avg_days", 0),
                        "recommendation": "Best value" if route.get("avg_cost_usd_mt", 99) < 25 else "Standard",
                    })
                freight_options.sort(key=lambda x: x["rate_usd_mt"])
            except Exception:
                pass

        if not freight_options:
            freight_options = [
                {"route": "Middle East -> Mundra", "rate_usd_mt": 18, "transit_days": 3, "recommendation": "Best value"},
                {"route": "Middle East -> Kandla", "rate_usd_mt": 17, "transit_days": 3, "recommendation": "Cheapest"},
                {"route": "UAE -> Mumbai", "rate_usd_mt": 28, "transit_days": 4, "recommendation": "Standard"},
            ]

        # ── 5. Port recommendation ──────────────────────────────────────────
        port_rec = {"port": "Mundra", "congestion_pct": 30, "reason": "Low congestion, priority-1 port"}
        if maritime_intel_engine is not None:
            try:
                ports = getattr(maritime_intel_engine, "INDIAN_PORTS", {})
                port_congestion = maritime.get("port_congestion", [])
                best_port = None
                best_score = 999
                for pc in port_congestion:
                    if pc.get("priority", 3) <= 2 and pc.get("score", 100) < best_score:
                        best_score = pc["score"]
                        best_port = pc
                if best_port:
                    port_rec = {
                        "port": best_port.get("port", "Mundra"),
                        "congestion_pct": best_port.get("score", 30),
                        "reason": f"Lowest congestion ({best_port.get('level', 'moderate')}) among priority ports",
                    }
            except Exception:
                pass

        # ── 6. Talking points ────────────────────────────────────────────────
        talking_points = [
            f"Current Brent crude is ${market.get('brent_usd', 'N/A')}/bbl — trend is {market.get('trend', 'stable')}.",
            f"Our target FOB is ${target_fob_val}/MT for {target_qty:.0f} MT cargo.",
            f"Preferred loading window: within 15-20 days of deal confirmation.",
            f"We accept both bulk vessel and container shipments to western India ports.",
            f"Recommended discharge port: {port_rec['port']} (congestion at {port_rec['congestion_pct']}%).",
            f"Payment: LC at sight or TT against BL — negotiable based on relationship.",
        ]
        if crude_forecast.get("direction") == "DOWN":
            talking_points.append(
                "Crude forecast is bearish — use this to negotiate lower FOB price."
            )
        elif crude_forecast.get("direction") == "UP":
            talking_points.append(
                "Crude forecast is bullish — consider locking FOB quickly before it rises."
            )
        talking_points.append(
            f"Quality requirement: VG-30 / VG-40 as per BIS IS:73 specification, with refinery test certificate."
        )

        # ── 7. Objection responses ──────────────────────────────────────────
        objection_responses = [
            {"objection": "FOB price is firm, no discount",
             "response": "We have multiple enquiries from Indian buyers. Can you match $"
                         f"{target_fob_val}/MT? We can increase quantity to {target_qty + 2000:.0f} MT."},
            {"objection": "Loading window is tight",
             "response": "We are flexible on port. If Mundra is congested, we can switch to "
                         "Kandla or Mangalore. This gives you more loading flexibility."},
            {"objection": "Payment must be advance TT",
             "response": "We can offer LC at sight through ICICI Bank. This protects both "
                         "parties and speeds up the transaction."},
        ]

        # ── 8. Closing strategy ─────────────────────────────────────────────
        closing_strategy = (
            f"Negotiate FOB to ${target_fob_val}/MT or lower. Offer to increase "
            f"quantity to {target_qty + 2000:.0f} MT as a sweetener. Lock the deal within "
            f"48 hours citing crude volatility. Confirm loading date commitment."
        )

        # ── 9. Follow-up actions ─────────────────────────────────────────────
        follow_up = [
            "Send formal enquiry on WhatsApp/email with target FOB and quantity.",
            "Request latest refinery test certificate and cargo specification sheet.",
            "Verify vessel availability and loading schedule at origin port.",
            "Get freight quotation from at least 2 shipping lines for comparison.",
            "Confirm LC terms with bank (ICICI) for the transaction value.",
        ]

        # ── 10. WhatsApp draft ───────────────────────────────────────────────
        whatsapp_draft = (
            f"Dear {name},\n\n"
            f"We are looking for *{target_qty:.0f} MT Bitumen VG-30* cargo.\n\n"
            f"Target FOB: *${target_fob_val}/MT*\n"
            f"Destination: {port_rec['port']}, India\n"
            f"Loading: Within 15-20 days\n"
            f"Payment: LC at sight / Negotiable\n\n"
            f"Current Brent: ${market.get('brent_usd', 'N/A')}/bbl\n\n"
            f"Please share your best FOB offer.\n\n"
            f"Regards,\n{self.company}"
        )

        return {
            "opening_context": (
                f"Market snapshot: {market.get('narrative', 'Stable market conditions.')} "
                f"Crude forecast: {crude_forecast.get('direction', 'STABLE')} "
                f"(confidence: {crude_forecast.get('confidence', 50)}%). "
                f"Last contact with {name}: {last_contact} days ago."
            ),
            "price_targets": {
                "market_fob": market_fob,
                "target_fob": target_fob_val,
                "floor_fob": floor_fob,
                "justification": (
                    f"Market FOB benchmark is ${market_fob}/MT. Our target ${target_fob_val}/MT "
                    f"is 5% below market. Floor price ${floor_fob}/MT represents 10% discount, "
                    f"below which the deal does not make commercial sense after duties and freight."
                ),
            },
            "freight_options": freight_options[:5],
            "port_recommendation": port_rec,
            "talking_points": talking_points,
            "objection_responses": objection_responses,
            "closing_strategy": closing_strategy,
            "follow_up_actions": follow_up,
            "whatsapp_draft": whatsapp_draft,
            "market_context": market,
            "crude_forecast": {
                "direction": crude_forecast.get("direction", "STABLE"),
                "confidence": crude_forecast.get("confidence", 50),
            },
            "supplier_db_info": {
                "country": db_supplier.get("country", country),
                "products": db_supplier.get("products", ""),
                "last_deal_price": last_price,
            },
        }

    # ══════════════════════════════════════════════════════════════════════════
    #  MODE 2: IMPORTER GUIDE — Indian Buyers
    # ══════════════════════════════════════════════════════════════════════════

    def _importer_guide(self, importer_info: dict) -> dict:
        """
        Build a discussion guide for talking to an Indian importer/buyer.

        party_info keys:
          name        : Buyer company name
          state       : Indian state
          city        : City (optional)
          product     : Grade (default VG-30)
          quantity_mt : Desired quantity (optional)
        """
        name = importer_info.get("name", "Buyer")
        state = importer_info.get("state", "Gujarat")
        city = importer_info.get("city", "")
        product = importer_info.get("product", "VG-30")
        quantity_mt = float(importer_info.get("quantity_mt", 100))

        # ── 1. CRM pre-fill ─────────────────────────────────────────────────
        db_customer = _get_customer_from_db(name)
        crm_profile = _get_crm_profile(name)
        crm_intel = crm_profile.get("intelligence", {})
        last_price = crm_intel.get("last_price")
        preferred_grade = crm_intel.get("preferred_grade", product)
        relationship = crm_intel.get("relationship_stage", "new")
        monthly_demand = crm_intel.get("expected_monthly_demand")

        # Use CRM city/state if not provided
        if not city:
            city = db_customer.get("city", crm_profile.get("basic", {}).get("city", "Vadodara"))
        if not state:
            state = db_customer.get("state", crm_profile.get("basic", {}).get("state", "Gujarat"))

        # ── 2. Regional demand forecast ──────────────────────────────────────
        demand_outlook: Dict[str, Any] = {
            "state": state,
            "demand_trend": "STABLE",
            "confidence": 55,
            "details": f"Standard demand outlook for {state}.",
        }
        if ml_forecast_engine is not None:
            try:
                forecast = ml_forecast_engine.forecast_state_demand(state, months_ahead=3)
                demand_outlook = {
                    "state": state,
                    "demand_trend": forecast.get("direction", "STABLE"),
                    "confidence": forecast.get("confidence", 55),
                    "details": (
                        f"{state} demand forecast: {forecast.get('direction', 'STABLE')} "
                        f"(model: {forecast.get('model', 'heuristic')}, "
                        f"confidence: {forecast.get('confidence', 55)}%). "
                        f"Monsoon factor: {forecast.get('monsoon_factor', 0.65)}."
                    ),
                }
            except Exception:
                pass

        # ── 3. Competitive pricing (3-tier offers) ───────────────────────────
        calc = self._get_calc()
        landed_cost = 0.0
        best_source = "Market average"
        alternatives: list[dict] = []

        if calc and city:
            try:
                sources = calc.find_best_sources(city, grade=preferred_grade or "VG30", top_n=3)
                if sources:
                    best = sources[0]
                    landed_cost = float(best.get("landed_cost", 0))
                    best_source = best.get("source", "Best available")
                    alternatives = sources[1:3]
            except Exception:
                pass

        if landed_cost <= 0:
            landed_cost = 42000  # fallback

        pricing_tiers = {
            "aggressive": round(landed_cost + self.min_margin),
            "balanced": round(landed_cost + self.balanced_add),
            "premium": round(landed_cost + self.premium_add),
            "landed_cost": round(landed_cost),
            "margin_per_mt": {
                "aggressive": self.min_margin,
                "balanced": self.balanced_add,
                "premium": self.premium_add,
            },
        }

        # ── 4. Inventory suggestion ──────────────────────────────────────────
        optimal_mt = quantity_mt
        reasoning = "Standard order size for new customer."
        if monthly_demand and float(monthly_demand) > 0:
            md = float(monthly_demand)
            optimal_mt = round(md * 1.5, 0)  # 1.5 months stock
            reasoning = (
                f"Based on expected monthly demand of {md:.0f} MT, we recommend "
                f"1.5-month buffer ({optimal_mt:.0f} MT) to optimize freight cost "
                f"and ensure supply continuity."
            )
        elif demand_outlook.get("demand_trend") == "UP":
            optimal_mt = round(quantity_mt * 1.3, 0)
            reasoning = (
                f"Demand in {state} is trending UP. Recommend stocking {optimal_mt:.0f} MT "
                f"to capture upcoming project demand before price revision."
            )

        inventory_suggestion = {
            "optimal_mt": optimal_mt,
            "reasoning": reasoning,
        }

        # ── 5. Delivery estimate ─────────────────────────────────────────────
        delivery_estimate = {
            "days": "3-5 business days",
            "route": f"Refinery/Terminal -> {city}",
            "port": best_source,
        }
        if alternatives:
            delivery_estimate["alternative_sources"] = [
                a.get("source", "") for a in alternatives
            ]

        # ── 6. Talking points ────────────────────────────────────────────────
        market = _get_market_context()
        talking_points = [
            f"Best landed cost for {city}: {_fmt_inr(landed_cost)}/MT (source: {best_source}).",
            f"Our offer: {_fmt_inr(pricing_tiers['balanced'])}/MT — competitive with guaranteed quality.",
            f"Dispatch within 48 hours of payment confirmation. GPS-tracked delivery.",
            f"All material comes with refinery test certificate and BIS compliance.",
            f"HSN: {_HSN_CODE}, GST: {self.gst_pct}% included in quoted rate.",
        ]
        if last_price and float(last_price) > 0:
            savings = float(last_price) - pricing_tiers["aggressive"]
            if savings > 0:
                talking_points.insert(1, (
                    f"Your last purchase was at {_fmt_inr(last_price)}/MT. "
                    f"We can offer {_fmt_inr(savings)}/MT savings at our aggressive rate."
                ))
            else:
                talking_points.insert(1, (
                    f"Market has moved since your last purchase at {_fmt_inr(last_price)}/MT. "
                    f"Current rate reflects updated crude and freight costs."
                ))
        if demand_outlook.get("demand_trend") == "UP":
            talking_points.append(
                f"Demand in {state} is rising. Lock rate now before next price revision."
            )
        talking_points.append(
            f"We supply to L&T, Dilip Buildcon, and other Tier-1 contractors."
        )

        # ── 7. Payment terms ─────────────────────────────────────────────────
        payment_terms = {
            "standard": self.payment_terms,
            "early_discount": "2% discount for payment within 24 hours of invoice.",
        }
        if relationship == "hot":
            payment_terms["relationship_bonus"] = (
                "As a valued regular customer, 50% advance + 50% at delivery is available."
            )

        # ── 8. Objection handling ────────────────────────────────────────────
        objection_responses = _get_objections_for_mode(self.MODE_IMPORTER)

        # ── 9. Follow-up actions ─────────────────────────────────────────────
        follow_up = [
            f"Send WhatsApp offer with {_fmt_inr(pricing_tiers['balanced'])}/MT rate.",
            "Schedule follow-up call within 2 hours if no response.",
            "Prepare detailed cost breakdown PDF if customer requests.",
            "Update CRM with discussion outcome and next action.",
            "If price objection: send competitor comparison showing our value.",
        ]

        # ── 10. WhatsApp draft ───────────────────────────────────────────────
        comm = self._get_comm()
        if comm:
            try:
                whatsapp_draft = comm.whatsapp_offer(
                    customer_name=name,
                    city=city,
                    grade=preferred_grade or "VG-30",
                    quantity_mt=quantity_mt,
                    price_per_mt=pricing_tiers["balanced"],
                    source=best_source,
                )
            except Exception:
                whatsapp_draft = self._fallback_whatsapp_importer(
                    name, city, preferred_grade or "VG-30", quantity_mt, pricing_tiers)
        else:
            whatsapp_draft = self._fallback_whatsapp_importer(
                name, city, preferred_grade or "VG-30", quantity_mt, pricing_tiers)

        return {
            "demand_outlook": demand_outlook,
            "pricing_tiers": pricing_tiers,
            "inventory_suggestion": inventory_suggestion,
            "delivery_estimate": delivery_estimate,
            "talking_points": talking_points,
            "payment_terms": payment_terms,
            "objection_responses": objection_responses,
            "follow_up_actions": follow_up,
            "whatsapp_draft": whatsapp_draft,
            "best_source": best_source,
            "alternatives": [
                {"source": a.get("source"), "landed_cost": a.get("landed_cost")}
                for a in alternatives
            ],
            "customer_crm": {
                "relationship": relationship,
                "last_price": last_price,
                "monthly_demand": monthly_demand,
                "preferred_grade": preferred_grade,
            },
        }

    def _fallback_whatsapp_importer(
        self, name: str, city: str, grade: str,
        qty: float, tiers: dict
    ) -> str:
        """Fallback WhatsApp message when CommunicationHub is unavailable."""
        return (
            f"*BITUMEN OFFER — {_today()}*\n"
            f"{name} | {city}\n\n"
            f"Grade: *{grade}*\n"
            f"Qty: *{qty:.0f} MT*\n"
            f"Rate: *{_fmt_inr(tiers.get('balanced', 0))}/MT* (Landed {city})\n\n"
            f"Dispatch: Within 48 hours\n"
            f"Validity: {self.quote_validity} hours only\n"
            f"Payment: {self.payment_terms}\n\n"
            f"Reply *CONFIRM* to lock this price\n\n"
            f"— {self.company}"
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  MODE 3: TRADER GUIDE — Local District Distributors
    # ══════════════════════════════════════════════════════════════════════════

    def _trader_guide(self, trader_info: dict) -> dict:
        """
        Build a discussion guide for talking to a local trader/distributor.

        party_info keys:
          name        : Trader/distributor name
          city        : City
          state       : State
          quantity_mt : Desired quantity (optional)
        """
        name = trader_info.get("name", "Trader")
        city = trader_info.get("city", "")
        state = trader_info.get("state", "")
        quantity_mt = float(trader_info.get("quantity_mt", 50))

        # ── 1. CRM pre-fill ─────────────────────────────────────────────────
        db_customer = _get_customer_from_db(name)
        crm_profile = _get_crm_profile(name)
        crm_intel = crm_profile.get("intelligence", {})
        last_price = crm_intel.get("last_price")
        relationship = crm_intel.get("relationship_stage", "new")

        if not city:
            city = db_customer.get("city", crm_profile.get("basic", {}).get("city", ""))
        if not state:
            state = db_customer.get("state", crm_profile.get("basic", {}).get("state", "Gujarat"))

        # ── 2. Local landed cost ─────────────────────────────────────────────
        calc = self._get_calc()
        our_landed_cost = 0.0
        best_source = "Market average"

        if calc and city:
            try:
                cost_data = calc.find_best_sources(city, grade="VG30", top_n=3)
                if cost_data:
                    best = cost_data[0]
                    our_landed_cost = float(best.get("landed_cost", 0))
                    best_source = best.get("source", "Best available")
            except Exception:
                pass

        if our_landed_cost <= 0:
            our_landed_cost = 42000  # fallback estimate

        # ── 3. Competitor pricing estimate (heuristic) ───────────────────────
        # Competitors typically operate at 5-15% above our cost
        competitor_avg = round(our_landed_cost * 1.08)  # ~8% above
        recommended_price = round(our_landed_cost + self.balanced_add)
        margin_pct = round(
            (recommended_price - our_landed_cost) / recommended_price * 100, 1
        ) if recommended_price > 0 else 0

        pricing_analysis = {
            "our_landed_cost": round(our_landed_cost),
            "our_landed_cost_formatted": _fmt_inr(our_landed_cost),
            "competitor_avg": competitor_avg,
            "competitor_avg_formatted": _fmt_inr(competitor_avg),
            "margin_pct": margin_pct,
            "recommended_price": recommended_price,
            "recommended_price_formatted": _fmt_inr(recommended_price),
        }

        # ── 4. Local demand intelligence ─────────────────────────────────────
        local_demand: Dict[str, Any] = {
            "projects": [],
            "demand_trend": "STABLE",
            "confidence": 50.0,
        }

        # Try to get infra projects from news/tender data
        try:
            news_data = _load_json(BASE / "tbl_news_feed.json")
            infra_keywords = {"highway", "road", "nhai", "tender", "construction",
                              "expressway", "bitumen", "asphalt", "paving"}
            relevant_projects: list[str] = []
            if isinstance(news_data, list):
                for article in news_data[-100:]:
                    title = (article.get("title") or "").lower()
                    if any(kw in title for kw in infra_keywords):
                        if state.lower() in title or city.lower() in title or not state:
                            relevant_projects.append(article.get("title", "Infrastructure project"))
            local_demand["projects"] = relevant_projects[:5]
        except Exception:
            pass

        # Demand forecast from ML engine
        if ml_forecast_engine is not None and state:
            try:
                forecast = ml_forecast_engine.forecast_state_demand(state, months_ahead=3)
                local_demand["demand_trend"] = forecast.get("direction", "STABLE")
                local_demand["confidence"] = forecast.get("confidence", 50)
            except Exception:
                pass

        # ── 5. Transport options ─────────────────────────────────────────────
        transport_options = [
            {
                "mode": "Bulk tanker",
                "cost_per_mt": round(self.bulk_rate_km * 300),  # avg 300km
                "delivery_days": "2-3",
            },
            {
                "mode": "Drum delivery",
                "cost_per_mt": round(self.drum_rate_km * 300),
                "delivery_days": "3-5",
            },
        ]

        # Try to get actual distance for more accurate estimate
        if calc and city:
            try:
                domestic = calc.calculate_domestic_landed_cost(
                    base_price=our_landed_cost * 0.85,  # approximate base before GST+freight
                    source=best_source,
                    destination=city,
                    load_type="Bulk",
                )
                dist = domestic.get("distance_km", 300)
                transport_options = [
                    {
                        "mode": "Bulk tanker",
                        "cost_per_mt": round(self.bulk_rate_km * dist),
                        "delivery_days": "2-3" if dist < 500 else "3-5",
                    },
                    {
                        "mode": "Drum delivery",
                        "cost_per_mt": round(self.drum_rate_km * dist),
                        "delivery_days": "3-5" if dist < 500 else "5-7",
                    },
                ]
            except Exception:
                pass

        # ── 6. Talking points ────────────────────────────────────────────────
        talking_points = [
            f"Our landed cost in {city or state}: {_fmt_inr(our_landed_cost)}/MT — direct from source, no middleman.",
            f"Recommended selling price for your market: {_fmt_inr(recommended_price)}/MT "
            f"(margin: {margin_pct}%).",
            f"We offer both bulk and drum delivery with GPS tracking.",
            f"Minimum order: 20 MT bulk / 100 drums. No upper limit.",
            f"Quality: BIS-certified VG-30/VG-40 with refinery test certificate on every load.",
            f"Competitor average in your area: ~{_fmt_inr(competitor_avg)}/MT — "
            f"you get better margins with our pricing.",
        ]
        if local_demand.get("demand_trend") == "UP":
            talking_points.append(
                f"Demand in {state} is growing. Good time to stock up and capture project orders."
            )
        if last_price and float(last_price) > 0:
            talking_points.append(
                f"Your last purchase was at {_fmt_inr(last_price)}/MT. Current rate reflects "
                f"latest market movement."
            )

        # ── 7. Competitor comparison ─────────────────────────────────────────
        competitor_comparison = [
            {
                "competitor": "Local PSU depot",
                "price": _fmt_inr(round(our_landed_cost * 1.05)),
                "advantage": "We match PSU quality at competitive pricing with faster dispatch.",
            },
            {
                "competitor": "Other traders",
                "price": _fmt_inr(round(our_landed_cost * 1.10)),
                "advantage": "Direct sourcing = better margins. No supply chain markup.",
            },
            {
                "competitor": "Import terminal",
                "price": _fmt_inr(round(our_landed_cost * 0.98)),
                "advantage": "We offer doorstep delivery + credit terms for regular orders.",
            },
        ]

        # ── 8. Storage advice ────────────────────────────────────────────────
        now_month = datetime.datetime.now(IST).month
        if now_month in (6, 7, 8, 9):
            storage_advice = (
                "Monsoon season: demand slows temporarily. Recommend maintaining minimum "
                "stock (1-month) and re-ordering as projects resume in October. "
                "Store drums in covered area to prevent water contamination."
            )
        elif now_month in (10, 11, 12, 1, 2, 3):
            storage_advice = (
                "Peak construction season. Recommend stocking 2-3 months' requirement "
                f"({round(quantity_mt * 2.5):.0f} MT) to avoid supply disruption during "
                "high-demand period. Bulk storage preferred for cost efficiency."
            )
        else:
            storage_advice = (
                "Transition period. Maintain 1.5-month stock. Watch for tender announcements "
                "and road project allocations that could drive sudden demand."
            )

        # ── 9. Objection handling ────────────────────────────────────────────
        objection_responses = _get_objections_for_mode(self.MODE_TRADER)

        # ── 10. Follow-up actions ────────────────────────────────────────────
        follow_up = [
            "Send WhatsApp with rate card and delivery schedule.",
            "Share territory exclusivity proposal if quantity commitment is 200+ MT/month.",
            "Update CRM with trader's territory details and competitor landscape.",
            f"Schedule site visit to {city} for relationship building.",
            "Send sample test certificate for quality assurance.",
        ]

        # ── 11. WhatsApp draft ───────────────────────────────────────────────
        whatsapp_draft = (
            f"Dear {name},\n\n"
            f"*Bitumen VG-30 Rate Card — {_today()}*\n\n"
            f"Landed {city or state}:\n"
            f"  Bulk: *{_fmt_inr(recommended_price)}/MT*\n"
            f"  Drum: *{_fmt_inr(round(recommended_price * 1.05))}/MT*\n\n"
            f"Min Order: 20 MT (bulk) / 100 drums\n"
            f"Dispatch: Within 48 hours\n"
            f"Payment: {self.payment_terms}\n"
            f"Validity: {self.quote_validity} hours\n\n"
            f"All rates inclusive of GST. Refinery test certificate provided.\n\n"
            f"Reply *ORDER* to confirm.\n\n"
            f"— {self.company}, Vadodara"
        )

        return {
            "local_demand": local_demand,
            "pricing_analysis": pricing_analysis,
            "transport_options": transport_options,
            "talking_points": talking_points,
            "competitor_comparison": competitor_comparison,
            "storage_advice": storage_advice,
            "objection_responses": objection_responses,
            "follow_up_actions": follow_up,
            "whatsapp_draft": whatsapp_draft,
            "best_source": best_source,
            "trader_crm": {
                "relationship": relationship,
                "last_price": last_price,
                "city": city,
                "state": state,
            },
        }

    # ══════════════════════════════════════════════════════════════════════════
    #  AI-ENHANCED TALKING POINTS
    # ══════════════════════════════════════════════════════════════════════════

    def generate_ai_talking_points(self, guide: dict, party_info: dict) -> str:
        """
        Use ai_fallback_engine to create a natural conversation flow
        from the structured guide data.

        Parameters
        ----------
        guide      : The output dict from prepare_discussion().
        party_info : The original party_info dict.

        Returns
        -------
        str — Natural-language conversation script.
        """
        if ask_with_fallback is None:
            return self._format_talking_points_fallback(guide, party_info)

        mode = guide.get("mode", "importer")
        name = party_info.get("name", "the party")

        # Build a concise context string for the AI
        context_parts = [
            f"Mode: {mode} discussion.",
            f"Party: {name}.",
        ]

        # Add pricing context
        if mode == "supplier":
            targets = guide.get("price_targets", {})
            context_parts.append(
                f"Target FOB: ${targets.get('target_fob', 'N/A')}/MT. "
                f"Market FOB: ${targets.get('market_fob', 'N/A')}/MT."
            )
        elif mode == "importer":
            tiers = guide.get("pricing_tiers", {})
            context_parts.append(
                f"Balanced offer: {_fmt_inr(tiers.get('balanced', 0))}/MT. "
                f"Aggressive: {_fmt_inr(tiers.get('aggressive', 0))}/MT."
            )
        elif mode == "trader":
            pa = guide.get("pricing_analysis", {})
            context_parts.append(
                f"Recommended price: {pa.get('recommended_price_formatted', 'N/A')}/MT. "
                f"Competitor avg: {pa.get('competitor_avg_formatted', 'N/A')}/MT."
            )

        # Add talking points
        points = guide.get("talking_points", [])
        if points:
            context_parts.append("Key points: " + " | ".join(points[:5]))

        # Add market context
        opening = guide.get("opening_context", "")
        if opening:
            context_parts.append(f"Market: {opening[:200]}")

        context_str = " ".join(context_parts)

        # Inject business context for negotiation-aware scripts
        biz_ctx = ""
        try:
            from business_context import get_business_context
            biz_ctx = get_business_context("negotiation") + "\n\n"
        except Exception:
            pass

        # Inject segment chatbot script if category is available
        segment_ctx = ""
        try:
            from business_context import get_segment_for_category, get_segment_chatbot_script
            category = party_info.get("category", "")
            if category:
                seg_key = get_segment_for_category(category)
                if seg_key:
                    script = get_segment_chatbot_script(seg_key)
                    if script:
                        segment_ctx = (
                            f"\nSegment: {seg_key}\n"
                            f"Greeting style: {script.get('greeting', '')}\n"
                            f"Pitch: {script.get('pitch', '')}\n"
                            f"Credit objection: {script.get('objection_credit', '')}\n"
                            f"Close: {script.get('close', '')}\n\n"
                        )
        except Exception:
            pass

        prompt = (
            f"You are PRINCE P SHAH (PPS), owner of PPS Anantam Corporation Pvt Ltd (PACPL), "
            f"Vadodara, Gujarat. 24 years experience. Commission Agent + Logistics Arranger.\n\n"
            f"{biz_ctx}{segment_ctx}"
            f"Generate a natural 2-minute conversation script for a {mode} discussion "
            f"with {name}. Use the following data:\n\n{context_str}\n\n"
            f"STRICT RULE: Payment is 100% Advance only. NEVER offer credit.\n"
            f"Structure: Opening greeting, market context (30 sec), our proposal (1 min), "
            f"handle likely objections (30 sec), close with next steps. "
            f"Keep it professional, confident, and data-driven. Use specific numbers."
        )

        try:
            result = ask_with_fallback(prompt, context=context_str)
            if isinstance(result, dict) and result.get("answer"):
                return str(result["answer"])
            elif isinstance(result, str):
                return result
        except Exception as exc:
            LOG.warning("AI talking points generation failed: %s", exc)

        return self._format_talking_points_fallback(guide, party_info)

    def _format_talking_points_fallback(self, guide: dict, party_info: dict) -> str:
        """Generate structured talking points without AI assistance."""
        mode = guide.get("mode", "importer")
        name = party_info.get("name", "Sir/Madam")
        points = guide.get("talking_points", [])

        lines = [
            f"=== DISCUSSION BRIEF: {name} ({mode.upper()}) ===\n",
            f"Generated: {guide.get('generated_at', _now())}\n",
            "OPENING:",
            f'  "Hello {name}, this is [Your Name] from PPS Anantam, Vadodara."\n',
        ]

        # Add market context
        opening = guide.get("opening_context", "")
        if opening:
            lines.append("MARKET CONTEXT:")
            lines.append(f'  "{opening[:300]}"\n')

        # Key talking points
        lines.append("KEY DISCUSSION POINTS:")
        for i, point in enumerate(points[:8], 1):
            lines.append(f"  {i}. {point}")

        # Objections
        objections = guide.get("objection_responses", [])
        if objections:
            lines.append("\nOBJECTION HANDLING:")
            for obj in objections[:4]:
                lines.append(f'  If: "{obj.get("objection", "")}"')
                lines.append(f'  Say: "{obj.get("response", "")}"')

        # Closing
        closing = guide.get("closing_strategy", "")
        if closing:
            lines.append(f"\nCLOSING STRATEGY:\n  {closing}")

        lines.append("\n=== END BRIEF ===")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def prepare_discussion(mode: str, party_info: dict) -> dict:
    """
    Module-level convenience function for dashboard use.
    Creates a DiscussionGuide instance and generates a brief.

    Parameters
    ----------
    mode       : 'supplier', 'importer', or 'trader'.
    party_info : Dict with party details.

    Returns
    -------
    dict — Complete discussion guide.
    """
    guide = DiscussionGuide()
    return guide.prepare_discussion(mode, party_info)


def prepare_supplier_discussion(supplier_info: dict) -> dict:
    """Convenience: generate a supplier discussion guide."""
    return prepare_discussion("supplier", supplier_info)


def prepare_importer_discussion(importer_info: dict) -> dict:
    """Convenience: generate an importer discussion guide."""
    return prepare_discussion("importer", importer_info)


def prepare_trader_discussion(trader_info: dict) -> dict:
    """Convenience: generate a local trader discussion guide."""
    return prepare_discussion("trader", trader_info)


def generate_ai_talking_points(guide: dict, party_info: dict) -> str:
    """
    Module-level convenience function.
    Generate AI-enhanced natural conversation script from a guide.
    """
    dg = DiscussionGuide()
    return dg.generate_ai_talking_points(guide, party_info)


def get_discussion_modes() -> list:
    """Return available discussion modes with descriptions."""
    return [
        {
            "mode": DiscussionGuide.MODE_SUPPLIER,
            "label": "Supplier Discussion",
            "description": "International cargo sellers — FOB, freight, loading, ports, payment",
            "icon": "ship",
        },
        {
            "mode": DiscussionGuide.MODE_IMPORTER,
            "label": "Importer/Buyer Discussion",
            "description": "Indian buyers — demand, pricing tiers, delivery, inventory, payment",
            "icon": "handshake",
        },
        {
            "mode": DiscussionGuide.MODE_TRADER,
            "label": "Local Trader Discussion",
            "description": "District distributors — local demand, transport, margins, storage",
            "icon": "truck",
        },
    ]


def get_engine_status() -> dict:
    """Return status of all dependencies used by the discussion guidance engine."""
    return {
        "engine": "discussion_guidance_engine",
        "version": "1.0",
        "status": "operational",
        "dependencies": {
            "calculation_engine": BitumenCalculationEngine is not None,
            "negotiation_engine": NegotiationAssistant is not None,
            "communication_engine": CommunicationHub is not None,
            "crm_engine": IntelligentCRM is not None,
            "ml_forecast_engine": ml_forecast_engine is not None,
            "market_intelligence_engine": MarketIntelligenceEngine is not None,
            "maritime_intel_engine": maritime_intel_engine is not None,
            "ai_fallback_engine": ask_with_fallback is not None,
            "database": True,  # always has fallback
        },
        "modes": [DiscussionGuide.MODE_SUPPLIER, DiscussionGuide.MODE_IMPORTER, DiscussionGuide.MODE_TRADER],
        "checked_at": _now(),
    }
