"""
PPS Anantam — Telegram Bot API Engine v1.0
============================================
Send messages, documents, and images to Telegram channels/groups via Bot API.
Settings stored in telegram_settings.json.
"""
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
_BASE = Path(__file__).parent
_SETTINGS_FILE = _BASE / "telegram_settings.json"
_LOG_FILE = _BASE / "telegram_log.json"
_API_BASE = "https://api.telegram.org/bot{token}"

_DEFAULT_SETTINGS = {
    "bot_token": "",
    "chats": [],
    "enabled": True,
}


# ---------------------------------------------------------------------------
#  Settings helpers
# ---------------------------------------------------------------------------

def _load_settings() -> dict:
    """Load bot token and chat configurations."""
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULT_SETTINGS)


def _save_settings(settings: dict):
    """Save settings to file."""
    _SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
#  Internal API helper
# ---------------------------------------------------------------------------

def _api_url(method: str, token: str | None = None) -> str:
    """Build full Telegram Bot API URL for *method*."""
    if token is None:
        token = _load_settings().get("bot_token", "")
    return f"{_API_BASE.format(token=token)}/{method}"


def _api_get(method: str, params: dict | None = None, token: str | None = None) -> dict:
    """GET request to Bot API with error handling."""
    try:
        resp = requests.get(_api_url(method, token), params=params or {}, timeout=15)
        return resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "description": str(exc)}
    except (ValueError, json.JSONDecodeError):
        return {"ok": False, "description": "Invalid JSON in API response"}


def _api_post(method: str, data: dict | None = None, files: dict | None = None,
              token: str | None = None) -> dict:
    """POST request to Bot API with error handling."""
    try:
        resp = requests.post(
            _api_url(method, token),
            data=data or {},
            files=files,
            timeout=30,
        )
        return resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "description": str(exc)}
    except (ValueError, json.JSONDecodeError):
        return {"ok": False, "description": "Invalid JSON in API response"}


# ---------------------------------------------------------------------------
#  Bot configuration
# ---------------------------------------------------------------------------

def configure_bot(token: str) -> dict:
    """Configure bot token. Returns bot info via getMe API call."""
    token = token.strip()
    if not token:
        return {"ok": False, "description": "Token cannot be empty."}

    result = _api_get("getMe", token=token)
    if result.get("ok"):
        settings = _load_settings()
        settings["bot_token"] = token
        _save_settings(settings)
        return {
            "ok": True,
            "bot": result.get("result", {}),
            "message": "Bot token saved successfully.",
        }
    return {
        "ok": False,
        "description": result.get("description", "Token verification failed."),
    }


def verify_bot() -> dict:
    """Verify bot token is valid. Returns bot info."""
    settings = _load_settings()
    token = settings.get("bot_token", "")
    if not token:
        return {"ok": False, "description": "No bot token configured."}

    result = _api_get("getMe", token=token)
    if result.get("ok"):
        return {"ok": True, "bot": result.get("result", {})}
    return {
        "ok": False,
        "description": result.get("description", "Token verification failed."),
    }


# ---------------------------------------------------------------------------
#  Chat management
# ---------------------------------------------------------------------------

def get_chat_list() -> list:
    """Get list of configured chat IDs with labels."""
    settings = _load_settings()
    return settings.get("chats", [])


def add_chat(chat_id: str, label: str = "", chat_type: str = "group"):
    """Add a chat ID to settings."""
    settings = _load_settings()
    chats = settings.get("chats", [])

    # Avoid duplicate chat_id
    for c in chats:
        if str(c.get("chat_id")) == str(chat_id):
            c["label"] = label or c.get("label", "")
            c["type"] = chat_type
            _save_settings(settings)
            return

    chats.append({
        "chat_id": str(chat_id),
        "label": label,
        "type": chat_type,
    })
    settings["chats"] = chats
    _save_settings(settings)


def remove_chat(chat_id: str):
    """Remove a chat ID from settings."""
    settings = _load_settings()
    chats = settings.get("chats", [])
    settings["chats"] = [c for c in chats if str(c.get("chat_id")) != str(chat_id)]
    _save_settings(settings)


# ---------------------------------------------------------------------------
#  Sending messages
# ---------------------------------------------------------------------------

def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> dict:
    """Send text message. Returns API response."""
    settings = _load_settings()
    if not settings.get("bot_token"):
        return {"ok": False, "description": "No bot token configured."}

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    result = _api_post("sendMessage", data=data)

    status = "success" if result.get("ok") else "failed"
    error = "" if result.get("ok") else result.get("description", "Unknown error")
    _log_send(chat_id, "message", status, error)

    return result


def send_document(chat_id: str, file_bytes: bytes, filename: str, caption: str = "") -> dict:
    """Send a file (PDF, etc). Returns API response."""
    settings = _load_settings()
    if not settings.get("bot_token"):
        return {"ok": False, "description": "No bot token configured."}

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"

    files = {"document": (filename, file_bytes)}
    result = _api_post("sendDocument", data=data, files=files)

    status = "success" if result.get("ok") else "failed"
    error = "" if result.get("ok") else result.get("description", "Unknown error")
    _log_send(chat_id, "document", status, error)

    return result


def send_photo(chat_id: str, image_bytes: bytes, caption: str = "") -> dict:
    """Send a photo/chart image. Returns API response."""
    settings = _load_settings()
    if not settings.get("bot_token"):
        return {"ok": False, "description": "No bot token configured."}

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"

    files = {"photo": ("photo.png", image_bytes, "image/png")}
    result = _api_post("sendPhoto", data=data, files=files)

    status = "success" if result.get("ok") else "failed"
    error = "" if result.get("ok") else result.get("description", "Unknown error")
    _log_send(chat_id, "photo", status, error)

    return result


# ---------------------------------------------------------------------------
#  Incoming updates (for setup verification)
# ---------------------------------------------------------------------------

def get_updates(offset: int = 0) -> list:
    """Get incoming messages (for setup verification)."""
    params = {}
    if offset:
        params["offset"] = offset
    result = _api_get("getUpdates", params=params)
    if result.get("ok"):
        return result.get("result", [])
    return []


# ---------------------------------------------------------------------------
#  Broadcast
# ---------------------------------------------------------------------------

def broadcast_message(text: str, parse_mode: str = "HTML") -> list:
    """Send to all configured chats. Returns list of results."""
    chats = get_chat_list()
    if not chats:
        return [{"ok": False, "description": "No chats configured."}]

    results = []
    for idx, chat in enumerate(chats):
        cid = chat.get("chat_id", "")
        if not cid:
            continue

        # Rate limiting: 0.5s sleep between consecutive sends
        if idx > 0:
            time.sleep(0.5)

        resp = send_message(cid, text, parse_mode=parse_mode)
        results.append({
            "chat_id": cid,
            "label": chat.get("label", ""),
            "ok": resp.get("ok", False),
            "description": resp.get("description", ""),
        })

    return results


# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------

def _log_send(chat_id: str, msg_type: str, status: str, error: str = ""):
    """Log send activity. Keeps last 500 entries."""
    entry = {
        "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
        "chat_id": str(chat_id),
        "type": msg_type,
        "status": status,
    }
    if error:
        entry["error"] = error

    # Load existing log
    log = []
    if _LOG_FILE.exists():
        try:
            log = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
            if not isinstance(log, list):
                log = []
        except (json.JSONDecodeError, OSError):
            log = []

    # Append and trim to last 500
    log.append(entry)
    log = log[-500:]

    try:
        _LOG_FILE.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass
