"""
PPS Anantams Logistics AI
API Intelligence & Monitoring System v3.0
==========================================
Centralized API Registry | Auto Health Check | Auto Repair Engine
Bug Tracker | Change Log | Development Activity Logger

All times in IST (Asia/Kolkata) | Format: DD-MM-YYYY HH:MM:SS
Security: No API keys stored in frontend. Config-driven. Keys via environment only.
"""

import json
import time
import threading
import requests
import datetime
import pytz
from pathlib import Path

# ── Optional yfinance ─────────────────────────────────────────────────────────
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_FILE  = BASE_DIR / "api_config.json"
CACHE_FILE   = BASE_DIR / "api_cache.json"
STATS_FILE   = BASE_DIR / "api_stats.json"
ERROR_LOG    = BASE_DIR / "api_error_log.json"
CHANGE_LOG   = BASE_DIR / "api_change_log.json"
DEV_LOG      = BASE_DIR / "api_dev_log.json"
HEALTH_LOG   = BASE_DIR / "api_health_log.json"

IST = pytz.timezone("Asia/Kolkata")

# ─────────────────────────────────────────────────────────────────────────────
# TIMESTAMP HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def now_ist() -> datetime.datetime:
    return datetime.datetime.now(IST)

def ts_str() -> str:
    return now_ist().strftime("%Y-%m-%d %H:%M:%S IST")

def ts_iso() -> str:
    return now_ist().isoformat()

# ─────────────────────────────────────────────────────────────────────────────
# JSON STORAGE HELPERS (thread-safe append)
# ─────────────────────────────────────────────────────────────────────────────

_lock = threading.RLock()  # RLock: re-entrant; allows _append_record → _save_json nesting

def _load_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def _save_json(path: Path, data):
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def _append_record(path: Path, record: dict, max_records: int = 500):
    """Append one record to a JSON list file, keeping only max_records."""
    with _lock:
        data = _load_json(path, [])
        data.append(record)
        if len(data) > max_records:
            data = data[-max_records:]
        _save_json(path, data)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    return _load_json(CONFIG_FILE, {"widgets": {}, "tab_api_map": {}, "health_check_config": {}})

def load_cache() -> dict:
    return _load_json(CACHE_FILE, {})

def save_cache(cache: dict):
    _save_json(CACHE_FILE, cache)

def load_stats() -> dict:
    return _load_json(STATS_FILE, {})

def save_stats(stats: dict):
    _save_json(STATS_FILE, stats)

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING ENGINES
# ─────────────────────────────────────────────────────────────────────────────

def log_error(api_id: str, component: str, error_type: str, message: str,
              severity: str = "P2", auto_fixed: bool = False,
              manual_required: bool = True, root_cause: str = "", resolution_notes: str = ""):
    """Log to api_error_log.json — persistent bug tracker."""
    record = {
        "datetime_ist": ts_str(),
        "api_id": api_id,
        "component": component,
        "error_type": error_type,
        "severity": severity,
        "message": message,
        "auto_fixed": auto_fixed,
        "manual_required": manual_required,
        "root_cause": root_cause,
        "resolution_notes": resolution_notes,
        "status": "Auto-Fixed" if auto_fixed else ("Open" if manual_required else "Suppressed"),
    }
    _append_record(ERROR_LOG, record, max_records=1000)

def log_change(component: str, what_changed: str, old_value: str, new_value: str,
               reason: str, trigger: str = "Auto", affected_tab: str = "",
               affected_api: str = "", user_id: str = "System"):
    """Log to api_change_log.json — full audit trail."""
    record = {
        "datetime_ist": ts_str(),
        "component": component,
        "what_changed": what_changed,
        "old_value": str(old_value),
        "new_value": str(new_value),
        "reason": reason,
        "trigger": trigger,
        "affected_tab": affected_tab,
        "affected_api": affected_api,
        "user_id": user_id,
    }
    _append_record(CHANGE_LOG, record, max_records=2000)

def log_dev_activity(activity_type: str, title: str, description: str,
                     status: str = "Completed", component: str = "",
                     department: str = "Technology"):
    """Log to api_dev_log.json — development activity tracker."""
    record = {
        "datetime_ist": ts_str(),
        "activity_type": activity_type,
        "title": title,
        "description": description,
        "status": status,
        "component": component,
        "department": department,
    }
    _append_record(DEV_LOG, record, max_records=500)

