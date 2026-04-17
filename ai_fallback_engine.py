"""
AI Engine — OpenAI-only (17-Apr-2026)
========================================
Single-provider Q&A engine. Uses OpenAI GPT-4o-mini exclusively.

Previously a multi-provider fallback chain (Ollama / HuggingFace / GPT4All /
Groq / Gemini / Mistral / DeepSeek / Claude); all removed per user request.

Setup:
  pip install openai
  Set OPENAI_API_KEY env var, or paste into secrets.toml as [ai] openai="sk-..."

Behaviour:
  • Every response is prefixed with the 'Who is this?' identity banner.
  • All events logged to ai_fallback_log.json.
  • If OpenAI key missing or API fails, returns a deterministic fallback message.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
import time
from pathlib import Path
from typing import Optional

BASE_DIR  = Path(__file__).parent
LOG_FILE  = BASE_DIR / "ai_fallback_log.json"
CFG_FILE  = BASE_DIR / "ai_fallback_config.json"

MAX_TOKENS          = 1024
MONITOR_INTERVAL    = 300   # 5 minutes in seconds
OLLAMA_ENDPOINT     = "http://localhost:11434"
HF_MODEL            = "HuggingFaceH4/zephyr-7b-beta"
GPT4ALL_MODEL       = "Phi-3-mini-4k-instruct.Q4_0.gguf"
OPENAI_MODEL        = "gpt-4o-mini"
CLAUDE_MODEL        = "claude-haiku-4-5-20251001"

# ── New FREE provider endpoints ───────────────────────────────────────────────
GROQ_ENDPOINT       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL          = "llama-3.3-70b-versatile"
GEMINI_ENDPOINT     = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL        = "gemini-2.0-flash"
MISTRAL_ENDPOINT    = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL       = "mistral-small-latest"
DEEPSEEK_ENDPOINT   = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL      = "deepseek-chat"

# Ollama model options — user can choose via UI
OLLAMA_MODELS = ["llama3", "mistral", "mixtral", "llama3:70b"]
OLLAMA_DEFAULT_MODEL = "llama3"

# ── Provider registry ─────────────────────────────────────────────────────────
#   Each entry describes one AI provider in priority order.

PROVIDER_CHAIN: list[dict] = [
    # Single provider — OpenAI GPT-4o-mini. All other providers (Ollama,
    # HuggingFace, GPT4All, Groq, Gemini, Mistral, DeepSeek, Claude) removed
    # per user request on 17-Apr-2026.
    {
        "id":          "openai",
        "name":        "OpenAI GPT-4o-mini",
        "short":       "OpenAI",
        "type":        "Paid — Primary",
        "cost":        "PAID",
        "icon":        "🤖",
        "pkg":         "openai",
        "needs_key":   True,
        "env_key":     "OPENAI_API_KEY",
        "cfg_key":     "openai_api_key",
        "install_cmd": "pip install openai",
        "setup_note":  "Get key at: https://platform.openai.com/api-keys",
    },
]

# ── Shared mutable state (thread-safe) ───────────────────────────────────────

_lock = threading.RLock()
_G: dict = {
    "active_idx":      0,      # current position in PROVIDER_CHAIN
    "last_errors":     {},     # {provider_id: last_error_message}
    "monitor_started": False,
}

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG & KEY MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def _load_cfg() -> dict:
    if CFG_FILE.exists():
        try:
            return json.loads(CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_cfg(data: dict):
    CFG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def get_api_key(provider_id: str) -> str:
    p = next((x for x in PROVIDER_CHAIN if x["id"] == provider_id), None)
    if not p:
        return ""
    # Cloud-resilient: try st.secrets["ai"][provider_id] first
    try:
        from cloud_secrets import get_secret_block
        ai_block = get_secret_block("ai")
        if ai_block.get(provider_id):
            return str(ai_block[provider_id]).strip()
        # also accept openai_api_key style aliases
        alias_key = f"{provider_id}_api_key"
        if ai_block.get(alias_key):
            return str(ai_block[alias_key]).strip()
    except Exception:
        pass
    env_key = p.get("env_key", "")
    if env_key:
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    cfg_key = p.get("cfg_key", "")
    if cfg_key:
        return _load_cfg().get(cfg_key, "").strip()
    return ""

def save_api_key(provider_id: str, key: str):
    p = next((x for x in PROVIDER_CHAIN if x["id"] == provider_id), None)
    if not p:
        return
    cfg_key = p.get("cfg_key", "")
    if cfg_key:
        data = _load_cfg()
        data[cfg_key] = key.strip()
        _save_cfg(data)
        # Cache in session so the key survives within current run if file wiped
        try:
            from cloud_secrets import remember_in_session
            remember_in_session("ai", {provider_id: key.strip()})
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════════════════════
# PACKAGE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _pkg_ok(pkg: str) -> bool:
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False

def _ollama_running() -> bool:
    """Check if Ollama daemon is live on localhost."""
    try:
        import urllib.request
        urllib.request.urlopen(f"{OLLAMA_ENDPOINT}/api/tags", timeout=2)
        return True
    except Exception:
        return False

def get_provider_status() -> list[dict]:
    """Return status dict for all providers (used by UI)."""
    rows = []
    for p in PROVIDER_CHAIN:
        pkg_ok  = _pkg_ok(p["pkg"])
        has_key = bool(get_api_key(p["id"])) if p["needs_key"] else True
        daemon  = _ollama_running() if p["id"] == "ollama" else True
        ready   = pkg_ok and has_key and daemon
        with _lock:
            last_err  = _G["last_errors"].get(p["id"], "")
            is_active = PROVIDER_CHAIN.index(p) == _G["active_idx"]
        rows.append({
            **p,
            "pkg_installed": pkg_ok,
            "has_key":       has_key,
            "daemon_ok":     daemon,
            "ready":         ready,
            "is_active":     is_active,
            "last_error":    last_err,
        })
    return rows

# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER QUERY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _get_business_ctx(scope: str = "general", segment: str = "") -> str:
    """Load business context for AI prompt injection."""
    try:
        from business_context import get_business_context
        return get_business_context(scope, segment=segment)
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# PII FILTER — Strips sensitive data before sending to restricted providers
# ══════════════════════════════════════════════════════════════════════════════

import re as _re
import urllib.request as _urllib_req

_PII_PATTERNS = [
    (_re.compile(r"(\+?91[\s\-]?)?[6-9]\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d[\s\-]?\d"), "[PHONE]"),
    (_re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    (_re.compile(r"[A-Z]{5}\d{4}[A-Z]"), "[PAN]"),
    (_re.compile(r"\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]{2}"), "[GSTIN]"),
    (_re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR]"),
    (_re.compile(r"\b\d{6}\b"), "[PIN]"),
]

_CUSTOMER_NAMES_CACHE: list = []
_CUSTOMER_NAMES_LOADED = False


def _load_customer_names() -> list:
    """Load customer/contact names from database (cached)."""
    global _CUSTOMER_NAMES_CACHE, _CUSTOMER_NAMES_LOADED
    if _CUSTOMER_NAMES_LOADED:
        return _CUSTOMER_NAMES_CACHE
    try:
        from database import get_all_contacts
        contacts = get_all_contacts()
        _CUSTOMER_NAMES_CACHE = [
            c.get("name", "") for c in contacts if c.get("name")
        ]
        _CUSTOMER_NAMES_LOADED = True
    except Exception:
        _CUSTOMER_NAMES_LOADED = True
    return _CUSTOMER_NAMES_CACHE


def _strip_pii(text: str) -> str:
    """Replace PII patterns with placeholders. Used for restricted providers (DeepSeek)."""
    if not text:
        return text
    result = text
    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)
    # Replace known customer names
    for name in _load_customer_names():
        if name and len(name) > 2 and name in result:
            result = result.replace(name, "[CUSTOMER]")
    return result


def _pii_filter_enabled() -> bool:
    """Check if PII filter is enabled in settings."""
    try:
        from settings_engine import load_settings
        return load_settings().get("ai_deepseek_pii_filter", True)
    except Exception:
        return True


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER HEALTH TRACKING — Auto-disable/reenable based on success rate
# ══════════════════════════════════════════════════════════════════════════════

_HEALTH: dict = {}  # {pid: {"calls": [(ts, success, latency_ms)], "disabled_until": None}}


def _init_health(pid: str):
    """Initialize health tracking for a provider if not present."""
    if pid not in _HEALTH:
        _HEALTH[pid] = {"calls": [], "disabled_until": None}


def _record_call(pid: str, success: bool, latency_ms: float = 0):
    """Record a call result for health tracking."""
    _init_health(pid)
    import time as _time
    with _lock:
        calls = _HEALTH[pid]["calls"]
        calls.append((_time.time(), success, latency_ms))
        # Keep last 100 calls only
        if len(calls) > 100:
            _HEALTH[pid]["calls"] = calls[-100:]
        # Auto-disable if >50% error in last 20 calls
        recent = calls[-20:]
        if len(recent) >= 5:
            error_rate = sum(1 for _, s, _ in recent if not s) / len(recent)
            try:
                from settings_engine import load_settings
                threshold = load_settings().get("ai_provider_auto_disable_threshold", 50) / 100
            except Exception:
                threshold = 0.5
            if error_rate > threshold:
                try:
                    from settings_engine import load_settings
                    cooldown_min = load_settings().get("ai_provider_cooldown_minutes", 15)
                except Exception:
                    cooldown_min = 15
                _HEALTH[pid]["disabled_until"] = _time.time() + (cooldown_min * 60)
                _log("auto_disabled", pid,
                     f"Error rate {error_rate:.0%} > {threshold:.0%} — disabled for {cooldown_min}min")


def _is_provider_disabled(pid: str) -> bool:
    """Check if a provider is auto-disabled (reenables after cooldown)."""
    _init_health(pid)
    import time as _time
    with _lock:
        until = _HEALTH[pid].get("disabled_until")
        if until is None:
            return False
        if _time.time() >= until:
            _HEALTH[pid]["disabled_until"] = None
            _log("auto_reenabled", pid, "Cooldown expired — provider re-enabled")
            return False
        return True


def get_provider_health(pid: str = "") -> dict:
    """Get health stats for one or all providers."""
    import time as _time
    if pid:
        _init_health(pid)
        with _lock:
            calls = _HEALTH[pid]["calls"]
            recent = calls[-20:] if calls else []
            success_count = sum(1 for _, s, _ in recent if s)
            total = len(recent)
            avg_lat = sum(l for _, _, l in recent) / max(total, 1)
            return {
                "provider": pid,
                "success_rate": round(success_count / max(total, 1) * 100, 1),
                "avg_latency_ms": round(avg_lat, 0),
                "total_calls": len(calls),
                "is_disabled": _is_provider_disabled(pid),
                "disabled_until": _HEALTH[pid].get("disabled_until"),
            }
    # All providers
    result = {}
    for p in PROVIDER_CHAIN:
        result[p["id"]] = get_provider_health(p["id"])
    return result


# ══════════════════════════════════════════════════════════════════════════════
# NEW PROVIDER QUERY FUNCTIONS — OpenAI-compatible + Gemini REST
# ══════════════════════════════════════════════════════════════════════════════

def _query_openai_compatible(question: str, context: str, key: str,
                              endpoint: str, model: str) -> str:
    """Generic OpenAI-format API caller using urllib (no extra packages)."""
    biz = _get_business_ctx("general")
    messages = [
        {"role": "system", "content": (
            "You are a Bitumen Sales Dashboard AI assistant for PPS Anantam Capital Pvt Ltd. "
            "Answer ONLY from the dashboard data provided. Use Indian number formatting "
            "(Rs crore/lakh). Dates: DD-MM-YYYY. Be concise but complete.\n\n"
            f"{biz}\n\n"
            f"LIVE DASHBOARD DATA:\n{context[:4000]}"
        )},
        {"role": "user", "content": question},
    ]
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.3,
    }).encode("utf-8")

    req = _urllib_req.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with _urllib_req.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"].strip()


def _query_groq(question: str, context: str, key: str) -> str:
    """Query Groq (Llama-3.3-70B) — fastest inference."""
    return _query_openai_compatible(question, context, key, GROQ_ENDPOINT, GROQ_MODEL)


def _query_gemini(question: str, context: str, key: str) -> str:
    """Query Google Gemini 2.0 Flash — different REST format."""
    biz = _get_business_ctx("general")
    prompt_text = (
        "You are a Bitumen Sales Dashboard AI assistant for PPS Anantam Capital Pvt Ltd. "
        "Answer ONLY from the dashboard data provided. Use Indian number formatting "
        "(Rs crore/lakh). Dates: DD-MM-YYYY. Be concise but complete.\n\n"
        f"{biz}\n\n"
        f"LIVE DASHBOARD DATA:\n{context[:4000]}\n\n"
        f"Question: {question}"
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": MAX_TOKENS,
        },
    }).encode("utf-8")

    url = f"{GEMINI_ENDPOINT}/{GEMINI_MODEL}:generateContent?key={key}"
    req = _urllib_req.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _urllib_req.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def _query_mistral(question: str, context: str, key: str) -> str:
    """Query Mistral Small — EU-safe, good for emails."""
    return _query_openai_compatible(question, context, key, MISTRAL_ENDPOINT, MISTRAL_MODEL)


def _query_deepseek(question: str, context: str, key: str) -> str:
    """Query DeepSeek Chat — research only, PII stripped."""
    return _query_openai_compatible(question, context, key, DEEPSEEK_ENDPOINT, DEEPSEEK_MODEL)


def _query_openai(question: str, context: str, key: str) -> str:
    """Query OpenAI GPT-4o-mini. Tries SDK first, then falls back to requests.post."""
    biz = _get_business_ctx("general")
    messages = [
        {"role": "system", "content": (
            "You are a Bitumen Sales Dashboard AI assistant for PPS Anantam Capital Pvt Ltd. "
            "Answer ONLY from the dashboard data provided. Use Indian number formatting "
            "(₹ crore/lakh). Dates: DD-MM-YYYY. Be concise but complete.\n\n"
            f"{biz}\n\n"
            f"LIVE DASHBOARD DATA:\n{context[:5000]}"
        )},
        {"role": "user", "content": question},
    ]

    # --- Try OpenAI SDK (if installed) ---
    try:
        import openai as _oai
        client = _oai.OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except ImportError:
        pass  # SDK not installed — fall through to requests

    # --- HTTP requests fallback (no SDK needed) ---
    import requests as _req
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       OPENAI_MODEL,
        "messages":    messages,
        "max_tokens":  MAX_TOKENS,
        "temperature": 0.3,
    }
    r = _req.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def get_preferred_ollama_model() -> str:
    """Get the user's preferred Ollama model from config."""
    try:
        if CFG_FILE.exists():
            cfg = json.loads(CFG_FILE.read_text(encoding="utf-8"))
            model = cfg.get("ollama_preferred_model", "").strip()
            if model:
                return model
    except Exception:
        pass
    return OLLAMA_DEFAULT_MODEL


