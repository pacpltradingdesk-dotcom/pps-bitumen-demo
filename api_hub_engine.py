"""
PPS Anantam Agentic AI Eco System
API HUB Engine v1.0 — Central Data Integration Layer
=====================================================
Auto-updating normalized data tables from external APIs.
All connectors modular. Keys stored only in hub_catalog.json.
No hardcoded credentials. Full retry + cache + validation.

Normalized Tables (7):
  tbl_crude_prices    — Brent, WTI, OPEC prices in USD/bbl
  tbl_fx_rates        — USD/INR, EUR/INR, GBP/INR exchange rates
  tbl_trade_imports   — UN Comtrade bitumen import flows (India HS 271320)
  tbl_ports_volume    — Port-level bitumen cargo volume estimates
  tbl_refinery_production — Refinery production data
  tbl_weather         — Multi-city weather (Mumbai, Kandla, Mangalore, Delhi, Vadodara)
  tbl_news_feed       — Oil/bitumen headlines with sentiment

All times: IST  DD-MM-YYYY HH:MM:SS IST
India format: ₹, DD-MM-YYYY
"""

import json
import time
import threading
import datetime
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytz
import requests

# ─── IST helpers ──────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")


def _now() -> datetime.datetime:
    return datetime.datetime.now(IST)


def _ts() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S IST")

# alias used by dashboard modules
_ist_now = _ts


def _date_str() -> str:
    return _now().strftime("%Y-%m-%d")


# ─── Paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent

CATALOG_FILE = BASE / "hub_catalog.json"
HUB_LOG_FILE = BASE / "hub_activity_log.json"

# Normalized table files
TBL_CRUDE      = BASE / "tbl_crude_prices.json"
TBL_FX         = BASE / "tbl_fx_rates.json"
TBL_TRADE      = BASE / "tbl_trade_imports.json"
TBL_PORTS      = BASE / "tbl_ports_volume.json"
TBL_REFINERY   = BASE / "tbl_refinery_production.json"
TBL_WEATHER    = BASE / "tbl_weather.json"
TBL_NEWS       = BASE / "tbl_news_feed.json"
TBL_WORLD_BANK = BASE / "tbl_world_bank.json"
TBL_MARITIME   = BASE / "tbl_maritime_intel.json"

# ── Contact import tables ──────────────────────────────────────────────────────
TBL_CONTACTS    = BASE / "tbl_contacts.json"
TBL_IMPORT_HIST = BASE / "tbl_import_history.json"

# ── Directory tables ───────────────────────────────────────────────────────────
TBL_DIR_ORGS    = BASE / "tbl_dir_orgs.json"
TBL_DIR_SOURCES = BASE / "tbl_dir_sources.json"
TBL_DIR_CHANGES = BASE / "tbl_dir_changes.json"
TBL_DIR_FETCHES = BASE / "tbl_dir_fetch_logs.json"
TBL_DIR_BUGS    = BASE / "tbl_dir_bugs.json"
TBL_DIR_GEO     = BASE / "tbl_dir_geo.json"

# Cache file (keyed by connector_id)
HUB_CACHE_FILE = BASE / "hub_cache.json"

_lock = threading.RLock()

# ─── HTTP session with default headers ────────────────────────────────────────
_session = requests.Session()
_session.headers.update({"User-Agent": "PPS-Anantam-APIHub/1.0"})

# ─────────────────────────────────────────────────────────────────────────────
# SMART API SCHEDULING — TTL per connector (minutes)
# Business-critical (crude/FX) refresh more often than background data
# ─────────────────────────────────────────────────────────────────────────────
CONNECTOR_SCHEDULE: Dict[str, int] = {
    "eia_crude": 15,         # critical — crude prices
    "fx": 60,                # critical — FX rates
    "news": 10,              # important — news
    "maritime_intel": 15,    # important — vessel tracking
    "weather": 60,           # moderate
    "ports": 120,            # moderate
    "refinery": 120,         # moderate
    "un_comtrade": 1440,     # daily — trade data
    "world_bank_india": 10080,  # weekly — macro data
    "data_gov_in": 1440,     # daily — govt data
    "gem_portal": 1440,      # daily — tenders
    "morth_data": 10080,     # weekly — road data
    "nhai_projects": 10080,  # weekly — NHAI
    "ppac_data": 10080,      # weekly — petroleum
    # ── NEW connectors (Step 9) ──────────────────────────────────────
    "rbi_fx": 360,           # 6h — RBI reference rate
    "opec_monthly": 1440,    # daily — OPEC basket & report
    "eia_steo": 10080,       # weekly — EIA short-term outlook
    "dgft_imports": 1440,    # daily — India trade stats
    "nhai_tenders": 1440,    # daily — highway tenders
    "cement_index": 1440,    # daily — construction demand proxy
    "iocl_circular": 360,    # 6h — IOCL bitumen pricing
    "fred_macro": 1440,      # daily — USD index, rates
}


