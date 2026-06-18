"""
PPS Anantam — refinery & import price board (pure, no Streamlit / no I/O).

Why this exists
---------------
The Command Center REFINERY and IMPORT tickers used to show *hardcoded* prices
that never moved and contradicted the headline VG30 base (e.g. refinery VG30 at
₹42,000 while the base read ₹50,500). This module makes every location price:

  • DERIVE from the single-source-of-truth VG30 base, scaled proportionally, so
    the whole board moves with the market and stays internally consistent; and
  • allow a MANUAL OVERRIDE (a real published rate entered via Manual Price
    Entry) to win for any one location — but only if it is sane.

A sanity guard rejects absurd overrides (a fat-fingered value far from the
derived price) and falls back to the derived value, so one bad manual entry can
never flash a wrong number on a client-facing screen.

Kept dependency-free so it is fully unit-testable (see tests/test_price_board.py).
"""
from __future__ import annotations

from typing import NamedTuple

import price_master

# Reference VG30 base at which the REF prices hold true. Every reference price is
# scaled by (current_base / REF_BASE). Sourced from the single price master.
REF_BASE = float(price_master.VG30_BASE)

# An override more than this fraction away from the derived price is treated as
# a data-entry error and ignored (the derived price is shown instead).
SANITY_TOLERANCE = 0.25


class RefineryItem(NamedTuple):
    name: str
    grade: str
    ref_price: int      # price when base == REF_BASE
    override_key: str   # key in live_prices.json that may override it


class ImportItem(NamedTuple):
    name: str
    ref_price: int
    override_key: str


# Refinery + import ticker rows, derived from the single price master so the
# ticker, the calculator and the feasibility engine can never show different
# numbers for the same location. Prices scale with the live base; a real
# published rate can be pinned per location via Manual Price Entry.
REFINERY_ITEMS: list[RefineryItem] = [
    RefineryItem(name, grade, price, key)
    for name, grade, key, price in price_master.board_items("refinery")
]

IMPORT_ITEMS: list[ImportItem] = [
    ImportItem(name, price, key)
    for name, grade, key, price in price_master.board_items("import")
]


def scale_price(ref_price: float, base_vg30: float | None,
                ref_base: float = REF_BASE) -> int:
    """Scale a reference price proportionally to the current VG30 base.

    Falls back to the reference price (no scaling) when the base is missing or
    zero, so the board never goes blank or zero.
    """
    if not base_vg30 or not ref_base:
        return int(round(ref_price))
    return int(round(ref_price * (base_vg30 / ref_base)))


def resolve_price(ref_price: float, base_vg30: float | None,
                  override: float | None, ref_base: float = REF_BASE,
                  tolerance: float = SANITY_TOLERANCE) -> int:
    """Return the manual override if present and sane, else the derived price.

    "Sane" = a positive number within ``tolerance`` of the derived price. This
    rejects fat-fingered overrides (e.g. ₹67,350 where ~₹36,500 is expected).
    """
    derived = scale_price(ref_price, base_vg30, ref_base)
    if override is None:
        return derived
    try:
        ov = float(override)
    except (TypeError, ValueError):
        return derived
    if ov <= 0:
        return derived
    if derived > 0 and abs(ov - derived) / derived > tolerance:
        return derived
    return int(round(ov))


def build_price_board(base_vg30: float | None,
                      overrides: dict | None = None) -> dict:
    """Build the refinery + import price board for the current VG30 base.

    Returns ``{"refinery": [(name, grade, price), ...],
               "imports":  [(name, price), ...]}`` with every price either
    derived from the base or a sane manual override.
    """
    overrides = overrides or {}
    refinery = [
        (it.name, it.grade,
         resolve_price(it.ref_price, base_vg30, overrides.get(it.override_key)))
        for it in REFINERY_ITEMS
    ]
    imports = [
        (it.name,
         resolve_price(it.ref_price, base_vg30, overrides.get(it.override_key)))
        for it in IMPORT_ITEMS
    ]
    return {"refinery": refinery, "imports": imports}
