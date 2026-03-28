"""
ai_setup_engine.py — AI Setup & Environment Engine
=====================================================
Auto-detect environment, install packages, manage Ollama,
run health tests, maintain module registry.
ZERO paid services. All FREE / open-source.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
REGISTRY_FILE = BASE / "ai_module_registry.json"
SETUP_LOG_FILE = BASE / "ai_setup_log.json"
OLLAMA_ENDPOINT = "http://localhost:11434"

LOG = logging.getLogger("ai_setup")


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


# ═══════════════════════════════════════════════════════════════════════════════
# A. ENVIRONMENT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_environment() -> dict:
    """Detect OS, RAM, CPU, disk, Python version, GPU, venv."""
    env = {
        "os": platform.system(),
        "os_version": platform.version(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "ram_gb": 0.0,
        "cpu_cores": os.cpu_count() or 1,
        "disk_free_gb": 0.0,
        "gpu_available": False,
        "gpu_name": "",
        "venv_path": "",
        "detected_at": _now_ist(),
    }

    # RAM via psutil
    try:
        import psutil
        env["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        # Fallback: platform-specific
        try:
            if platform.system() == "Windows":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulonglong = ctypes.c_ulonglong
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", c_ulonglong),
                        ("ullAvailPhys", c_ulonglong),
                        ("ullTotalPageFile", c_ulonglong),
                        ("ullAvailPageFile", c_ulonglong),
                        ("ullTotalVirtual", c_ulonglong),
                        ("ullAvailVirtual", c_ulonglong),
                        ("ullAvailExtendedVirtual", c_ulonglong),
                    ]
                mem = MEMORYSTATUSEX()
                mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
                env["ram_gb"] = round(mem.ullTotalPhys / (1024 ** 3), 1)
            else:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            kb = int(line.split()[1])
                            env["ram_gb"] = round(kb / (1024 ** 2), 1)
                            break
        except Exception:
            env["ram_gb"] = 4.0  # Conservative default

    # Disk free
    try:
        usage = shutil.disk_usage(str(BASE))
        env["disk_free_gb"] = round(usage.free / (1024 ** 3), 1)
    except Exception:
        pass

    # GPU detection
    try:
        import torch
        if torch.cuda.is_available():
            env["gpu_available"] = True
            env["gpu_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    # Venv path
    venv = os.environ.get("VIRTUAL_ENV", "")
    if venv:
        env["venv_path"] = venv
    elif hasattr(sys, "prefix") and sys.prefix != sys.base_prefix:
        env["venv_path"] = sys.prefix

    return env


def get_resource_tier(env: dict | None = None) -> str:
    """Determine resource tier: LOW (<8GB), MEDIUM (8-15GB), HIGH (>=16GB)."""
    if env is None:
        env = detect_environment()
    ram = env.get("ram_gb", 4.0)
    if ram < 8:
        return "LOW"
    elif ram < 16:
        return "MEDIUM"
    else:
        return "HIGH"


# ═══════════════════════════════════════════════════════════════════════════════
# B. PACKAGE INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

# Package tiers: which packages to install per resource tier
_PACKAGES = {
    "LOW": [
        "scikit-learn",
        "numpy",
        "sentence-transformers",
    ],
    "MEDIUM": [
        "scikit-learn",
        "numpy",
        "sentence-transformers",
        "lightgbm",
        "faiss-cpu",
        "shap",
    ],
    "HIGH": [
        "scikit-learn",
        "numpy",
        "sentence-transformers",
        "lightgbm",
        "faiss-cpu",
        "shap",
        "xgboost",
        "transformers",
    ],
}

# Always try these (lightweight)
_ALWAYS_PACKAGES = ["psutil", "ollama", "huggingface-hub"]


def _is_pkg_installed(pkg_name: str) -> bool:
    """Check if a package is importable."""
    import_name = pkg_name.replace("-", "_").replace("faiss_cpu", "faiss")
    if import_name == "scikit_learn":
        import_name = "sklearn"
    if import_name == "sentence_transformers":
        import_name = "sentence_transformers"
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def install_packages(tier: str | None = None, dry_run: bool = False) -> dict:
    """
    Install packages based on resource tier.
    Returns: {package: "installed"|"already"|"failed"|"dry_run"}
    """
    if tier is None:
        tier = get_resource_tier()

    tier_packages = _PACKAGES.get(tier, _PACKAGES["LOW"])
    all_packages = _ALWAYS_PACKAGES + tier_packages
    # Deduplicate while preserving order
    seen = set()
    packages = []
    for p in all_packages:
        if p not in seen:
            seen.add(p)
            packages.append(p)

    results = {}
    for pkg in packages:
        if _is_pkg_installed(pkg):
            results[pkg] = "already"
            continue

        if dry_run:
            results[pkg] = "dry_run"
            continue

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", pkg],
                capture_output=True, text=True, timeout=300,
            )
            # Verify installation
            if _is_pkg_installed(pkg):
                results[pkg] = "installed"
                LOG.info("Installed package: %s", pkg)
            else:
                results[pkg] = "failed"
                LOG.warning("Package %s install completed but import failed", pkg)
        except subprocess.TimeoutExpired:
            results[pkg] = "failed"
            LOG.warning("Package %s install timed out", pkg)
        except Exception as e:
            results[pkg] = "failed"
            LOG.warning("Failed to install %s: %s", pkg, e)

    _log_setup_event("install_packages", {"tier": tier, "results": results})
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# C. OLLAMA MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def _ollama_running() -> bool:
    """Check if Ollama daemon is live."""
    try:
        urllib.request.urlopen(f"{OLLAMA_ENDPOINT}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def _find_ollama() -> str | None:
    """Find the Ollama executable."""
    path = shutil.which("ollama")
    if path:
        return path
    # Common Windows locations
    if platform.system() == "Windows":
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Ollama\ollama.exe"),
            r"C:\Users\HP\AppData\Local\Programs\Ollama\ollama.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    # Linux/Mac
    for c in ["/usr/local/bin/ollama", "/usr/bin/ollama"]:
        if os.path.isfile(c):
            return c
    return None


def _ollama_models() -> list[str]:
    """Get list of locally available Ollama models."""
    try:
        req = urllib.request.urlopen(f"{OLLAMA_ENDPOINT}/api/tags", timeout=5)
        data = json.loads(req.read().decode())
        return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


def _pull_ollama_model(model: str) -> bool:
    """Pull an Ollama model. Returns True on success."""
    ollama_bin = _find_ollama()
    if not ollama_bin:
        return False
    try:
        result = subprocess.run(
            [ollama_bin, "pull", model],
            capture_output=True, text=True, timeout=600,
        )
        return result.returncode == 0
    except Exception as e:
        LOG.warning("Failed to pull model %s: %s", model, e)
        return False


def setup_ollama(tier: str | None = None) -> dict:
    """
    Setup Ollama: find binary, start daemon, pull models.
    Returns: {"status": str, "models": list, "port": int, "details": str}
    """
    if tier is None:
        tier = get_resource_tier()

    result = {
        "status": "not_found",
        "models": [],
        "port": 11434,
        "binary": "",
        "details": "",
    }

    # Step 1: Find binary
    ollama_bin = _find_ollama()
    if not ollama_bin:
        result["details"] = (
            "Ollama not found. Install from https://ollama.com/download. "
            "After installing, restart this setup."
        )
        _log_setup_event("ollama_setup", result)
        return result

    result["binary"] = ollama_bin

    # Step 2: Start daemon if not running
    if not _ollama_running():
        try:
            # Start as background process
            subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            # Wait for startup
            for _ in range(15):
                time.sleep(1)
                if _ollama_running():
                    break
        except Exception as e:
            result["details"] = f"Failed to start Ollama daemon: {e}"
            result["status"] = "start_failed"
            _log_setup_event("ollama_setup", result)
            return result

    if not _ollama_running():
        result["status"] = "start_failed"
        result["details"] = "Ollama daemon did not start within 15 seconds"
        _log_setup_event("ollama_setup", result)
        return result

    # Step 3: Check existing models
    existing = _ollama_models()
    result["models"] = existing

    # Step 4: Pull models based on tier
    models_to_pull = []
    if tier == "LOW":
        models_to_pull = ["tinyllama:latest"]
    elif tier == "MEDIUM":
        models_to_pull = ["llama3:latest"]
    else:  # HIGH
        models_to_pull = ["llama3:latest", "mistral:latest"]

    pulled = []
    for model in models_to_pull:
        # Check if already available (strip tag for matching)
        base_name = model.split(":")[0]
        if any(base_name in m for m in existing):
            pulled.append(model)
            continue
        LOG.info("Pulling Ollama model: %s (this may take several minutes)", model)
        if _pull_ollama_model(model):
            pulled.append(model)
        else:
            LOG.warning("Failed to pull model: %s", model)

    result["models"] = _ollama_models()  # Refresh list
    result["status"] = "running"
    result["details"] = f"Ollama running. Models: {', '.join(result['models']) or 'none yet'}"

    _log_setup_event("ollama_setup", result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# D. HEALTH TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def run_health_tests() -> list[dict]:
    """
    Run health tests on all AI modules. Returns list of test results.
    Each: {module, status, engine_used, response_ms, error, details}
    """
    tests = []

    # 1. AI Fallback Engine (LLM chain)
    tests.append(_test_module(
        "ai_fallback_engine",
        "LLM Chain (Ollama/HF/GPT4All)",
        _test_ai_fallback,
    ))

    # 2. ML Forecast Engine
    tests.append(_test_module(
        "ml_forecast_engine",
        "Prophet + sklearn Forecasting",
        _test_ml_forecast,
    ))

    # 3. ML Boost Engine
    tests.append(_test_module(
        "ml_boost_engine",
        "LightGBM/XGBoost Scoring",
        _test_ml_boost,
    ))

    # 4. Anomaly Engine
    tests.append(_test_module(
        "anomaly_engine",
        "Anomaly Detection",
        _test_anomaly,
    ))

    # 5. RAG Engine
    tests.append(_test_module(
        "rag_engine",
        "RAG Search (FAISS/TF-IDF)",
        _test_rag,
    ))

    # 6. FinBERT Engine
    tests.append(_test_module(
        "finbert_engine",
        "Financial Sentiment (FinBERT)",
        _test_finbert,
    ))

    # 7. NLP Extraction Engine
    tests.append(_test_module(
        "nlp_extraction_engine",
        "NLP Entity Extraction",
        _test_nlp,
    ))

    # 8. Auto Insight Engine
    tests.append(_test_module(
        "auto_insight_engine",
        "Auto Insight Generator",
        _test_auto_insight,
    ))

    # Register all results
    for t in tests:
        register_module(
            name=t["module"],
            display_name=t["display_name"],
            status=t["status"],
            engine=t.get("engine_used", ""),
            health_test=t["status"],
            error_log=t.get("error", ""),
        )

    _log_setup_event("health_tests", {"results": tests})
    return tests


def _test_module(module_name: str, display_name: str, test_fn) -> dict:
    """Run a single module test with timing."""
    result = {
        "module": module_name,
        "display_name": display_name,
        "status": "fail",
        "engine_used": "",
        "response_ms": 0,
        "error": None,
        "details": "",
    }
    start = time.time()
    try:
        test_result = test_fn()
        result["response_ms"] = round((time.time() - start) * 1000)
        result["status"] = test_result.get("status", "fail")
        result["engine_used"] = test_result.get("engine", "")
        result["details"] = test_result.get("details", "")
    except Exception as e:
        result["response_ms"] = round((time.time() - start) * 1000)
        result["error"] = str(e)
        result["status"] = "fail"
    return result


def _test_ai_fallback() -> dict:
    from ai_fallback_engine import get_provider_status
    statuses = get_provider_status()
    ready = [s for s in statuses if s.get("ready")]
    if ready:
        active = next((s for s in statuses if s.get("is_active")), ready[0])
        return {
            "status": "pass",
            "engine": active.get("id", "unknown"),
            "details": f"{len(ready)} providers ready, active: {active.get('name', 'unknown')}",
        }
    return {"status": "degraded", "engine": "none", "details": "No LLM providers ready"}


def _test_ml_forecast() -> dict:
    from ml_forecast_engine import get_ml_status
    ml = get_ml_status()
    engines = []
    if ml.get("prophet_available"):
        engines.append("Prophet")
    if ml.get("sklearn_available"):
        engines.append("sklearn")
    if engines:
        return {"status": "pass", "engine": "+".join(engines),
                "details": f"{ml.get('models_on_disk', 0)} models trained"}
    return {"status": "degraded", "engine": "heuristic", "details": "Using heuristic fallbacks"}


def _test_ml_boost() -> dict:
    from ml_boost_engine import get_boost_status
    bs = get_boost_status()
    if bs.get("lightgbm_available") or bs.get("xgboost_available"):
        return {"status": "pass", "engine": bs["active_engine"],
                "details": f"SHAP: {'yes' if bs.get('shap_available') else 'no'}"}
    if bs.get("sklearn_available"):
        return {"status": "degraded", "engine": "sklearn",
                "details": "Using sklearn GradientBoosting fallback"}
    return {"status": "degraded", "engine": "rule", "details": "Using rule-based scoring"}


def _test_anomaly() -> dict:
    from anomaly_engine import get_anomaly_status
    ae = get_anomaly_status()
    engine = ae.get("active_engine", "zscore")
    return {"status": "pass", "engine": engine,
            "details": f"IsolationForest: {'yes' if ae.get('isolation_forest_available') else 'no'}"}


def _test_rag() -> dict:
    from rag_engine import get_rag_status
    rs = get_rag_status()
    engine = rs.get("active_engine", "keyword")
    docs = rs.get("documents_indexed", 0)
    return {"status": "pass" if docs > 0 else "degraded", "engine": engine,
            "details": f"{docs} documents indexed, engine: {engine}"}


def _test_finbert() -> dict:
    from finbert_engine import get_finbert_status
    fs = get_finbert_status()
    engine = fs.get("active_engine", "keyword")
    return {"status": "pass" if engine != "keyword" else "degraded",
            "engine": engine, "details": f"Active engine: {engine}"}


def _test_nlp() -> dict:
    from nlp_extraction_engine import get_nlp_status
    nlp = get_nlp_status()
    if nlp.get("spacy_available"):
        return {"status": "pass", "engine": "spacy",
                "details": f"Model: {nlp.get('spacy_model', 'unknown')}"}
    return {"status": "degraded", "engine": "regex",
            "details": "Using regex fallback (spaCy not installed)"}


def _test_auto_insight() -> dict:
    try:
        from auto_insight_engine import get_insight_history
        history = get_insight_history(days=7)
        return {"status": "pass", "engine": "llm+rule",
                "details": f"{len(history)} insights in last 7 days"}
    except Exception:
        return {"status": "degraded", "engine": "rule",
                "details": "Insight engine available (no history yet)"}


# ═══════════════════════════════════════════════════════════════════════════════
# E. MODULE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

def _load_registry() -> list[dict]:
    try:
        if REGISTRY_FILE.exists():
            data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _save_registry(registry: list[dict]) -> None:
    try:
        REGISTRY_FILE.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        LOG.warning("Failed to save module registry: %s", e)


def register_module(
    name: str,
    display_name: str = "",
    status: str = "unknown",
    engine: str = "",
    health_test: str = "",
    error_log: str = "",
) -> None:
    """Register or update a module in the registry."""
    registry = _load_registry()

    # Find existing entry or create new
    entry = None
    for m in registry:
        if m.get("name") == name:
            entry = m
            break

    if entry is None:
        entry = {"name": name}
        registry.append(entry)

    entry.update({
        "display_name": display_name or name,
        "status": status,
        "engine": engine,
        "health_test": health_test,
        "last_tested": _now_ist(),
        "error_log": error_log or "",
    })

    _save_registry(registry)


def get_module_registry() -> list[dict]:
    """Returns all registered modules."""
    return _load_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# F. FULL SETUP ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

def full_setup(force: bool = False) -> dict:
    """
    Master orchestrator: detect → install → ollama → health tests → register.
    Idempotent unless force=True.
    """
    report = {
        "started_at": _now_ist(),
        "environment": {},
        "tier": "",
        "packages": {},
        "ollama": {},
        "health_tests": [],
        "completed_at": "",
        "status": "running",
    }

    # Step 1: Detect environment
    env = detect_environment()
    report["environment"] = env
    tier = get_resource_tier(env)
    report["tier"] = tier
    LOG.info("AI Setup: Environment detected — %s, RAM: %sGB, Tier: %s",
             env["os"], env["ram_gb"], tier)

    # Step 2: Install packages
    report["packages"] = install_packages(tier)
    installed_count = sum(1 for v in report["packages"].values() if v == "installed")
    already_count = sum(1 for v in report["packages"].values() if v == "already")
    LOG.info("AI Setup: Packages — %d installed, %d already present", installed_count, already_count)

    # Step 3: Setup Ollama
    try:
        report["ollama"] = setup_ollama(tier)
    except Exception as e:
        report["ollama"] = {"status": "error", "details": str(e)}
        LOG.warning("AI Setup: Ollama setup failed: %s", e)

    # Step 4: Run health tests
    report["health_tests"] = run_health_tests()
    passed = sum(1 for t in report["health_tests"] if t["status"] == "pass")
    total = len(report["health_tests"])
    LOG.info("AI Setup: Health tests — %d/%d passed", passed, total)

    report["completed_at"] = _now_ist()
    report["status"] = "complete"

    _log_setup_event("full_setup", {
        "tier": tier,
        "packages_installed": installed_count,
        "ollama_status": report["ollama"].get("status", "unknown"),
        "health_passed": passed,
        "health_total": total,
    })

    return report


# ═══════════════════════════════════════════════════════════════════════════════
# G. SETUP STATUS (read-only, fast)
# ═══════════════════════════════════════════════════════════════════════════════

def get_setup_status() -> dict:
    """Returns current setup state without running anything."""
    env = detect_environment()
    tier = get_resource_tier(env)
    registry = get_module_registry()

    # Quick package check
    tier_packages = _ALWAYS_PACKAGES + _PACKAGES.get(tier, _PACKAGES["LOW"])
    installed = sum(1 for p in set(tier_packages) if _is_pkg_installed(p))

    # Module status counts
    passed = sum(1 for m in registry if m.get("health_test") == "pass")
    degraded = sum(1 for m in registry if m.get("health_test") == "degraded")
    failed = sum(1 for m in registry if m.get("health_test") == "fail")

    return {
        "tier": tier,
        "ram_gb": env["ram_gb"],
        "os": env["os"],
        "packages_installed": installed,
        "packages_total": len(set(tier_packages)),
        "ollama_running": _ollama_running(),
        "ollama_models": _ollama_models() if _ollama_running() else [],
        "modules_total": len(registry),
        "modules_passed": passed,
        "modules_degraded": degraded,
        "modules_failed": failed,
        "registry": registry,
        "checked_at": _now_ist(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def _log_setup_event(event: str, data: dict) -> None:
    """Append to setup log file."""
    try:
        logs = []
        if SETUP_LOG_FILE.exists():
            logs = json.loads(SETUP_LOG_FILE.read_text(encoding="utf-8"))
            if not isinstance(logs, list):
                logs = []
        logs.append({
            "event": event,
            "timestamp": _now_ist(),
            "data": data,
        })
        if len(logs) > 200:
            logs = logs[-200:]
        SETUP_LOG_FILE.write_text(
            json.dumps(logs, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_setup_log(limit: int = 50) -> list[dict]:
    """Returns recent setup log entries."""
    try:
        if SETUP_LOG_FILE.exists():
            data = json.loads(SETUP_LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return list(reversed(data[-limit:]))
    except Exception:
        pass
    return []
