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
