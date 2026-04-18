"""
PPS Anantam — 15-Day Forward Strategy Engine v1.0
====================================================
Combines multiple data signals to produce actionable
business recommendations for procurement and stock strategy.

Outputs:
  - Demand Strength Score (0-100)
  - Price Direction Probability (UP/DOWN/STABLE)
  - Stock Strategy (BUY NOW / WAIT / HOLD / SELECTIVE BUY)
  - Procurement Recommendation
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent


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


# Seasonal index: month -> weight (0-30 scale, 30 = peak demand)
_SEASONAL_WEIGHTS = {
    1: 28, 2: 30, 3: 27,    # Jan-Mar: peak road construction
    4: 18, 5: 12, 6: 8,     # Apr-Jun: tapering
    7: 5, 8: 5, 9: 8,       # Jul-Sep: monsoon (lowest)
    10: 22, 11: 26, 12: 28, # Oct-Dec: post-monsoon ramp-up
}


class ForwardStrategyEngine:
    """Produces 15-day forward-looking business recommendations."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()

    def calculate_demand_strength_score(self) -> dict:
        """
        Composite demand score 0-100.

        Components:
          seasonal_weight (30%): Month-based construction activity
          weather_factor (20%): Rainfall impact
          govt_spending_signal (20%): Tender/budget proxy
          historical_pattern (15%): Same month last year
          tender_activity (15%): Recent tender count
        """
        now = datetime.datetime.now(IST)
        month = now.month

        # 1. Seasonal weight (0-30)
        seasonal_raw = _SEASONAL_WEIGHTS.get(month, 15)
        seasonal_detail = "Peak construction" if seasonal_raw >= 25 else \
            "Monsoon low" if seasonal_raw <= 8 else "Moderate season"

        # 2. Weather factor (0-20)
        weather_raw = self._get_weather_factor()

        # 3. Government spending signal (0-20)
        govt_raw = self._get_govt_spending_signal()

        # 4. Historical pattern (0-15)
        historical_raw = min(15, seasonal_raw * 0.5)  # Correlates with season

        # 5. Tender activity (0-15)
        tender_raw = self._get_tender_activity_score()

        total = seasonal_raw + weather_raw + govt_raw + historical_raw + tender_raw
        total = min(100, max(0, round(total)))

        if total >= 70:
            label, color = "STRONG", "#2d6a4f"
        elif total >= 40:
            label, color = "MODERATE", "#c9a84c"
        else:
            label, color = "WEAK", "#b85c38"

        return {
            "total_score": total,
            "components": {
                "seasonal": {"raw": seasonal_raw, "weighted": seasonal_raw,
                             "detail": seasonal_detail},
                "weather": {"raw": weather_raw, "weighted": weather_raw,
                            "detail": f"Rain factor: {weather_raw}/20"},
                "govt_spending": {"raw": govt_raw, "weighted": govt_raw,
                                  "detail": f"Govt signal: {govt_raw}/20"},
                "historical": {"raw": historical_raw, "weighted": historical_raw,
                               "detail": f"Historical match: {historical_raw:.0f}/15"},
                "tender_activity": {"raw": tender_raw, "weighted": tender_raw,
                                    "detail": f"Tender score: {tender_raw}/15"},
            },
            "label": label,
            "color": color,
        }

    def calculate_price_direction(self) -> dict:
        """
        Price direction probability using weighted signals.

        Signals:
          crude_trend_7d (35%): Brent 7-day moving average
          fx_trend_7d (20%): INR/USD 7-day trend
          refinery_utilization (15%): Supply constraint
          seasonal_price_pattern (15%): Historical price same month
          import_volume_trend (15%): Import volume changes
        """
        signals = {}

        # 1. Crude trend (weight 0.35)
        crude_signal = self._get_crude_trend_signal()
        signals["crude_trend"] = {
            "direction": crude_signal["direction"],
            "weight": 0.35,
            "value": crude_signal["change_pct"],
            "detail": crude_signal["detail"],
        }

        # 2. FX trend (weight 0.20)
        fx_signal = self._get_fx_trend_signal()
        signals["fx_trend"] = {
            "direction": fx_signal["direction"],
            "weight": 0.20,
            "value": fx_signal["change_pct"],
            "detail": fx_signal["detail"],
        }

        # 3. Refinery utilization (weight 0.15)
        refinery_signal = self._get_refinery_signal()
        signals["refinery_utilization"] = {
            "direction": refinery_signal["direction"],
            "weight": 0.15,
            "value": refinery_signal["value"],
            "detail": refinery_signal["detail"],
        }

        # 4. Seasonal price pattern (weight 0.15)
        month = datetime.datetime.now(IST).month
        seasonal_dir = "UP" if month in (10, 11, 12, 1, 2, 3) else \
            "DOWN" if month in (7, 8, 9) else "STABLE"
        signals["seasonal_pattern"] = {
            "direction": seasonal_dir,
            "weight": 0.15,
            "value": 0,
            "detail": f"Month {month}: historically {'rising' if seasonal_dir == 'UP' else 'falling' if seasonal_dir == 'DOWN' else 'stable'}",
        }

        # 5. Import volume trend (weight 0.15)
        import_signal = self._get_import_signal()
        signals["import_volume"] = {
            "direction": import_signal["direction"],
            "weight": 0.15,
            "value": import_signal["value"],
            "detail": import_signal["detail"],
        }

        # Calculate weighted direction
        dir_scores = {"UP": 0, "DOWN": 0, "STABLE": 0}
        for sig in signals.values():
            dir_scores[sig["direction"]] += sig["weight"]

        direction = max(dir_scores, key=dir_scores.get)
        confidence = round(dir_scores[direction] * 100)
        confidence = min(95, max(20, confidence))  # Clamp to 20-95%

        arrows = {"UP": "\u25b2", "DOWN": "\u25bc", "STABLE": "\u25c6"}

        return {
            "direction": direction,
            "confidence_pct": confidence,
            "signals": signals,
            "arrow": arrows.get(direction, "\u25c6"),
        }

    def generate_stock_strategy(self, price_direction: dict = None,
                                 demand_score: dict = None) -> dict:
        """Stock strategy recommendation based on price + demand signals."""
        if not price_direction:
            price_direction = self.calculate_price_direction()
        if not demand_score:
            demand_score = self.calculate_demand_strength_score()

        direction = price_direction.get("direction", "STABLE")
        score = demand_score.get("total_score", 50)
        rationale = []

        if direction == "UP" and score > 60:
            strategy = "BUY NOW"
            action = "Procure at current rates before prices increase further"
            color = "#b85c38"
            urgency = "HIGH"
            rationale.append(f"Price direction: {direction} ({price_direction.get('confidence_pct', 0)}% confidence)")
            rationale.append(f"Demand strength: {score}/100 ({demand_score.get('label', '')})")
            rationale.append("Lock in current rates while available")
        elif direction == "DOWN" and score < 40:
            strategy = "WAIT"
            action = "Delay procurement — prices likely to soften"
            color = "#2d6a4f"
            urgency = "LOW"
            rationale.append(f"Price direction: {direction} (prices falling)")
            rationale.append(f"Demand weak: {score}/100")
            rationale.append("Better prices expected in coming days")
        elif direction == "STABLE":
            strategy = "HOLD"
            action = "Maintain current inventory levels"
            color = "#c9a84c"
            urgency = "MEDIUM"
            rationale.append("Prices stable — no urgency")
            rationale.append(f"Demand: {score}/100 ({demand_score.get('label', '')})")
        else:
            strategy = "SELECTIVE BUY"
            action = "Buy only for confirmed orders"
            color = "#1e3a5f"
            urgency = "MEDIUM"
            rationale.append("Mixed signals — buy only against firm orders")
            rationale.append(f"Price: {direction}, Demand: {score}/100")

        # Procurement recommendation
        procurement = self._get_procurement_recommendation()
        if procurement.get("best_source"):
            rationale.append(f"Best source: {procurement['best_source']} at {procurement.get('best_price', 'N/A')}/MT")

        return {
            "strategy": strategy,
            "action": action,
            "recommended_qty_mt": procurement.get("buy_qty_mt", 0),
            "recommended_price": procurement.get("best_price", 0),
            "recommended_source": procurement.get("best_source", ""),
            "rationale": rationale,
            "color": color,
            "urgency": urgency,
        }

    def generate_full_outlook(self) -> dict:
        """Master method: combines all sub-analyses."""
        demand_score = self.calculate_demand_strength_score()
        price_direction = self.calculate_price_direction()
        stock_strategy = self.generate_stock_strategy(price_direction, demand_score)
        procurement = self._get_procurement_recommendation()

        return {
            "demand_score": demand_score,
            "price_direction": price_direction,
            "stock_strategy": stock_strategy,
            "procurement_recommendation": procurement,
            "generated_at": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        }

    # ─── Signal Extractors ───────────────────────────────────────────────

    def _get_weather_factor(self) -> float:
        """Extract weather/rain factor (0-20). Higher = less rain = more demand."""
        weather = _load_json(BASE / "tbl_weather.json", [])
        if not weather:
            # Default: assume moderate conditions
            month = datetime.datetime.now(IST).month
            return 5 if month in (7, 8, 9) else 15 if month in (6, 10) else 18

        total_rain = 0
        count = 0
        for w in weather[-10:]:  # Last 10 records
            rain = w.get("rain_mm", w.get("rain", 0))
            if rain is not None:
                try:
                    total_rain += float(rain)
                    count += 1
                except (ValueError, TypeError):
                    pass

        avg_rain = total_rain / max(count, 1)
        if avg_rain > 50:
            return 0  # Heavy rain
        elif avg_rain > 20:
            return 8  # Moderate rain
        elif avg_rain > 5:
            return 14  # Light rain
        return 20  # No rain

    def _get_govt_spending_signal(self) -> float:
        """Government spending proxy (0-20). Uses tender/org data."""
        try:
            orgs = _load_json(BASE / "tbl_dir_orgs.json", [])
            # Count recent entries as proxy for activity
            if not orgs:
                return 12  # Default moderate
            return min(20, len(orgs) * 0.5)
        except Exception:
            return 12

    def _get_tender_activity_score(self) -> float:
        """Tender activity score (0-15). Based on recent opportunities/tenders."""
        try:
            from database import get_all_opportunities
            opps = get_all_opportunities()
            recent = [o for o in opps if o.get("type") == "tender_match"]
            return min(15, len(recent) * 3)
        except Exception:
            return 5

    def _get_crude_trend_signal(self) -> dict:
        """Analyze 7-day Brent crude trend."""
        crude = _load_json(BASE / "tbl_crude_prices.json", [])
        brent = [r for r in crude if r.get("benchmark") == "Brent" and r.get("price")]
        if len(brent) < 2:
            return {"direction": "STABLE", "change_pct": 0, "detail": "Insufficient data"}

        recent = brent[-7:] if len(brent) >= 7 else brent
        first_price = recent[0].get("price", 0)
        last_price = recent[-1].get("price", 0)

        if first_price <= 0:
            return {"direction": "STABLE", "change_pct": 0, "detail": "Invalid price data"}

        change_pct = round((last_price - first_price) / first_price * 100, 2)

        if change_pct > 2:
            direction = "UP"
        elif change_pct < -2:
            direction = "DOWN"
        else:
            direction = "STABLE"

        return {
            "direction": direction,
            "change_pct": change_pct,
            "detail": f"Brent {change_pct:+.1f}% (${first_price:.1f} -> ${last_price:.1f})",
        }

    def _get_fx_trend_signal(self) -> dict:
        """Analyze 7-day USD/INR trend."""
        fx = _load_json(BASE / "tbl_fx_rates.json", [])
        usd_inr = [r for r in fx if str(r.get("pair", "")) == "USD/INR" and r.get("rate")]
        if len(usd_inr) < 2:
            return {"direction": "STABLE", "change_pct": 0, "detail": "Insufficient FX data"}

        recent = usd_inr[-7:] if len(usd_inr) >= 7 else usd_inr
        first_rate = recent[0].get("rate", 0)
        last_rate = recent[-1].get("rate", 0)

        if first_rate <= 0:
            return {"direction": "STABLE", "change_pct": 0, "detail": "Invalid FX data"}

        change_pct = round((last_rate - first_rate) / first_rate * 100, 2)

        # INR weakening = UP pressure on bitumen prices (imports costlier)
        if change_pct > 0.5:
            direction = "UP"
        elif change_pct < -0.5:
            direction = "DOWN"
        else:
            direction = "STABLE"

        return {
            "direction": direction,
            "change_pct": change_pct,
            "detail": f"USD/INR {change_pct:+.1f}% ({first_rate:.2f} -> {last_rate:.2f})",
        }

    def _get_refinery_signal(self) -> dict:
        """Refinery utilization signal."""
        refinery = _load_json(BASE / "tbl_refinery_production.json", [])
        if not refinery:
            return {"direction": "STABLE", "value": 0,
                    "detail": "No refinery data available"}

        # Look for "All India Total" row
        total_rows = [r for r in refinery
                      if "all india" in str(r.get("refinery", "")).lower()
                      or "total" in str(r.get("refinery", "")).lower()]
        if total_rows:
            latest = total_rows[-1]
            utilization = latest.get("utilization_pct", latest.get("capacity_utilization", 0))
            try:
                utilization = float(utilization)
            except (ValueError, TypeError):
                utilization = 0

            if utilization > 90:
                direction = "UP"
            elif utilization < 70:
                direction = "DOWN"
            else:
                direction = "STABLE"

            return {"direction": direction, "value": utilization,
                    "detail": f"Refinery utilization: {utilization:.0f}%"}

        return {"direction": "STABLE", "value": 0, "detail": "Refinery data incomplete"}

    def _get_import_signal(self) -> dict:
        """Import volume trend — falling imports = domestic price pressure UP."""
        imports = _load_json(BASE / "tbl_imports_countrywise.json", [])
        if not imports:
            return {"direction": "STABLE", "value": 0,
                    "detail": "No import data available"}

        # Sum recent import values
        recent = imports[-5:] if len(imports) >= 5 else imports
        total_value = sum(float(r.get("trade_value_usd", 0)) for r in recent
                          if r.get("trade_value_usd"))
        if total_value <= 0:
            return {"direction": "STABLE", "value": 0, "detail": "Import data incomplete"}

        # Compare with earlier period if available
        if len(imports) >= 10:
            earlier = imports[-10:-5]
            earlier_value = sum(float(r.get("trade_value_usd", 0)) for r in earlier
                                if r.get("trade_value_usd"))
            if earlier_value > 0:
                change = (total_value - earlier_value) / earlier_value * 100
                if change < -10:
                    return {"direction": "UP", "value": change,
                            "detail": f"Imports down {change:.0f}% (price pressure up)"}
                elif change > 10:
                    return {"direction": "DOWN", "value": change,
                            "detail": f"Imports up {change:.0f}% (more supply)"}

        return {"direction": "STABLE", "value": 0, "detail": "Import volumes stable"}

    def _get_procurement_recommendation(self) -> dict:
        """How much to buy, from where, at what price."""
        try:
            from calculation_engine import BitumenCalculationEngine
            calc = BitumenCalculationEngine()
            # Get best source for major destination
            sources = calc.find_best_sources("Ahmedabad", grade="VG30", top_n=3)
            if sources:
                best = sources[0]
                return {
                    "buy_qty_mt": 500,  # Default recommendation
                    "best_source": best.get("source", ""),
                    "best_price": best.get("landed_cost", 0),
                    "alternative_source": sources[1].get("source", "") if len(sources) > 1 else "",
                    "alternative_price": sources[1].get("landed_cost", 0) if len(sources) > 1 else 0,
                }
        except Exception:
            pass

        return {
            "buy_qty_mt": 500,
            "best_source": "Market",
            "best_price": 0,
            "alternative_source": "",
            "alternative_price": 0,
        }
