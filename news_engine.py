"""
News Engine — PPS Anantams Logistics Dashboard
================================================
Multi-source news aggregator for business intelligence.

Regions: International | Domestic (India)
Sources: RSS feeds (free, no key) + optional NewsAPI / GNews (free-tier keys)
Language: English + Hindi

Auto-fetch every 10 minutes via background thread.
All timestamps in IST (Asia/Kolkata = UTC+5:30).
All dates in DD-MM-YYYY format.

Storage (JSON files in news_data/):
  articles.json       — all articles (max 5,000)
  fetch_log.json      — source fetch history (max 2,000)
  change_history.json — audit trail (max 5,000)
  news_sources.json   — live source status
  saved_articles.json — user-saved articles

DB Schema equivalent:
  news_articles:     article_id, region, headline, summary, source_name,
                     source_url, published_at_ist, fetched_at_ist, tags,
                     impact_score, duplicate_cluster_id, sentiment, status, language
  news_fetch_log:    fetch_id, source_id, start_time_ist, end_time_ist,
                     records_fetched, failures, error_message, status
  news_change_history: timestamp_ist, change_type, article_id, old_value,
                        new_value, reason, actor
"""

from __future__ import annotations

import datetime
import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Optional
import difflib

BASE_DIR   = Path(__file__).parent
NEWS_DIR   = BASE_DIR / "news_data"
NEWS_DIR.mkdir(exist_ok=True)

ARTICLES_FILE   = NEWS_DIR / "articles.json"
FETCH_LOG_FILE  = NEWS_DIR / "fetch_log.json"
CHANGE_FILE     = NEWS_DIR / "change_history.json"
SOURCES_FILE    = NEWS_DIR / "news_sources.json"
SAVED_FILE      = NEWS_DIR / "saved_articles.json"
NEWS_CFG_FILE   = BASE_DIR / "news_config.json"

REFRESH_INTERVAL_MIN = 10        # default refresh
IST_OFFSET           = datetime.timedelta(hours=5, minutes=30)
MAX_ARTICLES         = 5_000
MAX_LOG              = 2_000
DEDUP_THRESHOLD      = 0.72      # SequenceMatcher ratio for duplicate detection

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE REGISTRY — 14 sources: 12 RSS (free) + 2 optional API
# ══════════════════════════════════════════════════════════════════════════════

