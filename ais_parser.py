"""
PPS Anantam — AIS message parser (pure, no network / no streamlit).
Parses AISStream.io WebSocket messages into a normalized vessel registry
and builds JSON snapshots. Kept dependency-free so it is fully unit-testable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# AIS ship-type codes 80-89 = tankers (all subtypes).
TANKER_MIN, TANKER_MAX = 80, 89

# AIS sentinel "not available" values.
SOG_NA, COG_NA, HEADING_NA = 1023, 360, 511


def clean_ais_text(s: str | None) -> str:
    """Strip AIS '@' padding and surrounding whitespace."""
    if not s:
        return ""
    return s.replace("@", "").strip()


def is_tanker(ship_type: int | None) -> bool:
    """True if the AIS ship type code is in the tanker range (80-89)."""
    return ship_type is not None and TANKER_MIN <= ship_type <= TANKER_MAX


def parse_message(raw: dict) -> dict | None:
    """Normalize an AISStream message into a partial record.

    Returns a dict with `kind` = "position" or "static", or None when the
    message type is irrelevant or the MMSI is missing/invalid.
    """
    mtype = raw.get("MessageType")
    meta = raw.get("MetaData") or {}
    msg = raw.get("Message") or {}
    mmsi = meta.get("MMSI")

    if mtype == "PositionReport":
        pr = msg.get("PositionReport") or {}
        mmsi = mmsi if mmsi is not None else pr.get("UserID")
        if mmsi is None:
            return None
        lat, lon = pr.get("Latitude"), pr.get("Longitude")
        if lat is None or lon is None:
            return None
        sog, cog, hdg = pr.get("Sog"), pr.get("Cog"), pr.get("TrueHeading")
        return {
            "mmsi": int(mmsi), "kind": "position",
            "lat": lat, "lon": lon,
            "sog": None if sog in (None, SOG_NA) else sog,
            "cog": None if cog in (None, COG_NA) else cog,
            "heading": None if hdg in (None, HEADING_NA) else hdg,
            "nav_status": pr.get("NavigationalStatus"),
            "time_utc": meta.get("time_utc"),
        }

    if mtype == "ShipStaticData":
        sd = msg.get("ShipStaticData") or {}
        mmsi = mmsi if mmsi is not None else sd.get("UserID")
        if mmsi is None:
            return None
        return {
            "mmsi": int(mmsi), "kind": "static",
            "name": clean_ais_text(sd.get("Name") or meta.get("ShipName")),
            "imo": sd.get("ImoNumber"),
            "ship_type": sd.get("Type"),
            "destination": clean_ais_text(sd.get("Destination")),
            "draught": sd.get("MaximumStaticDraught"),
            "time_utc": meta.get("time_utc"),
        }

    return None


def _parse_iso(s: str | None) -> datetime:
    """Parse an ISO-8601 'Z' timestamp into an aware UTC datetime.

    Returns epoch (very old) if unparseable, so callers treat it as stale.
    """
    if not s:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


_POSITION_FIELDS = ("lat", "lon", "sog", "cog", "heading", "nav_status")
_STATIC_FIELDS = ("name", "imo", "ship_type", "destination", "draught")


def update_registry(registry: dict, rec: dict | None, now_iso: str) -> None:
    """Merge a parsed record into the MMSI-keyed registry (in place).

    Only non-None incoming fields overwrite, so a sentinel/blank value never
    clobbers previously-good data. `now_iso` becomes the vessel's last_seen.
    """
    if not rec:
        return
    mmsi = rec["mmsi"]
    v = registry.setdefault(mmsi, {"mmsi": mmsi})
    fields = _POSITION_FIELDS if rec["kind"] == "position" else _STATIC_FIELDS
    for k in fields:
        if rec.get(k) is not None:
            v[k] = rec[k]
    v["last_seen"] = now_iso


def prune_registry(registry: dict, now: datetime, max_age_min: int) -> None:
    """Drop vessels not seen within `max_age_min` minutes (in place)."""
    cutoff = now - timedelta(minutes=max_age_min)
    stale = [m for m, v in registry.items() if _parse_iso(v.get("last_seen")) < cutoff]
    for m in stale:
        del registry[m]


def build_snapshot(registry: dict, now_iso: str) -> dict:
    """Build the JSON snapshot: tankers that currently have a position."""
    vessels = [
        v for v in registry.values()
        if is_tanker(v.get("ship_type")) and v.get("lat") is not None
    ]
    return {"updated_utc": now_iso, "source": "aisstream", "vessels": vessels}


def in_any_box(lat: float | None, lon: float | None, boxes: list) -> bool:
    """True if (lat, lon) falls inside any [[latA,lonA],[latB,lonB]] box.

    Corner order is normalized (min/max), so boxes may list corners in any order.
    Used as a client-side guard because the AISStream bounding-box filter is
    not always honored — we enforce the region ourselves.
    """
    if lat is None or lon is None:
        return False
    for (a_lat, a_lon), (b_lat, b_lon) in boxes:
        if min(a_lat, b_lat) <= lat <= max(a_lat, b_lat) and \
           min(a_lon, b_lon) <= lon <= max(a_lon, b_lon):
            return True
    return False


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON via temp file + os.replace so readers never see a partial file."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    os.replace(tmp, path)
