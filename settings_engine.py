"""
PPS Anantam — Settings Engine v1.0
===================================
Configurable business rules for the entire dashboard ecosystem.
All pricing, tax, logistics, and sync settings in one place.
Stored in settings.json — editable via UI Settings page.
"""

import json
from pathlib import Path

BASE = Path(__file__).parent
SETTINGS_FILE = BASE / "settings.json"

# ─── Default Settings ─────────────────────────────────────────────────────────

DEFAULT_SETTINGS = {
    # Margin & Pricing
    "margin_min_per_mt": 500,
    "margin_balanced_multiplier": 1.6,
    "margin_premium_multiplier": 2.4,
    "gst_rate_pct": 18,
    "customs_duty_pct": 2.5,
    "landing_charges_pct": 1.0,

    # Transport Rates
    "bulk_rate_per_km": 5.5,
    "drum_rate_per_km": 6.0,
    "decanter_conversion_cost": 500,

    # Import Cost Defaults
    "default_fob_usd": 380,
    "default_freight_usd": 35,
    "default_insurance_pct": 0.5,
    "default_switch_bl_usd": 2,
    "default_port_charges_inr": 10000,
    "default_cha_per_mt": 75,
    "default_handling_per_mt": 100,
    "default_vessel_qty_mt": 5000,

    # Quotation Defaults
    "quote_validity_hours": 24,
    "payment_default_terms": "100% Advance",

    # Alert Thresholds
    "price_alert_threshold_pct": 5,
    "crude_price_min_usd": 40,
    "crude_price_max_usd": 150,
    "bitumen_price_min_inr": 15000,
    "bitumen_price_max_inr": 120000,
    "fx_min_usdinr": 50,
    "fx_max_usdinr": 120,

    # Sync Schedule
    "sync_schedule_hour": 6,
    "sync_schedule_minute": 0,
    "sync_interval_minutes": 60,
    "news_fetch_interval_minutes": 10,

    # Currency
    "currency_default": "INR",
    "currency_international": "USD",

    # Ports
    "ports": [
        "Kandla", "Mundra", "Mangalore", "JNPT",
        "Karwar", "Haldia", "Ennore", "Paradip"
    ],

    # Grades
    "grades": [
        "VG30", "VG10", "VG40", "Emulsion",
        "CRMB-55", "CRMB-60", "PMB"
    ],

    # CRM Relationship Decay (days)
    "crm_hot_threshold_days": 7,
    "crm_warm_threshold_days": 30,
    "crm_cold_threshold_days": 90,

    # Data Retention
    "max_price_history_records": 5000,
    "max_news_articles": 5000,
    "max_sync_logs": 1000,
    "max_communication_records": 10000,

    # Email Engine
    "email_enabled": False,
    "email_rate_limit_per_hour": 50,
    "email_auto_send_offer": False,
    "email_auto_send_followup": False,
    "email_auto_send_reactivation": False,
    "email_auto_send_payment_reminder": False,
    "email_director_report_enabled": False,
    "email_director_report_time": "08:30",
    "email_director_report_to": "",
    "email_weekly_summary_enabled": False,
    "email_weekly_summary_day": "Monday",
    "email_weekly_summary_time": "09:00",
    "email_weekly_summary_to": "",
    "email_max_retries": 3,
    "email_retry_delay_minutes": 15,

    # WhatsApp Engine (360dialog)
    "whatsapp_enabled": False,
    "whatsapp_auto_send_offer": False,
    "whatsapp_auto_send_followup": False,
    "whatsapp_auto_send_reactivation": False,
    "whatsapp_auto_send_payment_reminder": False,
    "whatsapp_rate_limit_per_minute": 20,
    "whatsapp_rate_limit_per_day": 1000,
    "whatsapp_session_message_enabled": True,

    # AI Learning
    "ai_learning_enabled": True,
    "ai_learning_daily": True,
    "ai_learning_weekly": True,
    "ai_learning_monthly": True,

    # Infra Demand Intelligence
    "infra_demand_enabled": True,
    "gdelt_sync_interval_min": 120,
    "infra_backfill_months": 24,

    # Role-Based Access Control
    "rbac_enabled": False,
    "rbac_default_role": "viewer",
    "rbac_session_timeout_min": 480,

    # Universal Action Bar
    "action_bar_enabled": True,
    "action_bar_show_email": True,
    "action_bar_show_whatsapp": True,
    "action_bar_show_pdf": True,
    "action_bar_show_print": True,
    "action_bar_show_excel": True,
    "action_bar_show_share": True,

    # Ops Monitoring
    "ops_monitoring_enabled": True,

    # System Control Center — Master Switches
    "ai_enabled": True,
    "sync_enabled": True,
    "anomaly_detection_enabled": True,
    "maintenance_mode": False,

    # AI Workers & Setup
    "ai_workers_enabled": True,
    "ai_auto_setup_on_start": True,
    "ai_resource_tier": "auto",         # "auto", "LOW", "MEDIUM", "HIGH"
    "ollama_auto_start": True,

    # Export Settings
    "excel_export_include_metadata": True,
    "csv_export_encoding": "utf-8-sig",

    # ── Market Data API Keys ─────────────────────────────────────────────────
    "api_key_eia": "",
    "api_key_eia_enabled": False,
    "api_key_fred": "",
    "api_key_fred_enabled": False,
    "api_key_data_gov_in": "",
    "api_key_data_gov_in_enabled": False,
    "api_key_openweather": "",
    "api_key_openweather_enabled": False,
    "api_key_newsapi": "",
    "api_key_newsapi_enabled": False,

    # ── Google Sheets Integration ─────────────────────────────────────────────
    "google_sheets_enabled": False,
    "google_sheets_sync_interval_minutes": 60,
    "google_sheets_auto_sync": False,
    "google_sheets_service_account_path": "",

    # ── Client Chat ────────────────────────────────────────────────────────────
    "chat_enabled": False,
    "chat_polling_interval_seconds": 10,
    "chat_max_message_length": 2000,

    # ── Share Links ────────────────────────────────────────────────────────────
    "share_links_enabled": True,
    "share_links_default_expiry_hours": 48,
    "share_links_require_password": False,
    "share_links_max_active": 100,

    # ── Share Automation ───────────────────────────────────────────────────────
    "share_automation_enabled": False,
    "share_automation_max_schedules": 50,

    # ── Universal Share Button ─────────────────────────────────────────────────
    "share_button_enabled": True,
    "share_button_show_email": True,
    "share_button_show_whatsapp": True,
    "share_button_show_pdf": True,
    "share_button_show_link": True,
    "share_button_show_image": True,

    # ── AI Message Generation ──────────────────────────────────────────────────
    "ai_message_tone": "professional",
    "ai_message_language": "en",

    # ── Communication Tracking ─────────────────────────────────────────────────
    "comm_tracking_enabled": True,
    "comm_tracking_retention_days": 365,

    # ── Maritime Intelligence ─────────────────────────────────────────────────
    "maritime_enabled": True,
    "maritime_refresh_interval_minutes": 15,
    "maritime_vessel_count": 12,
    "maritime_priority_ports": ["Mundra", "Kandla", "Mumbai"],
    "maritime_container_first": True,
    "maritime_show_risk_alerts": True,
    "maritime_marine_weather_enabled": True,
    "maritime_rss_enabled": True,
    "maritime_multimodal_enabled": True,
    "maritime_map_center_lat": 18.0,
    "maritime_map_center_lon": 68.0,
    "maritime_map_zoom": 4,

    # ── Port-Specific Charges (INR) ──────────────────────────────────────────
    "port_charges": {
        "Kandla": {"berthing": 8000, "cha_per_mt": 70, "handling_per_mt": 90},
        "Mundra": {"berthing": 12000, "cha_per_mt": 80, "handling_per_mt": 110},
        "Mangalore": {"berthing": 10000, "cha_per_mt": 75, "handling_per_mt": 100},
        "JNPT": {"berthing": 15000, "cha_per_mt": 90, "handling_per_mt": 120},
        "Karwar": {"berthing": 7000, "cha_per_mt": 65, "handling_per_mt": 85},
        "Haldia": {"berthing": 9000, "cha_per_mt": 75, "handling_per_mt": 95},
        "Ennore": {"berthing": 11000, "cha_per_mt": 80, "handling_per_mt": 105},
        "Paradip": {"berthing": 8500, "cha_per_mt": 70, "handling_per_mt": 90},
    },

    # ── Election Years (dynamic for demand_analytics) ────────────────────────
    "election_years": [2024, 2029, 2034],

    # ── Purchase Advisor Weights ─────────────────────────────────────────────
    "purchase_advisor_enabled": True,
    "purchase_advisor_urgency_weights": {
        "price_trend": 0.25,
        "demand_season": 0.20,
        "inventory_level": 0.15,
        "crude_momentum": 0.20,
        "fx_pressure": 0.10,
        "supply_risk": 0.10,
    },

    # ── CRM Automation — Daily Rotation ──────────────────────────────────────
    "daily_rotation_enabled": False,
    "daily_rotation_count": 2400,
    "daily_rotation_time": "09:00",
    "rotation_cycle_days": 10,
    "rotation_min_gap_days": 7,
    "rotation_channels": ["whatsapp", "email"],
    "rotation_retry_failed": True,
    "rotation_retry_max_attempts": 3,

    # ── CRM Automation — Festival Broadcasts ─────────────────────────────────
    "festival_broadcast_enabled": False,
    "festival_broadcast_time": "07:00",
    "festival_broadcast_days_ahead": 1,
    "festival_broadcast_channels": ["whatsapp", "email"],

    # ── CRM Automation — Price Broadcasts ────────────────────────────────────
    "price_broadcast_enabled": False,
    "price_change_threshold_pct": 2.0,
    "price_broadcast_channels": ["whatsapp", "email"],
    "price_watch_interval_minutes": 5,

    # ── CRM Automation — AI Auto-Reply ───────────────────────────────────────
    "ai_auto_reply_enabled": False,
    "ai_auto_reply_confidence_threshold": 0.7,
    "ai_auto_reply_escalate_unsure": True,
    "ai_auto_reply_languages": ["en", "hi"],

    # ── CRM Automation — WhatsApp Festival Mode ──────────────────────────────
    "whatsapp_festival_mode_limit": 24000,
    "whatsapp_stagger_batch_size": 1000,
    "whatsapp_stagger_delay_minutes": 60,

    # ── CRM Automation — SendGrid Bulk Email ─────────────────────────────────
    "sendgrid_enabled": False,
    "sendgrid_api_key": "",
    "sendgrid_from_email": "",
    "sendgrid_from_name": "PPS Anantam",
    "sendgrid_daily_limit": 10000,

    # ── CRM Automation — Contact Categories ──────────────────────────────────
    "contact_categories": [
        "Importer", "Exporter", "Trader", "Dealer",
        "Decanter Unit", "Commission Agent",
        "Truck Transporter", "Tanker Transporter"
    ],

    # ── SMS Engine (Fast2SMS) ──────────────────────────────────────────────
    "sms_enabled": False,
    "fast2sms_api_key": "",
    "sms_daily_limit": 100,

    # ── DPDP Privacy Compliance ────────────────────────────────────────────
    "dpdp_compliance_enabled": True,
    "unsubscribe_footer_text": "To unsubscribe, reply STOP.",
    "consent_required_for_broadcast": True,

    # ── Bhashini Translation ───────────────────────────────────────────────
    "bhashini_enabled": False,
    "bhashini_api_key": "",

    # ── AI Calling (Placeholder) ───────────────────────────────────────────
    "ai_calling_enabled": False,
    "ai_calling_provider": "none",
    "ai_calling_api_key": "",

    # ── Multi-AI Provider API Keys ─────────────────────────────────────────
    "groq_api_key": "",
    "gemini_api_key": "",
    "mistral_api_key": "",
    "deepseek_api_key": "",
    "brevo_api_key": "",
    "elevenlabs_api_key": "",

    # ── AI Provider Enable/Disable ─────────────────────────────────────────
    "ai_provider_groq_enabled": True,
    "ai_provider_gemini_enabled": True,
    "ai_provider_mistral_enabled": True,
    "ai_provider_deepseek_enabled": True,
    "ai_deepseek_pii_filter": True,

    # ── Voice (Stubs) ──────────────────────────────────────────────────────
    "voice_tts_enabled": False,
    "voice_stt_enabled": False,
    "voice_tts_provider": "elevenlabs",
    "voice_stt_provider": "whisper",

    # ── AI Provider Health ─────────────────────────────────────────────────
    "ai_provider_auto_disable_threshold": 50,
    "ai_provider_cooldown_minutes": 15,
    "ai_provider_health_check_interval": 300,

    # ── News Ticker ────────────────────────────────────────────────────
    "ticker_speed": 600,

    # ── Owner & Company Identity ─────────────────────────────────────────
    "owner_name": "PRINCE P SHAH",
    "owner_mobile": "+91 7795242424",
    "owner_email": "princepshah@gmail.com",
    "company_trade_name": "PACPL",

    # ── Segment-Aware Communication ──────────────────────────────────────
    "segment_aware_templates": True,
    "default_communication_language": "en",

    # ── Price Factor Thresholds ──────────────────────────────────────────
    "pf_crude_threshold_pct": 3.0,
    "pf_fx_threshold_pct": 1.0,
    "pf_conference_threshold_pct": 2.0,
    "pf_psu_threshold_pct": 1.5,

    # ── Daily Automation Schedule ────────────────────────────────────────
    "schedule_price_gathering_time": "05:00",
    "schedule_daily_brief_time": "06:30",
    "schedule_festival_check_time": "07:00",
    "schedule_daily_broadcast_time": "09:00",
    "schedule_price_alerts_time": "18:00",
    "schedule_daily_report_time": "21:00",
}


