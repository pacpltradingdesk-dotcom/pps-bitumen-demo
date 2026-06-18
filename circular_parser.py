"""
PPS Anantam — Multi Energy circular parser (pure, no AI / no I/O / no Streamlit).

Turns rows extracted from the fortnightly "All India Petroleum Products Price
Revision" circular into price_master override keys, ready to write to
live_prices.json after a human review step.

Pipeline:  extracted rows  ->  normalize grade  ->  match location to keys  ->
           sanity-band check  ->  {override_key: price} + new VG30 base.

VG30 == 60/70 penetration grade, VG10 == 80/100 (IS 73:2013). Kept dependency-free
so it is fully unit-testable (see tests/test_circular_parser.py). The keys it
produces are validated against price_master by the test suite (drift guard).
"""
from __future__ import annotations

import re

# Bitumen bulk is ~₹70k-85k/MT; this wide band only rejects obvious OCR misreads
# (dropped or added digits), never a plausible real revision.
SANE_MIN, SANE_MAX = 30_000, 150_000

# VG30 (60/70) locations -> price_master keys. A circular location may map to
# more than one key (e.g. Mumbai has two refineries).
_VG30_LOCATION_KEYS: dict[str, list[str]] = {
    "koyali":        ["IOCL_KOYALI_VG30"],
    "baroda":        ["IOCL_KOYALI_VG30"],
    "mathura":       ["IOCL_MATHURA_VG30"],
    "haldia":        ["IOCL_HALDIA_VG30", "BULK_HALDIA_IMPORT"],
    "barauni":       ["IOCL_BARAUNI_VG30"],
    "panipat":       ["IOCL_PANIPAT_VG30"],
    "mumbai":        ["BPCL_MUMBAI_VG30", "HPCL_MUMBAI_VG30"],
    "jnpt":          ["BULK_JNPT_IMPORT"],
    "vizag":         ["HPCL_VIZAG_VG30"],
    "visakhapatnam": ["HPCL_VIZAG_VG30"],
    "chennai":       ["CPCL_CHENNAI_VG30"],
    "mangalore":     ["MRPL_MANGALORE_VG30", "BULK_MANGALORE_IMPORT"],
    "kochi":         ["BPCL_KOCHI_VG30"],
    "coimbatore":    ["BPCL_KOCHI_VG30"],
    "mundra":        ["BULK_MUNDRA_IMPORT"],
    "kandla":        ["BULK_KANDLA_IMPORT"],
}

# VG10 (80/100) — only the two regional drum/VG10 bases exist in price_master.
_VG10_LOCATION_KEYS: dict[str, list[str]] = {
    "mumbai":  ["DRUM_MUMBAI_VG10"],
    "jnpt":    ["DRUM_MUMBAI_VG10"],
    "koyali":  ["DRUM_KANDLA_VG10"],
    "baroda":  ["DRUM_KANDLA_VG10"],
    "kandla":  ["DRUM_KANDLA_VG10"],
}

# Mumbai/JNPT VG30 is the headline reference (price_master.VG30_BASE).
_BASE_TOKENS = ("mumbai", "jnpt")


def normalize_grade(text: str | None) -> str | None:
    """Map a grade label to 'VG30' / 'VG10', or None if unrecognized.

    Handles the circular's penetration labels (60/70 -> VG30, 80/100 -> VG10)
    and direct viscosity labels ('VG30', 'VG 10')."""
    if not text:
        return None
    t = str(text).upper().replace(" ", "")
    if "VG30" in t or "60/70" in t:
        return "VG30"
    if "VG10" in t or "80/100" in t:
        return "VG10"
    return None


def is_sane_price(price) -> bool:
    """True only for a plausible bitumen ₹/MT value (rejects OCR misreads)."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return False
    return SANE_MIN <= p <= SANE_MAX


def _location_keys_for(grade: str) -> dict[str, list[str]]:
    return _VG10_LOCATION_KEYS if grade == "VG10" else _VG30_LOCATION_KEYS


def match_keys(location: str | None, grade: str) -> list[str]:
    """price_master override keys for a circular location + grade (may be many)."""
    if not location:
        return []
    loc = str(location).lower()
    table = _location_keys_for(grade)
    keys: list[str] = []
    for alias, alias_keys in table.items():
        if alias in loc:
            keys.extend(alias_keys)
    return list(dict.fromkeys(keys))  # de-dup, preserve order


def _is_base_location(location: str) -> bool:
    loc = str(location or "").lower()
    return any(tok in loc for tok in _BASE_TOKENS)


def build_updates(rows: list[dict]) -> dict:
    """Turn extracted rows into a review-ready update set.

    Each row: {"location": str, "grade": str, "price": number}.
    Returns:
      updates    {override_key: price}  — sane, matched rows only
      vg30_base  int|None               — new headline base (Mumbai/JNPT VG30)
      unmatched  [...]                   — bad/unknown grade or location
      rejected   [...]                   — price outside the sanity band
    """
    updates: dict[str, int] = {}
    unmatched: list[dict] = []
    rejected: list[dict] = []
    vg30_base = None

    for r in rows or []:
        grade = normalize_grade(r.get("grade"))
        location = r.get("location") or ""
        price = r.get("price")
        if grade is None:
            unmatched.append({"row": r, "reason": "unknown grade"})
            continue
        keys = match_keys(location, grade)
        if not keys:
            unmatched.append({"row": r, "reason": "unknown location"})
            continue
        if not is_sane_price(price):
            rejected.append({"row": r, "reason": "price outside sanity band"})
            continue
        ip = int(float(price))
        for k in keys:
            updates[k] = ip
        if grade == "VG30" and _is_base_location(location):
            vg30_base = ip

    return {"updates": updates, "vg30_base": vg30_base,
            "unmatched": unmatched, "rejected": rejected}
