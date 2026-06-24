"""WhatsApp bridge for Client Chat — inbound ingest + outbound send.

The dashboard never talks to WhatsApp directly. It talks to this thin adapter,
which keeps the shared VPS WhatsApp infra decoupled and the dashboard
channel-agnostic.

Phase 1 (this file, local & safe):
  - send_text()      → enqueues the reply to a local outbox file (whatsapp_outbox.json).
                       No real message is sent; lets the whole approve-flow be tested.
  - ingest_incoming()→ writes an incoming customer message into chat_messages so it
                       shows up in the Client Chat inbox (used by the "simulate
                       incoming" tester, and later by the real WhatsApp listener).

Phase 2 (VPS wiring): swap send_text()'s body to push the job onto the existing
VPS WhatsApp send-queue, and run a listener on the WhatsApp server that calls
ingest_incoming() for every real inbound customer message. The dashboard code does
NOT change — only this adapter does.
"""
import json
import re
import datetime
from pathlib import Path

_OUTBOX_PATH = Path(__file__).resolve().parent / "whatsapp_outbox.json"  # local stub — do NOT commit

# On the VPS the app dir is /opt/pps-bitumen; the WhatsApp bridge (pps_chat_bridge.js
# on the whatsapp-server) drains this JSONL queue and sends from janki's number.
# Locally this dir does not exist, so send_text() falls back to the local stub.
_VPS_DIR = Path("/opt/pps-bitumen")
_VPS_OUTBOUND = _VPS_DIR / "wa_outbound.jsonl"


def normalize_phone(raw: str) -> str:
    """Strip to digits and default to India country code for 10-digit numbers."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:                 # bare Indian mobile → add 91
        digits = "91" + digits
    return digits


def conversation_id_for_phone(phone: str) -> str:
    """Stable conversation id keyed by phone, so inbound + outbound merge into one thread."""
    return f"wa_{normalize_phone(phone)}"


def ingest_incoming(phone: str, name: str, text: str) -> str:
    """Record an incoming customer WhatsApp message into chat_messages (sender_type='customer').

    Returns the conversation_id. Phase 2's WhatsApp listener calls this for every
    real inbound message; Phase 1's "simulate incoming" tester also calls it.
    """
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


def send_text(phone: str, text: str) -> dict:
    """Outbound: deliver an approved sales reply to the customer over WhatsApp.

    Phase 1: append to a local outbox queue (no real send) and return a result dict.
    Phase 2: replace the body below with a push onto the VPS WhatsApp send-queue.
    """
    if not (text or "").strip():
        return {"ok": False, "error": "empty message"}

    # ── VPS live mode: append to the JSONL queue the WhatsApp bridge drains ──
    if _VPS_DIR.is_dir():
        job = {"phone": normalize_phone(phone), "text": text,
               "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        try:
            with _VPS_OUTBOUND.open("a", encoding="utf-8") as f:
                f.write(json.dumps(job, ensure_ascii=False) + "\n")
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "queued": True, "channel": "WhatsApp (janki · 919152007245)"}

    # ── Local stub: append to a JSON outbox, no real send ──
    job = {
        "phone": normalize_phone(phone),
        "text": text,
        "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "queued",
    }
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
    return {"ok": True, "queued": True, "channel": "whatsapp (local outbox — not live)"}
