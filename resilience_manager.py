"""
PPS Anantam — Resilience Manager v1.0
======================================
Core engine for 24/7/365 zero-downtime operations.

Components:
  1. HeartbeatMonitor  — Detects dead daemon threads, auto-restarts
  2. DeadLetterQueue   — Persistent failed-job queue with retry
  3. LKGCache          — Last-Known-Good data snapshots
  4. ConcurrentExecutor— Parallel task execution with timeouts
  5. GracefulDegradation — Output continuity when inputs fail

All timestamps: IST  DD-MM-YYYY HH:MM:SS IST
Zero external dependencies (no Redis, Celery, Postgres).
"""

from __future__ import annotations

import json
import time
import threading
import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Callable, Optional

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

def _now() -> datetime.datetime:
    return datetime.datetime.now(IST)

def _ts() -> str:
    return _now().strftime("%Y-%m-%d %H:%M:%S IST")

def _load_json(path: Path, default=None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else []

def _save_json(path: Path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HEARTBEAT MONITOR — Detects dead daemon threads
# ═══════════════════════════════════════════════════════════════════════════════

class HeartbeatMonitor:
    """
    Monitors all daemon threads. Auto-restarts crashed ones.

    Usage:
        HeartbeatMonitor.register("SyncScheduler", restart_fn, expected_interval_sec=3600)
        # In daemon loop:
        HeartbeatMonitor.beat("SyncScheduler")
    """
    _lock = threading.RLock()
    _heartbeats: dict[str, dict] = {}
    _checker_started = False

    @classmethod
    def register(cls, thread_name: str, restart_fn: Callable,
                 expected_interval_sec: int = 60) -> None:
        """Register a daemon thread for monitoring."""
        with cls._lock:
            cls._heartbeats[thread_name] = {
                "last_beat": time.time(),
                "expected_interval_sec": expected_interval_sec,
                "restart_fn": restart_fn,
                "restart_count_hour": 0,
                "restart_hour_marker": time.time(),
                "status": "alive",
                "registered_at": _ts(),
            }

    @classmethod
    def beat(cls, thread_name: str) -> None:
        """Called by each daemon thread on every loop iteration."""
        with cls._lock:
            if thread_name in cls._heartbeats:
                cls._heartbeats[thread_name]["last_beat"] = time.time()
                cls._heartbeats[thread_name]["status"] = "alive"

    @classmethod
    def check_all(cls) -> list[dict]:
        """Check all registered threads. Returns list of dead thread info."""
        from resilience_config import HEARTBEAT_CONFIG
        dead_multiplier = HEARTBEAT_CONFIG["dead_multiplier"]
        dead_threads = []
        now = time.time()
        with cls._lock:
            for name, info in cls._heartbeats.items():
                elapsed = now - info["last_beat"]
                threshold = info["expected_interval_sec"] * dead_multiplier
                if elapsed > threshold:
                    info["status"] = "dead"
                    dead_threads.append({
                        "name": name,
                        "last_beat_sec_ago": round(elapsed),
                        "threshold_sec": round(threshold),
                        "restart_count": info["restart_count_hour"],
                    })
        return dead_threads

    @classmethod
    def auto_restart_dead(cls) -> int:
        """Restart dead threads. Returns count of threads restarted."""
        from resilience_config import HEARTBEAT_CONFIG
        max_restarts = HEARTBEAT_CONFIG["max_restarts_per_hour"]
        alert_threshold = HEARTBEAT_CONFIG["alert_after_failed_restarts"]
        restarted = 0
        now = time.time()

        with cls._lock:
            for name, info in cls._heartbeats.items():
                if info["status"] != "dead":
                    continue

                # Reset hourly counter if >1 hour since marker
                if now - info["restart_hour_marker"] > 3600:
                    info["restart_count_hour"] = 0
                    info["restart_hour_marker"] = now

                if info["restart_count_hour"] >= max_restarts:
                    # Too many restarts — fire P0 alert
                    if info["restart_count_hour"] == alert_threshold:
                        try:
                            from sre_engine import SmartAlertEngine
                            SmartAlertEngine.fire(
                                severity="P0",
                                entity=name,
                                what_happened=f"Thread {name} failed {max_restarts} restarts in 1 hour",
                                where="HeartbeatMonitor",
                                why=f"Max restart attempts ({max_restarts}) exhausted",
                                action_needed=f"Manual investigation required for {name}",
                            )
                        except Exception:
                            pass
                    continue

                # Attempt restart
                restart_fn = info.get("restart_fn")
                if restart_fn:
                    try:
                        restart_fn()
                        info["restart_count_hour"] += 1
                        info["last_beat"] = time.time()
                        info["status"] = "restarted"
                        restarted += 1
                    except Exception:
                        info["restart_count_hour"] += 1

        return restarted

    @classmethod
    def get_status(cls) -> list[dict]:
        """Get status of all monitored threads."""
        now = time.time()
        result = []
        with cls._lock:
            for name, info in cls._heartbeats.items():
                elapsed = now - info["last_beat"]
                result.append({
                    "name": name,
                    "status": info["status"],
                    "last_beat_sec_ago": round(elapsed),
                    "expected_interval_sec": info["expected_interval_sec"],
                    "restart_count_hour": info["restart_count_hour"],
                    "registered_at": info.get("registered_at", ""),
                })
        return result

    @classmethod
    def start_checker(cls) -> None:
        """Start the background heartbeat checker thread."""
        if cls._checker_started:
            return
        cls._checker_started = True

        from resilience_config import HEARTBEAT_CONFIG
        interval = HEARTBEAT_CONFIG["check_interval_sec"]

        def _loop():
            time.sleep(60)  # settle time
            while True:
                try:
                    dead = cls.check_all()
                    if dead:
                        cls.auto_restart_dead()
                except Exception:
                    pass
                time.sleep(interval)

        t = threading.Thread(target=_loop, daemon=True, name="HeartbeatChecker")
        t.start()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DEAD LETTER QUEUE — Persistent failed-job queue with retry
# ═══════════════════════════════════════════════════════════════════════════════

class DeadLetterQueue:
    """
    Persistent queue for failed operations. Jobs retry with exponential backoff.

    Usage:
        DeadLetterQueue.push("api_fetch", {"connector": "eia_crude"}, "Timeout")
        stats = DeadLetterQueue.process_all()
    """
    _F_QUEUE = BASE / "dead_letter_queue.json"
    _F_ARCHIVE = BASE / "dead_letter_archive.json"
    _lock = threading.RLock()

    @classmethod
    def push(cls, job_type: str, payload: dict, error: str,
             max_retries: int = 3) -> str:
        """Add a failed job to the dead-letter queue."""
        from resilience_config import DLQ_CONFIG
        max_retries = min(max_retries, DLQ_CONFIG["max_retries"])
        job_id = f"DLQ-{_now().strftime('%Y%m%d-%H%M%S')}-{id(payload) % 10000:04d}"

        job = {
            "job_id": job_id,
            "job_type": job_type,
            "payload": payload,
            "error": str(error),
            "attempt": 0,
            "max_retries": max_retries,
            "created_at": _ts(),
            "next_retry_at": _ts(),
            "status": "pending",
        }

        with cls._lock:
            queue = _load_json(cls._F_QUEUE, [])
            # Enforce max queue size
            if len(queue) >= DLQ_CONFIG["max_queue_size"]:
                queue = queue[-DLQ_CONFIG["max_queue_size"] + 1:]
            queue.append(job)
            _save_json(cls._F_QUEUE, queue)
        return job_id

    @classmethod
    def process_all(cls) -> dict:
        """Process ready jobs. Returns {retried, exhausted, remaining}."""
        from resilience_config import DLQ_CONFIG
        backoffs = DLQ_CONFIG["backoff_minutes"]
        now = _now()
        retried = 0
        exhausted = 0

        with cls._lock:
            queue = _load_json(cls._F_QUEUE, [])
            remaining = []

            for job in queue:
                if job.get("status") == "completed":
                    continue
                if job.get("status") == "exhausted":
                    # Archive exhausted jobs
                    if DLQ_CONFIG["archive_after_exhaust"]:
                        cls._archive(job)
                    exhausted += 1
                    continue

                # Check if ready for retry
                attempt = job.get("attempt", 0)
                if attempt >= job.get("max_retries", 3):
                    job["status"] = "exhausted"
                    cls._archive(job)
                    exhausted += 1
                    continue

                # Execute retry
                success = cls._retry_job(job)
                if success:
                    job["status"] = "completed"
                    retried += 1
                else:
                    job["attempt"] = attempt + 1
                    # Schedule next retry
                    backoff_idx = min(job["attempt"] - 1, len(backoffs) - 1)
                    next_dt = now + datetime.timedelta(minutes=backoffs[backoff_idx])
                    job["next_retry_at"] = next_dt.strftime("%Y-%m-%d %H:%M:%S IST")
                    job["last_error"] = job.get("error", "Unknown")
                    remaining.append(job)
                    continue

                remaining.append(job)

            _save_json(cls._F_QUEUE, remaining)

        return {"retried": retried, "exhausted": exhausted, "remaining": len(remaining)}

    @classmethod
    def _retry_job(cls, job: dict) -> bool:
        """Attempt to retry a job. Returns True on success."""
        job_type = job.get("job_type", "")
        payload = job.get("payload", {})

        try:
            if job_type == "api_fetch":
                from api_manager import fetch_api_data
                result = fetch_api_data(payload.get("widget_id", ""), force=True)
                return result is not None
            elif job_type == "hub_connector":
                from api_hub_engine import run_single_connector
                return run_single_connector(payload.get("connector_id", ""))
            elif job_type == "sync_step":
                # Re-run a specific sync step
                from sync_engine import SyncEngine
                eng = SyncEngine()
                step_name = payload.get("step_name", "")
                method = getattr(eng, f"_step_{step_name}", None)
                if method:
                    method()
                    return True
            return False
        except Exception as e:
            job["error"] = str(e)
            return False

    @classmethod
    def _archive(cls, job: dict) -> None:
        """Move exhausted job to archive."""
        archive = _load_json(cls._F_ARCHIVE, [])
        job["archived_at"] = _ts()
        archive.append(job)
        archive = archive[-200:]  # keep last 200
        _save_json(cls._F_ARCHIVE, archive)

    @classmethod
    def get_stats(cls) -> dict:
        """Get queue statistics."""
        queue = _load_json(cls._F_QUEUE, [])
        pending = sum(1 for j in queue if j.get("status") == "pending")
        total = len(queue)
        return {"total": total, "pending": pending, "queue_file": str(cls._F_QUEUE)}

    @classmethod
    def get_queue(cls) -> list:
        """Get all items in the queue."""
        return _load_json(cls._F_QUEUE, [])


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LKG CACHE — Last-Known-Good data snapshots
# ═══════════════════════════════════════════════════════════════════════════════

class LKGCache:
    """
    Maintains last-known-good snapshots of all data sources.
    Only saves verified/estimated data (confidence >= 70%).
    Returns data with reduced confidence when used as fallback.

    Usage:
        LKGCache.save_snapshot("crude_prices", data, confidence_pct=92)
        snapshot = LKGCache.get_snapshot("crude_prices")
    """

    @staticmethod
    def _lkg_dir() -> Path:
        from resilience_config import LKG_CONFIG
        d = BASE / LKG_CONFIG["lkg_dir"]
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    def save_snapshot(cls, source_key: str, data: Any,
                      confidence_pct: int = 80) -> bool:
        """Save a snapshot. Only saves if confidence >= threshold."""
        from resilience_config import LKG_CONFIG
        if confidence_pct < LKG_CONFIG["min_confidence_to_save"]:
            return False

        snapshot = {
            "source_key": source_key,
            "data": data,
            "original_confidence": confidence_pct,
            "saved_at": _ts(),
            "saved_epoch": time.time(),
        }
        path = cls._lkg_dir() / f"{source_key}.json"
        _save_json(path, snapshot)
        return True

    @classmethod
    def get_snapshot(cls, source_key: str) -> Optional[dict]:
        """
        Get LKG snapshot. Returns None if expired or doesn't exist.
        Reduces confidence by penalty percentage.
        """
        from resilience_config import LKG_CONFIG
        path = cls._lkg_dir() / f"{source_key}.json"
        snapshot = _load_json(path, None)
        if not snapshot:
            return None

        # Check age
        saved_epoch = snapshot.get("saved_epoch", 0)
        age_hours = (time.time() - saved_epoch) / 3600
        max_age_hours = LKG_CONFIG["max_age_days"] * 24

        if age_hours > max_age_hours:
            return None

        # Reduce confidence
        orig_conf = snapshot.get("original_confidence", 80)
        penalty = LKG_CONFIG["confidence_penalty_pct"]
        floor = LKG_CONFIG["min_confidence_floor"]
        reduced_conf = max(floor, orig_conf - penalty)

        return {
            "data": snapshot["data"],
            "source_key": source_key,
            "confidence_pct": reduced_conf,
            "age_hours": round(age_hours, 1),
            "saved_at": snapshot.get("saved_at", ""),
            "is_lkg": True,
        }

    @classmethod
    def get_all_snapshots(cls) -> dict[str, dict]:
        """Get all LKG snapshots with their status."""
        result = {}
        lkg_dir = cls._lkg_dir()
        for f in lkg_dir.glob("*.json"):
            key = f.stem
            snap = cls.get_snapshot(key)
            if snap:
                result[key] = snap
            else:
                result[key] = {"source_key": key, "status": "expired_or_missing"}
        return result

    @classmethod
    def cleanup_old(cls, max_age_days: int = 7) -> int:
        """Remove LKG snapshots older than max_age_days. Returns count removed."""
        removed = 0
        cutoff = time.time() - (max_age_days * 86400)
        lkg_dir = cls._lkg_dir()
        for f in lkg_dir.glob("*.json"):
            try:
                snap = _load_json(f)
                if snap and snap.get("saved_epoch", 0) < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                pass
        return removed


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CONCURRENT EXECUTOR — Parallel task execution with timeouts
# ═══════════════════════════════════════════════════════════════════════════════

class ConcurrentExecutor:
    """
    ThreadPoolExecutor wrapper with per-task timeout and error collection.

    Usage:
        tasks = [
            {"name": "fetch_crude", "fn": connect_crude, "args": (), "timeout": 60},
            {"name": "fetch_fx",    "fn": connect_fx,    "args": (), "timeout": 30},
        ]
        results = ConcurrentExecutor.run_parallel(tasks, max_workers=5)
    """

    @staticmethod
    def run_parallel(tasks: list[dict], max_workers: int = 5,
                     timeout_per_task: int = 60) -> list[dict]:
        """
        Execute tasks in parallel with per-task timeout.
        Each task: {"name": str, "fn": callable, "args": tuple, "timeout": int}
        Returns: [{"name", "result", "error", "duration_ms"}]
        """
        results = []

        if not tasks:
            return results

        workers = min(max_workers, len(tasks))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for task in tasks:
                fn = task["fn"]
                args = task.get("args", ())
                kwargs = task.get("kwargs", {})
                future = pool.submit(fn, *args, **kwargs)
                futures[future] = task

            for future in futures:
                task = futures[future]
                name = task["name"]
                timeout = task.get("timeout", timeout_per_task)
                t0 = time.time()

                try:
                    result = future.result(timeout=timeout)
                    duration = round((time.time() - t0) * 1000)
                    results.append({
                        "name": name,
                        "result": result,
                        "error": None,
                        "duration_ms": duration,
                        "success": True,
                    })
                except FuturesTimeout:
                    duration = round((time.time() - t0) * 1000)
                    results.append({
                        "name": name,
                        "result": None,
                        "error": f"Timeout after {timeout}s",
                        "duration_ms": duration,
                        "success": False,
                    })
                except Exception as e:
                    duration = round((time.time() - t0) * 1000)
                    results.append({
                        "name": name,
                        "result": None,
                        "error": str(e),
                        "duration_ms": duration,
                        "success": False,
                    })

        return results


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GRACEFUL DEGRADATION — Output continuity when inputs fail
# ═══════════════════════════════════════════════════════════════════════════════

class GracefulDegradation:
    """
    Ensures outputs continue with reduced confidence when inputs fail.
    Walks the fallback chain: live API → LKG cache → static reference → emergency.

    Usage:
        result = GracefulDegradation.get_best_available("crude_prices")
        # → {"data": {...}, "source": "yfinance", "confidence_pct": 95, "is_degraded": False}
    """

    @classmethod
    def get_best_available(cls, category: str) -> dict:
        """
        Walk the fallback matrix for a category.
        Returns the best available data source.
        """
        from resilience_config import FALLBACK_MATRIX

        matrix = FALLBACK_MATRIX.get(category)
        if not matrix:
            return {
                "data": None,
                "source": "none",
                "confidence_pct": 0,
                "is_degraded": True,
                "level": "emergency",
                "label": "No fallback matrix defined",
            }

        # Try each level in order
        for level in ("primary", "secondary", "tertiary", "emergency"):
            entry = matrix.get(level)
            if not entry:
                continue

            source = entry.get("source", "")
            confidence = entry.get("confidence", 50)

            # Check if source requires a key and if it's configured
            if entry.get("requires_key"):
                try:
                    from settings_engine import get as sg
                    key_setting = entry.get("key_setting", "")
                    enabled_setting = f"{key_setting}_enabled"
                    key_val = sg(key_setting, "")
                    enabled = sg(enabled_setting, False)
                    if not key_val or not enabled:
                        continue  # Skip this level — key not configured
                except Exception:
                    continue

            # Try to get live data for this source
            if entry.get("type") in ("free_api", "keyed_api", "free_rss"):
                data = cls._try_live_source(category, source)
                if data is not None:
                    # Save as LKG on success
                    LKGCache.save_snapshot(category, data, confidence)
                    return {
                        "data": data,
                        "source": entry.get("label", source),
                        "confidence_pct": confidence,
                        "is_degraded": level != "primary",
                        "level": level,
                        "label": entry.get("label", source),
                    }

            elif entry.get("type") == "last_known_good":
                lkg = LKGCache.get_snapshot(category)
                if lkg and lkg.get("data"):
                    return {
                        "data": lkg["data"],
                        "source": f"LKG Cache ({lkg.get('age_hours', '?')}h old)",
                        "confidence_pct": lkg["confidence_pct"],
                        "is_degraded": True,
                        "level": level,
                        "label": entry.get("label", "Last-Known-Good"),
                    }

            elif entry.get("type") in ("static", "local", "manual"):
                value = entry.get("value")
                if value is not None:
                    return {
                        "data": value,
                        "source": entry.get("label", source),
                        "confidence_pct": confidence,
                        "is_degraded": True,
                        "level": level,
                        "label": entry.get("label", source),
                    }
                elif entry.get("type") == "local":
                    # system_time — python datetime
                    if source == "python_datetime_ist":
                        return {
                            "data": {"time": _now().strftime("%H:%M:%S IST")},
                            "source": "Python datetime",
                            "confidence_pct": confidence,
                            "is_degraded": True,
                            "level": level,
                            "label": entry.get("label", source),
                        }

        # All levels exhausted
        return {
            "data": None,
            "source": "none",
            "confidence_pct": 0,
            "is_degraded": True,
            "level": "exhausted",
            "label": "All fallback sources exhausted",
        }

    @classmethod
    def _try_live_source(cls, category: str, source: str) -> Optional[Any]:
        """Attempt to fetch data from a live source. Returns data or None."""
        try:
            if category == "crude_prices" and source == "yfinance":
                from api_manager import fetch_api_data
                brent = fetch_api_data("brent")
                wti = fetch_api_data("wti")
                if brent or wti:
                    return {"brent": brent, "wti": wti}
            elif category == "fx_rates" and source in ("fawazahmed0_cdn", "frankfurter_ecb"):
                from api_manager import fetch_api_data
                fx = fetch_api_data("usdinr")
                if fx:
                    return fx
            elif category == "weather" and source == "open_meteo":
                from api_manager import fetch_api_data
                w = fetch_api_data("weather_mumbai")
                if w:
                    return w
            elif category == "news":
                from api_manager import fetch_api_data
                return fetch_api_data("google_news") or True
            elif category == "system_time":
                from api_manager import fetch_api_data
                return fetch_api_data("current_time")
        except Exception:
            pass
        return None

    @staticmethod
    def compute_output_confidence(input_confidences: list[int],
                                  weights: Optional[list[float]] = None) -> int:
        """
        Compute weighted output confidence from input confidences.
        Returns 0-100 score.
        """
        if not input_confidences:
            return 0
        if weights and len(weights) == len(input_confidences):
            total_w = sum(weights)
            if total_w > 0:
                score = sum(c * w for c, w in zip(input_confidences, weights)) / total_w
                return max(0, min(100, round(score)))
        return max(0, min(100, round(sum(input_confidences) / len(input_confidences))))

    @staticmethod
    def confidence_html_badge(confidence_pct: int) -> str:
        """Return an HTML badge for confidence level."""
        from resilience_config import confidence_badge
        badge = confidence_badge(confidence_pct)
        return (
            f'<span style="background:{badge["color"]}20;color:{badge["color"]};'
            f'padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:600;">'
            f'{badge["emoji"]} {confidence_pct}% {badge["label"]}</span>'
        )
