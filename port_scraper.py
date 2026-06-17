"""
PPS Anantam — port-page scraper (cron job, runs every 15 min).
Fetches Indian port pages (official gov + free aggregator), parses them via
port_sources, merges/dedupes, and writes tbl_port_arrivals.json — the real
India-coverage vessel source consumed by maritime_intelligence_engine.

Run from cron: python port_scraper.py  (or import and call run()).
"""
from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import port_sources as ps

BASE = Path(__file__).parent
OUT_PATH = BASE / "tbl_port_arrivals.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
FETCH_TIMEOUT = 25

_MYST = "https://www.myshiptracking.com/ports/port-of-{slug}-in-in-india-id-{id}"

# All major bitumen-relevant Indian ports. Kandla also scrapes the official
# Deendayal "Ships Expected" page (gives cargo + agent when populated).
PORTS = [
    {"name": "Kandla", "lat": 23.03, "lon": 70.22,
     "gov": "https://www.deendayalport.gov.in/en/ships-expected/",
     "myst": _MYST.format(slug="kandla", id=233)},
    {"name": "Mundra", "lat": 22.84, "lon": 69.73,
     "myst": _MYST.format(slug="mundra", id=305)},
    {"name": "Mumbai", "lat": 18.95, "lon": 72.94,
     "myst": _MYST.format(slug="mumbai", id=3658)},
    {"name": "JNPT (Nhava Sheva)", "lat": 18.95, "lon": 72.95,
     "myst": _MYST.format(slug="nhava-sheva", id=3646)},
    {"name": "Chennai", "lat": 13.08, "lon": 80.29,
     "myst": _MYST.format(slug="chennai", id=3639)},
    {"name": "Visakhapatnam", "lat": 17.69, "lon": 83.29,
     "myst": _MYST.format(slug="visakhapatnam", id=3632)},
    {"name": "Paradip", "lat": 20.26, "lon": 86.67,
     "myst": _MYST.format(slug="paradip", id=3618)},
]

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [port-scraper] %(levelname)s %(message)s")
log = logging.getLogger("port_scraper")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception as e:
        log.warning("fetch failed %s: %s", url, e)
        return None


def _dedupe(records: list[dict]) -> list[dict]:
    """Collapse duplicate vessels (same name+port). Prefer the record that
    carries cargo (gov source) so commodity/agent detail is not lost."""
    best: dict[tuple, dict] = {}
    for r in records:
        key = (r["name"].upper(), r["port"])
        cur = best.get(key)
        if cur is None or (r.get("cargo") and not cur.get("cargo")):
            best[key] = r
    return list(best.values())


def run() -> dict:
    """Fetch + parse + merge all ports; write the snapshot; return it."""
    records: list[dict] = []
    for p in PORTS:
        gov_url, myst_url = p.get("gov"), p.get("myst")
        if gov_url:
            html = _fetch(gov_url)
            if html:
                records += ps.parse_deendayal(html, p["name"], p["lat"], p["lon"])
        if myst_url:
            html = _fetch(myst_url)
            if html:
                records += ps.parse_myshiptracking(html, p["name"], p["lat"], p["lon"])

    merged = _dedupe(records)
    snap = {"updated_utc": _now_iso(), "source": "port-pages", "vessels": merged}
    tmp = OUT_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, default=str)
    import os
    os.replace(tmp, OUT_PATH)
    log.info("wrote %d vessels across %d ports", len(merged), len(PORTS))
    return snap


if __name__ == "__main__":
    run()
