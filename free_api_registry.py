"""
free_api_registry.py -- Free API Catalog & Health Check
=========================================================
Registry of all free APIs used by the dashboard with health validation,
rate-limit tracking, and discovery helpers.

Usage:
    from free_api_registry import FREE_API_CATALOG, validate_api_health, get_healthy_apis
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

LOG = logging.getLogger("free_api_registry")
IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
REGISTRY_FILE = BASE / "api_registry_status.json"


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


# ==============================================================================
# FREE API CATALOG
# ==============================================================================

FREE_API_CATALOG: Dict[str, dict] = {
    # ── Existing Connectors (14) ─────────────────────────────────────────────
    "eia_crude": {
        "name": "Crude Oil Prices (yfinance)",
        "category": "commodity",
        "url": "https://finance.yahoo.com",
        "auth": "none",
        "rate_limit": "2000/day",
        "data": "Brent, WTI daily OHLCV",
        "ttl_min": 15,
        "connector": "connect_eia",
    },
    "fx_fawazahmed": {
        "name": "FX Rates (fawazahmed0)",
        "category": "currency",
        "url": "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "USD/INR daily rate",
        "ttl_min": 60,
        "connector": "connect_fx",
    },
    "news_gnews": {
        "name": "GNews RSS",
        "category": "news",
        "url": "https://news.google.com/rss",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "Commodity & energy news",
        "ttl_min": 10,
        "connector": "connect_news",
    },
    "weather_openmeteo": {
        "name": "Open-Meteo Weather",
        "category": "weather",
        "url": "https://api.open-meteo.com",
        "auth": "none",
        "rate_limit": "10000/day",
        "data": "5 Indian cities weather",
        "ttl_min": 60,
        "connector": "connect_weather",
    },
    "un_comtrade": {
        "name": "UN Comtrade",
        "category": "trade",
        "url": "https://comtradeapi.un.org",
        "auth": "none",
        "rate_limit": "100/hour",
        "data": "India bitumen imports HS 27132000",
        "ttl_min": 1440,
        "connector": "connect_comtrade",
    },
    "world_bank": {
        "name": "World Bank India",
        "category": "macro",
        "url": "https://api.worldbank.org/v2",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "India GDP, trade balance",
        "ttl_min": 10080,
        "connector": "connect_world_bank",
    },
    "ports_volume": {
        "name": "Port Volumes",
        "category": "logistics",
        "url": "estimated",
        "auth": "none",
        "rate_limit": "N/A",
        "data": "Indian port throughput estimates",
        "ttl_min": 120,
        "connector": "connect_ports",
    },
    "refinery_production": {
        "name": "Refinery Production",
        "category": "supply",
        "url": "estimated",
        "auth": "none",
        "rate_limit": "N/A",
        "data": "Indian refinery output",
        "ttl_min": 120,
        "connector": "connect_refinery",
    },
    "maritime_intel": {
        "name": "Maritime Intelligence",
        "category": "logistics",
        "url": "RSS feeds",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "Vessel tracking, port congestion",
        "ttl_min": 15,
        "connector": "connect_maritime",
    },
    "bdi_index": {
        "name": "Baltic Dry Index (yfinance)",
        "category": "logistics",
        "url": "https://finance.yahoo.com",
        "auth": "none",
        "rate_limit": "2000/day",
        "data": "BDI daily values",
        "ttl_min": 15,
        "connector": "connect_bdi",
    },
    "gold_price": {
        "name": "Gold Price (yfinance)",
        "category": "commodity",
        "url": "https://finance.yahoo.com",
        "auth": "none",
        "rate_limit": "2000/day",
        "data": "Gold USD/oz daily",
        "ttl_min": 15,
        "connector": "connect_gold",
    },

    # ── NEW Connectors (8) ───────────────────────────────────────────────────
    "rbi_fx": {
        "name": "RBI Reference Rate",
        "category": "currency",
        "url": "https://www.rbi.org.in/scripts/ReferenceRateArchive.aspx",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "RBI official USD/INR reference rate",
        "ttl_min": 360,
        "connector": "connect_rbi_fx",
    },
    "opec_monthly": {
        "name": "OPEC Monthly Report RSS",
        "category": "commodity",
        "url": "https://www.opec.org/opec_web/en/publications/338.htm",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "OPEC basket price, production data",
        "ttl_min": 1440,
        "connector": "connect_opec_monthly",
    },
    "eia_steo": {
        "name": "EIA Short-Term Outlook",
        "category": "commodity",
        "url": "https://api.eia.gov/v2",
        "auth": "free_key",
        "rate_limit": "unlimited",
        "data": "Energy price forecasts, production outlook",
        "ttl_min": 10080,
        "connector": "connect_eia_steo",
    },
    "dgft_imports": {
        "name": "DGFT India Trade (data.gov.in)",
        "category": "trade",
        "url": "https://api.data.gov.in/resource",
        "auth": "free_key",
        "rate_limit": "10000/day",
        "data": "India import/export trade statistics",
        "ttl_min": 1440,
        "connector": "connect_dgft_imports",
    },
    "nhai_tenders": {
        "name": "NHAI Tender Portal",
        "category": "infrastructure",
        "url": "https://nhai.gov.in",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "Highway construction tenders",
        "ttl_min": 1440,
        "connector": "connect_nhai_tenders",
    },
    "cement_index": {
        "name": "Cement Price Index",
        "category": "demand_proxy",
        "url": "public_sources",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "Cement prices as construction demand proxy",
        "ttl_min": 1440,
        "connector": "connect_cement_index",
    },
    "iocl_circular": {
        "name": "IOCL Bitumen Circular",
        "category": "pricing",
        "url": "https://iocl.com",
        "auth": "none",
        "rate_limit": "unlimited",
        "data": "IOCL bitumen price circulars",
        "ttl_min": 360,
        "connector": "connect_iocl_circular",
    },
    "fred_macro": {
        "name": "FRED Economic Data",
        "category": "macro",
        "url": "https://api.stlouisfed.org/fred",
        "auth": "free_key",
        "rate_limit": "unlimited",
        "data": "USD index, interest rates, CPI",
        "ttl_min": 1440,
        "connector": "connect_fred_data",
    },
}


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

def validate_api_health(connector_id: str) -> dict:
    """Test a single API connector and report health status."""
    entry = FREE_API_CATALOG.get(connector_id)
    if not entry:
        return {"connector_id": connector_id, "status": "unknown", "error": "Not in catalog"}

    start = time.time()
    try:
        from api_hub_engine import HubCache
        cached = HubCache.get(connector_id)
        elapsed = time.time() - start

        if cached:
            return {
                "connector_id": connector_id,
                "name": entry["name"],
                "status": "healthy",
                "cached": True,
                "response_ms": round(elapsed * 1000),
                "checked_at": _now_ist(),
            }
        else:
            return {
                "connector_id": connector_id,
                "name": entry["name"],
                "status": "no_cache",
                "cached": False,
                "response_ms": round(elapsed * 1000),
                "checked_at": _now_ist(),
            }
    except Exception as e:
        return {
            "connector_id": connector_id,
            "name": entry.get("name", connector_id),
            "status": "error",
            "error": str(e)[:100],
            "checked_at": _now_ist(),
        }


def validate_all_apis() -> dict:
    """Health check all registered APIs."""
    results = []
    healthy = 0
    for cid in FREE_API_CATALOG:
        r = validate_api_health(cid)
        results.append(r)
        if r.get("status") == "healthy":
            healthy += 1

    return {
        "total": len(results),
        "healthy": healthy,
        "unhealthy": len(results) - healthy,
        "health_pct": round(healthy / max(len(results), 1) * 100, 1),
        "details": results,
        "checked_at": _now_ist(),
    }


def get_healthy_apis() -> List[str]:
    """Return list of connector IDs with healthy cache."""
    healthy = []
    for cid in FREE_API_CATALOG:
        r = validate_api_health(cid)
        if r.get("status") == "healthy":
            healthy.append(cid)
    return healthy


def get_apis_by_category(category: str) -> List[dict]:
    """Return all APIs in a specific category."""
    return [
        {"id": cid, **entry}
        for cid, entry in FREE_API_CATALOG.items()
        if entry.get("category") == category
    ]


def get_categories() -> List[str]:
    """Return all unique API categories."""
    return sorted(set(e.get("category", "other") for e in FREE_API_CATALOG.values()))
