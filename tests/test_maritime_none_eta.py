"""Maritime pages must survive live-AIS vessels with eta_hours=None.

User report 09-07-2026: "Maritime Logistics failed to load: '<' not supported
between instances of 'NoneType' and 'NoneType'". Live AIS vessels legitimately
carry eta_hours=None (anchored / no speed-over-ground), but
generate_daily_summary() sorted container ETAs and took min() over raw
eta_hours values — two Nones compared and the whole page died. The simulator
always filled eta_hours, so this only crashed once REAL AIS data arrived.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from maritime_intelligence_engine import generate_daily_summary  # noqa: E402


def _vessel(name, port, eta_hours, cargo="container"):
    return {
        "vessel_name": name, "cargo_type": cargo,
        "departure_port": "Fujairah", "destination_port": port,
        "eta": "2026-07-12 10:00 IST", "eta_hours": eta_hours,
        "status": "in_transit", "cargo_mt": 30_000, "product_grade": "VG30",
        "is_simulated": False, "lat": 20.0, "lon": 65.0,
    }


def test_daily_summary_survives_none_eta_hours():
    intel = {
        "vessels": [
            _vessel("GULF PRIDE", "Mundra", None),      # anchored — no ETA
            _vessel("SEA QUEEN", "Mundra", None),        # two Nones -> old crash
            _vessel("OCEAN STAR", "Kandla", 42.5),
            _vessel("BULK RUNNER", "Kandla", None, cargo="bulk"),
        ],
        "port_congestion": [
            {"port": "Mundra", "score": 40, "level": "MEDIUM", "priority": "P1"},
            {"port": "Kandla", "score": 20, "level": "LOW", "priority": "P2"},
        ],
        "routes": [],
    }

    summary = generate_daily_summary(intel)   # must not raise

    assert isinstance(summary, dict)
    # Known-ETA vessel must sort ahead of the unknown-ETA ones.
    etas = summary.get("container_etas") or summary.get("upcoming_arrivals") or []
    if etas:
        known = [e for e in etas if e.get("eta_hours") is not None]
        if known:
            assert etas[0].get("eta_hours") == known[0].get("eta_hours")
