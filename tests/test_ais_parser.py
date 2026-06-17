from __future__ import annotations
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
