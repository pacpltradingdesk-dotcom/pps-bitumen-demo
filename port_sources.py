"""
PPS Anantam — port-page vessel parsers (pure, no network).
Free India-coverage vessel data scraped from Indian port pages:
  - Official port authority "Ships Expected" tables (cargo + agent)
  - Free aggregator port pages (MyShipTracking) — expected arrivals + in-port

Free AIS (AISStream) has ~no Arabian Gulf / India coverage, so these
port-centric arrival lists are our real-data source for the maritime page.
Kept dependency-free (regex on server-rendered HTML) so it is fully testable.
"""
from __future__ import annotations

import re

_FLAG_RE = re.compile(r"\[([A-Z]{2})\]\s*$")
_DT_RE = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
_MMSI_RE = re.compile(r"\d{9}")


def _clean_name_flag(s: str) -> tuple[str, str]:
    """'VELON 1 [AW]' -> ('VELON 1', 'AW'); 'NOFLAG' -> ('NOFLAG', '')."""
    s = (s or "").strip()
    m = _FLAG_RE.search(s)
    if m:
        return s[: m.start()].strip(), m.group(1)
    return s, ""


def _extract_dt(s: str) -> str:
    """Pull 'YYYY-MM-DD HH:MM' out of a noisy time cell, else ''."""
    m = _DT_RE.search(s or "")
    return m.group(1) if m else ""


def _cells(tr_html: str) -> list[str]:
    """Plain-text content of each <td> in a table row."""
    out = []
    for c in re.findall(r"<td[^>]*>(.*?)</td>", tr_html, re.S):
        txt = re.sub(r"<[^>]+>", " ", c)
        out.append(re.sub(r"\s+", " ", txt).strip())
    return out


def _rec(name: str, flag: str, port: str, lat: float, lon: float, source: str,
         *, mmsi: str = "", imo: str = "", eta: str = "", cargo: str = "",
         agent: str = "", status: str = "expected") -> dict:
    return {
        "name": name, "flag": flag, "mmsi": mmsi, "imo": imo,
        "port": port, "port_lat": lat, "port_lon": lon,
        "eta": eta, "cargo": cargo, "agent": agent,
        "status": status, "source": source,
    }


def parse_myshiptracking(html: str, port: str, lat: float, lon: float) -> list[dict]:
    """Parse MyShipTracking port page: expected arrivals + vessels in port."""
    recs: list[dict] = []
    for block in re.findall(r'<table class="myst-table[^>]*>.*?</table>', html, re.S):
        for tr in re.findall(r"<tr[^>]*>.*?</tr>", block, re.S):
            cells = _cells(tr)
            if len(cells) < 2:
                continue
            if _MMSI_RE.fullmatch(cells[0]):
                # Expected arrival: MMSI | NAME [FLAG] | ETA
                name, flag = _clean_name_flag(cells[1])
                if name:
                    recs.append(_rec(name, flag, port, lat, lon, "myshiptracking",
                                     mmsi=cells[0],
                                     eta=_extract_dt(cells[2] if len(cells) > 2 else ""),
                                     status="expected"))
            elif any(c in ("ARRIVAL", "DEPARTURE") for c in cells):
                continue  # activity feed row — not a vessel listing
            elif _FLAG_RE.search(cells[0]) and _extract_dt(cells[1]):
                # In port: NAME [FLAG] | arrived-time | ...
                name, flag = _clean_name_flag(cells[0])
                if name:
                    recs.append(_rec(name, flag, port, lat, lon, "myshiptracking",
                                     eta=_extract_dt(cells[1]), status="in_port"))
    return recs


def parse_deendayal(html: str, port: str, lat: float, lon: float) -> list[dict]:
    """Parse a Deendayal-style gov 'Ships Expected' table (cargo + agent).

    Columns: Sr No | VCN | Name | Date | Cargo Particulars | LOA/Draft | Agents | Remarks.
    Returns [] when the table is empty (header only) — the common live state.
    """
    recs: list[dict] = []
    m = re.search(r'<table[^>]*class="[^"]*table-bordered[^"]*"[^>]*>(.*?)</table>',
                  html, re.S)
    if not m:
        return recs
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S):
        cells = _cells(tr)
        if len(cells) < 7:
            continue  # header row (uses <th>) or malformed
        name = cells[2].strip()
        if not name:
            continue
        recs.append(_rec(name, "", port, lat, lon, "deendayal",
                         eta=cells[3], cargo=cells[4], agent=cells[6],
                         status="expected"))
    return recs