def log_health(api_id: str, status: str, latency_ms: int,
               http_code: int = 0, error_detail: str = "",
               action_taken: str = "None"):
    """Log to api_health_log.json — continuous health audit."""
    record = {
        "datetime_ist": ts_str(),
        "api_id": api_id,
        "status": status,
        "latency_ms": latency_ms,
        "http_code": http_code,
        "error_detail": error_detail,
        "action_taken": action_taken,
    }
    _append_record(HEALTH_LOG, record, max_records=2000)

# ─────────────────────────────────────────────────────────────────────────────
# YFINANCE FETCH
# ─────────────────────────────────────────────────────────────────────────────

def fetch_yfinance_with_history(symbol: str):
    """
    Download price + 7-day history for a yfinance ticker.
    Uses yf.download() which works for commodity futures (BZ=F, CL=F, NG=F etc.)
    unlike yf.Ticker().history() which silently returns empty for futures.
    """
    if not YFINANCE_AVAILABLE or not symbol:
        return None, None
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = yf.download(symbol, period="7d", progress=False, timeout=12)
        if data is None or data.empty:
            return None, None
        close_col = [c for c in data.columns if "Close" in str(c)]
        if not close_col:
            return None, None
        closes = data[close_col[0]].dropna()
        if len(closes) < 1:
            return None, None
        current   = float(closes.iloc[-1])
        history_7d = float(closes.iloc[0]) if len(closes) > 1 else current
        return current, history_7d
    except Exception:
        return None, None

# ─────────────────────────────────────────────────────────────────────────────
# PARSE HELPERS FOR SPECIAL API TYPES
# ─────────────────────────────────────────────────────────────────────────────

def _parse_worldbank(response_json) -> dict:
    """World Bank API returns [metadata, [data_array]]."""
    try:
        arr = response_json[1]
        for item in arr:
            if item.get("value") is not None:
                return {
                    "current": float(item["value"]),
                    "year": item.get("date", ""),
                    "country": item.get("country", {}).get("value", ""),
                }
    except Exception:
        pass
    return None

def _parse_open_meteo_daily(response_json) -> dict:
    """Open-Meteo daily forecast parser."""
    try:
        daily = response_json.get("daily", {})
        temps = daily.get("temperature_2m_max", [])
        precip = daily.get("precipitation_sum", [])
        dates = daily.get("time", [])
        return {"current": temps[0] if temps else 0, "forecast_7d": list(zip(dates, temps, precip))}
    except Exception:
        return None

def _parse_holiday_list(response_json) -> dict:
    """Nager.Date holiday list parser."""
    try:
        holidays = [
            {"date": h["date"], "name": h["localName"]}
            for h in response_json
        ]
        return {"current": len(holidays), "holidays": holidays[:20]}
    except Exception:
        return None


# ── India public holidays built-in (2025-2026, used when external API fails) ─
_INDIA_HOLIDAYS_2026 = [
    {"date": "2026-01-01", "name": "New Year's Day"},
    {"date": "2026-01-14", "name": "Makar Sankranti"},
    {"date": "2026-01-26", "name": "Republic Day"},
    {"date": "2026-03-03", "name": "Holi"},
    {"date": "2026-04-02", "name": "Ram Navami"},
    {"date": "2026-04-03", "name": "Good Friday"},
    {"date": "2026-04-14", "name": "Dr. Ambedkar Jayanti / Baisakhi"},
    {"date": "2026-05-01", "name": "Maharashtra Day / Labour Day"},
    {"date": "2026-06-08", "name": "Eid al-Adha (Bakrid)"},
    {"date": "2026-07-06", "name": "Muharram"},
    {"date": "2026-08-15", "name": "Independence Day"},
    {"date": "2026-08-25", "name": "Janmashtami"},
    {"date": "2026-09-14", "name": "Milad-un-Nabi (Prophet's Birthday)"},
    {"date": "2026-10-02", "name": "Gandhi Jayanti / Dussehra"},
    {"date": "2026-10-20", "name": "Diwali (Lakshmi Puja)"},
    {"date": "2026-11-04", "name": "Guru Nanak Jayanti"},
    {"date": "2026-11-14", "name": "Children's Day"},
    {"date": "2026-12-25", "name": "Christmas Day"},
]

