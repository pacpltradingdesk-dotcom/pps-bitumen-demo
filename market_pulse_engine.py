"""
PPS Anantam — Market Pulse Engine v1.0
=======================================
Real-time market monitoring engine that watches all data streams and
generates contextual, cross-correlated alerts for bitumen trading.

Alert examples:
  - "Demand likely to increase in Gujarat due to highway construction"
  - "Supply shortage expected: Jamnagar refinery maintenance"
  - "Crude Brent up 3.2% this week — expect bitumen price increase in 7-10 days"

Reads from: tbl_crude_prices, tbl_fx_rates, tbl_weather, tbl_news_feed,
            tbl_ports_volume, tbl_refinery_production, tbl_maritime_intel.
Writes to:  market_alerts.json (max 500 alerts, FIFO).

All times: IST (Asia/Kolkata)
"""
from __future__ import annotations

import json
import hashlib
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np

# ── Constants ────────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
ALERTS_FILE = BASE / "market_alerts.json"
MAX_ALERTS = 500

LOG = logging.getLogger("market_pulse_engine")
_lock = threading.RLock()

# ── Seasonal demand weights (month -> 0-30, 30 = peak) ──────────────────────
_SEASONAL_WEIGHTS = {
    1: 28, 2: 30, 3: 27,     # Jan-Mar: peak road construction
    4: 18, 5: 12, 6: 8,      # Apr-Jun: tapering
    7: 5,  8: 5,  9: 8,      # Jul-Sep: monsoon (lowest)
    10: 22, 11: 26, 12: 28,  # Oct-Dec: post-monsoon ramp-up
}

# Monsoon months per region (inclusive)
_MONSOON_MONTHS = {
    "Gujarat": (6, 9), "Maharashtra": (6, 9), "Rajasthan": (7, 9),
    "Karnataka": (6, 10), "Tamil Nadu": (10, 12), "Kerala": (6, 9),
    "Madhya Pradesh": (6, 9), "Uttar Pradesh": (7, 9), "Bihar": (6, 9),
    "West Bengal": (6, 9), "Odisha": (6, 9), "Andhra Pradesh": (6, 10),
}

# News keywords for supply disruption detection
_SUPPLY_KEYWORDS = {
    "shutdown", "maintenance", "turnaround", "fire", "explosion",
    "outage", "refinery closure", "blast", "accident", "force majeure",
    "sanctions", "embargo", "export ban", "opec cut",
}

# News keywords for demand signals
_DEMAND_KEYWORDS = {
    "highway", "road project", "nhai", "tender awarded", "expressway",
    "construction", "bitumen demand", "asphalt", "paving", "smart city",
    "bharatmala", "sagarmala", "pmgsy", "road construction",
}

# Port congestion thresholds (MT)
_PORT_HIGH_THRESHOLD = 40000
_PORT_LOW_THRESHOLD = 10000

# ── Optional engine imports ──────────────────────────────────────────────────
_HAS_HUB_CACHE = False
_HAS_MARKET_INTEL = False
_HAS_FINBERT = False
_HAS_ML_FORECAST = False
_HAS_FORWARD_STRATEGY = False
_HAS_INFRA_DEMAND = False

try:
    from api_hub_engine import HubCache
    _HAS_HUB_CACHE = True
except Exception:
    pass

try:
    from market_intelligence_engine import MarketIntelligenceEngine
    _HAS_MARKET_INTEL = True
except Exception:
    pass

try:
    from finbert_engine import analyze_financial_sentiment
    _HAS_FINBERT = True
except Exception:
    pass

try:
    from ml_forecast_engine import forecast_crude_price, forecast_fx_rate
    _HAS_ML_FORECAST = True
except Exception:
    pass

try:
    from forward_strategy_engine import ForwardStrategyEngine
    _HAS_FORWARD_STRATEGY = True
except Exception:
    pass

try:
    import infra_demand_engine
    _HAS_INFRA_DEMAND = True
except Exception:
    pass


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _now_ist() -> datetime:
    return datetime.now(IST)


def _ts_str(dt: Optional[datetime] = None) -> str:
    """Format datetime to IST string: DD-MM-YYYY HH:MM IST."""
    dt = dt or _now_ist()
    return dt.strftime("%Y-%m-%d %H:%M IST")


def _load_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError) as exc:
        LOG.warning("Failed to load %s: %s", path.name, exc)
    return default


def _save_json(path: Path, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except (IOError, OSError) as exc:
        LOG.error("Failed to save %s: %s", path.name, exc)


def _alert_id(category: str, msg_snippet: str) -> str:
    """Deterministic alert ID from category + message prefix."""
    raw = f"{category}:{msg_snippet[:80]}:{_now_ist().strftime('%Y%m%d%H')}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _pct_change(values: list[float], period: int = 7) -> float:
    """Percentage change over the last `period` data points."""
    if len(values) < 2:
        return 0.0
    start_idx = max(0, len(values) - period - 1)
    old = values[start_idx]
    new = values[-1]
    if old == 0:
        return 0.0
    return round(((new - old) / abs(old)) * 100, 2)


def _rsi(values: list[float], period: int = 14) -> float:
    """Relative Strength Index (0-100)."""
    if len(values) < period + 1:
        return 50.0
    deltas = np.diff(values[-period - 1:])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains) if len(gains) else 0.001
    avg_loss = np.mean(losses) if len(losses) else 0.001
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)


