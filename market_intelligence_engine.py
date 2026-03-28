"""
PPS Anantam — Market Intelligence Engine v1.0
===============================================
10-Signal Composite AI Intelligence for Bitumen Trading.

Signals:
  1. Crude Market Analysis     (tbl_crude_prices.json)
  2. Currency Impact Analysis  (tbl_fx_rates.json)
  3. Weather & Logistics       (tbl_weather.json)
  4. News & Event Analysis     (tbl_news_feed.json)
  5. Government Infrastructure (tbl_highway_km.json)
  6. Tender Demand Signal      (tbl_news_feed.json)
  7. Global Economic Signal    (tbl_world_bank.json)
  8. Search Demand Signal      (Google Trends / pytrends)
  9. Port & Shipping Signal    (tbl_ports_volume.json)
 10. Master Composite Signal   (weighted combination of 1-9)

All FREE data sources. Uses numpy for math — no heavy ML libraries.
Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import time
import threading
import datetime
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pytz

# ── Constants ────────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
_BASE = Path(__file__).parent
_LOG = logging.getLogger("market_intelligence")

TBL_SIGNALS    = _BASE / "tbl_market_signals.json"
TBL_WORLD_BANK = _BASE / "tbl_world_bank.json"

_lock = threading.RLock()
_CACHE_TTL_SEC = 7200  # 2 hours

# Optional: pytrends for Google Trends
_HAS_PYTRENDS = False
try:
    from pytrends.request import TrendReq        # type: ignore
    _HAS_PYTRENDS = True
except ImportError:
    pass

# ── Signal weights for master composite ──────────────────────────────────────
SIGNAL_WEIGHTS = {
    "crude_market": 0.25,
    "currency":     0.15,
    "weather":      0.10,
    "news":         0.15,
    "govt_infra":   0.10,
    "tenders":      0.10,
    "economic":     0.05,
    "search":       0.05,
    "ports":        0.05,
}

# ── News keyword categories ──────────────────────────────────────────────────
_NEWS_CATEGORIES = {
    "refinery_shutdown": {
        "keywords": {"shutdown", "maintenance", "fire", "accident", "outage",
                     "refinery closure", "turnaround", "explosion", "blast"},
        "impact_days": 14,
    },
    "infrastructure": {
        "keywords": {"highway", "road project", "nhai", "tender awarded",
                     "construction", "expressway", "bitumen demand", "asphalt",
                     "paving", "road construction"},
        "impact_days": 30,
    },
    "geopolitics": {
        "keywords": {"opec", "sanctions", "iran", "russia", "embargo",
                     "war", "middle east", "conflict", "geopolitical",
                     "crude oil ban", "export ban"},
        "impact_days": 7,
    },
    "port_disruption": {
        "keywords": {"port congestion", "vessel delay", "strike", "port closed",
                     "shipping delay", "freight", "maritime", "cyclone",
                     "blockade", "port disruption"},
        "impact_days": 5,
    },
}

# ── Tender keywords ─────────────────────────────────────────────────────────
_TENDER_KEYWORDS = {
    "tender", "loa", "work order", "awarded", "contract",
    "bid", "epc", "procurement", "nit", "rfp", "rfq",
    "notice inviting", "letter of acceptance",
}

# ── Indian states/cities for NER fallback ────────────────────────────────────
_INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya",
    "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim",
    "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "west bengal",
}
_MAJOR_CITIES = {
    "mumbai", "delhi", "bangalore", "hyderabad", "ahmedabad", "chennai",
    "kolkata", "pune", "jaipur", "lucknow", "kanpur", "nagpur", "indore",
    "bhopal", "vadodara", "surat", "visakhapatnam", "patna", "ludhiana",
    "coimbatore", "kochi", "guwahati", "mangalore", "kandla", "mundra",
    "rajkot", "baroda", "thane", "nashik", "aurangabad",
}

# ── Port risk keywords ──────────────────────────────────────────────────────
_PORT_RISK_KEYWORDS = {
    "congestion", "delay", "strike", "closed", "blockade",
    "weather disruption", "cyclone", "port shutdown",
}

# Monsoon penalty map (month → penalty 0-30)
_MONSOON_PENALTY = {6: 20, 7: 30, 8: 30, 9: 25, 10: 10, 11: 5}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _ts() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _load(path: Path, default: Any = None) -> Any:
    """Thread-safe JSON read."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        pass
    return default if default is not None else []


