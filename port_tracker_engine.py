"""
PPS Anantam Agentic AI Eco System
Port Import Tracker Engine v1.0
================================
Allocates UN Comtrade HS 271320 country-wise imports to Indian ports
using a configurable lookup table with confidence scoring.

No hardcoded formulas — all rules live in tbl_port_allocation_rules.json
and are editable from the PORT MAPPING HUB dashboard tab.

Tables managed:
  tbl_ports_master.json          — 10 major Indian port definitions
  tbl_port_allocation_rules.json — country→port split percentages
  tbl_imports_portwise.json      — allocated import volumes per port

Confidence scoring:
  direct data          → confidence_score 90–100  (reserved for future direct API)
  allocation_rule      → confidence_score 60–80   (rule from tbl_port_allocation_rules)
  default_distribution → confidence_score 45–55   (no country-specific rule)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from api_hub_engine import _load, _save, _ts, _date_str, _lock, BASE
except ImportError:
    import threading, datetime
    import pytz
    BASE  = Path(__file__).parent
    _lock = threading.RLock()
    def _load(p, d):
        try:
            if Path(p).exists():
                return json.load(open(p, encoding="utf-8"))
        except Exception: pass
        return d
    def _save(p, data):
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        json.dump(data, open(p,"w",encoding="utf-8"), indent=2, ensure_ascii=False, default=str)
    def _ts():
        return datetime.datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")
    def _date_str():
        return datetime.datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")


# ─── Table paths ───────────────────────────────────────────────────────────────
TBL_PORTS_MASTER = BASE / "tbl_ports_master.json"
TBL_ALLOC_RULES  = BASE / "tbl_port_allocation_rules.json"
TBL_IMP_PORTWISE = BASE / "tbl_imports_portwise.json"
TBL_IMP_CTRY     = BASE / "tbl_imports_countrywise.json"


# ─────────────────────────────────────────────────────────────────────────────
# PORTS MASTER DATA — 10 major Indian import ports for bitumen
# ─────────────────────────────────────────────────────────────────────────────

PORTS_MASTER: List[Dict] = [
    {"port_name": "Kandla (KPCT)",    "state": "Gujarat",        "coast": "West",
     "port_type": "Major", "lat": 23.03, "long": 70.22,
     "notes": "Largest bitumen import port; serves NW India"},
    {"port_name": "Mumbai (JNPT)",    "state": "Maharashtra",    "coast": "West",
     "port_type": "Major", "lat": 18.95, "long": 72.94,
     "notes": "Jawaharlal Nehru Port; West India hub"},
    {"port_name": "Chennai (CCTPL)",  "state": "Tamil Nadu",     "coast": "East",
     "port_type": "Major", "lat": 13.10, "long": 80.30,
     "notes": "Major East coast bitumen entry point"},
    {"port_name": "Paradip (PPT)",    "state": "Odisha",         "coast": "East",
     "port_type": "Major", "lat": 20.31, "long": 86.61,
     "notes": "Serves Odisha, Jharkhand, eastern belt"},
    {"port_name": "Mangalore (NMPT)", "state": "Karnataka",      "coast": "West",
     "port_type": "Major", "lat": 12.92, "long": 74.85,
     "notes": "New Mangalore Port; serves South-West"},
    {"port_name": "Haldia (HDC)",     "state": "West Bengal",    "coast": "East",
     "port_type": "Major", "lat": 22.07, "long": 88.07,
     "notes": "Serves East India; connects to Bangladesh corridor"},
    {"port_name": "Vizag (VPT)",      "state": "Andhra Pradesh", "coast": "East",
     "port_type": "Major", "lat": 17.68, "long": 83.28,
     "notes": "Visakhapatnam Port; AP + Telangana demand"},
    {"port_name": "Cochin (CPT)",     "state": "Kerala",         "coast": "West",
     "port_type": "Major", "lat":  9.96, "long": 76.27,
     "notes": "Cochin Port; South Kerala + backwater projects"},
    {"port_name": "Ennore (KPL)",     "state": "Tamil Nadu",     "coast": "East",
     "port_type": "Major", "lat": 13.21, "long": 80.32,
     "notes": "Kamarajar Port; industrial TN cargo"},
    {"port_name": "Mormugao (MPT)",   "state": "Goa",            "coast": "West",
     "port_type": "Major", "lat": 15.41, "long": 73.80,
     "notes": "Goa port; coastal Maharashtra spillover"},
]


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT ALLOCATION RULES
# Based on: shipping routes, refinery locations, known trade patterns
# Confidence 60–80 (rule-based proxy; editable by user)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_ALLOCATION_RULES: List[Dict] = []

_DEFAULT_RULES_RAW: Dict[str, List[Dict]] = {
    "Saudi Arabia": [
        {"port": "Kandla (KPCT)",    "pct": 45, "confidence": 78},
        {"port": "Mumbai (JNPT)",    "pct": 25, "confidence": 72},
        {"port": "Mangalore (NMPT)", "pct": 20, "confidence": 68},
        {"port": "Cochin (CPT)",     "pct": 10, "confidence": 65},
    ],
    "Iran": [
        {"port": "Kandla (KPCT)",    "pct": 68, "confidence": 80},
        {"port": "Mumbai (JNPT)",    "pct": 22, "confidence": 72},
        {"port": "Mangalore (NMPT)", "pct": 10, "confidence": 60},
    ],
    "Kuwait": [
        {"port": "Kandla (KPCT)",    "pct": 50, "confidence": 75},
        {"port": "Mumbai (JNPT)",    "pct": 30, "confidence": 70},
        {"port": "Mangalore (NMPT)", "pct": 20, "confidence": 65},
    ],
    "Iraq": [
        {"port": "Kandla (KPCT)",    "pct": 42, "confidence": 70},
        {"port": "Mumbai (JNPT)",    "pct": 33, "confidence": 68},
        {"port": "Mangalore (NMPT)", "pct": 25, "confidence": 65},
    ],
    "UAE": [
        {"port": "Kandla (KPCT)",    "pct": 40, "confidence": 72},
        {"port": "Mumbai (JNPT)",    "pct": 35, "confidence": 70},
        {"port": "Cochin (CPT)",     "pct": 15, "confidence": 65},
        {"port": "Mangalore (NMPT)", "pct": 10, "confidence": 60},
    ],
    "Singapore": [
        {"port": "Chennai (CCTPL)",  "pct": 35, "confidence": 72},
        {"port": "Vizag (VPT)",      "pct": 30, "confidence": 68},
        {"port": "Paradip (PPT)",    "pct": 20, "confidence": 65},
        {"port": "Haldia (HDC)",     "pct": 15, "confidence": 62},
    ],
    "China": [
        {"port": "Haldia (HDC)",     "pct": 30, "confidence": 68},
        {"port": "Paradip (PPT)",    "pct": 28, "confidence": 65},
        {"port": "Chennai (CCTPL)",  "pct": 22, "confidence": 65},
        {"port": "Vizag (VPT)",      "pct": 20, "confidence": 62},
    ],
    "Russia": [
        {"port": "Kandla (KPCT)",    "pct": 38, "confidence": 65},
        {"port": "Mumbai (JNPT)",    "pct": 28, "confidence": 62},
        {"port": "Paradip (PPT)",    "pct": 20, "confidence": 60},
        {"port": "Haldia (HDC)",     "pct": 14, "confidence": 58},
    ],
    "Netherlands": [
        {"port": "Kandla (KPCT)",    "pct": 35, "confidence": 62},
        {"port": "Mumbai (JNPT)",    "pct": 30, "confidence": 60},
        {"port": "Chennai (CCTPL)",  "pct": 20, "confidence": 58},
        {"port": "Mangalore (NMPT)", "pct": 15, "confidence": 55},
    ],
    "Default": [
        {"port": "Kandla (KPCT)",    "pct": 40, "confidence": 52},
        {"port": "Mumbai (JNPT)",    "pct": 25, "confidence": 50},
        {"port": "Chennai (CCTPL)",  "pct": 15, "confidence": 48},
        {"port": "Paradip (PPT)",    "pct": 10, "confidence": 48},
        {"port": "Mangalore (NMPT)", "pct": 10, "confidence": 46},
    ],
}

# Flatten into list-of-dicts for tbl_port_allocation_rules.json
def _build_default_rules() -> List[Dict]:
    rows = []
    for country, splits in _DEFAULT_RULES_RAW.items():
        for s in splits:
            rows.append({
                "origin_country":  country,
                "product":         "Bitumen (HS 271320)",
                "port_name":       s["port"],
                "split_pct":       s["pct"],
                "effective_from":  "2023-01-01",
                "confidence_score": s["confidence"],
                "method":          "allocation_rule" if country != "Default" else "default_distribution",
                "notes":           "Based on known trade routes and PPAC import data patterns",
            })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────────────────

def init_port_tracker() -> None:
    """Create tbl_ports_master.json and tbl_port_allocation_rules.json if not exist."""
    if not TBL_PORTS_MASTER.exists():
        _save(TBL_PORTS_MASTER, PORTS_MASTER)

    if not TBL_ALLOC_RULES.exists():
        _save(TBL_ALLOC_RULES, _build_default_rules())

    if not TBL_IMP_PORTWISE.exists():
        _save(TBL_IMP_PORTWISE, [])


# ─────────────────────────────────────────────────────────────────────────────
# LOAD / SAVE ALLOCATION RULES
# ─────────────────────────────────────────────────────────────────────────────

def load_allocation_rules() -> List[Dict]:
    """Load rules from JSON. Falls back to built-in defaults."""
    rules = _load(TBL_ALLOC_RULES, [])
    if not rules:
        rules = _build_default_rules()
        _save(TBL_ALLOC_RULES, rules)
    return rules


def save_allocation_rules(rules: List[Dict]) -> None:
    """Persist edited rules to tbl_port_allocation_rules.json."""
    with _lock:
        _save(TBL_ALLOC_RULES, rules)


def reset_allocation_rules() -> None:
    """Reset to built-in defaults."""
    _save(TBL_ALLOC_RULES, _build_default_rules())


# ─────────────────────────────────────────────────────────────────────────────
# ALLOCATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _get_rules_for_country(country: str, rules: List[Dict]) -> List[Dict]:
    """Return split rows for a specific country, falling back to Default."""
    country_rules = [r for r in rules if r["origin_country"] == country]
    if not country_rules:
        country_rules = [r for r in rules if r["origin_country"] == "Default"]
    return country_rules


def allocate_imports_to_ports() -> Dict:
    """
    Read tbl_imports_countrywise.json, apply allocation rules,
    write allocated rows to tbl_imports_portwise.json.

    Returns: {ok, records_written, method_summary}
    """
    init_port_tracker()

    country_data = _load(TBL_IMP_CTRY, [])
    if not country_data:
        return {"ok": False, "records_written": 0,
                "error": "tbl_imports_countrywise is empty — run comtrade_hs271320 connector first"}

    rules = load_allocation_rules()

    allocated_rows: List[Dict] = []
    method_counts  = {"allocation_rule": 0, "default_distribution": 0, "direct": 0}

    for imp_row in country_data:
        country    = imp_row.get("origin_country", "Unknown")
        period     = imp_row.get("period_label", "2024")
        qty_kg     = float(imp_row.get("qty_kg", 0) or 0)
        value_usd  = float(imp_row.get("value_usd", 0) or 0)
        hs_code    = imp_row.get("hs_code", "271320")

        if qty_kg <= 0:
            continue

        country_rules = _get_rules_for_country(country, rules)
        method = country_rules[0]["method"] if country_rules else "default_distribution"

        # Ensure splits sum to 100 (normalize if edited rules don't sum correctly)
        total_pct = sum(r.get("split_pct", 0) for r in country_rules)
        if total_pct <= 0:
            total_pct = 100.0

        for rule in country_rules:
            pct        = float(rule.get("split_pct", 0))
            normalized = pct / total_pct
            conf       = int(rule.get("confidence_score", 50))
            port_name  = rule.get("port_name", "Kandla (KPCT)")

            allocated_rows.append({
                "fetch_date_ist":    _ts(),
                "period_label":      period,
                "port_name":         port_name,
                "origin_country":    country,
                "hs_code":           hs_code,
                "qty_allocated_kg":  round(qty_kg * normalized, 0),
                "value_usd":         round(value_usd * normalized, 2),
                "split_pct":         round(pct, 2),
                "method":            method,
                "confidence_score":  conf,
                "source":            "UN Comtrade + PPS Port Allocation Rules v1.0",
            })
            method_counts[method] = method_counts.get(method, 0) + 1

    if allocated_rows:
        # Replace (not append) portwise table to avoid duplicates on re-run
        _save(TBL_IMP_PORTWISE, allocated_rows[-5000:])

    return {
        "ok":             True,
        "records_written": len(allocated_rows),
        "method_summary": method_counts,
        "source_records":  len(country_data),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_port_summary() -> List[Dict]:
    """Return list of ports sorted by total allocated qty_mt descending.
    Fields: port_name, state, coast, total_qty_mt, total_value_usd,
            avg_confidence, country_count, pct_share
    """
    rows = _load(TBL_IMP_PORTWISE, [])
    if not rows:
        return []

    # PORTS_MASTER lookup: port_name → {state, coast}
    master_lookup: Dict[str, Dict] = {
        p["port_name"]: {"state": p.get("state", ""), "coast": p.get("coast", "")}
        for p in PORTS_MASTER
    }

    totals: Dict[str, Dict] = {}
    for r in rows:
        port = r.get("port_name", "Unknown")
        if port not in totals:
            meta = master_lookup.get(port, {"state": "", "coast": ""})
            totals[port] = {
                "port_name":       port,
                "state":           meta["state"],
                "coast":           meta["coast"],
                "total_qty_mt":    0.0,
                "total_value_usd": 0.0,
                "avg_confidence":  [],
                "countries":       set(),
            }
        totals[port]["total_qty_mt"]     += float(r.get("qty_allocated_kg", 0)) / 1000.0
        totals[port]["total_value_usd"]  += float(r.get("value_usd", 0))
        totals[port]["avg_confidence"].append(int(r.get("confidence_score", 50)))
        totals[port]["countries"].add(r.get("origin_country", ""))

    result = []
    for port, d in totals.items():
        conf_list = d["avg_confidence"]
        result.append({
            "port_name":       port,
            "state":           d["state"],
            "coast":           d["coast"],
            "total_qty_mt":    round(d["total_qty_mt"], 1),
            "total_value_usd": round(d["total_value_usd"], 0),
            "avg_confidence":  round(sum(conf_list)/len(conf_list), 1) if conf_list else 0,
            "country_count":   len(d["countries"]),
            "pct_share":       0.0,  # calculated below
        })

    total_mt = sum(r["total_qty_mt"] for r in result) or 1.0
    for r in result:
        r["pct_share"] = round(r["total_qty_mt"] / total_mt * 100, 1)

    return sorted(result, key=lambda x: x["total_qty_mt"], reverse=True)


def get_country_port_matrix() -> Dict[str, Dict[str, float]]:
    """
    Build pivot: {country: {port: qty_mt}} for cross-tab display.
    """
    rows = _load(TBL_IMP_PORTWISE, [])
    matrix: Dict[str, Dict[str, float]] = {}
    for r in rows:
        country = r.get("origin_country", "Unknown")
        port    = r.get("port_name", "Unknown")
        qty_mt  = float(r.get("qty_allocated_kg", 0)) / 1000.0
        matrix.setdefault(country, {})
        matrix[country][port] = matrix[country].get(port, 0.0) + qty_mt
    return matrix


def get_confidence_breakdown() -> Dict[str, int]:
    """Return count of rows by confidence band: high/medium/low."""
    rows = _load(TBL_IMP_PORTWISE, [])
    breakdown = {"High (80-100)": 0, "Medium (60-79)": 0, "Low (< 60)": 0}
    for r in rows:
        c = int(r.get("confidence_score", 50))
        if c >= 80:
            breakdown["High (80-100)"] += 1
        elif c >= 60:
            breakdown["Medium (60-79)"] += 1
        else:
            breakdown["Low (< 60)"] += 1
    return breakdown


def get_top_port() -> str:
    """Return name of port with highest total allocated volume."""
    summary = get_port_summary()
    return summary[0]["port_name"] if summary else "No data"


def get_avg_confidence() -> float:
    """Return overall average confidence score across all portwise rows."""
    rows = _load(TBL_IMP_PORTWISE, [])
    if not rows:
        return 0.0
    scores = [int(r.get("confidence_score", 50)) for r in rows]
    return round(sum(scores) / len(scores), 1)


def get_total_allocated_mt() -> float:
    """Return total allocated volume in metric tonnes."""
    rows = _load(TBL_IMP_PORTWISE, [])
    return round(sum(float(r.get("qty_allocated_kg", 0)) for r in rows) / 1000.0, 1)