NEWS_SOURCES: list[dict] = [
    # ── INTERNATIONAL RSS ──────────────────────────────────────────────────
    {
        "source_id":           "oilprice_rss",
        "name":                "OilPrice.com",
        "type":                "RSS",
        "region":              "International",
        "feed_url":            "https://oilprice.com/rss/main",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 10,
        "tags_hint":           ["crude_oil", "brent", "wti", "opec"],
        "reliability":         88,
        "language":            "en",
    },
    {
        "source_id":           "eia_rss",
        "name":                "EIA — Today in Energy",
        "type":                "RSS",
        "region":              "International",
        "feed_url":            "https://www.eia.gov/rss/todayinenergy.xml",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 60,
        "tags_hint":           ["crude_oil", "refinery", "supply_chain"],
        "reliability":         92,
        "language":            "en",
    },
    {
        "source_id":           "rigzone_rss",
        "name":                "Rigzone",
        "type":                "RSS",
        "region":              "International",
        "feed_url":            "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 15,
        "tags_hint":           ["crude_oil", "refinery", "logistics"],
        "reliability":         82,
        "language":            "en",
    },
    {
        "source_id":           "reuters_biz_rss",
        "name":                "Reuters — Business",
        "type":                "RSS",
        "region":              "International",
        "feed_url":            "https://feeds.reuters.com/reuters/businessNews",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 10,
        "tags_hint":           ["crude_oil", "opec", "middle_east", "forex", "sanctions"],
        "reliability":         95,
        "language":            "en",
    },
    {
        "source_id":           "cnbc_energy_rss",
        "name":                "CNBC — Energy",
        "type":                "RSS",
        "region":              "International",
        "feed_url":            "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 10,
        "tags_hint":           ["crude_oil", "forex", "logistics"],
        "reliability":         88,
        "language":            "en",
    },
    {
        "source_id":           "mw_commodities_rss",
        "name":                "MarketWatch — Commodities",
        "type":                "RSS",
        "region":              "International",
        "feed_url":            "https://feeds.marketwatch.com/marketwatch/commodities/",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 10,
        "tags_hint":           ["crude_oil", "brent", "wti", "forex"],
        "reliability":         85,
        "language":            "en",
    },
    # ── DOMESTIC INDIA RSS ─────────────────────────────────────────────────
    {
        "source_id":           "pib_infra_rss",
        "name":                "PIB India — Infrastructure",
        "type":                "RSS",
        "region":              "Domestic",
        "feed_url":            "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 30,
        "tags_hint":           ["nhai", "morth", "pmgsy", "budget", "funding"],
        "reliability":         96,
        "language":            "en",
    },
    {
        "source_id":           "et_infra_rss",
        "name":                "Economic Times — Infrastructure",
        "type":                "RSS",
        "region":              "Domestic",
        "feed_url":            "https://economictimes.indiatimes.com/industry/indl-goods/svs/construction/rssfeeds/21048456.cms",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 10,
        "tags_hint":           ["nhai", "pwd", "tender", "highway", "bitumen"],
        "reliability":         89,
        "language":            "en",
    },
    {
        "source_id":           "bs_economy_rss",
        "name":                "Business Standard — Economy",
        "type":                "RSS",
        "region":              "Domestic",
        "feed_url":            "https://www.business-standard.com/rss/economy-policy-news.rss",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 10,
        "tags_hint":           ["budget", "funding", "policy", "nhai"],
        "reliability":         90,
        "language":            "en",
    },
    {
        "source_id":           "mint_rss",
        "name":                "Mint — Top News",
        "type":                "RSS",
        "region":              "Domestic",
        "feed_url":            "https://www.livemint.com/rss/news",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 10,
        "tags_hint":           ["nhai", "highway", "budget", "tender"],
        "reliability":         87,
        "language":            "en",
    },
    # ── HINDI RSS ──────────────────────────────────────────────────────────
    {
        "source_id":           "ndtv_hindi_rss",
        "name":                "NDTV Khabar (Hindi)",
        "type":                "RSS",
        "region":              "Domestic",
        "feed_url":            "https://khabar.ndtv.com/rss/all",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 15,
        "tags_hint":           ["nhai", "highway", "budget", "infrastructure"],
        "reliability":         82,
        "language":            "hi",
    },
    {
        "source_id":           "bhaskar_biz_rss",
        "name":                "Dainik Bhaskar (Hindi)",
        "type":                "RSS",
        "region":              "Domestic",
        "feed_url":            "https://www.bhaskar.com/rss-feed/1061/",
        "auth_type":           "none",
        "free_limit":          "Unlimited",
        "refresh_interval_min": 15,
        "tags_hint":           ["nhai", "highway", "infrastructure"],
        "reliability":         78,
        "language":            "hi",
    },
    # ── OPTIONAL API SOURCES (require free-tier API keys) ─────────────────
    {
        "source_id":           "newsapi_intl",
        "name":                "NewsAPI — International Energy",
        "type":                "API",
        "region":              "International",
        "endpoint":            "https://newsapi.org/v2/everything",
        "auth_type":           "key",
        "env_key":             "NEWSAPI_KEY",
        "cfg_key":             "newsapi_key",
        "free_limit":          "100 req/day",
        "refresh_interval_min": 60,
        "query":               "crude oil OR Brent crude OR OPEC OR oil sanctions OR tanker OR freight rates",
        "tags_hint":           ["crude_oil", "opec", "logistics", "sanctions"],
        "reliability":         90,
        "language":            "en",
        "setup_note":          "Free key at newsapi.org — 100 req/day",
    },
    {
        "source_id":           "gnews_domestic",
        "name":                "GNews — India Roads",
        "type":                "API",
        "region":              "Domestic",
        "endpoint":            "https://gnews.io/api/v4/search",
        "auth_type":           "key",
        "env_key":             "GNEWS_KEY",
        "cfg_key":             "gnews_key",
        "free_limit":          "100 req/day",
        "refresh_interval_min": 60,
        "query":               "NHAI road construction bitumen highway India tender",
        "tags_hint":           ["nhai", "highway", "tender", "bitumen"],
        "reliability":         82,
        "language":            "en",
        "setup_note":          "Free key at gnews.io — 100 req/day",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# KEYWORD TAXONOMY
# ══════════════════════════════════════════════════════════════════════════════

INTL_TAG_KEYWORDS: dict[str, list[str]] = {
    "crude_oil":    ["crude oil", "crude", "brent", "wti", "nymex", "barrel", "petroleum",
                     "oil price", "light crude", "sweet crude", "heavy crude", "oil market"],
    "opec":         ["opec", "opec+", "production cut", "oil cartel", "saudi aramco",
                     "saudi arabia oil", "uae oil", "russia oil", "oil output", "oil quota"],
    "middle_east":  ["middle east", "red sea", "strait of hormuz", "iraq", "iran", "israel",
                     "gaza", "persian gulf", "houthi", "suez canal", "arabian sea"],
    "sanctions":    ["sanctions", "embargo", "export ban", "russian oil", "iran sanctions",
                     "oil ban", "western sanctions", "asset freeze"],
    "forex":        ["usd/inr", "rupee", "dollar", "dxy", "federal reserve", "fed rate",
                     "interest rate", "forex", "exchange rate", "currency", "rbi", "usdinr"],
    "logistics":    ["shipping", "freight", "tanker", "vlcc", "port", "logistics",
                     "supply chain", "maritime", "cargo", "freight rate", "shipping cost"],
    "refinery":     ["refinery", "refining", "cracking", "refinery outage", "shutdown",
                     "refinery capacity", "crude run", "iocl", "bpcl", "hpcl", "mrpl"],
    "supply_chain": ["supply disruption", "inventory", "stockpile", "strategic reserve",
                     "supply chain", "global supply", "oil storage", "pipeline"],
}

DOMESTIC_TAG_KEYWORDS: dict[str, list[str]] = {
    "nhai":         ["nhai", "national highway", "highway project", "nh-", "nh ",
                     "highway award", "bharatmala", "nhai tender", "highway authority"],
    "morth":        ["morth", "ministry of road transport", "gadkari", "highway ministry",
                     "transport ministry", "road transport"],
    "pmgsy":        ["pmgsy", "pradhan mantri gram sadak", "rural road", "village road",
                     "gram sadak", "nrrda", "rural connectivity"],
    "pwd":          ["pwd", "public works", "state highway", "state road", "road department",
                     "state pwd", "mdrd", "sh-"],
    "tender":       ["tender", "bid", "loa", "letter of award", "contract awarded",
                     "epc contract", "ham model", "toll road", "annuity", "work order"],
    "budget":       ["road budget", "infrastructure budget", "highway allocation",
                     "road fund", "crif", "cess", "infrastructure outlay", "budgetary"],
    "bitumen":      ["bitumen", "asphalt", "vg-30", "vg-40", "pmb", "bituminous",
                     "road surface", "hot mix", "dbm", "road tar"],
    "highway":      ["highway", "expressway", "corridor", "ring road", "bypass", "flyover",
                     "bridge", "tunnel", "interchange", "cloverleaf"],
    "funding":      ["funding approved", "allocation", "sanctioned", "investment",
                     "capex", "infrastructure spending", "approved outlay"],
    "policy":       ["policy", "gst", "vat", "circular", "notification", "amendment",
                     "regulation", "compliance", "approval"],
}

BREAKING_KEYWORDS = [
    "breaking", "urgent", "crash", "record high", "record low", "surge", "plunge",
    "halt", "closure", "emergency", "attack", "war", "sanctions imposed", "ban",
    "shutdown", "disruption", "explosion", "fire", "force majeure", "act of god",
]

SOURCE_RELIABILITY: dict[str, int] = {
    "PIB India — Infrastructure": 96,
    "Reuters — Business":         95,
    "EIA — Today in Energy":      92,
    "Business Standard — Economy": 90,
    "NewsAPI — International Energy": 90,
    "Economic Times — Infrastructure": 89,
    "CNBC — Energy":              88,
    "OilPrice.com":               88,
    "Mint — Top News":            87,
    "Rigzone":                    82,
    "GNews — India Roads":        82,
    "NDTV Khabar (Hindi)":        82,
    "MarketWatch — Commodities":  85,
    "Dainik Bhaskar (Hindi)":     78,
}

# ══════════════════════════════════════════════════════════════════════════════
# DEMO ARTICLES (shown before live feed is available)
# ══════════════════════════════════════════════════════════════════════════════

DEMO_ARTICLES: list[dict] = [
    {
        "article_id": "demo001", "region": "International",
        "headline": "Brent Crude Rises 1.2% to ₹ 84.5/bbl on Red Sea Shipping Disruptions",
        "summary": "Brent crude futures climbed 1.2% to ₹ 84.50 per barrel on Thursday after Houthi attacks on commercial vessels in the Red Sea disrupted key shipping lanes. VLCC tanker freight rates rose 18% week-on-week as operators rerouted ships around the Cape of Good Hope, adding 10–14 days to voyage times.",
        "source_name": "OilPrice.com", "source_url": "https://oilprice.com",
        "published_at_ist": "01-03-2026 09:30 IST", "fetched_at_ist": "01-03-2026 09:32 IST",
        "tags": ["crude_oil", "brent", "logistics", "middle_east"],
        "impact_score": 87, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "negative", "status": "new", "language": "en",
    },
    {
        "article_id": "demo002", "region": "International",
        "headline": "OPEC+ Agrees to Extend Production Cuts Through Q2 2026; Brent Holds Near ₹ 83",
        "summary": "OPEC+ ministers agreed in a virtual meeting to maintain existing production cuts of 2.2 million barrels per day through June 2026. Saudi Arabia and Russia reiterated commitment to market stability. The decision kept Brent crude near ₹ 83/bbl, providing support amid global demand uncertainty.",
        "source_name": "Reuters — Business", "source_url": "https://www.reuters.com",
        "published_at_ist": "01-03-2026 11:15 IST", "fetched_at_ist": "01-03-2026 11:17 IST",
        "tags": ["opec", "crude_oil", "brent"],
        "impact_score": 82, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "neutral", "status": "new", "language": "en",
    },
    {
        "article_id": "demo003", "region": "International",
        "headline": "USD/INR Weakens to 87.2 as Federal Reserve Holds Rates; RBI Intervenes",
        "summary": "The Indian rupee weakened to 87.20 against the US dollar after the Federal Reserve held interest rates steady, signalling a cautious approach to rate cuts. The RBI intervened in the forex market to prevent excessive depreciation. A weaker rupee raises bitumen import costs by approximately ₹800–1,200/MT.",
        "source_name": "Mint — Top News", "source_url": "https://www.livemint.com",
        "published_at_ist": "01-03-2026 13:45 IST", "fetched_at_ist": "01-03-2026 13:47 IST",
        "tags": ["forex", "usd", "usdinr"],
        "impact_score": 85, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "negative", "status": "new", "language": "en",
    },
    {
        "article_id": "demo004", "region": "Domestic",
        "headline": "NHAI Awards ₹3,200 Cr Highway Package in Rajasthan Under Bharatmala Phase-I",
        "summary": "The National Highways Authority of India (NHAI) awarded a ₹3,200 crore EPC contract for a 87-km stretch in Rajasthan under the Bharatmala Pariyojana Phase-I programme. The project includes a 4-lane highway with 2 major bridges and 14 minor bridges. Estimated bitumen requirement: 23,000–28,000 MT over 30 months.",
        "source_name": "Economic Times — Infrastructure", "source_url": "https://economictimes.indiatimes.com",
        "published_at_ist": "01-03-2026 10:00 IST", "fetched_at_ist": "01-03-2026 10:02 IST",
        "tags": ["nhai", "tender", "highway", "bitumen"],
        "impact_score": 91, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "positive", "status": "new", "language": "en",
    },
    {
        "article_id": "demo005", "region": "Domestic",
        "headline": "MoRTH Announces ₹2.78 Lakh Crore Road Infrastructure Allocation for FY2026-27",
        "summary": "The Ministry of Road Transport & Highways (MoRTH) announced a record ₹2.78 lakh crore budget allocation for road infrastructure development in FY2026-27. The allocation includes ₹1.68 lakh crore for NHAI, ₹28,000 crore for state highway development (CRIF), and ₹19,000 crore for PMGSY Phase-IV.",
        "source_name": "PIB India — Infrastructure", "source_url": "https://pib.gov.in",
        "published_at_ist": "01-03-2026 16:00 IST", "fetched_at_ist": "01-03-2026 16:02 IST",
        "tags": ["morth", "budget", "nhai", "pmgsy", "funding"],
        "impact_score": 95, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "positive", "status": "new", "language": "en",
    },
    {
        "article_id": "demo006", "region": "Domestic",
        "headline": "IOCL Raises Bitumen VG-30 Price by ₹500/MT Effective 16-02-2026; HPCL Follows",
        "summary": "Indian Oil Corporation (IOCL) revised its bitumen VG-30 price upward by ₹500/MT effective 16 February 2026. The new ex-Koyali basic price stands at ₹48,302/MT. HPCL Bhatinda also revised prices by ₹500/MT to ₹46,390/MT. The revision aligns with rising Brent crude and higher naphtha crack spreads.",
        "source_name": "Business Standard — Economy", "source_url": "https://www.business-standard.com",
        "published_at_ist": "16-02-2026 09:00 IST", "fetched_at_ist": "16-02-2026 09:05 IST",
        "tags": ["bitumen", "nhai", "crude_oil", "refinery"],
        "impact_score": 93, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "negative", "status": "new", "language": "en",
    },
    {
        "article_id": "demo007", "region": "International",
        "headline": "Tanker Freight Rates Jump 18% as Houthi Attacks Force Cape of Good Hope Rerouting",
        "summary": "VLCC tanker freight rates surged 18% week-on-week as vessel operators avoided the Red Sea following escalating Houthi missile attacks on commercial shipping. The rerouting via the Cape of Good Hope adds approximately 12 days to voyage times between the Arabian Gulf and India's west coast ports, increasing delivered bitumen costs.",
        "source_name": "Rigzone", "source_url": "https://www.rigzone.com",
        "published_at_ist": "28-02-2026 14:20 IST", "fetched_at_ist": "28-02-2026 14:22 IST",
        "tags": ["logistics", "shipping", "middle_east", "freight"],
        "impact_score": 88, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "negative", "status": "new", "language": "en",
    },
    {
        "article_id": "demo008", "region": "Domestic",
        "headline": "PMGSY Phase-IV Targets 62,000 km Rural Roads; Cabinet Approves ₹70,000 Cr Outlay",
        "summary": "The Union Cabinet approved Phase-IV of the Pradhan Mantri Gram Sadak Yojana (PMGSY) targeting 62,500 km of rural roads across 25 states. The ₹70,125 crore programme focuses on North-East states and Left Wing Extremism (LWE) districts. Total bitumen demand estimated at 1.5–1.8 lakh MT over 5 years.",
        "source_name": "PIB India — Infrastructure", "source_url": "https://pib.gov.in",
        "published_at_ist": "25-02-2026 12:30 IST", "fetched_at_ist": "25-02-2026 12:32 IST",
        "tags": ["pmgsy", "budget", "funding", "highway"],
        "impact_score": 90, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "positive", "status": "new", "language": "en",
    },
    {
        "article_id": "demo009", "region": "International",
        "headline": "US Tightens Iran Sanctions; Oil Market Braces for Supply Shortfall of 500K bbl/d",
        "summary": "The United States Treasury Department announced additional sanctions on Iranian crude oil exports, targeting shipping companies and refineries processing Iranian oil. Analysts estimate potential removal of 400,000–600,000 barrels per day from global supply. Brent crude responded with a 2.1% spike to ₹ 85.80/bbl.",
        "source_name": "CNBC — Energy", "source_url": "https://www.cnbc.com",
        "published_at_ist": "27-02-2026 20:45 IST", "fetched_at_ist": "27-02-2026 20:47 IST",
        "tags": ["sanctions", "middle_east", "crude_oil", "supply_chain"],
        "impact_score": 89, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "negative", "status": "new", "language": "en",
    },
    {
        "article_id": "demo010", "region": "Domestic",
        "headline": "राजस्थान PWD ने ₹850 करोड़ की 5 राज्य राजमार्ग परियोजनाओं के लिए निविदाएं जारी कीं",
        "summary": "राजस्थान लोक निर्माण विभाग (PWD) ने कुल ₹850 करोड़ मूल्य की 5 राज्य राजमार्ग परियोजनाओं के लिए निविदाएं आमंत्रित की हैं। इन परियोजनाओं में जोधपुर-बाड़मेर (62 km), अजमेर-नागौर (48 km), कोटा-बूंदी बाईपास, उदयपुर-चित्तौड़गढ़ और जयपुर रिंग रोड का एक खंड शामिल है।",
        "source_name": "Dainik Bhaskar (Hindi)", "source_url": "https://www.bhaskar.com",
        "published_at_ist": "01-03-2026 08:15 IST", "fetched_at_ist": "01-03-2026 08:17 IST",
        "tags": ["pwd", "tender", "highway"],
        "impact_score": 72, "duplicate_cluster_id": None, "duplicate_count": 1,
        "similar_sources": [], "sentiment": "positive", "status": "new", "language": "hi",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# IST HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _now_ist() -> datetime.datetime:
    return datetime.datetime.utcnow() + IST_OFFSET

def _utc_to_ist(dt) -> datetime.datetime:
    if dt is None:
        return _now_ist()
    if hasattr(dt, "utctimetuple"):
        import calendar
        # strip timezone info and treat as UTC
        naive = datetime.datetime(*dt.timetuple()[:6])
        return naive + IST_OFFSET
    return _now_ist()

def _fmt_ist(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M IST")

def _parse_ist(s: str) -> Optional[datetime.datetime]:
    for fmt in ("%Y-%m-%d %H:%M IST", "%Y-%m-%d %H:%M:%S IST", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

def _load_news_cfg() -> dict:
    if NEWS_CFG_FILE.exists():
        try:
            return json.loads(NEWS_CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_news_cfg(key: str, value: str):
    data = _load_news_cfg()
    data[key] = value
    NEWS_CFG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    # Cloud safety net — also stash in session so the key survives even
    # if the file gets wiped before the next request.
    try:
        from cloud_secrets import remember_in_session
        merged = dict(data); merged[key] = value
        remember_in_session("news", merged)
    except Exception:
        pass

def get_news_api_key(cfg_key: str) -> str:
    """Cloud-resilient API key resolver.

    Priority:
      1. st.secrets["news"][cfg_key]  (Cloud-persistent)
      2. Environment variable from NEWS_SOURCES env_key
      3. Local news config file
    """
    import os
    # 1. Streamlit secrets
    try:
        from cloud_secrets import get_secret_block
        block = get_secret_block("news")
        if block.get(cfg_key):
            return str(block[cfg_key]).strip()
    except Exception:
        pass
    # 2. Env var
    src = next((s for s in NEWS_SOURCES if s.get("cfg_key") == cfg_key), None)
    if src and src.get("env_key"):
        val = os.environ.get(src["env_key"], "").strip()
        if val:
            return val
    # 3. Local file
    return _load_news_cfg().get(cfg_key, "").strip()

# ══════════════════════════════════════════════════════════════════════════════
# STORAGE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _load_json(path: Path, default) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def _save_json(path: Path, data: list, max_items: int = 5000):
    if len(data) > max_items:
        data = data[-max_items:]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def load_articles() -> list[dict]:
    articles = _load_json(ARTICLES_FILE, [])
    if not articles:
        return list(DEMO_ARTICLES)   # Return demo copy if empty
    return articles

def save_articles(articles: list[dict]):
    _save_json(ARTICLES_FILE, articles, MAX_ARTICLES)

def get_articles(region: str = "All", tags: list[str] = None,
                 max_age_hours: int = 168, search: str = "",
                 impact_min: int = 0, source: str = "All",
                 language: str = "All") -> list[dict]:
    """Query articles with filters."""
    articles = load_articles()
    now = _now_ist()
    result = []
    for a in articles:
        # Age filter
        pub = _parse_ist(a.get("published_at_ist", ""))
        if pub:
            age_h = (now - pub).total_seconds() / 3600
            if age_h > max_age_hours:
                continue
        # Region filter
        if region != "All" and a.get("region") != region:
            continue
        # Impact filter
        if a.get("impact_score", 0) < impact_min:
            continue
        # Source filter
        if source != "All" and a.get("source_name") != source:
            continue
        # Language filter
        if language != "All" and a.get("language", "en") != language:
            continue
        # Tag filter
        if tags:
            if not any(t in a.get("tags", []) for t in tags):
                continue
        # Search
        if search:
            text = (a.get("headline","") + " " + a.get("summary","")).lower()
            if search.lower() not in text:
                continue
        result.append(a)
    # Sort newest first
    result.sort(key=lambda x: x.get("published_at_ist",""), reverse=True)
    return result

def get_breaking_news(region: str = "All") -> list[dict]:
    """Return articles with impact_score >= 80."""
    return [a for a in get_articles(region=region, max_age_hours=24)
            if a.get("impact_score", 0) >= 80]

# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _tag_article(headline: str, summary: str, region: str, source_hint: list[str] = None) -> list[str]:
    text = (headline + " " + summary).lower()
    tags = set()
    taxonomy = INTL_TAG_KEYWORDS if region == "International" else DOMESTIC_TAG_KEYWORDS
    for tag, keywords in taxonomy.items():
        if any(kw in text for kw in keywords):
            tags.add(tag)
    # Also check opposite taxonomy lightly
    if region == "International":
        for tag, keywords in DOMESTIC_TAG_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                tags.add(tag)
    else:
        for tag, keywords in INTL_TAG_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                tags.add(tag)
    # Source hint tags
    if source_hint:
        tags.update(source_hint)
    return list(tags)

def _score_impact(headline: str, summary: str, tags: list[str],
                  source_name: str, pub_time: datetime.datetime) -> int:
    text = (headline + " " + summary).lower()
    score = 0

    # Tag weight (0–40): more tags = more relevant
    score += min(len(tags) * 7, 40)

    # Breaking keywords (+20)
    if any(kw in text for kw in BREAKING_KEYWORDS):
        score += 20

    # Source reliability weight (0–15)
    rel = SOURCE_RELIABILITY.get(source_name, 70)
    score += int(rel * 0.15)

    # Freshness weight (0–15): newest = highest
    now = _now_ist()
    age_h = (now - pub_time).total_seconds() / 3600 if pub_time else 48
    if age_h < 1:    score += 15
    elif age_h < 6:  score += 10
    elif age_h < 24: score += 5

    # High-value keywords boost (+10)
    HIGH_VALUE = ["billion", "crore", "lakh crore", "record", "all-time", "emergency",
                  "awarded", "approved", "sanctioned", "cuts production", "ban"]
    if any(kw in text for kw in HIGH_VALUE):
        score += 10

    return min(score, 100)

def _detect_sentiment(headline: str, summary: str) -> str:
    """Detect sentiment using full FinBERT → DistilBERT → VADER → Keyword chain."""
    text = f"{headline}. {summary}".strip(". ")
    if not text:
        return "neutral"
    try:
        from finbert_engine import analyze_financial_sentiment
        result = analyze_financial_sentiment(text)
        return result.get("sentiment", "neutral")
    except Exception:
        # Inline keyword fallback if finbert_engine not available
        text_lower = text.lower()
        pos = ["rise", "gain", "surge", "award", "approve", "growth", "record high",
               "boost", "launch", "complete", "achieve", "increase", "positive", "profit"]
        neg = ["fall", "crash", "drop", "ban", "loss", "decline", "negative",
               "risk", "dispute", "delay", "shortage", "outage", "attack", "halt", "fail"]
        p = sum(1 for w in pos if w in text_lower)
        n = sum(1 for w in neg if w in text_lower)
        if p > n:
            return "positive"
        elif n > p:
            return "negative"
        return "neutral"

# ══════════════════════════════════════════════════════════════════════════════
# DEDUPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def _deduplicate(new_articles: list[dict], existing: list[dict]) -> list[dict]:
    """
    Remove duplicates within new batch and against existing articles.
    Similar headlines (ratio > DEDUP_THRESHOLD) get clustered.
    """
    existing_headlines = [a.get("headline","") for a in existing[-500:]]  # last 500
    unique = []
    seen_in_batch: list[str] = []

    for art in new_articles:
        headline = art.get("headline", "")
        is_dup = False

        # Check against existing
        for ex_h in existing_headlines:
            ratio = difflib.SequenceMatcher(None, headline.lower(), ex_h.lower()).ratio()
            if ratio >= DEDUP_THRESHOLD:
                is_dup = True
                break

        if not is_dup:
            # Check against current batch
            for seen_h in seen_in_batch:
                ratio = difflib.SequenceMatcher(None, headline.lower(), seen_h.lower()).ratio()
                if ratio >= DEDUP_THRESHOLD:
                    is_dup = True
                    break

        if not is_dup:
            unique.append(art)
            seen_in_batch.append(headline)

    return unique

# ══════════════════════════════════════════════════════════════════════════════
# RSS FETCHER
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_rss(source: dict) -> tuple[list[dict], Optional[str]]:
    """Fetch and parse an RSS feed. Returns (articles, error_or_None)."""
    try:
        import feedparser
        import urllib.request

        req = urllib.request.Request(
            source["feed_url"],
            headers={"User-Agent": "PPS-Anantams-Dashboard/2.0 RSS Reader"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()

        feed = feedparser.parse(raw)
        if feed.bozo and not feed.entries:
            return [], f"Feed parse error: {getattr(feed, 'bozo_exception', 'unknown')}"

        articles = []
        for entry in feed.entries[:20]:  # Max 20 per source per fetch
            headline = getattr(entry, "title", "").strip()
            if not headline:
                continue

            summary = (
                getattr(entry, "summary", "") or
                getattr(entry, "description", "") or ""
            )[:500]

            link = getattr(entry, "link", source.get("feed_url", ""))
            pub_struct = getattr(entry, "published_parsed", None) or \
                         getattr(entry, "updated_parsed", None)

            if pub_struct:
                pub_dt = datetime.datetime(*pub_struct[:6])
                pub_ist = pub_dt + IST_OFFSET
            else:
                pub_ist = _now_ist()

            region  = source["region"]
            lang    = source.get("language", "en")
            tags    = _tag_article(headline, summary, region, source.get("tags_hint", []))
            score   = _score_impact(headline, summary, tags, source["name"], pub_ist)
            senti   = _detect_sentiment(headline, summary)
            art_id  = hashlib.sha256(f"{headline[:80]}|{link[:80]}".encode()).hexdigest()[:12]

            # Extract image from RSS entry (media:content, media:thumbnail, enclosures)
            image_url = ""
            try:
                # media:content or media:thumbnail
                media = getattr(entry, "media_content", None) or getattr(entry, "media_thumbnail", None)
                if media and isinstance(media, list) and media[0].get("url"):
                    image_url = media[0]["url"]
                # enclosures (e.g. <enclosure url="..." type="image/jpeg"/>)
                if not image_url:
                    enclosures = getattr(entry, "enclosures", [])
                    for enc in enclosures:
                        if "image" in enc.get("type", ""):
                            image_url = enc.get("href", enc.get("url", ""))
                            break
                # links with type image
                if not image_url:
                    for lnk in getattr(entry, "links", []):
                        if "image" in lnk.get("type", ""):
                            image_url = lnk.get("href", "")
                            break
            except Exception:
                pass

            articles.append({
                "article_id":         art_id,
                "region":             region,
                "headline":           headline,
                "summary":            summary,
                "source_name":        source["name"],
                "source_id":          source["source_id"],
                "source_url":         link,
                "image_url":          image_url,
                "published_at_ist":   _fmt_ist(pub_ist),
                "fetched_at_ist":     _fmt_ist(_now_ist()),
                "tags":               tags,
                "impact_score":       score,
                "duplicate_cluster_id": None,
                "duplicate_count":    1,
                "similar_sources":    [],
                "sentiment":          senti,
                "status":             "new",
                "language":           lang,
            })

        return articles, None

    except Exception as exc:
        return [], str(exc)

# ══════════════════════════════════════════════════════════════════════════════
# API FETCHERS
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_newsapi(source: dict, api_key: str) -> tuple[list[dict], Optional[str]]:
    try:
        import requests
        params = {
            "q":        source.get("query", "crude oil"),
            "language": "en",
            "sortBy":   "publishedAt",
            "pageSize": 20,
            "apiKey":   api_key,
        }
        resp = requests.get(source["endpoint"], params=params, timeout=15)
        if resp.status_code == 429:
            return [], "Rate limit (429) — daily limit reached"
        if resp.status_code == 401:
            return [], "Auth failed (401) — invalid API key"
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("articles", [])[:20]:
            headline = item.get("title", "").strip()
            if not headline or headline == "[Removed]":
                continue
            summary  = item.get("description", "") or ""
            link     = item.get("url", "")
            pub_raw  = item.get("publishedAt", "")
            try:
                pub_dt  = datetime.datetime.strptime(pub_raw, "%Y-%m-%dT%H:%M:%SZ")
                pub_ist = pub_dt + IST_OFFSET
            except Exception:
                pub_ist = _now_ist()
            region = source["region"]
            tags   = _tag_article(headline, summary, region, source.get("tags_hint", []))
            score  = _score_impact(headline, summary, tags, source["name"], pub_ist)
            art_id = hashlib.sha256(f"{headline[:80]}|{link[:80]}".encode()).hexdigest()[:12]
            articles.append({
                "article_id":         art_id,
                "region":             region,
                "headline":           headline,
                "summary":            summary[:500],
                "source_name":        item.get("source", {}).get("name", source["name"]),
                "source_id":          source["source_id"],
                "source_url":         link,
                "published_at_ist":   _fmt_ist(pub_ist),
                "fetched_at_ist":     _fmt_ist(_now_ist()),
                "tags":               tags,
                "impact_score":       score,
                "duplicate_cluster_id": None,
                "duplicate_count":    1,
                "similar_sources":    [],
                "sentiment":          _detect_sentiment(headline, summary),
                "status":             "new",
                "language":           "en",
            })
        return articles, None
    except Exception as exc:
        return [], str(exc)

def _fetch_gnews(source: dict, api_key: str) -> tuple[list[dict], Optional[str]]:
    try:
        import requests
        params = {
            "q":        source.get("query", "highway India"),
            "lang":     "en",
            "country":  "in",
            "max":      20,
            "token":    api_key,
        }
        resp = requests.get(source["endpoint"], params=params, timeout=15)
        if resp.status_code == 429:
            return [], "Rate limit (429)"
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("articles", [])[:20]:
            headline = item.get("title", "").strip()
            if not headline:
                continue
            summary  = item.get("description", "") or ""
            link     = item.get("url", "")
            pub_raw  = item.get("publishedAt", "")
            try:
                pub_dt  = datetime.datetime.fromisoformat(pub_raw.replace("Z","+00:00"))
                pub_ist = pub_dt.replace(tzinfo=None) + IST_OFFSET
            except Exception:
                pub_ist = _now_ist()
            region = source["region"]
            tags   = _tag_article(headline, summary, region, source.get("tags_hint", []))
            score  = _score_impact(headline, summary, tags, source["name"], pub_ist)
            art_id = hashlib.sha256(f"{headline[:80]}|{link[:80]}".encode()).hexdigest()[:12]
            articles.append({
                "article_id": art_id, "region": region, "headline": headline,
                "summary": summary[:500], "source_name": source["name"],
                "source_id": source["source_id"], "source_url": link,
                "published_at_ist": _fmt_ist(pub_ist), "fetched_at_ist": _fmt_ist(_now_ist()),
                "tags": tags, "impact_score": score, "duplicate_cluster_id": None,
                "duplicate_count": 1, "similar_sources": [], "language": "en",
                "sentiment": _detect_sentiment(headline, summary), "status": "new",
            })
        return articles, None
    except Exception as exc:
        return [], str(exc)

# ══════════════════════════════════════════════════════════════════════════════
# FETCH LOG + CHANGE HISTORY + BUG TRACKER
# ══════════════════════════════════════════════════════════════════════════════

def _log_fetch(source_id: str, start: datetime.datetime, end: datetime.datetime,
               fetched: int, error: str = ""):
    log = _load_json(FETCH_LOG_FILE, [])
    log.append({
        "fetch_id":       hashlib.md5(f"{source_id}{start}".encode()).hexdigest()[:8],
        "source_id":      source_id,
        "start_time_ist": _fmt_ist(start),
        "end_time_ist":   _fmt_ist(end),
        "records_fetched":fetched,
        "failures":       1 if error else 0,
        "error_message":  error,
        "status":         "Fail" if error else "OK",
    })
    _save_json(FETCH_LOG_FILE, log, MAX_LOG)

def _log_change(change_type: str, article_id: str, old_val: str,
                new_val: str, reason: str, actor: str = "System"):
    hist = _load_json(CHANGE_FILE, [])
    hist.append({
        "timestamp_ist": _fmt_ist(_now_ist()),
        "change_type":   change_type,
        "article_id":    article_id,
        "old_value":     str(old_val)[:200],
        "new_value":     str(new_val)[:200],
        "reason":        reason,
        "actor":         actor,
    })
    _save_json(CHANGE_FILE, hist, 5000)

def get_fetch_log(n: int = 100) -> list[dict]:
    return list(reversed(_load_json(FETCH_LOG_FILE, [])[-n:]))

def get_change_history(n: int = 100) -> list[dict]:
    return list(reversed(_load_json(CHANGE_FILE, [])[-n:]))

# ══════════════════════════════════════════════════════════════════════════════
# MAIN FETCH CYCLE
# ══════════════════════════════════════════════════════════════════════════════

_source_status: dict[str, dict] = {
    s["source_id"]: {"status": "Unknown", "last_fetch": "", "error": "", "count": 0}
    for s in NEWS_SOURCES
}

def run_fetch_cycle() -> dict[str, int]:
    """Fetch all enabled sources. Returns {source_id: articles_added}."""
    existing  = load_articles()
    added_map = {}

    for source in NEWS_SOURCES:
        sid   = source["source_id"]
        stype = source["type"]
        start = _now_ist()

        try:
            if stype == "RSS":
                articles, err = _fetch_rss(source)
            elif stype == "API" and source.get("cfg_key"):
                key = get_news_api_key(source["cfg_key"])
                if not key:
                    _source_status[sid] = {"status": "No Key", "last_fetch": _fmt_ist(start),
                                           "error": "API key not configured", "count": 0}
                    added_map[sid] = 0
                    continue
                if "newsapi" in sid:
                    articles, err = _fetch_newsapi(source, key)
                else:
                    articles, err = _fetch_gnews(source, key)
            else:
                continue

            end = _now_ist()

            if err:
                _source_status[sid] = {"status": "Fail", "last_fetch": _fmt_ist(start),
                                       "error": err[:120], "count": 0}
                _log_fetch(sid, start, end, 0, err)
                added_map[sid] = 0
                continue

            # Deduplicate
            unique = _deduplicate(articles, existing)
            existing.extend(unique)
            added_map[sid] = len(unique)
            _source_status[sid] = {"status": "OK", "last_fetch": _fmt_ist(end),
                                   "error": "", "count": len(unique)}

            for art in unique:
                _log_change("added", art["article_id"], "", art["headline"],
                            f"Fetched from {source['name']}")

            _log_fetch(sid, start, end, len(unique))

        except Exception as exc:
            end = _now_ist()
            err_str = str(exc)[:120]
            _source_status[sid] = {"status": "Fail", "last_fetch": _fmt_ist(start),
                                   "error": err_str, "count": 0}
            _log_fetch(sid, start, end, 0, err_str)
            added_map[sid] = 0

    save_articles(existing)
    return added_map

def get_source_health() -> list[dict]:
    rows = []
    for s in NEWS_SOURCES:
        sid = s["source_id"]
        st  = _source_status.get(sid, {"status": "Unknown", "last_fetch": "", "error": "", "count": 0})
        rows.append({**s, **st})
    return rows

# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND AUTO-FETCH
# ══════════════════════════════════════════════════════════════════════════════

_fetch_lock = threading.RLock()
_G_fetch: dict = {"started": False, "last_run": ""}

def start_auto_fetch(interval_min: int = REFRESH_INTERVAL_MIN):
    """Start background thread that fetches news every interval_min minutes."""
    with _fetch_lock:
        if _G_fetch["started"]:
            return
        _G_fetch["started"] = True

    def _loop():
        while True:
            try:
                run_fetch_cycle()
                _G_fetch["last_run"] = _fmt_ist(_now_ist())
            except Exception:
                pass
            time.sleep(interval_min * 60)

    t = threading.Thread(target=_loop, daemon=True, name="NewsFetcher")
    t.start()

def mark_article(article_id: str, status: str, actor: str = "User"):
    """Mark article as read/saved/archived."""
    articles = load_articles()
    for a in articles:
        if a["article_id"] == article_id:
            old = a.get("status", "new")
            a["status"] = status
            _log_change("updated", article_id, old, status,
                        f"User marked as {status}", actor)
            break
    save_articles(articles)

def get_last_fetch_time() -> str:
    return _G_fetch.get("last_run", "Not yet fetched")

def get_article_sources(region: str = "All") -> list[str]:
    articles = load_articles()
    seen = set()
    sources = []
    for a in articles:
        if region != "All" and a.get("region") != region:
            continue
        s = a.get("source_name", "")
        if s and s not in seen:
            seen.add(s)
            sources.append(s)
    return sorted(sources)

def get_all_tags(region: str = "All") -> list[str]:
    articles = load_articles()
    seen: set[str] = set()
    for a in articles:
        if region != "All" and a.get("region") != region:
            continue
        seen.update(a.get("tags", []))
    return sorted(seen)