def _save(path: Path, data: Any) -> None:
    """Thread-safe JSON write."""
    with _lock:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except (IOError, OSError) as e:
            _LOG.warning("Save failed %s: %s", path.name, e)


def _linear_slope(values: list[float]) -> float:
    """Simple OLS slope via numpy polyfit degree 1."""
    if len(values) < 3:
        return 0.0
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    coeffs = np.polyfit(x, y, 1)
    return float(coeffs[0])


def _momentum(values: list[float], period: int = 5) -> float:
    """Rate of change: (latest - period_ago) / period_ago * 100."""
    if len(values) < period + 1:
        return 0.0
    old = values[-(period + 1)]
    new = values[-1]
    if old == 0:
        return 0.0
    return round((new - old) / abs(old) * 100, 2)


def _volatility_label(values: list[float]) -> str:
    """Classify coefficient of variation as LOW / MEDIUM / HIGH."""
    if len(values) < 5:
        return "UNKNOWN"
    window = values[-14:] if len(values) >= 14 else values
    std = float(np.std(window))
    mean = float(np.mean(window))
    cv = std / mean if mean else 0
    if cv < 0.02:
        return "LOW"
    elif cv < 0.05:
        return "MEDIUM"
    return "HIGH"


def _neutral_signal(signal_id: str, reason: str = "") -> dict:
    """Neutral / fallback signal when computation fails."""
    return {
        "signal_id": signal_id,
        "signal_name": signal_id.replace("_", " ").title(),
        "direction": "SIDEWAYS",
        "confidence": 30,
        "status": "FALLBACK",
        "reason": reason[:200],
        "computed_at": _ts(),
    }


def _extract_price_series(data: list[dict], benchmark: str, n: int = 50) -> list[float]:
    """Extract last N prices for a given benchmark from tbl_crude_prices."""
    prices = []
    for row in data:
        if row.get("benchmark", "").lower() == benchmark.lower():
            try:
                prices.append(float(row["price"]))
            except (KeyError, ValueError, TypeError):
                pass
    return prices[-n:]


