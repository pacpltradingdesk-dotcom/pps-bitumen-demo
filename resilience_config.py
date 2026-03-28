"""
PPS Anantam — Resilience Configuration v1.0
=============================================
Central source of truth for fallback chains, validation rules,
health scoring, circuit breaker profiles, and retry strategies.

Zero paid services. All fallbacks use free APIs or local cache.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# A. FALLBACK MATRIX — Primary / Secondary / Tertiary / Emergency per category
# ═══════════════════════════════════════════════════════════════════════════════

FALLBACK_MATRIX: dict[str, dict] = {
    "fx_rates": {
        "label": "Foreign Exchange Rates",
        "icon": "💵",
        "primary": {
            "source": "fawazahmed0_cdn",
            "label": "fawazahmed0 CDN (Free)",
            "type": "free_api",
            "ttl_sec": 3600,
            "confidence": 95,
        },
        "secondary": {
            "source": "frankfurter_ecb",
            "label": "Frankfurter ECB (Free)",
            "type": "free_api",
            "ttl_sec": 7200,
            "confidence": 85,
        },
        "tertiary": {
            "source": "lkg_cache",
            "label": "Last-Known-Good Cache",
            "type": "last_known_good",
            "ttl_sec": 86400,
            "confidence": 60,
        },
        "emergency": {
            "source": "static_reference",
            "label": "Static Q1 2026 Reference",
            "type": "static",
            "value": {"USDINR": 86.80, "EURINR": 94.50, "GBPINR": 110.20},
            "confidence": 30,
        },
    },
    "crude_prices": {
        "label": "Crude Oil Prices",
        "icon": "🛢️",
        "primary": {
            "source": "yfinance",
            "label": "Yahoo Finance (Free)",
            "type": "free_api",
            "symbols": ["BZ=F", "CL=F"],
            "ttl_sec": 900,
            "confidence": 95,
        },
        "secondary": {
            "source": "eia_api",
            "label": "EIA API (Free with key)",
            "type": "keyed_api",
            "requires_key": True,
            "key_setting": "api_key_eia",
            "ttl_sec": 3600,
            "confidence": 90,
        },
        "tertiary": {
            "source": "lkg_cache",
            "label": "Last-Known-Good Cache",
            "type": "last_known_good",
            "ttl_sec": 86400,
            "confidence": 55,
        },
        "emergency": {
            "source": "static_reference",
            "label": "Static Q1 2026 Reference",
            "type": "static",
            "value": {"brent": 75.50, "wti": 71.50, "opec": 73.00},
            "confidence": 25,
        },
    },
    "weather": {
        "label": "Weather Data",
        "icon": "🌤️",
        "primary": {
            "source": "open_meteo",
            "label": "Open-Meteo (Free, no key)",
            "type": "free_api",
            "ttl_sec": 3600,
            "confidence": 90,
        },
        "secondary": {
            "source": "openweather",
            "label": "OpenWeather (Free with key)",
            "type": "keyed_api",
            "requires_key": True,
            "key_setting": "api_key_openweather",
            "ttl_sec": 3600,
            "confidence": 88,
        },
        "tertiary": {
            "source": "lkg_cache",
            "label": "Last-Known-Good Cache",
            "type": "last_known_good",
            "ttl_sec": 43200,
            "confidence": 50,
        },
        "emergency": {
            "source": "seasonal_average",
            "label": "Seasonal Average (Mar: 28-38C)",
            "type": "static",
            "value": {
                "Mumbai": 30, "Kandla": 33, "Mangalore": 31,
                "Delhi": 28, "Vadodara": 34,
            },
            "confidence": 25,
        },
    },
    "news": {
        "label": "News & Events",
        "icon": "📰",
        "primary": {
            "source": "rss_aggregator",
            "label": "12-Source RSS Aggregator (Free)",
            "type": "free_rss",
            "feeds": 12,
            "ttl_sec": 600,
            "confidence": 85,
        },
        "secondary": {
            "source": "google_news_rss",
            "label": "Google News RSS (Free)",
            "type": "free_rss",
            "ttl_sec": 1800,
            "confidence": 75,
        },
        "tertiary": {
            "source": "lkg_cache",
            "label": "Last-Known-Good Cache",
            "type": "last_known_good",
            "ttl_sec": 86400,
            "confidence": 45,
        },
        "emergency": {
            "source": "last_24h_cached_articles",
            "label": "Cached Articles (<24h)",
            "type": "local_file",
            "confidence": 30,
        },
    },
    "govt_data": {
        "label": "Government & Infrastructure Data",
        "icon": "🏛️",
        "primary": {
            "source": "data_gov_in",
            "label": "data.gov.in NHAI (Free with key)",
            "type": "keyed_api",
            "requires_key": True,
            "key_setting": "api_key_data_gov_in",
            "ttl_sec": 86400,
            "confidence": 90,
        },
        "secondary": {
            "source": "pib_rss",
            "label": "PIB Infrastructure RSS (Free)",
            "type": "free_rss",
            "ttl_sec": 86400,
            "confidence": 70,
        },
        "tertiary": {
            "source": "static_reference_2024",
            "label": "Static Reference (FY24 NHAI Data)",
            "type": "static",
            "confidence": 45,
        },
        "emergency": {
            "source": "manual_override",
            "label": "Manual Override / Settings",
            "type": "manual",
            "confidence": 20,
        },
    },
    "trade_data": {
        "label": "Trade & Import Data",
        "icon": "🚢",
        "primary": {
            "source": "un_comtrade",
            "label": "UN Comtrade HS 271320 (Free)",
            "type": "free_api",
            "ttl_sec": 86400,
            "confidence": 90,
        },
        "secondary": {
            "source": "world_bank_api",
            "label": "World Bank India (Free)",
            "type": "free_api",
            "ttl_sec": 86400,
            "confidence": 70,
        },
        "tertiary": {
            "source": "static_trade_cache_2023",
            "label": "Static Trade Data (2023)",
            "type": "static",
            "confidence": 40,
        },
        "emergency": {
            "source": "manual_override",
            "label": "Manual Override / Settings",
            "type": "manual",
            "confidence": 20,
        },
    },
    "system_time": {
        "label": "System Clock",
        "icon": "🕐",
        "primary": {
            "source": "timeapi_io",
            "label": "TimeAPI.io (Free)",
            "type": "free_api",
            "ttl_sec": 60,
            "confidence": 99,
        },
        "secondary": {
            "source": "worldtimeapi",
            "label": "WorldTimeAPI (Free)",
            "type": "free_api",
            "ttl_sec": 60,
            "confidence": 95,
        },
        "tertiary": {
            "source": "python_datetime_ist",
            "label": "Python datetime (Local IST)",
            "type": "local",
            "confidence": 90,
        },
        "emergency": {
            "source": "os_time",
            "label": "OS System Clock",
            "type": "local",
            "confidence": 85,
        },
    },
    "maritime_data": {
        "label": "Maritime Intelligence",
        "icon": "🚢",
        "primary": {
            "source": "open_meteo_marine",
            "label": "Open-Meteo Marine API (Free)",
            "type": "free_api",
            "ttl_sec": 3600,
            "confidence": 80,
        },
        "secondary": {
            "source": "weather_proxy",
            "label": "Weather-based Port Congestion Proxy",
            "type": "derived",
            "ttl_sec": 7200,
            "confidence": 65,
        },
        "tertiary": {
            "source": "news_sentiment",
            "label": "News Sentiment (Maritime RSS)",
            "type": "rss",
            "ttl_sec": 14400,
            "confidence": 50,
        },
        "emergency": {
            "source": "static_seasonal",
            "label": "Static Seasonal Averages",
            "type": "static",
            "confidence": 40,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# B. VALIDATION RULES — Per-data-type bounds & freshness
# ═══════════════════════════════════════════════════════════════════════════════

VALIDATION_RULES: dict[str, dict] = {
    "brent_usd": {
        "min": 20, "max": 200, "type": "float",
        "stale_hours": 6, "label": "Brent Crude (USD/bbl)",
    },
    "wti_usd": {
        "min": 18, "max": 195, "type": "float",
        "stale_hours": 6, "label": "WTI Crude (USD/bbl)",
    },
    "usdinr": {
        "min": 50, "max": 120, "type": "float",
        "stale_hours": 6, "label": "USD/INR Exchange Rate",
    },
    "eurinr": {
        "min": 55, "max": 140, "type": "float",
        "stale_hours": 12, "label": "EUR/INR Exchange Rate",
    },
    "weather_temp_c": {
        "min": -10, "max": 55, "type": "float",
        "stale_hours": 2, "label": "Temperature (Celsius)",
    },
    "bitumen_inr_per_mt": {
        "min": 15000, "max": 120000, "type": "float",
        "stale_hours": 12, "label": "Bitumen Price (INR/MT)",
    },
    "port_volume_mt": {
        "min": 0, "max": 500000, "type": "float",
        "stale_hours": 24, "label": "Port Volume (MT)",
    },
    "news_article_count": {
        "min": 0, "max": 10000, "type": "int",
        "stale_hours": 2, "label": "News Article Count",
    },
    "freight_inr_per_mt": {
        "min": 100, "max": 15000, "type": "float",
        "stale_hours": 24, "label": "Freight Rate (INR/MT)",
    },
    "margin_pct": {
        "min": -50, "max": 200, "type": "float",
        "stale_hours": 24, "label": "Margin Percentage",
    },
    "port_congestion_pct": {
        "min": 0, "max": 100, "type": "float",
        "stale_hours": 1, "label": "Port Congestion (%)",
    },
    "vessel_speed_knots": {
        "min": 0, "max": 25, "type": "float",
        "stale_hours": 1, "label": "Vessel Speed (knots)",
    },
    "wave_height_m": {
        "min": 0, "max": 15, "type": "float",
        "stale_hours": 2, "label": "Wave Height (meters)",
    },
}

def validate_value(rule_key: str, value) -> dict:
    """Validate a value against its rule. Returns {valid, reason, clamped_value}."""
    rule = VALIDATION_RULES.get(rule_key)
    if not rule:
        return {"valid": True, "reason": "No rule defined", "clamped_value": value}
    try:
        v = float(value) if rule["type"] == "float" else int(value)
    except (ValueError, TypeError):
        return {"valid": False, "reason": f"Cannot convert to {rule['type']}", "clamped_value": None}
    if v < rule["min"]:
        return {"valid": False, "reason": f"Below minimum ({rule['min']})", "clamped_value": rule["min"]}
    if v > rule["max"]:
        return {"valid": False, "reason": f"Above maximum ({rule['max']})", "clamped_value": rule["max"]}
    return {"valid": True, "reason": "OK", "clamped_value": v}


# ═══════════════════════════════════════════════════════════════════════════════
# C. HEALTH SCORING — Weighted algorithm with traffic-light thresholds
# ═══════════════════════════════════════════════════════════════════════════════

HEALTH_SCORING: dict = {
    "weights": {
        "api_availability":  0.30,
        "data_freshness":    0.25,
        "worker_uptime":     0.20,
        "error_rate":        0.15,
        "cache_hit_ratio":   0.10,
    },
    "thresholds": {
        "green":  80,    # >= 80% = healthy
        "yellow": 60,    # 60-79% = degraded
        "red":    40,    # 40-59% = critical
        # < 40% = blue (offline / unknown)
    },
}


def compute_health_score(metrics: dict) -> dict:
    """
    Compute weighted health score from component metrics.
    metrics: {component_name: score_0_to_100}
    Returns: {score, grade, color, label}
    """
    weights = HEALTH_SCORING["weights"]
    thresholds = HEALTH_SCORING["thresholds"]

    total_weight = 0.0
    weighted_sum = 0.0
    for comp, weight in weights.items():
        val = metrics.get(comp, 50)  # default 50 if missing
        weighted_sum += weight * val
        total_weight += weight

    score = round(weighted_sum / total_weight) if total_weight > 0 else 0
    score = max(0, min(100, score))

    if score >= thresholds["green"]:
        return {"score": score, "grade": "A", "color": "#22c55e", "label": "All Systems Operational"}
    elif score >= thresholds["yellow"]:
        return {"score": score, "grade": "B", "color": "#f59e0b", "label": "Degraded Performance"}
    elif score >= thresholds["red"]:
        return {"score": score, "grade": "C", "color": "#ef4444", "label": "Critical — Attention Required"}
    else:
        return {"score": score, "grade": "D", "color": "#3b82f6", "label": "Offline / Unknown"}


# ═══════════════════════════════════════════════════════════════════════════════
# D. CIRCUIT BREAKER PROFILES — Per-connector thresholds
# ═══════════════════════════════════════════════════════════════════════════════

CIRCUIT_BREAKER_PROFILES: dict[str, dict] = {
    "fast_api": {
        "label": "Fast APIs (yfinance, fawazahmed0, Frankfurter)",
        "threshold": 3,
        "timeout_sec": 30,
    },
    "slow_api": {
        "label": "Slow APIs (UN Comtrade, World Bank, EIA)",
        "threshold": 5,
        "timeout_sec": 120,
    },
    "rss_feed": {
        "label": "RSS Feeds (Google News, OilPrice, PIB)",
        "threshold": 3,
        "timeout_sec": 60,
    },
    "static_data": {
        "label": "Static Sources (PPAC, reference tables)",
        "threshold": 10,
        "timeout_sec": 300,
    },
}

# Map connector IDs to their circuit breaker profile
CONNECTOR_CB_MAP: dict[str, str] = {
    # Fast APIs
    "yfinance_brent": "fast_api",
    "yfinance_wti": "fast_api",
    "fawazahmed0_fx": "fast_api",
    "frankfurter_fx": "fast_api",
    "rbi_fx_historical": "fast_api",
    "open_meteo_hub": "fast_api",
    # Slow APIs
    "eia_crude": "slow_api",
    "un_comtrade": "slow_api",
    "comtrade_hs271320": "slow_api",
    "world_bank_india": "slow_api",
    "fred_macro": "slow_api",
    "data_gov_in_highways": "slow_api",
    # RSS
    "gnews_rss": "rss_feed",
    "newsapi": "rss_feed",
    # Static
    "ppac_proxy": "static_data",
    # Maritime
    "maritime_intel": "slow_api",
    "open_meteo_marine": "fast_api",
}


def get_cb_profile(connector_id: str) -> dict:
    """Get the circuit breaker profile for a connector."""
    profile_key = CONNECTOR_CB_MAP.get(connector_id, "slow_api")
    return CIRCUIT_BREAKER_PROFILES[profile_key]


# ═══════════════════════════════════════════════════════════════════════════════
# E. RETRY PROFILES — Backoff strategies
# ═══════════════════════════════════════════════════════════════════════════════

RETRY_PROFILES: dict[str, dict] = {
    "aggressive": {
        "label": "Fast retry for critical data",
        "max_retries": 5,
        "backoff_sec": [1, 2, 5, 10, 20],
    },
    "standard": {
        "label": "Default retry strategy",
        "max_retries": 3,
        "backoff_sec": [2, 8, 20],
    },
    "conservative": {
        "label": "Slow retry for non-critical data",
        "max_retries": 2,
        "backoff_sec": [5, 30],
    },
}

# Map categories to retry profiles
CATEGORY_RETRY_MAP: dict[str, str] = {
    "crude_prices": "aggressive",
    "fx_rates": "aggressive",
    "weather": "standard",
    "news": "standard",
    "govt_data": "conservative",
    "trade_data": "conservative",
    "system_time": "aggressive",
}


def get_retry_profile(category: str) -> dict:
    """Get the retry profile for a data category."""
    profile_key = CATEGORY_RETRY_MAP.get(category, "standard")
    return RETRY_PROFILES[profile_key]


# ═══════════════════════════════════════════════════════════════════════════════
# F. HEARTBEAT CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

HEARTBEAT_CONFIG: dict = {
    "check_interval_sec": 30,
    "dead_multiplier": 2.5,      # thread dead if no beat for interval * 2.5
    "max_restarts_per_hour": 3,
    "alert_after_failed_restarts": 3,
}


# ═══════════════════════════════════════════════════════════════════════════════
# G. DEAD LETTER QUEUE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

DLQ_CONFIG: dict = {
    "max_retries": 3,
    "backoff_minutes": [5, 30, 120],   # 5 min, 30 min, 2 hours
    "max_queue_size": 500,
    "archive_after_exhaust": True,
    "cleanup_archive_days": 30,
}


# ═══════════════════════════════════════════════════════════════════════════════
# H. LKG (LAST-KNOWN-GOOD) CACHE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

LKG_CONFIG: dict = {
    "min_confidence_to_save": 70,    # only save verified/estimated data
    "confidence_penalty_pct": 20,    # reduce confidence by 20% when using LKG
    "min_confidence_floor": 30,      # never report confidence below 30%
    "max_age_days": 7,               # discard LKG older than 7 days
    "lkg_dir": "lkg_cache",
}


# ═══════════════════════════════════════════════════════════════════════════════
# I. CONFIDENCE BADGE HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def confidence_badge(pct: int) -> dict:
    """Return badge info for a confidence percentage."""
    if pct >= 80:
        return {"emoji": "🟢", "color": "#22c55e", "label": "Verified", "level": "green"}
    elif pct >= 60:
        return {"emoji": "🟡", "color": "#f59e0b", "label": "Estimated", "level": "yellow"}
    elif pct >= 40:
        return {"emoji": "🔴", "color": "#ef4444", "label": "Stale", "level": "red"}
    else:
        return {"emoji": "🔵", "color": "#3b82f6", "label": "Unavailable", "level": "blue"}