def _get_local_holidays() -> dict:
    """Return built-in India public holidays for the current year."""
    year = now_ist().year
    holidays = [h for h in _INDIA_HOLIDAYS_2026 if h["date"].startswith(str(year))]
    if not holidays:
        # Fallback to full list if year not matching
        holidays = _INDIA_HOLIDAYS_2026
    return {"current": len(holidays), "holidays": holidays}

def _parse_rest_countries(response_json) -> dict:
    """REST Countries v3.1 — returns list with one country dict."""
    try:
        item = response_json[0] if isinstance(response_json, list) else response_json
        return {
            "current":    item.get("population", 0),
            "name":       item.get("name", {}).get("common", "India"),
            "capital":    (item.get("capital") or ["New Delhi"])[0],
            "area":       item.get("area", 3287263),
            "region":     item.get("region", "Asia"),
            "currencies": list((item.get("currencies") or {}).keys()),
        }
    except Exception:
        return None


def _parse_standard(response_json, rules: dict):
    """Standard key-path parser."""
    try:
        if "base_key" in rules and "target_key" in rules:
            return float(response_json[rules["base_key"]][rules["target_key"]])
        elif "direct_key" in rules:
            return response_json[rules["direct_key"]]
    except Exception:
        pass
    return None

# ─────────────────────────────────────────────────────────────────────────────
# CORE FETCH WITH AUTO-REPAIR
# ─────────────────────────────────────────────────────────────────────────────