def _bollinger_bands(values: list[float], period: int = 20) -> dict:
    """Bollinger Bands: middle (SMA), upper, lower, %B."""
    if len(values) < period:
        arr = values
    else:
        arr = values[-period:]
    middle = float(np.mean(arr))
    std = float(np.std(arr))
    upper = round(middle + 2 * std, 2)
    lower = round(middle - 2 * std, 2)
    current = values[-1] if values else middle
    band_width = upper - lower if upper != lower else 1.0
    pct_b = round((current - lower) / band_width * 100, 1)
    return {
        "middle": round(middle, 2),
        "upper": upper,
        "lower": lower,
        "pct_b": pct_b,
        "current": round(current, 2),
    }


def _extract_price_series(records: list, benchmark: str, limit: int = 60) -> list[float]:
    """Extract price floats for a given benchmark from crude records."""
    prices = []
    for r in records:
        bm = r.get("benchmark", "")
        if bm.lower() == benchmark.lower():
            p = r.get("price")
            if p is not None:
                try:
                    prices.append(float(p))
                except (ValueError, TypeError):
                    continue
    # Deduplicate consecutive identical values, keep last N
    return prices[-limit:] if prices else []


def _extract_fx_series(records: list, pair: str = "USD/INR", limit: int = 60) -> list[float]:
    """Extract rate floats for a given pair from FX records."""
    rates = []
    for r in records:
        if r.get("pair", "") == pair:
            rate = r.get("rate")
            if rate is not None:
                try:
                    rates.append(float(rate))
                except (ValueError, TypeError):
                    continue
    return rates[-limit:] if rates else []


# ═════════════════════════════════════════════════════════════════════════════
# ALERT PERSISTENCE
# ═════════════════════════════════════════════════════════════════════════════

def _load_alerts() -> list[dict]:
    return _load_json(ALERTS_FILE, [])


def _save_alerts(alerts: list[dict]) -> None:
    with _lock:
        # FIFO: keep only last MAX_ALERTS
        trimmed = alerts[-MAX_ALERTS:] if len(alerts) > MAX_ALERTS else alerts
        _save_json(ALERTS_FILE, trimmed)


def _append_alert(alert: dict) -> None:
    """Append alert to file, deduplicating by ID."""
    with _lock:
        existing = _load_alerts()
        ids = {a.get("id") for a in existing}
        if alert.get("id") not in ids:
            existing.append(alert)
            _save_alerts(existing)


# ═════════════════════════════════════════════════════════════════════════════
# MARKET PULSE ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class MarketPulseEngine:
    """
    Real-time market monitoring engine. Watches all data streams, generates
    contextual cross-correlated alerts, and maintains a live market state
    summary for the PPS Anantam bitumen trading dashboard.
    """

    def __init__(self):
        self._cache: Optional[dict] = None
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 900.0  # 15 min

    # ─── Master monitor ─────────────────────────────────────────────────

    def monitor_all(self) -> dict:
        """
        Run all monitors and return combined state + alerts.
        Returns:
            {
                "timestamp": str,
                "crude": dict,
                "fx": dict,
                "supply_disruptions": list[dict],
                "demand_signals": list[dict],
                "logistics": dict,
                "alerts": list[dict],
                "market_state": dict,
            }
        """
        now = time.time()
        if self._cache and (now - self._cache_ts) < self._cache_ttl:
            return self._cache

        LOG.info("Running full market pulse scan...")

        crude = self._safe_call(self.monitor_crude_volatility, {})
        fx = self._safe_call(self.monitor_fx_impact, {})
        supply = self._safe_call(self.monitor_supply_disruptions, [])
        demand = self._safe_call(self.monitor_demand_signals, [])
        logistics = self._safe_call(self.monitor_logistics, {})

        # Cross-correlate and generate alerts
        alerts = self._cross_correlate(crude, fx, supply, demand, logistics)

        # Persist new alerts
        for a in alerts:
            _append_alert(a)

        result = {
            "timestamp": _ts_str(),
            "crude": crude,
            "fx": fx,
            "supply_disruptions": supply,
            "demand_signals": demand,
            "logistics": logistics,
            "alerts": alerts,
            "market_state": self._build_market_state(crude, fx, supply, demand, logistics),
        }

        self._cache = result
        self._cache_ts = now
        LOG.info("Market pulse scan complete: %d new alerts generated.", len(alerts))
        return result

    @staticmethod
    def _safe_call(func, default):
        """Call a monitor function with graceful error handling."""
        try:
            return func()
        except Exception as exc:
            LOG.error("Monitor %s failed: %s", func.__name__, exc)
            return default

    # ─── 1. Crude Volatility ────────────────────────────────────────────

    def monitor_crude_volatility(self) -> dict:
        """
        Track crude price RSI, Bollinger bands, % changes.
        Flags P0 if weekly swing > 5%.
        """
        raw = _load_json(BASE / "tbl_crude_prices.json", [])
        brent = _extract_price_series(raw, "Brent", 60)
        wti = _extract_price_series(raw, "WTI", 60)

        if not brent:
            return {"status": "no_data", "severity": None}

        weekly_change = _pct_change(brent, 7)
        daily_change = _pct_change(brent, 1)
        rsi_val = _rsi(brent)
        bb = _bollinger_bands(brent)

        # Determine severity
        severity = None
        if abs(weekly_change) > 5:
            severity = "P0"
        elif abs(weekly_change) > 3:
            severity = "P1"
        elif abs(weekly_change) > 1.5:
            severity = "P2"

        # Direction
        if weekly_change > 1:
            direction = "RISING"
        elif weekly_change < -1:
            direction = "FALLING"
        else:
            direction = "STABLE"

        # Overbought/oversold
        if rsi_val > 70:
            rsi_label = "OVERBOUGHT"
        elif rsi_val < 30:
            rsi_label = "OVERSOLD"
        else:
            rsi_label = "NEUTRAL"

        # ML forecast overlay
        forecast_direction = None
        if _HAS_ML_FORECAST:
            try:
                fc = forecast_crude_price(days_ahead=30)
                forecast_direction = fc.get("direction", None)
            except Exception:
                pass

        return {
            "status": "active",
            "current_brent": brent[-1] if brent else None,
            "current_wti": wti[-1] if wti else None,
            "weekly_change_pct": weekly_change,
            "daily_change_pct": daily_change,
            "rsi": rsi_val,
            "rsi_label": rsi_label,
            "bollinger": bb,
            "direction": direction,
            "severity": severity,
            "forecast_direction": forecast_direction,
            "data_points": len(brent),
        }

    # ─── 2. Supply Disruptions ──────────────────────────────────────────

    def monitor_supply_disruptions(self) -> list[dict]:
        """
        Combine refinery news + port congestion + vessel delays into
        supply disruption alerts.
        """
        disruptions: list[dict] = []

        # (a) Refinery news from tbl_news_feed
        news = _load_json(BASE / "tbl_news_feed.json", [])
        for article in news[-200:]:
            headline = (article.get("headline") or "").lower()
            matched = [kw for kw in _SUPPLY_KEYWORDS if kw in headline]
            if matched:
                sentiment_score = article.get("sentiment_score")
                if _HAS_FINBERT and sentiment_score is None:
                    try:
                        result = analyze_financial_sentiment(article.get("headline", ""))
                        sentiment_score = result.get("score", 0.5)
                    except Exception:
                        sentiment_score = 0.5

                disruptions.append({
                    "type": "refinery_news",
                    "headline": article.get("headline", ""),
                    "keywords_matched": matched,
                    "sentiment": sentiment_score,
                    "date": article.get("date_time", ""),
                    "severity": "P0" if any(k in matched for k in
                                            ["shutdown", "explosion", "fire", "force majeure"]) else "P1",
                })

        # (b) Refinery production anomalies
        refinery = _load_json(BASE / "tbl_refinery_production.json", [])
        if refinery:
            production_by_refinery: dict[str, list[float]] = {}
            for rec in refinery:
                name = rec.get("refinery_or_region", "")
                qty = rec.get("quantity")
                if name and qty and name != "All India Total":
                    production_by_refinery.setdefault(name, []).append(float(qty))

            for name, qtys in production_by_refinery.items():
                if len(qtys) >= 2 and qtys[-1] < qtys[-2] * 0.7:
                    disruptions.append({
                        "type": "refinery_production_drop",
                        "refinery": name,
                        "previous": qtys[-2],
                        "current": qtys[-1],
                        "drop_pct": round((1 - qtys[-1] / qtys[-2]) * 100, 1),
                        "severity": "P1",
                    })

        # (c) Vessel delays from maritime intel
        maritime = _load_json(BASE / "tbl_maritime_intel.json", {})
        vessels = maritime.get("vessels", []) if isinstance(maritime, dict) else []
        for v in vessels:
            delay = v.get("delay_factor", 1.0)
            if delay > 1.2:
                disruptions.append({
                    "type": "vessel_delay",
                    "vessel": v.get("vessel_name", "Unknown"),
                    "route": f"{v.get('departure_port', '?')} -> {v.get('destination_port', '?')}",
                    "delay_factor": delay,
                    "cargo_mt": v.get("cargo_mt", 0),
                    "eta": v.get("eta", ""),
                    "severity": "P1" if delay > 1.5 else "P2",
                })

        return disruptions

    # ─── 3. Demand Signals ──────────────────────────────────────────────

    def monitor_demand_signals(self) -> list[dict]:
        """
        Combine infra tenders + seasonal patterns + weather data to produce
        demand alerts segmented by state/region.
        """
        signals: list[dict] = []
        now = _now_ist()
        month = now.month

        # (a) Seasonal baseline
        seasonal_score = _SEASONAL_WEIGHTS.get(month, 15)
        if seasonal_score >= 25:
            season_label = "PEAK"
        elif seasonal_score <= 8:
            season_label = "MONSOON_LOW"
        else:
            season_label = "MODERATE"

        signals.append({
            "type": "seasonal",
            "score": seasonal_score,
            "label": season_label,
            "detail": f"Month {month} seasonal demand score: {seasonal_score}/30",
        })

        # (b) News-based demand (NHAI tenders, highway construction)
        news = _load_json(BASE / "tbl_news_feed.json", [])
        demand_articles: list[dict] = []
        for article in news[-200:]:
            headline = (article.get("headline") or "").lower()
            matched = [kw for kw in _DEMAND_KEYWORDS if kw in headline]
            if matched:
                # Try to identify state from headline
                state = self._detect_state(article.get("headline", ""))
                demand_articles.append({
                    "headline": article.get("headline", ""),
                    "state": state,
                    "keywords": matched,
                    "date": article.get("date_time", ""),
                })

        if demand_articles:
            # Aggregate by state
            state_counts: dict[str, int] = {}
            for da in demand_articles:
                st = da.get("state") or "India (general)"
                state_counts[st] = state_counts.get(st, 0) + 1

            for state, count in state_counts.items():
                severity = "P1" if count >= 3 else "P2"
                signals.append({
                    "type": "infra_tender",
                    "state": state,
                    "article_count": count,
                    "severity": severity,
                    "detail": f"{count} infrastructure/tender article(s) detected for {state}",
                })

        # (c) Weather impact on demand
        weather = _load_json(BASE / "tbl_weather.json", [])
        if weather:
            rain_cities: dict[str, float] = {}
            for w in weather[-100:]:
                loc = w.get("location", "")
                rain = w.get("rain_mm", 0.0)
                if loc:
                    rain_cities[loc] = max(rain_cities.get(loc, 0.0), float(rain or 0))

            for city, rain_mm in rain_cities.items():
                if rain_mm > 50:
                    signals.append({
                        "type": "weather_disruption",
                        "city": city,
                        "rain_mm": rain_mm,
                        "severity": "P1" if rain_mm > 100 else "P2",
                        "detail": f"Heavy rainfall ({rain_mm}mm) in {city} — road work likely halted",
                    })
                elif rain_mm == 0 and seasonal_score >= 20:
                    signals.append({
                        "type": "weather_favorable",
                        "city": city,
                        "rain_mm": 0,
                        "detail": f"Dry conditions in {city} — favorable for construction",
                    })

        # (d) Infra demand engine integration
        if _HAS_INFRA_DEMAND:
            try:
                infra_alerts = infra_demand_engine.get_infra_alerts(status="new", limit=10)
                for ia in infra_alerts:
                    signals.append({
                        "type": "infra_engine_alert",
                        "state": ia.get("state", ""),
                        "severity": ia.get("severity", "P2"),
                        "detail": ia.get("message", ia.get("title", "")),
                        "source": "infra_demand_engine",
                    })
            except Exception as exc:
                LOG.debug("Infra demand engine unavailable: %s", exc)

        return signals

    # ─── 4. FX Impact ───────────────────────────────────────────────────

    def monitor_fx_impact(self) -> dict:
        """
        Track INR/USD movements and calculate import cost impact.
        A 1% INR depreciation raises import cost by ~1% directly.
        """
        raw = _load_json(BASE / "tbl_fx_rates.json", [])
        inr_rates = _extract_fx_series(raw, "USD/INR", 60)

        if not inr_rates:
            return {"status": "no_data"}

        weekly_change = _pct_change(inr_rates, 7)
        daily_change = _pct_change(inr_rates, 1)
        current = inr_rates[-1]

        # INR weakening = rate going UP (more rupees per dollar)
        if weekly_change > 0.5:
            direction = "WEAKENING"
            impact = "NEGATIVE"  # bad for importers
        elif weekly_change < -0.5:
            direction = "STRENGTHENING"
            impact = "POSITIVE"  # good for importers
        else:
            direction = "STABLE"
            impact = "NEUTRAL"

        severity = None
        if abs(weekly_change) > 2:
            severity = "P0"
        elif abs(weekly_change) > 1:
            severity = "P1"
        elif abs(weekly_change) > 0.5:
            severity = "P2"

        # Estimate cost impact per MT
        # Typical import: ~₹ 400/MT CFR -> at Rs 87, that is Rs 34,800
        import_usd_per_mt = 400
        cost_at_current = import_usd_per_mt * current
        cost_at_week_ago = import_usd_per_mt * (inr_rates[-min(8, len(inr_rates))]
                                                  if len(inr_rates) > 1 else current)
        cost_delta_inr = round(cost_at_current - cost_at_week_ago, 0)

        # ML forecast overlay
        forecast_direction = None
        if _HAS_ML_FORECAST:
            try:
                fc = forecast_fx_rate(days_ahead=30)
                forecast_direction = fc.get("direction", None)
            except Exception:
                pass

        return {
            "status": "active",
            "current_rate": current,
            "weekly_change_pct": weekly_change,
            "daily_change_pct": daily_change,
            "direction": direction,
            "impact": impact,
            "severity": severity,
            "cost_delta_inr_per_mt": cost_delta_inr,
            "forecast_direction": forecast_direction,
            "data_points": len(inr_rates),
        }

    # ─── 5. Logistics ───────────────────────────────────────────────────

    def monitor_logistics(self) -> dict:
        """Track port congestion, shipping routes, BDI changes."""
        ports = _load_json(BASE / "tbl_ports_volume.json", [])
        maritime = _load_json(BASE / "tbl_maritime_intel.json", {})

        # Port volumes
        port_summary: dict[str, dict] = {}
        for rec in ports[-100:]:
            name = rec.get("port_name", "")
            qty = rec.get("quantity", 0)
            if name:
                if name not in port_summary:
                    port_summary[name] = {"volumes": [], "latest": 0}
                port_summary[name]["volumes"].append(float(qty))
                port_summary[name]["latest"] = float(qty)

        congestion_level = "NORMAL"
        congested_ports: list[str] = []
        for name, data in port_summary.items():
            if data["latest"] > _PORT_HIGH_THRESHOLD:
                congested_ports.append(name)

        if len(congested_ports) >= 2:
            congestion_level = "HIGH"
        elif congested_ports:
            congestion_level = "MODERATE"

        # BDI from maritime intel
        bdi_value = None
        bdi_change = None
        if isinstance(maritime, dict):
            market = maritime.get("market_indicators", {})
            bdi_value = market.get("bdi")
            bdi_change = market.get("bdi_change_pct")

        # Vessel tracking summary
        vessels = maritime.get("vessels", []) if isinstance(maritime, dict) else []
        delayed_vessels = [v for v in vessels if v.get("delay_factor", 1.0) > 1.15]
        en_route_cargo_mt = sum(v.get("cargo_mt", 0) for v in vessels
                                if v.get("status") in ("en_route", "arriving"))

        severity = None
        if congestion_level == "HIGH" and len(delayed_vessels) > 2:
            severity = "P0"
        elif congestion_level == "HIGH" or len(delayed_vessels) > 1:
            severity = "P1"
        elif congested_ports or delayed_vessels:
            severity = "P2"

        return {
            "status": "active",
            "congestion_level": congestion_level,
            "congested_ports": congested_ports,
            "port_summary": {k: v["latest"] for k, v in port_summary.items()},
            "bdi": bdi_value,
            "bdi_change_pct": bdi_change,
            "delayed_vessels": len(delayed_vessels),
            "en_route_cargo_mt": en_route_cargo_mt,
            "total_vessels_tracked": len(vessels),
            "severity": severity,
        }

    # ─── 6. Cross-correlation → contextual alerts ───────────────────────

    def _cross_correlate(self, crude: dict, fx: dict, supply: list,
                         demand: list, logistics: dict) -> list[dict]:
        """
        Apply cross-correlation rules to generate actionable,
        natural-language alerts with recommended actions.
        """
        alerts: list[dict] = []
        now = _now_ist()
        expire_default = now + timedelta(hours=24)

        crude_dir = crude.get("direction", "STABLE")
        crude_sev = crude.get("severity")
        crude_weekly = crude.get("weekly_change_pct", 0)
        fx_dir = fx.get("direction", "STABLE")
        fx_sev = fx.get("severity")
        congestion = logistics.get("congestion_level", "NORMAL")
        bdi_change = logistics.get("bdi_change_pct") or 0

        # ── Rule 1: Crude up + INR weakening ────────────────────────────
        if crude_dir == "RISING" and fx_dir == "WEAKENING":
            alerts.append(self.generate_contextual_alert("price", {
                "message": (f"Double cost pressure: Crude Brent up {crude_weekly}% this week "
                            f"AND INR weakening — import costs rising sharply"),
                "impact": "Landed cost of imported bitumen will increase significantly within 7-10 days",
                "action": "Consider domestic sourcing or lock purchase prices immediately",
                "severity": "P0" if crude_sev == "P0" or fx_sev == "P0" else "P1",
                "confidence": 85,
                "sources": ["tbl_crude_prices", "tbl_fx_rates"],
            }))

        # ── Rule 2: Port congestion + monsoon approaching ───────────────
        month = now.month
        monsoon_approaching = month in (5, 6)
        if congestion == "HIGH" and monsoon_approaching:
            alerts.append(self.generate_contextual_alert("logistics", {
                "message": "Port congestion HIGH with monsoon season approaching — expect shipping delays",
                "impact": "Delivery lead times will extend by 7-14 days; coastal routes may face weather disruptions",
                "action": "Pre-stock bitumen inventory now; negotiate freight rates before monsoon premium kicks in",
                "severity": "P0",
                "confidence": 80,
                "sources": ["tbl_ports_volume", "tbl_weather"],
            }))

        # ── Rule 3: Refinery shutdown + low inventory ───────────────────
        shutdown_alerts = [s for s in supply if s.get("type") == "refinery_news"
                          and s.get("severity") == "P0"]
        if shutdown_alerts:
            alerts.append(self.generate_contextual_alert("supply", {
                "message": (f"Supply shortage imminent: {len(shutdown_alerts)} critical "
                            f"refinery disruption(s) detected"),
                "impact": "Domestic bitumen supply likely to tighten within 1-2 weeks",
                "action": "Secure purchase contracts now; consider importing to fill supply gap",
                "severity": "P0",
                "confidence": 75,
                "sources": ["tbl_news_feed", "tbl_refinery_production"],
            }))

        # ── Rule 4: NHAI tender surge + dry season ──────────────────────
        tender_signals = [d for d in demand if d.get("type") == "infra_tender"]
        is_dry_season = _SEASONAL_WEIGHTS.get(month, 15) >= 20
        if len(tender_signals) >= 2 and is_dry_season:
            states = [t.get("state", "India") for t in tender_signals]
            states_str = ", ".join(set(s for s in states if s))[:80] or "multiple states"
            total_articles = sum(t.get("article_count", 0) for t in tender_signals)
            alerts.append(self.generate_contextual_alert("demand", {
                "message": (f"Demand spike expected: {total_articles} tender/infra articles "
                            f"detected during peak construction season in {states_str}"),
                "impact": f"Bitumen demand likely to increase in {states_str} over next 2-4 weeks",
                "action": "Proactively reach out to contractors in these regions; prepare competitive quotes",
                "severity": "P1",
                "confidence": 70,
                "sources": ["tbl_news_feed", "infra_demand_engine"],
            }))

        # ── Rule 5: BDI rising + crude rising ───────────────────────────
        if bdi_change and float(bdi_change) > 3 and crude_dir == "RISING":
            alerts.append(self.generate_contextual_alert("logistics", {
                "message": (f"Freight costs increasing: BDI up {bdi_change}% "
                            f"combined with rising crude prices"),
                "impact": "Shipping and fuel surcharges will push landed import costs higher",
                "action": "Lock freight rates now; consider long-term shipping contracts",
                "severity": "P1",
                "confidence": 72,
                "sources": ["tbl_maritime_intel", "tbl_crude_prices"],
            }))

        # ── Rule 6: Multiple bullish signals → STRONG BUY ──────────────
        bullish_count = 0
        if crude_dir == "RISING":
            bullish_count += 1
        if fx_dir == "WEAKENING":
            bullish_count += 1
        if len(tender_signals) >= 2:
            bullish_count += 1
        if is_dry_season:
            bullish_count += 1
        if crude.get("forecast_direction") == "UP":
            bullish_count += 1

        if bullish_count >= 4:
            alerts.append(self.generate_contextual_alert("price", {
                "message": (f"STRONG BUY signal: {bullish_count}/5 indicators bullish — "
                            f"crude rising, INR weak, high demand season, tender surge"),
                "impact": "Bitumen prices highly likely to increase within 7-14 days",
                "action": "Buy aggressively at current prices; lock maximum volume with suppliers",
                "severity": "P0",
                "confidence": min(90, 60 + bullish_count * 6),
                "sources": ["tbl_crude_prices", "tbl_fx_rates", "tbl_news_feed"],
            }))
        elif bullish_count >= 3:
            alerts.append(self.generate_contextual_alert("price", {
                "message": (f"BUY signal: {bullish_count}/5 indicators bullish — "
                            f"market momentum favours price increase"),
                "impact": "Bitumen prices likely to rise in the near term",
                "action": "Consider increasing stock levels and locking current prices",
                "severity": "P1",
                "confidence": min(80, 55 + bullish_count * 5),
                "sources": ["tbl_crude_prices", "tbl_fx_rates", "tbl_news_feed"],
            }))

        # ── Rule 7: Single significant crude move ───────────────────────
        if crude_sev and not any(a.get("category") == "price" for a in alerts):
            direction_word = "up" if crude_weekly > 0 else "down"
            alerts.append(self.generate_contextual_alert("price", {
                "message": (f"Crude Brent {direction_word} {abs(crude_weekly)}% this week "
                            f"— expect bitumen price {'increase' if crude_weekly > 0 else 'decrease'} "
                            f"in 7-10 days"),
                "impact": (f"Landed cost of bitumen will {'rise' if crude_weekly > 0 else 'fall'} "
                           f"proportionally"),
                "action": (f"{'Buy now before prices increase' if crude_weekly > 0 else 'Wait for prices to drop further'}"
                           ),
                "severity": crude_sev,
                "confidence": 65,
                "sources": ["tbl_crude_prices"],
            }))

        # ── Rule 8: Heavy rain = construction halt ──────────────────────
        rain_signals = [d for d in demand if d.get("type") == "weather_disruption"]
        if rain_signals:
            cities = [r.get("city", "") for r in rain_signals]
            alerts.append(self.generate_contextual_alert("demand", {
                "message": f"Heavy rainfall in {', '.join(cities)} — road construction likely halted",
                "impact": "Short-term demand reduction in affected regions",
                "action": "Defer deliveries to affected areas; redirect stock to dry regions",
                "severity": "P2",
                "confidence": 60,
                "sources": ["tbl_weather"],
            }))

        # ── Rule 9: Vessel delays ───────────────────────────────────────
        delayed_count = logistics.get("delayed_vessels", 0)
        if delayed_count > 0:
            alerts.append(self.generate_contextual_alert("logistics", {
                "message": f"{delayed_count} vessel(s) delayed on bitumen import routes",
                "impact": "Import deliveries may be delayed; spot market could tighten",
                "action": "Check alternative suppliers; domestic procurement as backup",
                "severity": "P1" if delayed_count >= 3 else "P2",
                "confidence": 65,
                "sources": ["tbl_maritime_intel"],
            }))

        return alerts

    # ─── 7. Generate contextual alert ───────────────────────────────────

    def generate_contextual_alert(self, signal_type: str, data: dict) -> dict:
        """
        Cross-correlate signals into a structured, natural-language alert
        with standard fields.

        Args:
            signal_type: One of 'supply', 'demand', 'price', 'logistics', 'policy'.
            data: Dict with keys: message, impact, action, severity, confidence, sources.

        Returns:
            Standard alert dict per the Alert Data Model.
        """
        now = _now_ist()
        message = data.get("message", "Market alert")
        severity = data.get("severity", "P2")

        # Expiry: P0 = 12h, P1 = 24h, P2 = 48h
        expiry_hours = {"P0": 12, "P1": 24, "P2": 48}.get(severity, 24)
        expires = now + timedelta(hours=expiry_hours)

        return {
            "id": _alert_id(signal_type, message),
            "severity": severity,
            "category": signal_type,
            "message": message,
            "impact": data.get("impact", ""),
            "action": data.get("action", ""),
            "confidence": data.get("confidence", 50),
            "created_at": _ts_str(now),
            "expires_at": _ts_str(expires),
            "sources": data.get("sources", []),
        }

    # ─── 8. Active alerts ───────────────────────────────────────────────

    def get_active_alerts(self, max_age_hours: int = 24) -> list[dict]:
        """Return alerts not yet expired, up to max_age_hours old."""
        now = _now_ist()
        cutoff = now - timedelta(hours=max_age_hours)
        all_alerts = _load_alerts()
        active: list[dict] = []

        for a in all_alerts:
            # Parse created_at: "DD-MM-YYYY HH:MM IST"
            created_str = a.get("created_at", "")
            try:
                created_dt = datetime.strptime(
                    created_str.replace(" IST", ""), "%Y-%m-%d %H:%M"
                ).replace(tzinfo=IST)
            except (ValueError, TypeError):
                continue

            if created_dt >= cutoff:
                active.append(a)

        # Sort by severity (P0 first) then by created_at descending
        severity_order = {"P0": 0, "P1": 1, "P2": 2}
        active.sort(key=lambda x: (
            severity_order.get(x.get("severity", "P2"), 3),
            x.get("created_at", ""),
        ))
        # Reverse second key so newest first within same severity
        active.sort(key=lambda x: severity_order.get(x.get("severity", "P2"), 3))

        return active

    # ─── 9. Market state summary ────────────────────────────────────────

    def get_market_state_summary(self) -> dict:
        """
        One-shot summary of all market conditions.
        Suitable for display on the dashboard homepage.
        """
        result = self.monitor_all()
        return result.get("market_state", self._build_market_state(
            result.get("crude", {}),
            result.get("fx", {}),
            result.get("supply_disruptions", []),
            result.get("demand_signals", []),
            result.get("logistics", {}),
        ))

    def _build_market_state(self, crude: dict, fx: dict, supply: list,
                            demand: list, logistics: dict) -> dict:
        """Assemble a high-level market state object."""
        now = _now_ist()
        month = now.month
        seasonal = _SEASONAL_WEIGHTS.get(month, 15)

        # Overall market bias
        bullish = 0
        bearish = 0

        if crude.get("direction") == "RISING":
            bullish += 2
        elif crude.get("direction") == "FALLING":
            bearish += 2

        if fx.get("direction") == "WEAKENING":
            bullish += 1  # costs go up
        elif fx.get("direction") == "STRENGTHENING":
            bearish += 1  # costs go down

        if seasonal >= 22:
            bullish += 1
        elif seasonal <= 8:
            bearish += 1

        supply_disruptions_critical = len([s for s in supply if s.get("severity") == "P0"])
        if supply_disruptions_critical:
            bullish += 2

        tender_signals = len([d for d in demand if d.get("type") == "infra_tender"])
        if tender_signals >= 2:
            bullish += 1

        if logistics.get("congestion_level") == "HIGH":
            bullish += 1  # supply constrained

        total = bullish + bearish
        if total == 0:
            bias = "NEUTRAL"
            bias_score = 50
        elif bullish > bearish:
            bias = "BULLISH"
            bias_score = min(95, 50 + (bullish - bearish) * 8)
        else:
            bias = "BEARISH"
            bias_score = max(5, 50 - (bearish - bullish) * 8)

        # Market intelligence overlay
        intel_signal = None
        if _HAS_MARKET_INTEL:
            try:
                engine = MarketIntelligenceEngine()
                master = engine.compute_all_signals().get("master", {})
                intel_signal = {
                    "direction": master.get("market_direction"),
                    "confidence": master.get("confidence"),
                    "action": master.get("action"),
                }
            except Exception:
                pass

        # Active alerts count by severity
        active = self.get_active_alerts(max_age_hours=24)
        alert_counts = {"P0": 0, "P1": 0, "P2": 0}
        for a in active:
            sev = a.get("severity", "P2")
            alert_counts[sev] = alert_counts.get(sev, 0) + 1

        return {
            "timestamp": _ts_str(),
            "market_bias": bias,
            "bias_score": bias_score,
            "crude_direction": crude.get("direction", "UNKNOWN"),
            "crude_brent_usd": crude.get("current_brent"),
            "crude_weekly_change": crude.get("weekly_change_pct", 0),
            "fx_direction": fx.get("direction", "UNKNOWN"),
            "fx_rate": fx.get("current_rate"),
            "fx_weekly_change": fx.get("weekly_change_pct", 0),
            "seasonal_score": seasonal,
            "seasonal_label": "PEAK" if seasonal >= 25 else "LOW" if seasonal <= 8 else "MODERATE",
            "supply_disruptions": len(supply),
            "supply_critical": supply_disruptions_critical,
            "demand_signals": len(demand),
            "tender_activity": tender_signals,
            "logistics_congestion": logistics.get("congestion_level", "UNKNOWN"),
            "delayed_vessels": logistics.get("delayed_vessels", 0),
            "alert_counts": alert_counts,
            "total_active_alerts": len(active),
            "intel_signal": intel_signal,
            "recommendation": self._state_recommendation(bias, bias_score, active),
        }

    @staticmethod
    def _state_recommendation(bias: str, score: int, active_alerts: list) -> str:
        """Generate a one-line trading recommendation from market state."""
        p0_count = sum(1 for a in active_alerts if a.get("severity") == "P0")

        if p0_count >= 2:
            return "URGENT: Multiple critical alerts active — review immediately and take defensive positions"
        if bias == "BULLISH" and score >= 75:
            return "STRONG BUY: Market conditions favour aggressive procurement at current prices"
        if bias == "BULLISH" and score >= 60:
            return "BUY: Favourable conditions — consider increasing stock levels"
        if bias == "BEARISH" and score <= 25:
            return "WAIT: Market turning bearish — defer large purchases, prices may soften"
        if bias == "BEARISH" and score <= 40:
            return "HOLD: Mild bearish signals — maintain current stock, avoid overbuying"
        return "NEUTRAL: Market stable — proceed with normal procurement"

    # ─── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _detect_state(text: str) -> Optional[str]:
        """Simple state detection from headline text."""
        text_lower = text.lower()
        states = {
            "gujarat": "Gujarat", "rajasthan": "Rajasthan",
            "maharashtra": "Maharashtra", "madhya pradesh": "Madhya Pradesh",
            "uttar pradesh": "Uttar Pradesh", "karnataka": "Karnataka",
            "tamil nadu": "Tamil Nadu", "andhra pradesh": "Andhra Pradesh",
            "telangana": "Telangana", "kerala": "Kerala",
            "odisha": "Odisha", "bihar": "Bihar",
            "west bengal": "West Bengal", "punjab": "Punjab",
            "haryana": "Haryana", "chhattisgarh": "Chhattisgarh",
            "jharkhand": "Jharkhand", "assam": "Assam",
            "himachal pradesh": "Himachal Pradesh", "uttarakhand": "Uttarakhand",
            "goa": "Goa",
        }
        for key, name in states.items():
            if key in text_lower:
                return name
        return None