def _extract_fx_series(data: list[dict], pair: str = "USD/INR", n: int = 50) -> list[float]:
    """Extract last N rates for a given pair from tbl_fx_rates."""
    rates = []
    for row in data:
        if row.get("pair", "") == pair:
            try:
                rates.append(float(row["rate"]))
            except (KeyError, ValueError, TypeError):
                pass
    return rates[-n:]


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MarketIntelligenceEngine:
    """10-signal composite market intelligence engine."""

    def __init__(self):
        self._signals_cache: dict | None = None
        self._cache_ts: float = 0

    # ── Signal 1: Crude Market Analysis ─────────────────────────────────────

    def compute_crude_signal(self) -> dict:
        """
        Brent/WTI momentum, volatility, trend strength.
        Output: direction UP/DOWN/SIDEWAYS, confidence %, impact text.
        """
        try:
            raw = _load(_BASE / "tbl_crude_prices.json", [])
            brent = _extract_price_series(raw, "Brent", 50)
            wti = _extract_price_series(raw, "WTI", 50)

            if len(brent) < 5:
                return _neutral_signal("crude_market", "Insufficient Brent data")

            window = brent[-14:] if len(brent) >= 14 else brent
            slope = _linear_slope(window[-7:])
            mom = _momentum(window, 5)
            vol = _volatility_label(window)
            support = round(min(window), 2)
            resistance = round(max(window), 2)

            if slope > 0.3:
                direction = "UP"
            elif slope < -0.3:
                direction = "DOWN"
            else:
                direction = "SIDEWAYS"

            confidence = 50 + min(25, int(abs(slope) * 10))
            if vol == "LOW":
                confidence += 10
            confidence = min(95, max(30, confidence))

            impact_map = {
                "UP":       "Bitumen price may increase -- consider early procurement",
                "DOWN":     "Bitumen price may decrease -- monitor for buying opportunity",
                "SIDEWAYS": "Prices stable -- normal procurement timing",
            }

            return {
                "signal_id": "crude_market",
                "signal_name": "Crude Market Analysis",
                "direction": direction,
                "confidence": confidence,
                "impact": impact_map[direction],
                "momentum": mom,
                "volatility": vol,
                "trend_slope": round(slope, 3),
                "support": support,
                "resistance": resistance,
                "latest_brent": round(brent[-1], 2),
                "latest_wti": round(wti[-1], 2) if wti else None,
                "data_points": len(window),
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Crude signal failed: %s", e)
            return _neutral_signal("crude_market", str(e))

    # ── Signal 2: Currency Impact Analysis ──────────────────────────────────

    def compute_currency_signal(self) -> dict:
        """
        USD/INR trend × crude trend = import parity pressure.
        Output: pressure HIGH/MED/LOW, trend, advice.
        """
        try:
            raw = _load(_BASE / "tbl_fx_rates.json", [])
            fx = _extract_fx_series(raw, "USD/INR", 50)

            if len(fx) < 5:
                return _neutral_signal("currency", "Insufficient FX data")

            window = fx[-14:] if len(fx) >= 14 else fx
            slope = _linear_slope(window[-7:])
            mom = _momentum(window, 5)
            vol = _volatility_label(window)

            # Cross-reference crude
            crude_sig = self.compute_crude_signal()
            crude_dir = crude_sig.get("direction", "SIDEWAYS")

            if slope > 0.05:
                trend = "Weak INR"
            elif slope < -0.05:
                trend = "Strong INR"
            else:
                trend = "Stable"

            fx_up = slope > 0.02
            crude_up = crude_dir == "UP"
            if fx_up and crude_up:
                pressure = "HIGH"
            elif fx_up or crude_up:
                pressure = "MEDIUM"
            else:
                pressure = "LOW"

            advice_map = {
                "HIGH":   "Buy earlier -- import costs rising",
                "MEDIUM": "Watch closely -- one factor adverse",
                "LOW":    "Normal timing",
            }

            confidence = 50 + min(22, int(abs(slope) * 200))
            if vol == "LOW":
                confidence += 10
            confidence = min(95, max(35, confidence))

            return {
                "signal_id": "currency",
                "signal_name": "Currency Impact Analysis",
                "pressure": pressure,
                "trend": trend,
                "advice": advice_map[pressure],
                "confidence": confidence,
                "fx_momentum": mom,
                "fx_volatility": vol,
                "latest_usdinr": round(fx[-1], 2),
                "crude_cross_direction": crude_dir,
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Currency signal failed: %s", e)
            return _neutral_signal("currency", str(e))

    # ── Signal 3: Weather & Logistics Impact ────────────────────────────────

    def compute_weather_signal(self) -> dict:
        """
        Rain thresholds + monsoon calendar = road construction probability.
        Output: road_condition, logistics_risk, construction_probability %.
        """
        try:
            weather_data = _load(_BASE / "tbl_weather.json", [])
            if not weather_data:
                return _neutral_signal("weather", "No weather data")

            # Latest reading per city
            city_latest: dict[str, dict] = {}
            for w in weather_data:
                loc = w.get("location", "")
                if loc:
                    city_latest[loc] = w

            month = datetime.datetime.now(IST).month
            monsoon_penalty = _MONSOON_PENALTY.get(month, 0)

            affected: list[str] = []
            city_conditions: dict[str, dict] = {}
            total_rain = 0.0

            for city, data in city_latest.items():
                rain = float(data.get("rain_mm", 0) or 0)
                total_rain += rain
                if rain > 20:
                    cond = "POOR"
                    affected.append(city)
                elif rain > 5:
                    cond = "MODERATE"
                    affected.append(city)
                else:
                    cond = "GOOD"
                city_conditions[city] = {
                    "condition": cond,
                    "rain_mm": rain,
                    "temp": data.get("temp", 0),
                }

            avg_rain = total_rain / max(len(city_latest), 1)
            rain_penalty = min(40, avg_rain * 2)
            construction_prob = max(5, min(100, round(100 - rain_penalty - monsoon_penalty)))

            if any(v["condition"] == "POOR" for v in city_conditions.values()):
                road_condition = "POOR"
            elif any(v["condition"] == "MODERATE" for v in city_conditions.values()):
                road_condition = "MODERATE"
            else:
                road_condition = "GOOD"

            logistics_risk = (
                "HIGH" if road_condition == "POOR" else
                "MEDIUM" if road_condition == "MODERATE" else "LOW"
            )

            if month in (6, 7, 8, 9):
                monsoon_factor = "ACTIVE"
            elif month in (10, 11):
                monsoon_factor = "TAPER"
            else:
                monsoon_factor = "DRY"

            return {
                "signal_id": "weather",
                "signal_name": "Weather & Logistics Impact",
                "road_condition": road_condition,
                "logistics_risk": logistics_risk,
                "affected_cities": affected,
                "construction_probability": construction_prob,
                "monsoon_factor": monsoon_factor,
                "city_details": city_conditions,
                "cities_tracked": len(city_latest),
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Weather signal failed: %s", e)
            return _neutral_signal("weather", str(e))

    # ── Signal 4: News & Event Analysis ─────────────────────────────────────

    def compute_news_signal(self) -> dict:
        """
        Keyword classification + sentiment on recent news headlines.
        Output: supply_risk, events list, sentiment.
        """
        try:
            news_data = _load(_BASE / "tbl_news_feed.json", [])
            if not news_data:
                return _neutral_signal("news", "No news data")

            recent = news_data[-100:]
            events: list[dict] = []
            category_counts = {k: 0 for k in _NEWS_CATEGORIES}
            sentiments: list[float] = []

            for article in recent:
                headline = (article.get("headline") or "").lower()

                # Sentiment score
                sent_score = article.get("sentiment_score")
                if sent_score is None:
                    try:
                        from finbert_engine import analyze_financial_sentiment
                        result = analyze_financial_sentiment(headline)
                        sent_score = result.get("score", 0.5)
                        # Negate for negative sentiment
                        if result.get("sentiment") == "negative":
                            sent_score = -sent_score
                    except Exception:
                        sent_score = 0
                sentiments.append(float(sent_score or 0))

                # Event classification
                for cat, info in _NEWS_CATEGORIES.items():
                    if any(kw in headline for kw in info["keywords"]):
                        category_counts[cat] += 1
                        events.append({
                            "type": cat,
                            "headline": (article.get("headline") or "")[:120],
                            "impact_days": info["impact_days"],
                        })
                        break

            # Supply risk
            risk_score = (
                category_counts["refinery_shutdown"] * 3 +
                category_counts["geopolitics"] * 2 +
                category_counts["port_disruption"] * 2
            )
            supply_risk = "HIGH" if risk_score > 8 else "MEDIUM" if risk_score > 3 else "LOW"

            avg_sent = float(np.mean(sentiments)) if sentiments else 0.0
            sentiment = (
                "POSITIVE" if avg_sent > 0.15 else
                "NEGATIVE" if avg_sent < -0.15 else "NEUTRAL"
            )

            return {
                "signal_id": "news",
                "signal_name": "News & Event Analysis",
                "supply_risk": supply_risk,
                "events": events[:10],
                "sentiment": sentiment,
                "avg_sentiment_score": round(avg_sent, 3),
                "category_counts": category_counts,
                "articles_analyzed": len(recent),
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("News signal failed: %s", e)
            return _neutral_signal("news", str(e))

    # ── Signal 5: Government Infrastructure ─────────────────────────────────

    def compute_govt_infra_signal(self) -> dict:
        """
        State-wise demand scoring from highway/infrastructure data.
        Output: top_states ranked, demand_trend.
        """
        try:
            highway_data = _load(_BASE / "tbl_highway_km.json", [])
            if not highway_data:
                return _neutral_signal("govt_infra", "No highway data")

            max_demand = max(
                (r.get("bitumen_demand_mt", 1) or 1 for r in highway_data), default=1
            )
            max_target = max(
                (r.get("nhai_km_target", 1) or 1 for r in highway_data), default=1
            )

            state_scores: list[dict] = []
            for row in highway_data:
                comp_pct = float(row.get("completion_pct", 50) or 50)
                demand_norm = (float(row.get("bitumen_demand_mt", 0) or 0) / max_demand) * 100
                target_norm = (float(row.get("nhai_km_target", 0) or 0) / max_target) * 100
                score = round(comp_pct * 0.4 + demand_norm * 0.3 + target_norm * 0.3)
                state_scores.append({
                    "state": row.get("state", "Unknown"),
                    "score": min(100, score),
                    "demand_mt": row.get("bitumen_demand_mt", 0),
                    "completion_pct": comp_pct,
                })

            state_scores.sort(key=lambda x: x["score"], reverse=True)

            total_demand = sum(float(r.get("bitumen_demand_mt", 0) or 0) for r in highway_data)
            # Reference: India ~4.2M MT/year, monthly ~350K MT
            reference = 350000
            if total_demand > reference * 1.1:
                demand_trend = "RISING"
            elif total_demand < reference * 0.9:
                demand_trend = "FALLING"
            else:
                demand_trend = "STABLE"

            return {
                "signal_id": "govt_infra",
                "signal_name": "Government Infrastructure",
                "top_states": state_scores[:10],
                "demand_trend": demand_trend,
                "total_demand_mt": total_demand,
                "states_analyzed": len(state_scores),
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Govt infra signal failed: %s", e)
            return _neutral_signal("govt_infra", str(e))

    # ── Signal 6: Tender Demand Signal ──────────────────────────────────────

    def compute_tender_signal(self) -> dict:
        """
        Tender keywords in news + location extraction via regex.
        Output: tender count, top state/city, demand_level.
        """
        try:
            news_data = _load(_BASE / "tbl_news_feed.json", [])
            recent = (news_data or [])[-200:]

            # Try to import state/city lists from nlp_extraction_engine
            try:
                from nlp_extraction_engine import _INDIAN_STATES as ext_states
                from nlp_extraction_engine import _MAJOR_CITIES as ext_cities
                states_set = ext_states
                cities_set = ext_cities
            except ImportError:
                states_set = _INDIAN_STATES
                cities_set = _MAJOR_CITIES

            tender_articles: list[dict] = []
            state_counts: dict[str, int] = {}
            city_counts: dict[str, int] = {}

            for article in recent:
                headline = (article.get("headline") or "").lower()
                if any(kw in headline for kw in _TENDER_KEYWORDS):
                    tender_articles.append(article)
                    for state in states_set:
                        if state in headline:
                            key = state.title()
                            state_counts[key] = state_counts.get(key, 0) + 1
                    for city in cities_set:
                        if city in headline:
                            key = city.title()
                            city_counts[key] = city_counts.get(key, 0) + 1

            n_tenders = len(tender_articles)
            top_state = max(state_counts, key=state_counts.get) if state_counts else "N/A"
            top_city = max(city_counts, key=city_counts.get) if city_counts else "N/A"
            demand_level = "HIGH" if n_tenders > 10 else "MEDIUM" if n_tenders > 3 else "LOW"

            return {
                "signal_id": "tenders",
                "signal_name": "Tender Demand Signal",
                "new_tenders": n_tenders,
                "top_state": top_state,
                "top_city": top_city,
                "demand_level": demand_level,
                "state_breakdown": dict(sorted(state_counts.items(), key=lambda x: -x[1])[:10]),
                "recent_tenders": [
                    {"headline": (a.get("headline") or "")[:120], "date": a.get("date_time", "")}
                    for a in tender_articles[:5]
                ],
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Tender signal failed: %s", e)
            return _neutral_signal("tenders", str(e))

    # ── Signal 7: Global Economic Signal ────────────────────────────────────

    def compute_economic_signal(self) -> dict:
        """
        World Bank CPI/GDP → economic trend → construction outlook.
        Fallback: static reference (GDP 6.8%, CPI 5.2%).
        """
        try:
            wb_data = _load(TBL_WORLD_BANK, {})
            if not wb_data or not isinstance(wb_data, dict):
                wb_data = {
                    "gdp_growth": 6.8, "cpi": 5.2,
                    "source": "Static reference (World Bank API unavailable)",
                }

            gdp = float(wb_data.get("gdp_growth", 6.0))
            cpi = float(wb_data.get("cpi", 5.0))

            if gdp > 6:
                economic_trend = "GROWING"
            elif gdp < 4:
                economic_trend = "CONTRACTING"
            else:
                economic_trend = "STABLE"

            if economic_trend == "GROWING" and cpi < 7:
                construction_outlook = "POSITIVE"
            elif economic_trend == "CONTRACTING":
                construction_outlook = "NEGATIVE"
            else:
                construction_outlook = "NEUTRAL"

            return {
                "signal_id": "economic",
                "signal_name": "Global Economic Signal",
                "economic_trend": economic_trend,
                "construction_outlook": construction_outlook,
                "gdp_growth": gdp,
                "cpi": cpi,
                "source": wb_data.get("source", "World Bank API"),
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Economic signal failed: %s", e)
            return _neutral_signal("economic", str(e))

    # ── Signal 8: Search Demand Signal ──────────────────────────────────────

    def compute_search_signal(self) -> dict:
        """
        Google Trends via pytrends: 90-day interest for bitumen/road keywords.
        Fallback: neutral signal if pytrends unavailable.
        """
        if not _HAS_PYTRENDS:
            return {
                "signal_id": "search",
                "signal_name": "Search Demand Signal",
                "demand_interest": "STABLE",
                "signal_strength": "MEDIUM",
                "trending_terms": [],
                "interest_score": 50,
                "source": "Neutral (pytrends not installed)",
                "computed_at": _ts(),
                "status": "FALLBACK",
            }

        try:
            pytrends = TrendReq(hl="en-IN", tz=330, timeout=(10, 25))
            kw_list = ["bitumen", "road construction India", "asphalt",
                       "highway project India"]
            pytrends.build_payload(kw_list, timeframe="today 3-m", geo="IN")
            df = pytrends.interest_over_time()

            if df.empty:
                return _neutral_signal("search", "Empty pytrends response")

            if "isPartial" in df.columns:
                df = df.drop("isPartial", axis=1)

            mean_interest = df.mean(axis=1)
            recent_4w = float(mean_interest[-4:].mean()) if len(mean_interest) >= 4 else 50
            older_4w = float(mean_interest[-8:-4].mean()) if len(mean_interest) >= 8 else 50

            if recent_4w > older_4w * 1.15:
                demand_interest = "RISING"
            elif recent_4w < older_4w * 0.85:
                demand_interest = "FALLING"
            else:
                demand_interest = "STABLE"

            interest_score = min(100, max(0, int(recent_4w)))
            signal_strength = (
                "HIGH" if interest_score > 65 else
                "MEDIUM" if interest_score > 35 else "LOW"
            )

            trending = [
                col for col in df.columns
                if df[col].iloc[-1] > df[col].mean() * 1.2
            ]

            return {
                "signal_id": "search",
                "signal_name": "Search Demand Signal",
                "demand_interest": demand_interest,
                "signal_strength": signal_strength,
                "trending_terms": trending,
                "interest_score": interest_score,
                "source": "Google Trends",
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Search signal failed (rate limit?): %s", e)
            return {
                "signal_id": "search",
                "signal_name": "Search Demand Signal",
                "demand_interest": "STABLE",
                "signal_strength": "MEDIUM",
                "trending_terms": [],
                "interest_score": 50,
                "source": f"Neutral fallback ({str(e)[:50]})",
                "computed_at": _ts(),
                "status": "FALLBACK",
            }

    # ── Signal 9: Port & Shipping Signal ────────────────────────────────────

    def compute_port_signal(self) -> dict:
        """
        Port volume trend + congestion keyword detection in news.
        Output: port_risk, freight_delay, congested_ports.
        """
        try:
            ports_data = _load(_BASE / "tbl_ports_volume.json", [])
            news_data = _load(_BASE / "tbl_news_feed.json", [])

            if not ports_data:
                return _neutral_signal("ports", "No port data")

            # Latest port volumes
            port_volumes: dict[str, float] = {}
            for p in ports_data:
                name = p.get("port_name", "")
                qty = float(p.get("quantity", 0) or 0)
                port_volumes[name] = qty

            total = sum(port_volumes.values())
            # Reference: ~79K MT across major ports
            if total > 85000:
                volume_trend = "UP"
            elif total < 65000:
                volume_trend = "DOWN"
            else:
                volume_trend = "STABLE"

            # Port congestion from news
            congested: set[str] = set()
            congestion_count = 0
            port_names_lower = {k.lower(): k for k in port_volumes}

            for article in (news_data or [])[-100:]:
                headline = (article.get("headline") or "").lower()
                if any(kw in headline for kw in _PORT_RISK_KEYWORDS):
                    congestion_count += 1
                    for pname_lower, pname in port_names_lower.items():
                        short = pname_lower.split("(")[0].strip()
                        if short and short in headline:
                            congested.add(pname)

            if congestion_count > 3:
                freight_delay = "MAJOR"
                port_risk = "HIGH"
            elif congestion_count > 0:
                freight_delay = "MINOR"
                port_risk = "MEDIUM"
            else:
                freight_delay = "NONE"
                port_risk = "LOW"

            return {
                "signal_id": "ports",
                "signal_name": "Port & Shipping Signal",
                "port_risk": port_risk,
                "freight_delay": freight_delay,
                "congested_ports": list(congested),
                "volume_trend": volume_trend,
                "port_volumes": port_volumes,
                "total_volume_mt": total,
                "computed_at": _ts(),
                "status": "OK",
            }
        except Exception as e:
            _LOG.warning("Port signal failed: %s", e)
            return _neutral_signal("ports", str(e))

    # ── Signal 10: Master Composite Signal ──────────────────────────────────

    def compute_master_signal(self, signals: dict) -> dict:
        """
        Weighted composite of all 9 signals.
        Output: market_direction, confidence, demand_outlook, risk_level, action.
        """
        def _direction_score(sig: dict) -> float:
            d = (sig.get("direction") or sig.get("pressure") or
                 sig.get("demand_level") or sig.get("economic_trend") or
                 sig.get("demand_interest") or sig.get("volume_trend") or
                 sig.get("demand_trend") or sig.get("road_condition") or
                 "STABLE")
            up_set = {"UP", "HIGH", "POSITIVE", "RISING", "GROWING", "GOOD"}
            down_set = {"DOWN", "LOW", "NEGATIVE", "FALLING", "CONTRACTING", "POOR"}
            if d in up_set:
                return 1.0
            elif d in down_set:
                return -1.0
            return 0.0

        weighted_sum = 0.0
        confidences: list[int] = []
        signal_summary: list[dict] = []

        for sig_id, weight in SIGNAL_WEIGHTS.items():
            sig = signals.get(sig_id, {})
            score = _direction_score(sig)
            weighted_sum += score * weight
            if "confidence" in sig:
                confidences.append(int(sig["confidence"]))
            signal_summary.append({
                "signal": sig.get("signal_name", sig_id),
                "value": score,
                "weight_pct": int(weight * 100),
                "status": sig.get("status", "N/A"),
            })

        # Market direction
        if weighted_sum > 0.2:
            market_direction = "UP"
        elif weighted_sum < -0.2:
            market_direction = "DOWN"
        else:
            market_direction = "SIDEWAYS"

        confidence = int(np.mean(confidences)) if confidences else 50

        # Demand outlook
        weather_sig = signals.get("weather", {})
        govt_sig = signals.get("govt_infra", {})
        tender_sig = signals.get("tenders", {})
        demand_indicators = [
            weather_sig.get("construction_probability", 50),
            100 if govt_sig.get("demand_trend") == "RISING" else
                50 if govt_sig.get("demand_trend") == "STABLE" else 25,
            100 if tender_sig.get("demand_level") == "HIGH" else
                50 if tender_sig.get("demand_level") == "MEDIUM" else 25,
        ]
        demand_avg = float(np.mean(demand_indicators))
        demand_outlook = (
            "STRONG" if demand_avg > 70 else
            "WEAK" if demand_avg < 35 else "MODERATE"
        )

        # Risk level
        news_sig = signals.get("news", {})
        ports_sig = signals.get("ports", {})
        currency_sig = signals.get("currency", {})
        risk_indicators = [
            news_sig.get("supply_risk", "LOW"),
            ports_sig.get("port_risk", "LOW"),
            currency_sig.get("pressure", "LOW"),
        ]
        high_risks = sum(1 for r in risk_indicators if r == "HIGH")
        risk_level = "HIGH" if high_risks >= 2 else "MEDIUM" if high_risks >= 1 else "LOW"

        # Recommended action
        if market_direction == "UP" and demand_outlook == "STRONG":
            action = "Procurement favorable -- buy now before price increase"
        elif market_direction == "DOWN":
            action = "Prices declining -- wait 3-5 days for better rates"
        elif risk_level == "HIGH":
            action = "High risk detected -- secure supply from reliable sources"
        elif demand_outlook == "STRONG":
            action = "Strong demand ahead -- lock in procurement within 5 days"
        else:
            action = "Market stable -- follow normal procurement schedule"

        return {
            "signal_id": "master",
            "signal_name": "Master Composite Signal",
            "market_direction": market_direction,
            "confidence": confidence,
            "demand_outlook": demand_outlook,
            "risk_level": risk_level,
            "recommended_action": action,
            "weighted_score": round(weighted_sum, 3),
            "signals_summary": signal_summary,
            "computed_at": _ts(),
            "status": "OK",
        }

    # ── Orchestrator ────────────────────────────────────────────────────────

    def compute_all_signals(self) -> dict:
        """Run all 10 signals. Cache result. Return master dict keyed by signal_id."""
        now = time.time()
        if self._signals_cache and (now - self._cache_ts) < _CACHE_TTL_SEC:
            return self._signals_cache

        signal_methods = [
            ("compute_crude_signal",       "crude_market"),
            ("compute_currency_signal",    "currency"),
            ("compute_weather_signal",     "weather"),
            ("compute_news_signal",        "news"),
            ("compute_govt_infra_signal",  "govt_infra"),
            ("compute_tender_signal",      "tenders"),
            ("compute_economic_signal",    "economic"),
            ("compute_search_signal",      "search"),
            ("compute_port_signal",        "ports"),
        ]

        signals: dict[str, dict] = {}
        for method_name, sig_id in signal_methods:
            try:
                signals[sig_id] = getattr(self, method_name)()
            except Exception as e:
                _LOG.error("Signal %s failed: %s", sig_id, e)
                signals[sig_id] = _neutral_signal(sig_id, str(e))

        # Master composite (depends on 1-9)
        signals["master"] = self.compute_master_signal(signals)

        # Cache + persist
        self._signals_cache = signals
        self._cache_ts = now
        self._persist_signals(signals)

        return signals

    def _persist_signals(self, signals: dict) -> None:
        """Save to tbl_market_signals.json (rolling history)."""
        with _lock:
            existing = _load(TBL_SIGNALS, [])
            if not isinstance(existing, list):
                existing = []
            existing.append({
                "computed_at": _ts(),
                "signals": signals,
            })
            if len(existing) > 500:
                existing = existing[-500:]
            _save(TBL_SIGNALS, existing)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_all_signals() -> dict:
    """Module-level function for sync_engine integration."""
    engine = MarketIntelligenceEngine()
    return engine.compute_all_signals()


def get_master_signal() -> dict:
    """Quick accessor for the master composite signal."""
    engine = MarketIntelligenceEngine()
    all_signals = engine.compute_all_signals()
    return all_signals.get("master", {})


def get_signal_status() -> dict:
    """Status report for AI module registry."""
    return {
        "engine": "MarketIntelligenceEngine",
        "signals_count": 10,
        "pytrends_available": _HAS_PYTRENDS,
        "cache_ttl_sec": _CACHE_TTL_SEC,
        "output_table": "tbl_market_signals.json",
    }
