"""
PPS Anantam — SINGLE SOURCE OF TRUTH for Indian bitumen prices (Rs/MT).

VG30 == 60/70 penetration grade, VG10 == 80/100 (IS 73:2013).
Source: All India Petroleum Products Price Revision (Multi Energy circular).

Every consumer derives its view from here:
  • calculation_engine + feasibility_engine  -> default_prices()  (by location name)
  • price_board (ticker)                      -> board_items(kind) (by override key)
  • market_data.get_unified_prices()          -> VG30_BASE

EDIT PRICES ONLY IN THIS FILE. The consistency test (tests/test_price_consistency.py)
fails if any consumer ever diverges, so duplicate price maps can no longer drift.
"""
from __future__ import annotations

from typing import NamedTuple

# Ex-Mumbai bulk VG30 (60/70) — the reference every display scales from.
VG30_BASE = 76870


class PriceRec(NamedTuple):
    name: str        # calculation/feasibility source name (e.g. "IOCL Koyali")
    grade: str       # "VG30" / "VG10"
    key: str         # live_prices.json override key (e.g. "IOCL_KOYALI_VG30")
    price: int       # Rs/MT (true at VG30_BASE)
    kind: str        # "refinery" | "import"
    on_ticker: bool  # show in the Command Center / Global Market price ticker


# PSU refinery VG30 (60/70) bulk ex-refinery prices.
REFINERIES: list[PriceRec] = [
    PriceRec("IOCL Koyali",        "VG30", "IOCL_KOYALI_VG30",     78260, "refinery", True),
    PriceRec("IOCL Mathura",       "VG30", "IOCL_MATHURA_VG30",    76382, "refinery", True),
    PriceRec("IOCL Haldia",        "VG30", "IOCL_HALDIA_VG30",     77382, "refinery", True),
    PriceRec("IOCL Barauni",       "VG30", "IOCL_BARAUNI_VG30",    78412, "refinery", True),
    PriceRec("IOCL Panipat",       "VG30", "IOCL_PANIPAT_VG30",    76382, "refinery", True),
    PriceRec("IOCL Digboi",        "VG30", "IOCL_DIGBOI_VG30",     77090, "refinery", False),  # ~Guwahati
    PriceRec("IOCL Guwahati",      "VG30", "IOCL_GUWAHATI_VG30",   77090, "refinery", False),
    PriceRec("IOCL Bongaigaon",    "VG30", "IOCL_BONGAIGAON_VG30", 77090, "refinery", False),  # ~Guwahati
    PriceRec("BPCL Mumbai",        "VG30", "BPCL_MUMBAI_VG30",     76870, "refinery", True),
    PriceRec("BPCL Kochi",         "VG30", "BPCL_KOCHI_VG30",      76870, "refinery", True),   # Coimbatore/Kochi
    PriceRec("HPCL Mumbai",        "VG30", "HPCL_MUMBAI_VG30",     76870, "refinery", True),
    PriceRec("HPCL Visakhapatnam", "VG30", "HPCL_VIZAG_VG30",      77670, "refinery", True),
    PriceRec("CPCL Chennai",       "VG30", "CPCL_CHENNAI_VG30",    74582, "refinery", True),
    PriceRec("MRPL Mangalore",     "VG30", "MRPL_MANGALORE_VG30",  78850, "refinery", True),
    PriceRec("NRL Numaligarh",     "VG30", "NRL_NUMALIGARH_VG30",  77090, "refinery", False),  # ~Guwahati
    PriceRec("ONGC Tatipaka",      "VG30", "ONGC_TATIPAKA_VG30",   77670, "refinery", False),  # ~Vizag
    PriceRec("HMEL Bhatinda",      "VG30", "HMEL_BHATINDA_VG30",   76370, "refinery", False),  # Bathinda
    PriceRec("BORL Bina",          "VG30", "BORL_BINA_VG30",       76870, "refinery", False),  # ~Indore
    PriceRec("RIL Jamnagar",       "VG30", "RIL_JAMNAGAR_VG30",    77934, "refinery", False),  # Jamnagar/Vadinar
    PriceRec("Nayara Vadinar",     "VG30", "NAYARA_VADINAR_VG30",  77934, "refinery", False),
]

