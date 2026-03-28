"""
log_engine.py — Centralized Structured Logging
================================================
JSON-lines formatted logs with rotation.
Replaces ad-hoc JSON logging across all engines.

Usage:
    from log_engine import dashboard_log
    dashboard_log.info("sync_engine", "data_refresh", "Refreshed crude prices", records=50)
    dashboard_log.error("api_hub", "connect_eia", "Timeout", error="ConnectionTimeout")
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)

DEFAULT_LOG_FILE = LOG_DIR / "dashboard.log"
MAX_SIZE_MB = 5
BACKUP_COUNT = 3


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


class DashboardLogger:
    """Centralized structured logger with JSON-lines format and rotation."""

    def __init__(
        self,
        name: str = "dashboard",
        log_file: Path | str | None = None,
        max_size_mb: int = MAX_SIZE_MB,
        backup_count: int = BACKUP_COUNT,
    ):
        self.name = name
        self._log_file = Path(log_file) if log_file else DEFAULT_LOG_FILE

        # Set up Python logger with rotating file handler
        self._logger = logging.getLogger(f"pps_{name}")
        self._logger.setLevel(logging.DEBUG)

        if not self._logger.handlers:
            handler = RotatingFileHandler(
                self._log_file,
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def _log(self, level: str, component: str, action: str,
             details: str = "", error: str = "", **extra) -> dict:
        """Write a structured JSON-lines log entry."""
        entry = {
            "ts": _now_ist(),
            "level": level,
            "component": component,
            "action": action,
            "details": details,
        }
        if error:
            entry["error"] = error
        if extra:
            entry.update(extra)

        try:
            line = json.dumps(entry, ensure_ascii=False, default=str)
            self._logger.log(
                getattr(logging, level, logging.INFO),
                line,
            )
        except Exception:
            pass

        return entry

    def info(self, component: str, action: str, details: str = "", **extra):
        return self._log("INFO", component, action, details, **extra)

    def warning(self, component: str, action: str, details: str = "", **extra):
        return self._log("WARNING", component, action, details, **extra)

    def error(self, component: str, action: str, details: str = "", error: str = "", **extra):
        return self._log("ERROR", component, action, details, error=error, **extra)

    def debug(self, component: str, action: str, details: str = "", **extra):
        return self._log("DEBUG", component, action, details, **extra)

    # ── Query Logs ────────────────────────────────────────────────────────────

    def get_recent(
        self,
        component: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Read and filter recent log entries."""
        entries = []
        try:
            if self._log_file.exists():
                with open(self._log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if component and entry.get("component") != component:
                                continue
                            if level and entry.get("level") != level:
                                continue
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return entries[-limit:]

    def get_stats(self) -> dict:
        """Get log statistics by component and level."""
        entries = self.get_recent(limit=10000)
        stats = {
            "total": len(entries),
            "by_level": {},
            "by_component": {},
        }
        for e in entries:
            lvl = e.get("level", "UNKNOWN")
            comp = e.get("component", "unknown")
            stats["by_level"][lvl] = stats["by_level"].get(lvl, 0) + 1
            stats["by_component"][comp] = stats["by_component"].get(comp, 0) + 1
        return stats

    def clear(self):
        """Clear all log entries (for maintenance)."""
        try:
            with open(self._log_file, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass


# ── Module-level singleton ────────────────────────────────────────────────────

dashboard_log = DashboardLogger("dashboard")
