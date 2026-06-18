"""
PPS Anantam — bounded intra-fortnight VG30 drift (pure, no I/O).

The fortnightly Multi Energy circular is the authoritative VG30 base. Between
circulars the published number would otherwise sit frozen for ~15 days. This
nudges it with crude + FX moves since the circular ('anchor'), so the board
feels live — but capped to ±MAX_DRIFT_PCT so the estimate can never run away
from the published anchor.

Sensitivities mirror the price-prediction model (industry rules of thumb):
  ~₹450/MT per $1 Brent, ~₹120/MT per ₹1 USD/INR.
"""
from __future__ import annotations

BRENT_SENS = 450.0     # ₹/MT per $1/bbl Brent
FX_SENS = 120.0        # ₹/MT per ₹1 USD/INR
MAX_DRIFT_PCT = 0.05   # never drift more than ±5% from the published anchor


def drift_vg30(anchor_base, anchor_brent, anchor_usdinr, cur_brent, cur_usdinr,
               brent_sens: float = BRENT_SENS, fx_sens: float = FX_SENS,
               max_pct: float = MAX_DRIFT_PCT) -> int:
    """Estimate today's VG30 base by nudging the anchor with crude/FX moves.

    Returns the (rounded, int) drifted base. Degrades to the anchor base when
    any reference is missing or invalid — never raises.
    """
    try:
        ab = float(anchor_base)
    except (TypeError, ValueError):
        return 0
    if ab <= 0:
        return int(ab)

    if any(v is None for v in (anchor_brent, anchor_usdinr, cur_brent, cur_usdinr)):
        return int(round(ab))
    try:
        delta = ((float(cur_brent) - float(anchor_brent)) * brent_sens
                 + (float(cur_usdinr) - float(anchor_usdinr)) * fx_sens)
    except (TypeError, ValueError):
        return int(round(ab))

    cap = ab * max_pct
    delta = max(-cap, min(cap, delta))
    return int(round(ab + delta))