def _should_refresh(connector_id: str) -> bool:
    """Check if connector's cache has expired based on its schedule TTL."""
    ttl_minutes = CONNECTOR_SCHEDULE.get(connector_id, 60)
    cached = HubCache.get(connector_id)
    if cached is None:
        return True
    ts = cached.get("timestamp") or cached.get("fetched_at", "")
    if not ts:
        return True
    try:
        from datetime import datetime as _dt
        fetched = _dt.fromisoformat(str(ts)[:19])
        age_minutes = (_dt.now() - fetched).total_seconds() / 60
        return age_minutes >= ttl_minutes
    except Exception:
        return True


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT API CATALOG
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CATALOG: Dict[str, dict] = {
    "eia_crude": {
        "api_name":           "EIA Crude & Petroleum Prices",
        "category":           "Crude",
        "provider":           "US Energy Information Administration",
        "base_url":           "https://api.eia.gov/v2/",
        "endpoints":          ["petroleum/pri/spt/data/"],
        "auth_type":          "API Key",
        "key_value":          "",
        "status":             "Disabled",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "API key not configured — register free at eia.gov",
        "fallback_api":       "yfinance_brent",
        "data_output_tables": ["tbl_crude_prices"],
        "notes":              "Free API key from eia.gov. Provides WTI, Brent, heating oil, gasoline.",
    },
    "un_comtrade": {
        "api_name":           "UN Comtrade Trade Data",
        "category":           "Trade",
        "provider":           "United Nations Statistics Division",
        "base_url":           "https://comtradeapi.un.org/",
        "endpoints":          ["public/v1/preview/C/A/HS"],
        "auth_type":          "API Key",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "static_trade_cache",
        "data_output_tables": ["tbl_trade_imports"],
        "notes":              "Public preview endpoint — no key for basic queries. Full access requires subscription.",
    },
    "openweather": {
        "api_name":           "OpenWeatherMap Current Weather",
        "category":           "Weather",
        "provider":           "OpenWeather Ltd",
        "base_url":           "https://api.openweathermap.org/data/2.5/",
        "endpoints":          ["weather"],
        "auth_type":          "API Key",
        "key_value":          "",
        "status":             "Disabled",
        "refresh_frequency":  "1h",
        "cache_ttl_sec":      3600,
        "last_success_time":  None,
        "last_error_message": "API key not configured — register free at openweathermap.org",
        "fallback_api":       "open_meteo_hub",
        "data_output_tables": ["tbl_weather"],
        "notes":              "Free tier: 1000 calls/day. Register at openweathermap.org/api",
    },
    "newsapi": {
        "api_name":           "NewsAPI Global Headlines",
        "category":           "News",
        "provider":           "NewsAPI.org",
        "base_url":           "https://newsapi.org/v2/",
        "endpoints":          ["everything"],
        "auth_type":          "API Key",
        "key_value":          "",
        "status":             "Disabled",
        "refresh_frequency":  "1h",
        "cache_ttl_sec":      3600,
        "last_success_time":  None,
        "last_error_message": "API key not configured — register free at newsapi.org",
        "fallback_api":       "gnews_rss",
        "data_output_tables": ["tbl_news_feed"],
        "notes":              "Free tier: 100 requests/day. Register at newsapi.org",
    },
    "frankfurter_fx": {
        "api_name":           "Frankfurter FX Rates (ECB)",
        "category":           "FX",
        "provider":           "Frankfurter.app (European Central Bank data)",
        "base_url":           "https://api.frankfurter.app/",
        "endpoints":          ["latest"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1h",
        "cache_ttl_sec":      3600,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "fawazahmed0_fx",
        "data_output_tables": ["tbl_fx_rates"],
        "notes":              "No key required. ECB exchange rates via Frankfurter proxy.",
    },
    "open_meteo_hub": {
        "api_name":           "Open-Meteo Weather (No-key fallback)",
        "category":           "Weather",
        "provider":           "Open-Meteo.com",
        "base_url":           "https://api.open-meteo.com/v1/",
        "endpoints":          ["forecast"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1h",
        "cache_ttl_sec":      3600,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "",
        "data_output_tables": ["tbl_weather"],
        "notes":              "No key required. Primary fallback for weather. Covers all 5 port cities.",
    },
    "gnews_rss": {
        "api_name":           "Google News RSS (Bitumen/Crude headlines)",
        "category":           "News",
        "provider":           "Google News RSS",
        "base_url":           "https://news.google.com/rss/",
        "endpoints":          ["search"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1h",
        "cache_ttl_sec":      3600,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "",
        "data_output_tables": ["tbl_news_feed"],
        "notes":              "No key required. Google News RSS for crude oil/bitumen/India energy news.",
    },
    "fawazahmed0_fx": {
        "api_name":           "fawazahmed0 Currency API (CDN)",
        "category":           "FX",
        "provider":           "fawazahmed0 GitHub CDN",
        "base_url":           "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/",
        "endpoints":          ["usd.json"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "",
        "data_output_tables": ["tbl_fx_rates"],
        "notes":              "No key required. Fallback FX. Daily update from CDN.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# JSON HELPERS
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# GOVERNMENT DATA CATALOG (Phase 1 + Phase 2)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CATALOG_GOVT: Dict[str, dict] = {
    "comtrade_hs271320": {
        "api_name":           "UN Comtrade — HS 271320 Country-wise Imports",
        "category":           "Trade / Govt",
        "provider":           "United Nations Statistics Division",
        "base_url":           "https://comtradeapi.un.org/",
        "endpoints":          ["public/v1/preview/C/A/HS"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "static_trade_cache",
        "data_output_tables": ["tbl_imports_countrywise"],
        "notes":              "Public preview — no key. India HS 271320 imports by partner country.",
    },
    "rbi_fx_historical": {
        "api_name":           "RBI Reference Rate — USD/INR Historical (ECB proxy)",
        "category":           "FX / Govt",
        "provider":           "Frankfurter.app (ECB data) — RBI proxy",
        "base_url":           "https://api.frankfurter.app/",
        "endpoints":          ["{start_date}.."],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "fawazahmed0_fx",
        "data_output_tables": ["tbl_fx_rates"],
        "notes":              "12-month USD/INR history via ECB/Frankfurter. Labelled as RBI proxy.",
    },
    "ppac_proxy": {
        "api_name":           "PPAC Refinery Production (Static Ref + EIA Proxy)",
        "category":           "Refinery / Govt",
        "provider":           "PPAC (static) + EIA (live proxy)",
        "base_url":           "https://ppac.gov.in/",
        "endpoints":          ["data-statistics"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "",
        "data_output_tables": ["tbl_refinery_production"],
        "notes":              "PPAC has no public API. Uses Annual Report 2023-24 as static ref.",
    },
    "data_gov_in_highways": {
        "api_name":           "data.gov.in — NHAI Road Construction Progress",
        "category":           "Infrastructure / Govt",
        "provider":           "data.gov.in (Govt of India)",
        "base_url":           "https://api.data.gov.in/resource/",
        "endpoints":          ["3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"],
        "auth_type":          "API Key",
        "key_value":          "",
        "status":             "Disabled",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "API key not configured — register free at data.gov.in",
        "fallback_api":       "static_highway_ref",
        "data_output_tables": ["tbl_highway_km"],
        "notes":              "Free key: https://data.gov.in/user/register | NHAI road progress data.",
    },
    "fred_macro": {
        "api_name":           "FRED — USD/INR + Brent Crude History",
        "category":           "Macro / Govt",
        "provider":           "Federal Reserve Bank of St. Louis",
        "base_url":           "https://api.stlouisfed.org/fred/",
        "endpoints":          ["series/observations"],
        "auth_type":          "API Key",
        "key_value":          "",
        "status":             "Disabled",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "API key not configured — register free at fred.stlouisfed.org",
        "fallback_api":       "frankfurter_fx",
        "data_output_tables": ["tbl_demand_proxy"],
        "notes":              "Free key: https://fred.stlouisfed.org/docs/api/api_key.html | Series: DEXINUS, DCOILBRENTEU",
    },
    "world_bank_india": {
        "api_name":           "World Bank — India Economic Indicators",
        "category":           "Macro / Govt",
        "provider":           "World Bank Group",
        "base_url":           "https://api.worldbank.org/v2/",
        "endpoints":          ["country/IND/indicator/"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "1d",
        "cache_ttl_sec":      86400,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "",
        "data_output_tables": ["tbl_world_bank"],
        "notes":              "No key required. India CPI inflation, GDP growth rate.",
    },
    "maritime_intel": {
        "api_name":           "Maritime Intelligence — Vessel Tracking & Port Activity",
        "category":           "Maritime / Logistics",
        "provider":           "Open-Meteo Marine + RSS + Simulation",
        "base_url":           "https://marine-api.open-meteo.com/v1/marine",
        "endpoints":          ["marine"],
        "auth_type":          "None",
        "key_value":          "",
        "status":             "Live",
        "refresh_frequency":  "15m",
        "cache_ttl_sec":      900,
        "last_success_time":  None,
        "last_error_message": "",
        "fallback_api":       "",
        "data_output_tables": ["tbl_maritime_intel"],
        "notes":              "Free APIs + deterministic simulation. Vessel tracking, port congestion, route risk.",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _load(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _save(path: Path, data: Any) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _append_tbl(
    path: Path,
    records: List[dict],
    max_records: int = 500,
    source_type: str = "",
    source_confidence: float = -1,
    source_provider: str = "",
) -> None:
    """Append records to a normalized table JSON list, with dedup + validation + trim.
    Optionally injects _source_type, _source_confidence, _source_provider metadata."""
    with _lock:
        existing = _load(path, [])
        if not isinstance(existing, list):
            existing = []
        for rec in records:
            # Inject source confidence metadata (Phase D)
            if source_type:
                rec["_source_type"] = source_type
            if source_confidence >= 0:
                rec["_source_confidence"] = source_confidence
            if source_provider:
                rec["_source_provider"] = source_provider
            # Dedup key priority:
            #   1. url (news articles)
            #   2. benchmark / from_currency / city (market/fx/weather)
            #   3. headline (fallback for news without url)
            # Without this, news records with empty benchmark field all dedupe
            # against each other within the same minute → only 1 per minute saved.
            ts_prefix = str(rec.get("date_time", ""))[:16]
            dedup_key = (
                rec.get("url")
                or rec.get("benchmark")
                or rec.get("from_currency")
                or rec.get("city")
                or rec.get("headline", "")[:80]
            )
            def _key_of(e):
                return (
                    e.get("url")
                    or e.get("benchmark")
                    or e.get("from_currency")
                    or e.get("city")
                    or e.get("headline", "")[:80]
                )
            # If dedup_key is a URL/headline, match by that key alone (any time).
            # Otherwise fall back to same-minute + same-bm dedupe for time-series data.
            if rec.get("url") or rec.get("headline"):
                is_dup = any(_key_of(e) == dedup_key for e in existing[-200:])
            else:
                is_dup = any(
                    str(e.get("date_time", ""))[:16] == ts_prefix
                    and _key_of(e) == dedup_key
                    for e in existing[-50:]
                )
            if not is_dup:
                existing.append(rec)
        if len(existing) > max_records:
            existing = existing[-max_records:]
        _save(path, existing)


def _hub_log(connector_id: str, status: str, message: str, records_written: int = 0) -> None:
    record = {
        "timestamp_ist": _ts(),
        "connector_id":  connector_id,
        "status":        status,
        "message":       message,
        "records_written": records_written,
    }
    existing = _load(HUB_LOG_FILE, [])
    if not isinstance(existing, list):
        existing = []
    existing.append(record)
    if len(existing) > 1000:
        existing = existing[-1000:]
    _save(HUB_LOG_FILE, existing)


# ─────────────────────────────────────────────────────────────────────────────
# HUB CATALOG — CRUD
# ─────────────────────────────────────────────────────────────────────────────

class HubCatalog:
    """Manage the API catalog stored in hub_catalog.json."""

    @staticmethod
    def load() -> Dict[str, dict]:
        stored = _load(CATALOG_FILE, {})
        # Merge both default catalogs for any missing connectors
        merged = dict(DEFAULT_CATALOG)
        merged.update(DEFAULT_CATALOG_GOVT)
        merged.update(stored)
        return merged

    @staticmethod
    def save(catalog: Dict[str, dict]) -> None:
        _save(CATALOG_FILE, catalog)

    @staticmethod
    def get(connector_id: str) -> Optional[dict]:
        return HubCatalog.load().get(connector_id)

    @staticmethod
    def update_field(connector_id: str, field: str, value: Any) -> None:
        cat = HubCatalog.load()
        if connector_id in cat:
            cat[connector_id][field] = value
            HubCatalog.save(cat)

    @staticmethod
    def set_status(connector_id: str, status: str,
                   error_msg: str = "", success: bool = False) -> None:
        cat = HubCatalog.load()
        if connector_id in cat:
            cat[connector_id]["status"] = status
            if error_msg:
                cat[connector_id]["last_error_message"] = error_msg
            if success:
                cat[connector_id]["last_success_time"] = _ts()
                cat[connector_id]["last_error_message"] = ""
            HubCatalog.save(cat)

    @staticmethod
    def get_key(connector_id: str) -> str:
        entry = HubCatalog.get(connector_id)
        return (entry or {}).get("key_value", "").strip()

    @staticmethod
    def is_enabled(connector_id: str) -> bool:
        entry = HubCatalog.get(connector_id)
        return (entry or {}).get("status", "Disabled") != "Disabled"


# ─────────────────────────────────────────────────────────────────────────────
# CACHE MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class HubCache:
    @staticmethod
    def get(connector_id: str) -> Optional[Any]:
        cat   = HubCatalog.get(connector_id) or {}
        ttl   = cat.get("cache_ttl_sec", 3600)
        cache = _load(HUB_CACHE_FILE, {})
        entry = cache.get(connector_id)
        if not entry:
            return None
        if time.time() - entry.get("ts", 0) < ttl:
            return entry.get("data")
        return None

    @staticmethod
    def set(connector_id: str, data: Any) -> None:
        with _lock:
            cache = _load(HUB_CACHE_FILE, {})
            cache[connector_id] = {"ts": time.time(), "data": data}
            _save(HUB_CACHE_FILE, cache)

    @staticmethod
    def invalidate(connector_id: str) -> None:
        with _lock:
            cache = _load(HUB_CACHE_FILE, {})
            cache.pop(connector_id, None)
            _save(HUB_CACHE_FILE, cache)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP FETCH HELPER WITH RETRY + TIMEOUT + RATE-LIMIT HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def _http_get(url: str, params: dict = None, headers: dict = None,
              timeout: int = 10, max_retries: int = 3) -> Tuple[Optional[Any], Optional[str]]:
    """
    GET with retry + 429 backoff.
    Returns (parsed_json_or_text, error_message).
    """
    backoffs = [2, 8, 20]
    for attempt in range(max_retries):
        try:
            resp = _session.get(url, params=params, headers=headers or {}, timeout=timeout)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", backoffs[attempt]))
                time.sleep(min(wait, 30))
                continue
            if resp.status_code != 200:
                return None, f"HTTP {resp.status_code}"
            ct = resp.headers.get("Content-Type", "")
            if "xml" in ct or url.endswith(".xml") or "rss" in url.lower():
                return resp.text, None
            try:
                return resp.json(), None
            except Exception:
                return resp.text, None
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(backoffs[attempt])
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(backoffs[attempt])
            else:
                return None, f"Connection error: {str(e)[:80]}"
        except Exception as e:
            return None, str(e)[:120]
    return None, "All retries exhausted"


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR A — EIA CRUDE PRICES
# ─────────────────────────────────────────────────────────────────────────────

def connect_eia() -> dict:
    """
    Fetch crude oil spot prices from EIA API.
    Requires free API key configured in hub_catalog.json under 'eia_crude'.
    Fallback: yfinance (via existing api_manager).
    Populates: tbl_crude_prices
    """
    connector_id = "eia_crude"
    key = HubCatalog.get_key(connector_id)
    records_written = 0

    if key:
        # ── Try EIA primary ──────────────────────────────────────────────────
        url = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
        params = {
            "api_key":              key,
            "frequency":            "daily",
            "data[0]":              "value",
            "facets[series][]":     "RBRTE",   # Brent
            "sort[0][column]":      "period",
            "sort[0][direction]":   "desc",
            "length":               "7",
        }
        data, err = _http_get(url, params=params)
        if data and isinstance(data, dict) and "response" in data:
            rows = data["response"].get("data", [])
            records = []
            for row in rows:
                price_val = float(row.get("value", 0))
                if 40 <= price_val <= 150:  # Validate range
                    records.append({
                        "date_time":  row.get("period", _date_str()),
                        "benchmark":  "Brent",
                        "price":      price_val,
                        "currency":   "USD/bbl",
                        "source":     "EIA",
                    })
            # Also fetch WTI
            params["facets[series][]"] = "RCLC1"
            data2, _ = _http_get(url, params=params)
            if data2 and isinstance(data2, dict):
                for row in data2["response"].get("data", []):
                    price_val = float(row.get("value", 0))
                    if 40 <= price_val <= 150:  # Validate range
                        records.append({
                            "date_time": row.get("period", _date_str()),
                            "benchmark": "WTI",
                            "price":     price_val,
                            "currency":  "USD/bbl",
                            "source":    "EIA",
                        })
            if records:
                _append_tbl(TBL_CRUDE, records, max_records=500,
                            source_type="live_api", source_confidence=0.95,
                            source_provider="US Energy Information Administration")
                records_written = len(records)
                HubCatalog.set_status(connector_id, "Live", success=True)
                _hub_log(connector_id, "OK", f"EIA: {records_written} crude price records", records_written)
                HubCache.set(connector_id, records)
                return {"ok": True, "records": records_written, "source": "EIA"}
        err = err or "No data in EIA response"
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(err))
        _hub_log(connector_id, "FAIL", f"EIA primary failed: {err}")

    # ── Fallback: yfinance via existing api_manager ───────────────────────────
    try:
        from api_manager import fetch_yfinance_with_history
        # Fetch Brent and WTI as SEPARATE calls to avoid data contamination
        brent_val, brent_7d = fetch_yfinance_with_history("BZ=F")
        wti_val,   wti_7d   = fetch_yfinance_with_history("CL=F")
        records = []
        ts = _ts()

        # ── Price validation: reject values outside ₹ 40-₹ 150 range ──
        def _valid_crude(price, benchmark):
            if price is None:
                return False
            if price < 40 or price > 150:
                _hub_log(connector_id, "WARN",
                         f"Price validation REJECTED: {benchmark} ${price}/bbl (outside ₹ 40-₹ 150 range)")
                return False
            return True

        brent_ok = _valid_crude(brent_val, "Brent")
        wti_ok = _valid_crude(wti_val, "WTI")

        # ── Guard: Brent and WTI must NOT be equal (they differ by ₹ 3-₹ 8 typically) ──
        if brent_ok and wti_ok and abs(brent_val - wti_val) < 0.01:
            _hub_log(connector_id, "WARN",
                     f"WTI=Brent anomaly detected: Brent=${brent_val} WTI=${wti_val} — skipping save")
            brent_ok = False
            wti_ok = False

        if brent_ok:
            records.append({"date_time": ts, "benchmark": "Brent",
                            "price": round(brent_val, 2), "currency": "USD/bbl",
                            "source": "yfinance (EIA fallback)"})
        if wti_ok:
            records.append({"date_time": ts, "benchmark": "WTI",
                            "price": round(wti_val, 2), "currency": "USD/bbl",
                            "source": "yfinance (EIA fallback)"})
        if records:
            _append_tbl(TBL_CRUDE, records, max_records=500,
                        source_type="live_api", source_confidence=0.90,
                        source_provider="Yahoo Finance (yfinance library)")
            records_written = len(records)
            if not key:
                HubCatalog.set_status(connector_id, "Disabled",
                                      error_msg="API key not configured — using yfinance fallback")
            _hub_log(connector_id, "Fallback", f"yfinance fallback: {records_written} records", records_written)
            HubCache.set(connector_id, records)
            return {"ok": True, "records": records_written, "source": "yfinance fallback"}
    except Exception as e:
        pass

    _hub_log(connector_id, "FAIL", "EIA and fallback both failed")
    return {"ok": False, "records": 0, "source": "none", "error": "All sources failed"}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR B — UN COMTRADE TRADE IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

def connect_comtrade() -> dict:
    """
    Fetch India bitumen (HS 271320) import data from UN Comtrade.
    Uses public preview endpoint — no key required for basic queries.
    Full subscription endpoint used if key is configured.
    Populates: tbl_trade_imports
    """
    connector_id = "un_comtrade"
    key          = HubCatalog.get_key(connector_id)
    records_written = 0

    # Check cache first
    cached = HubCache.get(connector_id)
    if cached:
        return {"ok": True, "records": 0, "source": "cache", "cached": True}

    # ── Try public preview endpoint (v1 → v2 fallback) ─────────────────────────
    _yr = str(_now().year - 1)
    urls_to_try = []
    if key:
        urls_to_try.append((
            "https://comtradeapi.un.org/data/v1/get/C/A/HS",
            {"typeCode": "C", "freqCode": "A", "clCode": "HS",
             "period": _yr, "reporterCode": "356", "cmdCode": "271320",
             "flowCode": "M", "partnerCode": "0", "subscription-key": key},
        ))
    urls_to_try.append((
        "https://comtradeapi.un.org/public/v1/preview/C/A/HS",
        {"typeCode": "C", "freqCode": "A", "clCode": "HS",
         "period": _yr, "reporterCode": "356", "cmdCode": "271320",
         "flowCode": "M", "partnerCode": "0"},
    ))
    # v2 bulk endpoint as last resort
    urls_to_try.append((
        f"https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=356&cmdCode=271320&flowCode=M&period={_yr}",
        {},
    ))

    data = None
    err = None
    for url, params in urls_to_try:
        data, err = _http_get(url, params=params if params else None, timeout=15)
        if data and isinstance(data, dict) and data.get("data"):
            break
        data = None  # reset for next attempt

    data, err = _http_get(url, params=params, timeout=15)
    if data and isinstance(data, dict):
        rows = data.get("data", [])
        if rows:
            records = []
            for row in rows:
                records.append({
                    "date":     str(row.get("period", _now().year - 1)),
                    "country":  row.get("reporterDesc", "India"),
                    "product":  "Bitumen of Petroleum",
                    "hs_code":  "271320",
                    "quantity": float(row.get("netWgt", 0) or 0),
                    "unit":     "kg",
                    "value":    float(row.get("primaryValue", 0) or 0),
                    "currency": "USD",
                    "source":   "UN Comtrade",
                })
            _append_tbl(TBL_TRADE, records, max_records=500,
                        source_type="live_api", source_confidence=0.98,
                        source_provider="United Nations Statistics Division")
            records_written = len(records)
            HubCatalog.set_status(connector_id, "Live", success=True)
            HubCache.set(connector_id, records)
            _hub_log(connector_id, "OK", f"Comtrade: {records_written} import records", records_written)
            return {"ok": True, "records": records_written, "source": "UN Comtrade"}

    # ── Fallback: use static reference data ────────────────────────────────────
    err_msg = err or "Empty Comtrade response"
    HubCatalog.set_status(connector_id, "Static", error_msg=f"API unavailable — using cached reference. {str(err_msg)[:80]}")

    # Write a cached reference row so dashboard is not blank
    static_record = {
        "date":     str(_now().year - 1),
        "country":  "India",
        "product":  "Bitumen of Petroleum",
        "hs_code":  "271320",
        "quantity": 3500000000.0,
        "unit":     "kg",
        "value":    1400000000.0,
        "currency": "USD",
        "source":   "UN Comtrade (cached reference — API unavailable)",
    }
    existing = _load(TBL_TRADE, [])
    if not existing:
        _append_tbl(TBL_TRADE, [static_record], max_records=500,
                    source_type="cached_reference", source_confidence=0.45,
                    source_provider="UN Comtrade (fallback reference)")
        records_written = 1
    _hub_log(connector_id, "Fallback", f"Comtrade unavailable: {err_msg}. Static cache used.")
    return {"ok": False, "records": records_written, "error": str(err_msg)}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR C — WEATHER (OpenWeather + Open-Meteo fallback)
# ─────────────────────────────────────────────────────────────────────────────

_CITIES = [
    {"name": "Mumbai",     "lat": 19.0760, "lon": 72.8777, "q": "Mumbai,IN"},
    {"name": "Kandla",     "lat": 23.0333, "lon": 70.2167, "q": "Gandhidham,IN"},
    {"name": "Mangalore",  "lat": 12.8698, "lon": 74.8427, "q": "Mangalore,IN"},
    {"name": "Delhi",      "lat": 28.7041, "lon": 77.1025, "q": "New Delhi,IN"},
    {"name": "Vadodara",   "lat": 22.3072, "lon": 73.1812, "q": "Vadodara,IN"},
]


def connect_weather() -> dict:
    """
    Fetch weather for 5 port cities.
    Primary: OpenWeather (if key set).
    Fallback: Open-Meteo (no key required).
    Populates: tbl_weather
    """
    ow_key = HubCatalog.get_key("openweather")
    records = []

    for city in _CITIES:
        rec = None

        # Try OpenWeather if key is set
        if ow_key:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city["q"], "appid": ow_key, "units": "metric"}
            data, err = _http_get(url, params=params)
            if data and isinstance(data, dict) and "main" in data:
                rec = {
                    "date_time": _ts(),
                    "location":  city["name"],
                    "temp":      float(data["main"].get("temp", 0)),
                    "rain_mm":   float((data.get("rain") or {}).get("1h", 0)),
                    "humidity":  int(data["main"].get("humidity", 0)),
                    "source":    "OpenWeather",
                }

        # Fallback to Open-Meteo
        if rec is None:
            url    = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude":        city["lat"],
                "longitude":       city["lon"],
                "current_weather": "true",
                "daily":           "temperature_2m_max,precipitation_sum,relative_humidity_2m_max",
                "timezone":        "Asia/Kolkata",
                "forecast_days":   "1",
            }
            data, err = _http_get(url, params=params, timeout=12)
            if data and isinstance(data, dict):
                cw    = data.get("current_weather", {})
                daily = data.get("daily", {})
                rain  = (daily.get("precipitation_sum") or [0])[0] or 0
                hum   = (daily.get("relative_humidity_2m_max") or [0])[0] or 0
                rec   = {
                    "date_time": _ts(),
                    "location":  city["name"],
                    "temp":      float(cw.get("temperature", 0)),
                    "rain_mm":   float(rain),
                    "humidity":  int(hum),
                    "source":    "Open-Meteo (OpenWeather fallback)",
                }

        if rec:
            records.append(rec)

    if records:
        _src_prov = "OpenWeather Ltd" if ow_key else "Open-Meteo.com"
        _src_conf = 0.92 if ow_key else 0.88
        _append_tbl(TBL_WEATHER, records, max_records=1000,
                    source_type="live_api", source_confidence=_src_conf,
                    source_provider=_src_prov)
        HubCatalog.set_status("open_meteo_hub", "Live", success=True)
        if ow_key:
            HubCatalog.set_status("openweather", "Live", success=True)
        _hub_log("openweather", "OK", f"Weather: {len(records)} city records", len(records))
        HubCache.set("openweather", records)
        return {"ok": True, "records": len(records), "source": "weather"}
    else:
        _hub_log("openweather", "FAIL", "All weather sources failed for all cities")
        return {"ok": False, "records": 0, "error": "All weather sources failed"}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR D — NEWS FEED (NewsAPI + Google News RSS fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_rss(rss_text: str, source: str) -> List[dict]:
    """Parse RSS/Atom XML into tbl_news_feed records."""
    records = []
    try:
        root = ET.fromstring(rss_text)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}
        # Handle RSS 2.0 and Atom
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)
        for item in items[:20]:
            title   = (item.findtext("title") or item.findtext("atom:title", "", ns) or "").strip()
            link    = (item.findtext("link")  or item.findtext("atom:link", "", ns) or "").strip()
            pub     = (item.findtext("source") or item.findtext("atom:source", "", ns) or source).strip()
            if isinstance(pub, str) and len(pub) > 40:
                pub = pub[:40]
            if title:
                records.append({
                    "date_time":       _ts(),
                    "headline":        title[:200],
                    "publisher":       pub,
                    "url":             link[:300],
                    "sentiment_score": None,
                    "source":          source,
                })
    except Exception:
        pass
    return records


def connect_news() -> dict:
    """
    Fetch oil/bitumen/India headlines.
    Primary: NewsAPI (if key set).
    Fallback: Google News RSS (no key, always available).
    Populates: tbl_news_feed
    """
    connector_id = "newsapi"
    key          = HubCatalog.get_key(connector_id)
    records      = []

    # ── Try NewsAPI ────────────────────────────────────────────────────────────
    if key:
        url    = "https://newsapi.org/v2/everything"
        params = {
            "q":        "bitumen OR crude oil OR petroleum OR OPEC",
            "apiKey":   key,
            "pageSize": "20",
            "sortBy":   "publishedAt",
            "language": "en",
        }
        data, err = _http_get(url, params=params, timeout=10)
        if data and isinstance(data, dict) and data.get("status") == "ok":
            for art in data.get("articles", []):
                records.append({
                    "date_time":       _ts(),
                    "headline":        (art.get("title") or "")[:200],
                    "publisher":       (art.get("source") or {}).get("name", "NewsAPI")[:50],
                    "url":             (art.get("url") or "")[:300],
                    "sentiment_score": None,
                    "source":          "NewsAPI",
                })
            if records:
                _append_tbl(TBL_NEWS, records, max_records=500,
                            source_type="live_api", source_confidence=0.85,
                            source_provider="NewsAPI.org")
                HubCatalog.set_status(connector_id, "Live", success=True)
                _hub_log(connector_id, "OK", f"NewsAPI: {len(records)} articles", len(records))
                HubCache.set(connector_id, records)
                return {"ok": True, "records": len(records), "source": "NewsAPI"}

    # ── Fallback: Google News RSS ──────────────────────────────────────────────
    queries = [
        "bitumen+crude+oil+India",
        "OPEC+oil+price",
    ]
    for q in queries:
        url  = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        text, err = _http_get(url, timeout=10, max_retries=2)
        if text and isinstance(text, str) and "<rss" in text.lower():
            recs = _parse_rss(text, "Google News RSS")
            records.extend(recs)

    if records:
        # Deduplicate by headline
        seen = set()
        uniq = []
        for r in records:
            h = r["headline"][:80]
            if h not in seen:
                seen.add(h)
                uniq.append(r)
        records = uniq[:30]
        _append_tbl(TBL_NEWS, records, max_records=500,
                    source_type="live_feed", source_confidence=0.80,
                    source_provider="Google News RSS")
        HubCatalog.set_status("gnews_rss", "Live", success=True)
        if not key:
            HubCatalog.set_status(connector_id, "Disabled",
                                  error_msg="API key not configured — using Google News RSS fallback")
        _hub_log(connector_id, "Fallback", f"Google News RSS: {len(records)} articles", len(records))
        HubCache.set(connector_id, records)
        return {"ok": True, "records": len(records), "source": "Google News RSS"}

    _hub_log(connector_id, "FAIL", "NewsAPI and Google RSS both failed")
    return {"ok": False, "records": 0, "error": "All news sources failed"}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR E — FX RATES (Frankfurter primary, fawazahmed0 fallback)
# ─────────────────────────────────────────────────────────────────────────────

def connect_fx() -> dict:
    """
    Fetch USD/INR, EUR/INR, GBP/INR exchange rates.
    Primary: Frankfurter (ECB data, no key).
    Fallback: fawazahmed0 CDN.
    Populates: tbl_fx_rates
    """
    connector_id = "frankfurter_fx"
    records = []

    # Check cache
    cached = HubCache.get(connector_id)
    if cached:
        return {"ok": True, "records": 0, "source": "cache", "cached": True}

    # ── Frankfurter ───────────────────────────────────────────────────────────
    url = "https://api.frankfurter.app/latest"
    params = {"from": "USD", "to": "INR,EUR,GBP,JPY,AED,SAR"}
    data, err = _http_get(url, params=params, timeout=8)
    if data and isinstance(data, dict) and "rates" in data:
        ts = _ts()
        for pair, rate in data["rates"].items():
            records.append({
                "date_time": ts,
                "pair":      f"USD/{pair}",
                "rate":      float(rate),
                "source":    "Frankfurter (ECB)",
            })
        if records:
            _append_tbl(TBL_FX, records, max_records=500,
                        source_type="live_api", source_confidence=0.96,
                        source_provider="Frankfurter.app (ECB data)")
            HubCatalog.set_status(connector_id, "Live", success=True)
            HubCache.set(connector_id, records)
            _hub_log(connector_id, "OK", f"Frankfurter: {len(records)} FX pairs", len(records))
            return {"ok": True, "records": len(records), "source": "Frankfurter"}

    # ── Fallback: fawazahmed0 ─────────────────────────────────────────────────
    url2 = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
    data2, err2 = _http_get(url2, timeout=8)
    if data2 and isinstance(data2, dict) and "usd" in data2:
        rates = data2["usd"]
        ts    = _ts()
        for pair_key in ["inr", "eur", "gbp", "jpy", "aed", "sar"]:
            rate = rates.get(pair_key)
            if rate:
                records.append({
                    "date_time": ts,
                    "pair":      f"USD/{pair_key.upper()}",
                    "rate":      float(rate),
                    "source":    "fawazahmed0 CDN (Frankfurter fallback)",
                })
        if records:
            _append_tbl(TBL_FX, records, max_records=500,
                        source_type="live_api", source_confidence=0.85,
                        source_provider="fawazahmed0 CDN")
            HubCatalog.set_status("fawazahmed0_fx", "Live", success=True)
            HubCatalog.set_status(connector_id, "Failing",
                                  error_msg=f"Frankfurter failed: {err}. Using CDN fallback.")
            HubCache.set(connector_id, records)
            _hub_log(connector_id, "Fallback", f"fawazahmed0: {len(records)} FX pairs", len(records))
            return {"ok": True, "records": len(records), "source": "fawazahmed0 fallback"}

    HubCatalog.set_status(connector_id, "Failing",
                          error_msg=f"Both FX sources failed: {err} | {err2}")
    _hub_log(connector_id, "FAIL", "All FX sources failed")
    return {"ok": False, "records": 0, "error": "All FX sources failed"}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR F — PORTS VOLUME (derived from shipping freight + static estimates)
# ─────────────────────────────────────────────────────────────────────────────

def connect_ports() -> dict:
    """
    Port volume data — no free real-time API exists for Indian port bitumen cargo.
    Uses shipping freight API signal (BDI) + estimated port capacities.
    Marks source accurately as 'Estimated'.
    Populates: tbl_ports_volume
    """
    connector_id = "ports_volume"
    # Get BDI trend from existing system
    bdi_factor = 1.0
    try:
        from api_manager import fetch_yfinance_with_history
        bdi_val, bdi_7d = fetch_yfinance_with_history("BDIY")
        if bdi_val and bdi_7d and bdi_7d > 0:
            bdi_factor = bdi_val / bdi_7d  # trend indicator
    except Exception:
        pass

    PORT_ESTIMATES = [
        {"port_name": "Kandla (KPCT)",   "base_mt": 35000},
        {"port_name": "Mumbai (JNPT)",    "base_mt": 18000},
        {"port_name": "Mangalore (NMPT)", "base_mt": 12000},
        {"port_name": "Chennai (CCTPL)",  "base_mt": 8000},
        {"port_name": "Paradip (PPT)",    "base_mt": 6000},
    ]
    records = []
    ts = _ts()
    for port in PORT_ESTIMATES:
        records.append({
            "date":      _date_str(),
            "port_name": port["port_name"],
            "commodity": "Bitumen (VG-30/VG-10)",
            "quantity":  round(port["base_mt"] * bdi_factor),
            "unit":      "MT (estimated)",
            "source":    "BDI-adjusted estimate (no free auto-API for Indian port cargo)",
        })

    _append_tbl(TBL_PORTS, records, max_records=500,
                source_type="estimated", source_confidence=0.65,
                source_provider="Baltic Dry Index (freight signal)")
    _hub_log(connector_id, "OK",
             f"Ports volume: {len(records)} port estimates (BDI factor={bdi_factor:.2f})", len(records))
    return {"ok": True, "records": len(records), "source": "BDI-adjusted estimate"}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR G — REFINERY PRODUCTION (EIA / static reference)
# ─────────────────────────────────────────────────────────────────────────────

def connect_refinery() -> dict:
    """
    Refinery production data.
    Primary: EIA if key configured (world refinery data).
    Fallback: Static reference (IEA/PPAC published figures).
    Populates: tbl_refinery_production
    """
    connector_id = "eia_crude"  # Uses same EIA key
    key = HubCatalog.get_key(connector_id)
    records = []

    if key:
        # EIA refinery yields
        url = "https://api.eia.gov/v2/petroleum/pnp/wiup/data/"
        params = {
            "api_key":            key,
            "frequency":          "monthly",
            "data[0]":            "value",
            "facets[series][]":   "MRIPUPUS1",
            "sort[0][column]":    "period",
            "sort[0][direction]": "desc",
            "length":             "12",
        }
        data, err = _http_get(url, params=params, timeout=12)
        if data and isinstance(data, dict) and "response" in data:
            for row in data["response"].get("data", []):
                records.append({
                    "date":                 row.get("period", ""),
                    "refinery_or_region":   "USA (EIA Refinery Inputs)",
                    "product":              "Petroleum Products",
                    "quantity":             float(row.get("value", 0)),
                    "unit":                 "Thousand Barrels",
                    "source":               "EIA",
                })

    # Always write India static reference (official PPAC data — no auto-API)
    year = _now().year
    india_refs = [
        {"year": str(year - 1), "region": "India (IOC Panipat)", "product": "Bitumen VG-30/VG-10", "qty": 1200000, "unit": "MT"},
        {"year": str(year - 1), "region": "India (BPCL Mumbai)", "product": "Bitumen VG-30",        "qty": 850000,  "unit": "MT"},
        {"year": str(year - 1), "region": "India (HPCL Vizag)",  "product": "Bitumen VG-30",        "qty": 680000,  "unit": "MT"},
        {"year": str(year - 1), "region": "India (Total)",        "product": "Bitumen (all grades)", "qty": 4200000, "unit": "MT"},
    ]
    for ref in india_refs:
        records.append({
            "date":               ref["year"],
            "refinery_or_region": ref["region"],
            "product":            ref["product"],
            "quantity":           ref["qty"],
            "unit":               ref["unit"],
            "source":             "PPAC reference (no free API — official published data)",
        })

    existing = _load(TBL_REFINERY, [])
    if not existing or len(existing) < 4:
        _src_type = "live_api" if key else "cached_reference"
        _src_conf = 0.93 if key else 0.70
        _src_prov = "US Energy Information Administration" if key else "PPAC (Petroleum Planning & Analysis Cell)"
        _append_tbl(TBL_REFINERY, records, max_records=200,
                    source_type=_src_type, source_confidence=_src_conf,
                    source_provider=_src_prov)
    _hub_log("refinery", "OK", f"Refinery: {len(records)} records (static+EIA)", len(records))
    return {"ok": True, "records": len(records), "source": "PPAC+EIA"}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR H — WORLD BANK (India CPI / GDP — no key required)
# ─────────────────────────────────────────────────────────────────────────────

def connect_world_bank() -> dict:
    """
    World Bank API — India economic indicators.
    Fetches CPI inflation (FP.CPI.TOTL.ZG) and GDP growth (NY.GDP.MKTP.KD.ZG).
    No API key required. Output: tbl_world_bank.json
    """
    connector_id = "world_bank_india"
    records: dict = {}

    indicators = {
        "cpi":        "FP.CPI.TOTL.ZG",
        "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    }

    for label, indicator in indicators.items():
        url = f"https://api.worldbank.org/v2/country/IND/indicator/{indicator}"
        params = {"format": "json", "per_page": "5", "date": "2020:2026"}
        data, err = _http_get(url, params=params, timeout=15)
        if err:
            _hub_log(connector_id, "WARN", f"World Bank {label}: {err}")
            continue
        if isinstance(data, list) and len(data) > 1:
            for entry in data[1]:
                if entry.get("value") is not None:
                    records[label] = float(entry["value"])
                    records[f"{label}_year"] = entry.get("date", "")
                    break  # Latest non-null value

    if records:
        records["source"] = "World Bank API"
        records["fetched_at"] = _ts()
        _save(TBL_WORLD_BANK, records)
        HubCatalog.set_status(connector_id, "Live", success=True)
        _hub_log(connector_id, "OK", f"World Bank: {len(records)} indicators", len(records))
        return {"ok": True, "records": len(records), "source": "World Bank API"}

    # Static fallback
    fallback = {
        "gdp_growth": 6.8, "gdp_growth_year": "2024",
        "cpi": 5.2, "cpi_year": "2024",
        "source": "Static reference (World Bank API unavailable)",
        "fetched_at": _ts(),
    }
    _save(TBL_WORLD_BANK, fallback)
    _hub_log(connector_id, "FALLBACK", "Using static reference", 2)
    return {"ok": True, "records": 2, "source": "Static fallback"}


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTOR I — MARITIME INTELLIGENCE (Simulation + Open-Meteo Marine + RSS)
# ─────────────────────────────────────────────────────────────────────────────

def connect_maritime() -> dict:
    """
    Maritime Intelligence — vessel tracking, port congestion, route risk.
    Uses deterministic simulation + Open-Meteo Marine API + Maritime RSS.
    No API key required. Output: tbl_maritime_intel.json, tbl_maritime_routes.json
    """
    connector_id = "maritime_intel"
    try:
        from maritime_intelligence_engine import refresh_maritime_intel
        result = refresh_maritime_intel()
        summary = result.get("summary", {})
        vessel_count = summary.get("vessels_total", 0)
        port_count = len(result.get("port_congestion", []))
        total_records = vessel_count + port_count

        HubCatalog.set_status(connector_id, "Live", success=True)
        _hub_log(connector_id, "OK",
                 f"Maritime: {vessel_count} vessels, {port_count} ports", total_records)
        return {"ok": True, "records": total_records,
                "source": "Maritime Intelligence Engine"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Error", error_msg=str(e)[:200])
        _hub_log(connector_id, "FAIL", f"Maritime connector error: {e}")
        return {"ok": False, "records": 0, "error": str(e)[:100]}


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZED TABLE READER
# ─────────────────────────────────────────────────────────────────────────────

class NormalizedTables:
    """Read access to all normalized tables (7 original + 6 govt extension)."""

    @staticmethod
    def crude_prices(n: int = 100) -> List[dict]:
        data = _load(TBL_CRUDE, [])
        return data[-n:]

    @staticmethod
    def fx_rates(n: int = 100) -> List[dict]:
        data = _load(TBL_FX, [])
        return data[-n:]

    @staticmethod
    def trade_imports(n: int = 100) -> List[dict]:
        data = _load(TBL_TRADE, [])
        return data[-n:]

    @staticmethod
    def ports_volume(n: int = 100) -> List[dict]:
        data = _load(TBL_PORTS, [])
        return data[-n:]

    @staticmethod
    def refinery_production(n: int = 100) -> List[dict]:
        data = _load(TBL_REFINERY, [])
        return data[-n:]

    @staticmethod
    def weather(n: int = 200) -> List[dict]:
        data = _load(TBL_WEATHER, [])
        return data[-n:]

    @staticmethod
    def news_feed(n: int = 50) -> List[dict]:
        data = _load(TBL_NEWS, [])
        return data[-n:]

    @staticmethod
    def hub_log(n: int = 200) -> List[dict]:
        data = _load(HUB_LOG_FILE, [])
        return list(reversed(data[-n:]))

    @staticmethod
    def world_bank() -> dict:
        """World Bank India economic indicators (CPI, GDP)."""
        return _load(TBL_WORLD_BANK, {})

    @staticmethod
    def maritime_intel() -> dict:
        """Maritime vessel tracking, port congestion, route risk."""
        return _load(TBL_MARITIME, {})

    # ── Govt extension tables ─────────────────────────────────────────────
    @staticmethod
    def highway_km(n: int = 200) -> List[dict]:
        return _load(BASE / "tbl_highway_km.json", [])[-n:]

    @staticmethod
    def demand_proxy(n: int = 200) -> List[dict]:
        return _load(BASE / "tbl_demand_proxy.json", [])[-n:]

    @staticmethod
    def imports_countrywise(n: int = 500) -> List[dict]:
        return _load(BASE / "tbl_imports_countrywise.json", [])[-n:]

    @staticmethod
    def imports_portwise(n: int = 500) -> List[dict]:
        return _load(BASE / "tbl_imports_portwise.json", [])[-n:]

    @staticmethod
    def corr_results(n: int = 100) -> List[dict]:
        return _load(BASE / "tbl_corr_results.json", [])[-n:]

    @staticmethod
    def insights(n: int = 100) -> List[dict]:
        return _load(BASE / "tbl_insights.json", [])[-n:]

    @staticmethod
    def api_runs(n: int = 200) -> List[dict]:
        data = _load(BASE / "tbl_api_runs.json", [])
        return list(reversed(data[-n:]))

    # ── Directory tables ──────────────────────────────────────────────────────
    @staticmethod
    def dir_orgs(n: int = 500) -> List[dict]:
        return _load(BASE / "tbl_dir_orgs.json", [])[-n:]

    @staticmethod
    def dir_sources(n: int = 200) -> List[dict]:
        return _load(BASE / "tbl_dir_sources.json", [])[-n:]

    # ── Contact import tables ─────────────────────────────────────────────────
    @staticmethod
    def get_contacts() -> List[dict]:
        return _load(TBL_CONTACTS, [])

    @staticmethod
    def save_contacts(records: list) -> None:
        _save(TBL_CONTACTS, records)

    @staticmethod
    def get_import_history() -> List[dict]:
        return _load(TBL_IMPORT_HIST, [])

    @staticmethod
    def save_import_history(records: list) -> None:
        _save(TBL_IMPORT_HIST, records)

    @staticmethod
    def summary() -> dict:
        def _cnt(name): return len(_load(BASE / name, []))
        return {
            "tbl_crude_prices":          _cnt("tbl_crude_prices.json"),
            "tbl_fx_rates":              _cnt("tbl_fx_rates.json"),
            "tbl_trade_imports":         _cnt("tbl_trade_imports.json"),
            "tbl_ports_volume":          _cnt("tbl_ports_volume.json"),
            "tbl_refinery_production":   _cnt("tbl_refinery_production.json"),
            "tbl_weather":               _cnt("tbl_weather.json"),
            "tbl_news_feed":             _cnt("tbl_news_feed.json"),
            "tbl_highway_km":            _cnt("tbl_highway_km.json"),
            "tbl_demand_proxy":          _cnt("tbl_demand_proxy.json"),
            "tbl_imports_countrywise":   _cnt("tbl_imports_countrywise.json"),
            "tbl_imports_portwise":      _cnt("tbl_imports_portwise.json"),
            "tbl_corr_results":          _cnt("tbl_corr_results.json"),
            "tbl_insights":              _cnt("tbl_insights.json"),
            "tbl_api_runs":              _cnt("tbl_api_runs.json"),
            "tbl_maritime_intel":        len(_load(TBL_MARITIME, {}).get("vessels", [])) if isinstance(_load(TBL_MARITIME, {}), dict) else 0,
            "last_updated":              _ts(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# HUB HEALTH MONITOR — TEST ALL APIs
# ─────────────────────────────────────────────────────────────────────────────

class HubHealthMonitor:
    """Test connectivity + write status to catalog."""

    @staticmethod
    def test_one(connector_id: str) -> dict:
        """Quick connectivity test — does NOT write to normalized tables."""
        entry = HubCatalog.get(connector_id)
        if not entry:
            return {"connector_id": connector_id, "ok": False, "error": "Not found in catalog"}

        base_url = entry.get("base_url", "")
        key      = entry.get("key_value", "").strip()
        auth     = entry.get("auth_type", "None")

        if entry.get("status") == "Disabled" and not key:
            return {
                "connector_id": connector_id,
                "ok":           False,
                "status":       "Disabled",
                "error":        entry.get("last_error_message", "API key not configured"),
            }

        # Ping base URL. Some APIs return non-200 on root path (need query params) —
        # treat HTTP 400/404 on base URL as "reachable" (host responds = connectivity OK).
        start   = time.time()
        ok_ping = False
        err_msg = ""
        try:
            resp    = _session.get(base_url, timeout=6)
            latency = round((time.time() - start) * 1000)
            # 200/301/302/400/404 all mean the host is reachable
            ok_ping = resp.status_code < 500
            if not ok_ping:
                err_msg = f"HTTP {resp.status_code}"
        except Exception as e:
            latency = round((time.time() - start) * 1000)
            err_msg = str(e)[:80]

        if ok_ping:
            HubCatalog.set_status(connector_id, "Live", success=True)
            return {"connector_id": connector_id, "ok": True,
                    "latency_ms": latency, "status": "Live"}
        else:
            HubCatalog.set_status(connector_id, "Failing", error_msg=err_msg)
            return {"connector_id": connector_id, "ok": False,
                    "latency_ms": latency, "status": "Failing", "error": err_msg}

    @staticmethod
    def test_all() -> List[dict]:
        """Test all connectors. Returns list of results."""
        cat = HubCatalog.load()
        results = []
        for connector_id in cat:
            result = HubHealthMonitor.test_one(connector_id)
            results.append(result)
            time.sleep(0.3)  # polite spacing
        return results


# ─────────────────────────────────────────────────────────────────────────────
# FULL REFRESH — run all connectors
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# ADDITIONAL CONNECTORS — BDI (Baltic Dry Index) & Gold
# ─────────────────────────────────────────────────────────────────────────────

def connect_bdi() -> dict:
    """Fetch Baltic Dry Index from Yahoo Finance (^BDI)."""
    connector_id = "bdi_index"
    try:
        import yfinance as yf
        ticker = yf.Ticker("^BDI")
        hist = ticker.history(period="7d")
        if hist.empty:
            HubCatalog.set_status(connector_id, "Failing", error_msg="No BDI data")
            return {"ok": False, "error": "No BDI data from yfinance"}

        latest = float(hist["Close"].iloc[-1])
        records = []
        for dt, row in hist.iterrows():
            records.append({
                "date": dt.strftime("%Y-%m-%d"),
                "bdi_value": round(float(row["Close"]), 2),
                "source": "Yahoo Finance",
            })

        HubCache.set(connector_id, {"records": records, "latest": latest})
        HubCatalog.set_status(connector_id, "Live", success=True)
        return {"ok": True, "connector_id": connector_id, "records": len(records),
                "latest_bdi": latest}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_gold() -> dict:
    """Fetch Gold price from Yahoo Finance (GC=F)."""
    connector_id = "gold_price"
    try:
        import yfinance as yf
        ticker = yf.Ticker("GC=F")
        hist = ticker.history(period="7d")
        if hist.empty:
            HubCatalog.set_status(connector_id, "Failing", error_msg="No gold data")
            return {"ok": False, "error": "No gold data from yfinance"}

        latest = float(hist["Close"].iloc[-1])
        records = []
        for dt, row in hist.iterrows():
            records.append({
                "date": dt.strftime("%Y-%m-%d"),
                "gold_usd_oz": round(float(row["Close"]), 2),
                "source": "Yahoo Finance",
            })

        HubCache.set(connector_id, {"records": records, "latest": latest})
        HubCatalog.set_status(connector_id, "Live", success=True)
        return {"ok": True, "connector_id": connector_id, "records": len(records),
                "latest_gold": latest}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


# ═══════════════════════════════════════════════════════════════════════════════
# NEW CONNECTORS (Step 9) — 8 additional free API connectors
# ═══════════════════════════════════════════════════════════════════════════════

def connect_rbi_fx() -> dict:
    """Fetch RBI reference USD/INR rate."""
    connector_id = "rbi_fx"
    try:
        # Derive from existing FX data with RBI label
        # Primary source: RBI DBIE at rbi.org.in (HTML scraping not reliable)
        # Fallback: use fawazahmed0 FX data as RBI-approximate reference
        cached_fx = HubCache.get("fx")
        if cached_fx and isinstance(cached_fx, dict):
            records = cached_fx.get("records", [])
            if records:
                latest = records[-1] if isinstance(records, list) else records
                rate = latest.get("usd_inr") or latest.get("rate")
                if rate:
                    rbi_record = {
                        "date": _ts()[:10],
                        "usd_inr": round(float(rate), 4),
                        "source": "RBI Reference (via fawazahmed0)",
                    }
                    HubCache.set(connector_id, {"records": [rbi_record], "latest": float(rate)})
                    HubCatalog.set_status(connector_id, "Live", success=True)
                    return {"ok": True, "connector_id": connector_id, "records": 1,
                            "latest_rate": float(rate)}

        HubCatalog.set_status(connector_id, "Failing", error_msg="No FX data available")
        return {"ok": False, "error": "No FX data for RBI reference"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_opec_monthly() -> dict:
    """Fetch OPEC basket price and monthly report data."""
    connector_id = "opec_monthly"
    try:
        # OPEC provides basket price data via public pages
        # Fallback: derive OPEC basket estimate from Brent (OPEC basket ~ Brent - ₹ 2-4)
        cached_crude = HubCache.get("eia_crude")
        if cached_crude and isinstance(cached_crude, dict):
            records = cached_crude.get("records", [])
            opec_records = []
            for rec in (records[-30:] if isinstance(records, list) else []):
                brent = rec.get("brent_usd") or rec.get("close")
                if brent:
                    opec_records.append({
                        "date": rec.get("date", _ts()[:10]),
                        "opec_basket_usd": round(float(brent) - 2.5, 2),
                        "brent_reference": round(float(brent), 2),
                        "source": "Estimated from Brent",
                    })
            if opec_records:
                HubCache.set(connector_id, {"records": opec_records,
                                            "latest": opec_records[-1]["opec_basket_usd"]})
                HubCatalog.set_status(connector_id, "Live", success=True)
                return {"ok": True, "connector_id": connector_id,
                        "records": len(opec_records)}

        HubCatalog.set_status(connector_id, "Failing", error_msg="No crude data for OPEC estimate")
        return {"ok": False, "error": "Cannot estimate OPEC basket"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_eia_steo() -> dict:
    """Fetch EIA Short-Term Energy Outlook data."""
    connector_id = "eia_steo"
    try:
        # EIA STEO provides free energy forecasts
        # Try the free API endpoint
        url = "https://api.eia.gov/v2/steo/data/"
        api_key = ""
        try:
            from settings_engine import get_settings
            api_key = get_settings().get("eia_api_key", "")
        except Exception:
            pass

        if api_key:
            params = {
                "api_key": api_key,
                "frequency": "monthly",
                "data[0]": "value",
                "facets[seriesId][]": "BREPUUS",  # Brent price forecast
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 24,
            }
            resp = _session.get(url, params=params, timeout=30)
            if resp.ok:
                data = resp.json()
                records = []
                for item in data.get("response", {}).get("data", []):
                    records.append({
                        "period": item.get("period"),
                        "brent_forecast_usd": item.get("value"),
                        "source": "EIA STEO",
                    })
                if records:
                    HubCache.set(connector_id, {"records": records})
                    HubCatalog.set_status(connector_id, "Live", success=True)
                    return {"ok": True, "connector_id": connector_id,
                            "records": len(records)}

        # Fallback: use ML forecast as proxy
        try:
            from ml_forecast_engine import forecast_crude_price
            forecast = forecast_crude_price(30)
            if forecast and forecast.get("predicted"):
                records = [{"period": _ts()[:7], "brent_forecast_usd": forecast["predicted"][-1],
                            "source": "ML Forecast (EIA fallback)"}]
                HubCache.set(connector_id, {"records": records})
                HubCatalog.set_status(connector_id, "Live", success=True)
                return {"ok": True, "connector_id": connector_id, "records": 1}
        except Exception:
            pass

        HubCatalog.set_status(connector_id, "Failing", error_msg="No EIA API key configured")
        return {"ok": False, "error": "EIA STEO requires API key — set eia_api_key in settings"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_dgft_imports() -> dict:
    """Fetch India trade statistics from data.gov.in."""
    connector_id = "dgft_imports"
    try:
        # data.gov.in provides free trade data (API key optional)
        # Fallback: derive from existing UN Comtrade data
        cached = HubCache.get("un_comtrade")
        if cached and isinstance(cached, dict):
            records = cached.get("records", [])
            if records:
                HubCache.set(connector_id, {
                    "records": records,
                    "source": "UN Comtrade (DGFT fallback)",
                })
                HubCatalog.set_status(connector_id, "Live", success=True)
                return {"ok": True, "connector_id": connector_id,
                        "records": len(records) if isinstance(records, list) else 1}

        HubCatalog.set_status(connector_id, "Failing", error_msg="No trade data available")
        return {"ok": False, "error": "DGFT data unavailable"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_nhai_tenders() -> dict:
    """Fetch NHAI highway construction tenders."""
    connector_id = "nhai_tenders"
    try:
        # Use infra_demand_engine for NHAI/GDELT data
        try:
            from infra_demand_engine import get_nhai_tender_summary
            summary = get_nhai_tender_summary()
            if summary:
                HubCache.set(connector_id, summary)
                HubCatalog.set_status(connector_id, "Live", success=True)
                return {"ok": True, "connector_id": connector_id,
                        "records": summary.get("total_tenders", 0)}
        except (ImportError, AttributeError):
            pass

        # Fallback: use existing infra demand data
        try:
            from infra_demand_engine import get_infra_demand_signal
            signal = get_infra_demand_signal()
            if signal:
                HubCache.set(connector_id, {"signal": signal, "source": "infra_demand_engine"})
                HubCatalog.set_status(connector_id, "Live", success=True)
                return {"ok": True, "connector_id": connector_id, "records": 1}
        except Exception:
            pass

        HubCatalog.set_status(connector_id, "Failing", error_msg="Infra demand engine unavailable")
        return {"ok": False, "error": "NHAI tender data unavailable"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_cement_index() -> dict:
    """Fetch cement price index as a construction demand proxy."""
    connector_id = "cement_index"
    try:
        # Cement price is a strong proxy for construction activity/bitumen demand
        # Use public commodity data or estimate from construction indices
        import yfinance as yf

        # UltraTech Cement (India's largest cement company) as proxy
        ticker = yf.Ticker("ULTRACEMCO.NS")
        hist = ticker.history(period="30d")
        if not hist.empty:
            records = []
            for dt, row in hist.iterrows():
                records.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "cement_proxy_inr": round(float(row["Close"]), 2),
                    "volume": int(row.get("Volume", 0)),
                    "source": "UltraTech Cement NSE",
                })
            latest = float(hist["Close"].iloc[-1])
            pct_change_30d = round(
                (float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[0]) - 1) * 100, 2
            ) if len(hist) > 1 else 0.0

            HubCache.set(connector_id, {
                "records": records,
                "latest": latest,
                "pct_change_30d": pct_change_30d,
                "interpretation": "rising" if pct_change_30d > 2 else "falling" if pct_change_30d < -2 else "stable",
            })
            HubCatalog.set_status(connector_id, "Live", success=True)
            return {"ok": True, "connector_id": connector_id, "records": len(records),
                    "trend": "rising" if pct_change_30d > 2 else "stable"}

        HubCatalog.set_status(connector_id, "Failing", error_msg="No cement data")
        return {"ok": False, "error": "Cement index data unavailable"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_iocl_circular() -> dict:
    """Fetch IOCL bitumen price circular data."""
    connector_id = "iocl_circular"
    try:
        # IOCL publishes bitumen price circulars fortnightly
        # Use existing feasibility engine PSU price data
        try:
            from feasibility_engine import get_psu_prices
            prices = get_psu_prices()
            if prices:
                records = []
                for refinery, price_data in prices.items():
                    records.append({
                        "refinery": refinery,
                        "grade": "VG-30",
                        "price_inr_mt": price_data.get("price") or price_data.get("vg30"),
                        "effective_date": price_data.get("date", _ts()[:10]),
                        "source": "IOCL/PSU circular",
                    })
                if records:
                    HubCache.set(connector_id, {"records": records})
                    HubCatalog.set_status(connector_id, "Live", success=True)
                    return {"ok": True, "connector_id": connector_id,
                            "records": len(records)}
        except (ImportError, AttributeError):
            pass

        # Fallback: check existing price snapshot
        try:
            from ai_data_layer import get_price_snapshot
            snapshot = get_price_snapshot()
            if snapshot:
                HubCache.set(connector_id, {"snapshot": snapshot, "source": "ai_data_layer"})
                HubCatalog.set_status(connector_id, "Live", success=True)
                return {"ok": True, "connector_id": connector_id, "records": 1}
        except Exception:
            pass

        HubCatalog.set_status(connector_id, "Failing", error_msg="PSU price data unavailable")
        return {"ok": False, "error": "IOCL circular data unavailable"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def connect_fred_data() -> dict:
    """Fetch FRED economic data (USD index, interest rates)."""
    connector_id = "fred_macro"
    try:
        api_key = ""
        try:
            from settings_engine import get_settings
            api_key = get_settings().get("fred_api_key", "")
        except Exception:
            pass

        if api_key:
            # DXY (Dollar Index) and Fed Funds Rate
            series_ids = {"DTWEXBGS": "usd_broad_index", "DFF": "fed_funds_rate"}
            all_records = {}
            for series_id, label in series_ids.items():
                url = f"https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "limit": 30,
                    "sort_order": "desc",
                }
                resp = _session.get(url, params=params, timeout=30)
                if resp.ok:
                    data = resp.json()
                    observations = data.get("observations", [])
                    all_records[label] = [
                        {"date": obs["date"], "value": obs["value"]}
                        for obs in observations if obs.get("value") != "."
                    ]

            if all_records:
                HubCache.set(connector_id, {"records": all_records, "source": "FRED"})
                HubCatalog.set_status(connector_id, "Live", success=True)
                total = sum(len(v) for v in all_records.values())
                return {"ok": True, "connector_id": connector_id, "records": total}

        # Fallback: use yfinance for DXY
        try:
            import yfinance as yf
            dxy = yf.Ticker("DX-Y.NYB")
            hist = dxy.history(period="30d")
            if not hist.empty:
                records = []
                for dt, row in hist.iterrows():
                    records.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "usd_index": round(float(row["Close"]), 2),
                    })
                HubCache.set(connector_id, {
                    "records": {"usd_broad_index": records},
                    "source": "yfinance DXY fallback",
                })
                HubCatalog.set_status(connector_id, "Live", success=True)
                return {"ok": True, "connector_id": connector_id, "records": len(records)}
        except Exception:
            pass

        HubCatalog.set_status(connector_id, "Failing", error_msg="No FRED API key, yfinance DXY failed")
        return {"ok": False, "error": "FRED data unavailable — set fred_api_key in settings"}
    except Exception as e:
        HubCatalog.set_status(connector_id, "Failing", error_msg=str(e)[:80])
        return {"ok": False, "error": str(e)[:100]}


def run_single_connector(connector_id: str) -> bool:
    """Run a single connector by ID. Used by DeadLetterQueue retries."""
    _CONNECTOR_MAP = {
        "eia_crude": connect_eia, "un_comtrade": connect_comtrade,
        "weather": connect_weather, "news": connect_news,
        "fx": connect_fx, "ports": connect_ports, "refinery": connect_refinery,
        "maritime_intel": connect_maritime,
        "bdi_index": connect_bdi, "gold_price": connect_gold,
        # New connectors
        "rbi_fx": connect_rbi_fx, "opec_monthly": connect_opec_monthly,
        "eia_steo": connect_eia_steo, "dgft_imports": connect_dgft_imports,
        "nhai_tenders": connect_nhai_tenders, "cement_index": connect_cement_index,
        "iocl_circular": connect_iocl_circular, "fred_macro": connect_fred_data,
    }
    fn = _CONNECTOR_MAP.get(connector_id)
    if not fn:
        return False
    try:
        result = fn()
        return result.get("ok", False) if isinstance(result, dict) else bool(result)
    except Exception:
        return False


def run_all_connectors(force: bool = False) -> dict:
    """
    Run all API connectors in parallel with circuit breaker protection.
    If force=False, respects cache TTL.
    Returns summary of results.
    """
    results = {}
    connectors = [
        ("eia_crude",     connect_eia),
        ("un_comtrade",   connect_comtrade),
        ("weather",       connect_weather),
        ("news",          connect_news),
        ("fx",            connect_fx),
        ("ports",         connect_ports),
        ("refinery",      connect_refinery),
        ("maritime_intel", connect_maritime),
        ("bdi_index",     connect_bdi),
        ("gold_price",    connect_gold),
        # New connectors (Step 9)
        ("rbi_fx",        connect_rbi_fx),
        ("opec_monthly",  connect_opec_monthly),
        ("eia_steo",      connect_eia_steo),
        ("dgft_imports",  connect_dgft_imports),
        ("nhai_tenders",  connect_nhai_tenders),
        ("cement_index",  connect_cement_index),
        ("iocl_circular", connect_iocl_circular),
        ("fred_macro",    connect_fred_data),
    ]

    if force:
        for cid, _ in connectors:
            HubCache.invalidate(cid)
    else:
        # Smart scheduling — skip connectors with fresh cache
        connectors = [(cid, fn) for cid, fn in connectors if _should_refresh(cid)]
        if not connectors:
            return {"skipped": "all caches fresh", "refreshed": 0}

    # ── Try parallel execution via ConcurrentExecutor ─────────────────────
    try:
        from resilience_manager import ConcurrentExecutor, LKGCache, DeadLetterQueue
        from sre_engine import CircuitBreaker
        from resilience_config import get_cb_profile

        # Build per-connector circuit breakers (reuse across calls)
        if not hasattr(run_all_connectors, "_breakers"):
            run_all_connectors._breakers = {}
            for cid, _ in connectors:
                profile = get_cb_profile(cid)
                run_all_connectors._breakers[cid] = CircuitBreaker(
                    cid, profile["threshold"], profile["timeout_sec"])

        def _safe_connect(name, fn):
            """Wrap connector with circuit breaker + LKG fallback."""
            cb = run_all_connectors._breakers.get(name)
            try:
                if cb:
                    result = cb.call(fn)
                else:
                    result = fn()
                # Save as LKG on success
                if isinstance(result, dict) and result.get("ok"):
                    LKGCache.save_snapshot(name, result, confidence_pct=85)
                return result
            except ConnectionError:
                # Circuit breaker open — try LKG
                lkg = LKGCache.get_snapshot(name)
                if lkg and lkg.get("data"):
                    r = lkg["data"]
                    if isinstance(r, dict):
                        r["_lkg"] = True
                    return r
                return {"ok": False, "error": f"Circuit breaker OPEN for {name}"}
            except Exception as e:
                # Push to DLQ for later retry
                DeadLetterQueue.push("hub_connector", {"connector_id": name}, str(e))
                # Try LKG as last resort
                lkg = LKGCache.get_snapshot(name)
                if lkg and lkg.get("data"):
                    r = lkg["data"]
                    if isinstance(r, dict):
                        r["_lkg"] = True
                    return r
                return {"ok": False, "error": str(e)[:100]}

        tasks = [
            {"name": cid, "fn": _safe_connect, "args": (cid, fn), "timeout": 60}
            for cid, fn in connectors
        ]
        parallel_results = ConcurrentExecutor.run_parallel(tasks, max_workers=5, timeout_per_task=60)
        for pr in parallel_results:
            results[pr["name"]] = pr.get("result") or {"ok": False, "error": pr.get("error", "timeout")}

    except ImportError:
        # Fallback to sequential execution if resilience_manager not available
        for name, fn in connectors:
            try:
                result = fn()
                results[name] = result
            except Exception as e:
                results[name] = {"ok": False, "error": str(e)[:100]}
                _hub_log(name, "FAIL", f"Connector exception: {e}")

    # ── Govt connectors extension ─────────────────────────────────────────
    try:
        from govt_connectors import run_govt_connectors
        govt = run_govt_connectors(force=force)
        results.update(govt.get("results", {}))
    except Exception as _ge:
        _hub_log("govt_connectors", "FAIL", f"Govt connectors skipped: {_ge}")

    summary = {
        "timestamp_ist": _ts(),
        "total":   len(results),
        "ok":      sum(1 for r in results.values()
                       if isinstance(r, dict) and r.get("ok")),
        "failed":  sum(1 for r in results.values()
                       if isinstance(r, dict) and not r.get("ok")),
        "results": results,
        "table_summary": NormalizedTables.summary(),
    }
    _hub_log("hub_orchestrator", "OK",
             f"Full refresh: {summary['ok']}/{summary['total']} OK", 0)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# HUB SCHEDULER — background auto-refresh
# ─────────────────────────────────────────────────────────────────────────────

_hub_scheduler_started = False
_hub_sched_lock        = threading.Lock()


def start_hub_scheduler(interval_min: int = 60) -> None:
    """
    Start background daemon thread that runs run_all_connectors() periodically.
    Safe to call multiple times — starts only once per process.
    """
    global _hub_scheduler_started
    with _hub_sched_lock:
        if _hub_scheduler_started:
            return
        _hub_scheduler_started = True

    def _worker():
        time.sleep(90)  # allow dashboard to fully boot
        while True:
            try:
                from resilience_manager import HeartbeatMonitor
                HeartbeatMonitor.beat("HubScheduler")
            except Exception:
                pass
            try:
                run_all_connectors(force=False)
            except Exception as e:
                _hub_log("hub_scheduler", "FAIL", f"Scheduler exception: {e}")
            time.sleep(interval_min * 60)

    t = threading.Thread(target=_worker, daemon=True, name="HubScheduler")
    t.start()

    # Register with heartbeat monitor
    try:
        from resilience_manager import HeartbeatMonitor
        HeartbeatMonitor.register(
            "HubScheduler",
            restart_fn=lambda: start_hub_scheduler(interval_min),
            expected_interval_sec=interval_min * 60,
        )
    except Exception:
        pass

    _hub_log("hub_scheduler", "INFO",
             f"Hub scheduler started (interval={interval_min}min)", 0)


# ─────────────────────────────────────────────────────────────────────────────
# INITIALISE — call on startup
# ─────────────────────────────────────────────────────────────────────────────

def init_hub() -> None:
    """Ensure catalog + all table files exist. Call once on app startup."""
    # Write default catalog if missing
    if not CATALOG_FILE.exists():
        _save(CATALOG_FILE, DEFAULT_CATALOG)
    else:
        # Merge: add any new default connectors not already in file
        existing = _load(CATALOG_FILE, {})
        updated  = False
        for k, v in DEFAULT_CATALOG.items():
            if k not in existing:
                existing[k] = v
                updated = True
        if updated:
            _save(CATALOG_FILE, existing)

    # Also merge DEFAULT_CATALOG_GOVT into hub_catalog.json
    existing = _load(CATALOG_FILE, {})
    updated  = False
    for k, v in DEFAULT_CATALOG_GOVT.items():
        if k not in existing:
            existing[k] = v
            updated = True
    if updated:
        _save(CATALOG_FILE, existing)

    # Ensure all table files exist (original 7 + 10 new govt tables)
    for f, default in [
        (TBL_CRUDE,    []),
        (TBL_FX,       []),
        (TBL_TRADE,    []),
        (TBL_PORTS,    []),
        (TBL_REFINERY, []),
        (TBL_WEATHER,  []),
        (TBL_NEWS,     []),
        (HUB_LOG_FILE, []),
        (HUB_CACHE_FILE, {}),
        # Govt extension tables
        (BASE / "tbl_highway_km.json",            []),
        (BASE / "tbl_demand_proxy.json",          []),
        (BASE / "tbl_imports_countrywise.json",   []),
        (BASE / "tbl_ports_master.json",          []),
        (BASE / "tbl_port_allocation_rules.json", []),
        (BASE / "tbl_imports_portwise.json",      []),
        (BASE / "tbl_corr_results.json",          []),
        (BASE / "tbl_regression_coeff.json",      []),
        (BASE / "tbl_insights.json",              []),
        (BASE / "tbl_api_runs.json",              []),
        # Directory tables
        (BASE / "tbl_dir_orgs.json",             []),
        (BASE / "tbl_dir_sources.json",          []),
        (BASE / "tbl_dir_changes.json",          []),
        (BASE / "tbl_dir_fetch_logs.json",       []),
        (BASE / "tbl_dir_bugs.json",             []),
        (BASE / "tbl_dir_geo.json",              []),
        # Contact import tables
        (TBL_CONTACTS,    []),
        (TBL_IMPORT_HIST, []),
        # Maritime tables
        (TBL_MARITIME,                          {}),
        (BASE / "tbl_maritime_routes.json",     {}),
    ]:
        if not f.exists():
            _save(f, default)

    _hub_log("hub_init", "INFO", "API HUB Engine v3.2.3 initialised (+ govt tables + directory)", 0)
