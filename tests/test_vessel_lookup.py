from __future__ import annotations
from pathlib import Path
import vessel_lookup as vl

FIX = Path(__file__).parent / "fixtures"


def test_parse_vesselfinder_detail():
    html = (FIX / "vesselfinder_detail.html").read_text(encoding="utf-8")
    d = vl.parse_vesselfinder_detail(html)
    assert d["name"] == "HAFNIA MERLIN"
    assert "Tanker" in d["type"]
    assert d["imo"] == "9682239"
    assert d["mmsi"] == "563484000"
    assert d["built"] == "2015"
    assert d["flag"] == "Singapore"
    # Live params parsed from the n3/v3 table.
    assert d["params"]["Navigation Status"] == "At anchor"
    assert d["params"]["Destination"] == "WESTERN AWW"
    assert "Singapore" in d["params"]["Last Port"]
    assert "m" in d["params"]["Current draught"]


def test_parse_vesselfinder_detail_empty_safe():
    d = vl.parse_vesselfinder_detail("<html><body>nothing</body></html>")
    assert d["name"] == "" and d["params"] == {}
