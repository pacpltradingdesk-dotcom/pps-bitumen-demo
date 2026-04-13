"""
Freshness Guard
===============
On-app-load cache freshness checker. Solves the problem where background
schedulers die when the Streamlit app sleeps/restarts, leaving stale data.

Strategy:
  - Cache < SOFT_LIMIT min old  -> do nothing
  - SOFT_LIMIT <= age < HARD_LIMIT min -> kick background refresh (non-blocking)
  - Cache >= HARD_LIMIT min or missing -> synchronous refresh with spinner

A session-level lock prevents duplicate concurrent refreshes.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent

# Files that must stay fresh for the Home page
MARKET_CACHE = ROOT / "hub_cache.json"
NEWS_CACHE   = ROOT / "tbl_news_feed.json"

SOFT_LIMIT_MIN = 30    # Background refresh if older than this
HARD_LIMIT_MIN = 360   # Block-and-wait refresh if older than this (6 hrs)

_refresh_lock = threading.Lock()
_last_refresh_ts = 0.0
_MIN_INTERVAL_SEC = 120  # Never refresh more than once per 2 min per process


def _age_minutes(path: Path) -> float:
    """Return file age in minutes. Returns infinity if missing."""
    try:
        if not path.exists():
            return float("inf")
        return (time.time() - path.stat().st_mtime) / 60.0
    except Exception:
        return float("inf")


def _do_refresh(reason: str = "") -> dict:
    """Call the API hub to refresh all cached data. Returns summary dict."""
    global _last_refresh_ts
    now = time.time()
    if now - _last_refresh_ts < _MIN_INTERVAL_SEC:
        return {"skipped": True, "reason": "rate-limited"}

    # Only one refresh at a time
    if not _refresh_lock.acquire(blocking=False):
        return {"skipped": True, "reason": "already-running"}

    try:
        _last_refresh_ts = now
        try:
            from api_hub_engine import run_all_connectors
            result = run_all_connectors(force=True)
        except Exception as e:
            result = {"error": str(e)}

        # Also refresh the raw news articles pool (separate from tbl_news_feed)
        try:
            from news_engine import run_fetch_cycle
            run_fetch_cycle()
        except Exception:
            pass

        result["_triggered_by"] = reason
        result["_finished_at"] = time.time()
        return result
    finally:
        _refresh_lock.release()


def _refresh_in_background(reason: str):
    t = threading.Thread(target=_do_refresh, args=(reason,),
                         daemon=True, name="freshness_guard_bg")
    t.start()


def ensure_fresh(show_spinner: bool = True) -> dict:
    """
    Call at the top of any page that shows live prices/news.
    Returns status dict for optional UI display.

    Safe to call every rerun — internally rate-limited.
    """
    market_age = _age_minutes(MARKET_CACHE)
    news_age   = _age_minutes(NEWS_CACHE)
    worst_age  = max(market_age, news_age)

    status = {
        "market_age_min": round(market_age, 1) if market_age != float("inf") else None,
        "news_age_min":   round(news_age, 1)   if news_age   != float("inf") else None,
        "action": "fresh",
    }

    # Hard-stale: block and fetch
    if worst_age >= HARD_LIMIT_MIN:
        status["action"] = "sync-refresh"
        if show_spinner:
            try:
                import streamlit as st
                with st.spinner("Fetching latest market data & news…"):
                    status["result"] = _do_refresh(reason="hard-stale")
            except Exception:
                status["result"] = _do_refresh(reason="hard-stale")
        else:
            status["result"] = _do_refresh(reason="hard-stale")
        return status

    # Soft-stale: background refresh, user sees cached data now, fresh on next rerun
    if worst_age >= SOFT_LIMIT_MIN:
        status["action"] = "bg-refresh"
        _refresh_in_background("soft-stale")
        return status

    return status


def get_cache_freshness() -> dict:
    """Lightweight age reporter for UI 'Last updated' badges."""
    return {
        "market_age_min": _age_minutes(MARKET_CACHE),
        "news_age_min":   _age_minutes(NEWS_CACHE),
    }