def set_preferred_ollama_model(model: str) -> None:
    """Save the user's preferred Ollama model to config."""
    try:
        cfg = {}
        if CFG_FILE.exists():
            cfg = json.loads(CFG_FILE.read_text(encoding="utf-8"))
        cfg["ollama_preferred_model"] = model.strip()
        CFG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass


def _query_ollama(question: str, context: str) -> str:
    import ollama
    model_name = get_preferred_ollama_model()
    biz = _get_business_ctx("general")
    resp = ollama.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": (
                "You are a Bitumen Sales Dashboard AI for PPS Anantam Capital Pvt Ltd. "
                "Answer ONLY from this data. Indian format: Rs crore/lakh, DD-MM-YYYY.\n\n"
                f"{biz}\n\n"
                f"LIVE DASHBOARD DATA:\n{context[:3000]}"
            )},
            {"role": "user", "content": question},
        ],
    )
    # ollama >= 0.2.0 returns a Pydantic object; older returns a dict
    if hasattr(resp, "message"):
        return resp.message.content.strip()
    return resp["message"]["content"].strip()


def _query_huggingface(question: str, context: str, token: str) -> str:
    from huggingface_hub import InferenceClient
    client = InferenceClient(
        model=HF_MODEL,
        token=token if token else None,
    )
    biz = _get_business_ctx("general")
    # Mistral/Zephyr instruction format
    prompt = (
        f"<|system|>\nYou are a Bitumen Sales Dashboard AI for PPS Anantam Capital Pvt Ltd. "
        f"{biz}\n\nAnswer ONLY from this data:\n{context[:2000]}</s>\n"
        f"<|user|>\n{question}</s>\n"
        f"<|assistant|>\n"
    )
    result = client.text_generation(
        prompt,
        max_new_tokens=512,
        temperature=0.3,
        stop_sequences=["</s>", "<|user|>"],
    )
    return result.strip()