# ═════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def monitor_all() -> dict:
    """Module-level shortcut for MarketPulseEngine().monitor_all()."""
    engine = MarketPulseEngine()
    return engine.monitor_all()


def get_active_alerts(max_age_hours: int = 24) -> list[dict]:
    """Module-level shortcut for active alerts retrieval."""
    engine = MarketPulseEngine()
    return engine.get_active_alerts(max_age_hours=max_age_hours)


def get_market_state_summary() -> dict:
    """Module-level shortcut for dashboard market state."""
    engine = MarketPulseEngine()
    return engine.get_market_state_summary()


def get_pulse_status() -> dict:
    """Status report for AI module registry / health checks."""
    return {
        "engine": "MarketPulseEngine",
        "version": "1.0",
        "alerts_file": str(ALERTS_FILE),
        "max_alerts": MAX_ALERTS,
        "dependencies": {
            "api_hub_engine": _HAS_HUB_CACHE,
            "market_intelligence_engine": _HAS_MARKET_INTEL,
            "finbert_engine": _HAS_FINBERT,
            "ml_forecast_engine": _HAS_ML_FORECAST,
            "forward_strategy_engine": _HAS_FORWARD_STRATEGY,
            "infra_demand_engine": _HAS_INFRA_DEMAND,
        },
        "cross_correlation_rules": 9,
        "alert_categories": ["supply", "demand", "price", "logistics", "policy"],
        "severity_levels": ["P0", "P1", "P2"],
    }