def fetch_api_data(widget_id: str, force: bool = False):
    """
    Main fetch function.
    1. Check cache (skip if force=True or TTL expired)
    2. Try primary API
    3. On failure: auto-repair → retry → fallback
    4. Log everything
    5. Return parsed data dict or None
    """
    config_all = load_config()
    config = config_all.get("widgets", {}).get(widget_id)
    if not config:
        return None

    cache = load_cache()
    stats = load_stats()
    now_ts = time.time()

    # Init stats entry
    if widget_id not in stats:
        stats[widget_id] = {
            "status": "Unknown", "last_call_time": None, "avg_latency_ms": 0,
            "failures": 0, "calls": 0, "consecutive_failures": 0, "plan": "Free",
            "auto_repair_count": 0, "fallback_activations": 0,
        }

    # Cache check
    refresh_sec = config.get("refresh_interval_sec", 3600)
    cached = cache.get(widget_id)
    if not force and cached and (now_ts - cached.get("timestamp", 0)) < refresh_sec:
        return cached["data"]

    # ── Fetch attempt ────────────────────────────────────────────────────────
    start = time.time()
    provider = config.get("provider", "")
    endpoint = config.get("endpoint", "")
    rules = config.get("parse_rules", {})
    parse_type = rules.get("type", "standard")
    success = False
    result_data = None
    http_code = 0
    error_detail = ""
    action_taken = "Primary fetch"

    hc = config_all.get("health_check_config", {})
    max_retries = hc.get("max_retry_attempts", 3)
    retry_delay = hc.get("retry_delay_seconds", 10)

    for attempt in range(max_retries):
        try:
            if provider == "local_holidays" or endpoint == "local_holidays":
                result_data = _get_local_holidays()
                success = True
                break

            elif provider == "yfinance" or endpoint == "yfinance":
                sym = config.get("fallback_symbol", "")
                val, val_7d = fetch_yfinance_with_history(sym)
                if val is not None:
                    result_data = {"current": float(val), "history_7d": float(val_7d)}
                    success = True
                    break

            elif provider == "local_datetime":
                result_data = {"current": now_ist().strftime("%H:%M:%S")}
                success = True
                break

            else:
                resp = requests.get(endpoint, timeout=8, headers={"User-Agent": "BitumenDashboard/3.0"})
                http_code = resp.status_code

                if resp.status_code == 429:
                    error_detail = "Rate limit (429)"
                    action_taken = f"Rate limit hit — backing off {retry_delay}s"
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    continue

                if resp.status_code != 200:
                    error_detail = f"HTTP {resp.status_code}"
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    continue

                js = resp.json()

                # Parse by type
                if parse_type == "worldbank_array":
                    parsed = _parse_worldbank(js)
                    if parsed:
                        result_data = parsed
                        success = True
                        break
                elif parse_type == "open_meteo_daily":
                    parsed = _parse_open_meteo_daily(js)
                    if parsed:
                        result_data = parsed
                        success = True
                        break
                elif parse_type == "holiday_list":
                    parsed = _parse_holiday_list(js)
                    if parsed:
                        result_data = parsed
                        success = True
                        break
                elif parse_type == "rest_countries":
                    parsed = _parse_rest_countries(js)
                    if parsed:
                        result_data = parsed
                        success = True
                        break
                else:
                    raw = _parse_standard(js, rules)
                    if raw is not None:
                        if isinstance(raw, str):
                            result_data = {"current": raw}
                        else:
                            val_7d_supp = None
                            if config.get("history_needed"):
                                sym = config.get("fallback_symbol")
                                if sym:
                                    _, val_7d_supp = fetch_yfinance_with_history(sym)
                            result_data = {
                                "current": float(raw),
                                "history_7d": float(val_7d_supp) if val_7d_supp else float(raw),
                            }
                        success = True
                        break

        except requests.exceptions.Timeout:
            error_detail = "Timeout (>8s)"
            action_taken = f"Timeout on attempt {attempt+1}/{max_retries}"
            if attempt < max_retries - 1:
                time.sleep(2)
        except requests.exceptions.ConnectionError:
            error_detail = "Connection error (no internet or host unreachable)"
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception as e:
            error_detail = str(e)[:200]
            if attempt < max_retries - 1:
                time.sleep(2)

    # ── Fallback if primary failed ───────────────────────────────────────────
    if not success:
        fb = config.get("fallback", "")
        fb_sym = config.get("fallback_symbol", "")

        if fb == "yfinance" and fb_sym and YFINANCE_AVAILABLE:
            val, val_7d = fetch_yfinance_with_history(fb_sym)
            if val is not None:
                result_data = {"current": float(val), "history_7d": float(val_7d)}
                success = True
                action_taken = f"Fallback activated → yfinance ({fb_sym})"
                stats[widget_id]["fallback_activations"] = stats[widget_id].get("fallback_activations", 0) + 1
                stats[widget_id]["auto_repair_count"] = stats[widget_id].get("auto_repair_count", 0) + 1

                log_change(
                    component=widget_id,
                    what_changed="Data source switched to fallback",
                    old_value=f"Primary: {endpoint}",
                    new_value=f"Fallback: yfinance({fb_sym})",
                    reason=f"Primary failed: {error_detail}",
                    trigger="Auto",
                    affected_api=widget_id,
                )
                log_dev_activity(
                    activity_type="Auto-Repair",
                    title=f"Fallback activated: {widget_id}",
                    description=f"Primary API failed ({error_detail}). Switched to yfinance({fb_sym}) fallback automatically.",
                    status="Completed",
                    component=widget_id,
                )

        elif fb == "local_datetime":
            result_data = {"current": now_ist().strftime("%H:%M:%S")}
            success = True
            action_taken = "Fallback → local system time"

    # ── Latency calculation ──────────────────────────────────────────────────
    latency_ms = int((time.time() - start) * 1000)

    # ── Update stats ─────────────────────────────────────────────────────────
    stats[widget_id]["last_call_time"] = ts_str()
    stats[widget_id]["calls"] = stats[widget_id].get("calls", 0) + 1

    if success:
        stats[widget_id]["status"] = "OK"
        stats[widget_id]["consecutive_failures"] = 0
        old_avg = stats[widget_id].get("avg_latency_ms", 0)
        stats[widget_id]["avg_latency_ms"] = int((old_avg + latency_ms) / 2) if old_avg > 0 else latency_ms
    else:
        prev_consec = stats[widget_id].get("consecutive_failures", 0)
        stats[widget_id]["status"] = "Fail"
        stats[widget_id]["failures"] = stats[widget_id].get("failures", 0) + 1
        stats[widget_id]["consecutive_failures"] = prev_consec + 1

        log_error(
            api_id=widget_id,
            component="API Fetch",
            error_type=error_detail or "Unknown failure",
            message=f"{config.get('name', widget_id)} failed after {max_retries} retries. Error: {error_detail}",
            severity="P0" if prev_consec >= 2 else "P1",
            auto_fixed=False,
            manual_required=True,
            root_cause=error_detail,
            resolution_notes="Check endpoint URL, rate limit, and API availability. Consider replacing with alternative free API.",
        )

        # Alert threshold
        alert_threshold = hc.get("alert_on_consecutive_failures", 3)
        if stats[widget_id]["consecutive_failures"] >= alert_threshold:
            log_dev_activity(
                activity_type="Alert",
                title=f"CRITICAL: {widget_id} failed {stats[widget_id]['consecutive_failures']} times consecutively",
                description=f"API: {config.get('name', widget_id)} | Endpoint: {endpoint} | Error: {error_detail}. Manual intervention required.",
                status="Pending",
                component=widget_id,
                department="Technology",
            )

    save_stats(stats)

    # ── Health log entry ─────────────────────────────────────────────────────
    log_health(
        api_id=widget_id,
        status="OK" if success else "FAIL",
        latency_ms=latency_ms,
        http_code=http_code,
        error_detail=error_detail if not success else "",
        action_taken=action_taken,
    )

    # ── Save to cache and return ─────────────────────────────────────────────
    if success and result_data:
        cache[widget_id] = {"timestamp": now_ts, "data": result_data, "source": action_taken}
        save_cache(cache)
        return result_data

    # Return stale cache if total failure
    if cached:
        return cached["data"]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def run_all_health_checks(force: bool = True) -> dict:
    """Run health checks for all APIs in the registry. Returns summary dict."""
    config = load_config()
    widgets = config.get("widgets", {})
    results = {}
    total = len(widgets)
    healthy = 0
    failed = 0

    for wid in widgets:
        start = time.time()
        data = fetch_api_data(wid, force=force)
        latency = int((time.time() - start) * 1000)
        ok = data is not None
        results[wid] = {"ok": ok, "latency_ms": latency, "data": data}
        if ok:
            healthy += 1
        else:
            failed += 1

    summary = {
        "total": total, "healthy": healthy, "failed": failed,
        "health_pct": round(healthy / total * 100) if total > 0 else 0,
        "timestamp": ts_str(),
    }
    log_dev_activity(
        activity_type="Health Check",
        title=f"System-wide health check: {healthy}/{total} APIs healthy",
        description=f"Health: {summary['health_pct']}% | Failed: {failed} APIs | Run at {ts_str()}",
        status="Completed",
        component="All APIs",
        department="Technology",
    )
    return summary, results


