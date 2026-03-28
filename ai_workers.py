"""
ai_workers.py — AI Background Worker Threads
===============================================
6 daemon threads that run AI tasks on schedule.
Resource-aware: LOW tier skips heavy workers.
Matches sync_engine.py threading pattern.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
WORKER_LOG_FILE = BASE / "ai_worker_log.json"

LOG = logging.getLogger("ai_workers")

# ═══════════════════════════════════════════════════════════════════════════════
# WORKER DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

WORKER_DEFS = [
    {
        "name": "summarizer",
        "display": "News Summarizer",
        "interval": 3600,
        "desc": "Summarizes recent news articles for dashboard",
        "min_tier": "LOW",
    },
    {
        "name": "extractor",
        "display": "Tender Extractor",
        "interval": 3600,
        "desc": "NER extraction from tender/procurement text",
        "min_tier": "LOW",
    },
    {
        "name": "forecast",
        "display": "Price Forecaster",
        "interval": 7200,
        "desc": "Runs price/demand forecasting models",
        "min_tier": "MEDIUM",
    },
    {
        "name": "scoring",
        "display": "Opportunity Scorer",
        "interval": 3600,
        "desc": "Scores opportunities and risks using ML models",
        "min_tier": "LOW",
    },
    {
        "name": "alert",
        "display": "Anomaly Alerter",
        "interval": 1800,
        "desc": "Detects price shocks, tender spikes, demand anomalies",
        "min_tier": "LOW",
    },
    {
        "name": "report_writer",
        "display": "Report Writer",
        "interval": 86400,
        "desc": "Generates daily insight reports",
        "min_tier": "MEDIUM",
    },
    {
        "name": "market_signals",
        "display": "Market Intelligence",
        "interval": 7200,
        "desc": "Computes 10-signal market intelligence composite",
        "min_tier": "LOW",
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE CONNECTION MAP
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_MAP = {
    "News Summarization": {
        "module": "ai_fallback_engine",
        "worker": "summarizer",
        "dashboard_page": "News Intelligence",
    },
    "Tender Extraction": {
        "module": "nlp_extraction_engine",
        "worker": "extractor",
        "dashboard_page": "Opportunities",
    },
    "Demand Scoring": {
        "module": "ml_boost_engine",
        "worker": "scoring",
        "dashboard_page": "Demand Analytics",
    },
    "Price Forecasting": {
        "module": "ml_forecast_engine",
        "worker": "forecast",
        "dashboard_page": "Price Prediction",
    },
    "Anomaly Alerts": {
        "module": "anomaly_engine",
        "worker": "alert",
        "dashboard_page": "Alert Center",
    },
    "Daily Reports": {
        "module": "auto_insight_engine",
        "worker": "report_writer",
        "dashboard_page": "Home",
    },
    "Sentiment Analysis": {
        "module": "finbert_engine",
        "worker": "summarizer",
        "dashboard_page": "News Intelligence",
    },
    "RAG Search": {
        "module": "rag_engine",
        "worker": None,
        "dashboard_page": "AI Dashboard Assistant",
    },
    "Communication Intel": {
        "module": "auto_comm_intelligence",
        "worker": None,
        "dashboard_page": "Communication Hub",
    },
    "Market Intelligence": {
        "module": "market_intelligence_engine",
        "worker": "market_signals",
        "dashboard_page": "Market Signals",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# THREAD STATE
# ═══════════════════════════════════════════════════════════════════════════════

_workers: dict[str, dict] = {}
_lock = threading.RLock()

_TIER_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


# ═══════════════════════════════════════════════════════════════════════════════
# WORKER IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _run_summarizer() -> dict:
    """Summarize recent news articles."""
    try:
        articles_path = BASE / "news_data" / "articles.json"
        if not articles_path.exists():
            return {"processed": 0, "details": "No articles file found"}
        data = json.loads(articles_path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            return {"processed": 0, "details": "No articles to summarize"}

        # Get unsummarized articles (last 10)
        recent = [a for a in data[-10:] if not a.get("ai_summary")]
        if not recent:
            return {"processed": 0, "details": "All recent articles already summarized"}

        try:
            from ai_fallback_engine import ask_with_fallback
            processed = 0
            for article in recent[:5]:
                title = article.get("title", "")
                desc = article.get("description", article.get("summary", ""))
                if not title:
                    continue
                prompt = (
                    f"Summarize this bitumen/oil industry news in 2 sentences: "
                    f"{title}. {desc[:300]}"
                )
                result = ask_with_fallback(prompt)
                if result and not result.get("error"):
                    article["ai_summary"] = result.get("answer", "")[:300]
                    processed += 1

            if processed > 0:
                articles_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
            return {"processed": processed, "details": f"Summarized {processed} articles"}
        except ImportError:
            return {"processed": 0, "details": "ai_fallback_engine not available"}
    except Exception as e:
        return {"processed": 0, "error": str(e)}


def _run_extractor() -> dict:
    """Extract entities from recent data."""
    try:
        from nlp_extraction_engine import extract_entities
        # Sample extraction on recent news titles
        articles_path = BASE / "news_data" / "articles.json"
        if not articles_path.exists():
            return {"extracted": 0, "details": "No articles file"}
        data = json.loads(articles_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return {"extracted": 0}

        count = 0
        for article in data[-5:]:
            title = article.get("title", "")
            if title and not article.get("entities"):
                entities = extract_entities(title)
                if entities:
                    article["entities"] = entities
                    count += 1

        if count > 0:
            articles_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        return {"extracted": count, "details": f"Extracted entities from {count} articles"}
    except Exception as e:
        return {"extracted": 0, "error": str(e)}


def _run_forecast() -> dict:
    """Run price/demand forecasting."""
    try:
        from ml_forecast_engine import forecast_price
        result = forecast_price(days=7)
        return {
            "forecast_days": 7,
            "model": result.get("model", "unknown"),
            "details": f"7-day forecast generated via {result.get('model', 'unknown')}",
        }
    except Exception as e:
        return {"forecast_days": 0, "error": str(e)}


def _run_scoring() -> dict:
    """Run opportunity/risk scoring on active deals."""
    try:
        from ml_boost_engine import score_opportunity_boost
        # Score a sample to keep models warm
        sample = {
            "price_delta": 2.5,
            "relationship_score": 70,
            "days_since_contact": 14,
            "grade": "VG30",
            "quantity_mt": 100,
            "season": "Q1",
        }
        result = score_opportunity_boost(sample)
        return {
            "model": result.get("model", "unknown"),
            "score": result.get("score", 0),
            "details": f"Scoring active, model: {result.get('model', 'unknown')}",
        }
    except Exception as e:
        return {"score": 0, "error": str(e)}


def _run_alert() -> dict:
    """Run anomaly detection."""
    try:
        from anomaly_engine import get_anomaly_summary
        summary = get_anomaly_summary()
        return {
            "anomalies": summary.get("total_anomalies", 0),
            "alert_level": summary.get("alert_level", "normal"),
            "details": f"{summary.get('total_anomalies', 0)} anomalies, level: {summary.get('alert_level', 'normal')}",
        }
    except Exception as e:
        return {"anomalies": 0, "error": str(e)}


def _run_report_writer() -> dict:
    """Generate daily insight report."""
    try:
        from auto_insight_engine import schedule_insights
        schedule_insights()
        return {"generated": True, "details": "Daily insights scheduled/generated"}
    except Exception as e:
        return {"generated": False, "error": str(e)}


def _run_market_signals() -> dict:
    """Compute 10-signal market intelligence composite."""
    try:
        from market_intelligence_engine import compute_all_signals
        signals = compute_all_signals()
        master = signals.get("master", {})
        return {
            "direction": master.get("market_direction", "N/A"),
            "confidence": master.get("confidence", 0),
            "signals_ok": sum(1 for s in signals.values() if s.get("status") == "OK"),
        }
    except Exception as e:
        return {"error": str(e)}


_WORKER_FN_MAP = {
    "summarizer": _run_summarizer,
    "extractor": _run_extractor,
    "forecast": _run_forecast,
    "scoring": _run_scoring,
    "alert": _run_alert,
    "report_writer": _run_report_writer,
    "market_signals": _run_market_signals,
}


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def _worker_loop(name: str, interval: int):
    """Main loop for a worker thread."""
    while True:
        with _lock:
            state = _workers.get(name)
            if not state or not state.get("running"):
                break

        try:
            fn = _WORKER_FN_MAP.get(name)
            if fn:
                result = fn()
                with _lock:
                    if name in _workers:
                        _workers[name]["last_run"] = _now_ist()
                        _workers[name]["last_result"] = result
                        _workers[name]["status"] = "idle"
                _log_worker_event(name, "completed", result)
        except Exception as e:
            with _lock:
                if name in _workers:
                    _workers[name]["errors_24h"] = _workers[name].get("errors_24h", 0) + 1
                    _workers[name]["last_error"] = str(e)
                    _workers[name]["status"] = "error"
            _log_worker_event(name, "error", {"error": str(e)})
            LOG.warning("Worker '%s' error: %s", name, e)

        # Sleep in 1-second chunks for graceful shutdown
        for _ in range(interval):
            with _lock:
                state = _workers.get(name)
                if not state or not state.get("running"):
                    return
            time.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════════
# START / STOP
# ═══════════════════════════════════════════════════════════════════════════════

def start_workers(tier: str = "MEDIUM") -> dict:
    """Start all workers as daemon threads. Resource-aware."""
    tier_level = _TIER_ORDER.get(tier, 1)
    results = {}

    for wdef in WORKER_DEFS:
        name = wdef["name"]
        min_level = _TIER_ORDER.get(wdef["min_tier"], 0)

        # Skip if tier too low
        if tier_level < min_level:
            results[name] = "skipped"
            continue

        with _lock:
            existing = _workers.get(name)
            if existing and existing.get("running"):
                results[name] = "already_running"
                continue

        # Create worker state
        worker_state = {
            "running": True,
            "status": "starting",
            "last_run": "never",
            "last_result": {},
            "last_error": "",
            "errors_24h": 0,
            "started_at": _now_ist(),
            "interval": wdef["interval"],
            "display": wdef["display"],
        }

        thread = threading.Thread(
            target=_worker_loop,
            args=(name, wdef["interval"]),
            daemon=True,
            name=f"AIWorker-{name}",
        )

        with _lock:
            worker_state["thread"] = thread
            _workers[name] = worker_state

        thread.start()
        results[name] = "started"
        LOG.info("AI Worker '%s' started (interval: %ds)", name, wdef["interval"])

    _log_worker_event("system", "start_workers", {"tier": tier, "results": results})
    return results


def stop_workers() -> dict:
    """Graceful shutdown of all workers."""
    results = {}
    with _lock:
        for name, state in _workers.items():
            if state.get("running"):
                state["running"] = False
                results[name] = "stopping"
            else:
                results[name] = "already_stopped"

    # Wait for threads to finish (max 5 seconds each)
    for name in list(results.keys()):
        with _lock:
            state = _workers.get(name)
            thread = state.get("thread") if state else None
        if thread and thread.is_alive():
            thread.join(timeout=5)
            results[name] = "stopped"

    _log_worker_event("system", "stop_workers", results)
    return results


def force_run(worker_name: str) -> dict:
    """Force immediate execution of a worker."""
    fn = _WORKER_FN_MAP.get(worker_name)
    if not fn:
        return {"error": f"Unknown worker: {worker_name}"}

    try:
        result = fn()
        with _lock:
            if worker_name in _workers:
                _workers[worker_name]["last_run"] = _now_ist()
                _workers[worker_name]["last_result"] = result
        _log_worker_event(worker_name, "force_run", result)
        return {"status": "completed", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_worker_status() -> list[dict]:
    """Returns status of all workers."""
    statuses = []
    for wdef in WORKER_DEFS:
        name = wdef["name"]
        with _lock:
            state = _workers.get(name, {})

        is_running = state.get("running", False)
        thread = state.get("thread")
        thread_alive = thread.is_alive() if thread else False

        if is_running and thread_alive:
            status = state.get("status", "running")
            if status == "starting":
                status = "running"
        elif is_running and not thread_alive:
            status = "crashed"
        else:
            status = "stopped"

        statuses.append({
            "name": name,
            "display": wdef["display"],
            "status": status,
            "interval": wdef["interval"],
            "min_tier": wdef["min_tier"],
            "desc": wdef["desc"],
            "last_run": state.get("last_run", "never"),
            "started_at": state.get("started_at", ""),
            "errors_24h": state.get("errors_24h", 0),
            "last_error": state.get("last_error", ""),
        })
    return statuses


def get_feature_map() -> dict:
    """Returns feature map with live status of each module + worker."""
    result = {}
    for feature, info in FEATURE_MAP.items():
        module_name = info["module"]
        worker_name = info.get("worker")

        # Check module status
        module_ok = False
        try:
            __import__(module_name)
            module_ok = True
        except ImportError:
            pass

        # Check worker status
        worker_status = "N/A"
        if worker_name:
            with _lock:
                state = _workers.get(worker_name, {})
            if state.get("running"):
                thread = state.get("thread")
                worker_status = "running" if (thread and thread.is_alive()) else "crashed"
            else:
                worker_status = "stopped"

        result[feature] = {
            "module": module_name,
            "module_loaded": module_ok,
            "worker": worker_name,
            "worker_status": worker_status,
            "dashboard_page": info.get("dashboard_page", ""),
            "overall_status": "active" if module_ok and worker_status in ("running", "N/A") else "degraded",
        }
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def _log_worker_event(worker: str, event: str, data) -> None:
    """Append to worker log."""
    try:
        logs = []
        if WORKER_LOG_FILE.exists():
            logs = json.loads(WORKER_LOG_FILE.read_text(encoding="utf-8"))
            if not isinstance(logs, list):
                logs = []
        logs.append({
            "worker": worker,
            "event": event,
            "timestamp": _now_ist(),
            "data": data,
        })
        if len(logs) > 500:
            logs = logs[-500:]
        WORKER_LOG_FILE.write_text(
            json.dumps(logs, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_worker_log(limit: int = 50) -> list[dict]:
    """Returns recent worker log entries."""
    try:
        if WORKER_LOG_FILE.exists():
            data = json.loads(WORKER_LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return list(reversed(data[-limit:]))
    except Exception:
        pass
    return []
