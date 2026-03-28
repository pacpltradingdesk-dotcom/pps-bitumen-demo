try:
    from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    try:
        from india_localization import format_inr, format_inr_short, format_date, format_datetime_ist, get_financial_year, get_fy_quarter
    except:
        pass
"""
PPS Anantam Agentic AI Eco System
SRE Engine v1.0 — Self-Healing + Auto Bug Fixing + Smart Alerts
================================================================
Phase 1 : Observability — AuditLogger + Metrics
Phase 2 : Health Check Engine — 8 entity types
Phase 3 : Self-Healing Rulebook — API / Data / Calc / Export
Phase 4 : Smart Alert System — P0 / P1 / P2 with dedup
Phase 5 : Bug Auto-Creation — full lifecycle
Phase 6 : Overwrite / Conflict Protection

All timestamps: IST  DD-MM-YYYY HH:MM:SS IST
India format  : ₹, DD-MM-YYYY, 24-hour IST
"""

import json
import time
import math
import uuid
import hashlib
import threading
import traceback
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz

# ─── IST helpers ──────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")


def _now() -> datetime.datetime:
    return datetime.datetime.now(IST)


def _ts() -> str:
    """DD-MM-YYYY HH:MM:SS IST"""
    return _now().strftime("%Y-%m-%d %H:%M:%S IST")


def _ts_id() -> str:
    """YYYYMMDD-HHMMSS for IDs"""
    return _now().strftime("%Y%m%d-%H%M%S")


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{_ts_id()}-{uuid.uuid4().hex[:4].upper()}"


# ─── File paths ───────────────────────────────────────────────────────────────
BASE = Path(__file__).parent

# SRE-owned files
_F_HEALTH    = BASE / "sre_health_status.json"
_F_ALERTS    = BASE / "sre_alerts.json"
_F_BUGS      = BASE / "sre_bugs.json"
_F_CONFLICT  = BASE / "sre_conflict_log.json"
_F_AUDIT     = BASE / "sre_audit_log.json"
_F_CONFIG    = BASE / "sre_config.json"
_F_METRICS   = BASE / "sre_metrics.json"

# Existing files (read-compatible — no circular import)
_F_ERROR_LOG = BASE / "api_error_log.json"
_F_HLTH_LOG  = BASE / "api_health_log.json"
_F_CHG_LOG   = BASE / "api_change_log.json"
_F_STATS     = BASE / "api_stats.json"
_F_CACHE     = BASE / "api_cache.json"
_F_PRICES    = BASE / "live_prices.json"

# ─── Thread lock ──────────────────────────────────────────────────────────────
_lock = threading.RLock()

# ─── Default configuration ────────────────────────────────────────────────────
_DEFAULT_CFG: Dict = {
    "alert_thresholds": {
        "api_latency_warn_ms":       3000,
        "api_latency_crit_ms":      10000,
        "api_error_rate_warn_pct":     10,
        "api_error_rate_crit_pct":     30,
        "stale_data_warn_hours":        2,
        "stale_data_crit_hours":        6,
        "scheduler_overdue_warn_min":  45,
        "scheduler_overdue_crit_min":  90,
        "consecutive_fail_warn":        2,
        "consecutive_fail_crit":        5,
    },
    "auto_heal": {
        "max_retry_attempts":          3,
        "retry_backoff_sec":      [5, 15, 30],
        "bug_after_n_failures":        3,
        "suppress_same_alert_min":    30,
    },
    "pricing_sanity": {
        "min_bitumen_inr_per_mt":  15000,
        "max_bitumen_inr_per_mt": 120000,
        "min_freight_inr_per_mt":    100,
        "max_freight_inr_per_mt":  15000,
        "min_margin_pct":            -50,
        "max_margin_pct":            200,
        "min_brent_usd":              20,
        "max_brent_usd":             200,
        "min_usdinr":                 50,
        "max_usdinr":                120,
    },
    "export": {
        "min_pdf_size_bytes": 1024,
    },
}

# ─── JSON I/O helpers ─────────────────────────────────────────────────────────

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


def _append(path: Path, record: dict, max_records: int = 2000) -> None:
    with _lock:
        data = _load(path, [])
        if not isinstance(data, list):
            data = []
        data.append(record)
        if len(data) > max_records:
            data = data[-max_records:]
        _save(path, data)


def _cfg() -> Dict:
    stored = _load(_F_CONFIG, {})
    merged = dict(_DEFAULT_CFG)
    for k, v in stored.items():
        if isinstance(v, dict) and k in merged:
            merged[k].update(v)
        else:
            merged[k] = v
    return merged


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — AUDIT LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

class AuditLogger:
    """
    Centralized structured logger.
    Logs: request_id, route, component, severity, message, payload_hash, IST timestamp.
    """

    @staticmethod
    def _hash(payload: Any) -> str:
        try:
            raw = json.dumps(payload, sort_keys=True, default=str)
            return hashlib.sha256(raw.encode()).hexdigest()[:12]
        except Exception:
            return "nohash"

    @classmethod
    def log(
        cls,
        severity: str,          # INFO / WARN / ERROR / CRITICAL
        component: str,
        message: str,
        route: str = "",
        user_id: str = "system",
        payload: Any = None,
        request_id: str = "",
    ) -> str:
        rid = request_id or _gen_id("REQ")
        record = {
            "request_id":   rid,
            "timestamp_ist": _ts(),
            "severity":     severity.upper(),
            "route":        route,
            "component":    component,
            "user_id":      user_id,
            "message":      message,
            "payload_hash": cls._hash(payload) if payload is not None else "",
        }
        _append(_F_AUDIT, record, max_records=5000)
        return rid

    @classmethod
    def info(cls, component: str, message: str, **kw) -> str:
        return cls.log("INFO", component, message, **kw)

    @classmethod
    def warn(cls, component: str, message: str, **kw) -> str:
        return cls.log("WARN", component, message, **kw)

    @classmethod
    def error(cls, component: str, message: str, **kw) -> str:
        return cls.log("ERROR", component, message, **kw)

    @classmethod
    def critical(cls, component: str, message: str, **kw) -> str:
        return cls.log("CRITICAL", component, message, **kw)

    @classmethod
    def get_recent(cls, n: int = 200, severity: Optional[str] = None) -> List[dict]:
        data = _load(_F_AUDIT, [])
        if severity:
            data = [r for r in data if r.get("severity") == severity.upper()]
        return data[-n:]


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — HEALTH CHECK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _upsert_health(entity_type: str, entity_name: str, status: str,
                   error_code: str = "", details: str = "",
                   auto_fix_attempted: str = "N") -> None:
    """Write / update one entity's health record."""
    data: List[dict] = _load(_F_HEALTH, [])
    now = _ts()
    found = False
    for rec in data:
        if rec.get("entity_type") == entity_type and rec.get("entity_name") == entity_name:
            rec["status"]             = status
            rec["last_checked_ist"]   = now
            rec["error_code"]         = error_code
            rec["details"]            = details
            rec["auto_fix_attempted"] = auto_fix_attempted
            if status == "OK":
                rec["last_ok_ist"] = now
            found = True
            break
    if not found:
        data.append({
            "entity_type":       entity_type,
            "entity_name":       entity_name,
            "status":            status,
            "last_checked_ist":  now,
            "last_ok_ist":       now if status == "OK" else "",
            "error_code":        error_code,
            "auto_fix_attempted": auto_fix_attempted,
            "details":           details,
        })
    _save(_F_HEALTH, data)


