"""
PPS Anantam — single-ship lookup (scrape + parse, shown IN the dashboard).
Given an IMO or MMSI, fetches the VesselFinder detail page and parses a
rich live card (name, type, flag, built, nav status, destination, last
port, position-received, ETA, draught, course/speed) — no redirect.

Parsing is pure (regex on server-rendered HTML) so it is unit-testable.
"""
from __future__ import annotations

import re
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
DETAIL_URL = "https://www.vesselfinder.com/vessels/details/{id}"


def _strip(html_fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_fragment or "")).strip()


def parse_vesselfinder_detail(html: str) -> dict:
    """Parse a VesselFinder vessel-detail page into a structured dict."""
    out = {"name": "", "type": "", "imo": "", "mmsi": "", "built": "",
           "flag": "", "params": {}}
    if not html:
        return out

    # Title: "NAME, TYPE - Details and current position - IMO ... - VesselFinder"
    t = re.search(r"<title>([^<]+)</title>", html)
    if t:
        head = t.group(1).split(" - ")[0]          # "NAME, TYPE"
        if "," in head:
            name, _, vtype = head.partition(",")
            out["name"] = name.strip()
            out["type"] = vtype.strip()
        else:
            out["name"] = head.strip()

    # Meta description: "Vessel NAME (IMO 9682239, MMSI 563484000) is a TYPE
    # built in 2015 and currently sailing under the flag of Singapore."
    md = re.search(r'<meta name="description" content="([^"]+)"', html)
    if md:
        desc = md.group(1)
        m = re.search(r"IMO (\d+), MMSI (\d+)", desc)
        if m:
            out["imo"], out["mmsi"] = m.group(1), m.group(2)
        b = re.search(r"built in (\d{4})", desc)
        if b:
            out["built"] = b.group(1)
        f = re.search(r"flag of ([A-Za-z .'-]+?)\.", desc)
        if f:
            out["flag"] = f.group(1).strip()

    # Params table: one <tr> per row, with n3 (label) + v3 (value) cells.
    # Row-scoped so labels/values never merge across rows.
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        n = re.search(r'<td class="n3">(.*?)</td>', row, re.S)
        v = re.search(r'<td class="v3">(.*?)</td>', row, re.S)
        if not (n and v):
            continue
        lbl, val = _strip(n.group(1)), _strip(v.group(1))
        if lbl and len(lbl) < 40:
            out["params"][lbl] = val

    # Voyage / vilabel blocks (Destination, Last Port, ...) — value sits in the
    # next <a> or <div> after the label, and ETA/ATA in a following span.
    for lbl, val in re.findall(
            r'vilabel">([^<]+)</div>\s*<(?:a|div)[^>]*>([^<]+)</(?:a|div)>', html, re.S):
        out["params"].setdefault(_strip(lbl), _strip(val))
    em = re.search(r"ETA:\s*([^<]+?)<", html)
    if em:
        out["params"].setdefault("ETA", _strip(em.group(1)))
    return out


def fetch_vessel(query: str) -> dict | None:
    """Fetch + parse a vessel by IMO or MMSI (digits). None on any failure."""
    q = re.sub(r"\D", "", query or "")
    if not q:
        return None
    try:
        req = urllib.request.Request(DETAIL_URL.format(id=q), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", "ignore")
        data = parse_vesselfinder_detail(html)
        return data if data.get("name") else None
    except Exception:
        return None
