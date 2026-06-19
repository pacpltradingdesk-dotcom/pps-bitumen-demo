"""Manual-entry Sub-Location now offers the full city/terminal universe
(like the Pricing Calculator) plus a custom-type fallback."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "command_intel"))
import manual_entry as me  # noqa: E402


def test_location_options_is_rich_and_includes_terminals():
    opts = me._location_options()
    assert len(opts) > 50, "should be the full city list, not 5 hardcoded"
    for must in ("Kandla", "Mundra", "Mumbai"):
        assert must in opts, f"{must} missing from sub-location options"
    # refinery names should be stripped out (we want cities/terminals)
    assert not any("IOCL" in o for o in opts)


def test_drum_prefix_routes_gujarat_region_to_kandla():
    assert me._drum_prefix("Kandla") == "DRUM_KANDLA"
    assert me._drum_prefix("Mundra Port") == "DRUM_KANDLA"
    assert me._drum_prefix("Gujarat") == "DRUM_KANDLA"
    assert me._drum_prefix("Chennai") == "DRUM_MUMBAI"
    assert me._drum_prefix("") == "DRUM_MUMBAI"
