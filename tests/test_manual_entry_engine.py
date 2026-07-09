"""Manual Price Entry engine — bulk/drum routing, GST math, real entry log.

Live audit 09-07-2026 (reported by sales user):
1. Every Entry Form submit wrote a DRUM_* key even for BULK rate-card prices
   (a Gujarat bulk entry left DRUM_KANDLA_VG30 = 66,200 poisoning the sidebar).
2. The GST and Freight inputs were collected but silently ignored.
3. The "Recent Uploads" table was a hardcoded mock stamped datetime.now(),
   and real entries were never persisted anywhere.
This engine makes all three behaviours real and testable.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import manual_entry_engine as mee  # noqa: E402


# ── GST / freight math ───────────────────────────────────────────────────────

def test_basic_price_gst_inclusive_quote_is_stripped():
    # ₹91,615 delivered incl 18% GST, ₹4,000 freight → basic ex-GST ex-freight
    basic = mee.compute_basic_price(91_615, freight=4_000, gst_pct=18.0, gst_inclusive=True)
    assert basic == round(91_615 / 1.18 - 4_000)


def test_basic_price_exclusive_quote_stored_as_is_minus_freight():
    basic = mee.compute_basic_price(77_640, freight=0, gst_pct=18.0, gst_inclusive=False)
    assert basic == 77_640


def test_basic_price_rejects_nonpositive_result():
    try:
        mee.compute_basic_price(1_000, freight=5_000, gst_pct=18.0, gst_inclusive=False)
        assert False, "expected ValueError for negative basic price"
    except ValueError:
        pass


# ── override-key routing ─────────────────────────────────────────────────────

def test_drum_entries_route_to_drum_keys():
    assert mee.resolve_override_key("Mumbai", "VG30", "drum") == "DRUM_MUMBAI_VG30"
    assert mee.resolve_override_key("Gujarat", "VG10", "drum") == "DRUM_KANDLA_VG10"


def test_bulk_mumbai_vg30_routes_to_base():
    assert mee.resolve_override_key("Mumbai", "VG30", "bulk") == "VG30_BASE"


def test_bulk_port_city_routes_to_import_key():
    assert mee.resolve_override_key("Kandla", "VG30", "bulk") == "BULK_KANDLA_IMPORT"
    assert mee.resolve_override_key("Mundra", "VG30", "bulk") == "BULK_MUNDRA_IMPORT"


def test_bulk_refinery_city_routes_to_refinery_key():
    assert mee.resolve_override_key("Koyali/ Baroda", "VG30", "bulk") == "IOCL_KOYALI_VG30"
    assert mee.resolve_override_key("Panipat", "VG30", "bulk") == "IOCL_PANIPAT_VG30"


def test_bulk_unknown_city_or_grade_is_log_only():
    # No guessing: unmapped bulk entries must NOT write any live price key.
    assert mee.resolve_override_key("Jaipur", "VG30", "bulk") is None
    assert mee.resolve_override_key("Mumbai", "PMB", "bulk") is None


def test_drum_non_seeded_grades_are_log_only():
    # price_master seeds only DRUM_{MUMBAI,KANDLA}_{VG30,VG10} — a PMB/CRMB
    # drum key would be written but surface nowhere (review finding M3).
    assert mee.resolve_override_key("Mumbai", "PMB", "drum") is None
    assert mee.resolve_override_key("Gujarat", "CRMB", "drum") is None
    assert mee.resolve_override_key("Mumbai", "VG10", "drum") == "DRUM_MUMBAI_VG10"


def test_write_override_key_merges_and_persists(tmp_path):
    lp = tmp_path / "live_prices.json"
    lp.write_text('{"VG30_BASE": 77640}', encoding="utf-8")

    assert mee.write_override_key("BULK_KANDLA_IMPORT", 79000, path=lp) is True

    import json
    data = json.loads(lp.read_text(encoding="utf-8"))
    assert data == {"VG30_BASE": 77640, "BULK_KANDLA_IMPORT": 79000}


def test_write_override_key_survives_corrupt_file(tmp_path):
    lp = tmp_path / "live_prices.json"
    lp.write_text("[not, a, dict", encoding="utf-8")

    assert mee.write_override_key("VG30_BASE", 77640, path=lp) is True
    import json
    assert json.loads(lp.read_text(encoding="utf-8")) == {"VG30_BASE": 77640}


# ── real entry log ───────────────────────────────────────────────────────────

def test_entries_roundtrip_newest_first(tmp_path):
    log = tmp_path / "manual_entries.json"
    e1 = mee.build_entry(
        user="janki", location="Mumbai", grade="VG30", price_type="bulk",
        quote=77_640, freight=0, gst_pct=18.0, gst_inclusive=False,
        basic_price=77_640, applied_key="VG30_BASE", auto_price=77_640,
        target_revision="16-07-2026", remarks="rate card July",
    )
    mee.append_entry(e1, path=log)
    e2 = mee.build_entry(
        user="renuka", location="Kandla", grade="VG30", price_type="bulk",
        quote=79_000, freight=0, gst_pct=18.0, gst_inclusive=False,
        basic_price=79_000, applied_key="BULK_KANDLA_IMPORT", auto_price=79_044,
        target_revision="16-07-2026", remarks="",
    )
    mee.append_entry(e2, path=log)

    entries = mee.load_entries(path=log)
    assert len(entries) == 2
    assert entries[0]["user"] == "renuka"          # newest first
    assert entries[1]["basic_price"] == 77_640
    assert entries[0]["entry_ist"]                  # timestamp present


def test_conflict_flag_beyond_5pct():
    assert mee.is_conflict(basic=66_200, auto=77_640) is True
    assert mee.is_conflict(basic=77_800, auto=77_640) is False
    assert mee.is_conflict(basic=70_000, auto=None) is False   # nothing to compare


# ── UI drift guard ───────────────────────────────────────────────────────────

def test_manual_entry_page_has_no_fake_team_table():
    src = (Path(__file__).parent.parent / "command_intel" / "manual_entry.py").read_text(
        encoding="utf-8"
    )
    assert "Salesman A" not in src
    assert "Manager B" not in src
