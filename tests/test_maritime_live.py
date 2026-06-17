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
