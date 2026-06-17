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
    vessels = mie.get_live_vessels(path=snap, port_path=tmp_path / "noport.json")
    assert len(vessels) == 1
    assert vessels[0]["source"] == "AIS"
    assert vessels[0]["is_simulated"] is False


def test_get_live_vessels_falls_back_when_stale(tmp_path: Path):
    snap = tmp_path / "live.json"
    _write_snapshot(snap, "2020-01-01T00:00:00Z", [
        {"mmsi": 1, "lat": 22.8, "lon": 69.7, "ship_type": 80}])
    vessels = mie.get_live_vessels(path=snap, port_path=tmp_path / "noport.json")
    assert all(v.get("is_simulated") for v in vessels)   # simulated fallback


def test_get_live_vessels_falls_back_when_missing(tmp_path: Path):
    vessels = mie.get_live_vessels(path=tmp_path / "nope.json", port_path=tmp_path / "noport.json")
    assert all(v.get("is_simulated") for v in vessels)


def test_get_live_vessels_caps_count(tmp_path: Path):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = tmp_path / "live.json"
    many = [{"mmsi": i, "name": f"T{i}", "imo": 9000000 + i, "lat": 22.0 + i * 0.01,
             "lon": 69.0, "sog": 10.0, "ship_type": 80} for i in range(100)]
    _write_snapshot(snap, now_iso, many)
    vessels = mie.get_live_vessels(path=snap, port_path=tmp_path / "noport.json")
    assert len(vessels) == mie.MARITIME_LIVE_MAX_VESSELS


def test_refresh_uses_live_when_snapshot_fresh(tmp_path: Path, monkeypatch):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = tmp_path / "live.json"
    _write_snapshot(snap, now_iso, [
        {"mmsi": 1, "name": "REAL TANKER", "imo": 9000001, "lat": 22.8, "lon": 69.7,
         "sog": 10.0, "heading": 90, "ship_type": 80, "destination": "MUNDRA"}])
    # Point the engine at our temp snapshot and a temp output dir.
    monkeypatch.setattr(mie, "TBL_PORT_ARRIVALS", tmp_path / "noport.json")
    monkeypatch.setattr(mie, "TBL_LIVE_VESSELS", snap)
    monkeypatch.setattr(mie, "TBL_MARITIME_INTEL", tmp_path / "intel.json")
    monkeypatch.setattr(mie, "TBL_MARITIME_ROUTES", tmp_path / "routes.json")

    intel = mie.refresh_maritime_intel()
    assert intel["summary"]["vessel_data_simulated"] is False
    assert any(v["vessel_name"] == "REAL TANKER" for v in intel["vessels"])


def test_refresh_marks_simulated_when_no_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mie, "TBL_PORT_ARRIVALS", tmp_path / "noport.json")
    monkeypatch.setattr(mie, "TBL_LIVE_VESSELS", tmp_path / "missing.json")
    monkeypatch.setattr(mie, "TBL_MARITIME_INTEL", tmp_path / "intel.json")
    monkeypatch.setattr(mie, "TBL_MARITIME_ROUTES", tmp_path / "routes.json")
    intel = mie.refresh_maritime_intel()
    assert intel["summary"]["vessel_data_simulated"] is True


# ── Port-page arrivals as primary real source ────────────────────────────────

def test_map_port_arrival_in_port_and_expected():
    in_port = mie._map_port_arrival_to_vessel(
        {"name": "FUXING V", "mmsi": "412345678", "port": "Kandla",
         "port_lat": 23.03, "port_lon": 70.22, "eta": "2026-06-17 01:41",
         "status": "in_port", "source": "myshiptracking"})
    assert in_port["vessel_name"] == "FUXING V"
    assert in_port["imo"] == "MMSI 412345678"
    assert in_port["destination_port"] == "Kandla"
    assert in_port["status"] == "arriving"
    assert in_port["is_simulated"] is False and in_port["source"] == "PORT"

    expected = mie._map_port_arrival_to_vessel(
        {"name": "MT GULF PRIDE", "port": "Kandla", "port_lat": 23.03, "port_lon": 70.22,
         "eta": "18-06-2026", "cargo": "BITUMEN VG-30", "agent": "ABC", "status": "expected",
         "source": "deendayal"})
    assert expected["status"] == "en_route"
    assert expected["product_grade"] == "BITUMEN VG-30"   # gov cargo surfaced
    assert expected["imo"] == "—"


def test_compute_delivery_prediction_handles_none_eta():
    # Port/anchored vessels have eta_hours=None — must not crash.
    v = {"vessel_name": "PORT VESSEL", "eta": "—", "eta_hours": None, "delay_factor": 1.0}
    pred = mie.LogisticsRiskEngine.compute_delivery_prediction(v, None)
    assert pred["vessel_name"] == "PORT VESSEL"


def test_refresh_uses_port_arrivals_end_to_end(tmp_path: Path, monkeypatch):
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    port = tmp_path / "port.json"
    port.write_text(json.dumps({"updated_utc": now_iso, "source": "port-pages",
        "vessels": [{"name": "FUXING V", "port": "Kandla", "port_lat": 23.03,
                     "port_lon": 70.22, "eta": "2026-06-18 10:00", "status": "expected",
                     "source": "myshiptracking"}]}), encoding="utf-8")
    monkeypatch.setattr(mie, "TBL_PORT_ARRIVALS", port)
    monkeypatch.setattr(mie, "TBL_MARITIME_INTEL", tmp_path / "intel.json")
    monkeypatch.setattr(mie, "TBL_MARITIME_ROUTES", tmp_path / "routes.json")
    intel = mie.refresh_maritime_intel()   # must not crash on None eta_hours
    assert intel["summary"]["vessel_data_simulated"] is False
    assert any(v["vessel_name"] == "FUXING V" for v in intel["vessels"])


