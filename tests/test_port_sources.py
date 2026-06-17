from __future__ import annotations
from pathlib import Path
import port_sources as ps

FIX = Path(__file__).parent / "fixtures"


def test_clean_name_flag():
    assert ps._clean_name_flag("VELON 1 [AW]") == ("VELON 1", "AW")
    assert ps._clean_name_flag("VIGOR OL [LR]") == ("VIGOR OL", "LR")
    assert ps._clean_name_flag("NOFLAG") == ("NOFLAG", "")


def test_extract_dt():
    assert ps._extract_dt("LT 2026-06-17 12:42 UT") == "2026-06-17 12:42"
    assert ps._extract_dt("no date here") == ""


def test_parse_myshiptracking_real_fixture():
    html = (FIX / "myst_kandla.html").read_text(encoding="utf-8")
    recs = ps.parse_myshiptracking(html, "Kandla", 23.03, 70.22)
    # Should find both expected-arrival and in-port vessels.
    by_name = {r["name"]: r for r in recs}
    assert "VELON 1" in by_name
    assert by_name["VELON 1"]["mmsi"] == "307074000"
    assert by_name["VELON 1"]["status"] == "expected"
    assert "2026-06-17 12:42" in by_name["VELON 1"]["eta"]
    assert "VIGOR OL" in by_name and by_name["VIGOR OL"]["status"] == "in_port"
    # In-port vessels now also carry MMSI/IMO from the row's vessel link.
    assert by_name["VIGOR OL"]["mmsi"] == "636023727"
    assert by_name["VIGOR OL"]["imo"] == "1057268"
    # All records carry the port + coords + source.
    for r in recs:
        assert r["port"] == "Kandla" and r["port_lat"] == 23.03 and r["source"] == "myshiptracking"
    # Activity rows (ARRIVAL/DEPARTURE) must not leak in as vessels.
    assert all(r["name"] not in ("ARRIVAL", "DEPARTURE") for r in recs)
    assert len(recs) >= 10


_GOV_HTML = """
<table class="table table-bordered">
<tr><th>Sr No</th><th>VCN NUMBER</th><th>Name Of The Vessels</th><th>Date</th>
<th>Cargo Particulars</th><th>Loa Draft</th><th>Agents</th><th>Remarks</th></tr>
<tr><td>1</td><td>VCN123</td><td>MT GULF PRIDE</td><td>18-06-2026</td>
<td>BITUMEN VG-30</td><td>180 / 9.5</td><td>ABC Shipping</td><td>-</td></tr>
<tr><td>2</td><td>VCN124</td><td>MV OCEAN STAR</td><td>19-06-2026</td>
<td>CRUDE OIL</td><td>200 / 11</td><td>XYZ Agents</td><td>-</td></tr>
</table>
"""


def test_parse_deendayal_populated():
    recs = ps.parse_deendayal(_GOV_HTML, "Kandla", 23.03, 70.22)
    assert len(recs) == 2
    first = recs[0]
    assert first["name"] == "MT GULF PRIDE"
    assert first["cargo"] == "BITUMEN VG-30"
    assert first["agent"] == "ABC Shipping"
    assert first["eta"] == "18-06-2026"
    assert first["status"] == "expected"
    assert first["source"] == "deendayal" and first["port"] == "Kandla"


def test_parse_deendayal_empty_is_safe():
    # The real page is often empty (header row only) -> no rows, no crash.
    html = (FIX / "deendayal_ships.html").read_text(encoding="utf-8")
    recs = ps.parse_deendayal(html, "Kandla", 23.03, 70.22)
    assert recs == []
