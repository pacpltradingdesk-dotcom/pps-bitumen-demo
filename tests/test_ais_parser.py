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