# ═══════════════════════════════════════════════════════════════════════════════
# Circuit Breaker — resilient API call wrapper
# ═══════════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    Circuit breaker pattern for external API calls.
    States: CLOSED (normal) → OPEN (blocking) → HALF_OPEN (testing).
    """
    CLOSED    = "CLOSED"
    OPEN      = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, name: str, failure_threshold: int = 5,
                 recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN and self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._state = self.HALF_OPEN
            return self._state

    def call(self, func, *args, **kwargs):
        """Execute func through circuit breaker protection."""
        st = self.state
        if st == self.OPEN:
            AuditLogger.warn("CircuitBreaker",
                             f"[{self.name}] OPEN — call blocked")
            raise ConnectionError(
                f"Circuit breaker {self.name} is OPEN — too many failures")

        try:
            result = func(*args, **kwargs)
            with self._lock:
                if self._state == self.HALF_OPEN:
                    AuditLogger.info("CircuitBreaker",
                                     f"[{self.name}] recovered → CLOSED")
                self._state = self.CLOSED
                self._failure_count = 0
            return result
        except Exception as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()
                if self._failure_count >= self.failure_threshold:
                    self._state = self.OPEN
                    AuditLogger.error("CircuitBreaker",
                                      f"[{self.name}] → OPEN after "
                                      f"{self._failure_count} failures")
            raise

    def reset(self):
        """Manually reset to CLOSED."""
        with self._lock:
            self._state = self.CLOSED
            self._failure_count = 0
            self._last_failure_time = None


class HealthCheckEngine:
    """
    Runs health checks across 7 entity types:
      api, data, calculation, export, scheduler, page, widget
    Each check writes to sre_health_status.json.
    """

    # ── 1. API Health ──────────────────────────────────────────────────────────
    @staticmethod
    def check_apis() -> List[dict]:
        """
        Read api_stats.json (written by api_manager).
        Flag FAIL if consecutive_failures >= threshold.
        Flag WARN if avg_latency_ms > warn threshold.
        """
        cfg = _cfg()
        thr = cfg["alert_thresholds"]
        stats: dict = _load(_F_STATS, {})
        results = []

        for api_id, s in stats.items():
            consec_fail = s.get("consecutive_failures", 0)
            latency     = s.get("avg_latency_ms", 0)
            status_raw  = s.get("status", "Unknown")
            calls       = s.get("calls", 0)
            failures    = s.get("failures", 0)
            error_rate  = (failures / calls * 100) if calls > 0 else 0

            if status_raw == "Fail" or consec_fail >= thr["consecutive_fail_crit"]:
                status = "FAIL"
                err    = f"Consecutive failures: {consec_fail}  Error rate: {error_rate:.1f}%"
            elif (consec_fail >= thr["consecutive_fail_warn"]
                  or latency > thr["api_latency_warn_ms"]
                  or error_rate > thr["api_error_rate_warn_pct"]):
                status = "WARN"
                err    = f"Latency {latency}ms  Error rate {error_rate:.1f}%  ConsecFail {consec_fail}"
            else:
                status = "OK"
                err    = ""

            _upsert_health("api", api_id, status, error_code=err,
                           details=f"calls={calls} failures={failures} latency={latency}ms")
            results.append({"entity": api_id, "status": status, "details": err})

        AuditLogger.info("HealthCheckEngine", f"API health checked: {len(results)} APIs")
        return results

    # ── 2. Data Quality Health ─────────────────────────────────────────────────
    @staticmethod
    def check_data_quality() -> List[dict]:
        """
        Validate live_prices.json and api_cache.json for:
        - Missing/null values
        - Stale data (timestamp old)
        - Out-of-range numeric values
        """
        cfg = _cfg()
        ps  = cfg["pricing_sanity"]
        results = []

        # Check live_prices.json
        prices: dict = _load(_F_PRICES, {})
        price_issues = []
        expected_keys = ["DRUM_MUMBAI_VG30", "DRUM_KANDLA_VG30"]
        for key in expected_keys:
            val = prices.get(key)
            if val is None:
                price_issues.append(f"Missing: {key}")
            elif not isinstance(val, (int, float)):
                price_issues.append(f"Non-numeric: {key}={val}")
            elif val < ps["min_bitumen_inr_per_mt"] or val > ps["max_bitumen_inr_per_mt"]:
                price_issues.append(
                    f"Out of range: {key}={format_inr(val)} "
                    f"(expected {format_inr(ps['min_bitumen_inr_per_mt'])}–{format_inr(ps['max_bitumen_inr_per_mt'])})"
                )

        if price_issues:
            status = "WARN"
            detail = "; ".join(price_issues)
        else:
            status = "OK"
            detail = f"{len(prices)} price keys OK"
        _upsert_health("data", "live_prices", status, details=detail)
        results.append({"entity": "live_prices", "status": status, "details": detail})

        # Check api_cache.json for staleness
        cache: dict = _load(_F_CACHE, {})
        stale_warn_sec  = cfg["alert_thresholds"]["stale_data_warn_hours"]  * 3600
        stale_crit_sec  = cfg["alert_thresholds"]["stale_data_crit_hours"]  * 3600
        now_ts = time.time()
        stale_warn_list, stale_crit_list = [], []

        for api_id, entry in cache.items():
            cached_ts = entry.get("timestamp", 0) if isinstance(entry, dict) else 0
            age_sec = now_ts - cached_ts
            if age_sec > stale_crit_sec:
                stale_crit_list.append(f"{api_id}({age_sec/3600:.1f}h)")
            elif age_sec > stale_warn_sec:
                stale_warn_list.append(f"{api_id}({age_sec/3600:.1f}h)")

        if stale_crit_list:
            cache_status = "FAIL"
            cache_detail = f"STALE CRITICAL: {', '.join(stale_crit_list[:5])}"
        elif stale_warn_list:
            cache_status = "WARN"
            cache_detail = f"Stale warn: {', '.join(stale_warn_list[:5])}"
        else:
            cache_status = "OK"
            cache_detail = f"{len(cache)} cached entries fresh"
        _upsert_health("data", "api_cache_freshness", cache_status, details=cache_detail)
        results.append({"entity": "api_cache_freshness", "status": cache_status, "details": cache_detail})

        # ── Anomaly detection (if anomaly_engine is available) ──────────────
        try:
            from anomaly_engine import detect_price_anomalies
            anomalies = detect_price_anomalies()
            if anomalies:
                anom_detail = f"{len(anomalies)} price anomalies detected"
                _upsert_health("data", "price_anomalies", "WARN", details=anom_detail)
                results.append({"entity": "price_anomalies", "status": "WARN",
                                "details": anom_detail})
            else:
                _upsert_health("data", "price_anomalies", "OK",
                               details="No anomalies detected")
                results.append({"entity": "price_anomalies", "status": "OK",
                                "details": "No anomalies detected"})
        except ImportError:
            pass  # anomaly_engine not available (ML packages not installed)
        except Exception:
            pass  # graceful fallback

        AuditLogger.info("HealthCheckEngine", f"Data quality checked: {len(results)} entities")
        return results

    # ── 3. Calculation Health ──────────────────────────────────────────────────
    @staticmethod
    def check_calculations(sample_calcs: Optional[List[dict]] = None) -> List[dict]:
        """
        Validate recent calculation outputs for NaN, Inf, negative prices, impossible margins.
        `sample_calcs` is a list of {'name': str, 'value': float, 'unit': str} dicts.
        If None, reads last known from cache.
        """
        cfg = _cfg()
        ps  = cfg["pricing_sanity"]
        results = []

        if sample_calcs is None:
            # Pull from cache: check brent, usdinr
            cache = _load(_F_CACHE, {})
            sample_calcs = []
            for key, rule in [
                ("brent",  {"min": ps["min_brent_usd"],  "max": ps["max_brent_usd"],  "unit": "USD/bbl"}),
                ("wti",    {"min": ps["min_brent_usd"],  "max": ps["max_brent_usd"],  "unit": "USD/bbl"}),
                ("usdinr", {"min": ps["min_usdinr"],     "max": ps["max_usdinr"],      "unit": "₹/USD"}),
            ]:
                entry = cache.get(key, {})
                if isinstance(entry, dict):
                    val = (entry.get("data") or {}).get("current")
                    if val is not None:
                        sample_calcs.append({"name": key, "value": float(val), **rule})

        for item in sample_calcs:
            name  = item.get("name", "unknown")
            value = item.get("value")
            vmin  = item.get("min", -1e9)
            vmax  = item.get("max",  1e9)
            unit  = item.get("unit", "")

            if value is None:
                status, detail = "WARN", f"{name}: no value"
            elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                status, detail = "FAIL", f"{name}: NaN/Inf detected"
            elif value < vmin or value > vmax:
                status, detail = "WARN", f"{name}={value:.2f}{unit} outside [{vmin},{vmax}]"
            else:
                status, detail = "OK", f"{name}={value:.2f} {unit} OK"

            _upsert_health("calculation", name, status, details=detail)
            results.append({"entity": name, "status": status, "details": detail})

        AuditLogger.info("HealthCheckEngine", f"Calculation health: {len(results)} checks")
        return results

    # ── 4. Export Health ───────────────────────────────────────────────────────
    @staticmethod
    def check_export() -> dict:
        """
        Check for recently generated PDFs in PDF archive paths.
        Detect zero-byte or too-small files as 'blank PDF'.
        """
        cfg = _cfg()
        min_bytes = cfg["export"]["min_pdf_size_bytes"]

        pdf_dirs = [
            BASE / "pdf_exports",
            BASE / "exports",
            BASE / "reports",
        ]
        found_pdfs = []
        blank_pdfs = []

        for d in pdf_dirs:
            if d.exists():
                for p in d.glob("*.pdf"):
                    sz = p.stat().st_size
                    found_pdfs.append(p.name)
                    if sz < min_bytes:
                        blank_pdfs.append(f"{p.name}({sz}B)")

        if blank_pdfs:
            status  = "FAIL"
            detail  = f"Blank/tiny PDFs: {', '.join(blank_pdfs)}"
        elif found_pdfs:
            status  = "OK"
            detail  = f"{len(found_pdfs)} PDFs found, all ≥{min_bytes}B"
        else:
            status  = "OK"
            detail  = "No PDF exports yet (normal on first run)"

        _upsert_health("export", "pdf_export", status, details=detail)
        AuditLogger.info("HealthCheckEngine", f"Export health: {status} — {detail}")
        return {"entity": "pdf_export", "status": status, "details": detail}

    # ── 5. Scheduler Health ────────────────────────────────────────────────────
    @staticmethod
    def check_scheduler() -> dict:
        """
        Read api_health_log.json to determine last auto health-check run time.
        Flag WARN if overdue.
        """
        cfg  = _cfg()
        thr  = cfg["alert_thresholds"]
        log: List[dict] = _load(_F_HLTH_LOG, [])

        if not log:
            _upsert_health("scheduler", "auto_health_check", "WARN",
                           details="No health log records found")
            return {"entity": "scheduler", "status": "WARN", "details": "No records"}

        last_rec   = log[-1]
        last_ts_str = last_rec.get("datetime_ist", "")

        try:
            # Parse "DD-MM-YYYY HH:MM:SS IST"
            last_dt = datetime.datetime.strptime(last_ts_str.replace(" IST", ""),
                                                 "%Y-%m-%d %H:%M:%S")
            last_dt = IST.localize(last_dt)
            age_min = (_now() - last_dt).total_seconds() / 60
        except Exception:
            age_min = 9999

        if age_min > thr["scheduler_overdue_crit_min"]:
            status = "FAIL"
            detail = f"Last run {age_min:.0f} min ago — OVERDUE (crit>{thr['scheduler_overdue_crit_min']}min)"
        elif age_min > thr["scheduler_overdue_warn_min"]:
            status = "WARN"
            detail = f"Last run {age_min:.0f} min ago — overdue (warn>{thr['scheduler_overdue_warn_min']}min)"
        else:
            status = "OK"
            detail = f"Last run {age_min:.1f} min ago — on schedule"

        _upsert_health("scheduler", "auto_health_check", status, details=detail)
        AuditLogger.info("HealthCheckEngine", f"Scheduler health: {status} — {detail}")
        return {"entity": "auto_health_check", "status": status, "details": detail}

    # ── 6. Error Rate Health ───────────────────────────────────────────────────
    @staticmethod
    def check_error_rates() -> dict:
        """Read api_error_log.json and compute open error rate and P0 count."""
        errors: List[dict] = _load(_F_ERROR_LOG, [])
        # Recent 100 entries
        recent = errors[-100:] if len(errors) > 100 else errors
        p0_open = sum(1 for e in recent
                      if e.get("severity") == "P0" and e.get("status") == "Open")
        p1_open = sum(1 for e in recent
                      if e.get("severity") == "P1" and e.get("status") == "Open")
        total   = len(recent)

        if p0_open > 0:
            status = "FAIL"
            detail = f"{p0_open} P0 open, {p1_open} P1 open in last {total} records"
        elif p1_open >= 5:
            status = "WARN"
            detail = f"{p1_open} P1 open errors (threshold ≥5)"
        else:
            status = "OK"
            detail = f"p0_open={p0_open} p1_open={p1_open} in last {total} records"

        _upsert_health("errors", "error_log", status, details=detail)
        return {"entity": "error_log", "status": status, "details": detail}

    # ── 7. Resource Monitoring (CPU, Memory, Disk) ──────────────────────────
    @staticmethod
    def check_resources() -> dict:
        """Check system resources via psutil (if available)."""
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/") if not hasattr(psutil, 'disk_usage') else psutil.disk_usage(".")

            alerts = []
            status = "OK"
            if cpu_pct > 90:
                alerts.append(f"CPU critical: {cpu_pct}%")
                status = "FAIL"
            elif cpu_pct > 75:
                alerts.append(f"CPU high: {cpu_pct}%")
                status = "WARN"

            if mem.percent > 85:
                alerts.append(f"Memory critical: {mem.percent}%")
                status = "FAIL"
            elif mem.percent > 70:
                alerts.append(f"Memory high: {mem.percent}%")
                if status != "FAIL":
                    status = "WARN"

            if disk.percent > 90:
                alerts.append(f"Disk critical: {disk.percent}%")
                status = "FAIL"

            detail = (f"CPU={cpu_pct}% Mem={mem.percent}% Disk={disk.percent}% "
                      f"MemUsed={mem.used // (1024**2)}MB")
            _upsert_health("resource", "system_resources", status, details=detail)
            return {
                "entity": "system_resources", "status": status,
                "cpu_pct": cpu_pct, "memory_pct": mem.percent,
                "disk_pct": disk.percent, "memory_used_mb": mem.used // (1024**2),
                "alerts": alerts, "details": detail,
            }
        except ImportError:
            return {"entity": "system_resources", "status": "OK",
                    "details": "psutil not installed — resource monitoring disabled"}
        except Exception as e:
            return {"entity": "system_resources", "status": "OK",
                    "details": f"Resource check error: {e}"}

    # ── 8. AI Provider Health ─────────────────────────────────────────────────
    @staticmethod
    def check_ai_providers() -> List[dict]:
        """Check health of all AI providers from ai_fallback_engine."""
        results = []
        try:
            from ai_fallback_engine import PROVIDER_CHAIN, get_provider_health, _is_provider_disabled
            for p in PROVIDER_CHAIN:
                pid = p["id"]
                health = get_provider_health(pid)
                sr = health.get("success_rate", 100)
                disabled = health.get("is_disabled", False)
                latency = health.get("avg_latency_ms", 0)
                total = health.get("total_calls", 0)

                if disabled:
                    status = "FAIL"
                    detail = f"{p['name']} auto-disabled (error rate too high)"
                elif total >= 5 and sr < 50:
                    status = "FAIL"
                    detail = f"{p['name']} success_rate={sr}% (<50%)"
                elif total >= 5 and sr < 80:
                    status = "WARN"
                    detail = f"{p['name']} success_rate={sr}% (<80%)"
                elif latency > 5000:
                    status = "WARN"
                    detail = f"{p['name']} avg_latency={latency:.0f}ms (>5s)"
                else:
                    status = "OK"
                    detail = (f"{p['name']} OK — {sr}% success, "
                              f"{latency:.0f}ms avg, {total} calls")

                _upsert_health("ai_provider", pid, status, details=detail)
                results.append({
                    "entity": pid, "name": p["name"], "status": status,
                    "success_rate": sr, "avg_latency_ms": latency,
                    "total_calls": total, "is_disabled": disabled,
                    "details": detail,
                })
        except ImportError:
            results.append({"entity": "ai_providers", "status": "OK",
                            "details": "ai_fallback_engine not available"})
        except Exception as e:
            results.append({"entity": "ai_providers", "status": "WARN",
                            "details": f"AI provider check error: {e}"})
        return results

    # ── Full run ───────────────────────────────────────────────────────────────
    @classmethod
    def run_all(cls) -> dict:
        """Run all health checks. Returns summary dict."""
        results = {
            "timestamp_ist": _ts(),
            "api_health":    cls.check_apis(),
            "data_health":   cls.check_data_quality(),
            "calc_health":   cls.check_calculations(),
            "export_health": cls.check_export(),
            "sched_health":  cls.check_scheduler(),
            "error_rates":   cls.check_error_rates(),
            "resources":     cls.check_resources(),
            "ai_provider_health": cls.check_ai_providers(),
        }

        # Aggregate summary
        all_statuses = []
        for key in ("api_health", "data_health", "calc_health", "ai_provider_health"):
            for r in results[key]:
                all_statuses.append(r["status"])
        for key in ("export_health", "sched_health", "error_rates", "resources"):
            all_statuses.append(results[key]["status"])

        total  = len(all_statuses)
        fails  = all_statuses.count("FAIL")
        warns  = all_statuses.count("WARN")
        oks    = all_statuses.count("OK")
        health_pct = int(oks / total * 100) if total else 0

        results["summary"] = {
            "total": total, "ok": oks, "warn": warns, "fail": fails,
            "health_pct": health_pct,
            "overall": "FAIL" if fails > 0 else ("WARN" if warns > 0 else "OK"),
        }

        # Save metrics snapshot
        _append(_F_METRICS, {"timestamp_ist": _ts(), **results["summary"]}, max_records=500)
        AuditLogger.info("HealthCheckEngine",
                         f"Full health run: {health_pct}% OK  fail={fails} warn={warns}")
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — SELF-HEALING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SelfHealEngine:
    """
    Auto-fix engine for safe reversible actions only.
    NEVER silently changes business-critical numbers.
    All changes logged to api_change_log.json (existing audit) + sre_audit_log.json.
    """

    # ── A. API self-heal: trigger retry via api_manager ───────────────────────
    @staticmethod
    def heal_api(api_id: str) -> dict:
        """Force re-fetch with exponential back-off. Logs result."""
        try:
            from api_manager import fetch_api_data, log_error, log_change
        except ImportError:
            return {"api_id": api_id, "healed": False, "reason": "api_manager unavailable"}

        cfg      = _cfg()
        backoffs = cfg["auto_heal"]["retry_backoff_sec"]
        result   = None

        for i, delay in enumerate(backoffs):
            AuditLogger.info("SelfHealEngine", f"API heal attempt {i+1}/{len(backoffs)}: {api_id}")
            result = fetch_api_data(api_id, force=True)
            if result is not None:
                log_change(
                    component=api_id,
                    what_changed="auto_heal_fetch",
                    old_value="FAIL",
                    new_value="OK",
                    reason=f"SRE auto-heal attempt {i+1} succeeded",
                    trigger="Auto",
                    affected_api=api_id,
                )
                AuditLogger.info("SelfHealEngine", f"API {api_id} healed on attempt {i+1}")
                _upsert_health("api", api_id, "OK",
                               details=f"Healed on attempt {i+1}", auto_fix_attempted="Y")
                return {"api_id": api_id, "healed": True, "attempt": i+1}
            if i < len(backoffs) - 1:
                time.sleep(delay)

        # All retries failed → log error
        AuditLogger.error("SelfHealEngine", f"API {api_id} heal FAILED after {len(backoffs)} attempts")
        try:
            log_error(
                api_id=api_id,
                component="SelfHealEngine",
                error_type="Heal Failed",
                message=f"Auto-heal exhausted {len(backoffs)} retries for {api_id}",
                severity="P1",
                auto_fixed=False,
                manual_required=True,
            )
        except Exception:
            pass
        _upsert_health("api", api_id, "FAIL",
                       error_code="HEAL_EXHAUSTED",
                       details=f"All {len(backoffs)} heal attempts failed",
                       auto_fix_attempted="Y")
        return {"api_id": api_id, "healed": False, "attempts": len(backoffs)}

    # ── B. Calculation self-heal: revert to last valid ────────────────────────
    @staticmethod
    def heal_calculation(name: str, bad_value: Any, last_valid: Any, reason: str) -> dict:
        """
        Log the bad value, restore the last valid.
        NEVER silently replaces — always writes to change log.
        Returns dict with old, new, reason.
        """
        AuditLogger.warn(
            "SelfHealEngine",
            f"Calc heal: {name} bad={bad_value} → restoring last_valid={last_valid}",
        )
        try:
            from api_manager import log_change
            log_change(
                component="Calculation",
                what_changed=name,
                old_value=str(bad_value),
                new_value=str(last_valid),
                reason=f"SRE auto-heal: {reason}",
                trigger="Auto",
                affected_tab="Calculation Engine",
            )
        except Exception:
            pass
        _upsert_health("calculation", name, "WARN",
                       details=f"Reverted bad value ({bad_value}) → last_valid ({last_valid})",
                       auto_fix_attempted="Y")
        return {"name": name, "old": bad_value, "new": last_valid, "healed": True, "reason": reason}

    # ── C. Data self-heal: quarantine bad row ─────────────────────────────────
    @staticmethod
    def quarantine_data(entity: str, field: str, bad_value: Any, reason: str) -> None:
        """Tag suspicious data as 'needs review' without deleting."""
        record = {
            "quarantine_id":   _gen_id("QRN"),
            "timestamp_ist":   _ts(),
            "entity":          entity,
            "field":           field,
            "bad_value":       str(bad_value),
            "reason":          reason,
            "status":          "Needs Review",
        }
        _append(BASE / "sre_quarantine_log.json", record, max_records=1000)
        AuditLogger.warn("SelfHealEngine", f"Quarantined: {entity}.{field}={bad_value} — {reason}")

    # ── D. Export self-heal: log blank PDF event ──────────────────────────────
    @staticmethod
    def heal_export(export_name: str, file_path: str, size_bytes: int) -> dict:
        """
        Called when a generated PDF is found to be blank/too small.
        Logs the issue. Cannot auto-regenerate (needs UI context).
        Returns guidance for caller.
        """
        AuditLogger.error(
            "SelfHealEngine",
            f"Blank PDF detected: {export_name} ({size_bytes}B) at {file_path}",
        )
        _upsert_health("export", "pdf_export", "FAIL",
                       error_code="BLANK_PDF",
                       details=f"{export_name}: {size_bytes}B — too small",
                       auto_fix_attempted="Y")
        return {
            "export_name":  export_name,
            "size_bytes":   size_bytes,
            "action":       "Re-render charts then retry export",
            "fallback":     "Export table-only version as backup",
            "healed":       False,  # requires UI re-trigger
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — SMART ALERT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SmartAlertEngine:
    """
    Generates P0 / P1 / P2 alerts from health data.
    Deduplication: same entity not re-alerted within suppress_same_alert_min minutes.
    Stores alerts in sre_alerts.json.
    """

    @staticmethod
    def _is_suppressed(entity: str, severity: str) -> bool:
        """Return True if this entity/severity was alerted recently."""
        cfg = _cfg()
        suppress_min = cfg["auto_heal"]["suppress_same_alert_min"]
        alerts: List[dict] = _load(_F_ALERTS, [])
        cutoff = _now() - datetime.timedelta(minutes=suppress_min)

        for a in reversed(alerts):
            if a.get("entity") != entity:
                continue
            if a.get("severity") != severity:
                continue
            if a.get("status") in ("Resolved", "Suppressed"):
                continue
            ts_str = a.get("triggered_on_ist", "")
            try:
                ts_dt = datetime.datetime.strptime(ts_str.replace(" IST", ""),
                                                   "%Y-%m-%d %H:%M:%S")
                ts_dt = IST.localize(ts_dt)
                if ts_dt > cutoff:
                    return True  # within suppress window
            except Exception:
                pass
        return False

    @classmethod
    def fire(
        cls,
        severity: str,       # P0 / P1 / P2
        entity: str,
        what_happened: str,
        where: str,
        why: str,
        auto_fix_result: str = "",
        action_needed: str = "",
    ) -> Optional[str]:
        """Create a new alert unless suppressed. Returns alert_id or None."""
        if cls._is_suppressed(entity, severity):
            return None

        alert_id = _gen_id("ALT")
        record = {
            "alert_id":         alert_id,
            "severity":         severity,
            "entity":           entity,
            "message":          what_happened,
            "what_happened":    what_happened,
            "where":            where,
            "why":              why,
            "triggered_on_ist": _ts(),
            "resolved_on_ist":  None,
            "status":           "Open",
            "auto_fix_result":  auto_fix_result,
            "action_needed":    action_needed,
            "details_json":     json.dumps({
                "entity": entity, "where": where, "why": why,
            }),
        }
        _append(_F_ALERTS, record, max_records=2000)
        AuditLogger.warn("SmartAlertEngine",
                         f"[{severity}] {entity}: {what_happened[:80]}")
        return alert_id

    @classmethod
    def resolve(cls, alert_id: str, resolution: str = "Resolved") -> bool:
        alerts: List[dict] = _load(_F_ALERTS, [])
        for a in alerts:
            if a.get("alert_id") == alert_id:
                a["status"]          = resolution
                a["resolved_on_ist"] = _ts()
                _save(_F_ALERTS, alerts)
                return True
        return False

    @classmethod
    def from_health_results(cls, health_results: dict) -> int:
        """
        Translate health check results into alerts automatically.
        Returns number of new alerts fired.
        """
        fired = 0

        # API health
        for r in health_results.get("api_health", []):
            entity = r["entity"]
            if r["status"] == "FAIL":
                alert_id = cls.fire(
                    "P0", entity,
                    what_happened=f"API {entity} is DOWN",
                    where=f"API Layer / {entity}",
                    why=r.get("details", ""),
                    action_needed="Check API endpoint, rotate if needed, or activate fallback manually",
                )
                if alert_id:
                    fired += 1
            elif r["status"] == "WARN":
                alert_id = cls.fire(
                    "P1", entity,
                    what_happened=f"API {entity} degraded performance",
                    where=f"API Layer / {entity}",
                    why=r.get("details", ""),
                    action_needed="Monitor latency, consider fallback if worsens",
                )
                if alert_id:
                    fired += 1

        # Data health
        for r in health_results.get("data_health", []):
            entity = r["entity"]
            if r["status"] == "FAIL":
                cls.fire("P1", entity,
                         what_happened=f"Data quality FAIL: {entity}",
                         where="Data Layer",
                         why=r.get("details", ""),
                         action_needed="Re-fetch or manually validate data")
                fired += 1
            elif r["status"] == "WARN":
                cls.fire("P2", entity,
                         what_happened=f"Data quality WARN: {entity}",
                         where="Data Layer",
                         why=r.get("details", ""),
                         action_needed="Review data freshness")
                fired += 1

        # Calculation health
        for r in health_results.get("calc_health", []):
            if r["status"] == "FAIL":
                cls.fire("P1", r["entity"],
                         what_happened=f"Calculation invalid: {r['entity']}",
                         where="Calculation Engine",
                         why=r.get("details", ""),
                         action_needed="Review formula inputs and validate outputs")
                fired += 1
            elif r["status"] == "WARN":
                cls.fire("P2", r["entity"],
                         what_happened=f"Calculation warning: {r['entity']}",
                         where="Calculation Engine",
                         why=r.get("details", ""),
                         action_needed="Validate range boundaries")
                fired += 1

        # Export health
        exp = health_results.get("export_health", {})
        if exp.get("status") == "FAIL":
            cls.fire("P0", "pdf_export",
                     what_happened="PDF export producing blank/corrupt files",
                     where="Export Engine",
                     why=exp.get("details", ""),
                     action_needed="Re-render dashboard, retry export, check print CSS")
            fired += 1

        # Scheduler health
        sched = health_results.get("sched_health", {})
        if sched.get("status") == "FAIL":
            cls.fire("P0", "auto_health_scheduler",
                     what_happened="Health check scheduler is OVERDUE",
                     where="Scheduler / api_manager.start_auto_health()",
                     why=sched.get("details", ""),
                     action_needed="Restart dashboard process to reinitialise scheduler")
            fired += 1
        elif sched.get("status") == "WARN":
            cls.fire("P1", "auto_health_scheduler",
                     what_happened="Health check scheduler running late",
                     where="Scheduler",
                     why=sched.get("details", ""),
                     action_needed="Monitor; if persists restart app")
            fired += 1

        # Error rates
        err = health_results.get("error_rates", {})
        if err.get("status") == "FAIL":
            cls.fire("P0", "error_log",
                     what_happened="P0 errors open in system — immediate attention needed",
                     where="Error Log / Bug Tracker",
                     why=err.get("details", ""),
                     action_needed="Open Bug Tracker → filter P0 → resolve manually")
            fired += 1

        return fired

    @classmethod
    def get_open_alerts(cls, severity: Optional[str] = None) -> List[dict]:
        alerts: List[dict] = _load(_F_ALERTS, [])
        open_alerts = [a for a in alerts if a.get("status") == "Open"]
        if severity:
            open_alerts = [a for a in open_alerts if a.get("severity") == severity]
        return list(reversed(open_alerts))  # newest first

    @classmethod
    def get_all_alerts(cls, n: int = 200) -> List[dict]:
        alerts: List[dict] = _load(_F_ALERTS, [])
        return list(reversed(alerts[-n:]))  # newest first


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — BUG AUTO-CREATOR
# ═══════════════════════════════════════════════════════════════════════════════

class BugAutoCreator:
    """
    Creates structured bugs when auto-heal fails.
    Lifecycle: Open → In Progress → Fixed → Verified
    """

    @classmethod
    def create(
        cls,
        severity: str,          # P0 / P1 / P2
        entity: str,
        title: str,
        component_owner: str,   # frontend / backend / data / scheduler
        reproduction_steps: List[str],
        logs_attached: Optional[List[str]] = None,
        auto_created: bool = True,
    ) -> str:
        """Create a new bug. Returns bug_id."""
        bug_id = _gen_id("BUG")
        record = {
            "bug_id":              bug_id,
            "severity":            severity,
            "entity":              entity,
            "title":               title,
            "component_owner":     component_owner,
            "reproduction_steps":  reproduction_steps,
            "logs_attached":       logs_attached or [],
            "status":              "Open",
            "auto_created":        auto_created,
            "created_ist":         _ts(),
            "updated_ist":         _ts(),
        }
        _append(_F_BUGS, record, max_records=2000)
        AuditLogger.error("BugAutoCreator",
                          f"Bug created [{severity}] {bug_id}: {title}")
        return bug_id

    @classmethod
    def update_status(cls, bug_id: str, new_status: str) -> bool:
        """Update bug lifecycle status."""
        valid = {"Open", "In Progress", "Fixed", "Verified", "Suppressed"}
        if new_status not in valid:
            return False
        bugs: List[dict] = _load(_F_BUGS, [])
        for b in bugs:
            if b.get("bug_id") == bug_id:
                b["status"]      = new_status
                b["updated_ist"] = _ts()
                _save(_F_BUGS, bugs)
                AuditLogger.info("BugAutoCreator",
                                 f"Bug {bug_id} status → {new_status}")
                return True
        return False

    @classmethod
    def from_failed_heal(cls, api_id: str, heal_result: dict, alert_id: str = "") -> str:
        """Auto-create a bug when a heal attempt fails."""
        attempts = heal_result.get("attempts", 3)
        steps = [
            f"1. API '{api_id}' returned FAIL status in api_stats.json",
            f"2. SelfHealEngine attempted {attempts} retries with exponential back-off",
            f"3. All retry attempts failed — fallback also failed or unavailable",
            f"4. Alert {alert_id} was raised (severity: P0/P1)",
            f"5. Bug auto-created at {_ts()}",
            "6. Manual investigation required — check endpoint, key, rate-limit",
        ]
        return cls.create(
            severity="P1",
            entity=api_id,
            title=f"API {api_id} unresolvable after {attempts} auto-heal attempts",
            component_owner="backend",
            reproduction_steps=steps,
            logs_attached=[str(_F_ERROR_LOG), str(_F_HLTH_LOG)],
        )

    @classmethod
    def get_bugs(cls, status: Optional[str] = None, severity: Optional[str] = None) -> List[dict]:
        bugs: List[dict] = _load(_F_BUGS, [])
        if status:
            bugs = [b for b in bugs if b.get("status") == status]
        if severity:
            bugs = [b for b in bugs if b.get("severity") == severity]
        return list(reversed(bugs))


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — CONFLICT / OVERWRITE PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════

class ConflictProtector:
    """
    Detects when auto or manual data would overwrite an existing value.
    Always keeps both versions + audit trail.
    Never silently overwrites.
    """

    @classmethod
    def check_and_log(
        cls,
        entity_id: str,
        field: str,
        current_value: Any,
        new_value: Any,
        actor: str,          # "system" or "user:<name>"
        source: str,         # "auto_heal" / "manual_entry" / "api_fetch"
    ) -> dict:
        """
        Compare current_value vs new_value.
        If different: log to change_history + conflict_log (if actor conflict).
        Returns {'conflict': bool, 'conflict_id': str or None}.
        """
        # Log to change_history always
        ch_record = {
            "change_id":     _gen_id("CHG"),
            "timestamp_ist": _ts(),
            "entity":        entity_id,
            "field":         field,
            "old_value":     str(current_value),
            "new_value":     str(new_value),
            "actor":         actor,
            "source":        source,
        }
        _append(BASE / "sre_change_history.json", ch_record, max_records=5000)

        # Detect conflict: manual entry trying to overwrite auto, or vice versa
        is_conflict = False
        conflict_id = None

        if str(current_value) != str(new_value):
            # Check if last entry for same entity/field was by a different actor type
            hist: List[dict] = _load(BASE / "sre_change_history.json", [])
            prev = [r for r in reversed(hist[:-1])  # exclude the one we just wrote
                    if r.get("entity") == entity_id and r.get("field") == field]
            if prev:
                last_actor = prev[0].get("actor", "")
                last_source = prev[0].get("source", "")
                # Conflict: last was manual, new is auto (or vice versa)
                if (("user" in last_actor and "system" in actor)
                        or ("system" in last_actor and "user" in actor)):
                    is_conflict = True

            if is_conflict:
                conflict_id = _gen_id("CONF")
                conf_record = {
                    "conflict_id":   conflict_id,
                    "timestamp_ist": _ts(),
                    "entity_id":     entity_id,
                    "field":         field,
                    "auto_value":    str(new_value) if "system" in actor else str(current_value),
                    "manual_value":  str(current_value) if "system" in actor else str(new_value),
                    "status":        "Pending",
                    "resolution":    "",
                    "resolved_by":   "",
                }
                _append(_F_CONFLICT, conf_record, max_records=1000)
                AuditLogger.warn(
                    "ConflictProtector",
                    f"Conflict: {entity_id}.{field} auto={conf_record['auto_value']} "
                    f"vs manual={conf_record['manual_value']}",
                )

        return {"conflict": is_conflict, "conflict_id": conflict_id}

    @classmethod
    def get_pending_conflicts(cls) -> List[dict]:
        data: List[dict] = _load(_F_CONFLICT, [])
        return [r for r in reversed(data) if r.get("status") == "Pending"]

    @classmethod
    def resolve_conflict(cls, conflict_id: str, keep: str, resolved_by: str) -> bool:
        """Mark conflict resolved. `keep` = 'auto' or 'manual'."""
        data: List[dict] = _load(_F_CONFLICT, [])
        for r in data:
            if r.get("conflict_id") == conflict_id:
                r["status"]      = "Resolved"
                r["resolution"]  = f"Kept: {keep}"
                r["resolved_by"] = resolved_by
                _save(_F_CONFLICT, data)
                return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# DATA VALIDATOR (inline call anywhere)
# ═══════════════════════════════════════════════════════════════════════════════

class DataValidator:
    """
    Validate individual values or dicts before saving.
    Returns (is_valid: bool, issues: List[str]).
    """

    @staticmethod
    def validate_price(value: Any, label: str = "price",
                       min_inr: float = 1000.0, max_inr: float = 200000.0
                       ) -> tuple:
        issues = []
        if value is None:
            issues.append(f"{label}: None value")
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            issues.append(f"{label}: NaN/Inf")
        elif not isinstance(value, (int, float)):
            issues.append(f"{label}: non-numeric ({type(value).__name__})")
        elif value < min_inr:
            issues.append(f"{label}={format_inr(value)} below min {format_inr(min_inr)}")
        elif value > max_inr:
            issues.append(f"{label}={format_inr(value)} above max {format_inr(max_inr)}")
        return (len(issues) == 0, issues)

    @staticmethod
    def validate_pct(value: Any, label: str = "pct",
                     min_pct: float = -100.0, max_pct: float = 500.0) -> tuple:
        issues = []
        if value is None:
            issues.append(f"{label}: None")
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            issues.append(f"{label}: NaN/Inf")
        elif not isinstance(value, (int, float)):
            issues.append(f"{label}: non-numeric")
        elif value < min_pct or value > max_pct:
            issues.append(f"{label}={value:.2f}% out of [{min_pct},{max_pct}]%")
        return (len(issues) == 0, issues)

    @staticmethod
    def validate_live_prices(prices_dict: dict) -> tuple:
        """Validate an entire live_prices dict."""
        cfg    = _cfg()
        ps     = cfg["pricing_sanity"]
        issues = []
        for key, val in prices_dict.items():
            ok, errs = DataValidator.validate_price(
                val, key,
                min_inr=ps["min_bitumen_inr_per_mt"],
                max_inr=ps["max_bitumen_inr_per_mt"],
            )
            if not ok:
                issues.extend(errs)
        return (len(issues) == 0, issues)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ExportValidator:
    """
    Call before and after PDF generation to ensure non-blank output.
    """

    @staticmethod
    def validate_before_export(content_items: List[Any]) -> tuple:
        """
        Pre-export check: ensure there is actual content.
        `content_items` is a list of items (rows, chart data, etc.) to be exported.
        Returns (ok: bool, issues: List[str]).
        """
        issues = []
        if not content_items:
            issues.append("No content items to export — export will be blank")
        elif len(content_items) < 1:
            issues.append("Export content is empty")
        return (len(issues) == 0, issues)

    @staticmethod
    def validate_after_export(file_path: str) -> tuple:
        """
        Post-export check: ensure file exists and is above minimum size.
        Returns (ok: bool, issues: List[str]).
        """
        cfg    = _cfg()
        min_sz = cfg["export"]["min_pdf_size_bytes"]
        issues = []
        p      = Path(file_path)

        if not p.exists():
            issues.append(f"Export file not found: {file_path}")
        else:
            sz = p.stat().st_size
            if sz < min_sz:
                issues.append(f"Export file too small: {sz}B (min {min_sz}B) — likely blank")
                SelfHealEngine.heal_export(p.name, file_path, sz)
                SmartAlertEngine.fire(
                    "P0", "pdf_export",
                    what_happened=f"Blank PDF: {p.name} ({sz}B)",
                    where="Export Engine / PDF Generator",
                    why=f"File size {sz}B below minimum {min_sz}B",
                    action_needed="Re-render and retry export",
                )

        return (len(issues) == 0, issues)


# ═══════════════════════════════════════════════════════════════════════════════
# METRICS READER
# ═══════════════════════════════════════════════════════════════════════════════

def get_sre_metrics() -> dict:
    """Return current live metrics for dashboard display."""
    health_data: List[dict] = _load(_F_HEALTH, [])
    alerts: List[dict]      = _load(_F_ALERTS, [])
    bugs: List[dict]        = _load(_F_BUGS, [])
    audit: List[dict]       = _load(_F_AUDIT, [])
    metrics_hist: List[dict]= _load(_F_METRICS, [])

    # Health summary
    ok   = sum(1 for h in health_data if h.get("status") == "OK")
    warn = sum(1 for h in health_data if h.get("status") == "WARN")
    fail = sum(1 for h in health_data if h.get("status") == "FAIL")
    total_entities = len(health_data)
    health_pct = int(ok / total_entities * 100) if total_entities else 0

    # Alert summary
    open_alerts = [a for a in alerts if a.get("status") == "Open"]
    p0_open = sum(1 for a in open_alerts if a.get("severity") == "P0")
    p1_open = sum(1 for a in open_alerts if a.get("severity") == "P1")
    p2_open = sum(1 for a in open_alerts if a.get("severity") == "P2")

    # Bug summary
    open_bugs  = [b for b in bugs if b.get("status") == "Open"]
    fixed_bugs = [b for b in bugs if b.get("status") in ("Fixed", "Verified")]

    # Error rate from audit (last 100)
    recent_audit = audit[-100:] if len(audit) > 100 else audit
    err_count = sum(1 for r in recent_audit if r.get("severity") in ("ERROR", "CRITICAL"))

    return {
        "timestamp_ist":   _ts(),
        "health": {
            "total": total_entities, "ok": ok, "warn": warn, "fail": fail,
            "health_pct": health_pct,
            "entities": health_data,
        },
        "alerts": {
            "total_open": len(open_alerts),
            "p0": p0_open, "p1": p1_open, "p2": p2_open,
            "all_open": open_alerts,
        },
        "bugs": {
            "total": len(bugs),
            "open": len(open_bugs),
            "fixed": len(fixed_bugs),
            "open_bugs": open_bugs,
        },
        "audit": {
            "total_records": len(audit),
            "recent_errors": err_count,
        },
        "metrics_history": metrics_hist[-50:],
    }


def get_health_status() -> List[dict]:
    return _load(_F_HEALTH, [])


def get_conflict_log() -> List[dict]:
    return list(reversed(_load(_F_CONFLICT, [])))


def get_change_history(n: int = 200) -> List[dict]:
    data = _load(BASE / "sre_change_history.json", [])
    return list(reversed(data[-n:]))


# ═══════════════════════════════════════════════════════════════════════════════
# SRE ORCHESTRATOR — ties all phases together
# ═══════════════════════════════════════════════════════════════════════════════

class SREOrchestrator:
    """
    Single entry-point to run full SRE cycle:
      1. Run all health checks
      2. Fire smart alerts from results
      3. Auto-heal FAIL entities
      4. Create bugs for unresolved heals
    """

    @classmethod
    def auto_escalate(cls) -> int:
        """Escalate P1 alerts open >24h to P0. Returns count escalated."""
        alerts: List[dict] = _load(_F_ALERTS, [])
        cutoff = _now() - datetime.timedelta(hours=24)
        escalated = 0
        for a in alerts:
            if a.get("severity") != "P1" or a.get("status") != "Open":
                continue
            ts_str = a.get("triggered_on_ist", "")
            try:
                ts_dt = datetime.datetime.strptime(
                    ts_str.replace(" IST", ""), "%Y-%m-%d %H:%M:%S")
                ts_dt = IST.localize(ts_dt)
                if ts_dt < cutoff:
                    a["severity"] = "P0"
                    a["action_needed"] = (
                        a.get("action_needed", "") +
                        " [AUTO-ESCALATED from P1 after 24h]"
                    )
                    escalated += 1
            except Exception:
                pass
        if escalated:
            _save(_F_ALERTS, alerts)
            AuditLogger.warn("SREOrchestrator",
                             f"Auto-escalated {escalated} P1 alerts → P0")
        return escalated

    @classmethod
    def run_cycle(cls) -> dict:
        AuditLogger.info("SREOrchestrator", "=== SRE CYCLE START ===")
        t_start = time.time()

        # Phase 2: health checks
        health = HealthCheckEngine.run_all()

        # Phase 4: alerts from health
        alerts_fired = SmartAlertEngine.from_health_results(health)

        # Auto-escalate stale P1 alerts → P0
        escalated = cls.auto_escalate()

        # Phase 3: auto-heal failed APIs
        heal_results = []
        bugs_created = []
        cfg = _cfg()
        for r in health.get("api_health", []):
            if r["status"] == "FAIL":
                heal = SelfHealEngine.heal_api(r["entity"])
                heal_results.append(heal)
                if not heal.get("healed"):
                    # Phase 5: create bug
                    bug_id = BugAutoCreator.from_failed_heal(
                        r["entity"], heal,
                        alert_id="(see sre_alerts.json)"
                    )
                    bugs_created.append(bug_id)

        # ── Resilience: Heartbeat check + DLQ processing + LKG cleanup ────
        heartbeat_dead = 0
        heartbeat_restarted = 0
        dlq_stats = {}
        lkg_cleaned = 0
        try:
            from resilience_manager import HeartbeatMonitor, DeadLetterQueue, LKGCache
            dead = HeartbeatMonitor.check_all()
            heartbeat_dead = len(dead)
            if dead:
                heartbeat_restarted = HeartbeatMonitor.auto_restart_dead()
                AuditLogger.warn("SREOrchestrator",
                                 f"Heartbeat: {heartbeat_dead} dead threads, "
                                 f"{heartbeat_restarted} restarted")
            dlq_stats = DeadLetterQueue.process_all()
            if dlq_stats.get("retried", 0) > 0:
                AuditLogger.info("SREOrchestrator",
                                 f"DLQ: retried={dlq_stats['retried']}, "
                                 f"exhausted={dlq_stats['exhausted']}")
            lkg_cleaned = LKGCache.cleanup_old()
        except Exception as _res_err:
            AuditLogger.warn("SREOrchestrator",
                             f"Resilience integration skipped: {_res_err}")

        elapsed = time.time() - t_start
        summary = {
            "timestamp_ist":   _ts(),
            "elapsed_sec":     round(elapsed, 2),
            "health_summary":  health.get("summary", {}),
            "alerts_fired":    alerts_fired,
            "alerts_escalated": escalated,
            "heals_attempted": len(heal_results),
            "heals_succeeded": sum(1 for h in heal_results if h.get("healed")),
            "bugs_created":    bugs_created,
            "heartbeat_dead":  heartbeat_dead,
            "heartbeat_restarted": heartbeat_restarted,
            "dlq_stats":       dlq_stats,
            "lkg_cleaned":     lkg_cleaned,
        }
        AuditLogger.info("SREOrchestrator",
                         f"=== SRE CYCLE END — {elapsed:.1f}s  "
                         f"health={health.get('summary',{}).get('health_pct',0)}%  "
                         f"alerts={alerts_fired}  bugs={len(bugs_created)} ===")
        return summary


# ─── Background auto-SRE thread ───────────────────────────────────────────────
_sre_thread_started = False
_sre_thread_lock    = threading.Lock()


def start_sre_background(interval_min: int = 15) -> None:
    """
    Start a background daemon thread that runs SREOrchestrator.run_cycle()
    every `interval_min` minutes. Safe to call multiple times (runs only once).
    """
    global _sre_thread_started
    with _sre_thread_lock:
        if _sre_thread_started:
            return
        _sre_thread_started = True

    def _worker():
        time.sleep(60)  # settle time on startup
        while True:
            try:
                # Heartbeat beat
                try:
                    from resilience_manager import HeartbeatMonitor
                    HeartbeatMonitor.beat("SREBackground")
                except Exception:
                    pass
                SREOrchestrator.run_cycle()
            except Exception as e:
                AuditLogger.error("SREBackground", f"Cycle exception: {e}")
            time.sleep(interval_min * 60)

    t = threading.Thread(target=_worker, daemon=True, name="SREBackground")
    t.start()

    # Register with heartbeat monitor
    try:
        from resilience_manager import HeartbeatMonitor
        HeartbeatMonitor.register(
            "SREBackground",
            restart_fn=lambda: start_sre_background(interval_min),
            expected_interval_sec=interval_min * 60,
        )
    except Exception:
        pass

    AuditLogger.info("SREOrchestrator",
                     f"SRE background thread started (interval={interval_min}min)")


# ─── Initialise default config if missing ─────────────────────────────────────
def init_sre() -> None:
    """Call once on startup. Creates default config if missing."""
    if not _F_CONFIG.exists():
        _save(_F_CONFIG, _DEFAULT_CFG)
    # Ensure all JSON files exist
    for f, default in [
        (_F_HEALTH,   []),
        (_F_ALERTS,   []),
        (_F_BUGS,     []),
        (_F_CONFLICT, []),
        (_F_AUDIT,    []),
        (_F_METRICS,  []),
    ]:
        if not f.exists():
            _save(f, default)
    AuditLogger.info("SREOrchestrator", "SRE Engine initialised")