def test_api_health(widget_id: str) -> dict:
    """Test a single API. Used by API Dashboard's diagnostic button."""
    return fetch_api_data(widget_id, force=True)


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

def validate_api_schema(widget_id: str) -> dict:
    """
    Validate that the API response still matches the expected schema.
    Returns {"valid": bool, "message": str}
    """
    cache = load_cache()
    cached = cache.get(widget_id, {}).get("data")

    if not cached:
        return {"valid": False, "message": "No cached data to validate"}

    if not isinstance(cached, dict):
        return {"valid": False, "message": f"Expected dict, got {type(cached).__name__}"}

    if "current" not in cached:
        return {"valid": False, "message": "Missing 'current' key in cached data"}

    return {"valid": True, "message": "Schema OK"}


# ─────────────────────────────────────────────────────────────────────────────
# RELIABILITY SCORER
# ─────────────────────────────────────────────────────────────────────────────

def get_reliability_scores() -> dict:
    """Calculate reliability % per API based on calls vs failures."""
    stats = load_stats()
    scores = {}
    for wid, s in stats.items():
        total = s.get("calls", 0)
        fails = s.get("failures", 0)
        if total > 0:
            scores[wid] = round(((total - fails) / total) * 100, 1)
        else:
            scores[wid] = 0.0
    return scores


# ─────────────────────────────────────────────────────────────────────────────
# DATA RETRIEVAL HELPERS (for tab usage)
# ─────────────────────────────────────────────────────────────────────────────

def get_brent_price() -> float:
    data = fetch_api_data("brent")
    return data["current"] if data else 80.0

def get_wti_price() -> float:
    data = fetch_api_data("wti")
    return data["current"] if data else 75.0

def get_usdinr() -> float:
    data = fetch_api_data("usdinr")
    return data["current"] if data else 83.25

def get_india_vix() -> float:
    data = fetch_api_data("india_vix")
    return data["current"] if data else 15.0

def get_nifty() -> float:
    data = fetch_api_data("nifty50")
    return data["current"] if data else 22000.0

def get_weather(city_key: str = "weather_mumbai") -> dict:
    return fetch_api_data(city_key) or {"current": 30}

def get_holidays() -> list:
    data = fetch_api_data("govt_holiday_api")
    return data.get("holidays", []) if data else []


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC LOG READERS (for Dev Activity tab)
# ─────────────────────────────────────────────────────────────────────────────

def get_error_log(n: int = 100) -> list:
    data = _load_json(ERROR_LOG, [])
    return list(reversed(data[-n:]))

