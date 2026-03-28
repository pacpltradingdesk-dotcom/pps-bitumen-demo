"""
auto_insight_engine.py — Auto-Generated Dashboard Insights
============================================================
LLM auto-analyzes dashboard data and generates daily insights.
Uses ai_fallback_engine for free LLM access — no new dependencies.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent
INSIGHTS_FILE = BASE / "auto_insights.json"

LOG = logging.getLogger("auto_insight")


def _now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _now_date() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def _load_insights() -> list[dict]:
    try:
        if INSIGHTS_FILE.exists():
            data = json.loads(INSIGHTS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _save_insights(insights: list[dict]) -> None:
    # Keep rolling 30-day history
    if len(insights) > 90:
        insights = insights[-90:]
    try:
        INSIGHTS_FILE.write_text(
            json.dumps(insights, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        LOG.warning("Failed to save insights: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA COLLECTORS
# ═══════════════════════════════════════════════════════════════════════════════

def _collect_price_data() -> str:
    """Collect price context for insight generation."""
    try:
        data = json.loads((BASE / "tbl_crude_prices.json").read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            latest = data[-1]
            brent = latest.get("brent_usd", "N/A")
            wti = latest.get("wti_usd", "N/A")
            return f"Crude prices: Brent ${brent}/bbl, WTI ${wti}/bbl"
    except Exception:
        pass
    return "Crude price data unavailable"


def _collect_fx_data() -> str:
    try:
        data = json.loads((BASE / "tbl_fx_rates.json").read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            latest = data[-1]
            usd_inr = latest.get("USD_INR", latest.get("usd_inr", "N/A"))
            return f"FX Rate: USD/INR = {usd_inr}"
    except Exception:
        pass
    return "FX data unavailable"


def _collect_demand_data() -> str:
    try:
        from database import _get_conn
        conn = _get_conn()
        rows = conn.execute(
            "SELECT state, AVG(composite_score) as avg_score "
            "FROM infra_demand_scores GROUP BY state "
            "ORDER BY avg_score DESC LIMIT 5"
        ).fetchall()
        conn.close()
        if rows:
            lines = [f"{r[0]}: score {round(r[1], 1)}" for r in rows]
            return "Top demand states: " + ", ".join(lines)
    except Exception:
        pass
    return "Demand data unavailable"


def _collect_anomaly_data() -> str:
    try:
        from anomaly_engine import get_anomaly_summary
        summary = get_anomaly_summary()
        if summary.get("total_anomalies", 0) > 0:
            return (f"Anomaly alert ({summary['alert_level']}): "
                    f"{summary['total_anomalies']} anomalies detected, "
                    f"{summary['high_severity_count']} high severity")
    except Exception:
        pass
    return "No anomalies detected"


def _collect_sentiment_data() -> str:
    try:
        from finbert_engine import get_market_sentiment
        sentiment = get_market_sentiment()
        if sentiment.get("article_count", 0) > 0:
            return (f"Market sentiment: {sentiment['overall']} "
                    f"(trend: {sentiment['trend']}, "
                    f"score: {sentiment['score']}, "
                    f"{sentiment['article_count']} articles)")
    except Exception:
        pass
    return "Market sentiment data unavailable"


def _collect_data_health() -> str:
    try:
        from data_confidence_engine import get_overall_health
        health = get_overall_health()
        counts = health.get("counts", {})
        return (f"Data health: {health['overall']} "
                f"(avg score: {health['average_score']}%, "
                f"verified: {counts.get('verified', 0)}, "
                f"stale: {counts.get('stale', 0)})")
    except Exception:
        pass
    return "Data health check unavailable"


# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_daily_insights() -> dict:
    """
    Auto-analyze dashboard data and generate insights.
    Called from sync_engine after data refresh.
    """
    # Collect all data points
    data_points = [
        _collect_price_data(),
        _collect_fx_data(),
        _collect_demand_data(),
        _collect_anomaly_data(),
        _collect_sentiment_data(),
        _collect_data_health(),
    ]

    context = "\n".join(f"- {dp}" for dp in data_points)

    # Generate insights via LLM
    # Inject business context
    biz_ctx = ""
    try:
        from business_context import get_business_context
        biz_ctx = get_business_context("general") + "\n\n"
    except Exception:
        pass

    prompt = (
        f"You are a bitumen sales intelligence analyst for PPS Anantam Capital Pvt Ltd. "
        f"Today is {_now_date()}.\n\n{biz_ctx}"
        f"Current dashboard data:\n{context}\n\n"
        f"Generate 3-5 actionable insights for bitumen sales decision-making. "
        f"For each insight provide:\n"
        f"1. A short title (max 10 words)\n"
        f"2. A brief explanation (2-3 sentences)\n"
        f"3. Severity: 'info', 'warning', or 'action_required'\n"
        f"4. Category: 'pricing', 'demand', 'market', 'risk', or 'opportunity'\n\n"
        f"Format as JSON array: "
        f'[{{"title": "...", "body": "...", "severity": "...", "category": "..."}}]'
    )

    insights = []
    model_used = "rule"

    try:
        from ai_fallback_engine import ask_with_fallback
        result = ask_with_fallback(prompt)
        if result and not result.get("error"):
            answer = result.get("answer", "")
            # Try to parse JSON from response
            parsed = _extract_json_array(answer)
            if parsed:
                insights = parsed
                model_used = result.get("model", "ai")
    except Exception as e:
        LOG.warning("LLM insight generation failed: %s", e)

    # Fallback: rule-based insights
    if not insights:
        insights = _generate_rule_insights(data_points)
        model_used = "rule"

    result = {
        "insights": insights,
        "generated_at": _now_ist(),
        "date": _now_date(),
        "model": model_used,
        "data_points_used": len(data_points),
    }

    # Save to history
    history = _load_insights()
    history.append(result)
    _save_insights(history)

    return result


def _extract_json_array(text: str) -> list[dict]:
    """Try to extract a JSON array from LLM output."""
    import re
    # Look for [...] pattern
    match = re.search(r'\[[\s\S]*?\]', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []


def _generate_rule_insights(data_points: list[str]) -> list[dict]:
    """Rule-based insight generation fallback."""
    insights = []

    for dp in data_points:
        dp_lower = dp.lower()

        if "brent" in dp_lower and "$" in dp:
            try:
                import re
                price_match = re.search(r'\$(\d+\.?\d*)', dp)
                if price_match:
                    price = float(price_match.group(1))
                    if price > 85:
                        insights.append({
                            "title": "Crude prices elevated",
                            "body": f"Brent at ${price}/bbl. High crude costs may push bitumen prices up. Consider forward buying or locking prices with key customers.",
                            "severity": "warning",
                            "category": "pricing",
                        })
                    elif price < 70:
                        insights.append({
                            "title": "Crude prices favorable",
                            "body": f"Brent at ${price}/bbl. Lower crude costs create margin opportunity. Good time to reactivate price-sensitive customers.",
                            "severity": "info",
                            "category": "opportunity",
                        })
            except Exception:
                pass

        if "anomaly" in dp_lower and "high" in dp_lower:
            insights.append({
                "title": "Anomalies detected in data",
                "body": dp,
                "severity": "action_required",
                "category": "risk",
            })

        if "sentiment" in dp_lower:
            if "negative" in dp_lower or "bearish" in dp_lower:
                insights.append({
                    "title": "Market sentiment turning negative",
                    "body": f"News sentiment analysis shows bearish trend. Monitor for demand slowdown signals.",
                    "severity": "warning",
                    "category": "market",
                })

    if not insights:
        insights.append({
            "title": "Market conditions stable",
            "body": "No significant changes detected. Maintain current pricing and outreach strategy.",
            "severity": "info",
            "category": "market",
        })

    return insights


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE-LEVEL INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_page_insight(page_name: str, data_context: dict) -> str:
    """Generate insight text for a specific dashboard page."""
    try:
        from ai_fallback_engine import ask_with_fallback
        prompt = (
            f"Generate a 1-2 sentence insight for the '{page_name}' page of a "
            f"bitumen sales dashboard. Current data: {json.dumps(data_context, default=str)[:500]}. "
            f"Be specific and actionable."
        )
        result = ask_with_fallback(prompt)
        if result and not result.get("error"):
            return result.get("answer", "")[:200]
    except Exception:
        pass
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# HISTORY ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

def get_insight_history(days: int = 7) -> list[dict]:
    """Returns past daily insights for trend analysis."""
    history = _load_insights()
    if not history:
        return []

    cutoff = (datetime.now(IST) - timedelta(days=days)).strftime("%Y-%m-%d")
    return [h for h in history if h.get("date", "") >= cutoff]


def schedule_insights() -> None:
    """Called from sync_engine to generate daily insights after data refresh."""
    today = _now_date()
    history = _load_insights()

    # Only generate once per day
    if history and history[-1].get("date") == today:
        LOG.info("Daily insights already generated for %s", today)
        return

    generate_daily_insights()
    LOG.info("Daily insights generated for %s", today)
