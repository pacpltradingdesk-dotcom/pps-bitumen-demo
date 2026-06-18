"""Tests for circular_parser — maps rows extracted from the Multi Energy
fortnightly circular into price_master override keys, with grade normalization
and a sanity band so a misread number can never reach the live board.
"""
from __future__ import annotations

import price_master
import circular_parser as cp


# ── grade normalization (the circular prints "60/70-VG30" / "80/100-VG10") ──

def test_normalize_grade_pen_to_viscosity():
    assert cp.normalize_grade("60/70-VG30") == "VG30"
    assert cp.normalize_grade("80/100-VG10") == "VG10"
    assert cp.normalize_grade("60/70") == "VG30"
    assert cp.normalize_grade("80/100") == "VG10"


def test_normalize_grade_direct():
    assert cp.normalize_grade("VG30") == "VG30"
    assert cp.normalize_grade("vg 10") == "VG10"


def test_normalize_grade_unknown():
    assert cp.normalize_grade("PMB") is None
    assert cp.normalize_grade("") is None
    assert cp.normalize_grade(None) is None


# ── sanity band — bitumen is ~₹70k-85k; reject obvious misreads ──

def test_is_sane_price():
    assert cp.is_sane_price(78260) is True
    assert cp.is_sane_price(76870) is True
    assert cp.is_sane_price(500) is False        # OCR dropped digits
    assert cp.is_sane_price(999999) is False     # OCR added digits
    assert cp.is_sane_price(None) is False
    assert cp.is_sane_price("abc") is False


# ── location -> price_master key(s) ──

def test_match_keys_refinery():
    assert "IOCL_KOYALI_VG30" in cp.match_keys("Koyali/Baroda", "VG30")
    assert "IOCL_MATHURA_VG30" in cp.match_keys("Mathura", "VG30")
    assert "MRPL_MANGALORE_VG30" in cp.match_keys("Mangalore", "VG30")


def test_match_keys_mumbai_maps_refineries():
    keys = cp.match_keys("Mumbai/JNPT", "VG30")
    assert "BPCL_MUMBAI_VG30" in keys and "HPCL_MUMBAI_VG30" in keys


def test_match_keys_vg10_uses_drum_keys():
    assert "DRUM_MUMBAI_VG10" in cp.match_keys("Mumbai/JNPT", "VG10")
    assert "DRUM_KANDLA_VG10" in cp.match_keys("Koyali/Baroda", "VG10")


def test_match_keys_unknown_location():
    assert cp.match_keys("Nowhereville", "VG30") == []


def test_all_mapped_keys_exist_in_price_master():
    """Drift guard: every key the parser can produce must be a real
    price_master key (else we'd write a key nothing reads)."""
    valid = {r.key for r in price_master.ALL_RECS} | set(price_master.DRUM_PRICES) | {"VG30_BASE"}
    for grade in ("VG30", "VG10"):
        for keys in cp._location_keys_for(grade).values():
            for k in keys:
                assert k in valid, f"{k} not in price_master"


# ── build_updates: the full pipeline ──

def test_build_updates_happy_path():
    rows = [
        {"location": "Koyali/Baroda", "grade": "60/70-VG30", "price": 78500},
        {"location": "Mathura",       "grade": "60/70-VG30", "price": 76000},
        {"location": "Mumbai/JNPT",   "grade": "60/70-VG30", "price": 77000},
    ]
    out = cp.build_updates(rows)
    assert out["updates"]["IOCL_KOYALI_VG30"] == 78500
    assert out["updates"]["IOCL_MATHURA_VG30"] == 76000
    assert out["updates"]["BPCL_MUMBAI_VG30"] == 77000
    # Mumbai/JNPT VG30 is the headline reference.
    assert out["vg30_base"] == 77000
    assert out["unmatched"] == [] and out["rejected"] == []


def test_build_updates_flags_unmatched_location():
    out = cp.build_updates([{"location": "Atlantis", "grade": "VG30", "price": 78000}])
    assert out["updates"] == {}
    assert out["unmatched"] and "Atlantis" in str(out["unmatched"])


def test_build_updates_rejects_insane_price():
    out = cp.build_updates([{"location": "Mathura", "grade": "VG30", "price": 7}])
    assert "IOCL_MATHURA_VG30" not in out["updates"]
    assert out["rejected"] and "Mathura" in str(out["rejected"])


def test_build_updates_skips_unknown_grade():
    out = cp.build_updates([{"location": "Mathura", "grade": "PMB", "price": 90000}])
    assert out["updates"] == {}
    assert out["unmatched"]
