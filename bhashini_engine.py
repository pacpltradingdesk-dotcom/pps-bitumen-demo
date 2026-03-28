"""
Bhashini Translation Engine — Indian Language Translation Stub
===============================================================
Wrapper for Bhashini (govt free API) for translating between Indian languages.
Falls back gracefully when API is unavailable.

Supported languages: en, hi, gu, mr, ta, te

PPS Anantam Capital Pvt Ltd — Business Intelligence v1.0
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger("bhashini_engine")

# Bhashini language codes
LANG_CODES = {
    "en": "en",
    "hi": "hi",
    "gu": "gu",
    "mr": "mr",
    "ta": "ta",
    "te": "te",
}

LANG_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "gu": "Gujarati",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
}


def _load_settings() -> dict:
    try:
        from settings_engine import load_settings
        return load_settings()
    except Exception:
        return {}


def is_enabled() -> bool:
    """Check if Bhashini translation is enabled."""
    settings = _load_settings()
    return bool(settings.get("bhashini_enabled", False))


def translate(text: str, source_lang: str = "en",
              target_lang: str = "hi") -> str:
    """
    Translate text between Indian languages using Bhashini API.

    Args:
        text: Text to translate
        source_lang: Source language code (en, hi, gu, mr, ta, te)
        target_lang: Target language code

    Returns:
        Translated text, or original text with note if translation fails.
    """
    if not text or not text.strip():
        return text

    if source_lang == target_lang:
        return text

    # Validate language codes
    if source_lang not in LANG_CODES or target_lang not in LANG_CODES:
        return text

    settings = _load_settings()
    if not settings.get("bhashini_enabled", False):
        return text

    api_key = settings.get("bhashini_api_key", "")
    if not api_key:
        logger.debug("Bhashini API key not configured")
        return text

    try:
        return _call_bhashini_api(text, source_lang, target_lang, api_key)
    except Exception as e:
        logger.warning(f"Bhashini translation failed: {e}")
        src_name = LANG_NAMES.get(source_lang, source_lang)
        tgt_name = LANG_NAMES.get(target_lang, target_lang)
        return f"{text}\n\n(Translation from {src_name} to {tgt_name} unavailable)"


def _call_bhashini_api(text: str, source: str, target: str,
                       api_key: str) -> str:
    """Call Bhashini ULCA translation API."""
    url = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute"

    payload = {
        "pipelineTasks": [{
            "taskType": "translation",
            "config": {
                "language": {
                    "sourceLanguage": LANG_CODES[source],
                    "targetLanguage": LANG_CODES[target],
                }
            }
        }],
        "inputData": {
            "input": [{"source": text[:2000]}]  # Limit input size
        }
    }

    headers = {
        "Content-Type": "application/json",
        "ulcaApiKey": api_key,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    # Extract translated text from response
    output = result.get("pipelineResponse", [{}])
    if output:
        texts = output[0].get("output", [{}])
        if texts:
            return texts[0].get("target", text)

    return text


def get_supported_languages() -> dict:
    """Return supported language codes and names."""
    return dict(LANG_NAMES)


def get_translation_status() -> dict:
    """Get translation engine status."""
    settings = _load_settings()
    return {
        "enabled": bool(settings.get("bhashini_enabled", False)),
        "api_key_configured": bool(settings.get("bhashini_api_key", "")),
        "supported_languages": list(LANG_NAMES.keys()),
    }