def _query_gpt4all(question: str, context: str) -> str:
    from gpt4all import GPT4All
    biz = _get_business_ctx("general")
    # allow_download=True fetches the model on first run (~2 GB)
    model = GPT4All(GPT4ALL_MODEL, allow_download=True)
    with model.chat_session(
        system_prompt=(
            "You are a Bitumen Sales Dashboard AI for PPS Anantam Capital Pvt Ltd. "
            f"{biz}\n\nAnswer only from this data:\n{context[:1500]}"
        )
    ):
        return model.generate(question, max_tokens=512)


def _query_claude(question: str, context: str, key: str) -> str:
    import anthropic
    biz = _get_business_ctx("general")
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=(
            "You are a Bitumen Sales Dashboard AI for PPS Anantam Capital Pvt Ltd. "
            "Answer ONLY from the data provided. Indian format: ₹ crore/lakh, DD-MM-YYYY.\n\n"
            f"{biz}\n\n"
            f"LIVE DASHBOARD DATA:\n{context[:4000]}"
        ),
        messages=[{"role": "user", "content": question}],
    )
    return resp.content[0].text.strip()


def _run_provider(pid: str, question: str, context: str) -> tuple[str, Optional[str]]:
    """
    Call the appropriate provider. Returns (answer, error_or_None).
    Tracks health metrics and applies PII filter for restricted providers.
    """
    import time as _t
    key = get_api_key(pid)
    t0 = _t.time()

    # Check if provider is enabled in settings
    try:
        from settings_engine import load_settings
        _s = load_settings()
        enable_key = f"ai_provider_{pid}_enabled"
        if enable_key in _s and not _s[enable_key]:
            return "", f"{pid} is disabled in settings"
    except Exception:
        pass

    try:
        # PII filter for restricted providers (DeepSeek)
        q = question
        c = context
        p_info = next((x for x in PROVIDER_CHAIN if x["id"] == pid), {})
        if p_info.get("restricted") and _pii_filter_enabled():
            q = _strip_pii(question)
            c = _strip_pii(context)

        if pid == "openai":
            if not key:
                return "", "OpenAI API key not configured"
            ans = _query_openai(q, c, key)

        elif pid == "ollama":
            if not _ollama_running():
                return "", "Ollama daemon not running (start the Ollama app first)"
            ans = _query_ollama(q, c)

        elif pid == "huggingface":
            ans = _query_huggingface(q, c, key)

        elif pid == "gpt4all":
            ans = _query_gpt4all(q, c)

        elif pid == "claude":
            if not key:
                return "", "Anthropic API key not configured"
            ans = _query_claude(q, c, key)

        elif pid == "groq":
            if not key:
                return "", "Groq API key not configured"
            ans = _query_groq(q, c, key)

        elif pid == "gemini":
            if not key:
                return "", "Gemini API key not configured"
            ans = _query_gemini(q, c, key)

        elif pid == "mistral":
            if not key:
                return "", "Mistral API key not configured"
            ans = _query_mistral(q, c, key)

        elif pid == "deepseek":
            if not key:
                return "", "DeepSeek API key not configured"
            ans = _query_deepseek(q, c, key)

        else:
            return "", f"Unknown provider: {pid}"

        latency = (_t.time() - t0) * 1000
        _record_call(pid, True, latency)
        return ans, None

    except Exception as exc:
        latency = (_t.time() - t0) * 1000
        _record_call(pid, False, latency)
        return "", str(exc)