def test_get_live_vessels_prefers_port_arrivals(tmp_path: Path):
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    port = tmp_path / "port.json"
    port.write_text(json.dumps({"updated_utc": now_iso, "source": "port-pages",
        "vessels": [{"name": "PORT VESSEL", "port": "Kandla", "port_lat": 23.03,
                     "port_lon": 70.22, "eta": "2026-06-18 10:00", "status": "expected",
                     "source": "myshiptracking"}]}), encoding="utf-8")
    # Even with a fresh AIS snapshot present, port arrivals win.
    ais = tmp_path / "ais.json"
    ais.write_text(json.dumps({"updated_utc": now_iso, "source": "aisstream",
        "vessels": [{"mmsi": 1, "name": "AIS VESSEL", "imo": 9000001, "lat": 22.8,
                     "lon": 69.7, "sog": 10.0, "ship_type": 80, "destination": "MUNDRA"}]}),
        encoding="utf-8")
    vessels = mie.get_live_vessels(path=ais, port_path=port)
    assert len(vessels) == 1
    assert vessels[0]["vessel_name"] == "PORT VESSEL"
    assert vessels[0]["source"] == "PORT"


# ── Refinement: honest destination, status, distance gate ────────────────────

def test_destination_inferred_flag_when_ais_dest_unknown():
    # AIS destination 'SINGAPORE' does not match an Indian port -> inferred.
    near_mundra = {"mmsi": 1, "name": "X", "lat": 22.80, "lon": 69.70,
                   "sog": 9.0, "ship_type": 80, "destination": "SINGAPORE"}
    v = mie._map_ais_to_vessel(near_mundra)
    assert v["dest_inferred"] is True

    # AIS destination matching an Indian port -> NOT inferred.
    declared = {**near_mundra, "destination": "MUNDRA"}
    v2 = mie._map_ais_to_vessel(declared)
    assert v2["dest_inferred"] is False
    assert v2["destination_port"] == "Mundra"


def test_status_anchored_arriving_en_route():
    # Stopped (sog ~0) far from port -> anchored, not "delayed".
    anchored = mie._map_ais_to_vessel(
        {"mmsi": 1, "lat": 18.0, "lon": 68.0, "sog": 0.0, "ship_type": 80})
    assert anchored["status"] == "anchored"
    # Right next to Mundra -> arriving.
    arriving = mie._map_ais_to_vessel(
        {"mmsi": 2, "lat": 22.84, "lon": 69.73, "sog": 6.0, "ship_type": 80})
    assert arriving["status"] == "arriving"
    # Moving in open sea -> en_route.
    enroute = mie._map_ais_to_vessel(
        {"mmsi": 3, "lat": 18.0, "lon": 68.0, "sog": 11.0, "ship_type": 80})
    assert enroute["status"] == "en_route"


def test_eta_none_when_stopped():
    stopped = mie._map_ais_to_vessel(
        {"mmsi": 1, "lat": 18.0, "lon": 68.0, "sog": 0.0, "ship_type": 80})
    assert stopped["eta"] == "—"
    assert stopped["eta_hours"] is None


def test_nearest_port_any_includes_supply_ports():
    # A point at Jebel Ali (a supply port) resolves to Jebel Ali, ~0 nm.
    name, dist = mie._nearest_port_any(25.02, 55.06)
    assert name == "Jebel Ali" and dist < 30


def test_gulf_vessel_labelled_near_supply_port():
    # Tanker in the Persian Gulf with no Indian destination -> 'near Jebel Ali'.
    v = mie._map_ais_to_vessel(
        {"mmsi": 1, "lat": 25.0, "lon": 55.1, "sog": 8.0, "ship_type": 80})
    assert v["dest_inferred"] is True
    assert v["destination_port"] == "Jebel Ali"


def test_distance_gate_keeps_relevant_drops_far(tmp_path: Path):
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = tmp_path / "live.json"
    _write_snapshot(snap, now_iso, [
        # A: near Mundra, declared MUNDRA -> kept.
        {"mmsi": 1, "name": "NEAR INDIA", "imo": 9000001, "lat": 22.8, "lon": 69.7,
         "sog": 10.0, "ship_type": 80, "destination": "MUNDRA"},
        # B: in the Gulf near a supply port, no Indian dest -> kept (near Jebel Ali).
        {"mmsi": 2, "name": "GULF SUPPLY", "imo": 9000002, "lat": 25.0, "lon": 55.1,
         "sog": 6.0, "ship_type": 80, "destination": "FUJAIRAH"},
        # C: far in the Gulf, but DECLARES an Indian port -> kept (valuable).
        {"mmsi": 3, "name": "GULF TO INDIA", "imo": 9000003, "lat": 26.5, "lon": 56.0,
         "sog": 11.0, "ship_type": 80, "destination": "MUNDRA"},
        # D: mid-ocean, far from every port, no Indian dest -> dropped.
        {"mmsi": 4, "name": "MID OCEAN", "imo": 9000004, "lat": -25.0, "lon": 75.0,
         "sog": 5.0, "ship_type": 80, "destination": "CAPE TOWN"},
    ])
    names = {v["vessel_name"] for v in mie.get_live_vessels(path=snap, port_path=tmp_path / "noport.json")}
    assert {"NEAR INDIA", "GULF SUPPLY", "GULF TO INDIA"} <= names
    assert "MID OCEAN" not in names
