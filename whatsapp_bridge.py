"""WhatsApp bridge for Client Chat — per-user WhatsApp linking + send + inbound ingest.

The dashboard never runs WhatsApp itself (that needs Node + headless Chrome). It
talks to a small **isolated** service `pps-chat-wa` (own pm2 process / own port /
own sessions) over localhost. That service is completely separate from the bulk
`whatsapp-server` — this bridge is the only thing the dashboard imports.

Flow:
  - Each dashboard user links THEIR OWN WhatsApp via QR (start_link / link_status).
  - send_text(phone, text, from_user) → POST /send → the user's linked client sends.
  - The service writes every inbound customer message to wa_inbound.jsonl; the
    dashboard drains it into chat_messages via drain_inbound() on each render.

Locally (no service, no /opt/pps-bitumen) everything degrades to a safe stub so the
approve-flow UI can still be exercised offline.
"""
import json
import os
import re
import datetime
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# ── Isolated pps-chat-wa service (localhost only) ──
_SVC_URL = os.environ.get("PPS_CHATWA_URL", "http://127.0.0.1:8530").rstrip("/")
_TOKEN_FILE = Path("/opt/pps-chat-wa/.token")


def _svc_token() -> str:
    try:
        if _TOKEN_FILE.exists():
            return _TOKEN_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return os.environ.get("PPS_CHATWA_TOKEN", "")


# ── Dashboard-owned runtime files (on the VPS app dir) ──
_VPS_DIR = Path("/opt/pps-bitumen")
_INBOUND = _VPS_DIR / "wa_inbound.jsonl"           # written by the service
_INBOUND_POS = _VPS_DIR / "wa_inbound.pos"         # drain offset
_OUTBOX_PATH = Path(__file__).resolve().parent / "whatsapp_outbox.json"  # local stub only


def normalize_phone(raw: str) -> str:
    """Strip to digits and default to India country code for 10-digit numbers."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:                 # bare Indian mobile → add 91
        digits = "91" + digits
    return digits


def conversation_id_for_phone(phone: str) -> str:
    """Stable conversation id keyed by phone, so inbound + outbound merge into one thread."""
    return f"wa_{normalize_phone(phone)}"


# ── Talking to the isolated service ──
def _svc_call(method: str, path: str, payload: dict | None = None, timeout: float = 30.0) -> dict:
    """Call the pps-chat-wa service. Returns parsed JSON, or {'ok': False, 'error': ...}."""
    url = f"{_SVC_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("x-token", _svc_token())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {"ok": True}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}", "offline": False}
    except Exception as e:
        # service not running / not reachable (e.g. local dev)
        return {"ok": False, "error": str(e), "offline": True}


def link_status(user: str) -> dict:
    """Current WhatsApp link status for a dashboard user → {status, number, qr?}."""
    return _svc_call("GET", f"/status?user={urllib.parse.quote(user)}")


def start_link(user: str) -> dict:
    """Begin linking this user's WhatsApp → {status:'qr', qr} or {status:'connected', number}."""
    return _svc_call("POST", "/link/start", {"user": user})


def unlink(user: str) -> dict:
    """Log out / remove this user's linked WhatsApp."""
    return _svc_call("POST", "/unlink", {"user": user})


def send_text(phone: str, text: str, from_user: str | None = None) -> dict:
    """Outbound: deliver an approved reply from `from_user`'s linked WhatsApp."""
    if not (text or "").strip():
        return {"ok": False, "error": "empty message"}

    if from_user:
        res = _svc_call("POST", "/send", {"user": from_user, "phone": normalize_phone(phone), "text": text})
        if res.get("ok"):
            return {"ok": True, "channel": f"WhatsApp ({res.get('number', from_user)})"}
        if not res.get("offline"):
            return {"ok": False, "error": res.get("error", "send failed")}
        # service offline → fall through to local stub

    # ── Local stub (service unreachable / no user) ──
    job = {"phone": normalize_phone(phone), "text": text,
           "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": "queued"}
    try:
        existing = json.loads(_OUTBOX_PATH.read_text(encoding="utf-8")) if _OUTBOX_PATH.exists() else []
        if not isinstance(existing, list):
            existing = []
    except Exception:
        existing = []
    existing.append(job)
    try:
        _OUTBOX_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "queued": True, "channel": "whatsapp (local stub — service offline)"}


# ── Inbound ──
def ingest_incoming(phone: str, name: str, text: str) -> str:
    """Record one incoming customer message into chat_messages (sender_type='customer')."""
    from database import insert_chat_message
    cid = conversation_id_for_phone(phone)
    insert_chat_message({
        "conversation_id": cid,
        "sender_type": "customer",
        "sender_name": (name or "").strip() or normalize_phone(phone),
        "message_text": text,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return cid


def drain_inbound() -> int:
    """Drain wa_inbound.jsonl (written by the service) into chat_messages. Returns count.

    Uses a byte offset so each line ingests exactly once. No-op locally (file absent).
    Called on each Client Chat render; a 1-min cron also runs it for background ingest.
    """
    if not _INBOUND.exists():
        return 0
    try:
        start = int(_INBOUND_POS.read_text(encoding="utf-8").strip()) if _INBOUND_POS.exists() else 0
    except Exception:
        start = 0
    try:
        with _INBOUND.open("r", encoding="utf-8") as f:
            f.seek(start)
            lines = f.readlines()
            end = f.tell()
    except Exception:
        return 0
    n = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
            ingest_incoming(j.get("phone", ""), j.get("name", ""), j.get("text", ""))
            n += 1
        except Exception:
            continue
    try:
        _INBOUND_POS.write_text(str(end), encoding="utf-8")
    except Exception:
        pass
    return n