# ══════════════════════════════════════════════════════════════════════════════
# CORE FALLBACK LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def ask_with_fallback(question: str, context: str = "", start_from_primary: bool = False) -> dict:
    """
    Try providers in priority order starting from the current active provider
    (or from provider 0 / primary if start_from_primary=True).

    Returns:
      {
        answer, provider_id, provider_name, provider_type, provider_icon,
        fallback_reason, tried, error
      }
    """
    with _lock:
        start_idx = 0 if start_from_primary else _G["active_idx"]

    tried: list[dict] = []

    for offset in range(len(PROVIDER_CHAIN)):
        idx = (start_idx + offset) % len(PROVIDER_CHAIN)
        p   = PROVIDER_CHAIN[idx]

        # Skip if auto-disabled (health check)
        if _is_provider_disabled(p["id"]):
            tried.append({"id": p["id"], "name": p["name"],
                          "reason": f"{p['name']} auto-disabled (high error rate)"})
            continue

        # Skip if package not installed (urllib always available for cloud providers)
        if p["pkg"] not in ("urllib",) and not _pkg_ok(p["pkg"]):
            tried.append({"id": p["id"], "name": p["name"],
                          "reason": f"Package '{p['pkg']}' not installed. Run: {p['install_cmd']}"})
            continue

        # Skip if needs key but key missing
        if p["needs_key"] and not get_api_key(p["id"]):
            tried.append({"id": p["id"], "name": p["name"],
                          "reason": f"API key not configured for {p['name']}"})
            continue

        answer, err = _run_provider(p["id"], question, context)
        if err:
            with _lock:
                _G["last_errors"][p["id"]] = err
            tried.append({"id": p["id"], "name": p["name"], "reason": err})
            _log("fallback", p["id"], f"Failed — {err}")
            continue

        # ── SUCCESS ─────────────────────────────────────────────────────────
        with _lock:
            _G["active_idx"] = idx
            _G["last_errors"].pop(p["id"], None)

        fallback_reason = ""
        if tried:
            fallback_reason = " → ".join(f'{t["name"]} ({t["reason"]})' for t in tried)

        _log("success", p["id"], f"Answered: {question[:60]}")

        return {
            "answer":          answer,
            "provider_id":     p["id"],
            "provider_name":   p["name"],
            "provider_type":   p["type"],
            "provider_icon":   p["icon"],
            "fallback_reason": fallback_reason,
            "tried":           tried,
            "error":           None,
        }

    # ── ALL FAILED ───────────────────────────────────────────────────────────
    _log("all_failed", "none", f"All providers failed for: {question[:60]}")
    return {
        "answer": (
            "⚠️ All AI providers are currently unavailable.\n\n"
            "**To activate a provider:**\n"
            "• OpenAI: enter API key in sidebar\n"
            "• Ollama: install from ollama.com then run `ollama pull llama3`\n"
            "• HuggingFace: `pip install huggingface-hub`\n"
            "• GPT4All: `pip install gpt4all`\n"
            "• Claude: enter Anthropic API key in sidebar"
        ),
        "provider_id":     "none",
        "provider_name":   "None Available",
        "provider_type":   "—",
        "provider_icon":   "❌",
        "fallback_reason": "All providers failed",
        "tried":           tried,
        "error":           "all_failed",
    }


def format_who_response(result: dict) -> str:
    """
    Wrap the raw AI answer in the standard 'Who is this?' identity banner.
    """
    name  = result["provider_name"]
    ptype = result["provider_type"]
    icon  = result["provider_icon"]
    tried = result.get("tried", [])
    ts    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")

    # Build status line
    if result["provider_id"] == "openai" and not tried:
        status_line = "✅ Paid OpenAI API is **active and responding**."
    elif tried:
        # Find primary failure reason
        primary_fail = next((t["reason"] for t in tried if t["id"] == "openai"), "")
        if primary_fail:
            status_line = (
                f"⚠️ Paid OpenAI API is **unavailable** ({primary_fail}). "
                f"Auto-switched to **{name}** (free fallback). "
                "Will restore silently when OpenAI recovers."
            )
        else:
            status_line = f"⚠️ Switched to **{name}** — higher-priority providers unavailable."
    else:
        status_line = f"ℹ️ Serving via **{ptype}**."

    header = (
        f"{icon} **Who is this?** I am **{name} — Free Dashboard AI** "
        f"({ptype}).\n{status_line}"
    )

    if result.get("error") == "all_failed":
        return f"{header}\n\n{result['answer']}"

    return (
        f"{header}\n\n"
        f"---\n\n"
        f"{result['answer']}\n\n"
        f"---\n"
        f"_Active AI: {name} | {ptype} | {ts}_"
    )

# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND MONITOR — silently restores primary every 5 minutes
# ══════════════════════════════════════════════════════════════════════════════

def _monitor_loop():
    while True:
        time.sleep(MONITOR_INTERVAL)
        with _lock:
            if _G["active_idx"] == 0:
                continue   # Already on primary — nothing to do
        # Test if primary (Ollama — free, local) is back
        primary = PROVIDER_CHAIN[0]
        if not _pkg_ok(primary["pkg"]):
            continue
        if primary["needs_key"]:
            key = get_api_key(primary["id"])
            if not key:
                continue
        _, err = _run_provider(primary["id"], "Reply with exactly: OK", "Dashboard health check.")
        if not err:
            with _lock:
                _G["active_idx"] = 0
            _log("restored", primary["id"],
                 f"Primary {primary['name']} recovered — silently switched back from fallback")


def start_monitor():
    """Start the background monitor thread (idempotent)."""
    with _lock:
        if _G["monitor_started"]:
            return
        _G["monitor_started"] = True
    t = threading.Thread(target=_monitor_loop, daemon=True, name="AIFallbackMonitor")
    t.start()

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def _log(event: str, provider: str, message: str):
    record = {
        "ts":       datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "event":    event,
        "provider": provider,
        "message":  message,
    }
    try:
        logs: list = []
        if LOG_FILE.exists():
            logs = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        logs.append(record)
        if len(logs) > 1000:
            logs = logs[-1000:]
        LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_logs(n: int = 100) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    try:
        data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        return list(reversed(data[-n:]))
    except Exception:
        return []


