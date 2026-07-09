"""TENDERS ticker must show tender/infra-procurement news, not general news.

Live audit 09-07-2026: the TENDERS ticker was scrolling "Delhi rains: Roads
waterlogged", "crime scene reconstruction", "Wayanad landslide ... tunnel
construction site", "Manhattan skyscraper evacuated" — the keyword regex had
no word boundaries and generic words (road/construction/infra) matched any
disaster or crime story that mentioned a road.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from news_engine import filter_tender_headlines  # noqa: E402


def _arts(*headlines):
    return [{"headline": h, "summary": ""} for h in headlines]


def test_strong_procurement_keywords_pass():
    arts = _arts(
        "NHAI awards 120km highway contract in Bihar worth Rs 2,400 Cr",
        "Gujarat PWD floats tender for 80km rural road upgrade",
        "MoRTH approves 6-lane expressway connecting Vadodara to Mumbai",
        "Govt to widen capex scope from FY28 for highway projects",
    )
    assert len(filter_tender_headlines(arts)) == 4


def test_disaster_and_crime_news_rejected():
    arts = _arts(
        "Delhi rains update: Roads waterlogged, trains delayed",
        "Baruipur case: accused shot dead during crime scene reconstruction",
        "Wayanad landslide: rubble slide at tunnel construction site",
        "Manhattan skyscraper evacuated after structural columns buckled",
        "Monsoon rains bring Gurugram to a halt as bus sinks into caved-in road",
    )
    assert filter_tender_headlines(arts) == []


def test_generic_word_needs_procurement_context():
    arts = _arts(
        "New road opens for traffic in city",              # generic, no context
        "State floats Rs 500 crore road construction tender",  # context: tender/crore
    )
    out = filter_tender_headlines(arts)
    assert len(out) == 1
    assert "500 crore" in out[0]


def test_reconstruction_does_not_match_construction():
    arts = _arts("Historic fort reconstruction project wins award")
    assert filter_tender_headlines(arts) == []
