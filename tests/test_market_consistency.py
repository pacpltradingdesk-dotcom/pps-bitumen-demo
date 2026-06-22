"""Live Market dict must come from the same single source (get_unified_prices)
as the Command Center, so prices never disagree across screens."""

import market_data as md


def test_live_market_brent_matches_unified():
    u = md.get_unified_prices()
    m = md.get_live_market_data()
    if u.get("brent") is not None:
        assert m["brent"]["value"] == f"${float(u['brent']):.2f}"


def test_live_market_usdinr_matches_unified():
    u = md.get_unified_prices()
    m = md.get_live_market_data()
    if u.get("usdinr") is not None:
        assert m["usdinr"]["value"] == f"{float(u['usdinr']):.2f}"


def test_live_market_wti_matches_unified():
    u = md.get_unified_prices()
    m = md.get_live_market_data()
    if u.get("wti") is not None:
        assert m["wti"]["value"] == f"${float(u['wti']):.2f}"


def test_power_stats_ribbon_vg30_matches_unified():
    """The Power Stats ribbon must show the same VG30 as the single source —
    the QA-log "₹79,339 in ribbon vs ₹79,110 in Command Center" divergence."""
    from components.power_stats_ribbon import _vg30_price
    u = md.get_unified_prices()
    if u.get("vg30") is not None:
        assert _vg30_price() == int(round(float(u["vg30"])))
