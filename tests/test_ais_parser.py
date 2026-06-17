from __future__ import annotations
import json
from pathlib import Path
import ais_parser as ap


def test_clean_ais_text_strips_at_padding():
    assert ap.clean_ais_text("MUNDRA@@@@@@@@H") == "MUNDRAH"
    assert ap.clean_ais_text("  GULF PRIDE  ") == "GULF PRIDE"
    assert ap.clean_ais_text("") == ""
    assert ap.clean_ais_text(None) == ""


def test_is_tanker_range():
    assert ap.is_tanker(80) is True
    assert ap.is_tanker(89) is True
    assert ap.is_tanker(84) is True
    assert ap.is_tanker(70) is False   # cargo ship
    assert ap.is_tanker(None) is False


_POSITION_MSG = {
    "MessageType": "PositionReport",
    "MetaData": {"MMSI": 259000420, "ShipName": "AUGUSTSON",
                 "time_utc": "2026-06-17 09:29:50.0 +0000 UTC"},
    "Message": {"PositionReport": {
        "UserID": 259000420, "Latitude": 21.43, "Longitude": 67.21,
        "Sog": 11.8, "Cog": 99.3, "TrueHeading": 98, "NavigationalStatus": 0}},
}

_STATIC_MSG = {
    "MessageType": "ShipStaticData",
    "MetaData": {"MMSI": 259000420, "ShipName": "AUGUSTSON",
                 "time_utc": "2026-06-17 09:25:00.0 +0000 UTC"},
    "Message": {"ShipStaticData": {
        "UserID": 259000420, "ImoNumber": 9876543, "Name": "GULF PRIDE@@@",
        "Type": 80, "Destination": "MUNDRA@@@@", "MaximumStaticDraught": 7.5}},
}


def test_parse_position_report():
    rec = ap.parse_message(_POSITION_MSG)
    assert rec["mmsi"] == 259000420
    assert rec["kind"] == "position"
    assert rec["lat"] == 21.43 and rec["lon"] == 67.21
    assert rec["sog"] == 11.8 and rec["cog"] == 99.3 and rec["heading"] == 98
    assert rec["nav_status"] == 0


def test_parse_position_sentinels_become_none():
    msg = {"MessageType": "PositionReport",
           "MetaData": {"MMSI": 1, "time_utc": "x"},
           "Message": {"PositionReport": {
               "UserID": 1, "Latitude": 5.0, "Longitude": 6.0,
               "Sog": 1023, "Cog": 360, "TrueHeading": 511, "NavigationalStatus": 15}}}
    rec = ap.parse_message(msg)
    assert rec["sog"] is None and rec["cog"] is None and rec["heading"] is None


def test_parse_ship_static_data():
    rec = ap.parse_message(_STATIC_MSG)
    assert rec["mmsi"] == 259000420
    assert rec["kind"] == "static"
    assert rec["name"] == "GULF PRIDE"        # @ stripped
    assert rec["imo"] == 9876543
    assert rec["ship_type"] == 80
    assert rec["destination"] == "MUNDRA"     # @ stripped


def test_parse_unknown_type_returns_none():
    assert ap.parse_message({"MessageType": "BaseStationReport",
                             "MetaData": {}, "Message": {}}) is None


def test_parse_missing_mmsi_returns_none():
    assert ap.parse_message({"MessageType": "PositionReport",
                             "MetaData": {}, "Message": {"PositionReport": {}}}) is None


def test_update_registry_merges_position_then_static():
    reg: dict = {}
    ap.update_registry(reg, ap.parse_message(_POSITION_MSG), "2026-06-17T09:29:50Z")
    ap.update_registry(reg, ap.parse_message(_STATIC_MSG), "2026-06-17T09:30:00Z")
    v = reg[259000420]
    assert v["lat"] == 21.43 and v["sog"] == 11.8        # from position
    assert v["name"] == "GULF PRIDE" and v["ship_type"] == 80  # from static
    assert v["last_seen"] == "2026-06-17T09:30:00Z"      # latest wins


def test_update_registry_skips_none_position_fields():
    reg: dict = {}
    ap.update_registry(reg, ap.parse_message(_POSITION_MSG), "t1")
    # A later position with sentinel SOG must not overwrite the good 11.8.
    sentinel = {"MessageType": "PositionReport", "MetaData": {"MMSI": 259000420, "time_utc": "x"},
                "Message": {"PositionReport": {"UserID": 259000420, "Latitude": 21.5,
                            "Longitude": 67.3, "Sog": 1023, "Cog": 360, "TrueHeading": 511}}}
    ap.update_registry(reg, ap.parse_message(sentinel), "t2")
    assert reg[259000420]["sog"] == 11.8     # preserved
    assert reg[259000420]["lat"] == 21.5     # position still updated


def test_prune_registry_drops_stale():
    now = ap._parse_iso("2026-06-17T10:00:00Z")
    reg = {1: {"mmsi": 1, "last_seen": "2026-06-17T09:58:00Z"},   # 2 min old
           2: {"mmsi": 2, "last_seen": "2026-06-17T08:00:00Z"}}   # 2 h old
    ap.prune_registry(reg, now, max_age_min=60)
    assert 1 in reg and 2 not in reg


def test_build_snapshot_only_tankers_with_position():
    reg = {
        1: {"mmsi": 1, "lat": 21.0, "lon": 67.0, "ship_type": 80, "name": "T1"},   # tanker w/ pos
        2: {"mmsi": 2, "lat": 22.0, "lon": 68.0, "ship_type": 70, "name": "C1"},   # cargo (excluded)
        3: {"mmsi": 3, "ship_type": 80, "name": "T2"},                              # tanker, no pos (excluded)
    }
    snap = ap.build_snapshot(reg, "2026-06-17T10:00:00Z")
    mmsis = {v["mmsi"] for v in snap["vessels"]}
    assert mmsis == {1}
    assert snap["source"] == "aisstream"
    assert snap["updated_utc"] == "2026-06-17T10:00:00Z"


def test_atomic_write_json_roundtrip(tmp_path: Path):
    target = tmp_path / "snap.json"
    data = {"updated_utc": "t", "vessels": [{"mmsi": 1}]}
    ap.atomic_write_json(target, data)
    assert json.loads(target.read_text(encoding="utf-8")) == data
    # No leftover temp file.
    assert not (tmp_path / "snap.json.tmp").exists()
