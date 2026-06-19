"""Tests for the PPS bitumen rate-card image feature."""

import io

import price_master
import rate_image_engine as rie
from market_data import get_unified_prices


# ── Data layer ────────────────────────────────────────────────────────────
def test_price_master_has_grade_differentials():
    d = price_master.GRADE_DIFFERENTIALS
    for g in ("VG-10", "VG-30", "VG-40", "CRMB-60", "PMB"):
        assert g in d
    assert d["VG-30"] == 0
    assert isinstance(price_master.DRUM_PREMIUM, int)


def test_get_card_rates_structure_and_grades():
    rows = rie.get_card_rates()
    grades = [r["grade"] for r in rows]
    for g in ("VG-30", "VG-10", "VG-40", "CRMB-60", "PMB", "Emulsion"):
        assert g in grades
    for r in rows:
        assert r["direction"] in ("▲", "▼", "■")


def test_vg30_bulk_tracks_live_unified_price():
    rows = {r["grade"]: r for r in rie.get_card_rates()}
    live = int(float(get_unified_prices().get("vg30") or 0))
    assert rows["VG-30"]["bulk"] == live


def test_drum_is_bulk_plus_premium_for_priced_grades():
    rows = {r["grade"]: r for r in rie.get_card_rates()}
    vg30 = rows["VG-30"]
    assert vg30["drum"] == vg30["bulk"] + price_master.DRUM_PREMIUM


def test_emulsion_is_on_request_not_fabricated():
    rows = {r["grade"]: r for r in rie.get_card_rates()}
    em = rows["Emulsion"]
    assert em.get("on_request") is True
    assert em["bulk"] is None


# ── Image layer ───────────────────────────────────────────────────────────
def test_build_rate_card_image_returns_png_bytes():
    data = rie.build_rate_card_image()
    assert isinstance(data, (bytes, bytearray))
    assert data[:4] == b"\x89PNG", "output must be a real PNG"


def test_image_opens_with_sane_dimensions():
    from PIL import Image
    img = Image.open(io.BytesIO(rie.build_rate_card_image()))
    assert img.format == "PNG"
    assert img.width >= 500 and img.height >= 400