# Import-terminal prices = the published Multi-Energy "Bitumen Bulk Basic Prices"
# location rate (import discount removed — team treats import == published price,
# so every screen matches the circular and there's no "wrong price" mismatch).
IMPORTS: list[PriceRec] = [
    PriceRec("Mangalore Port Import", "VG30", "BULK_MANGALORE_IMPORT", 78850, "import", True),
    PriceRec("Karwar Port Import",    "VG30", "BULK_KARWAR_IMPORT",    78230, "import", False),
    PriceRec("Digi Port Import",      "VG30", "BULK_DIGI_IMPORT",      76870, "import", False),  # Mumbai
    PriceRec("Taloja Terminal",       "VG30", "BULK_TALOJA_IMPORT",    76870, "import", False),  # Mumbai
    PriceRec("VVF Mumbai Terminal",   "VG30", "BULK_VVF_IMPORT",       76870, "import", False),  # Mumbai
    PriceRec("Kandla Port Import",    "VG30", "BULK_KANDLA_IMPORT",    78260, "import", True),
    PriceRec("Mundra Port Import",    "VG30", "BULK_MUNDRA_IMPORT",    77390, "import", True),
    PriceRec("JNPT Import Terminal",  "VG30", "BULK_JNPT_IMPORT",      76870, "import", True),   # Mumbai/JNPT
    PriceRec("Haldia Port Import",    "VG30", "BULK_HALDIA_IMPORT",    77382, "import", True),
    PriceRec("Ennore Port Import",    "VG30", "BULK_ENNORE_IMPORT",    74582, "import", False),  # Chennai
]

ALL_RECS: list[PriceRec] = REFINERIES + IMPORTS

# Regional VG30 / VG10 bulk base prices (looked up by key, not location name).
DRUM_PRICES: dict[str, int] = {
    "DRUM_MUMBAI_VG30": 76870, "DRUM_KANDLA_VG30": 78260,
    "DRUM_MUMBAI_VG10": 75910, "DRUM_KANDLA_VG10": 76960,
}

# Per-grade Rs/MT differential vs VG-30, from the IOCL fortnightly circular
# relationships already encoded in competitor_intelligence.PSU_PRICES
# (VG-10 ≈ VG-30 −1300, VG-40 ≈ +2680, CRMB-60 ≈ +1594, PMB ≈ CRMB premium).
# Lets every grade derive from VG30_BASE so displays never drift.
GRADE_DIFFERENTIALS: dict[str, int] = {
    "VG-10": -1300, "VG-30": 0, "VG-40": 2680, "CRMB-60": 1594, "PMB": 1644,
}


def get_grade_differentials() -> dict:
    """Grade premiums over VG30, with runtime overrides layered on the defaults.

    Lets the fortnightly circular (or a one-time manual edit) update the
    VG40/CRMB/PMB premiums WITHOUT a code change or redeploy. Override source:
    live_prices.json["GRADE_DIFFERENTIALS"] — a {grade_key: premium} dict written
    by the Update-from-Circular flow. Falls back to the GRADE_DIFFERENTIALS
    defaults for any grade not overridden. Set-and-forget."""
    diffs = dict(GRADE_DIFFERENTIALS)
    try:
        import json as _json
        from pathlib import Path as _Path
        _lp = _Path(__file__).parent / "live_prices.json"
        if _lp.exists():
            ov = _json.loads(_lp.read_text(encoding="utf-8")).get("GRADE_DIFFERENTIALS", {})
            if isinstance(ov, dict):
                for k, v in ov.items():
                    try:
                        diffs[str(k)] = int(float(v))
                    except (TypeError, ValueError):
                        continue
    except Exception:
        pass
    return diffs

# Drum (packed) premium over bulk = DRUM_KANDLA_VG30 (78260) − VG30_BASE (76870).
DRUM_PREMIUM: int = 1390

# Non-price operational constants used by the cost engines.
OPERATIONAL: dict[str, float] = {
    "DECANTER_CONVERSION_COST": 500,
    "BULK_RATE_PER_KM": 5.5,
    "DRUM_RATE_PER_KM": 6.0,
}


def default_prices() -> dict:
    """Full default price map for calculation_engine + feasibility_engine:
    location-name keyed prices, plus drum keys and operational constants."""
    d: dict = {rec.name: rec.price for rec in ALL_RECS}
    d.update(DRUM_PRICES)
    d.update(OPERATIONAL)
    return d


def board_items(kind: str) -> list[tuple]:
    """(name, grade, key, price) tuples for the price_board ticker, one kind
    ("refinery" or "import"), limited to rows flagged for the ticker."""
    return [(r.name, r.grade, r.key, r.price)
            for r in ALL_RECS if r.kind == kind and r.on_ticker]