def get_active_provider() -> dict:
    with _lock:
        return PROVIDER_CHAIN[_G["active_idx"]]


def force_provider(provider_id: str) -> bool:
    """Manually override the active provider (for testing/UI)."""
    for i, p in enumerate(PROVIDER_CHAIN):
        if p["id"] == provider_id:
            with _lock:
                _G["active_idx"] = i
            _log("manual_override", provider_id, f"User manually switched to {p['name']}")
            return True
    return False


def get_active_model_name() -> str:
    """Returns human-readable name of the active AI model (for UI display)."""
    p = get_active_provider()
    pid = p["id"]
    cost = p.get("cost", "FREE")
    if pid == "ollama":
        model = get_preferred_ollama_model()
        return f"{model.title()} ({cost} · Local)"
    elif pid == "huggingface":
        return f"Zephyr-7B ({cost} · Cloud)"
    elif pid == "gpt4all":
        return f"Phi-3 Mini ({cost} · Offline)"
    elif pid == "openai":
        return f"GPT-4o-mini ({cost})"
    elif pid == "claude":
        return f"Claude Haiku ({cost})"
    elif pid == "groq":
        return f"Llama-3.3-70B ({cost} · Groq)"
    elif pid == "gemini":
        return f"Gemini 2.0 Flash ({cost} · Google)"
    elif pid == "mistral":
        return f"Mistral Small ({cost} · EU)"
    elif pid == "deepseek":
        return f"DeepSeek Chat ({cost} · Research)"
    return p["name"]


def get_provider_status() -> list[dict]:
    """Returns status of all providers for UI display."""
    statuses = []
    with _lock:
        active_idx = _G["active_idx"]
    for i, p in enumerate(PROVIDER_CHAIN):
        pkg_ok = _pkg_ok(p["pkg"]) if p["pkg"] not in ("urllib",) else True
        key_ok = True
        if p["needs_key"]:
            key_ok = bool(get_api_key(p["id"]))
        health = get_provider_health(p["id"])
        statuses.append({
            "id": p["id"],
            "name": p["name"],
            "type": p["type"],
            "cost": p.get("cost", "FREE"),
            "icon": p["icon"],
            "pkg_installed": pkg_ok,
            "key_configured": key_ok,
            "is_active": i == active_idx,
            "ready": pkg_ok and (key_ok or not p["needs_key"]) and not health.get("is_disabled"),
            "last_error": _G["last_errors"].get(p["id"], ""),
            "health": health,
        })
    return statuses


# ══════════════════════════════════════════════════════════════════════════════
# TASK-BASED ROUTING — Right AI for right job
# ══════════════════════════════════════════════════════════════════════════════

TASK_ROUTING_TABLE = {
    "whatsapp_reply":  {"primary": "groq",    "fallback": ["ollama", "gemini"]},
    "email_draft":     {"primary": "gemini",  "fallback": ["ollama", "mistral"]},
    "market_analysis": {"primary": "gemini",  "fallback": ["deepseek", "ollama"]},
    "customer_chat":   {"primary": "groq",    "fallback": ["ollama", "gemini"]},
    "director_brief":  {"primary": "gemini",  "fallback": ["ollama", "groq"]},
    "call_script":     {"primary": "ollama",  "fallback": ["groq", "gemini"]},
    "price_inquiry":   {"primary": "groq",    "fallback": ["ollama", "gemini"]},
    "hindi_regional":  {"primary": "gemini",  "fallback": ["ollama", "groq"]},
    "private_data":    {"primary": "ollama",  "fallback": ["gpt4all"]},
    "research_only":   {"primary": "deepseek", "fallback": ["gemini", "mistral"]},
}


