# -*- coding: utf-8 -*-
"""
PPS Anantam — Infra Demand Intelligence Engine v1.0
=====================================================
GDELT + data.gov.in + budget cross-check → bitumen demand estimation.
2-year backfill + live incremental updates.

Sources:
  GDELT DOC 2.0 API     — infrastructure news, sentiment, tender signals
  GDELT GEO 2.0 API     — geo-located infrastructure events
  data.gov.in            — NHAI road progress, MoRTH highway length
  road_budget_demand.py  — STATE_DATA, MONTHLY_DEMAND_INDEX, STATE_MONSOON_MONTHS

Output tables (SQLite):
  infra_news             — parsed infrastructure articles
  infra_budgets          — state budget data
  infra_demand_scores    — computed demand scores per state/city
  infra_alerts           — P0/P1/P2 demand intelligence alerts
  infra_sources          — source health registry

All times: IST (Asia/Kolkata)
"""

import datetime
import difflib
import hashlib
import json
import re
import sqlite3
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytz
import requests

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

_lock = threading.RLock()
_session = requests.Session()
_session.headers.update({"User-Agent": "PPS-Anantam-InfraDemand/1.0"})


def _now() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════════
# GEO MASTER — Indian States, Cities, Departments, Work Types
# ═══════════════════════════════════════════════════════════════════════════════

INDIAN_STATES = {
    "Andhra Pradesh": ["AP"],
    "Arunachal Pradesh": ["AR"],
    "Assam": ["AS"],
    "Bihar": ["BR"],
    "Chhattisgarh": ["CG"],
    "Goa": ["GA"],
    "Gujarat": ["GJ"],
    "Haryana": ["HR"],
    "Himachal Pradesh": ["HP"],
    "Jharkhand": ["JH"],
    "Karnataka": ["KA"],
    "Kerala": ["KL"],
    "Madhya Pradesh": ["MP"],
    "Maharashtra": ["MH"],
    "Manipur": ["MN"],
    "Meghalaya": ["ML"],
    "Mizoram": ["MZ"],
    "Nagaland": ["NL"],
    "Odisha": ["OD", "OR"],
    "Punjab": ["PB"],
    "Rajasthan": ["RJ"],
    "Sikkim": ["SK"],
    "Tamil Nadu": ["TN"],
    "Telangana": ["TS", "TG"],
    "Tripura": ["TR"],
    "Uttar Pradesh": ["UP"],
    "Uttarakhand": ["UK", "UA"],
    "West Bengal": ["WB"],
    "Delhi": ["DL"],
    "Jammu and Kashmir": ["JK"],
    "Ladakh": ["LA"],
    "Chandigarh": ["CH"],
    "Puducherry": ["PY"],
    "Andaman and Nicobar": ["AN"],
}

MAJOR_CITIES = {
    "Mumbai": "Maharashtra", "Pune": "Maharashtra", "Nagpur": "Maharashtra",
    "Nashik": "Maharashtra", "Aurangabad": "Maharashtra", "Thane": "Maharashtra",
    "Solapur": "Maharashtra", "Kolhapur": "Maharashtra",
    "Delhi": "Delhi", "New Delhi": "Delhi", "Noida": "Uttar Pradesh",
    "Gurgaon": "Haryana", "Gurugram": "Haryana", "Faridabad": "Haryana",
    "Ghaziabad": "Uttar Pradesh",
    "Bengaluru": "Karnataka", "Bangalore": "Karnataka", "Mysore": "Karnataka",
    "Hubli": "Karnataka", "Mangalore": "Karnataka", "Mangaluru": "Karnataka",
    "Hyderabad": "Telangana", "Warangal": "Telangana", "Secunderabad": "Telangana",
    "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu", "Madurai": "Tamil Nadu",
    "Salem": "Tamil Nadu", "Tiruchirappalli": "Tamil Nadu",
    "Kolkata": "West Bengal", "Siliguri": "West Bengal", "Durgapur": "West Bengal",
    "Ahmedabad": "Gujarat", "Surat": "Gujarat", "Vadodara": "Gujarat",
    "Rajkot": "Gujarat", "Gandhinagar": "Gujarat", "Bhavnagar": "Gujarat",
    "Jaipur": "Rajasthan", "Jodhpur": "Rajasthan", "Udaipur": "Rajasthan",
    "Kota": "Rajasthan", "Ajmer": "Rajasthan", "Bikaner": "Rajasthan",
    "Lucknow": "Uttar Pradesh", "Kanpur": "Uttar Pradesh", "Agra": "Uttar Pradesh",
    "Varanasi": "Uttar Pradesh", "Meerut": "Uttar Pradesh",
    "Allahabad": "Uttar Pradesh", "Prayagraj": "Uttar Pradesh",
    "Gorakhpur": "Uttar Pradesh", "Bareilly": "Uttar Pradesh",
    "Patna": "Bihar", "Gaya": "Bihar", "Muzaffarpur": "Bihar",
    "Bhopal": "Madhya Pradesh", "Indore": "Madhya Pradesh",
    "Jabalpur": "Madhya Pradesh", "Gwalior": "Madhya Pradesh",
    "Raipur": "Chhattisgarh", "Bilaspur": "Chhattisgarh",
    "Bhubaneswar": "Odisha", "Cuttack": "Odisha",
    "Ranchi": "Jharkhand", "Jamshedpur": "Jharkhand", "Dhanbad": "Jharkhand",
    "Chandigarh": "Chandigarh", "Ludhiana": "Punjab", "Amritsar": "Punjab",
    "Jalandhar": "Punjab",
    "Dehradun": "Uttarakhand", "Haridwar": "Uttarakhand",
    "Guwahati": "Assam", "Imphal": "Manipur", "Shillong": "Meghalaya",
    "Gangtok": "Sikkim", "Agartala": "Tripura",
    "Thiruvananthapuram": "Kerala", "Kochi": "Kerala", "Kozhikode": "Kerala",
    "Visakhapatnam": "Andhra Pradesh", "Vijayawada": "Andhra Pradesh",
    "Nellore": "Andhra Pradesh", "Tirupati": "Andhra Pradesh",
    "Panaji": "Goa", "Shimla": "Himachal Pradesh",
    "Srinagar": "Jammu and Kashmir", "Jammu": "Jammu and Kashmir",
    "Leh": "Ladakh",
}

