"""
system_control_engine.py — System Control Center Backend
=========================================================
Collects status from all subsystems: AI models, APIs, workers,
data pipelines, errors, health scoring, master switches.
No new dependencies — reads from existing engines.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
LOG = logging.getLogger("system_control")


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _load_json(path: Path) -> list | dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# A. AI MODELS STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_ai_models_status() -> list[dict]:
    """Status of all AI/ML models — LLMs, ML scorers, NLP engines."""
    models = []

    # 1. AI Fallback Engine — LLM providers
    try:
        from ai_fallback_engine import get_provider_status
        for p in get_provider_status():
            models.append({
                "name": p.get("name", p.get("id", "Unknown")),
                "type": "LLM",
                "status": "running" if p.get("active") else ("standby" if p.get("ready") else "unavailable"),
                "cost": p.get("cost", "FREE"),
                "last_used": p.get("last_used", "N/A"),
                "version": p.get("model", ""),
                "can_toggle": True,
            })
    except Exception:
        models.append({"name": "AI Fallback Engine", "type": "LLM", "status": "unavailable",
                        "cost": "FREE", "last_used": "N/A", "version": "", "can_toggle": False})

    # 2. ML Forecast Engine
    try:
        from ml_forecast_engine import get_ml_status
        ml = get_ml_status()
        models.append({
            "name": "Prophet Forecasting",
            "type": "ML",
            "status": "running" if ml["prophet_available"] else "unavailable",
            "cost": "FREE",
            "last_used": "N/A",
            "version": "Prophet" if ml["prophet_available"] else "Not installed",
            "can_toggle": False,
        })
        models.append({
            "name": "sklearn Scoring",
            "type": "ML",
            "status": "running" if ml["sklearn_available"] else "unavailable",
            "cost": "FREE",
            "last_used": "N/A",
            "version": f"{ml['models_on_disk']} models trained",
            "can_toggle": False,
        })
    except Exception:
        pass

    # 3. ML Boost Engine
    try:
        from ml_boost_engine import get_boost_status
        bs = get_boost_status()
        models.append({
            "name": "LightGBM/XGBoost Boost",
            "type": "ML",
            "status": "running" if bs["lightgbm_available"] or bs["xgboost_available"] else "unavailable",
            "cost": "FREE",
            "last_used": "N/A",
            "version": bs["active_engine"],
            "can_toggle": False,
        })
        models.append({
            "name": "SHAP Explainability",
            "type": "ML",
            "status": "running" if bs["shap_available"] else "unavailable",
            "cost": "FREE",
            "last_used": "N/A",
            "version": "SHAP" if bs["shap_available"] else "Feature importance fallback",
            "can_toggle": False,
        })
    except Exception:
        pass

    # 4. NLP Engine
    try:
        from nlp_extraction_engine import get_nlp_status
        nlp = get_nlp_status()
        models.append({
            "name": "spaCy NER",
            "type": "NLP",
            "status": "running" if nlp.get("spacy_available") else "unavailable",
            "cost": "FREE",
            "last_used": "N/A",
            "version": nlp.get("spacy_model", "Not installed"),
            "can_toggle": False,
        })
    except Exception:
        pass

    # 5. Anomaly Engine
    try:
        from anomaly_engine import get_anomaly_status
        ae = get_anomaly_status()
        models.append({
            "name": "Anomaly Detection",
            "type": "ML",
            "status": "running",
            "cost": "FREE",
            "last_used": "N/A",
            "version": ae["active_engine"],
            "can_toggle": False,
        })
    except Exception:
        pass

    # 6. RAG Engine
    try:
        from rag_engine import get_rag_status
        rs = get_rag_status()
        models.append({
            "name": "RAG Search",
            "type": "Search",
            "status": "running" if rs.get("index_built") or rs.get("documents_indexed", 0) > 0 else "standby",
            "cost": "FREE",
            "last_used": "N/A",
            "version": rs.get("active_engine", "keyword"),
            "can_toggle": False,
        })
    except Exception:
        pass

    # 7. FinBERT Engine
    try:
        from finbert_engine import get_finbert_status
        fs = get_finbert_status()
        models.append({
            "name": "FinBERT Sentiment",
            "type": "NLP",
            "status": "running" if fs.get("active_engine") != "keyword" else "standby",
            "cost": "FREE",
            "last_used": "N/A",
            "version": fs.get("active_engine", "keyword"),
            "can_toggle": False,
        })
    except Exception:
        pass

    # Enrich from module registry (health test results)
    try:
        from ai_setup_engine import get_module_registry
        registry = {m["name"]: m for m in get_module_registry()}
        for model in models:
            for reg_name, reg_data in registry.items():
                if reg_name.replace("_engine", "") in model["name"].lower().replace(" ", "_"):
                    if reg_data.get("last_tested"):
                        model["last_used"] = reg_data["last_tested"]
                    break
    except Exception:
        pass

    return models


# ═══════════════════════════════════════════════════════════════════════════════
# B. API CONNECTION STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_api_connections_status() -> list[dict]:
    """Status of all API connections with latency and health."""
    connections = []

    # From api_manager
    try:
        from api_manager import run_all_health_checks, get_reliability_scores
        summary, results = run_all_health_checks(force=False)
        reliability = get_reliability_scores()

        for widget_id, result in results.items():
            connections.append({
                "name": widget_id.replace("_", " ").title(),
                "api_id": widget_id,
                "status": "healthy" if result.get("ok") else "down",
                "latency_ms": result.get("latency_ms", 0),
                "health_pct": reliability.get(widget_id, 0),
                "last_sync": _now_ist(),
            })
    except Exception:
        pass

    # From data_confidence_engine
    try:
        from data_confidence_engine import get_all_confidences
        for conf in get_all_confidences():
            # Only add if not already tracked from api_manager
            already = any(c["name"].lower().replace(" ", "") == conf.source_name.lower().replace(" ", "")
                         for c in connections)
            if not already:
                connections.append({
                    "name": conf.source_name,
                    "api_id": conf.source_key,
                    "status": "healthy" if conf.confidence in ("verified", "estimated") else "degraded",
                    "latency_ms": 0,
                    "health_pct": conf.confidence_score,
                    "last_sync": conf.last_updated,
                    "records": conf.record_count,
                })
    except Exception:
        pass

    return connections


# ═══════════════════════════════════════════════════════════════════════════════
# C. WORKER STATUS
# ═══════════════════════════════════════════════════════════════════════════════

_WORKER_DEFS = [
    {"name": "API Health Checker", "module": "api_manager", "flag": "_G_health", "interval": "30 min"},
    {"name": "SRE Self-Healing", "module": "sre_engine", "flag": "_sre_thread_started", "interval": "15 min"},
    {"name": "API Hub Scheduler", "module": "api_hub_engine", "flag": "_hub_scheduler_started", "interval": "60 min"},
    {"name": "Sync Engine", "module": "sync_engine", "flag": "_scheduler_running", "interval": "60 min"},
    {"name": "Email Queue Processor", "module": "email_engine", "flag": "_email_scheduler_running", "interval": "5 min"},
    {"name": "WhatsApp Queue Processor", "module": "whatsapp_engine", "flag": "_wa_scheduler_running", "interval": "2 min"},
    {"name": "News Fetcher", "module": "news_engine", "flag": "_bg_started", "interval": "10 min"},
    {"name": "AI Fallback Monitor", "module": "ai_fallback_engine", "flag": "_G", "interval": "5 min", "dict_key": "monitor_started"},
]


def get_worker_status() -> list[dict]:
    """Status of all background workers."""
    workers = []
    for wdef in _WORKER_DEFS:
        status = "unknown"
        try:
            mod = sys.modules.get(wdef["module"])
            if mod:
                flag_val = getattr(mod, wdef["flag"], None)
                if isinstance(flag_val, dict) and "dict_key" in wdef:
                    status = "running" if flag_val.get(wdef["dict_key"]) else "stopped"
                elif flag_val:
                    status = "running"
                else:
                    status = "stopped"
            else:
                status = "not_loaded"
        except Exception:
            status = "error"

        workers.append({
            "name": wdef["name"],
            "module": wdef["module"],
            "status": status,
            "schedule": wdef["interval"],
            "last_run": "N/A",
            "next_run": "N/A",
            "errors_24h": 0,
        })

    # Enrich with sync history
    try:
        from sync_engine import get_sync_history
        history = get_sync_history(limit=5)
        if history:
            latest = history[-1] if isinstance(history, list) else {}
            for w in workers:
                if w["module"] == "sync_engine":
                    w["last_run"] = latest.get("completed_at", latest.get("started_at", "N/A"))
                    w["status"] = "running" if latest.get("status") == "running" else w["status"]
    except Exception:
        pass

    # Add AI worker threads
    try:
        from ai_workers import get_worker_status as _get_ai_workers
        for aw in _get_ai_workers():
            interval_sec = aw.get("interval", 3600)
            interval_text = f"{interval_sec // 60} min" if interval_sec < 3600 else f"{interval_sec // 3600} hr"
            workers.append({
                "name": f"AI: {aw['display']}",
                "module": "ai_workers",
                "status": aw["status"],
                "schedule": interval_text,
                "last_run": aw.get("last_run", "N/A"),
                "next_run": "N/A",
                "errors_24h": aw.get("errors_24h", 0),
            })
    except Exception:
        pass

    return workers


# ═══════════════════════════════════════════════════════════════════════════════
# D. OUTPUT MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

def get_output_monitoring() -> dict:
    """Emails/WhatsApp/PDFs sent today."""
    result = {"emails_today": 0, "whatsapp_today": 0, "pdfs_today": 0, "reports_today": 0}
    today = datetime.now(IST).strftime("%Y-%m-%d")

    try:
        from database import _get_conn
        conn = _get_conn()
        # Emails
        row = conn.execute(
            "SELECT COUNT(*) FROM email_queue WHERE status='sent' AND created_at LIKE ?",
            (f"{today}%",)
        ).fetchone()
        result["emails_today"] = row[0] if row else 0
        # WhatsApp
        row = conn.execute(
            "SELECT COUNT(*) FROM wa_queue WHERE status='sent' AND created_at LIKE ?",
            (f"{today}%",)
        ).fetchone()
        result["whatsapp_today"] = row[0] if row else 0
        conn.close()
    except Exception:
        pass

    # PDFs from archive
    try:
        archive = BASE / "pdf_archive"
        if archive.exists():
            result["pdfs_today"] = len([
                f for f in archive.iterdir()
                if f.suffix == ".pdf" and f.stat().st_mtime > time.time() - 86400
            ])
    except Exception:
        pass

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# E. ERROR LOG
# ═══════════════════════════════════════════════════════════════════════════════

def get_error_log(limit: int = 50) -> list[dict]:
    """Last N errors with severity from SRE audit log + API error log."""
    errors = []

    # SRE audit log (ERROR and CRITICAL only)
    try:
        from sre_engine import AuditLogger
        for entry in AuditLogger.get_recent(n=limit * 2):
            if entry.get("severity") in ("ERROR", "CRITICAL", "WARN"):
                errors.append({
                    "time": entry.get("timestamp_ist", ""),
                    "severity": entry.get("severity", "ERROR"),
                    "source": entry.get("component", "unknown"),
                    "message": entry.get("message", ""),
                    "request_id": entry.get("request_id", ""),
                })
    except Exception:
        pass

    # API error log
    try:
        api_errors = _load_json(BASE / "api_error_log.json")
        if isinstance(api_errors, list):
            for entry in api_errors[-limit:]:
                errors.append({
                    "time": entry.get("timestamp", entry.get("time", "")),
                    "severity": entry.get("severity", "ERROR"),
                    "source": entry.get("api", entry.get("source", "API")),
                    "message": entry.get("error", entry.get("message", "")),
                    "request_id": "",
                })
    except Exception:
        pass

    # Sort by time (newest first) and limit
    errors.sort(key=lambda e: e.get("time", ""), reverse=True)
    return errors[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# F. SYSTEM HEALTH SCORE
# ═══════════════════════════════════════════════════════════════════════════════

def get_system_health_score() -> dict:
    """
    Overall system health: 0-100 composite score.
    Formula: API_health*30 + Data_freshness*25 + AI_readiness*20 + Worker_uptime*15 + Error_rate*10
    """
    breakdown = {
        "api_health": 50,
        "data_freshness": 50,
        "ai_readiness": 50,
        "worker_uptime": 50,
        "error_rate": 80,
    }

    # API health
    try:
        conns = get_api_connections_status()
        if conns:
            healthy = sum(1 for c in conns if c["status"] in ("healthy",))
            breakdown["api_health"] = round(healthy / len(conns) * 100) if conns else 50
    except Exception:
        pass

    # Data freshness
    try:
        from data_confidence_engine import get_overall_health
        health = get_overall_health()
        breakdown["data_freshness"] = round(health.get("average_score", 50))
    except Exception:
        pass

    # AI readiness (combine model status + module registry health tests)
    try:
        models = get_ai_models_status()
        if models:
            ready = sum(1 for m in models if m["status"] in ("running", "standby"))
            model_score = round(ready / len(models) * 100) if models else 50
        else:
            model_score = 50
        # Also check module registry
        try:
            from ai_setup_engine import get_module_registry
            registry = get_module_registry()
            if registry:
                passed = sum(1 for m in registry if m.get("health_test") == "pass")
                reg_score = round(passed / len(registry) * 100)
                breakdown["ai_readiness"] = round((model_score + reg_score) / 2)
            else:
                breakdown["ai_readiness"] = model_score
        except Exception:
            breakdown["ai_readiness"] = model_score
    except Exception:
        pass

    # Worker uptime
    try:
        workers = get_worker_status()
        if workers:
            running = sum(1 for w in workers if w["status"] == "running")
            breakdown["worker_uptime"] = round(running / len(workers) * 100) if workers else 50
    except Exception:
        pass

    # Error rate (inverse — fewer errors = higher score)
    try:
        errors = get_error_log(50)
        critical = sum(1 for e in errors if e.get("severity") == "CRITICAL")
        error_count = sum(1 for e in errors if e.get("severity") == "ERROR")
        breakdown["error_rate"] = max(0, 100 - critical * 20 - error_count * 5)
    except Exception:
        pass

    # Weighted composite
    score = (
        breakdown["api_health"] * 0.30 +
        breakdown["data_freshness"] * 0.25 +
        breakdown["ai_readiness"] * 0.20 +
        breakdown["worker_uptime"] * 0.15 +
        breakdown["error_rate"] * 0.10
    )
    score = round(max(0, min(100, score)))

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "breakdown": breakdown,
        "timestamp": _now_ist(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# G. MASTER SWITCHES
# ═══════════════════════════════════════════════════════════════════════════════

_SWITCH_KEYS = {
    "ai_enabled": {"label": "AI Engine", "default": True},
    "sync_enabled": {"label": "Sync Engine", "default": True},
    "email_enabled": {"label": "Email Alerts", "default": True},
    "whatsapp_enabled": {"label": "WhatsApp Alerts", "default": True},
    "anomaly_detection_enabled": {"label": "Anomaly Detection", "default": True},
    "maintenance_mode": {"label": "Maintenance Mode", "default": False},
    "ops_monitoring_enabled": {"label": "Ops Monitoring", "default": True},
    "infra_demand_enabled": {"label": "Infra Demand Intelligence", "default": True},
}


def get_master_switches() -> dict:
    """Current state of all system toggles."""
    switches = {}
    try:
        from settings_engine import load_settings
        settings = load_settings()
        for key, meta in _SWITCH_KEYS.items():
            switches[key] = {
                "label": meta["label"],
                "enabled": settings.get(key, meta["default"]),
                "key": key,
            }
    except Exception:
        for key, meta in _SWITCH_KEYS.items():
            switches[key] = {"label": meta["label"], "enabled": meta["default"], "key": key}
    return switches


def set_master_switch(switch_name: str, enabled: bool) -> bool:
    """Toggle a system switch. Returns True if successful."""
    if switch_name not in _SWITCH_KEYS:
        return False
    try:
        from settings_engine import update
        update(switch_name, enabled)
        LOG.info("Master switch '%s' set to %s", switch_name, enabled)
        return True
    except Exception as e:
        LOG.error("Failed to set switch '%s': %s", switch_name, e)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# H. SECURITY STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_security_status() -> dict:
    """SSL, login, backup status."""
    status = {
        "ssl_enabled": False,
        "ssl_note": "Streamlit local development — HTTPS via reverse proxy in production",
        "login_protection": False,
        "rbac_enabled": False,
        "last_backup": "N/A",
        "backup_status": "no_backup_configured",
    }

    try:
        from settings_engine import load_settings
        settings = load_settings()
        status["rbac_enabled"] = settings.get("rbac_enabled", False)
        status["login_protection"] = settings.get("rbac_enabled", False)
    except Exception:
        pass

    # Check for backup files
    try:
        backups = list(BASE.glob("backup_*.db")) + list(BASE.glob("*.backup"))
        if backups:
            latest = max(backups, key=lambda f: f.stat().st_mtime)
            from datetime import datetime as dt
            status["last_backup"] = dt.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M IST")
            status["backup_status"] = "ok"
    except Exception:
        pass

    return status


# ═══════════════════════════════════════════════════════════════════════════════
# I. DATA FLOW STATUS
# ═══════════════════════════════════════════════════════════════════════════════

def get_data_flow_status() -> dict:
    """Data pipeline status: API → Raw → Processing → AI/ML → DB → Dashboard → Output."""
    stages = []

    # Stage 1: API Sources
    try:
        conns = get_api_connections_status()
        healthy = sum(1 for c in conns if c["status"] == "healthy")
        stages.append({
            "name": "API Sources",
            "icon": "🌐",
            "status": "ok" if healthy > len(conns) * 0.5 else "degraded",
            "detail": f"{healthy}/{len(conns)} healthy",
        })
    except Exception:
        stages.append({"name": "API Sources", "icon": "🌐", "status": "unknown", "detail": ""})

    # Stage 2: Raw Data
    try:
        from data_confidence_engine import get_overall_health
        health = get_overall_health()
        stages.append({
            "name": "Raw Data",
            "icon": "📦",
            "status": "ok" if health["overall"] in ("healthy", "partial") else "degraded",
            "detail": f"avg score: {health['average_score']}%",
        })
    except Exception:
        stages.append({"name": "Raw Data", "icon": "📦", "status": "unknown", "detail": ""})

    # Stage 3: Processing Engines
    try:
        workers = get_worker_status()
        running = sum(1 for w in workers if w["status"] == "running")
        stages.append({
            "name": "Processing",
            "icon": "⚙️",
            "status": "ok" if running >= len(workers) * 0.5 else "degraded",
            "detail": f"{running}/{len(workers)} workers",
        })
    except Exception:
        stages.append({"name": "Processing", "icon": "⚙️", "status": "unknown", "detail": ""})

    # Stage 4: AI/ML
    try:
        models = get_ai_models_status()
        active = sum(1 for m in models if m["status"] in ("running", "standby"))
        stages.append({
            "name": "AI / ML",
            "icon": "🧠",
            "status": "ok" if active > 0 else "degraded",
            "detail": f"{active}/{len(models)} active",
        })
    except Exception:
        stages.append({"name": "AI / ML", "icon": "🧠", "status": "unknown", "detail": ""})

    # Stage 5: Database
    try:
        from database import _get_conn
        conn = _get_conn()
        tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()
        conn.close()
        stages.append({
            "name": "Database",
            "icon": "🗄️",
            "status": "ok",
            "detail": f"{tables[0]} tables",
        })
    except Exception:
        stages.append({"name": "Database", "icon": "🗄️", "status": "unknown", "detail": ""})

    # Stage 6: Dashboard
    stages.append({
        "name": "Dashboard",
        "icon": "📊",
        "status": "ok",
        "detail": "Streamlit running",
    })

    # Stage 7: Output
    try:
        output = get_output_monitoring()
        total = output["emails_today"] + output["whatsapp_today"] + output["pdfs_today"]
        stages.append({
            "name": "Output",
            "icon": "📤",
            "status": "ok" if total > 0 else "idle",
            "detail": f"{total} items today",
        })
    except Exception:
        stages.append({"name": "Output", "icon": "📤", "status": "unknown", "detail": ""})

    return {"stages": stages, "timestamp": _now_ist()}