def get_change_log(n: int = 200) -> list:
    data = _load_json(CHANGE_LOG, [])
    return list(reversed(data[-n:]))

def get_dev_log(n: int = 100) -> list:
    data = _load_json(DEV_LOG, [])
    return list(reversed(data[-n:]))

def get_health_log(n: int = 200) -> list:
    data = _load_json(HEALTH_LOG, [])
    return list(reversed(data[-n:]))


# ─────────────────────────────────────────────────────────────────────────────
# MANUAL CHANGE LOGGING (called from UI)
# ─────────────────────────────────────────────────────────────────────────────

def record_manual_change(component: str, what: str, old_val: str, new_val: str,
                          reason: str, tab: str, user: str = "Dashboard User"):
    log_change(
        component=component, what_changed=what, old_value=old_val,
        new_value=new_val, reason=reason, trigger="Manual",
        affected_tab=tab, user_id=user,
    )

def record_api_added(api_id: str, api_name: str, endpoint: str, tabs: list):
    log_dev_activity(
        activity_type="API Added",
        title=f"New API registered: {api_name}",
        description=f"API ID: {api_id} | Endpoint: {endpoint} | Tabs: {', '.join(tabs)}",
        status="Active",
        component=api_id,
    )
    log_change(
        component="api_config.json",
        what_changed="New API entry added",
        old_value="Not present",
        new_value=api_id,
        reason="API registry expansion",
        trigger="Development",
        affected_api=api_id,
        affected_tab=", ".join(tabs),
    )

def record_api_removed(api_id: str, reason: str):
    log_dev_activity(
        activity_type="API Removed",
        title=f"API deregistered: {api_id}",
        description=f"API ID: {api_id} removed. Reason: {reason}",
        status="Completed",
        component=api_id,
    )

def record_model_change(component: str, description: str, tab: str):
    log_dev_activity(
        activity_type="Model Change",
        title=f"Model updated: {component}",
        description=description,
        status="Deployed",
        component=component,
        department="Technology",
    )
    log_change(
        component=component, what_changed="Business logic / model updated",
        old_value="Previous version", new_value="New version",
        reason=description, trigger="Development", affected_tab=tab,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM INIT — log startup
# ─────────────────────────────────────────────────────────────────────────────

def init_system():
    """Called once on dashboard startup."""
    config = load_config()
    api_count = len(config.get("widgets", {}))
    log_dev_activity(
        activity_type="System Start",
        title="Dashboard initialized",
        description=f"API Intelligence System v3.0 started. {api_count} APIs registered. Auto-repair: Enabled.",
        status="Running",
        component="System",
        department="Technology",
    )


# ─────────────────────────────────────────────────────────────────────────────
# AUTO HEALTH SCHEDULER — background thread, checks every 30 min
# ─────────────────────────────────────────────────────────────────────────────

_G_health: dict = {"started": False, "last_run": "", "last_summary": {}}
_health_lock = threading.RLock()

AUTO_HEALTH_INTERVAL_MIN = 30   # check all APIs every 30 minutes


def start_auto_health(interval_min: int = AUTO_HEALTH_INTERVAL_MIN):
    """
    Start a daemon thread that runs run_all_health_checks() every interval_min.
    Idempotent — safe to call multiple times (only starts once per process).
    """
    with _health_lock:
        if _G_health["started"]:
            return
        _G_health["started"] = True

    def _loop():
        # Wait 90 seconds after startup before first check (let dashboard settle)
        time.sleep(90)
        while True:
            try:
                summary, _results = run_all_health_checks(force=True)
                _G_health["last_run"] = ts_str()
                _G_health["last_summary"] = summary
            except Exception as exc:
                log_error(
                    api_id="auto_health_scheduler",
                    component="Auto Health Scheduler",
                    error_type="SchedulerError",
                    message=str(exc)[:200],
                    severity="P2",
                    root_cause="Auto health scheduler exception",
                )
            time.sleep(interval_min * 60)

    t = threading.Thread(target=_loop, daemon=True, name="AutoHealthChecker")
    t.start()


def get_auto_health_status() -> dict:
    """Return last auto-health run info for the Dev Activity / API Dashboard."""
    return {
        "started":      _G_health["started"],
        "last_run":     _G_health.get("last_run", "Not yet run"),
        "last_summary": _G_health.get("last_summary", {}),
        "interval_min": AUTO_HEALTH_INTERVAL_MIN,
    }
