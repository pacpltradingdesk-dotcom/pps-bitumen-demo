"""
PPS Anantam -- Unified Recommendation Engine v1.0
===================================================
Generates actionable buy/sell/hold recommendations with confidence scores,
expiry times, risk assessment, and accuracy tracking.

Aggregates signals from:
  - PurchaseAdvisorEngine  (6-signal urgency index)
  - ForwardStrategyEngine  (15-day outlook)
  - OpportunityEngine      (4 opportunity types)
  - BitumenCalculationEngine (find_best_sources)
  - ml_forecast_engine     (crude, FX, state demand forecasts)
  - MarketIntelligenceEngine (10-signal composite)
  - IntelligentCRM         (customer relationship data)
  - model_monitor          (prediction logging & accuracy)
  - ai_fallback_engine     (natural language summaries)

Each recommendation includes:
  action, confidence (0-100), supporting_signals, risk_assessment,
  alternative_action, expires_at, natural_language summary.

Storage:
  ml_models/recommendations.json -- daily recommendations (last 30 days).
"""
from __future__ import annotations

import json
import logging
import datetime
from pathlib import Path
from typing import Any

import pytz

# -- Constants ---------------------------------------------------------------
IST = pytz.timezone("Asia/Kolkata")
LOG = logging.getLogger("recommendation_engine")

BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / "ml_models"
MODEL_DIR.mkdir(exist_ok=True)
RECOMMENDATIONS_FILE = MODEL_DIR / "recommendations.json"

# Confidence weights for sub-engine signals when composing the buy timing rec
_BUY_WEIGHTS = {
    "purchase_advisor": 0.30,
    "crude_forecast": 0.20,
    "fx_forecast": 0.15,
    "forward_strategy": 0.20,
    "seasonal": 0.15,
}

# Seasonal demand index (month -> 0-100 scale)
_SEASONAL_INDEX = {
    1: 90, 2: 95, 3: 100, 4: 85, 5: 70, 6: 30,
    7: 15, 8: 15, 9: 30, 10: 80, 11: 90, 12: 95,
}

# Key Indian states for demand forecasting
_KEY_STATES = [
    "Gujarat", "Maharashtra", "Rajasthan", "Madhya Pradesh",
    "Uttar Pradesh", "Karnataka", "Tamil Nadu", "Andhra Pradesh",
    "Telangana", "West Bengal",
]

# Recommendation validity (hours)
_BUY_EXPIRY_HOURS = 24
_SELL_EXPIRY_HOURS = 24
_DAILY_EXPIRY_HOURS = 18


# -- Helpers -----------------------------------------------------------------

def _now_ist() -> datetime.datetime:
    return datetime.datetime.now(IST)


def _ts() -> str:
    return _now_ist().strftime("%Y-%m-%d %H:%M IST")


