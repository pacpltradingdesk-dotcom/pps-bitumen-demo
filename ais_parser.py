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