def load_settings() -> dict:
    """Load settings from file, merge with defaults for any missing keys."""
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                settings.update(stored)
        except (json.JSONDecodeError, IOError):
            pass
    return settings


def save_settings(settings: dict) -> None:
    """Save settings to file."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def get(key: str, default=None):
    """Get a single setting value."""
    settings = load_settings()
    return settings.get(key, default)


def update(key: str, value) -> None:
    """Update a single setting value."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def reset_to_defaults() -> None:
    """Reset all settings to defaults."""
    save_settings(DEFAULT_SETTINGS)


# ─── Secure API Key Access ───────────────────────────────────────────────────

_SENSITIVE_KEYS = {
    "api_key_eia", "api_key_fred", "api_key_data_gov_in",
    "api_key_openweather", "api_key_newsapi", "sendgrid_api_key",
    "fast2sms_api_key", "bhashini_api_key", "ai_calling_api_key",
    "groq_api_key", "gemini_api_key", "mistral_api_key",
    "deepseek_api_key", "brevo_api_key", "elevenlabs_api_key",
}

_ENV_VAR_MAP = {
    "api_key_eia": "EIA_API_KEY",
    "api_key_fred": "FRED_API_KEY",
    "api_key_data_gov_in": "DATA_GOV_IN_KEY",
    "api_key_openweather": "OPENWEATHER_API_KEY",
    "api_key_newsapi": "NEWSAPI_KEY",
    "sendgrid_api_key": "SENDGRID_API_KEY",
    "fast2sms_api_key": "FAST2SMS_API_KEY",
    "bhashini_api_key": "BHASHINI_API_KEY",
    "ai_calling_api_key": "AI_CALLING_API_KEY",
    "groq_api_key": "GROQ_API_KEY",
    "gemini_api_key": "GEMINI_API_KEY",
    "mistral_api_key": "MISTRAL_API_KEY",
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    "brevo_api_key": "BREVO_API_KEY",
    "elevenlabs_api_key": "ELEVENLABS_API_KEY",
}


