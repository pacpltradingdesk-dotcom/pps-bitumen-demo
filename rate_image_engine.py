"""
PPS Bitumen Rate-Card Image
===========================
Generates a branded, shareable PNG of PPS Anantam's current bitumen rates
(Bulk + Drum) with a market-direction arrow — styled like the Multi Energy
Enterprises bulletin, but for PPS's own products.

Data comes from the single source of truth (market_data.get_unified_prices /
price_master) — no hardcoded/stale prices. Rendering is pure Pillow (no kaleido).

Public API:
  get_card_rates()                 -> list[dict]  (data, testable)
  build_rate_card_image(as_of)     -> bytes        (PNG, testable)
  render_rate_image_panel()        -> None         (Streamlit UI, thin)
"""

from __future__ import annotations

import io
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "pps_logo.png"

# Order shown on the card.
GRADE_ORDER = ["VG-30", "VG-10", "VG-40", "CRMB-60", "PMB", "Emulsion"]

# Palette (PPS navy/blue theme).
NAVY   = (15, 23, 42)
BLUE   = (37, 99, 235)
SLATE  = (51, 65, 85)
MUTED  = (100, 116, 139)
GREEN  = (5, 150, 105)
RED    = (220, 38, 38)
BORDER = (203, 213, 225)
WHITE  = (255, 255, 255)
TITLEBG = (239, 246, 255)

ARROW_COLOR = {"▲": GREEN, "▼": RED, "■": MUTED}


# ── Data ──────────────────────────────────────────────────────────────────
def _live_vg30() -> int:
    import price_master
    try:
        from market_data import get_unified_prices
        return int(float(get_unified_prices().get("vg30") or 0)) or price_master.VG30_BASE
    except Exception:
        return price_master.VG30_BASE


def _market_direction() -> str:
    """One market-trend arrow (▲/▼/■) from the crude forecast direction.
    Honestly a market-trend indicator, not a per-grade forecast."""
    try:
        from ml_forecast_engine import forecast_crude_price
        d = str((forecast_crude_price(15) or {}).get("direction", "")).upper()
        if d in ("UP", "RISING", "BULLISH"):
            return "▲"
        if d in ("DOWN", "FALLING", "BEARISH"):
            return "▼"
    except Exception:
        pass
    return "■"


def get_card_rates() -> list[dict]:
    """Ordered rate rows: {grade, bulk, drum, direction, on_request}."""
    import price_master
    vg30 = _live_vg30()
    arrow = _market_direction()
    rows: list[dict] = []
    for g in GRADE_ORDER:
        if g == "Emulsion":
            # No grounded per-MT price — never fabricate a number.
            rows.append({"grade": g, "bulk": None, "drum": None,
                         "direction": arrow, "on_request": True})
            continue
        bulk = vg30 + price_master.GRADE_DIFFERENTIALS.get(g, 0)
        rows.append({"grade": g, "bulk": bulk, "drum": bulk + price_master.DRUM_PREMIUM,
                     "direction": arrow, "on_request": False})
    return rows


# ── Rendering ───────────────────────────────────────────────────────────────
def _font(size: int, bold: bool = False):
    from PIL import ImageFont
    names = (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["arial.ttf", "DejaVuSans.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)
    except Exception:
        return ImageFont.load_default()


def _company() -> dict:
    """Return the company-profile dict regardless of its variable name."""
    try:
        import company_config as cc
        for v in vars(cc).values():
            if isinstance(v, dict) and "legal_name" in v:
                return v
    except Exception:
        pass
    return {}


def _fmt(v) -> str:
    try:
        from india_localization import format_inr
        return format_inr(v)
    except Exception:
        return f"₹{int(v):,}"


def _center(draw, cx, y, text, font, fill):
    w = draw.textlength(text, font=font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def build_rate_card_image(as_of: datetime.date | None = None) -> bytes:
    """Render the rate card to PNG bytes."""
    from PIL import Image, ImageDraw

    co = _company()
    rows = get_card_rates()
    as_of = as_of or datetime.date.today()

    W = 680
    pad = 20
    row_h = 38
    header_h = 250
    table_top = header_h + 60
    H = table_top + (len(rows) + 1) * row_h + 70

    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    f_co    = _font(30, bold=True)
    f_tag   = _font(14)
    f_small = _font(12)
    f_title = _font(20, bold=True)
    f_note  = _font(13)
    f_grade = _font(20, bold=True)
    f_price = _font(19, bold=True)
    f_foot  = _font(12, bold=True)

    # Outer + inner borders (MEE-style double frame).
    d.rectangle([4, 4, W - 5, H - 5], outline=NAVY, width=3)
    d.rectangle([10, 10, W - 11, H - 11], outline=BORDER, width=1)

    cx = W // 2
    y = 22

    # Logo (centered).
    try:
        if LOGO_PATH.exists():
            logo = Image.open(LOGO_PATH).convert("RGBA")
            lw = 70
            lh = int(logo.height * lw / logo.width)
            logo = logo.resize((lw, lh))
            img.paste(logo, (cx - lw // 2, y), logo)
            y += lh + 6
    except Exception:
        pass

    _center(d, cx, y, co.get("short_name", "PPS Anantams").upper() + " CORPORATION", f_co, NAVY)
    y += 40
    _center(d, cx, y, "Bitumen Trading  *  Pan-India Supply to Contractors & PWDs", f_tag, BLUE)
    y += 22
    contact = f"{co.get('city', 'Vadodara')}  |  {co.get('owner_mobile', '')}  |  GST {co.get('gst_no', '')}"
    _center(d, cx, y, contact, f_small, SLATE)
    y += 24
    d.line([20, y, W - 20, y], fill=NAVY, width=2)

    # Title bar.
    ty = table_top - 52
    d.rectangle([16, ty, W - 17, ty + 34], fill=TITLEBG)
    _center(d, cx, ty + 7, f"PPS Anantam — Bitumen Rates as on {as_of.strftime('%d.%m.%Y')}",
            f_title, NAVY)

    # Currency notes.
    ny = ty + 40
    d.text((28, ny), "(Currency: INR ₹)", font=f_note, fill=MUTED)
    rt = "(Rs./MT)"
    d.text((W - 28 - d.textlength(rt, font=f_note), ny), rt, font=f_note, fill=MUTED)

    # Table frame.
    tx0, tx1 = 28, W - 28
    ty0 = table_top
    ty1 = ty0 + (len(rows) + 1) * row_h
    d.rectangle([tx0, ty0, tx1, ty1], outline=NAVY, width=2)

    # Both price columns are RIGHT-aligned at fixed edges with a clear gap so
    # the bulk and drum numbers never collide.
    bulk_right = tx1 - 150
    drum_right = tx1 - 16

    # Column header (right-aligned to match the values below).
    hy = ty0 + 9
    d.text((tx0 + 14, hy), "GRADE", font=f_small, fill=MUTED)
    d.text((bulk_right - d.textlength("BULK", font=f_small), hy), "BULK", font=f_small, fill=MUTED)
    d.text((drum_right - d.textlength("DRUM", font=f_small), hy), "DRUM", font=f_small, fill=MUTED)
    d.line([tx0, ty0 + row_h, tx1, ty0 + row_h], fill=BORDER, width=1)

    for i, r in enumerate(rows):
        ry = ty0 + (i + 1) * row_h + 8
        arrow = r["direction"]
        d.text((tx0 + 14, ry), r["grade"], font=f_grade, fill=NAVY)
        d.text((tx0 + 160, ry), arrow, font=f_grade, fill=ARROW_COLOR.get(arrow, MUTED))
        if r.get("on_request"):
            d.text((bulk_right - d.textlength("On request", font=f_note), ry),
                   "On request", font=f_note, fill=MUTED)
        else:
            bt = _fmt(r["bulk"])
            d.text((bulk_right - d.textlength(bt, font=f_price), ry), bt, font=f_price, fill=SLATE)
            dt = _fmt(r["drum"])
            d.text((drum_right - d.textlength(dt, font=f_price), ry), dt, font=f_price, fill=SLATE)
        if i < len(rows) - 1:
            d.line([tx0, ty0 + (i + 2) * row_h, tx1, ty0 + (i + 2) * row_h], fill=BORDER, width=1)

    # Footer disclaimer.
    fy = ty1 + 18
    _center(d, cx, fy,
            "Rates indicative; confirm before booking. Please do not circulate onward.",
            f_foot, RED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Streamlit UI (thin) ─────────────────────────────────────────────────────
def render_rate_image_panel():
    import streamlit as st
    import urllib.parse

    st.markdown("#### 📸 Rate Card Image")
    st.caption("Branded image of today's PPS bitumen rates — download or share on WhatsApp.")

    try:
        png = build_rate_card_image()
    except Exception as e:
        st.error(f"Could not build rate image: {e}")
        return

    st.image(png, caption="PPS Bitumen Rate Card", use_container_width=True)

    today = datetime.date.today().strftime("%Y%m%d")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 Download PNG", data=png,
                           file_name=f"PPS_Rates_{today}.png", mime="image/png",
                           use_container_width=True)
    with c2:
        rows = get_card_rates()
        lines = [f"*PPS Anantam — Bitumen Rates {datetime.date.today():%d-%m-%Y}* (Rs./MT)"]
        for r in rows:
            if r.get("on_request"):
                lines.append(f"{r['grade']}: On request")
            else:
                lines.append(f"{r['grade']} {r['direction']}  Bulk {_fmt(r['bulk'])} | Drum {_fmt(r['drum'])}")
        caption = "\n".join(lines) + "\n\n(Rate card image attached)"
        wa = "https://wa.me/?text=" + urllib.parse.quote(caption)
        st.link_button("🟢 Share on WhatsApp", wa, use_container_width=True)
        st.caption("Tip: attach the downloaded PNG in WhatsApp — wa.me can't attach images via link.")
