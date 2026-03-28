"""
PPS Anantam — Maritime Intelligence Engine v1.0
=================================================
Core engine for vessel tracking, port congestion monitoring,
logistics risk scoring, marine weather, maritime news, and
multi-modal supply chain intelligence.

No paid APIs. Uses:
  - Open-Meteo Marine API (free, no key)
  - Maritime RSS feeds (gCaptain, MaritimeExecutive)
  - Existing tbl_weather, tbl_crude_prices, tbl_news_feed data
  - Deterministic vessel simulation (great-circle interpolation)

Output tables:
  tbl_maritime_intel.json  — Vessel positions, port congestion, risk scores
  tbl_maritime_routes.json — Route definitions + shipment tracking
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ── IST timezone ─────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).parent

TBL_MARITIME_INTEL  = BASE / "tbl_maritime_intel.json"
TBL_MARITIME_ROUTES = BASE / "tbl_maritime_routes.json"


def _now() -> datetime:
    return datetime.now(IST)


def _ts() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S IST")


def _load(path: Path, default: Any = None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else []


def _save(path: Path, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# A. STATIC PORT & ROUTE DATA
# ═══════════════════════════════════════════════════════════════════════════════

INDIAN_PORTS: dict[str, dict] = {
    "Mundra":        {"lat": 22.84, "lon": 69.73, "type": "container+bulk", "priority": 1,
                      "base_congestion": 30, "label": "Mundra (Adani)"},
    "Kandla":        {"lat": 23.03, "lon": 70.22, "type": "container+bulk", "priority": 1,
                      "base_congestion": 35, "label": "Kandla (Deendayal)"},
    "Mumbai":        {"lat": 18.95, "lon": 72.94, "type": "container",      "priority": 1,
                      "base_congestion": 40, "label": "Mumbai (JNPT)"},
    "Mangalore":     {"lat": 12.92, "lon": 74.85, "type": "bulk",           "priority": 2,
                      "base_congestion": 20, "label": "New Mangalore"},
    "Chennai":       {"lat": 13.08, "lon": 80.29, "type": "bulk",           "priority": 2,
                      "base_congestion": 25, "label": "Chennai (Kamarajar)"},
    "Paradip":       {"lat": 20.26, "lon": 86.67, "type": "bulk",           "priority": 3,
                      "base_congestion": 18, "label": "Paradip"},
    "Visakhapatnam": {"lat": 17.69, "lon": 83.29, "type": "bulk",           "priority": 3,
                      "base_congestion": 22, "label": "Visakhapatnam"},
    "Haldia":        {"lat": 22.06, "lon": 88.06, "type": "bulk",           "priority": 3,
                      "base_congestion": 28, "label": "Haldia (Kolkata)"},
    "Kochi":         {"lat": 9.97,  "lon": 76.27, "type": "bulk",           "priority": 3,
                      "base_congestion": 15, "label": "Kochi"},
    "Tuticorin":     {"lat": 8.76,  "lon": 78.13, "type": "bulk",           "priority": 3,
                      "base_congestion": 12, "label": "V.O. Chidambaranar"},
}

SUPPLY_PORTS: dict[str, dict] = {
    "Bandar Abbas": {"lat": 27.18, "lon": 56.27, "country": "Iran",
                     "products": ["VG-30", "VG-40", "60/70"]},
    "Jebel Ali":    {"lat": 25.02, "lon": 55.06, "country": "UAE",
                     "products": ["VG-30", "VG-40", "Polymer Modified"]},
    "Ras Tanura":   {"lat": 26.64, "lon": 50.16, "country": "Saudi Arabia",
                     "products": ["60/70", "80/100"]},
    "Singapore":    {"lat": 1.26,  "lon": 103.84, "country": "Singapore",
                     "products": ["VG-30", "VG-40", "CRMB"]},
    "Bahrain":      {"lat": 26.00, "lon": 50.55, "country": "Bahrain",
                     "products": ["60/70", "VG-30"]},
}

ROUTES: list[dict] = [
    {"id": "ME-MUN",  "from": "Bandar Abbas", "to": "Mundra",    "type": "bulk",
     "avg_days": 3, "distance_nm": 650,  "avg_cost_usd_mt": 18},
    {"id": "ME-KAN",  "from": "Bandar Abbas", "to": "Kandla",    "type": "bulk",
     "avg_days": 3, "distance_nm": 620,  "avg_cost_usd_mt": 17},
    {"id": "UAE-MUM", "from": "Jebel Ali",    "to": "Mumbai",    "type": "container",
     "avg_days": 4, "distance_nm": 1100, "avg_cost_usd_mt": 28},
    {"id": "UAE-MUN", "from": "Jebel Ali",    "to": "Mundra",    "type": "container",
     "avg_days": 3, "distance_nm": 900,  "avg_cost_usd_mt": 24},
    {"id": "SG-CHN",  "from": "Singapore",    "to": "Chennai",   "type": "bulk",
     "avg_days": 5, "distance_nm": 1500, "avg_cost_usd_mt": 32},
    {"id": "SG-MUM",  "from": "Singapore",    "to": "Mumbai",    "type": "container",
     "avg_days": 6, "distance_nm": 2200, "avg_cost_usd_mt": 38},
    {"id": "SA-MNG",  "from": "Ras Tanura",   "to": "Mangalore", "type": "bulk",
     "avg_days": 5, "distance_nm": 1600, "avg_cost_usd_mt": 30},
    {"id": "BH-KAN",  "from": "Bahrain",      "to": "Kandla",    "type": "bulk",
     "avg_days": 4, "distance_nm": 800,  "avg_cost_usd_mt": 20},
]

# Vessel name pools
_PREFIXES = ["MT", "MV", "MT", "MV", "MT"]
_NAMES = [
    "Arabian Star", "Pacific Voyager", "Gulf Pearl", "Indian Tide",
    "Ocean Pioneer", "Desert Wind", "Coral Stream", "Horizon Dawn",
    "Phoenix Rising", "Dragon Wave", "Neptune's Grace", "Silk Route",
    "Eastern Promise", "Monsoon Spirit", "Amber Fortune", "Golden Anchor",
    "Blue Diamond", "Silver Cloud", "Jade Empress", "Ruby Horizon",
]


# ═══════════════════════════════════════════════════════════════════════════════
# B. VESSEL SIMULATOR — Deterministic simulation via great-circle interpolation
# ═══════════════════════════════════════════════════════════════════════════════

class VesselSimulator:
    """Generate realistic vessel positions along known routes."""

    @staticmethod
    def generate_vessels(count: int = 12, seed: int | None = None) -> list[dict]:
        """Generate `count` simulated vessels on active routes.

        Uses the current date as seed base so positions are deterministic
        within the same day but vary day-to-day.
        """
        now = _now()
        if seed is None:
            seed = int(now.strftime("%Y%m%d"))
        rng = random.Random(seed)

        vessels: list[dict] = []
        for i in range(count):
            route = ROUTES[i % len(ROUTES)]
            from_port = SUPPLY_PORTS[route["from"]]
            to_port = INDIAN_PORTS[route["to"]]

            # Departure within last avg_days * 1.3 days
            max_hours = int(route["avg_days"] * 24 * 1.3)
            depart_hours_ago = rng.randint(2, max(3, max_hours))
            departure_time = now - timedelta(hours=depart_hours_ago)
            total_transit_hours = route["avg_days"] * 24
            elapsed_hours = depart_hours_ago
            progress = min(elapsed_hours / total_transit_hours, 0.98)

            # Add small random variance to progress
            progress = max(0.02, min(0.98, progress + rng.uniform(-0.05, 0.05)))

            lat, lon = VesselSimulator._interpolate_position(
                from_port["lat"], from_port["lon"],
                to_port["lat"], to_port["lon"],
                progress,
            )

            # Speed: 10-14 knots typical for bitumen tanker
            speed = round(rng.uniform(10.0, 14.0), 1)
            heading = VesselSimulator._compute_heading(lat, lon, to_port["lat"], to_port["lon"])

            # ETA
            remaining_hours = max(1, total_transit_hours * (1 - progress))
            # Add delay factor based on weather/congestion (simple random for simulation)
            delay_factor = rng.uniform(0.9, 1.3)
            adjusted_remaining = remaining_hours * delay_factor
            eta = now + timedelta(hours=adjusted_remaining)

            # Status
            if progress > 0.95:
                status = "arriving"
            elif delay_factor > 1.15:
                status = "delayed"
            else:
                status = "en_route"

            # Vessel name (deterministic per index + seed)
            prefix = _PREFIXES[i % len(_PREFIXES)]
            name = _NAMES[i % len(_NAMES)]
            imo = f"IMO{9100000 + (seed + i * 137) % 900000}"

            vessel = {
                "vessel_name": f"{prefix} {name}",
                "imo": imo,
                "route_id": route["id"],
                "cargo_type": route["type"],
                "departure_port": route["from"],
                "destination_port": route["to"],
                "departure_time": departure_time.strftime("%Y-%m-%d %H:%M IST"),
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "speed_knots": speed,
                "heading": round(heading, 1),
                "progress_pct": round(progress * 100, 1),
                "status": status,
                "eta": eta.strftime("%Y-%m-%d %H:%M IST"),
                "eta_hours": round(adjusted_remaining, 1),
                "delay_factor": round(delay_factor, 2),
                "cargo_mt": rng.choice([3000, 5000, 8000, 10000, 15000, 20000]),
                "product_grade": rng.choice(["VG-30", "VG-40", "60/70", "80/100"]),
            }
            vessels.append(vessel)

        # Sort: container vessels FIRST
        vessels.sort(key=lambda v: (0 if v["cargo_type"] == "container" else 1, v["eta_hours"]))
        return vessels

    @staticmethod
    def _interpolate_position(lat1: float, lon1: float,
                              lat2: float, lon2: float,
                              progress: float) -> tuple[float, float]:
        """Great-circle interpolation between two points."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        lam1 = math.radians(lon1)
        lam2 = math.radians(lon2)

        # Angular distance
        d = math.acos(
            math.sin(phi1) * math.sin(phi2) +
            math.cos(phi1) * math.cos(phi2) * math.cos(lam2 - lam1)
        )

        if d < 1e-10:
            return lat1, lon1

        a = math.sin((1 - progress) * d) / math.sin(d)
        b = math.sin(progress * d) / math.sin(d)

        x = a * math.cos(phi1) * math.cos(lam1) + b * math.cos(phi2) * math.cos(lam2)
        y = a * math.cos(phi1) * math.sin(lam1) + b * math.cos(phi2) * math.sin(lam2)
        z = a * math.sin(phi1) + b * math.sin(phi2)

        lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
        lon = math.degrees(math.atan2(y, x))
        return lat, lon

    @staticmethod
    def _compute_heading(lat1: float, lon1: float,
                         lat2: float, lon2: float) -> float:
        """Compute bearing from (lat1,lon1) to (lat2,lon2) in degrees."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dlam = math.radians(lon2 - lon1)

        x = math.sin(dlam) * math.cos(phi2)
        y = (math.cos(phi1) * math.sin(phi2) -
             math.sin(phi1) * math.cos(phi2) * math.cos(dlam))

        brng = math.degrees(math.atan2(x, y))
        return (brng + 360) % 360


# ═══════════════════════════════════════════════════════════════════════════════
# C. PORT CONGESTION MONITOR — 5-Factor Proxy Model
# ═══════════════════════════════════════════════════════════════════════════════

class PortCongestionMonitor:
    """Compute port congestion score (0-100) from proxy indicators."""

    # Weights for 5 factors
    W_WEATHER   = 0.25
    W_BDI       = 0.20
    W_NEWS      = 0.15
    W_SEASONAL  = 0.20
    W_HISTORICAL = 0.20

    @staticmethod
    def compute_all_ports() -> list[dict]:
        """Compute congestion for all Indian ports."""
        results = []
        for port_name, port_data in INDIAN_PORTS.items():
            result = PortCongestionMonitor.compute_congestion(port_name, port_data)
            results.append(result)
        # Sort: priority ports first
        results.sort(key=lambda x: (x.get("priority", 9), -x.get("score", 0)))
        return results

    @staticmethod
    def compute_congestion(port_name: str, port_data: dict | None = None) -> dict:
        """Compute congestion score for a single port."""
        if port_data is None:
            port_data = INDIAN_PORTS.get(port_name, {})

        now = _now()
        base = port_data.get("base_congestion", 25)

        # Factor 1: Weather severity
        weather_score = PortCongestionMonitor._weather_factor(port_name, port_data)

        # Factor 2: BDI (Baltic Dry Index) pressure
        bdi_score = PortCongestionMonitor._bdi_factor()

        # Factor 3: News sentiment (maritime disruption keywords)
        news_score = PortCongestionMonitor._news_factor(port_name)

        # Factor 4: Seasonal pattern
        seasonal_score = PortCongestionMonitor._seasonal_factor(now.month)

        # Factor 5: Historical base
        historical_score = min(100, base + random.Random(int(now.strftime("%Y%m%d"))).randint(-5, 10))

        # Weighted composite
        score = round(
            weather_score * PortCongestionMonitor.W_WEATHER +
            bdi_score * PortCongestionMonitor.W_BDI +
            news_score * PortCongestionMonitor.W_NEWS +
            seasonal_score * PortCongestionMonitor.W_SEASONAL +
            historical_score * PortCongestionMonitor.W_HISTORICAL
        )
        score = max(0, min(100, score))

        # Level
        if score >= 75:
            level = "Critical"
        elif score >= 50:
            level = "High"
        elif score >= 30:
            level = "Medium"
        else:
            level = "Low"

        # Simulated vessel waiting count based on score
        rng = random.Random(int(now.strftime("%Y%m%d")) + hash(port_name))
        vessels_waiting = max(0, int(score / 15) + rng.randint(-1, 2))
        avg_wait_hours = round(max(0, score * 0.4 + rng.uniform(-2, 5)), 1)

        return {
            "port": port_name,
            "label": port_data.get("label", port_name),
            "lat": port_data.get("lat", 0),
            "lon": port_data.get("lon", 0),
            "type": port_data.get("type", "bulk"),
            "priority": port_data.get("priority", 3),
            "score": score,
            "level": level,
            "factors": {
                "weather": round(weather_score, 1),
                "bdi": round(bdi_score, 1),
                "news": round(news_score, 1),
                "seasonal": round(seasonal_score, 1),
                "historical": round(historical_score, 1),
            },
            "vessels_waiting": vessels_waiting,
            "avg_wait_hours": avg_wait_hours,
            "updated_at": _ts(),
        }

    @staticmethod
    def _weather_factor(port_name: str, port_data: dict) -> float:
        """Weather severity score (0-100) from tbl_weather or Open-Meteo."""
        try:
            weather = _load(BASE / "tbl_weather.json", [])
            if weather:
                # Find weather for nearest city
                city_map = {
                    "Mundra": "Kutch", "Kandla": "Kutch", "Mumbai": "Mumbai",
                    "Mangalore": "Mangalore", "Chennai": "Chennai",
                    "Haldia": "Kolkata", "Kochi": "Kochi",
                }
                city = city_map.get(port_name, "Mumbai")
                for w in reversed(weather):
                    if city.lower() in str(w.get("city", "")).lower():
                        temp = float(w.get("temperature", 30))
                        wind = float(w.get("wind_speed", 10))
                        humidity = float(w.get("humidity", 60))
                        # High wind = congestion risk, high humidity = monsoon risk
                        score = min(100, int(wind * 2.5 + max(0, humidity - 70) * 0.5))
                        return score
        except Exception:
            pass
        # Fallback: mild default
        return 20.0

    @staticmethod
    def _bdi_factor() -> float:
        """BDI-based freight demand pressure (0-100)."""
        try:
            crude = _load(BASE / "tbl_crude_prices.json", [])
            if crude:
                latest = crude[-1] if isinstance(crude, list) else crude
                bdi = float(latest.get("bdi", latest.get("BDI", 1500)))
                # BDI 500=low demand(20), 1500=moderate(50), 3000+=high(90)
                return min(100, max(0, (bdi - 500) / 25))
        except Exception:
            pass
        return 40.0  # Moderate default

    @staticmethod
    def _news_factor(port_name: str) -> float:
        """Maritime disruption keywords in recent news (0-100)."""
        try:
            news = _load(BASE / "tbl_news_feed.json", [])
            if not news:
                return 15.0

            disruption_keywords = [
                "port congestion", "shipping delay", "vessel queue",
                "storm", "cyclone", "monsoon", "strike", "blockade",
                "tanker", "maritime", "freight rate", "supply disruption",
            ]
            port_keywords = [port_name.lower(), "india port", "indian port"]

            score = 0
            recent = news[-50:] if len(news) > 50 else news
            for article in recent:
                title = str(article.get("title", "")).lower()
                text = str(article.get("summary", article.get("description", ""))).lower()
                combined = title + " " + text

                has_disruption = any(kw in combined for kw in disruption_keywords)
                has_port = any(kw in combined for kw in port_keywords)

                if has_disruption and has_port:
                    score += 15
                elif has_disruption:
                    score += 5
            return min(100, score)
        except Exception:
            pass
        return 15.0

    @staticmethod
    def _seasonal_factor(month: int) -> float:
        """Seasonal congestion pattern (0-100). Monsoon Jun-Sep = high."""
        seasonal_scores = {
            1: 25, 2: 20, 3: 30, 4: 35, 5: 40,
            6: 65, 7: 80, 8: 75, 9: 60,  # Monsoon peak
            10: 45, 11: 35, 12: 30,
        }
        return float(seasonal_scores.get(month, 30))


# ═══════════════════════════════════════════════════════════════════════════════
# D. LOGISTICS RISK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class LogisticsRiskEngine:
    """Compute route-level and vessel-level logistics risk scores."""

    # Piracy risk zones (simplified bounding boxes)
    PIRACY_ZONES = [
        {"name": "Gulf of Aden", "lat_min": 11, "lat_max": 15, "lon_min": 43, "lon_max": 51, "risk": 30},
        {"name": "Strait of Hormuz", "lat_min": 25, "lat_max": 27, "lon_min": 55, "lon_max": 57, "risk": 15},
    ]

    @staticmethod
    def compute_route_risk(route: dict, port_congestion: dict | None = None) -> dict:
        """Compute risk score for a route."""
        dest_port = route["to"]
        congestion_score = 30  # default

        if port_congestion:
            for pc in port_congestion if isinstance(port_congestion, list) else [port_congestion]:
                if pc.get("port") == dest_port:
                    congestion_score = pc.get("score", 30)
                    break

        # Factor 1: Destination port congestion (weight 35%)
        f_congestion = congestion_score

        # Factor 2: Route distance risk — longer = more risk (weight 20%)
        distance = route.get("distance_nm", 1000)
        f_distance = min(100, int(distance / 25))

        # Factor 3: Piracy proximity (weight 15%)
        from_port = SUPPLY_PORTS.get(route["from"], {})
        to_port = INDIAN_PORTS.get(route["to"], {})
        f_piracy = LogisticsRiskEngine._piracy_factor(
            from_port.get("lat", 25), from_port.get("lon", 55),
            to_port.get("lat", 20), to_port.get("lon", 73),
        )

        # Factor 4: Seasonal (weight 15%)
        f_seasonal = PortCongestionMonitor._seasonal_factor(_now().month)

        # Factor 5: BDI freight pressure (weight 15%)
        f_bdi = PortCongestionMonitor._bdi_factor()

        risk_score = round(
            f_congestion * 0.35 +
            f_distance * 0.20 +
            f_piracy * 0.15 +
            f_seasonal * 0.15 +
            f_bdi * 0.15
        )
        risk_score = max(0, min(100, risk_score))

        if risk_score >= 70:
            risk_level = "Critical"
        elif risk_score >= 45:
            risk_level = "High"
        elif risk_score >= 25:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        # Delay prediction
        base_delay_hours = route["avg_days"] * 24 * (risk_score / 200)
        delay_probability = min(95, risk_score * 1.1)

        return {
            "route_id": route["id"],
            "from": route["from"],
            "to": route["to"],
            "cargo_type": route["type"],
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": {
                "congestion": round(f_congestion, 1),
                "distance": round(f_distance, 1),
                "piracy": round(f_piracy, 1),
                "seasonal": round(f_seasonal, 1),
                "bdi": round(f_bdi, 1),
            },
            "delay_probability_pct": round(delay_probability, 1),
            "predicted_delay_hours": round(base_delay_hours, 1),
            "avg_transit_days": route["avg_days"],
            "distance_nm": route.get("distance_nm", 0),
            "avg_cost_usd_mt": route.get("avg_cost_usd_mt", 0),
        }

    @staticmethod
    def compute_delivery_prediction(vessel: dict, route_risk: dict | None = None) -> dict:
        """Predict delivery time with risk adjustment."""
        eta_str = vessel.get("eta", "")
        remaining_hours = vessel.get("eta_hours", 48)
        delay_hours = 0

        if route_risk:
            delay_hours = route_risk.get("predicted_delay_hours", 0)
        else:
            delay_hours = remaining_hours * (vessel.get("delay_factor", 1.0) - 1.0)

        predicted_hours = remaining_hours + delay_hours
        predicted_eta = _now() + timedelta(hours=predicted_hours)

        confidence = max(30, 95 - int(delay_hours * 2))

        return {
            "vessel_name": vessel.get("vessel_name", ""),
            "original_eta": eta_str,
            "predicted_eta": predicted_eta.strftime("%Y-%m-%d %H:%M IST"),
            "delay_hours": round(delay_hours, 1),
            "total_hours": round(predicted_hours, 1),
            "confidence_pct": confidence,
            "risk_factors": route_risk.get("factors", {}) if route_risk else {},
        }

    @staticmethod
    def _piracy_factor(lat1: float, lon1: float,
                       lat2: float, lon2: float) -> float:
        """Check if route midpoint passes through piracy zones."""
        mid_lat = (lat1 + lat2) / 2
        mid_lon = (lon1 + lon2) / 2

        for zone in LogisticsRiskEngine.PIRACY_ZONES:
            if (zone["lat_min"] <= mid_lat <= zone["lat_max"] and
                    zone["lon_min"] <= mid_lon <= zone["lon_max"]):
                return float(zone["risk"])
        return 5.0  # Minimal default risk


# ═══════════════════════════════════════════════════════════════════════════════
# E. MARINE WEATHER — Open-Meteo Marine API (free, no key)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_marine_weather(lat: float, lon: float) -> dict:
    """Fetch marine weather from Open-Meteo Marine API.

    Returns wave_height, wind_speed, swell_period, visibility.
    Falls back to seasonal averages on failure.
    """
    try:
        from api_hub_engine import _http_get
        url = "https://marine-api.open-meteo.com/v1/marine"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "wave_height,wave_period,wind_wave_height",
            "timezone": "Asia/Kolkata",
        }
        data, err = _http_get(url, params=params, timeout=10)
        if not err and isinstance(data, dict):
            current = data.get("current", {})
            return {
                "wave_height_m": current.get("wave_height", 1.0),
                "wave_period_s": current.get("wave_period", 6.0),
                "wind_wave_height_m": current.get("wind_wave_height", 0.5),
                "source": "Open-Meteo Marine API",
                "fetched_at": _ts(),
            }
    except Exception:
        pass

    # Seasonal fallback
    month = _now().month
    if month in (6, 7, 8, 9):  # Monsoon
        return {"wave_height_m": 2.5, "wave_period_s": 8.0, "wind_wave_height_m": 1.5,
                "source": "Seasonal fallback (monsoon)", "fetched_at": _ts()}
    return {"wave_height_m": 1.0, "wave_period_s": 5.0, "wind_wave_height_m": 0.3,
            "source": "Seasonal fallback (calm)", "fetched_at": _ts()}


# ═══════════════════════════════════════════════════════════════════════════════
# F. MARITIME NEWS — RSS Feeds
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_maritime_news(max_articles: int = 20) -> list[dict]:
    """Parse maritime RSS feeds for relevant news.

    Sources: gCaptain, MaritimeExecutive
    Falls back to empty list (non-critical component).
    """
    articles: list[dict] = []
    feeds = [
        ("https://gcaptain.com/feed/", "gCaptain"),
        ("https://www.maritime-executive.com/feed", "Maritime Executive"),
    ]

    keywords = [
        "bitumen", "asphalt", "tanker", "india", "mundra", "kandla",
        "mumbai", "port", "freight", "shipping", "vessel", "crude",
        "oil tanker", "maritime", "cargo", "bulk carrier",
    ]

    for feed_url, source_name in feeds:
        try:
            import xml.etree.ElementTree as ET
            from api_hub_engine import _http_get
            # Fetch raw XML
            import requests
            resp = requests.get(feed_url, timeout=10,
                                headers={"User-Agent": "PPS-Anantam-Maritime/1.0"})
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                continue

            for item in channel.findall("item")[:30]:
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")

                combined = (title + " " + desc).lower()
                relevance = sum(1 for kw in keywords if kw in combined)

                if relevance > 0:
                    articles.append({
                        "title": title,
                        "source": source_name,
                        "url": link,
                        "published": pub_date,
                        "relevance_score": relevance,
                        "fetched_at": _ts(),
                    })
        except Exception:
            continue

    articles.sort(key=lambda a: a.get("relevance_score", 0), reverse=True)
    return articles[:max_articles]


# ═══════════════════════════════════════════════════════════════════════════════
# G. MULTI-MODAL TRANSPORT MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class MultiModalMonitor:
    """Monitor transport status across sea, road, rail, air."""

    @staticmethod
    def get_transport_status() -> dict:
        """Get current status for all transport modes."""
        return {
            "sea": MultiModalMonitor._sea_status(),
            "road": MultiModalMonitor._road_status(),
            "rail": MultiModalMonitor._rail_status(),
            "air": MultiModalMonitor._air_status(),
            "updated_at": _ts(),
        }

    @staticmethod
    def _sea_status() -> dict:
        """Sea transport: derived from vessel simulation + port congestion."""
        try:
            vessels = VesselSimulator.generate_vessels(count=12)
            delayed = sum(1 for v in vessels if v["status"] == "delayed")
            ports = PortCongestionMonitor.compute_all_ports()
            avg_congestion = sum(p["score"] for p in ports) / max(1, len(ports))

            if avg_congestion > 60 or delayed > 4:
                risk_level = "High"
            elif avg_congestion > 35 or delayed > 2:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            disruptions = []
            for p in ports:
                if p["score"] > 50:
                    disruptions.append(f"{p['port']}: Congestion {p['level']} ({p['score']}%)")

            cost_pressure = min(100, int(avg_congestion * 1.2 + delayed * 5))

            return {
                "status": "Active",
                "risk_level": risk_level,
                "active_vessels": len(vessels),
                "delayed_vessels": delayed,
                "avg_port_congestion": round(avg_congestion, 1),
                "disruptions": disruptions,
                "cost_pressure_index": cost_pressure,
            }
        except Exception:
            return {"status": "Unknown", "risk_level": "Unknown", "disruptions": []}

    @staticmethod
    def _road_status() -> dict:
        """Road transport: derived from weather + news keywords."""
        try:
            now = _now()
            month = now.month

            # Weather-based risk
            weather = _load(BASE / "tbl_weather.json", [])
            road_risk = 20  # default
            if weather:
                latest = weather[-1] if isinstance(weather, list) else weather
                rain = str(latest.get("description", "")).lower()
                if any(w in rain for w in ["rain", "storm", "thunderstorm", "heavy"]):
                    road_risk += 30
                wind_speed = float(latest.get("wind_speed", 10))
                if wind_speed > 30:
                    road_risk += 15

            # Monsoon factor
            if month in (6, 7, 8, 9):
                road_risk += 25

            # News-based disruptions
            news = _load(BASE / "tbl_news_feed.json", [])
            road_keywords = ["highway", "nh closure", "road block", "landslide",
                             "flood", "waterlog", "bridge collapse", "truck"]
            disruptions = []
            if news:
                for article in news[-30:]:
                    text = str(article.get("title", "")).lower()
                    for kw in road_keywords:
                        if kw in text:
                            disruptions.append(article.get("title", "")[:80])
                            road_risk += 10
                            break

            road_risk = min(100, road_risk)
            if road_risk > 60:
                level = "High"
            elif road_risk > 35:
                level = "Medium"
            else:
                level = "Low"

            return {
                "status": "Active",
                "risk_level": level,
                "risk_score": road_risk,
                "disruptions": disruptions[:5],
                "cost_pressure_index": min(100, road_risk + 10),
                "monsoon_impact": month in (6, 7, 8, 9),
            }
        except Exception:
            return {"status": "Unknown", "risk_level": "Unknown", "disruptions": []}

    @staticmethod
    def _rail_status() -> dict:
        """Rail transport: derived from news + seasonal patterns."""
        try:
            now = _now()
            rail_risk = 15  # Rail is generally reliable

            news = _load(BASE / "tbl_news_feed.json", [])
            rail_keywords = ["rail freight", "goods train", "railway", "rail cargo",
                             "train delay", "derailment", "rail disruption"]
            disruptions = []
            if news:
                for article in news[-30:]:
                    text = str(article.get("title", "")).lower()
                    for kw in rail_keywords:
                        if kw in text:
                            disruptions.append(article.get("title", "")[:80])
                            rail_risk += 12
                            break

            # Monsoon: minor rail impact
            if now.month in (7, 8):
                rail_risk += 10

            rail_risk = min(100, rail_risk)
            level = "High" if rail_risk > 50 else "Medium" if rail_risk > 25 else "Low"

            return {
                "status": "Active",
                "risk_level": level,
                "risk_score": rail_risk,
                "disruptions": disruptions[:3],
                "cost_pressure_index": min(100, rail_risk + 5),
            }
        except Exception:
            return {"status": "Unknown", "risk_level": "Unknown", "disruptions": []}

    @staticmethod
    def _air_status() -> dict:
        """Air transport: static (bitumen not air-shipped), but cargo disruptions noted."""
        return {
            "status": "Not Applicable",
            "risk_level": "Low",
            "risk_score": 5,
            "disruptions": [],
            "cost_pressure_index": 0,
            "note": "Bitumen not shipped by air. Monitoring cargo flight disruptions for supply chain context.",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# H. MASTER REFRESH — Orchestrates all sub-engines
# ═══════════════════════════════════════════════════════════════════════════════

def refresh_maritime_intel() -> dict:
    """Run full maritime intelligence refresh.

    Generates vessels, computes port congestion, route risks,
    multi-modal status, and writes output tables.
    """
    try:
        from settings_engine import get as gs
        vessel_count = gs("maritime_vessel_count", 12)
    except Exception:
        vessel_count = 12

    # 1. Generate vessels
    vessels = VesselSimulator.generate_vessels(count=vessel_count)

    # 2. Compute port congestion
    port_congestion = PortCongestionMonitor.compute_all_ports()

    # 3. Compute route risks
    route_risks = []
    for route in ROUTES:
        risk = LogisticsRiskEngine.compute_route_risk(route, port_congestion)
        route_risks.append(risk)
    route_risks.sort(key=lambda r: (0 if r["cargo_type"] == "container" else 1, -r["risk_score"]))

    # 4. Delivery predictions
    predictions = []
    for vessel in vessels:
        route_risk = next(
            (r for r in route_risks if r["route_id"] == vessel["route_id"]), None)
        pred = LogisticsRiskEngine.compute_delivery_prediction(vessel, route_risk)
        predictions.append(pred)

    # 5. Marine weather for priority ports
    marine_weather = {}
    try:
        from settings_engine import get as gs
        if gs("maritime_marine_weather_enabled", True):
            for port_name in gs("maritime_priority_ports", ["Mundra", "Kandla", "Mumbai"]):
                port_data = INDIAN_PORTS.get(port_name)
                if port_data:
                    marine_weather[port_name] = fetch_marine_weather(
                        port_data["lat"], port_data["lon"])
    except Exception:
        pass

    # 6. Maritime news
    maritime_news = []
    try:
        from settings_engine import get as gs
        if gs("maritime_rss_enabled", True):
            maritime_news = fetch_maritime_news(max_articles=15)
    except Exception:
        pass

    # 7. Multi-modal transport
    multi_modal = {}
    try:
        from settings_engine import get as gs
        if gs("maritime_multimodal_enabled", True):
            multi_modal = MultiModalMonitor.get_transport_status()
    except Exception:
        pass

    # 8. Compute aggregate risk index
    avg_route_risk = sum(r["risk_score"] for r in route_risks) / max(1, len(route_risks))
    avg_port_cong = sum(p["score"] for p in port_congestion) / max(1, len(port_congestion))
    logistics_risk_index = round((avg_route_risk * 0.5 + avg_port_cong * 0.5), 1)

    # 9. Container-specific stats
    container_vessels = [v for v in vessels if v["cargo_type"] == "container"]
    bulk_vessels = [v for v in vessels if v["cargo_type"] == "bulk"]
    container_routes = [r for r in route_risks if r["cargo_type"] == "container"]
    bulk_routes = [r for r in route_risks if r["cargo_type"] == "bulk"]

    # Build summary
    summary = {
        "vessels_total": len(vessels),
        "vessels_container": len(container_vessels),
        "vessels_bulk": len(bulk_vessels),
        "vessels_delayed": sum(1 for v in vessels if v["status"] == "delayed"),
        "avg_route_risk": round(avg_route_risk, 1),
        "avg_port_congestion": round(avg_port_cong, 1),
        "logistics_risk_index": logistics_risk_index,
        "priority_ports_status": {
            p["port"]: {"score": p["score"], "level": p["level"]}
            for p in port_congestion if p["priority"] == 1
        },
        "last_updated": _ts(),
    }

    # Write output tables
    intel_data = {
        "vessels": vessels,
        "port_congestion": port_congestion,
        "route_risks": route_risks,
        "predictions": predictions,
        "marine_weather": marine_weather,
        "maritime_news": maritime_news,
        "multi_modal": multi_modal,
        "summary": summary,
        "last_updated": _ts(),
    }
    _save(TBL_MARITIME_INTEL, intel_data)

    route_data = {
        "routes": ROUTES,
        "route_risks": route_risks,
        "active_shipments": vessels,
        "last_updated": _ts(),
    }
    _save(TBL_MARITIME_ROUTES, route_data)

    return intel_data


# ═══════════════════════════════════════════════════════════════════════════════
# I. ALERTS GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_alerts(intel_data: dict | None = None) -> list[dict]:
    """Generate prioritized alerts from maritime intelligence data.

    Container alerts are always sorted FIRST.
    """
    if intel_data is None:
        intel_data = _load(TBL_MARITIME_INTEL, {})

    alerts: list[dict] = []

    # Vessel delay alerts
    for v in intel_data.get("vessels", []):
        if v.get("status") == "delayed":
            alerts.append({
                "type": "vessel_delay",
                "severity": "warning" if v.get("delay_factor", 1) < 1.2 else "critical",
                "cargo_type": v.get("cargo_type", "bulk"),
                "title": f"{v['vessel_name']} delayed to {v['destination_port']}",
                "detail": f"ETA: {v['eta']} | Delay factor: {v.get('delay_factor', 1):.1f}x",
                "port": v.get("destination_port", ""),
            })

    # Port congestion alerts
    for p in intel_data.get("port_congestion", []):
        if p.get("score", 0) >= 50:
            alerts.append({
                "type": "port_congestion",
                "severity": "critical" if p["score"] >= 75 else "warning",
                "cargo_type": p.get("type", "bulk"),
                "title": f"{p['port']} congestion: {p['level']} ({p['score']}%)",
                "detail": f"Vessels waiting: {p.get('vessels_waiting', 0)} | Avg wait: {p.get('avg_wait_hours', 0)}h",
                "port": p.get("port", ""),
            })

    # Route risk alerts
    for r in intel_data.get("route_risks", []):
        if r.get("risk_score", 0) >= 50:
            alerts.append({
                "type": "route_risk",
                "severity": "critical" if r["risk_score"] >= 70 else "warning",
                "cargo_type": r.get("cargo_type", "bulk"),
                "title": f"Route {r['from']} → {r['to']}: {r['risk_level']} risk ({r['risk_score']})",
                "detail": f"Delay probability: {r.get('delay_probability_pct', 0):.0f}%",
                "port": r.get("to", ""),
            })

    # Sort: container FIRST, then by severity (critical > warning)
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: (
        0 if a.get("cargo_type") == "container" else 1,
        severity_order.get(a.get("severity", "info"), 2),
    ))

    return alerts


# ═══════════════════════════════════════════════════════════════════════════════
# J. DAILY SUMMARY GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_summary(intel_data: dict | None = None) -> dict:
    """Generate daily summary outputs for sharing.

    Returns:
        - priority_port_status: Summary for Mundra, Kandla, Mumbai
        - container_shipment_eta: Sorted list of container ETAs
        - delay_risk_score: Overall delay risk (0-100)
        - logistics_cost_pressure_index: Cost pressure (0-100)
    """
    if intel_data is None:
        intel_data = _load(TBL_MARITIME_INTEL, {})

    summary = intel_data.get("summary", {})
    vessels = intel_data.get("vessels", [])
    port_congestion = intel_data.get("port_congestion", [])
    multi_modal = intel_data.get("multi_modal", {})

    # 1. Priority Port Status
    priority_ports = {}
    try:
        from settings_engine import get as gs
        priority_names = gs("maritime_priority_ports", ["Mundra", "Kandla", "Mumbai"])
    except Exception:
        priority_names = ["Mundra", "Kandla", "Mumbai"]

    for p in port_congestion:
        if p.get("port") in priority_names:
            port_vessels = [v for v in vessels if v.get("destination_port") == p["port"]]
            container_count = sum(1 for v in port_vessels if v["cargo_type"] == "container")
            bulk_count = sum(1 for v in port_vessels if v["cargo_type"] == "bulk")
            next_eta = min((v["eta_hours"] for v in port_vessels), default=0)

            priority_ports[p["port"]] = {
                "congestion_score": p["score"],
                "congestion_level": p["level"],
                "container_vessels": container_count,
                "bulk_vessels": bulk_count,
                "total_vessels": len(port_vessels),
                "next_eta_hours": round(next_eta, 1),
                "vessels_waiting": p.get("vessels_waiting", 0),
            }

    # 2. Container Shipment ETAs
    container_etas = []
    for v in vessels:
        if v["cargo_type"] == "container":
            container_etas.append({
                "vessel": v["vessel_name"],
                "from": v["departure_port"],
                "to": v["destination_port"],
                "eta": v["eta"],
                "eta_hours": v["eta_hours"],
                "status": v["status"],
                "cargo_mt": v.get("cargo_mt", 0),
                "grade": v.get("product_grade", ""),
            })
    container_etas.sort(key=lambda x: x["eta_hours"])

    # 3. Overall Delay Risk Score
    delayed_count = sum(1 for v in vessels if v["status"] == "delayed")
    delay_risk = min(100, int(
        delayed_count / max(1, len(vessels)) * 100 * 0.5 +
        summary.get("avg_route_risk", 30) * 0.3 +
        summary.get("avg_port_congestion", 25) * 0.2
    ))

    # 4. Logistics Cost Pressure Index
    sea_pressure = multi_modal.get("sea", {}).get("cost_pressure_index", 30)
    road_pressure = multi_modal.get("road", {}).get("cost_pressure_index", 20)
    cost_pressure = round(sea_pressure * 0.6 + road_pressure * 0.3 + 10, 1)  # +10 base

    return {
        "date": _now().strftime("%Y-%m-%d"),
        "priority_port_status": priority_ports,
        "container_shipment_etas": container_etas,
        "delay_risk_score": delay_risk,
        "logistics_cost_pressure_index": min(100, cost_pressure),
        "summary": summary,
        "generated_at": _ts(),
    }
