from __future__ import annotations
import importlib.util
from pathlib import Path

_PATH = Path(__file__).parent.parent / "command_intel" / "maritime_logistics_dashboard.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mld", _PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_track_links_builds_all_three_sources():
    mld = _load_module()
    links = mld._track_links("HAFNIA MERLIN")
    assert set(links) == {"MarineTraffic", "VesselFinder", "MyShipTracking"}
    # URL-encoded query in each link.
    assert "HAFNIA+MERLIN" in links["VesselFinder"]
    assert "HAFNIA+MERLIN" in links["MyShipTracking"]
    assert "HAFNIA+MERLIN" in links["MarineTraffic"]
    assert links["MarineTraffic"].startswith("https://www.marinetraffic.com")
    assert links["VesselFinder"].startswith("https://www.vesselfinder.com")
    assert links["MyShipTracking"].startswith("https://www.myshiptracking.com")


def test_track_links_handles_imo_number():
    mld = _load_module()
    links = mld._track_links("9876543")
    assert "9876543" in links["VesselFinder"]
