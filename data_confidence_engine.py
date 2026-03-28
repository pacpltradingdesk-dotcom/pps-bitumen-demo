"""
data_confidence_engine.py — Data Confidence & Freshness Scoring
================================================================
Every data source gets: Verified / Estimated / Stale / Unavailable.
No silent "N/A" or fake data shown as real.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

LOG = logging.getLogger("data_confidence")

# ── Paths ────────────────────────────────────────────────────────────────────
_BASE = Path(__file__).resolve().parent
_TBL_CRUDE    = _BASE / "tbl_crude_prices.json"
_TBL_FX       = _BASE / "tbl_fx_rates.json"
_TBL_WEATHER  = _BASE / "tbl_weather.json"
_TBL_NEWS     = _BASE / "tbl_news_feed.json"
_TBL_TRADE    = _BASE / "tbl_imports_countrywise.json"
_TBL_PORTS    = _BASE / "tbl_ports_volume.json"
_TBL_REFINERY = _BASE / "tbl_refinery_production.json"
_NEWS_ARTICLES = _BASE / "news_data" / "articles.json"

# ── IST timezone ─────────────────────────────────────────────────────────────
try:
    import pytz
    _IST = pytz.timezone("Asia/Kolkata")
except Exception:
    _IST = None


def _now_ist() -> datetime:
    if _IST:
        return datetime.now(_IST)
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def _parse_ts(ts_str: str) -> Optional[datetime]:
    """Parse common timestamp formats from records."""
    if not ts_str:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S IST",
        "%Y-%m-%d %H:%M IST",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(ts_str.strip().replace(" IST", ""), fmt.replace(" IST", ""))
            return dt
        except ValueError:
            continue
    return None


def _load_json(path: Path) -> list:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _latest_record_time(records: list) -> Optional[datetime]:
    """Find the most recent timestamp across records."""
    latest = None
    for rec in records[-50:]:  # check last 50 for speed
        ts_str = rec.get("date_time") or rec.get("timestamp") or rec.get("fetched_at") or ""
        dt = _parse_ts(ts_str)
        if dt and (latest is None or dt > latest):
            latest = dt
    return latest


def _latest_source(records: list) -> str:
    """Get source field from most recent record."""
    for rec in reversed(records[-20:]):
        src = rec.get("source", "")
        if src:
            return src
    return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CONFIDENCE DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DataConfidence:
    source_name:       str    # "Crude Oil Prices"
    source_key:        str    # "crude_prices"
    source_type:       str    # "api" | "computed" | "static" | "user_input"
    confidence:        str    # "verified" | "estimated" | "stale" | "unavailable"
    confidence_score:  int    # 0-100
    freshness_minutes: int    # minutes since last update
    provider:          str    # "yfinance (EIA fallback)"
    last_updated:      str    # IST timestamp string
    notes:             str    # explanation
    record_count:      int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE SCORING LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def _score_freshness(minutes: int, source_type: str) -> tuple:
    """
    Score freshness and assign confidence label.
    Returns: (confidence_label, confidence_score)
    """
    if minutes < 0:
        return "unavailable", 0

    if source_type == "api":
        if minutes <= 120:       # < 2 hours
            return "verified", max(80, 100 - minutes // 3)
        elif minutes <= 360:     # 2-6 hours
            return "estimated", max(50, 80 - (minutes - 120) // 6)
        elif minutes <= 1440:    # 6-24 hours
            return "stale", max(20, 50 - (minutes - 360) // 30)
        else:
            return "stale", max(10, 20 - (minutes - 1440) // 120)

    elif source_type == "static":
        # Static reference data — always estimated unless very old
        if minutes <= 43200:     # < 30 days
            return "estimated", 65
        elif minutes <= 129600:  # < 90 days
            return "stale", 40
        else:
            return "stale", 25

    elif source_type == "computed":
        if minutes <= 360:
            return "verified", 75
        elif minutes <= 1440:
            return "estimated", 55
        else:
            return "stale", 30

    # Default
    if minutes <= 120:
        return "verified", 85
    elif minutes <= 720:
        return "estimated", 55
    else:
        return "stale", 25


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE-SPECIFIC CONFIDENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_SOURCE_DEFS = {
    "crude_prices": {
        "name": "Crude Oil Prices",
        "file": _TBL_CRUDE,
        "source_type": "api",
        "primary_provider": "EIA",
        "fallback_note": "yfinance fallback when EIA key missing",
    },
    "fx_rates": {
        "name": "FX Exchange Rates",
        "file": _TBL_FX,
        "source_type": "api",
        "primary_provider": "Frankfurter (ECB)",
        "fallback_note": "fawazahmed0 CDN fallback",
    },
    "weather": {
        "name": "Weather Data",
        "file": _TBL_WEATHER,
        "source_type": "api",
        "primary_provider": "Open-Meteo",
        "fallback_note": "Open-Meteo fallback when OpenWeather key missing",
    },
    "news_feed": {
        "name": "News Feed",
        "file": _TBL_NEWS,
        "source_type": "api",
        "primary_provider": "NewsAPI / Google RSS",
        "fallback_note": "Google News RSS fallback",
    },
    "trade_imports": {
        "name": "Trade Imports (Countrywise)",
        "file": _TBL_TRADE,
        "source_type": "api",
        "primary_provider": "UN Comtrade",
        "fallback_note": "Cached reference when API unavailable",
    },
    "ports_volume": {
        "name": "Port Cargo Volumes",
        "file": _TBL_PORTS,
        "source_type": "computed",
        "primary_provider": "BDI-adjusted estimate",
        "fallback_note": "No free auto-API — always estimated from Baltic Dry Index",
    },
    "refinery_production": {
        "name": "Refinery Production",
        "file": _TBL_REFINERY,
        "source_type": "static",
        "primary_provider": "PPAC / EIA",
        "fallback_note": "PPAC static reference when EIA unavailable",
    },
    "news_articles": {
        "name": "News Articles (NLP)",
        "file": _NEWS_ARTICLES,
        "source_type": "api",
        "primary_provider": "NewsAPI + Google RSS",
        "fallback_note": "NLP-processed articles",
    },
}


def get_data_confidence(source_key: str) -> DataConfidence:
    """Returns confidence for a specific data source."""
    defn = _SOURCE_DEFS.get(source_key)
    if not defn:
        return DataConfidence(
            source_name=source_key,
            source_key=source_key,
            source_type="unknown",
            confidence="unavailable",
            confidence_score=0,
            freshness_minutes=-1,
            provider="unknown",
            last_updated="N/A",
            notes="Unknown data source key",
            record_count=0,
        )

    records = _load_json(defn["file"])
    now = _now_ist()
    latest_dt = _latest_record_time(records)
    provider = _latest_source(records) if records else defn["primary_provider"]

    if not records or latest_dt is None:
        return DataConfidence(
            source_name=defn["name"],
            source_key=source_key,
            source_type=defn["source_type"],
            confidence="unavailable",
            confidence_score=0,
            freshness_minutes=-1,
            provider=defn["primary_provider"],
            last_updated="No data",
            notes=f"No records found — {defn['fallback_note']}",
            record_count=0,
        )

    # Calculate freshness
    # Make both datetimes naive for comparison
    now_naive = now.replace(tzinfo=None) if now.tzinfo else now
    latest_naive = latest_dt.replace(tzinfo=None) if latest_dt.tzinfo else latest_dt
    delta = now_naive - latest_naive
    minutes = max(0, int(delta.total_seconds() / 60))

    # Apply source-type specific adjustments
    source_type = defn["source_type"]
    confidence_label, confidence_score = _score_freshness(minutes, source_type)

    # Adjust for known weak sources
    is_fallback = "fallback" in provider.lower() or "cached" in provider.lower()
    if is_fallback and confidence_label == "verified":
        confidence_label = "estimated"
        confidence_score = min(confidence_score, 75)

    if source_key == "ports_volume":
        confidence_label = "estimated"
        confidence_score = min(confidence_score, 65)

    if source_key == "trade_imports" and "cached" in provider.lower():
        confidence_label = "stale"
        confidence_score = min(confidence_score, 45)

    notes = provider
    if is_fallback:
        notes += f" — {defn['fallback_note']}"

    return DataConfidence(
        source_name=defn["name"],
        source_key=source_key,
        source_type=source_type,
        confidence=confidence_label,
        confidence_score=confidence_score,
        freshness_minutes=minutes,
        provider=provider,
        last_updated=latest_dt.strftime("%Y-%m-%d %H:%M IST"),
        notes=notes,
        record_count=len(records),
    )


def get_all_confidences() -> List[DataConfidence]:
    """Returns confidence for ALL tracked data sources."""
    return [get_data_confidence(key) for key in _SOURCE_DEFS]


def get_overall_health() -> dict:
    """Returns summary health across all data sources."""
    confs = get_all_confidences()
    total = len(confs)
    counts = {"verified": 0, "estimated": 0, "stale": 0, "unavailable": 0}
    for c in confs:
        counts[c.confidence] = counts.get(c.confidence, 0) + 1

    avg_score = sum(c.confidence_score for c in confs) / total if total else 0

    if counts["unavailable"] >= 2:
        overall = "degraded"
    elif counts["stale"] >= 3:
        overall = "partial"
    elif counts["verified"] >= total // 2:
        overall = "healthy"
    else:
        overall = "partial"

    return {
        "overall": overall,
        "average_score": round(avg_score, 1),
        "counts": counts,
        "total_sources": total,
        "sources": [c.to_dict() for c in confs],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STREAMLIT UI RENDERING
# ═══════════════════════════════════════════════════════════════════════════════

_BADGE_COLORS = {
    "verified":    ("#2d6a4f", "#d4edda", "Verified"),     # green
    "estimated":   ("#856404", "#fff3cd", "Estimated"),     # yellow
    "stale":       ("#a04000", "#ffe0cc", "Stale"),         # orange
    "unavailable": ("#721c24", "#f8d7da", "Unavailable"),   # red
}


def render_confidence_badge(conf: DataConfidence) -> str:
    """Returns inline HTML for a confidence badge."""
    fg, bg, label = _BADGE_COLORS.get(conf.confidence, ("#333", "#eee", "Unknown"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:4px;font-size:0.8em;font-weight:600;">'
        f'{label} ({conf.confidence_score}%)</span>'
    )


def render_confidence_bar() -> None:
    """Renders a compact top-of-page bar showing overall data health."""
    try:
        import streamlit as st
    except ImportError:
        return

    health = get_overall_health()
    counts = health["counts"]
    overall = health["overall"]

    if overall == "healthy":
        bar_color = "#2d6a4f"
        bar_bg = "#d4edda"
        icon = "✅"
    elif overall == "partial":
        bar_color = "#856404"
        bar_bg = "#fff3cd"
        icon = "⚠️"
    else:
        bar_color = "#a04000"
        bar_bg = "#ffe0cc"
        icon = "🔴"

    parts = []
    if counts["verified"]:
        parts.append(f'<span style="color:#2d6a4f;">■ {counts["verified"]} Verified</span>')
    if counts["estimated"]:
        parts.append(f'<span style="color:#856404;">■ {counts["estimated"]} Estimated</span>')
    if counts["stale"]:
        parts.append(f'<span style="color:#a04000;">■ {counts["stale"]} Stale</span>')
    if counts["unavailable"]:
        parts.append(f'<span style="color:#721c24;">■ {counts["unavailable"]} Unavailable</span>')

    status_text = " &nbsp;|&nbsp; ".join(parts)

    st.markdown(
        f'<div style="background:{bar_bg};color:{bar_color};padding:6px 16px;'
        f'border-radius:6px;margin-bottom:8px;font-size:0.85em;">'
        f'{icon} <strong>Data Health:</strong> {status_text} '
        f'&nbsp;(avg score: {health["average_score"]}%)</div>',
        unsafe_allow_html=True,
    )


def render_source_footnote(source_keys: list) -> None:
    """Renders footnote showing source attribution for displayed data."""
    try:
        import streamlit as st
    except ImportError:
        return

    if not source_keys:
        return

    lines = []
    for key in source_keys:
        conf = get_data_confidence(key)
        badge = render_confidence_badge(conf)
        age = ""
        if conf.freshness_minutes >= 0:
            if conf.freshness_minutes < 60:
                age = f"{conf.freshness_minutes}m ago"
            elif conf.freshness_minutes < 1440:
                age = f"{conf.freshness_minutes // 60}h ago"
            else:
                age = f"{conf.freshness_minutes // 1440}d ago"

        lines.append(
            f'<span style="font-size:0.78em;color:#666;">'
            f'{badge} <strong>{conf.source_name}</strong> — '
            f'{conf.provider} · {age} · {conf.record_count} records</span>'
        )

    footnote_html = "<br>".join(lines)
    st.markdown(
        f'<div style="border-top:1px solid #ddd;padding-top:6px;margin-top:10px;">'
        f'<span style="font-size:0.75em;color:#888;font-weight:600;">📊 Data Sources</span><br>'
        f'{footnote_html}</div>',
        unsafe_allow_html=True,
    )


def render_data_health_card() -> None:
    """Renders a summary card for the Home page showing data source status."""
    try:
        import streamlit as st
    except ImportError:
        return

    health = get_overall_health()
    sources = health["sources"]

    with st.expander("📊 Data Source Health", expanded=False):
        for src in sources:
            conf_obj = DataConfidence(**src)
            badge = render_confidence_badge(conf_obj)
            age = ""
            if conf_obj.freshness_minutes >= 0:
                if conf_obj.freshness_minutes < 60:
                    age = f"{conf_obj.freshness_minutes}m ago"
                elif conf_obj.freshness_minutes < 1440:
                    age = f"{conf_obj.freshness_minutes // 60}h ago"
                else:
                    age = f"{conf_obj.freshness_minutes // 1440}d ago"
            else:
                age = "no data"

            st.markdown(
                f'{badge} **{conf_obj.source_name}** — '
                f'{conf_obj.provider} · {age} · {conf_obj.record_count} records',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# GRACEFUL DEGRADATION — Fallback-aware confidence
# ═══════════════════════════════════════════════════════════════════════════════

def get_source_with_fallback(source_key: str) -> dict:
    """
    Get data for a source, walking the fallback chain if needed.
    Returns: {"data", "source", "confidence_pct", "is_degraded", "level"}
    """
    try:
        from resilience_manager import GracefulDegradation
        # Map data_confidence keys → fallback matrix categories
        _KEY_TO_CATEGORY = {
            "crude_prices": "crude_prices",
            "fx_rates": "fx_rates",
            "weather": "weather",
            "news_feed": "news",
            "news_articles": "news",
            "trade_imports": "trade_data",
            "ports_volume": "trade_data",
            "refinery_production": "trade_data",
        }
        category = _KEY_TO_CATEGORY.get(source_key, source_key)
        return GracefulDegradation.get_best_available(category)
    except ImportError:
        # Fallback: return standard confidence without degradation info
        conf = get_data_confidence(source_key)
        return {
            "data": None,
            "source": conf.provider,
            "confidence_pct": conf.confidence_score,
            "is_degraded": conf.confidence in ("stale", "unavailable"),
            "level": "primary" if conf.confidence == "verified" else "secondary",
        }


def compute_dashboard_confidence() -> dict:
    """
    Compute aggregate dashboard health from all sources.
    Returns: {"score", "color", "label", "degraded_sources", "source_details"}
    """
    confs = get_all_confidences()
    scores = [c.confidence_score for c in confs]
    degraded = [c.source_name for c in confs if c.confidence in ("stale", "unavailable")]

    try:
        from resilience_config import compute_health_score
        metrics = {"data_freshness": sum(scores) / len(scores) if scores else 0}
        result = compute_health_score(metrics)
    except ImportError:
        avg = sum(scores) / len(scores) if scores else 0
        result = {"score": round(avg), "color": "#f59e0b", "label": "Unknown"}

    result["degraded_sources"] = degraded
    result["source_details"] = [
        {"name": c.source_name, "confidence": c.confidence,
         "score": c.confidence_score, "age_min": c.freshness_minutes}
        for c in confs
    ]
    return result
