"""Manual Price Entry engine — pure logic behind the Fortnight CRM entry form.

Owns the three behaviours the form used to fake (live audit 09-07-2026):

1. **Routing** — a field quote updates the correct live_prices.json key for its
   price type: drum quotes go to DRUM_* regional keys, bulk quotes go to the
   matching refinery/import override key (VG30_BASE for the Ex-Mumbai base).
   Unmapped bulk locations are LOG-ONLY — never a silent wrong-key write.
2. **GST/freight math** — a GST-inclusive quote is stripped to the basic
   ex-GST price before it touches any live key (the board stores basic prices;
   the calculator adds GST back on top).
3. **Real entry log** — every submit is persisted to manual_entries.json with
   user/remarks/conflict, replacing the old hardcoded demo table.

No streamlit imports — fully unit-testable (tests/test_manual_entry_engine.py).
"""
from __future__ import annotations

import datetime
import json
import threading
from pathlib import Path
from typing import Optional

import pytz

ROOT = Path(__file__).parent
ENTRIES_PATH = ROOT / "manual_entries.json"
PROOF_DIR = ROOT / "uploads" / "manual_entry_proofs"
MAX_ENTRIES = 500
CONFLICT_THRESHOLD_PCT = 5.0  # matches settings.json price-alert swing threshold

_IST = pytz.timezone("Asia/Kolkata")
_lock = threading.RLock()


# ── GST / freight math ───────────────────────────────────────────────────────

def compute_basic_price(quote: float, freight: float, gst_pct: float,
                        gst_inclusive: bool) -> int:
    """Reduce a field quote to the basic ex-GST, ex-freight price.

    The live board stores BASIC prices (the pricing calculator adds GST and
    transport on top), so an inclusive quote must be stripped before storage.
    """
    if quote is None or quote <= 0:
        raise ValueError("quote must be a positive number")
    ex_gst = quote / (1 + gst_pct / 100.0) if gst_inclusive else float(quote)
    basic = ex_gst - (freight or 0)
    if basic <= 0:
        raise ValueError("basic price came out non-positive — check quote/freight")
    return round(basic)


# ── override-key routing ─────────────────────────────────────────────────────

def _drum_prefix(location: str) -> str:
    """Gujarat/Kandla/Mundra region → DRUM_KANDLA, everything else → DRUM_MUMBAI."""
    loc = (location or "").lower()
    if any(k in loc for k in ("kandla", "mundra", "gujarat", "gandhidham")):
        return "DRUM_KANDLA"
    return "DRUM_MUMBAI"


_CITY_ALIASES = {
    "baroda": "koyali", "vadodara": "koyali",
    "vizag": "visakhapatnam", "madras": "chennai", "cochin": "kochi",
}


def _bulk_key_map() -> dict:
    """City token → live_prices override key, derived from price_master so the
    mapping can never drift from the board. Port-only cities map to BULK_*
    import keys; refinery cities map to their refinery key."""
    mapping: dict = {}
    try:
        import price_master
        for name, grade, key, _price in price_master.board_items("refinery"):
            if grade != "VG30":
                continue
            city = name.split()[-1].lower()          # "IOCL Koyali" -> "koyali"
            mapping.setdefault(city, key)
        for name, _grade, key, _price in price_master.board_items("import"):
            city = name.split()[0].lower()           # "Kandla Port Import" -> "kandla"
            mapping.setdefault(city, key)
    except Exception:
        pass
    # The Ex-Mumbai bulk VG30 IS the board base — override the refinery entry.
    mapping["mumbai"] = "VG30_BASE"
    mapping["jnpt"] = "VG30_BASE"
    return mapping