def get_api_key_secure(key: str) -> str:
    """
    Get an API key securely.
    Checks: environment variable → encrypted vault → settings.json (legacy).
    """
    env_var = _ENV_VAR_MAP.get(key, "")
    try:
        from vault_engine import get_secret
        val = get_secret(f"settings_{key}", env_var=env_var)
        if val:
            return val
    except ImportError:
        pass
    # Check environment directly
    if env_var:
        val = __import__("os").environ.get(env_var, "").strip()
        if val:
            return val
    # Fallback to plain settings.json (legacy)
    return load_settings().get(key, "")


def _migrate_sensitive_to_vault():
    """One-time: move plaintext API keys from settings.json into encrypted vault."""
    try:
        from vault_engine import set_secret, _HAS_CRYPTOGRAPHY
        if not _HAS_CRYPTOGRAPHY:
            return
    except ImportError:
        return
    settings = load_settings()
    dirty = False
    for key in _SENSITIVE_KEYS:
        val = settings.get(key, "")
        if val and isinstance(val, str) and len(val) > 5:
            set_secret(f"settings_{key}", val)
            settings[key] = ""  # Clear from JSON
            dirty = True
    if dirty:
        save_settings(settings)


# Initialize settings file if it doesn't exist
if not SETTINGS_FILE.exists():
    save_settings(DEFAULT_SETTINGS)

# Auto-migrate sensitive keys to vault on first import
try:
    _migrate_sensitive_to_vault()
except Exception:
    pass