DEPT_KEYWORDS = {
    "NHAI": ["nhai", "national highway authority", "national highways authority"],
    "MoRTH": ["morth", "ministry of road transport", "road transport ministry"],
    "PMGSY": ["pmgsy", "pradhan mantri gram sadak", "rural road"],
    "PWD": ["pwd", "public works department", "state highway"],
    "Smart City": ["smart city", "smart cities", "urban infrastructure"],
    "BRO": ["bro", "border roads", "border road organisation"],
    "NHIDCL": ["nhidcl", "northeast highway"],
    "Municipal": ["municipal", "nagar palika", "nagar nigam", "ulb", "urban local body"],
}

TENDER_KEYWORDS = [
    "tender", "bid", "awarded", "loa", "letter of award", "contract awarded",
    "epc", "ham", "bot", "annuity", "work order", "road project awarded",
    "highway project", "construction awarded", "road contract",
]

WORK_TYPE_KEYWORDS = {
    "new_construction": ["new road", "greenfield", "new highway", "new expressway",
                         "construction of", "4-lane", "6-lane", "widening",
                         "lane expansion", "corridor"],
    "overlay": ["overlay", "resurfacing", "strengthening", "rehabilitation",
                "re-surfacing", "road restoration"],
    "maintenance": ["maintenance", "repair", "pothole", "restoration",
                    "patching", "patch work"],
    "dbm_bc": ["dbm", "dense bituminous macadam", "bituminous concrete",
               "bc layer", "hot mix", "asphalt", "bituminous", "bitumen"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE — Table creation + CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def _get_conn():
    from database import DB_PATH
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_infra_tables():
    """Create infra_* tables if they don't exist. Safe to call multiple times."""
    conn = _get_conn()
    try:
        cur = conn.cursor()

        cur.execute("""CREATE TABLE IF NOT EXISTS infra_news (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      TEXT UNIQUE,
            title           TEXT,
            summary         TEXT,
            source_url      TEXT,
            published_at    TEXT,
            state           TEXT,
            district        TEXT,
            city            TEXT,
            department      TEXT,
            category        TEXT,
            sentiment_score REAL DEFAULT 0,
            sentiment_label TEXT DEFAULT 'neutral',
            confidence      TEXT,
            tags            TEXT,
            fetched_at      TEXT
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS infra_budgets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            state           TEXT,
            fy_year         TEXT,
            budget_head     TEXT,
            allocation_cr   REAL DEFAULT 0,
            revised_cr      REAL DEFAULT 0,
            expenditure_cr  REAL DEFAULT 0,
            source_url      TEXT,
            fetched_at      TEXT
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS infra_demand_scores (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            state               TEXT,
            city                TEXT,
            period_start        TEXT,
            period_end          TEXT,
            demand_likelihood   TEXT,
            mt_min              REAL DEFAULT 0,
            mt_max              REAL DEFAULT 0,
            tender_signal_count INTEGER DEFAULT 0,
            budget_score        REAL DEFAULT 0,
            seasonal_factor     REAL DEFAULT 0,
            weather_factor      REAL DEFAULT 0,
            news_sentiment      REAL DEFAULT 0,
            composite_score     REAL DEFAULT 0,
            reason_codes        TEXT,
            computed_at         TEXT
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS infra_alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type      TEXT,
            priority        TEXT,
            state           TEXT,
            city            TEXT,
            title           TEXT,
            description     TEXT,
            source_url      TEXT,
            created_at      TEXT,
            status          TEXT DEFAULT 'new'
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS infra_sources (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name     TEXT UNIQUE,
            source_type     TEXT,
            last_success    TEXT,
            last_failure    TEXT,
            total_records   INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'unknown',
            health_score    REAL DEFAULT 50
        )""")

        # Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_news_state ON infra_news(state)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_news_pub ON infra_news(published_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_news_cat ON infra_news(category)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_news_aid ON infra_news(article_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_demand_state ON infra_demand_scores(state)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_alerts_prio ON infra_alerts(priority)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_alerts_status ON infra_alerts(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_infra_budgets_state ON infra_budgets(state)")

        conn.commit()
    finally:
        conn.close()


def _insert_news_batch(articles: List[dict]) -> int:
    """Insert parsed articles. Skips duplicates via article_id UNIQUE. Returns inserted count."""
    conn = _get_conn()
    inserted = 0
    try:
        cur = conn.cursor()
        for a in articles:
            try:
                cur.execute("""INSERT OR IGNORE INTO infra_news
                    (article_id, title, summary, source_url, published_at,
                     state, district, city, department, category,
                     sentiment_score, sentiment_label, confidence, tags, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    a["article_id"], a["title"], a.get("summary", ""),
                    a["source_url"], a["published_at"],
                    a.get("state"), a.get("district"), a.get("city"),
                    a.get("department"), a.get("category", "general"),
                    a.get("sentiment_score", 0), a.get("sentiment_label", "neutral"),
                    a.get("confidence", ""), a.get("tags", "[]"), a.get("fetched_at", _now()),
                ))
                if cur.rowcount > 0:
                    inserted += 1
            except Exception:
                continue
        conn.commit()
    finally:
        conn.close()
    return inserted


def _insert_demand_scores(scores: List[dict]) -> int:
    conn = _get_conn()
    inserted = 0
    try:
        cur = conn.cursor()
        for s in scores:
            cur.execute("""INSERT INTO infra_demand_scores
                (state, city, period_start, period_end, demand_likelihood,
                 mt_min, mt_max, tender_signal_count, budget_score,
                 seasonal_factor, weather_factor, news_sentiment,
                 composite_score, reason_codes, computed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                s["state"], s.get("city"), s["period_start"], s["period_end"],
                s["demand_likelihood"], s["mt_min"], s["mt_max"],
                s.get("tender_signal_count", 0), s.get("budget_score", 0),
                s.get("seasonal_factor", 0), s.get("weather_factor", 0),
                s.get("news_sentiment", 0), s.get("composite_score", 0),
                json.dumps(s.get("reason_codes", [])), s.get("computed_at", _now()),
            ))
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def _insert_infra_alert(alert: dict):
    conn = _get_conn()
    try:
        conn.execute("""INSERT INTO infra_alerts
            (alert_type, priority, state, city, title, description, source_url, created_at, status)
            VALUES (?,?,?,?,?,?,?,?,?)""", (
            alert["alert_type"], alert["priority"],
            alert.get("state"), alert.get("city"),
            alert["title"], alert["description"],
            alert.get("source_url", ""), _now(), "new",
        ))
        conn.commit()
    finally:
        conn.close()


def _update_source_health(source_name: str, source_type: str, success: bool, records: int):
    conn = _get_conn()
    try:
        now = _now()
        row = conn.execute("SELECT id, total_records, health_score FROM infra_sources WHERE source_name=?",
                           (source_name,)).fetchone()
        if row:
            new_total = (row["total_records"] or 0) + records
            if success:
                conn.execute("UPDATE infra_sources SET last_success=?, total_records=?, status='live', health_score=MIN(100, health_score+5) WHERE source_name=?",
                             (now, new_total, source_name))
            else:
                conn.execute("UPDATE infra_sources SET last_failure=?, status='failing', health_score=MAX(0, health_score-10) WHERE source_name=?",
                             (now, source_name))
        else:
            conn.execute("INSERT INTO infra_sources (source_name, source_type, last_success, last_failure, total_records, status, health_score) VALUES (?,?,?,?,?,?,?)",
                         (source_name, source_type, now if success else None, None if success else now, records, "live" if success else "failing", 80 if success else 30))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# GDELT DOC 2.0 API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_GEO_URL = "https://api.gdeltproject.org/api/v2/geo/geo"

GDELT_INFRA_QUERY = (
    '(highway OR "road construction" OR NHAI OR "national highway" '
    'OR expressway OR "road project" OR tender OR bitumen OR asphalt '
    'OR "infrastructure project" OR "road widening" OR PWD '
    'OR MoRTH OR PMGSY OR Bharatmala OR "road work") '
    'sourcecountry:IN'
)


def _gdelt_get(url: str, params: dict, max_retries: int = 3) -> Tuple[Any, Optional[str]]:
    """HTTP GET with exponential backoff for GDELT rate limits."""
    backoffs = [3, 10, 30]
    for attempt in range(max_retries):
        try:
            resp = _session.get(url, params=params, timeout=25)
            if resp.status_code == 429:
                wait = min(int(resp.headers.get("Retry-After", str(backoffs[attempt]))), 60)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                return None, f"HTTP {resp.status_code}"
            ct = resp.headers.get("Content-Type", "")
            if "json" in ct:
                return resp.json(), None
            return resp.text, None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(backoffs[attempt])
            else:
                return None, str(e)[:200]
    return None, "All retries exhausted"


def fetch_gdelt_articles(query: str = GDELT_INFRA_QUERY,
                         start_dt: str = None, end_dt: str = None,
                         max_records: int = 250) -> Tuple[List[dict], Optional[str]]:
    """Fetch articles from GDELT DOC 2.0 artlist mode."""
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": str(max_records),
        "format": "json",
        "sort": "DateDesc",
    }
    if start_dt:
        params["STARTDATETIME"] = start_dt
    if end_dt:
        params["ENDDATETIME"] = end_dt

    data, err = _gdelt_get(GDELT_DOC_URL, params)
    if err:
        return [], err
    if isinstance(data, dict):
        return data.get("articles", []), None
    if isinstance(data, list):
        return data, None
    return [], "Unexpected GDELT format"


def fetch_gdelt_timeline(query: str = GDELT_INFRA_QUERY,
                         start_dt: str = None, end_dt: str = None) -> Tuple[Any, Optional[str]]:
    """Fetch timeline volume data from GDELT."""
    params = {"query": query, "mode": "timelinevolinfo", "format": "json"}
    if start_dt:
        params["STARTDATETIME"] = start_dt
    if end_dt:
        params["ENDDATETIME"] = end_dt
    return _gdelt_get(GDELT_DOC_URL, params)


def fetch_gdelt_tone(query: str = GDELT_INFRA_QUERY,
                     start_dt: str = None, end_dt: str = None) -> Tuple[Any, Optional[str]]:
    """Fetch tone/sentiment data from GDELT."""
    params = {"query": query, "mode": "tonechart", "format": "json"}
    if start_dt:
        params["STARTDATETIME"] = start_dt
    if end_dt:
        params["ENDDATETIME"] = end_dt
    return _gdelt_get(GDELT_DOC_URL, params)


def fetch_gdelt_geo(query: str = GDELT_INFRA_QUERY) -> Tuple[List[dict], Optional[str]]:
    """Fetch geo-located events from GDELT GEO 2.0 (last 7 days)."""
    params = {"query": query, "mode": "pointdata", "format": "json"}
    data, err = _gdelt_get(GDELT_GEO_URL, params)
    if isinstance(data, dict):
        return data.get("features", data.get("data", [])), err
    return [], err


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS PARSER + LOCATION EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════════

def _article_id(url: str, title: str) -> str:
    raw = f"{url}|{title}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _extract_location(text: str) -> dict:
    """
    Extract {state, district, city} from text.
    Primary: spaCy NER (via nlp_extraction_engine). Fallback: keyword matching.
    """
    # ── spaCy NER path ──────────────────────────────────────────────────
    try:
        from nlp_extraction_engine import extract_entities
        ents = extract_entities(text)
        if ents.get("states") or ents.get("cities"):
            result = {"state": None, "district": None, "city": None}
            if ents["states"]:
                # Map NLP state name back to our canonical names
                nlp_state = ents["states"][0]
                for state_name in INDIAN_STATES:
                    if state_name.lower() == nlp_state.lower():
                        result["state"] = state_name
                        break
                else:
                    result["state"] = nlp_state
            if ents["cities"]:
                nlp_city = ents["cities"][0]
                result["city"] = nlp_city
                if not result["state"] and nlp_city in MAJOR_CITIES:
                    result["state"] = MAJOR_CITIES[nlp_city]
            return result
    except Exception:
        pass

    # ── Regex fallback (always works) ───────────────────────────────────
    text_lower = text.lower()
    result = {"state": None, "district": None, "city": None}

    # City match first (most specific)
    for city, state in MAJOR_CITIES.items():
        if city.lower() in text_lower:
            result["city"] = city
            result["state"] = state
            return result

    # State match
    for state_name, abbrs in INDIAN_STATES.items():
        if state_name.lower() in text_lower:
            result["state"] = state_name
            return result
        for abbr in abbrs:
            if re.search(r'\b' + re.escape(abbr) + r'\b', text):
                result["state"] = state_name
                return result

    return result


def _extract_department(text: str) -> Optional[str]:
    text_lower = text.lower()
    for dept, keywords in DEPT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return dept
    return None


def _detect_tender(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in TENDER_KEYWORDS)


def _detect_work_type(text: str) -> Optional[str]:
    text_lower = text.lower()
    for wtype, keywords in WORK_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return wtype
    return None


def _sentiment_label(tone: float, text: str = "") -> str:
    """
    Sentiment classification.
    Primary: HuggingFace sentiment (via nlp_extraction_engine). Fallback: GDELT tone.
    """
    if text:
        try:
            from nlp_extraction_engine import analyze_sentiment
            result = analyze_sentiment(text)
            if result.get("engine") != "none":
                return result["sentiment"]
        except Exception:
            pass
    # GDELT tone fallback
    if tone >= 2.0:
        return "positive"
    if tone <= -2.0:
        return "negative"
    return "neutral"


def parse_gdelt_article(raw: dict) -> Optional[dict]:
    """Parse one GDELT artlist article into infra_news schema."""
    url = raw.get("url", "")
    title = raw.get("title", "")
    if not title or not url:
        return None

    combined = f"{title} {raw.get('domain', '')}"
    location = _extract_location(combined)

    # GDELT tone: comma-separated "tone,pos_score,neg_score,polarity,..."
    tone_raw = raw.get("tone", "0")
    try:
        tone = float(str(tone_raw).split(",")[0])
    except (ValueError, IndexError):
        tone = 0.0

    is_tender = _detect_tender(title)
    work_type = _detect_work_type(title)
    department = _extract_department(title)

    tags = []
    if is_tender:
        tags.append("tender_signal")
    if work_type:
        tags.append(work_type)
    if department:
        tags.append(department.lower().replace(" ", "_"))

    if is_tender:
        category = "tender"
    elif any(kw in title.lower() for kw in ["budget", "allocation", "expenditure", "spending"]):
        category = "budget"
    elif any(kw in title.lower() for kw in ["delay", "protest", "litigation", "dispute", "cancel"]):
        category = "disruption"
    elif any(kw in title.lower() for kw in ["construction", "highway", "road", "expressway", "nhai"]):
        category = "infrastructure"
    else:
        category = "general"

    seen_date = raw.get("seendate", "")
    try:
        dt = datetime.datetime.strptime(seen_date[:14], "%Y%m%d%H%M%S")
        pub_ist = dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        pub_ist = _now()

    return {
        "article_id": _article_id(url, title),
        "title": title[:500],
        "summary": title[:500],
        "source_url": url[:500],
        "published_at": pub_ist,
        "state": location["state"],
        "district": location["district"],
        "city": location["city"],
        "department": department,
        "category": category,
        "sentiment_score": round(tone, 2),
        "sentiment_label": _sentiment_label(tone, text=title),
        "confidence": "gdelt_direct",
        "tags": json.dumps(tags),
        "fetched_at": _now(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BUDGET DATA — data.gov.in + static seed from road_budget_demand.py
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_budget_data_gov_in() -> dict:
    """Fetch highway budget data from data.gov.in (requires free API key)."""
    try:
        from api_hub_engine import HubCatalog
        key = HubCatalog.get_key("data_gov_in_highways")
    except Exception:
        key = ""

    if not key:
        return {"ok": False, "records": 0, "error": "No data.gov.in API key configured"}

    datasets = [
        {"id": "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69", "name": "NHAI Progress"},
        {"id": "9ef84268-d588-465a-a308-a864a43d0070", "name": "MoRTH Highway Length"},
    ]

    records = []
    for ds in datasets:
        try:
            url = f"https://api.data.gov.in/resource/{ds['id']}"
            resp = _session.get(url, params={"api-key": key, "format": "json", "limit": "500"}, timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for row in data.get("records", []):
                state = str(row.get("state", row.get("state_name", "All India"))).strip()
                records.append({
                    "state": state,
                    "fy_year": str(row.get("year", row.get("period", "2024-25"))),
                    "budget_head": ds["name"],
                    "allocation_cr": _safe_float(row, ["allocation", "budget_allocation", "total"]),
                    "revised_cr": _safe_float(row, ["revised", "revised_estimate"]),
                    "expenditure_cr": _safe_float(row, ["expenditure", "actual_expenditure"]),
                    "source_url": url,
                    "fetched_at": _now(),
                })
        except Exception:
            continue

    if records:
        conn = _get_conn()
        try:
            cur = conn.cursor()
            for r in records:
                cur.execute("""INSERT INTO infra_budgets
                    (state, fy_year, budget_head, allocation_cr, revised_cr,
                     expenditure_cr, source_url, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (r["state"], r["fy_year"], r["budget_head"],
                     r["allocation_cr"], r["revised_cr"], r["expenditure_cr"],
                     r["source_url"], r["fetched_at"]))
            conn.commit()
        finally:
            conn.close()
        _update_source_health("data.gov.in", "budget_api", True, len(records))
        return {"ok": True, "records": len(records)}

    return {"ok": False, "records": 0, "error": "No budget records fetched"}


def seed_budget_from_static() -> int:
    """Seed infra_budgets with STATE_DATA from road_budget_demand.py."""
    try:
        from command_intel.road_budget_demand import STATE_DATA
    except Exception:
        return 0

    conn = _get_conn()
    inserted = 0
    try:
        cur = conn.cursor()
        for _, row in STATE_DATA.iterrows():
            try:
                cur.execute("""INSERT OR IGNORE INTO infra_budgets
                    (state, fy_year, budget_head, allocation_cr, revised_cr,
                     expenditure_cr, source_url, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?)""", (
                    str(row["State"]), "2024-25", "Central+State Combined",
                    float(row.get("Total_Budget_Cr", 0)),
                    float(row.get("Central_Cr", 0)),
                    float(row.get("State_Cr", 0)),
                    "road_budget_demand.py (PRS/MoRTH/IBEF)", _now(),
                ))
                if cur.rowcount > 0:
                    inserted += 1
            except Exception:
                continue
        conn.commit()
    finally:
        conn.close()
    return inserted


def _safe_float(row: dict, keys: list) -> float:
    for k in keys:
        v = row.get(k)
        if v is not None:
            try:
                return float(str(v).replace(",", ""))
            except (ValueError, TypeError):
                pass
    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DEMAND ESTIMATION MODEL
# ═══════════════════════════════════════════════════════════════════════════════

# Month-name index for seasonal lookup
_MONTH_NAMES = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}


def _get_seasonal_factor(state: str, month: int) -> float:
    """Get seasonal construction factor using road_budget_demand.py data."""
    try:
        from command_intel.road_budget_demand import MONTHLY_DEMAND_INDEX, STATE_MONSOON_MONTHS
    except Exception:
        return 0.8

    m = _MONTH_NAMES.get(month, "Jan")
    monsoon = STATE_MONSOON_MONTHS.get(state, {"off": [], "partial": []})

    if m in monsoon.get("off", []):
        return 0.10
    if m in monsoon.get("partial", []):
        return 0.50
    return MONTHLY_DEMAND_INDEX.get(m, 1.0)


def _get_weather_factor(state: str) -> float:
    """Get weather factor from tbl_weather.json."""
    try:
        with open(BASE / "tbl_weather.json", "r", encoding="utf-8") as f:
            weather = json.load(f)
        for w in weather:
            rain = w.get("rain_mm", 0)
            if rain and float(rain) > 5:
                return 0.4
        return 0.85
    except Exception:
        return 0.7


def _get_budget_infra_score(state: str) -> float:
    """Budget infra score (0-100) for a state."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT SUM(allocation_cr) as total_alloc, SUM(expenditure_cr) as total_exp FROM infra_budgets WHERE state=?",
            (state,)).fetchone()
        if row and row["total_alloc"]:
            alloc = float(row["total_alloc"] or 0)
            # Score based on allocation magnitude (max 50k Cr = 50 pts)
            alloc_score = min(50, alloc / 1000)
            # Expenditure ratio bonus (max 30 pts)
            exp = float(row["total_exp"] or 0)
            exp_ratio = (exp / alloc * 100) if alloc > 0 else 0
            exp_score = min(30, exp_ratio / 3.33)
            return round(alloc_score + exp_score + 10, 1)  # +10 base
    except Exception:
        pass
    finally:
        conn.close()
    return 30.0


def _get_tender_signal_count(state: str, days: int = 30) -> int:
    conn = _get_conn()
    try:
        cutoff = (datetime.datetime.now(IST) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM infra_news WHERE state=? AND category='tender' AND published_at>=?",
            (state, cutoff)).fetchone()
        return int(row["cnt"]) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def _get_news_sentiment(state: str, days: int = 30) -> float:
    conn = _get_conn()
    try:
        cutoff = (datetime.datetime.now(IST) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT AVG(sentiment_score) as avg_s FROM infra_news WHERE state=? AND published_at>=?",
            (state, cutoff)).fetchone()
        return round(float(row["avg_s"] or 0), 2) if row else 0.0
    except Exception:
        return 0.0
    finally:
        conn.close()


def _get_state_base_mt(state: str) -> int:
    """Get annual base bitumen MT estimate from road_budget_demand.py."""
    try:
        from command_intel.road_budget_demand import STATE_DATA
        match = STATE_DATA[STATE_DATA["State"] == state]
        if not match.empty:
            return int(match.iloc[0]["Est_Bitumen_MT"])
    except Exception:
        pass
    return 50000  # Default for unmapped states


def compute_demand_score(state: str, city: str = None, window_days: int = 30) -> dict:
    """
    Compute demand estimation for a state.

    Weighted composite:
      tender_signal_count  (25%)
      budget_infra_score   (25%)
      seasonal_factor      (20%)
      weather_factor       (10%)
      news_sentiment       (20%)

    Returns: {state, demand_likelihood, mt_min, mt_max, composite_score, reason_codes, ...}
    """
    now = datetime.datetime.now(IST)
    month = now.month

    tender_count = _get_tender_signal_count(state, window_days)
    budget_score = _get_budget_infra_score(state)
    seasonal = _get_seasonal_factor(state, month)
    weather = _get_weather_factor(state)
    sentiment = _get_news_sentiment(state, window_days)

    # Normalize to 0-100
    tender_norm = min(100, tender_count * 10)
    budget_norm = budget_score
    seasonal_norm = min(100, seasonal * 100)
    weather_norm = weather * 100
    sentiment_norm = max(0, min(100, 50 + sentiment * 5))

    composite = (
        tender_norm * 0.25 +
        budget_norm * 0.25 +
        seasonal_norm * 0.20 +
        weather_norm * 0.10 +
        sentiment_norm * 0.20
    )
    composite = max(0, min(100, round(composite, 1)))

    if composite >= 65:
        likelihood = "High"
    elif composite >= 35:
        likelihood = "Medium"
    else:
        likelihood = "Low"

    # MT estimation
    base_annual_mt = _get_state_base_mt(state)
    monthly_base = base_annual_mt / 12
    factor = composite / 60  # Normalize around 1.0 at score=60
    period_months = window_days / 30
    mt_estimate = monthly_base * factor * period_months
    mt_min = int(mt_estimate * 0.7)
    mt_max = int(mt_estimate * 1.3)

    # Reason codes
    reasons = []
    if tender_count >= 5:
        reasons.append(f"High tender activity ({tender_count} signals)")
    elif tender_count >= 2:
        reasons.append(f"Moderate tender activity ({tender_count} signals)")
    if budget_score >= 60:
        reasons.append("Strong budget allocation")
    elif budget_score >= 40:
        reasons.append("Moderate budget support")
    if seasonal >= 0.9:
        reasons.append("Peak construction season")
    elif seasonal <= 0.3:
        reasons.append("Monsoon / off-season")
    if weather >= 0.7:
        reasons.append("Favorable weather window")
    elif weather <= 0.4:
        reasons.append("Weather disruption risk")
    if sentiment >= 1.5:
        reasons.append("Positive news sentiment")
    elif sentiment <= -1.5:
        reasons.append("Negative news sentiment")

    return {
        "state": state,
        "city": city,
        "period_start": now.strftime("%Y-%m-%d"),
        "period_end": (now + datetime.timedelta(days=window_days)).strftime("%Y-%m-%d"),
        "demand_likelihood": likelihood,
        "mt_min": mt_min,
        "mt_max": mt_max,
        "tender_signal_count": tender_count,
        "budget_score": budget_score,
        "seasonal_factor": round(seasonal, 2),
        "weather_factor": round(weather, 2),
        "news_sentiment": sentiment,
        "composite_score": composite,
        "reason_codes": reasons,
        "computed_at": _now(),
    }


def compute_all_state_scores(window_days: int = 30) -> List[dict]:
    """Compute demand scores for all states in INDIAN_STATES."""
    scores = []
    for state in INDIAN_STATES:
        try:
            score = compute_demand_score(state, window_days=window_days)
            scores.append(score)
        except Exception:
            continue
    return sorted(scores, key=lambda s: s["composite_score"], reverse=True)


def get_target_rankings(window_days: int = 30, top_n: int = 10) -> List[dict]:
    """Top N states ranked by demand score for given window."""
    all_scores = compute_all_state_scores(window_days)
    return all_scores[:top_n]


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_demand_alerts() -> List[dict]:
    """Scan for demand intelligence alerts."""
    alerts = []
    conn = _get_conn()
    try:
        now = datetime.datetime.now(IST)
        cutoff_7d = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        cutoff_30d = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

        # 1. Tender spike: >5 tender articles for a state in 7 days
        rows = conn.execute("""
            SELECT state, COUNT(*) as cnt FROM infra_news
            WHERE category='tender' AND published_at>=? AND state IS NOT NULL
            GROUP BY state HAVING cnt >= 5
        """, (cutoff_7d,)).fetchall()
        for r in rows:
            alerts.append({
                "alert_type": "tender_spike",
                "priority": "P1" if r["cnt"] >= 10 else "P2",
                "state": r["state"],
                "title": f"Tender spike in {r['state']}: {r['cnt']} signals in 7 days",
                "description": f"{r['cnt']} infrastructure tender articles detected in {r['state']} over the last 7 days, indicating increased procurement activity.",
            })

        # 2. Negative news risk: >3 disruption articles in 7 days
        rows = conn.execute("""
            SELECT state, COUNT(*) as cnt FROM infra_news
            WHERE category='disruption' AND published_at>=? AND state IS NOT NULL
            GROUP BY state HAVING cnt >= 3
        """, (cutoff_7d,)).fetchall()
        for r in rows:
            alerts.append({
                "alert_type": "negative_risk",
                "priority": "P1",
                "state": r["state"],
                "title": f"Disruption risk in {r['state']}: {r['cnt']} negative signals",
                "description": f"{r['cnt']} disruption articles (delays, litigation, protests) detected in {r['state']}.",
            })

        # 3. Budget change detection (would need multi-period data)
        # Simplified: flag states with very low budget scores
        for state in list(INDIAN_STATES.keys())[:15]:  # Top 15 states
            score = _get_budget_infra_score(state)
            if score < 20:
                alerts.append({
                    "alert_type": "budget_concern",
                    "priority": "P2",
                    "state": state,
                    "title": f"Low budget score for {state}: {score}/100",
                    "description": f"Budget infrastructure score is low ({score}/100). May indicate funding gaps.",
                })

    except Exception:
        pass
    finally:
        conn.close()

    # Insert new alerts (skip if similar recent alert exists)
    for alert in alerts:
        try:
            existing = conn if False else _get_conn()
            try:
                row = existing.execute(
                    "SELECT id FROM infra_alerts WHERE alert_type=? AND state=? AND status='new' AND created_at>=?",
                    (alert["alert_type"], alert.get("state"), (now - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"))
                ).fetchone()
                if not row:
                    _insert_infra_alert(alert)
            finally:
                existing.close()
        except Exception:
            pass

    return alerts


# ═══════════════════════════════════════════════════════════════════════════════
# DATA RETRIEVAL FOR DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def get_heatmap_data() -> List[dict]:
    """State-level demand scores for heatmap display."""
    return compute_all_state_scores(window_days=30)


def get_live_feed(limit: int = 50, state: str = None, category: str = None) -> List[dict]:
    """Recent infra_news articles."""
    conn = _get_conn()
    try:
        sql = "SELECT * FROM infra_news WHERE 1=1"
        params = []
        if state:
            sql += " AND state=?"
            params.append(state)
        if category:
            sql += " AND category=?"
            params.append(category)
        sql += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_infra_alerts(status: str = "new", limit: int = 50) -> List[dict]:
    """Get demand intelligence alerts."""
    conn = _get_conn()
    try:
        if status:
            rows = conn.execute("SELECT * FROM infra_alerts WHERE status=? ORDER BY created_at DESC LIMIT ?",
                                (status, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM infra_alerts ORDER BY created_at DESC LIMIT ?",
                                (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_source_health() -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM infra_sources ORDER BY source_name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trend_data(months: int = 24) -> dict:
    """Monthly aggregated article counts + sentiment for trend charts."""
    conn = _get_conn()
    try:
        cutoff = (datetime.datetime.now(IST) - datetime.timedelta(days=months * 30)).strftime("%Y-%m-%d")
        rows = conn.execute("""
            SELECT substr(published_at, 1, 7) as month,
                   COUNT(*) as total,
                   SUM(CASE WHEN category='tender' THEN 1 ELSE 0 END) as tenders,
                   SUM(CASE WHEN category='disruption' THEN 1 ELSE 0 END) as disruptions,
                   AVG(sentiment_score) as avg_sentiment
            FROM infra_news WHERE published_at >= ?
            GROUP BY month ORDER BY month
        """, (cutoff,)).fetchall()
        return {"months": [dict(r) for r in rows]}
    finally:
        conn.close()


def get_news_stats() -> dict:
    """Quick stats for the dashboard header."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) as c FROM infra_news").fetchone()["c"]
        states_covered = conn.execute("SELECT COUNT(DISTINCT state) as c FROM infra_news WHERE state IS NOT NULL").fetchone()["c"]
        tenders = conn.execute("SELECT COUNT(*) as c FROM infra_news WHERE category='tender'").fetchone()["c"]
        last_fetch = conn.execute("SELECT MAX(fetched_at) as m FROM infra_news").fetchone()["m"]
        return {"total_articles": total, "states_covered": states_covered,
                "tender_signals": tenders, "last_fetch": last_fetch or "Never"}
    except Exception:
        return {"total_articles": 0, "states_covered": 0, "tender_signals": 0, "last_fetch": "Never"}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION — Backfill + Live Update
# ═══════════════════════════════════════════════════════════════════════════════

def run_backfill(months: int = 24, progress_callback=None) -> dict:
    """
    Backfill last N months of GDELT data + seed budget data.
    progress_callback(pct, msg) if provided.
    """
    init_infra_tables()
    result = {"months_processed": 0, "articles_fetched": 0, "articles_inserted": 0,
              "budget_seeded": 0, "scores_computed": 0, "errors": []}

    now = datetime.datetime.now(IST)
    total_steps = months + 2  # months + budget + scores

    # 1. Seed budget from static data
    if progress_callback:
        progress_callback(5, "Seeding budget baseline data...")
    budget_count = seed_budget_from_static()
    result["budget_seeded"] = budget_count

    # 2. Try data.gov.in budget fetch
    try:
        budget_result = fetch_budget_data_gov_in()
        if budget_result.get("ok"):
            result["budget_seeded"] += budget_result["records"]
    except Exception as e:
        result["errors"].append(f"data.gov.in: {str(e)[:100]}")

    # 3. GDELT month-by-month backfill
    for i in range(months):
        month_offset = months - i
        start = now - datetime.timedelta(days=month_offset * 30)
        end = now - datetime.timedelta(days=(month_offset - 1) * 30)
        start_str = start.strftime("%Y%m%d000000")
        end_str = end.strftime("%Y%m%d000000")

        pct = int(10 + (i / months) * 70)
        if progress_callback:
            progress_callback(pct, f"Fetching GDELT: {start.strftime('%b %Y')}...")

        try:
            articles_raw, err = fetch_gdelt_articles(
                start_dt=start_str, end_dt=end_str, max_records=250)
            if err:
                result["errors"].append(f"GDELT {start.strftime('%Y-%m')}: {err}")
                _update_source_health("GDELT DOC", "news_api", False, 0)
                time.sleep(2)
                continue

            parsed = [a for a in (parse_gdelt_article(r) for r in articles_raw) if a]
            result["articles_fetched"] += len(parsed)

            inserted = _insert_news_batch(parsed)
            result["articles_inserted"] += inserted
            result["months_processed"] += 1

            _update_source_health("GDELT DOC", "news_api", True, inserted)
            time.sleep(1)  # Rate limit courtesy

        except Exception as e:
            result["errors"].append(f"Month {i}: {str(e)[:100]}")
            time.sleep(2)

    # 4. Compute demand scores
    if progress_callback:
        progress_callback(85, "Computing demand scores...")
    for window in [7, 15, 30]:
        scores = compute_all_state_scores(window)
        _insert_demand_scores(scores)
        result["scores_computed"] += len(scores)

    # 5. Generate alerts
    if progress_callback:
        progress_callback(95, "Generating alerts...")
    generate_demand_alerts()

    if progress_callback:
        progress_callback(100, "Backfill complete!")

    return result


def run_live_update() -> dict:
    """Incremental update: fetch recent GDELT + recompute scores + alerts."""
    init_infra_tables()
    result = {"articles_fetched": 0, "articles_inserted": 0,
              "scores_computed": 0, "alerts_generated": 0, "errors": []}

    # 1. Fetch recent GDELT articles (last 3 months rolling window)
    try:
        articles_raw, err = fetch_gdelt_articles(max_records=250)
        if err:
            result["errors"].append(f"GDELT: {err}")
            _update_source_health("GDELT DOC", "news_api", False, 0)
        else:
            parsed = [a for a in (parse_gdelt_article(r) for r in articles_raw) if a]
            result["articles_fetched"] = len(parsed)
            inserted = _insert_news_batch(parsed)
            result["articles_inserted"] = inserted
            _update_source_health("GDELT DOC", "news_api", True, inserted)
    except Exception as e:
        result["errors"].append(f"GDELT fetch: {str(e)[:100]}")

    # 2. Fetch GDELT GEO (last 7 days)
    try:
        geo_data, err = fetch_gdelt_geo()
        if not err and geo_data:
            _update_source_health("GDELT GEO", "geo_api", True, len(geo_data))
    except Exception:
        pass

    # 3. Recompute demand scores
    try:
        for window in [7, 15, 30]:
            scores = compute_all_state_scores(window)
            _insert_demand_scores(scores)
            result["scores_computed"] += len(scores)
    except Exception as e:
        result["errors"].append(f"Scoring: {str(e)[:100]}")

    # 4. Generate alerts
    try:
        alerts = generate_demand_alerts()
        result["alerts_generated"] = len(alerts)
    except Exception:
        pass

    return result