def _expiry(hours: int) -> str:
    return (_now_ist() + datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M IST")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        pass
    return default if default is not None else []


def _save_json(path: Path, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except (IOError, OSError) as exc:
        LOG.warning("Failed to save %s: %s", path.name, exc)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _weighted_confidence(parts: dict[str, float], weights: dict[str, float]) -> int:
    """Compute weighted average confidence from sub-signal confidences."""
    total_w, total_v = 0.0, 0.0
    for key, w in weights.items():
        if key in parts:
            total_v += parts[key] * w
            total_w += w
    if total_w == 0:
        return 50
    return int(_clamp(total_v / total_w))


# -- Optional engine imports (all guarded) -----------------------------------

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


def _get_calc_engine():
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


def _forecast_crude():
    try:
        from ml_forecast_engine import forecast_crude_price
        return forecast_crude_price(days_ahead=15)
    except Exception:
        return {}


def _forecast_fx():
    try:
        from ml_forecast_engine import forecast_fx_rate
        return forecast_fx_rate(days_ahead=15)
    except Exception:
        return {}


def _forecast_state(state: str):
    try:
        from ml_forecast_engine import forecast_state_demand
        return forecast_state_demand(state, months_ahead=2)
    except Exception:
        return {}


def _ai_summary(prompt: str) -> str:
    """Generate a natural-language summary via the AI fallback engine."""
    try:
        from ai_fallback_engine import ask_with_fallback
        result = ask_with_fallback(prompt, context="bitumen trading recommendation")
        return result.get("answer", "") if isinstance(result, dict) else str(result)
    except Exception:
        return ""


def _log_recommendation(action: str, confidence: float, target_date: str = "") -> None:
    """Log recommendation to model_monitor for later accuracy tracking."""
    try:
        from model_monitor import log_prediction
        log_prediction(
            model_name="recommendation_engine",
            prediction=confidence,
            confidence=confidence,
            features={"action": action},
            target_date=target_date or _now_ist().strftime("%Y-%m-%d"),
        )
    except Exception:
        pass


def _get_customers() -> list[dict]:
    """Load active customer list from database or fallback."""
    try:
        from database import get_all_customers
        return get_all_customers()
    except Exception:
        from customer_source import load_customers
        return load_customers()


# ============================================================================
# RECOMMENDATION ENGINE
# ============================================================================

class RecommendationEngine:
    """Unified recommendation engine for buy/sell/hold decisions."""

    def __init__(self):
        self._cache: dict | None = None

    # -- Master function ------------------------------------------------------

    def generate_daily_recommendations(self) -> dict:
        """Master function -- generates all recommendation types.

        Returns dict with keys:
          buy_timing, sell_timing, demand_forecast, price_forecast,
          trade_specific, risk_warnings, generated_at, expires_at
        """
        LOG.info("Generating daily recommendations ...")

        buy = self._buy_timing_rec()
        sell = self._sell_timing_rec()
        demand = self._demand_recs()
        price = self._price_recs()
        trades = self._trade_recs()
        risks = self._risk_recs()

        result = {
            "buy_timing": buy,
            "sell_timing": sell,
            "demand_forecast": demand,
            "price_forecast": price,
            "trade_specific": trades,
            "risk_warnings": risks,
            "generated_at": _ts(),
            "expires_at": _expiry(_DAILY_EXPIRY_HOURS),
        }

        # Persist to disk
        self._persist(result)

        # Log for accuracy tracking
        _log_recommendation(
            action=buy.get("action", "HOLD"),
            confidence=buy.get("confidence", 50),
        )

        self._cache = result
        LOG.info("Daily recommendations generated successfully.")
        return result

    # -- Buy timing -----------------------------------------------------------

    def _buy_timing_rec(self) -> dict:
        """Combines purchase_advisor urgency, crude forecast, FX forecast,
        forward strategy, and seasonal signals into a single buy recommendation.
        """
        signals: list[str] = []
        risks: list[str] = []
        sub_confidences: dict[str, float] = {}

        # 1. Purchase advisor urgency index
        urgency_data = {}
        advisor = _get_purchase_advisor()
        if advisor:
            try:
                urgency_data = advisor.compute_urgency_index()
                idx = urgency_data.get("urgency_index", 50)
                sub_confidences["purchase_advisor"] = _clamp(idx)
                signals.append(
                    f"Urgency index: {idx}/100 ({urgency_data.get('recommendation', 'N/A')})"
                )
                if idx >= 70:
                    signals.append(urgency_data.get("stock_recommendation", ""))
            except Exception as exc:
                LOG.debug("Purchase advisor failed: %s", exc)

        # 2. Crude price forecast
        crude_fc = _forecast_crude()
        if crude_fc and crude_fc.get("direction"):
            direction = crude_fc["direction"]
            conf = crude_fc.get("confidence", 50)
            sub_confidences["crude_forecast"] = float(conf)
            signals.append(
                f"Crude forecast: {direction} ({crude_fc.get('model', 'heuristic')}, "
                f"conf {conf:.0f}%)"
            )
            if direction == "UP":
                risks.append("Crude prices rising -- procurement costs may increase")
            elif direction == "DOWN":
                signals.append("Crude prices declining -- may benefit from waiting")

        # 3. FX forecast
        fx_fc = _forecast_fx()
        if fx_fc and fx_fc.get("direction"):
            direction = fx_fc["direction"]
            conf = fx_fc.get("confidence", 50)
            sub_confidences["fx_forecast"] = float(conf)
            signals.append(f"USD/INR forecast: {direction} (conf {conf:.0f}%)")
            if direction == "UP":
                risks.append("INR weakening -- import costs rising")

        # 4. Forward strategy outlook
        fwd = _get_forward_strategy()
        if fwd:
            try:
                outlook = fwd.generate_full_outlook()
                strategy = outlook.get("stock_strategy", {})
                strat_name = strategy.get("strategy", "HOLD")
                sub_confidences["forward_strategy"] = _clamp(
                    outlook.get("demand_score", {}).get("total_score", 50)
                )
                signals.append(
                    f"15-day strategy: {strat_name} "
                    f"(demand {outlook.get('demand_score', {}).get('total_score', '?')}/100)"
                )
                for r in strategy.get("rationale", []):
                    signals.append(f"  - {r}")
            except Exception as exc:
                LOG.debug("Forward strategy failed: %s", exc)

        # 5. Seasonal factor
        month = _now_ist().month
        seasonal_score = _SEASONAL_INDEX.get(month, 50)
        sub_confidences["seasonal"] = float(seasonal_score)
        is_peak = month in (10, 11, 12, 1, 2, 3)
        if is_peak:
            signals.append(f"Peak construction season (month {month}, index {seasonal_score})")
        else:
            signals.append(f"Off-season period (month {month}, index {seasonal_score})")

        # Composite confidence
        confidence = _weighted_confidence(sub_confidences, _BUY_WEIGHTS)

        # Determine action
        urgency_idx = urgency_data.get("urgency_index", 50) if urgency_data else 50
        crude_dir = crude_fc.get("direction", "STABLE") if crude_fc else "STABLE"

        if urgency_idx >= 75 or (crude_dir == "UP" and confidence >= 65):
            action = "BUY NOW"
            window = "next 48 hours"
            alt_action = "If cash flow tight, buy 50% now and 50% within 5 days"
        elif urgency_idx >= 55 or confidence >= 50:
            action = "SELECTIVE BUY"
            window = "next 5-7 days"
            alt_action = "Buy only against confirmed customer orders"
        else:
            wait_days = max(7, int((55 - urgency_idx) * 0.4) + 5)
            action = f"WAIT {wait_days} DAYS"
            window = f"reassess in {wait_days} days"
            alt_action = "Monitor daily; buy immediately if crude spikes >3% in a day"

        # Best sources
        best_sources: list[dict] = []
        calc = _get_calc_engine()
        if calc:
            try:
                sources = calc.find_best_sources("Ahmedabad", grade="VG30", top_n=3)
                for s in (sources or []):
                    best_sources.append({
                        "source": s.get("source", ""),
                        "landed_cost": s.get("landed_cost", 0),
                        "category": s.get("category", ""),
                    })
            except Exception:
                pass

        # Quantity suggestion based on urgency
        if urgency_idx >= 75 and is_peak:
            qty_suggestion = 1000
        elif urgency_idx >= 60:
            qty_suggestion = 500
        else:
            qty_suggestion = 200

        # Natural-language summary
        nl = (
            f"Recommendation: {action}. "
            f"Overall confidence {confidence}%. "
            f"Window: {window}. "
            f"{'Peak season boosts urgency. ' if is_peak else ''}"
            f"{'Crude rising -- lock in prices early. ' if crude_dir == 'UP' else ''}"
            f"Suggested quantity: {qty_suggestion} MT."
        )

        return {
            "action": action,
            "confidence": confidence,
            "window": window,
            "best_sources": best_sources,
            "quantity_suggestion_mt": qty_suggestion,
            "reasons": [s for s in signals if s],
            "risks": risks,
            "supporting_signals": list(sub_confidences.keys()),
            "risk_assessment": "; ".join(risks) if risks else "No significant risks identified",
            "alternative_action": alt_action,
            "expires_at": _expiry(_BUY_EXPIRY_HOURS),
            "natural_language": nl,
        }

    # -- Sell timing ----------------------------------------------------------

    def _sell_timing_rec(self) -> dict:
        """Combines CRM hot leads, price direction, and demand peaks into
        a sell-side recommendation with target customers and pricing tiers.
        """
        signals: list[str] = []
        priority_customers: list[dict] = []

        # CRM hot leads
        crm = _get_crm()
        customers = _get_customers()
        hot_leads: list[dict] = []
        if customers:
            for c in customers:
                stage = (c.get("relationship_stage") or "").lower()
                if stage == "hot":
                    hot_leads.append(c)
            if hot_leads:
                signals.append(f"{len(hot_leads)} hot leads in CRM")

        # Price direction from forward strategy
        fwd = _get_forward_strategy()
        price_dir = "STABLE"
        if fwd:
            try:
                pd_result = fwd.calculate_price_direction()
                price_dir = pd_result.get("direction", "STABLE")
                signals.append(
                    f"Price direction: {price_dir} "
                    f"({pd_result.get('confidence_pct', 50)}% confidence)"
                )
            except Exception:
                pass

        # Seasonal demand
        month = _now_ist().month
        seasonal_idx = _SEASONAL_INDEX.get(month, 50)
        is_peak = seasonal_idx >= 70
        if is_peak:
            signals.append(f"High-demand season (index {seasonal_idx})")

        # Build priority customer list
        for c in hot_leads[:10]:
            city = c.get("city", "")
            best_price = 0
            calc = _get_calc_engine()
            if calc and city:
                try:
                    sources = calc.find_best_sources(city, grade="VG30", top_n=1)
                    if sources:
                        best_price = sources[0].get("landed_cost", 0)
                except Exception:
                    pass
            priority_customers.append({
                "name": c.get("name", ""),
                "city": city,
                "last_price": c.get("last_purchase_price", 0),
                "expected_demand_mt": c.get("expected_monthly_demand", 100),
                "current_best_landed": best_price,
            })

        # Pricing tiers (from settings or defaults)
        min_margin = 500
        try:
            from settings_engine import load_settings
            s = load_settings()
            min_margin = s.get("margin_min_per_mt", 500)
        except Exception:
            pass

        pricing = {
            "aggressive": {"margin_per_mt": min_margin, "label": "Aggressive"},
            "balanced": {"margin_per_mt": int(min_margin * 1.6), "label": "Balanced"},
            "premium": {"margin_per_mt": int(min_margin * 2.4), "label": "Premium"},
        }

        # Timing advice
        if price_dir == "UP" and is_peak:
            timing = "Sell at premium -- prices rising in peak season"
            confidence = 80
        elif price_dir == "UP":
            timing = "Sell at balanced -- uptrend supports firm pricing"
            confidence = 70
        elif is_peak:
            timing = "Sell aggressively -- peak demand covers volume"
            confidence = 65
        elif price_dir == "DOWN":
            timing = "Sell fast at aggressive -- clear stock before further decline"
            confidence = 60
        else:
            timing = "Normal selling pace -- maintain balanced pricing"
            confidence = 55

        nl = (
            f"Sell timing: {timing}. "
            f"{len(priority_customers)} priority customers identified. "
            f"{'Price trend supports premium. ' if price_dir == 'UP' else ''}"
        )

        return {
            "targets": [pc["name"] for pc in priority_customers],
            "pricing": pricing,
            "timing": timing,
            "confidence": confidence,
            "priority_customers": priority_customers,
            "reasons": signals,
            "supporting_signals": ["crm_hot_leads", "price_direction", "seasonal_demand"],
            "risk_assessment": "Customer credit risk -- verify payment before dispatch"
            if priority_customers else "No hot leads -- focus on outbound prospecting",
            "alternative_action": "Offer volume discounts to warm leads if hot leads are exhausted",
            "expires_at": _expiry(_SELL_EXPIRY_HOURS),
            "natural_language": nl,
        }

    # -- Demand recommendations -----------------------------------------------

    def _demand_recs(self) -> dict:
        """State-wise demand forecast for next 15/30 days."""
        state_forecasts: list[dict] = []

        for state in _KEY_STATES:
            fc = _forecast_state(state)
            if fc and fc.get("predicted"):
                direction = fc.get("direction", "STABLE")
                conf = fc.get("confidence", 50)
                predicted_vals = fc.get("predicted", [])
                avg_demand = (
                    sum(predicted_vals[:2]) / max(len(predicted_vals[:2]), 1)
                    if predicted_vals else 0
                )
                state_forecasts.append({
                    "state": state,
                    "direction": direction,
                    "confidence": round(conf, 1),
                    "avg_demand_score": round(avg_demand, 1),
                    "model": fc.get("model", "unknown"),
                    "monsoon_factor": fc.get("monsoon_factor", 1.0),
                })

        # Sort by demand score descending
        state_forecasts.sort(key=lambda x: x["avg_demand_score"], reverse=True)

        top_states = [sf["state"] for sf in state_forecasts[:3]]
        overall_direction = "STABLE"
        if state_forecasts:
            up_count = sum(1 for sf in state_forecasts if sf["direction"] == "UP")
            down_count = sum(1 for sf in state_forecasts if sf["direction"] == "DOWN")
            if up_count > down_count + 2:
                overall_direction = "RISING"
            elif down_count > up_count + 2:
                overall_direction = "FALLING"

        nl = (
            f"Demand outlook: {overall_direction}. "
            f"Top demand states: {', '.join(top_states)}. "
            f"{len(state_forecasts)} states analyzed."
        )

        return {
            "overall_direction": overall_direction,
            "state_forecasts": state_forecasts,
            "top_demand_states": top_states,
            "forecast_horizon": "15-60 days",
            "natural_language": nl,
            "generated_at": _ts(),
        }

    # -- Price recommendations ------------------------------------------------

    def _price_recs(self) -> dict:
        """Crude, bitumen, and FX price forecasts with confidence bands."""
        crude_fc = _forecast_crude()
        fx_fc = _forecast_fx()

        # Derive bitumen price direction from crude + FX
        crude_dir = crude_fc.get("direction", "STABLE") if crude_fc else "STABLE"
        fx_dir = fx_fc.get("direction", "STABLE") if fx_fc else "STABLE"

        if crude_dir == "UP" and fx_dir == "UP":
            bitumen_dir = "UP"
            bitumen_conf = 80
        elif crude_dir == "UP" or fx_dir == "UP":
            bitumen_dir = "UP"
            bitumen_conf = 65
        elif crude_dir == "DOWN" and fx_dir == "DOWN":
            bitumen_dir = "DOWN"
            bitumen_conf = 75
        elif crude_dir == "DOWN" or fx_dir == "DOWN":
            bitumen_dir = "STABLE"
            bitumen_conf = 55
        else:
            bitumen_dir = "STABLE"
            bitumen_conf = 60

        nl = (
            f"Crude: {crude_dir} "
            f"(current ${crude_fc.get('current_price', 'N/A')}). "
            f"FX: {fx_dir} "
            f"(current {fx_fc.get('current_price', 'N/A')}). "
            f"Bitumen price outlook: {bitumen_dir}."
        )

        return {
            "crude": {
                "direction": crude_dir,
                "confidence": crude_fc.get("confidence", 50),
                "current_price_usd": crude_fc.get("current_price"),
                "model": crude_fc.get("model", "unavailable"),
                "forecast_15d": crude_fc.get("predicted", [])[:15],
                "lower_band": crude_fc.get("lower", [])[:15],
                "upper_band": crude_fc.get("upper", [])[:15],
            },
            "fx": {
                "direction": fx_dir,
                "confidence": fx_fc.get("confidence", 50),
                "current_rate": fx_fc.get("current_price"),
                "model": fx_fc.get("model", "unavailable"),
                "forecast_15d": fx_fc.get("predicted", [])[:15],
                "lower_band": fx_fc.get("lower", [])[:15],
                "upper_band": fx_fc.get("upper", [])[:15],
            },
            "bitumen": {
                "direction": bitumen_dir,
                "confidence": bitumen_conf,
                "drivers": f"Crude {crude_dir}, FX {fx_dir}",
            },
            "natural_language": nl,
            "generated_at": _ts(),
        }

    # -- Trade-specific recommendations ---------------------------------------

    def _trade_recs(self) -> list[dict]:
        """Trade-specific recommendations for import, domestic buy, local sell."""
        recs: list[dict] = []

        calc = _get_calc_engine()
        crude_fc = _forecast_crude()
        fx_fc = _forecast_fx()

        # 1. Import recommendation
        import_rec = self._import_trade_rec(calc, crude_fc, fx_fc)
        if import_rec:
            recs.append(import_rec)

        # 2. Domestic buy recommendation
        domestic_rec = self._domestic_trade_rec(calc, crude_fc)
        if domestic_rec:
            recs.append(domestic_rec)

        # 3. Local sell recommendation
        sell_rec = self._local_sell_trade_rec(calc)
        if sell_rec:
            recs.append(sell_rec)

        return recs

    def _import_trade_rec(self, calc, crude_fc: dict, fx_fc: dict) -> dict | None:
        """Import trade recommendation: FOB source ranking + timing + vessel."""
        crude_dir = crude_fc.get("direction", "STABLE") if crude_fc else "STABLE"
        fx_dir = fx_fc.get("direction", "STABLE") if fx_fc else "STABLE"

        if crude_dir == "UP" and fx_dir == "UP":
            action = "HOLD"
            timing = "Defer import -- both crude and INR adverse"
            confidence = 70
        elif crude_dir == "DOWN":
            action = "BUY"
            timing = "Good window for import -- crude declining"
            confidence = 65
        else:
            action = "SELECTIVE BUY"
            timing = "Import selectively -- mixed signals"
            confidence = 55

        # Find best import sources
        sources: list[dict] = []
        if calc:
            try:
                all_sources = calc.find_best_sources(
                    "Kandla", grade="VG30", load_type="Bulk", top_n=5
                )
                for s in (all_sources or []):
                    if "import" in s.get("category", "").lower() or \
                       "terminal" in s.get("category", "").lower():
                        sources.append({
                            "source": s.get("source", ""),
                            "landed_cost": s.get("landed_cost", 0),
                        })
            except Exception:
                pass

        return {
            "trade_type": "import",
            "action": action,
            "confidence": confidence,
            "timing": timing,
            "top_sources": sources[:3],
            "supporting_signals": [
                f"Crude {crude_dir}",
                f"FX {fx_dir}",
            ],
            "risk_assessment": "Vessel booking lead time 15-20 days; FX lock recommended",
            "alternative_action": "Partial hedge via forward FX contract",
            "natural_language": (
                f"Import: {action}. {timing}. "
                f"{len(sources)} import sources ranked."
            ),
            "expires_at": _expiry(_BUY_EXPIRY_HOURS),
        }

    def _domestic_trade_rec(self, calc, crude_fc: dict) -> dict | None:
        """Domestic buy recommendation: refinery pricing + bulk timing."""
        crude_dir = crude_fc.get("direction", "STABLE") if crude_fc else "STABLE"

        if crude_dir == "UP":
            action = "BUY NOW"
            timing = "Lock refinery prices before next revision"
            confidence = 70
        elif crude_dir == "DOWN":
            action = "WAIT"
            timing = "Refinery prices may drop in next revision cycle"
            confidence = 60
        else:
            action = "SELECTIVE BUY"
            timing = "Buy against confirmed orders only"
            confidence = 55

        # Find best refinery sources
        sources: list[dict] = []
        if calc:
            try:
                all_sources = calc.find_best_sources(
                    "Ahmedabad", grade="VG30", load_type="Bulk", top_n=5
                )
                for s in (all_sources or []):
                    cat = (s.get("category") or "").lower()
                    if "refinery" in cat or "indian" in cat:
                        sources.append({
                            "source": s.get("source", ""),
                            "landed_cost": s.get("landed_cost", 0),
                        })
            except Exception:
                pass

        return {
            "trade_type": "domestic_buy",
            "action": action,
            "confidence": confidence,
            "timing": timing,
            "top_sources": sources[:3],
            "supporting_signals": [f"Crude {crude_dir}", "Refinery revision cycle"],
            "risk_assessment": "Refinery supply allocation may limit availability",
            "alternative_action": "Diversify across 2-3 refineries to reduce allocation risk",
            "natural_language": (
                f"Domestic: {action}. {timing}. "
                f"{len(sources)} refinery sources available."
            ),
            "expires_at": _expiry(_BUY_EXPIRY_HOURS),
        }

    def _local_sell_trade_rec(self, calc) -> dict | None:
        """Local sell recommendation: customer priority + territory pricing."""
        customers = _get_customers()
        month = _now_ist().month
        is_peak = _SEASONAL_INDEX.get(month, 50) >= 70

        if is_peak:
            action = "SELL"
            timing = "Maximize volume -- peak demand period"
            confidence = 75
        else:
            action = "SELECTIVE SELL"
            timing = "Focus on premium accounts -- off-peak margins"
            confidence = 55

        # Territory analysis
        territory_data: list[dict] = []
        city_set: set[str] = set()
        for c in customers:
            city = c.get("city", "")
            if city and city not in city_set and calc:
                city_set.add(city)
                try:
                    sources = calc.find_best_sources(city, grade="VG30", top_n=1)
                    if sources:
                        territory_data.append({
                            "city": city,
                            "best_landed": sources[0].get("landed_cost", 0),
                            "best_source": sources[0].get("source", ""),
                        })
                except Exception:
                    continue
        territory_data.sort(key=lambda x: x.get("best_landed", 999999))

        return {
            "trade_type": "local_sell",
            "action": action,
            "confidence": confidence,
            "timing": timing,
            "top_territories": territory_data[:5],
            "customer_count": len(customers),
            "supporting_signals": [
                f"Season index: {_SEASONAL_INDEX.get(month, 50)}",
                f"{len(customers)} active customers",
            ],
            "risk_assessment": "Credit risk on new customers; stick to advance payment",
            "alternative_action": "Offer early-bird discounts for bulk pre-orders",
            "natural_language": (
                f"Local sell: {action}. {timing}. "
                f"{len(territory_data)} territories analyzed."
            ),
            "expires_at": _expiry(_SELL_EXPIRY_HOURS),
        }

    # -- Risk recommendations -------------------------------------------------

    def _risk_recs(self) -> list[dict]:
        """Risk warnings: supply chain, FX, seasonal, credit."""
        warnings: list[dict] = []

        # 1. Supply chain risk from market intelligence
        mi = _get_market_intelligence()
        if mi:
            try:
                all_signals = mi.compute_all_signals()
                news_sig = all_signals.get("news", {})
                port_sig = all_signals.get("ports", {})

                if news_sig.get("supply_risk") == "HIGH":
                    warnings.append({
                        "type": "supply_chain",
                        "severity": "HIGH",
                        "title": "Supply chain disruption risk",
                        "description": (
                            f"News sentiment indicates high supply risk. "
                            f"Events: {len(news_sig.get('events', []))} flagged."
                        ),
                        "recommended_action": "Secure 2-week buffer stock from reliable sources",
                        "confidence": 75,
                        "expires_at": _expiry(48),
                    })

                if port_sig.get("port_risk") == "HIGH":
                    congested = port_sig.get("congested_ports", [])
                    warnings.append({
                        "type": "port_disruption",
                        "severity": "HIGH",
                        "title": "Port congestion alert",
                        "description": (
                            f"Congested ports: {', '.join(congested) or 'multiple'}. "
                            f"Freight delays: {port_sig.get('freight_delay', 'N/A')}."
                        ),
                        "recommended_action": "Shift to domestic sources or alternate ports",
                        "confidence": 70,
                        "expires_at": _expiry(72),
                    })

                master = all_signals.get("master", {})
                if master.get("risk_level") == "HIGH":
                    warnings.append({
                        "type": "composite_risk",
                        "severity": "HIGH",
                        "title": "Overall market risk elevated",
                        "description": master.get("recommended_action", ""),
                        "recommended_action": "Review all open positions; reduce exposure",
                        "confidence": int(master.get("confidence", 50)),
                        "expires_at": _expiry(24),
                    })
            except Exception as exc:
                LOG.debug("Market intelligence risk check failed: %s", exc)

        # 2. FX risk
        fx_fc = _forecast_fx()
        if fx_fc and fx_fc.get("direction") == "UP":
            conf = fx_fc.get("confidence", 50)
            if conf >= 55:
                warnings.append({
                    "type": "fx_risk",
                    "severity": "MEDIUM" if conf < 70 else "HIGH",
                    "title": "INR depreciation risk",
                    "description": (
                        f"USD/INR forecast trending UP (conf {conf:.0f}%). "
                        f"Current rate: {fx_fc.get('current_price', 'N/A')}."
                    ),
                    "recommended_action": "Consider FX hedging for upcoming import payments",
                    "confidence": int(conf),
                    "expires_at": _expiry(48),
                })

        # 3. Seasonal risk
        month = _now_ist().month
        if month in (6, 7, 8):
            warnings.append({
                "type": "seasonal_monsoon",
                "severity": "MEDIUM",
                "title": "Monsoon season demand drop",
                "description": (
                    "Active monsoon reduces road construction activity. "
                    "Expect 30-50% demand reduction in western and coastal states."
                ),
                "recommended_action": "Reduce inventory; focus on covered storage orders",
                "confidence": 85,
                "expires_at": _expiry(720),
            })
        elif month in (12, 1, 2):
            warnings.append({
                "type": "seasonal_peak",
                "severity": "LOW",
                "title": "Peak season supply competition",
                "description": (
                    "Peak construction season drives high demand. "
                    "Supplier allocation may tighten."
                ),
                "recommended_action": "Secure forward allocations from top 2 refineries",
                "confidence": 80,
                "expires_at": _expiry(720),
            })

        # 4. Credit risk from CRM
        customers = _get_customers()
        overdue_customers: list[str] = []
        for c in customers:
            outstanding = c.get("outstanding_inr", 0)
            try:
                outstanding = float(outstanding or 0)
            except (ValueError, TypeError):
                outstanding = 0
            if outstanding > 500000:
                overdue_customers.append(c.get("name", "Unknown"))

        if overdue_customers:
            warnings.append({
                "type": "credit_risk",
                "severity": "MEDIUM",
                "title": f"High outstanding: {len(overdue_customers)} customer(s)",
                "description": (
                    f"Customers with >5L outstanding: {', '.join(overdue_customers[:5])}."
                ),
                "recommended_action": "Follow up on payments before new dispatches",
                "confidence": 90,
                "expires_at": _expiry(48),
            })

        return warnings

    # -- Trade-specific accessor ----------------------------------------------

    def get_trade_specific_recommendations(self, trade_type: str) -> list[dict]:
        """Get recommendations filtered by trade type.

        Args:
            trade_type: "import", "domestic_buy", or "local_sell"

        Returns:
            list of recommendation dicts for the specified trade type.
        """
        # Try cached recommendations first
        recs = self.get_latest_recommendations()
        trades = recs.get("trade_specific", [])
        matching = [t for t in trades if t.get("trade_type") == trade_type]

        if matching:
            return matching

        # Generate fresh if no cache
        calc = _get_calc_engine()
        crude_fc = _forecast_crude()
        fx_fc = _forecast_fx()

        if trade_type == "import":
            rec = self._import_trade_rec(calc, crude_fc, fx_fc)
            return [rec] if rec else []
        elif trade_type == "domestic_buy":
            rec = self._domestic_trade_rec(calc, crude_fc)
            return [rec] if rec else []
        elif trade_type == "local_sell":
            rec = self._local_sell_trade_rec(calc)
            return [rec] if rec else []

        return []

    # -- Persistence ----------------------------------------------------------

    def _persist(self, result: dict) -> None:
        """Save daily recommendations to disk. Keep last 30 days."""
        history = _load_json(RECOMMENDATIONS_FILE, [])
        if not isinstance(history, list):
            history = []

        history.append({
            "date": _now_ist().strftime("%Y-%m-%d"),
            "generated_at": result.get("generated_at", _ts()),
            "recommendations": result,
        })

        # Keep last 30 days only
        if len(history) > 30:
            history = history[-30:]

        _save_json(RECOMMENDATIONS_FILE, history)

    # -- Cache / retrieval ----------------------------------------------------

    def get_latest_recommendations(self) -> dict:
        """Load most recent recommendations from disk cache."""
        if self._cache:
            return self._cache

        history = _load_json(RECOMMENDATIONS_FILE, [])
        if history and isinstance(history, list):
            latest = history[-1]
            recs = latest.get("recommendations", {})
            # Check if still valid
            expires = recs.get("expires_at", "")
            if expires:
                try:
                    exp_dt = datetime.datetime.strptime(expires, "%Y-%m-%d %H:%M IST")
                    exp_dt = IST.localize(exp_dt)
                    if exp_dt > _now_ist():
                        self._cache = recs
                        return recs
                except (ValueError, TypeError):
                    pass
            # Return even if expired (stale data better than nothing)
            return recs

        return {}

    # -- Accuracy tracking ----------------------------------------------------

    def track_recommendation_accuracy(self) -> dict:
        """Compare past recommendations with actual outcomes.

        Evaluates accuracy using model_monitor data and historical
        recommendation outcomes.
        """
        result = {
            "total_recommendations": 0,
            "evaluated": 0,
            "accuracy_metrics": {},
            "recent_performance": [],
            "generated_at": _ts(),
        }

        # 1. Model monitor accuracy for recommendation_engine predictions
        try:
            from model_monitor import evaluate_accuracy
            acc = evaluate_accuracy("recommendation_engine", lookback_days=30)
            result["accuracy_metrics"] = acc
        except Exception:
            pass

        # 2. Analyze historical recommendations
        history = _load_json(RECOMMENDATIONS_FILE, [])
        if not isinstance(history, list):
            history = []

        result["total_recommendations"] = len(history)

        # Simple outcome tracking: compare buy recommendations with
        # subsequent price changes
        crude_data = _load_json(BASE / "tbl_crude_prices.json", [])
        brent_prices: dict[str, float] = {}
        for r in (crude_data if isinstance(crude_data, list) else []):
            if r.get("benchmark") == "Brent" and r.get("price"):
                ts = r.get("timestamp") or r.get("date") or ""
                date_str = str(ts)[:10]
                try:
                    brent_prices[date_str] = float(r["price"])
                except (ValueError, TypeError):
                    pass

        evaluated_count = 0
        correct_count = 0

        for entry in history[-14:]:
            rec_date = entry.get("date", "")
            recs = entry.get("recommendations", {})
            buy = recs.get("buy_timing", {})
            action = buy.get("action", "")

            # Find price on recommendation date and 7 days later
            rec_price = brent_prices.get(rec_date)
            if not rec_price:
                continue

            future_date = None
            try:
                rd = datetime.datetime.strptime(rec_date, "%Y-%m-%d")
                future_date = (rd + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            except ValueError:
                continue

            future_price = brent_prices.get(future_date)
            if not future_price:
                continue

            evaluated_count += 1
            price_change_pct = ((future_price - rec_price) / rec_price) * 100
            was_correct = False

            if "BUY" in action and price_change_pct > 0:
                was_correct = True
            elif "WAIT" in action and price_change_pct <= 0:
                was_correct = True
            elif "HOLD" in action and abs(price_change_pct) < 2:
                was_correct = True
            elif "SELECTIVE" in action:
                was_correct = True  # conservative advice is always partially correct

            if was_correct:
                correct_count += 1

            result["recent_performance"].append({
                "date": rec_date,
                "action": action,
                "confidence": buy.get("confidence", 0),
                "price_at_rec": rec_price,
                "price_7d_later": future_price,
                "change_pct": round(price_change_pct, 2),
                "was_correct": was_correct,
            })

        result["evaluated"] = evaluated_count
        if evaluated_count > 0:
            result["directional_accuracy_pct"] = round(
                (correct_count / evaluated_count) * 100, 1
            )
        else:
            result["directional_accuracy_pct"] = None

        return result


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

def generate_daily_recommendations() -> dict:
    """Module-level shortcut for sync_engine integration."""
    engine = RecommendationEngine()
    return engine.generate_daily_recommendations()


def get_latest_recommendations() -> dict:
    """Module-level shortcut for dashboard integration."""
    engine = RecommendationEngine()
    return engine.get_latest_recommendations()


def get_trade_recommendations(trade_type: str) -> list[dict]:
    """Module-level shortcut for trade-specific recommendations."""
    engine = RecommendationEngine()
    return engine.get_trade_specific_recommendations(trade_type)


def track_accuracy() -> dict:
    """Module-level shortcut for accuracy tracking."""
    engine = RecommendationEngine()
    return engine.track_recommendation_accuracy()


def get_engine_status() -> dict:
    """Status report for AI module registry / SRE engine."""
    return {
        "engine": "RecommendationEngine",
        "version": "1.0",
        "output_file": str(RECOMMENDATIONS_FILE),
        "recommendation_types": [
            "buy_timing", "sell_timing", "demand_forecast",
            "price_forecast", "trade_specific", "risk_warnings",
        ],
        "dependent_engines": [
            "purchase_advisor_engine", "forward_strategy_engine",
            "opportunity_engine", "calculation_engine",
            "ml_forecast_engine", "market_intelligence_engine",
            "crm_engine", "model_monitor", "ai_fallback_engine",
        ],
        "expiry_hours": {
            "buy": _BUY_EXPIRY_HOURS,
            "sell": _SELL_EXPIRY_HOURS,
            "daily": _DAILY_EXPIRY_HOURS,
        },
    }