def ask_routed(question: str, context: str = "",
               task_type: str = "customer_chat") -> dict:
    """
    Task-based AI routing — tries the best provider for the job first,
    then falls to task-specific fallbacks, then global ask_with_fallback.

    Returns same dict format as ask_with_fallback + 'routed' key.
    """
    route = TASK_ROUTING_TABLE.get(task_type)
    if not route:
        result = ask_with_fallback(question, context, start_from_primary=True)
        result["routed"] = False
        result["task_type"] = task_type
        return result

    # Try primary for this task type
    chain = [route["primary"]] + route.get("fallback", [])
    tried: list[dict] = []

    for pid in chain:
        p = next((x for x in PROVIDER_CHAIN if x["id"] == pid), None)
        if not p:
            continue

        # Skip disabled
        if _is_provider_disabled(pid):
            tried.append({"id": pid, "name": p["name"],
                          "reason": f"Auto-disabled (health)"})
            continue

        # Skip if pkg not available (local providers)
        if p["pkg"] not in ("urllib",) and not _pkg_ok(p["pkg"]):
            tried.append({"id": pid, "name": p["name"],
                          "reason": f"Package not installed"})
            continue

        # Skip if key needed but missing
        if p["needs_key"] and not get_api_key(pid):
            tried.append({"id": pid, "name": p["name"],
                          "reason": f"API key not configured"})
            continue

        answer, err = _run_provider(pid, question, context)
        if err:
            tried.append({"id": pid, "name": p["name"], "reason": err})
            _log("routed_fallback", pid, f"Task={task_type} — {err}")
            continue

        # Success
        _log("routed_success", pid, f"Task={task_type}: {question[:50]}")
        fallback_reason = ""
        if tried:
            fallback_reason = " -> ".join(f'{t["name"]} ({t["reason"]})' for t in tried)

        return {
            "answer": answer,
            "provider_id": pid,
            "provider_name": p["name"],
            "provider_type": p["type"],
            "provider_icon": p["icon"],
            "fallback_reason": fallback_reason,
            "tried": tried,
            "error": None,
            "routed": True,
            "task_type": task_type,
        }

    # All task-specific providers failed — fall to global chain
    _log("routed_global_fallback", "none",
         f"Task={task_type} all specific providers failed — using global chain")
    result = ask_with_fallback(question, context, start_from_primary=True)
    result["routed"] = False
    result["task_type"] = task_type
    return result


# ══════════════════════════════════════════════════════════════════════════════
# VOICE STUBS — ElevenLabs TTS + Whisper STT (placeholder)
# ══════════════════════════════════════════════════════════════════════════════

def text_to_speech(text: str, voice_id: str = "pNInz6obpgDQGcFmaJgB",
                   language: str = "en") -> dict:
    """
    ElevenLabs TTS stub — converts text to audio bytes.
    Returns {success, audio_bytes, error}.
    """
    try:
        from settings_engine import load_settings, get_api_key_secure
        settings = load_settings()
        if not settings.get("voice_tts_enabled"):
            return {"success": False, "audio_bytes": b"", "error": "TTS not enabled"}
        api_key = get_api_key_secure("elevenlabs_api_key")
        if not api_key:
            return {"success": False, "audio_bytes": b"", "error": "ElevenLabs API key not configured"}

        payload = json.dumps({
            "text": text[:5000],
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }).encode("utf-8")
        req = _urllib_req.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            data=payload,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        with _urllib_req.urlopen(req, timeout=30) as resp:
            audio = resp.read()
        return {"success": True, "audio_bytes": audio, "error": ""}
    except Exception as e:
        return {"success": False, "audio_bytes": b"", "error": str(e)}


def speech_to_text(audio_path: str, language: str = "en") -> dict:
    """
    Whisper STT stub — transcribes audio file to text.
    Returns {success, text, error}.
    Requires: pip install openai-whisper (local) or OpenAI API.
    """
    try:
        from settings_engine import load_settings
        if not load_settings().get("voice_stt_enabled"):
            return {"success": False, "text": "", "error": "STT not enabled"}
        # Try local whisper first
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, language=language)
            return {"success": True, "text": result.get("text", ""), "error": ""}
        except ImportError:
            return {"success": False, "text": "",
                    "error": "Whisper not installed. Run: pip install openai-whisper"}
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}
