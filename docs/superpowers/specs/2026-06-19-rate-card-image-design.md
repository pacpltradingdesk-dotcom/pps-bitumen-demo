# PPS Bitumen Rate-Card Image — Design

**Date:** 2026-06-19
**Goal:** Generate a branded, shareable PNG image of PPS Anantam's current bitumen
rates (Bulk + Drum) with a market-direction arrow — styled like the Multi Energy
Enterprises (MEE) bulletin the user shared, but for PPS's own products.

## Why
PPS currently shares rates as plain WhatsApp text or PDF. A clean branded image
is far more shareable on WhatsApp/groups and looks professional. The MEE bulletin
is the visual reference.

## Data — single source of truth (no stale literals)
`get_card_rates()` returns an ordered list of rows:
`{grade, bulk, drum, direction}` where:
- **VG-30 Bulk** = `market_data.get_unified_prices()['vg30']` (live), fallback
  `price_master.VG30_BASE` (76870).
- Other grades derive from VG-30 via a NEW documented map in `price_master.py`:
  `GRADE_DIFFERENTIALS` (Rs/MT vs VG-30, sourced from the IOCL fortnightly circular
  already encoded in `competitor_intelligence.PSU_PRICES`):
  - VG-10: −1300, VG-30: 0, VG-40: +2680, CRMB-60: +1594, PMB: +1644 (≈CRMB premium)
- **Drum** = bulk + `DRUM_PREMIUM` (1390, = existing `DRUM_KANDLA_VG30 − VG30_BASE`).
- **Emulsion**: no grounded per-MT price → shown as "On request" (never fabricated).
- **direction** (▲/▼/■): one market trend from `ml_forecast_engine.forecast_crude_price`
  direction (UP/DOWN/STABLE), applied as a market-trend indicator (honestly labelled,
  not a per-grade forecast). Degrades to ■ (neutral) if forecast unavailable.

Extending `price_master` keeps the single-source-of-truth invariant — the existing
`tests/test_price_consistency.py` continues to guard it.

## Image — `build_rate_card_image(as_of=None) -> bytes`
Pure function, **Pillow** (already available; no kaleido). Returns PNG bytes.
Layout (mirrors MEE):
- Outer bordered card, white background, navy accents (PPS theme).
- Header: `pps_logo.png` (if present) + "PPS ANANTAMS CORPORATION PVT LTD" +
  tagline + "Vadodara | <phone> | GST 24AAHCV1611L2ZD" (from `company_config`).
- Title bar: "PPS Anantam — Bitumen Rates as on DD.MM.YYYY".
- Left note "(Currency: INR ₹)", right note "(Rs./MT)".
- Inner bordered table: each row = `GRADE  <arrow>  Bulk ₹x,xx,xxx   Drum ₹x,xx,xxx`.
- Footer disclaimer: "Rates indicative; confirm before booking. Not for onward circulation."
- **Fonts:** robust cross-platform loader — try Windows (`arialbd.ttf`/`arial.ttf`)
  then Linux/Pillow bundled (`DejaVuSans-Bold.ttf`/`DejaVuSans.ttf`), fall back to
  `ImageFont.load_default()`. Indian-grouped numbers via `india_localization.format_inr`.

## UI — `render_rate_image_panel()` (Streamlit, thin)
- Build image → `st.image(preview)`.
- `st.download_button` (PNG, filename `PPS_Rates_YYYYMMDD.png`).
- "Share on WhatsApp" → `wa.me` link with a pre-filled text caption (note: user
  attaches the downloaded image — `wa.me` can't attach media via URL).
- If `whatsapp_engine` WA-Business media send is configured, offer "Send via WA Business".
- Wired into the Price Board page (`price_board.py`) as a "📸 Rate Image" expander.

## Files
- `rate_image_engine.py` — `get_card_rates()`, `build_rate_card_image()`, `render_rate_image_panel()`.
- `price_master.py` — add `GRADE_DIFFERENTIALS`, `DRUM_PREMIUM`.
- `price_board.py` — wire the expander.
- `tests/test_rate_image.py`.

## Tests (TDD)
- `get_card_rates()`: returns expected grades; VG-30 bulk == `get_unified_prices()['vg30']`;
  drum == bulk + premium; emulsion row is "On request"; direction in {▲,▼,■}.
- `build_rate_card_image()`: returns non-empty `bytes` starting with the PNG magic
  header `\x89PNG`; image opens in Pillow with sane dimensions.
- `price_master`: GRADE_DIFFERENTIALS keys present; consistency test still passes.

## Scope cuts (YAGNI)
- No multi-language, no scheduled auto-send, no per-grade independent forecast,
  no editable layout. Bitumen grades only.