def resolve_override_key(location: str, grade: str,
                         price_type: str) -> Optional[str]:
    """Return the live_prices.json key a quote should update, or None.

    None means LOG-ONLY: the entry is recorded but no live price changes.
    Guessing a key was how a bulk entry once poisoned DRUM_KANDLA_VG30.
    """
    grade = (grade or "").upper()
    ptype = (price_type or "").strip().lower()
    if ptype == "drum":
        if grade not in ("VG30", "VG10"):
            return None  # only seeded drum keys exist; others surface nowhere
        return f"{_drum_prefix(location)}_{grade}"
    if ptype == "bulk":
        if grade != "VG30":
            return None  # board carries only VG30 bulk keys
        loc = (location or "").lower()
        for alias, canonical in _CITY_ALIASES.items():
            if alias in loc:
                loc = loc.replace(alias, canonical)
        for city, key in _bulk_key_map().items():
            if city in loc:
                return key
    return None


def write_override_key(key: str, price: float,
                       path: Optional[Path] = None) -> bool:
    """Locked read-merge-write of one live_prices.json override key.

    All override writes (Entry Form + Refinery/Import Override tab) go through
    this single locked path so near-simultaneous submits can't lose updates.
    """
    lp_path = path or (ROOT / "live_prices.json")
    if not key:
        return False
    try:
        with _lock:
            lp: dict = {}
            if lp_path.exists():
                try:
                    loaded = json.loads(lp_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        lp = loaded
                except Exception:
                    lp = {}
            lp[key] = int(price)
            lp_path.write_text(json.dumps(lp, indent=4, ensure_ascii=False),
                               encoding="utf-8")
        return True
    except Exception:
        return False


# ── conflict check ───────────────────────────────────────────────────────────

def is_conflict(basic: float, auto: Optional[float],
                threshold_pct: float = CONFLICT_THRESHOLD_PCT) -> bool:
    """Flag entries that deviate from the auto/derived price beyond threshold."""
    if not auto:
        return False
    return abs(basic - auto) / auto * 100.0 > threshold_pct


# ── real entry log ───────────────────────────────────────────────────────────

def _now_ist() -> str:
    return datetime.datetime.now(_IST).strftime("%d-%m-%Y %H:%M IST")


def build_entry(*, user: str, location: str, grade: str, price_type: str,
                quote: float, freight: float, gst_pct: float,
                gst_inclusive: bool, basic_price: int,
                applied_key: Optional[str], auto_price: Optional[float],
                target_revision: str, remarks: str = "",
                proof_file: str = "") -> dict:
    return {
        "entry_ist": _now_ist(),
        "target_revision": target_revision,
        "location": location,
        "grade": grade,
        "price_type": price_type,
        "quote": float(quote),
        "freight": float(freight or 0),
        "gst_pct": float(gst_pct or 0),
        "gst_inclusive": bool(gst_inclusive),
        "basic_price": int(basic_price),
        "applied_key": applied_key or "",
        "auto_price": float(auto_price) if auto_price else None,
        "conflict": is_conflict(basic_price, auto_price),
        "user": user or "unknown",
        "remarks": (remarks or "").strip(),
        "proof_file": proof_file or "",
    }


def append_entry(entry: dict, path: Path = ENTRIES_PATH) -> None:
    with _lock:
        entries = []
        try:
            if path.exists():
                entries = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(entries, list):
                    entries = []
        except Exception:
            entries = []
        entries.append(entry)
        if len(entries) > MAX_ENTRIES:
            entries = entries[-MAX_ENTRIES:]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, indent=2, ensure_ascii=False),
                        encoding="utf-8")


def load_entries(path: Path = ENTRIES_PATH, limit: int = 50) -> list:
    """Newest first."""
    try:
        if path.exists():
            entries = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(entries, list):
                return list(reversed(entries))[:limit]
    except Exception:
        pass
    return []


def save_proof(data: bytes, original_name: str,
               directory: Path = PROOF_DIR) -> str:
    """Persist an uploaded quotation proof; returns the stored filename."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(_IST).strftime("%Y%m%d_%H%M%S")
    safe = "".join(c for c in (original_name or "proof")
                   if c.isalnum() or c in "._-")[-80:]
    fname = f"{stamp}_{safe}"
    (directory / fname).write_bytes(data)
    return fname
