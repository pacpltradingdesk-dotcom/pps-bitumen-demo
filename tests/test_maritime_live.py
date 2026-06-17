from __future__ import annotations
import maritime_intelligence_engine as mie


def test_haversine_known_distance():
    # Mundra (22.84, 69.73) -> Kandla (23.03, 70.22): ~30 nm.
    d = mie._haversine_nm(22.84, 69.73, 23.03, 70.22)
    assert 20 < d < 45


def test_nearest_indian_port_picks_mundra():
    # A point just off Mundra should resolve to Mundra.
    assert mie._nearest_indian_port(22.80, 69.70) == "Mundra"


def test_match_destination_port_text():
    assert mie._match_destination_port("MUNDRA") == "Mundra"
    assert mie._match_destination_port("INMUN VIA XYZ") in ("Mundra", None)
    assert mie._match_destination_port("ROTTERDAM") is None
    assert mie._match_destination_port("") is None


from datetime import datetime, timedelta, timezone


def test_is_fresh_true_and_false():
    now = datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
    assert mie._is_fresh("2026-06-17T09:50:00Z", 20, now=now) is True   # 10 min old
    assert mie._is_fresh("2026-06-17T09:30:00Z", 20, now=now) is False  # 30 min old
    assert mie._is_fresh(None, 20, now=now) is False


def test_map_ais_to_vessel_shape():
    raw = {"mmsi": 477123456, "name": "GULF PRIDE", "imo": 9876543,
           "lat": 22.80, "lon": 69.70, "sog": 11.8, "heading": 98,
           "ship_type": 80, "destination": "MUNDRA"}
    v = mie._map_ais_to_vessel(raw)
    assert v["vessel_name"] == "GULF PRIDE"
    assert v["imo"] == "IMO9876543"
    assert v["cargo_type"] == "bulk"
    assert v["destination_port"] == "Mundra"
    assert v["speed_knots"] == 11.8
    assert v["is_simulated"] is False and v["source"] == "AIS"
    assert v["cargo_mt"] is None and v["product_grade"] is None
    # Required keys present for the UI template.
    for k in ("departure_port", "progress_pct", "status", "eta", "eta_hours",
              "delay_factor", "lat", "lon"):
        assert k in v


def test_map_ais_to_vessel_handles_missing_name_and_imo():
    raw = {"mmsi": 12345, "lat": 22.0, "lon": 69.0, "ship_type": 80}
    v = mie._map_ais_to_vessel(raw)
    assert v["vessel_name"] == "MMSI 12345"
    assert v["imo"] == "—"
    assert v["speed_knots"] == 0.0


import json
from pathlib import Path


def _write_snapshot(path: Path, updated_iso: str, vessels: list) -> None:
    path.write_text(json.dumps({"updated_utc": updated_iso, "source": "aisstream",
                                "vessels": vessels}), encoding="utf-8")


def test_get_live_vessels_returns_live_when_fresh(tmp_path: Path):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = tmp_path / "live.json"
    _write_snapshot(snap, now_iso, [
        {"mmsi": 1, "name": "TANKER ONE", "imo": 9000001, "lat": 22.8, "lon": 69.7,
         "sog": 10.0, "heading": 90, "ship_type": 80, "destination": "MUNDRA"},
    ])
    vessels = mie.get_live_vessels(path=snap)
    assert len(vessels) == 1
    assert vessels[0]["source"] == "AIS"
    assert vessels[0]["is_simulated"] is False


def test_get_live_vessels_falls_back_when_stale(tmp_path: Path):
    snap = tmp_path / "live.json"
    _write_snapshot(snap, "2020-01-01T00:00:00Z", [
        {"mmsi": 1, "lat": 22.8, "lon": 69.7, "ship_type": 80}])
    vessels = mie.get_live_vessels(path=snap)
    assert all(v.get("is_simulated") for v in vessels)   # simulated fallback


def test_get_live_vessels_falls_back_when_missing(tmp_path: Path):
    vessels = mie.get_live_vessels(path=tmp_path / "nope.json")
    assert all(v.get("is_simulated") for v in vessels)


def test_get_live_vessels_caps_count(tmp_path: Path):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = tmp_path / "live.json"
    many = [{"mmsi": i, "name": f"T{i}", "imo": 9000000 + i, "lat": 22.0 + i * 0.01,
             "lon": 69.0, "sog": 10.0, "ship_type": 80} for i in range(100)]
    _write_snapshot(snap, now_iso, many)
    vessels = mie.get_live_vessels(path=snap)
    assert len(vessels) == mie.MARITIME_LIVE_MAX_VESSELS


def test_refresh_uses_live_when_snapshot_fresh(tmp_path: Path, monkeypatch):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = tmp_path / "live.json"
    _write_snapshot(snap, now_iso, [
        {"mmsi": 1, "name": "REAL TANKER", "imo": 9000001, "lat": 22.8, "lon": 69.7,
         "sog": 10.0, "heading": 90, "ship_type": 80, "destination": "MUNDRA"}])
    # Point the engine at our temp snapshot and a temp output dir.
    monkeypatch.setattr(mie, "TBL_LIVE_VESSELS", snap)
    monkeypatch.setattr(mie, "TBL_MARITIME_INTEL", tmp_path / "intel.json")
    monkeypatch.setattr(mie, "TBL_MARITIME_ROUTES", tmp_path / "routes.json")

    intel = mie.refresh_maritime_intel()
    assert intel["summary"]["vessel_data_simulated"] is False
    assert any(v["vessel_name"] == "REAL TANKER" for v in intel["vessels"])


def test_refresh_marks_simulated_when_no_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mie, "TBL_LIVE_VESSELS", tmp_path / "missing.json")
    monkeypatch.setattr(mie, "TBL_MARITIME_INTEL", tmp_path / "intel.json")
    monkeypatch.setattr(mie, "TBL_MARITIME_ROUTES", tmp_path / "routes.json")
    intel = mie.refresh_maritime_intel()
    assert intel["summary"]["vessel_data_simulated"] is True
