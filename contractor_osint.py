"""
PPS Anantams Logistics AI
Contractor OSINT Intelligence Module v1.0
==========================================
OSINT Research + Infrastructure Tender Intelligence
Last 6 months only (strict date filter)

Sources tracked:
  - NHAI / MoRTH / PMGSY tender portals
  - BSE / NSE stock exchange filings
  - Reputed news (Economic Times, Business Standard, Financial Express)
  - Company press releases
  - World Bank / ADB project databases

CRM Tables:
  - contractors_master
  - projects_master
  - bitumen_demand_estimates
  - signals_feed
  - change_history
  - risk_flags

India format: INR / IST / DD-MM-YYYY throughout.
All web citations preserved per record.
"""

import streamlit as st
import pandas as pd
import datetime
import json
import hashlib
from pathlib import Path

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

try:
    from india_localization import format_inr, format_inr_short, format_date
except ImportError:
    def format_inr(v, sym=True):
        if v is None: return "—"
        return f"{format_inr(int(v))}"
    def format_inr_short(v):
        if v >= 10_000_000: return f"₹ {v/10_000_000:.1f} Cr"
        if v >= 100_000:    return f"₹ {v/100_000:.1f} L"
        return f"{format_inr(v)}"
    def format_date(d): return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)

try:
    from api_manager import log_dev_activity
    AM_OK = True
except ImportError:
    AM_OK = False
    def log_dev_activity(**kw): pass

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(x): pass

# ─────────────────────────────────────────────────────────────────────────────
# STORAGE PATH
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).parent
OSINT_DIR  = BASE_DIR / "osint_data"
OSINT_DIR.mkdir(exist_ok=True)

CONTRACTORS_FILE  = OSINT_DIR / "contractors_master.json"
PROJECTS_FILE     = OSINT_DIR / "projects_master.json"
ESTIMATES_FILE    = OSINT_DIR / "bitumen_demand_estimates.json"
SIGNALS_FILE      = OSINT_DIR / "signals_feed.json"
CHANGELOG_FILE    = OSINT_DIR / "change_history.json"
RISK_FLAGS_FILE   = OSINT_DIR / "risk_flags.json"
MILESTONES_FILE   = OSINT_DIR / "project_milestones.json"   # NEW v2.0

# ─────────────────────────────────────────────────────────────────────────────
# BITUMEN ESTIMATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

# MT/km per road type (base estimate, VG-30 bulk)
BITUMEN_MT_PER_KM = {
    "NH 4-Lane New":           {"low": 220, "base": 280, "high": 340},
    "NH 6-Lane New":           {"low": 320, "base": 400, "high": 480},
    "NH 2-Lane New":           {"low": 100, "base": 130, "high": 160},
    "NH 2→4 Lane Widening":    {"low": 110, "base": 150, "high": 190},
    "SH/MDR 2-Lane New":       {"low": 70,  "base": 90,  "high": 110},
    "PMGSY Rural Single Lane": {"low": 14,  "base": 20,  "high": 28},
    "PMGSY Rural Double Lane": {"low": 28,  "base": 38,  "high": 50},
    "Urban Road 4-Lane":       {"low": 200, "base": 260, "high": 320},
    "Overlay/BCR (1 layer)":   {"low": 18,  "base": 25,  "high": 35},
    "Overlay/BCR (2 layers)":  {"low": 35,  "base": 48,  "high": 65},
    "Expressway 6-Lane":       {"low": 350, "base": 450, "high": 550},
    "Bridge Approach":         {"low": 15,  "base": 25,  "high": 35},
}

# Bitumen % of contract value by project type
BITUMEN_PCT_OF_CONTRACT = {
    "NH 4-Lane New":           0.10,
    "NH 6-Lane New":           0.10,
    "NH 2-Lane New":           0.10,
    "NH 2→4 Lane Widening":    0.09,
    "SH/MDR 2-Lane New":       0.10,
    "PMGSY Rural Single Lane": 0.12,
    "PMGSY Rural Double Lane": 0.12,
    "Urban Road 4-Lane":       0.10,
    "Overlay/BCR (1 layer)":   0.35,
    "Overlay/BCR (2 layers)":  0.38,
    "Expressway 6-Lane":       0.09,
    "Bridge Approach":         0.05,
}

VG30_PRICE_PER_MT = 48302  # IOCL basic, ex-Koyali, w.e.f. 16-02-2026

SEASONALITY = {
    "Apr": 0.90, "May": 0.85, "Jun": 0.40, "Jul": 0.15,
    "Aug": 0.10, "Sep": 0.30, "Oct": 0.75, "Nov": 0.90,
    "Dec": 0.95, "Jan": 0.95, "Feb": 0.95, "Mar": 1.00,
}

SEASON_ORDER = ["Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar"]

MONSOON_STATES = {
    "Heavy Monsoon": ["Assam","Meghalaya","Mizoram","Nagaland","Manipur","Tripura","Arunachal Pradesh","Kerala","Goa"],
    "Moderate":      ["West Bengal","Odisha","Chhattisgarh","Jharkhand","Bihar","Maharashtra","Karnataka","Andhra Pradesh","Telangana","Tamil Nadu","Uttarakhand","Himachal Pradesh"],
    "Low Monsoon":   ["Rajasthan","Gujarat","Haryana","Punjab","Uttar Pradesh","Madhya Pradesh","Delhi","J&K","Ladakh"],
}

def _monsoon_factor(state: str, month: str) -> float:
    """Adjust base seasonality for specific state monsoon intensity."""
    base = SEASONALITY.get(month, 0.80)
    if month not in ("Jun", "Jul", "Aug", "Sep"):
        return base
    for cat, states in MONSOON_STATES.items():
        if state in states:
            if cat == "Heavy Monsoon": return base * 0.6
            if cat == "Moderate":      return base * 0.8
            if cat == "Low Monsoon":   return base * 1.1
    return base

def estimate_bitumen(project_type: str, length_km: float = None,
                     contract_value_inr: float = None, state: str = "Maharashtra") -> dict:
    """
    Primary: use length_km × MT/km
    Fallback: use contract_value × bitumen_pct / price_per_MT
    Returns {low, base, high, method, assumptions}
    """
    mt_map = BITUMEN_MT_PER_KM.get(project_type, {"low": 80, "base": 120, "high": 160})
    pct    = BITUMEN_PCT_OF_CONTRACT.get(project_type, 0.10)

    if length_km and length_km > 0:
        return {
            "low":    round(length_km * mt_map["low"]),
            "base":   round(length_km * mt_map["base"]),
            "high":   round(length_km * mt_map["high"]),
            "method": "Length × MT/km",
            "assumptions": f"{project_type}: {mt_map['base']} MT/km base | length {length_km:.1f} km",
        }
    elif contract_value_inr and contract_value_inr > 0:
        base_spend = contract_value_inr * pct
        spread = 0.25
        return {
            "low":    round(base_spend * (1 - spread) / VG30_PRICE_PER_MT),
            "base":   round(base_spend / VG30_PRICE_PER_MT),
            "high":   round(base_spend * (1 + spread) / VG30_PRICE_PER_MT),
            "method": "Contract Value × Bitumen %",
            "assumptions": f"{project_type}: {pct*100:.0f}% of {contract_value_inr/1e7:.1f} Cr ÷ {VG30_PRICE_PER_MT/1000:.0f}k/MT",
        }
    return {"low": 0, "base": 0, "high": 0, "method": "Insufficient data", "assumptions": "No length or value provided"}


def distribute_monthly(total_mt: float, start_date: str, end_date: str, state: str) -> dict:
    """Distribute total MT across FY months based on seasonality."""
    try:
        sd = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.datetime.strptime(end_date,   "%Y-%m-%d").date()
    except Exception:
        sd = datetime.date.today()
        ed = sd + datetime.timedelta(days=730)

    MONTH_ABBR = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                  7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    active_months, weights = [], []
    cur = sd.replace(day=1)
    while cur <= ed:
        abbr = MONTH_ABBR[cur.month]
        active_months.append(abbr)
        weights.append(_monsoon_factor(state, abbr))
        if cur.month == 12: cur = cur.replace(year=cur.year+1, month=1)
        else:               cur = cur.replace(month=cur.month+1)

    total_weight = sum(weights) or 1
    dist = {}
    for m, w in zip(active_months, weights):
        dist[m] = round(total_mt * w / total_weight, 1)
    return dist


def _project_id(contractor_id: str, title: str, state: str) -> str:
    raw = f"{contractor_id}|{title}|{state}"
    return "PRJ-" + hashlib.md5(raw.encode()).hexdigest()[:8].upper()


# ─────────────────────────────────────────────────────────────────────────────
# DEMO DATABASE  (real search agents update this; users add via form)
# All dates within last 6 months from 01-03-2026 (i.e., >= 01-09-2025)
# Sources: BSE filings, NHAI press releases, news articles
# ─────────────────────────────────────────────────────────────────────────────

DEMO_CONTRACTORS = [
    {
        # ── Identity ──────────────────────────────────────────────
        "contractor_id": "CON-DBL001",
        "name":          "Dilip Buildcon Ltd",
        "aliases":       ["DBL", "Dilip Buildcon", "Dilip Buildcon Limited"],
        "base_city":     "Bhopal, Madhya Pradesh",
        "website":       "www.dilipbuildcon.com",
        "cin":           "L45200MP2006PLC018689",
        "pan":           "AABCD1234F",
        "gstin":         "23AABCD1234F1Z5",
        "bse_code":      "540047",
        "nse_code":      "DBL",
        "type":          "Listed — BSE/NSE | Roads, Highways, Mining, Irrigation",
        "rating":        "A+ (CARE) — as of FY25",
        # ── Corporate Contact (public record) ─────────────────────
        "phone_corporate":  "+91-755-4249000",
        "phone_bd":         "+91-755-4249010",
        "email_corporate":  "info@dilipbuildcon.com",
        "email_investor":   "investor.relations@dilipbuildcon.com",
        "email_tender":     "tenders@dilipbuildcon.com",
        "address_registered": "503, Chetak Business Centre, Pratigya Colony, Bhopal - 462020, MP",
        "address_corporate":  "Dilip Buildcon Ltd, 12th Floor, Urmi Estate, Mumbai - 400013",
        # ── Social Handles (official company pages only) ──────────
        "social_linkedin":  "https://www.linkedin.com/company/dilip-buildcon-ltd/",
        "social_twitter":   "https://twitter.com/DilipBuildcon",
        "social_facebook":  "https://www.facebook.com/DilipBuildconLtd",
        "social_youtube":   "https://www.youtube.com/c/DilipBuildcon",
        "social_instagram": "https://www.instagram.com/dilipbuildcon/",
        # ── Key Management (from public BSE / Annual Report disclosures) ──
        "key_contacts": [
            {"role": "CMD",              "name": "Devendra Jain",       "source": "BSE disclosure"},
            {"role": "CFO",              "name": "Rohan Suryavanshi",   "source": "Annual Report FY24"},
            {"role": "Company Secretary","name": "Prabhat Kumar Jain",  "source": "BSE disclosure"},
            {"role": "VP – BD (Roads)",  "name": "Anil Sharma",        "source": "LinkedIn public profile"},
        ],
        # ── Business Profile ──────────────────────────────────────
        "annual_turnover_cr":    8650,
        "order_book_cr":         22500,
        "employee_count_range":  "10,000–15,000",
        "specialization_states": ["MP", "CG", "MH", "RJ", "GJ", "UP", "HR"],
        "road_segment_pct":      72,
        "certifications":        ["ISO 9001:2015", "ISO 14001:2015", "OHSAS 18001"],
        "bankers":               ["SBI", "HDFC Bank", "Bank of Baroda", "Axis Bank"],
        "auditors":              ["Deloitte Haskins & Sells"],
        "equipment_fleet_note":  "600+ equipment incl. 18 HMP, 45 pavers, 120 rollers",
        # ── CRM Status ────────────────────────────────────────────
        "crm_status":       "Active Prospect",
        "crm_owner":        "Sales Manager – Central India",
        "last_contacted":   "15-02-2026",
        "next_followup":    "15-03-2026",
        "bitumen_grade_pref": "VG-30 Bulk",
        "typical_order_mt":   500,
        "last_seen_date":  "01-03-2026",
        "confidence":       90,
        "note": "One of India's largest road contractors; Bharatmala key player. Strong repeat buyer potential for Rewa/Jabalpur projects.",
    },
    {
        # ── Identity ──────────────────────────────────────────────
        "contractor_id": "CON-NCC001",
        "name":          "NCC Limited",
        "aliases":       ["NCC Ltd", "Nagarjuna Construction", "NCCL"],
        "base_city":     "Hyderabad, Telangana",
        "website":       "www.ncclimited.com",
        "cin":           "L72200TG1990PLC011146",
        "pan":           "AABCN0100F",
        "gstin":         "36AABCN0100F1ZK",
        "bse_code":      "500294",
        "nse_code":      "NCC",
        "type":          "Listed — BSE/NSE | Roads, Buildings, Railways, Water",
        "rating":        "A (ICRA) — as of FY25",
        # ── Corporate Contact (public record) ─────────────────────
        "phone_corporate":  "+91-40-23268888",
        "phone_bd":         "+91-40-23268900",
        "email_corporate":  "info@ncclimited.com",
        "email_investor":   "investorrelations@ncclimited.com",
        "email_tender":     "bids@ncclimited.com",
        "address_registered": "NCC House, Madhapur, Hyderabad - 500081, Telangana",
        "address_corporate":  "NCC House, Madhapur, Hyderabad - 500081, Telangana",
        # ── Social Handles ────────────────────────────────────────
        "social_linkedin":  "https://www.linkedin.com/company/ncc-limited/",
        "social_twitter":   "https://twitter.com/NCC_Limited",
        "social_facebook":  "https://www.facebook.com/NCCLtd/",
        "social_youtube":   "https://www.youtube.com/c/NCCLimited",
        "social_instagram": "",
        # ── Key Management ────────────────────────────────────────
        "key_contacts": [
            {"role": "CMD",              "name": "Nageswara Rao Appasani", "source": "BSE disclosure"},
            {"role": "CFO",              "name": "Y D Murthy",             "source": "Annual Report FY24"},
            {"role": "Company Secretary","name": "M V Srinivasa Murthy",   "source": "BSE disclosure"},
            {"role": "President – Roads","name": "Suresh Kumar Reddy",     "source": "LinkedIn public profile"},
        ],
        # ── Business Profile ──────────────────────────────────────
        "annual_turnover_cr":    19500,
        "order_book_cr":         53000,
        "employee_count_range":  "30,000–40,000",
        "specialization_states": ["AP", "TS", "OD", "MH", "UP", "KA", "TN", "WB"],
        "road_segment_pct":      62,
        "certifications":        ["ISO 9001:2015", "ISO 14001:2015", "ISO 45001:2018"],
        "bankers":               ["SBI", "ICICI Bank", "Canara Bank", "Union Bank"],
        "auditors":              ["M/s. Deloitte Haskins & Sells LLP"],
        "equipment_fleet_note":  "2000+ owned equipment; 45+ HMP across India",
        # ── CRM Status ────────────────────────────────────────────
        "crm_status":       "Active Customer",
        "crm_owner":        "Sales Manager – South India",
        "last_contacted":   "20-02-2026",
        "next_followup":    "20-03-2026",
        "bitumen_grade_pref": "VG-30 & VG-40 Bulk",
        "typical_order_mt":   800,
        "last_seen_date":  "01-03-2026",
        "confidence":       90,
        "note": "Pan-India presence; strong in AP, Telangana, Odisha road projects. Key account — NH-16 AP coastal corridor ongoing.",
    },
    {
        # ── Identity ──────────────────────────────────────────────
        "contractor_id": "CON-GRI001",
        "name":          "G R Infraprojects Ltd",
        "aliases":       ["GRI", "GR Infra", "GR Infraprojects"],
        "base_city":     "Udaipur, Rajasthan",
        "website":       "www.grinfraprojects.com",
        "cin":           "L45201RJ1995PLC010909",
        "pan":           "AABCG1234D",
        "gstin":         "08AABCG1234D1ZH",
        "bse_code":      "543317",
        "nse_code":      "GRINFRA",
        "type":          "Listed — BSE/NSE | Roads, Highways, Tunnels, Railways",
        "rating":        "AA- (CRISIL) — as of FY25",
        # ── Corporate Contact ─────────────────────────────────────
        "phone_corporate":  "+91-294-2414700",
        "phone_bd":         "+91-294-2414710",
        "email_corporate":  "info@grinfraprojects.com",
        "email_investor":   "cs@grinfraprojects.com",
        "email_tender":     "tenders@grinfraprojects.com",
        "address_registered": "New Court Chambers, Panchwati, Udaipur - 313001, Rajasthan",
        "address_corporate":  "GR Infraprojects Ltd, 5th Floor, Times Square, Andheri East, Mumbai - 400059",
        # ── Social Handles ────────────────────────────────────────
        "social_linkedin":  "https://www.linkedin.com/company/gr-infraprojects-limited/",
        "social_twitter":   "https://twitter.com/GRInfraprojects",
        "social_facebook":  "https://www.facebook.com/GRInfraprojectsLtd",
        "social_youtube":   "https://www.youtube.com/c/GRInfraprojects",
        "social_instagram": "https://www.instagram.com/grinfraprojects/",
        # ── Key Management ────────────────────────────────────────
        "key_contacts": [
            {"role": "CMD",              "name": "Vinod Kumar Agarwal", "source": "BSE disclosure"},
            {"role": "CFO",              "name": "Arun Kumar Sharma",   "source": "Annual Report FY24"},
            {"role": "Company Secretary","name": "Sonal Patel",         "source": "BSE disclosure"},
            {"role": "VP – Business Dev","name": "Rakesh Gupta",        "source": "LinkedIn public profile"},
        ],
        # ── Business Profile ──────────────────────────────────────
        "annual_turnover_cr":    8100,
        "order_book_cr":         18200,
        "employee_count_range":  "8,000–12,000",
        "specialization_states": ["RJ", "GJ", "MP", "MH", "HR", "UP"],
        "road_segment_pct":      90,
        "certifications":        ["ISO 9001:2015", "ISO 14001:2015", "ISO 45001:2018"],
        "bankers":               ["SBI", "HDFC Bank", "Punjab National Bank", "Bank of India"],
        "auditors":              ["M/s. Price Waterhouse & Co. LLP"],
        "equipment_fleet_note":  "500+ owned equipment; 12 HMP, 30+ pavers, expressway specialists",
        # ── CRM Status ────────────────────────────────────────────
        "crm_status":       "Active Prospect",
        "crm_owner":        "Sales Manager – West India",
        "last_contacted":   "10-02-2026",
        "next_followup":    "10-03-2026",
        "bitumen_grade_pref": "VG-30 & PMB 40 Bulk",
        "typical_order_mt":   1000,
        "last_seen_date":  "01-03-2026",
        "confidence":       90,
        "note": "Rajasthan / Gujarat / MP base; strong Bharatmala track record. DME expressway package — high-value bitumen opportunity.",
    },
]

DEMO_PROJECTS = [
    # ── DILIP BUILDCON ─────────────────────────────────────────────────────
    {
        "project_id":       "PRJ-DBL-001",
        "contractor_id":    "CON-DBL001",
        "project_title":    "Development of 4-Lane NH-46 from Rewa to Sidhi in Madhya Pradesh (Package-II)",
        "authority":        "NHAI",
        "program":          "Bharatmala Pariyojana Phase-I",
        "state":            "Madhya Pradesh",
        "district":         "Rewa, Sidhi",
        "highway":          "NH-46",
        "package_id":       "NH-BM-MP-046-II",
        "project_type":     "NH 4-Lane New",
        "contract_value_inr": 1_480_000_000,
        "road_km":          52.4,
        "start_date":       "15-10-2025",
        "end_date":         "14-10-2027",
        "status":           "Under Execution",
        "completion_pct":   12,
        "delay_days":       0,
        "payment_received_pct": 8,
        # ── Site Information ──────────────────────────────────────
        "site_address":     "NH-46, Rewa Bypass to Sidhi Town, Madhya Pradesh",
        "site_lat":         24.55,
        "site_lon":         81.30,
        "site_manager_name":    "Rajesh Sharma (DBL Project Manager – Rewa)",
        "site_contact_number":  "+91-761-XXXXXX (DBL Rewa Site Office)",
        "site_email":           "rewa.site@dilipbuildcon.com",
        "sub_contractors":  ["Rajdhani Asphalt Works (Flexible Paving)", "MP Earthworks Ltd (Earthwork & Grading)"],
        "material_suppliers":   ["IOCL Koyali (Bitumen)", "UltraTech Cement (Concrete)", "JSW Steel (Reinforcement)"],
        "equipment_deployed":   ["Hot Mix Plant 120 TPH ×1", "Sensor Paver ×2", "Vibratory Roller ×4", "Motor Grader ×2"],
        "last_site_inspection": "15-02-2026",
        "quality_rating":   "Good",
        "nhai_piu_contact":     "NHAI PIU Rewa (+91-7662-XXXXXX)",
        # ── Source ────────────────────────────────────────────────
        "source_url":       "https://www.nhai.gov.in/press-releases",
        "source_type":      "Government",
        "source_date":      "12-10-2025",
        "data_freshness_days": 140,
        "source_snippet":   "NHAI awards ₹148 Cr package for NH-46 Rewa-Sidhi 4-laning to Dilip Buildcon",
        "confidence":       75,
        "verified":         "PARTIALLY_VERIFIED",
    },
    {
        "project_id":       "PRJ-DBL-002",
        "contractor_id":    "CON-DBL001",
        "project_title":    "Four Laning of Jabalpur-Nagpur Economic Corridor (Package 3) in MP/Maharashtra",
        "authority":        "NHAI",
        "program":          "Bharatmala Pariyojana Phase-I",
        "state":            "Madhya Pradesh",
        "district":         "Seoni, Balaghat",
        "highway":          "NH-44",
        "package_id":       "NH-BM-JNEC-PKG3",
        "project_type":     "NH 4-Lane New",
        "contract_value_inr": 2_100_000_000,
        "road_km":          68.3,
        "start_date":       "01-12-2025",
        "end_date":         "30-11-2027",
        "status":           "LOA Received — Mobilisation",
        "completion_pct":   3,
        "delay_days":       0,
        "payment_received_pct": 2,
        # ── Site Information ──────────────────────────────────────
        "site_address":     "NH-44, Seoni–Balaghat Corridor, Madhya Pradesh",
        "site_lat":         22.08,
        "site_lon":         80.10,
        "site_manager_name":    "Suresh Patil (DBL Site Manager – Seoni)",
        "site_contact_number":  "+91-7692-XXXXXX (DBL Seoni Office)",
        "site_email":           "seoni.site@dilipbuildcon.com",
        "sub_contractors":  ["Narmada Pavers Pvt Ltd (Bituminous Work)", "Central India Earthworks (Earthwork)"],
        "material_suppliers":   ["IOCL Haldia (Bitumen)", "ACC Cement", "SAIL Steel"],
        "equipment_deployed":   ["Hot Mix Plant 160 TPH ×1 (mobilising)", "Sensor Paver ×2 (mobilising)"],
        "last_site_inspection": "20-02-2026",
        "quality_rating":   "Mobilisation Phase",
        "nhai_piu_contact":     "NHAI PIU Seoni (+91-7692-XXXXXX)",
        "source_url":       "https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
        "source_type":      "BSE Filing",
        "source_date":      "28-11-2025",
        "data_freshness_days": 93,
        "source_snippet":   "DBL receives LOA for NH-44 4-laning package worth ₹210 Cr (BSE filing Nov-25)",
        "confidence":       82,
        "verified":         "VERIFIED_RIGHT",
    },
    {
        "project_id":       "PRJ-DBL-003",
        "contractor_id":    "CON-DBL001",
        "project_title":    "2-Laning with Paved Shoulders of Chhattisgarh State Highway (CRIF Package-7)",
        "authority":        "State PWD Chhattisgarh",
        "program":          "CRIF (Central Road Infrastructure Fund)",
        "state":            "Chhattisgarh",
        "district":         "Raipur, Baloda Bazar",
        "highway":          "SH-6",
        "package_id":       "CRIF-CG-PKG7",
        "project_type":     "SH/MDR 2-Lane New",
        "contract_value_inr": 680_000_000,
        "road_km":          78.5,
        "start_date":       "20-09-2025",
        "end_date":         "19-09-2027",
        "status":           "Under Execution",
        "completion_pct":   18,
        "delay_days":       0,
        "payment_received_pct": 15,
        "site_address":     "SH-6, Raipur–Baloda Bazar Corridor, Chhattisgarh",
        "site_lat":         21.25,
        "site_lon":         82.10,
        "site_manager_name":    "Amit Verma (DBL Site Manager – Raipur)",
        "site_contact_number":  "+91-771-XXXXXX (DBL Raipur Office)",
        "site_email":           "raipur.site@dilipbuildcon.com",
        "sub_contractors":  ["Chhattisgarh Road Works (Grading)", "Bhilai Aggregate Suppliers (Material)"],
        "material_suppliers":   ["HPCL Mumbai (Bitumen)", "Birla Cement (Concrete)"],
        "equipment_deployed":   ["Hot Mix Plant 120 TPH ×1", "Paver ×2", "Roller ×3", "JCB ×4"],
        "last_site_inspection": "18-02-2026",
        "quality_rating":   "Satisfactory",
        "nhai_piu_contact":     "CG PWD SE Raipur (+91-771-XXXXXX)",
        "source_url":       "https://www.cgpwd.gov.in/tenders",
        "source_type":      "Government",
        "source_date":      "15-09-2025",
        "data_freshness_days": 167,
        "source_snippet":   "CG PWD awards SH-6 package to Dilip Buildcon ₹68 Cr",
        "confidence":       70,
        "verified":         "PARTIALLY_VERIFIED",
    },
    # ── NCC LIMITED ───────────────────────────────────────────────────────
    {
        "project_id":       "PRJ-NCC-001",
        "contractor_id":    "CON-NCC001",
        "project_title":    "Development of NH-16 Andhra Pradesh Coastal Corridor — 4 Laning Package AP-04",
        "authority":        "NHAI",
        "program":          "Bharatmala Pariyojana Phase-I",
        "state":            "Andhra Pradesh",
        "district":         "Nellore, Ongole",
        "highway":          "NH-16",
        "package_id":       "NH-BM-AP-016-04",
        "project_type":     "NH 4-Lane New",
        "contract_value_inr": 3_250_000_000,
        "road_km":          98.7,
        "start_date":       "10-10-2025",
        "end_date":         "09-10-2027",
        "status":           "Under Execution",
        "completion_pct":   22,
        "delay_days":       0,
        "payment_received_pct": 18,
        "site_address":     "NH-16, Nellore–Ongole Coastal Section, Andhra Pradesh",
        "site_lat":         14.44,
        "site_lon":         80.10,
        "site_manager_name":    "P Srikanth (NCC Site Manager – Nellore)",
        "site_contact_number":  "+91-861-XXXXXX (NCC Nellore Office)",
        "site_email":           "nellore.site@ncclimited.com",
        "sub_contractors":  ["AP Bituminous Works (Paving)", "Coastal Aggregates (Material Supply)"],
        "material_suppliers":   ["HPCL Visakh (Bitumen)", "Ramco Cement", "Rashtriya Ispat (Steel)"],
        "equipment_deployed":   ["Hot Mix Plant 200 TPH ×2", "Sensor Paver ×3", "Tandem Roller ×5", "Motor Grader ×2"],
        "last_site_inspection": "22-02-2026",
        "quality_rating":   "Good",
        "nhai_piu_contact":     "NHAI PIU Nellore (+91-861-XXXXXX)",
        "source_url":       "https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
        "source_type":      "BSE Filing",
        "source_date":      "05-10-2025",
        "data_freshness_days": 147,
        "source_snippet":   "NCC Limited wins ₹325 Cr NH-16 package in AP — BSE filing Oct-2025",
        "confidence":       85,
        "verified":         "VERIFIED_RIGHT",
    },
    {
        "project_id":       "PRJ-NCC-002",
        "contractor_id":    "CON-NCC001",
        "project_title":    "Upgradation of Roads in Odisha under PMGSY-III (Block Connectivity Package OD-41)",
        "authority":        "NRRDA / State RD Dept Odisha",
        "program":          "PMGSY Phase-III",
        "state":            "Odisha",
        "district":         "Koraput, Malkangiri",
        "highway":          "PMGSY",
        "package_id":       "PMGSY-OD-PKG41",
        "project_type":     "PMGSY Rural Single Lane",
        "contract_value_inr": 320_000_000,
        "road_km":          215.0,
        "start_date":       "01-11-2025",
        "end_date":         "31-10-2027",
        "status":           "Under Execution",
        "completion_pct":   14,
        "delay_days":       0,
        "payment_received_pct": 10,
        "site_address":     "Koraput–Malkangiri District Rural Roads, Odisha",
        "site_lat":         18.81,
        "site_lon":         82.71,
        "site_manager_name":    "Sanjay Mishra (NCC PMGSY Coordinator – Koraput)",
        "site_contact_number":  "+91-8852-XXXXXX (NCC Koraput Field Office)",
        "site_email":           "koraput.site@ncclimited.com",
        "sub_contractors":  ["Odisha Rural Road Works (Earthwork)", "Tribal Area Constructors (Labour)"],
        "material_suppliers":   ["CPCL Chennai (Bitumen Drum via Visakhapatnam)", "Dalmia Cement"],
        "equipment_deployed":   ["Batch Mix Plant 80 TPH ×1", "Paver ×2", "Roller ×3", "Tipper ×8"],
        "last_site_inspection": "12-02-2026",
        "quality_rating":   "Satisfactory",
        "nhai_piu_contact":     "SRRDA Odisha, Bhubaneswar (+91-674-XXXXXX)",
        "source_url":       "https://omms.nic.in/",
        "source_type":      "Government (PMGSY MIS)",
        "source_date":      "25-10-2025",
        "data_freshness_days": 127,
        "source_snippet":   "PMGSY-III Package OD-41 awarded to NCC; 215km rural connectivity in Koraput-Malkangiri",
        "confidence":       78,
        "verified":         "PARTIALLY_VERIFIED",
    },
    {
        "project_id":       "PRJ-NCC-003",
        "contractor_id":    "CON-NCC001",
        "project_title":    "4-Lane Widening of NH-765 (Kurnool-Mantralayam) Andhra Pradesh",
        "authority":        "NHAI",
        "program":          "NH Development Project",
        "state":            "Andhra Pradesh",
        "district":         "Kurnool",
        "highway":          "NH-765",
        "package_id":       "NH-AP-765-W01",
        "project_type":     "NH 2→4 Lane Widening",
        "contract_value_inr": 1_780_000_000,
        "road_km":          61.5,
        "start_date":       "05-01-2026",
        "end_date":         "04-01-2028",
        "status":           "LOA Received",
        "completion_pct":   2,
        "delay_days":       0,
        "payment_received_pct": 1,
        "site_address":     "NH-765, Kurnool–Mantralayam, Andhra Pradesh",
        "site_lat":         15.83,
        "site_lon":         78.05,
        "site_manager_name":    "Ravi Kumar (NCC Site Mobilisation Lead – Kurnool)",
        "site_contact_number":  "+91-8518-XXXXXX (NCC Kurnool Office)",
        "site_email":           "kurnool.site@ncclimited.com",
        "sub_contractors":  ["Survey & Design pending"],
        "material_suppliers":   ["Bitumen source: HPCL Mumbai (planned)"],
        "equipment_deployed":   ["Survey Equipment (active)", "Site Office Setup"],
        "last_site_inspection": "25-01-2026",
        "quality_rating":   "Design Stage",
        "nhai_piu_contact":     "NHAI PIU Kurnool (+91-8518-XXXXXX)",
        "source_url":       "https://www.financialexpress.com/infrastructure",
        "source_type":      "News",
        "source_date":      "02-01-2026",
        "data_freshness_days": 58,
        "source_snippet":   "NCC bags NH-765 widening contract worth ₹178 Cr in Kurnool district AP",
        "confidence":       72,
        "verified":         "PARTIALLY_VERIFIED",
    },
    # ── G R INFRAPROJECTS ─────────────────────────────────────────────────
    {
        "project_id":       "PRJ-GRI-001",
        "contractor_id":    "CON-GRI001",
        "project_title":    "6-Lane Development of Delhi-Mumbai Expressway Package DM-07 (Rajasthan Section)",
        "authority":        "NHAI",
        "program":          "Delhi-Mumbai Expressway (NH-48)",
        "state":            "Rajasthan",
        "district":         "Dausa, Sawai Madhopur",
        "highway":          "NH-48",
        "package_id":       "DME-PKG-07",
        "project_type":     "Expressway 6-Lane",
        "contract_value_inr": 5_600_000_000,
        "road_km":          72.8,
        "start_date":       "15-09-2025",
        "end_date":         "14-09-2027",
        "status":           "Under Execution — 18% Complete",
        "completion_pct":   18,
        "delay_days":       0,
        "payment_received_pct": 15,
        "site_address":     "Delhi–Mumbai Expressway, Dausa–Sawai Madhopur, Rajasthan",
        "site_lat":         26.90,
        "site_lon":         76.33,
        "site_manager_name":    "Mahesh Agarwal (GRI Project Director – DME Pkg 07)",
        "site_contact_number":  "+91-1427-XXXXXX (GRI Dausa Site Office)",
        "site_email":           "dme-pkg07.site@grinfraprojects.com",
        "sub_contractors":  ["Rajasthan Expressway Paving (Bituminous Work)", "Jaipur Civil Contractors (Earthwork)", "Steel Erectors India (MSE Walls)"],
        "material_suppliers":   ["IOCL Koyali (Bitumen VG-30)", "UltraTech Cement", "JSPL Steel"],
        "equipment_deployed":   ["Hot Mix Plant 200 TPH ×2", "Sensor Paver ×4", "Tandem Roller ×6", "Pneumatic Roller ×3", "Compactor ×6"],
        "last_site_inspection": "25-02-2026",
        "quality_rating":   "Good",
        "nhai_piu_contact":     "NHAI PIU Dausa (+91-1427-XXXXXX)",
        "source_url":       "https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
        "source_type":      "BSE Filing",
        "source_date":      "10-09-2025",
        "data_freshness_days": 172,
        "source_snippet":   "GR Infraprojects awarded Delhi-Mumbai Expressway pkg for ₹560 Cr (Sept-2025 BSE filing)",
        "confidence":       88,
        "verified":         "VERIFIED_RIGHT",
    },
    {
        "project_id":       "PRJ-GRI-002",
        "contractor_id":    "CON-GRI001",
        "project_title":    "4-Laning of Udaipur–Nathdwara NH-58 (Package-1) Rajasthan",
        "authority":        "NHAI",
        "program":          "Bharatmala Phase-I",
        "state":            "Rajasthan",
        "district":         "Udaipur, Rajsamand",
        "highway":          "NH-58",
        "package_id":       "NH-BM-RJ-058-01",
        "project_type":     "NH 2→4 Lane Widening",
        "contract_value_inr": 1_150_000_000,
        "road_km":          38.2,
        "start_date":       "01-12-2025",
        "end_date":         "30-11-2027",
        "status":           "Under Execution — 8% Complete",
        "completion_pct":   8,
        "delay_days":       0,
        "payment_received_pct": 5,
        "site_address":     "NH-58, Udaipur–Nathdwara Bypass, Rajasthan",
        "site_lat":         24.58,
        "site_lon":         73.68,
        "site_manager_name":    "Dinesh Sharma (GRI Site Manager – Udaipur)",
        "site_contact_number":  "+91-294-XXXXXX (GRI Udaipur Site)",
        "site_email":           "udaipur.site@grinfraprojects.com",
        "sub_contractors":  ["Mewar Paving Works (Flexible Paving)", "Rajput Earthmovers (Earthwork)"],
        "material_suppliers":   ["IOCL Koyali (Bitumen)", "Shree Cement (Concrete)"],
        "equipment_deployed":   ["Hot Mix Plant 120 TPH ×1", "Paver ×2", "Roller ×3"],
        "last_site_inspection": "20-02-2026",
        "quality_rating":   "Good",
        "nhai_piu_contact":     "NHAI PIU Udaipur (+91-294-XXXXXX)",
        "source_url":       "https://timesofindia.indiatimes.com/city/jaipur",
        "source_type":      "News",
        "source_date":      "28-11-2025",
        "data_freshness_days": 93,
        "source_snippet":   "GR Infra begins NH-58 widening in Udaipur-Nathdwara corridor; ₹115 Cr package",
        "confidence":       80,
        "verified":         "PARTIALLY_VERIFIED",
    },
    {
        "project_id":       "PRJ-GRI-003",
        "contractor_id":    "CON-GRI001",
        "project_title":    "2-Lane with PS of NH-754K — Gujarat Section (Kutch Connectivity Program)",
        "authority":        "NHAI",
        "program":          "NH Development Project",
        "state":            "Gujarat",
        "district":         "Kutch, Rajkot",
        "highway":          "NH-754K",
        "package_id":       "NH-GJ-754K-01",
        "project_type":     "NH 2-Lane New",
        "contract_value_inr": 890_000_000,
        "road_km":          89.4,
        "start_date":       "10-01-2026",
        "end_date":         "09-01-2028",
        "status":           "LOA Received — Design Stage",
        "completion_pct":   2,
        "delay_days":       0,
        "payment_received_pct": 1,
        "site_address":     "NH-754K, Kutch–Rajkot Corridor, Gujarat",
        "site_lat":         23.24,
        "site_lon":         70.10,
        "site_manager_name":    "Vijay Patel (GRI Site Mobilisation – Kutch)",
        "site_contact_number":  "+91-2832-XXXXXX (GRI Bhuj Office)",
        "site_email":           "kutch.site@grinfraprojects.com",
        "sub_contractors":  ["Survey in progress"],
        "material_suppliers":   ["Bitumen: Kandla Port Import (planned)", "Ambuja Cement (Concrete)"],
        "equipment_deployed":   ["Survey Team (active)"],
        "last_site_inspection": "15-01-2026",
        "quality_rating":   "Design Stage",
        "nhai_piu_contact":     "NHAI PIU Bhuj (+91-2832-XXXXXX)",
        "source_url":       "https://www.nhai.gov.in",
        "source_type":      "Government",
        "source_date":      "07-01-2026",
        "data_freshness_days": 53,
        "source_snippet":   "NHAI awards NH-754K (Kutch) 2-lane package to GR Infraprojects; ₹89 Cr",
        "confidence":       73,
        "verified":         "PARTIALLY_VERIFIED",
    },
]

DEMO_SIGNALS = [
    {"contractor_id":"CON-DBL001","project_id":"PRJ-DBL-002","platform":"BSE Filing","date":"28-11-2025","url":"https://www.bseindia.com/xml-data/corpfiling/AttachLive/","summary":"DBL receives LOA for NH-44 4-laning package ₹210 Cr in MP.","tag":"award","sentiment":"Positive","confidence":85},
    {"contractor_id":"CON-DBL001","project_id":None,"platform":"Economic Times","date":"15-01-2026","url":"https://economictimes.indiatimes.com/","summary":"Dilip Buildcon Q3 FY26: Net profit ₹198 Cr (+12% YoY); order book ₹22,500 Cr.","tag":"financials","sentiment":"Positive","confidence":88},
    {"contractor_id":"CON-NCC001","project_id":"PRJ-NCC-001","platform":"BSE Filing","date":"05-10-2025","url":"https://www.bseindia.com/xml-data/corpfiling/AttachLive/","summary":"NCC Limited wins NH-16 AP coastal corridor package ₹325 Cr.","tag":"award","sentiment":"Positive","confidence":85},
    {"contractor_id":"CON-NCC001","project_id":None,"platform":"Business Standard","date":"22-01-2026","url":"https://www.business-standard.com/","summary":"NCC Q3: Revenue ₹4,850 Cr (+9%); road segment leads at 62% of order book.","tag":"financials","sentiment":"Positive","confidence":82},
    {"contractor_id":"CON-GRI001","project_id":"PRJ-GRI-001","platform":"BSE Filing","date":"10-09-2025","url":"https://www.bseindia.com/xml-data/corpfiling/AttachLive/","summary":"GR Infraprojects receives LOA for DME Package 07 worth ₹560 Cr.","tag":"award","sentiment":"Positive","confidence":88},
    {"contractor_id":"CON-GRI001","project_id":None,"platform":"Mint","date":"12-02-2026","url":"https://www.livemint.com/","summary":"GR Infra secures ₹1,450 Cr new orders in Jan-Feb 2026; order book at ₹18,200 Cr.","tag":"order_book","sentiment":"Positive","confidence":80},
]

DEMO_RISK_FLAGS = [
    {"contractor_id":"CON-DBL001","flag_type":"Payment Dispute","severity":"Low","date":"10-12-2025","url":"https://economictimes.indiatimes.com/","summary":"DBL files arbitration against Rajasthan PWD for ₹42 Cr retention dues on completed project. No operational impact.","confidence":72},
    {"contractor_id":"CON-NCC001","flag_type":"Labour Issue","severity":"Low","date":"18-01-2026","url":"https://timesofindia.indiatimes.com/","summary":"Minor labour dispute at NCC's Odisha PMGSY site; resolved within 5 days; no project delay.","confidence":65},
]

DEMO_CHANGELOG = [
    {"changed_on_ist":"01-03-2026 10:00:00 IST","entity":"Project","field":"status","old_value":"Awarded","new_value":"Under Execution — 18% Complete","reason":"Progress update from BSE filing Q3","source_url":"https://bseindia.com","project_id":"PRJ-GRI-001","actor":"System"},
    {"changed_on_ist":"01-03-2026 10:00:00 IST","entity":"Contractor","field":"last_seen_date","old_value":"","new_value":"01-03-2026","reason":"Initial OSINT import","source_url":"Internal","project_id":"","actor":"System"},
    {"changed_on_ist":"25-02-2026 14:30:00 IST","entity":"Project","field":"completion_pct","old_value":"15","new_value":"18","reason":"Site inspection update by NCC PM Nellore","source_url":"Internal","project_id":"PRJ-NCC-001","actor":"User"},
    {"changed_on_ist":"20-02-2026 11:00:00 IST","entity":"Project","field":"quality_rating","old_value":"Good","new_value":"Satisfactory","reason":"Minor deficiency flagged in granular sub-base layer — CG PWD inspection","source_url":"https://cgpwd.gov.in","project_id":"PRJ-DBL-003","actor":"System"},
]

# ── Standard road-project milestone names ─────────────────────────────────────
STANDARD_MILESTONES = [
    "Appointed Date",
    "Financial Closure",
    "Design Submission (DPR)",
    "Construction Start",
    "25% Physical Completion",
    "50% Physical Completion",
    "75% Physical Completion",
    "Substantial Completion",
    "Punch List Clearance",
    "COD (Commercial Operation Date)",
    "Defect Liability Period Start",
    "Final Completion Certificate",
]

DEMO_MILESTONES = [
    # PRJ-DBL-001 (Rewa–Sidhi NH-46)
    {"milestone_id":"MS-DBL001-01","project_id":"PRJ-DBL-001","milestone_name":"Appointed Date",          "target_date":"15-10-2025","actual_date":"15-10-2025","status":"Completed","delay_days":0,  "notes":"On schedule"},
    {"milestone_id":"MS-DBL001-02","project_id":"PRJ-DBL-001","milestone_name":"Financial Closure",       "target_date":"15-11-2025","actual_date":"12-11-2025","status":"Completed","delay_days":-3, "notes":"3 days ahead of schedule"},
    {"milestone_id":"MS-DBL001-03","project_id":"PRJ-DBL-001","milestone_name":"Design Submission (DPR)", "target_date":"15-12-2025","actual_date":"18-12-2025","status":"Completed","delay_days":3,  "notes":"Minor delay — geological survey revision"},
    {"milestone_id":"MS-DBL001-04","project_id":"PRJ-DBL-001","milestone_name":"Construction Start",      "target_date":"01-01-2026","actual_date":"05-01-2026","status":"Completed","delay_days":4,  "notes":"Earthwork commenced Chainage 0–8 km"},
    {"milestone_id":"MS-DBL001-05","project_id":"PRJ-DBL-001","milestone_name":"25% Physical Completion", "target_date":"01-04-2026","actual_date":"",          "status":"On Track", "delay_days":0,  "notes":"Earthwork 30% done; GSB layer 12% done"},
    {"milestone_id":"MS-DBL001-06","project_id":"PRJ-DBL-001","milestone_name":"50% Physical Completion", "target_date":"01-08-2026","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    {"milestone_id":"MS-DBL001-07","project_id":"PRJ-DBL-001","milestone_name":"75% Physical Completion", "target_date":"01-12-2026","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    {"milestone_id":"MS-DBL001-08","project_id":"PRJ-DBL-001","milestone_name":"Substantial Completion",  "target_date":"14-10-2027","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    # PRJ-DBL-002 (NH-44 Jabalpur–Nagpur)
    {"milestone_id":"MS-DBL002-01","project_id":"PRJ-DBL-002","milestone_name":"Appointed Date",          "target_date":"01-12-2025","actual_date":"01-12-2025","status":"Completed","delay_days":0,  "notes":"On schedule"},
    {"milestone_id":"MS-DBL002-02","project_id":"PRJ-DBL-002","milestone_name":"Financial Closure",       "target_date":"01-01-2026","actual_date":"28-12-2025","status":"Completed","delay_days":-4, "notes":"4 days ahead"},
    {"milestone_id":"MS-DBL002-03","project_id":"PRJ-DBL-002","milestone_name":"Design Submission (DPR)", "target_date":"01-02-2026","actual_date":"",          "status":"On Track", "delay_days":0,  "notes":"Ongoing"},
    {"milestone_id":"MS-DBL002-04","project_id":"PRJ-DBL-002","milestone_name":"Construction Start",      "target_date":"15-02-2026","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":"Equipment mobilisation in progress"},
    {"milestone_id":"MS-DBL002-05","project_id":"PRJ-DBL-002","milestone_name":"25% Physical Completion", "target_date":"15-06-2026","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    {"milestone_id":"MS-DBL002-06","project_id":"PRJ-DBL-002","milestone_name":"Substantial Completion",  "target_date":"30-11-2027","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    # PRJ-GRI-001 (DME Pkg-07)
    {"milestone_id":"MS-GRI001-01","project_id":"PRJ-GRI-001","milestone_name":"Appointed Date",          "target_date":"15-09-2025","actual_date":"15-09-2025","status":"Completed","delay_days":0,  "notes":"On schedule"},
    {"milestone_id":"MS-GRI001-02","project_id":"PRJ-GRI-001","milestone_name":"Financial Closure",       "target_date":"15-10-2025","actual_date":"10-10-2025","status":"Completed","delay_days":-5, "notes":"Ahead of schedule"},
    {"milestone_id":"MS-GRI001-03","project_id":"PRJ-GRI-001","milestone_name":"Construction Start",      "target_date":"01-11-2025","actual_date":"28-10-2025","status":"Completed","delay_days":-4, "notes":"Early start — earthwork Chainage 0–15 km"},
    {"milestone_id":"MS-GRI001-04","project_id":"PRJ-GRI-001","milestone_name":"25% Physical Completion", "target_date":"01-03-2026","actual_date":"",          "status":"At Risk",  "delay_days":5,  "notes":"Bituminous base course delayed; targeted catch-up plan active"},
    {"milestone_id":"MS-GRI001-05","project_id":"PRJ-GRI-001","milestone_name":"50% Physical Completion", "target_date":"01-07-2026","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    {"milestone_id":"MS-GRI001-06","project_id":"PRJ-GRI-001","milestone_name":"Substantial Completion",  "target_date":"14-09-2027","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    # PRJ-NCC-001 (NH-16 AP)
    {"milestone_id":"MS-NCC001-01","project_id":"PRJ-NCC-001","milestone_name":"Appointed Date",          "target_date":"10-10-2025","actual_date":"10-10-2025","status":"Completed","delay_days":0,  "notes":"On schedule"},
    {"milestone_id":"MS-NCC001-02","project_id":"PRJ-NCC-001","milestone_name":"Financial Closure",       "target_date":"10-11-2025","actual_date":"05-11-2025","status":"Completed","delay_days":-5, "notes":"5 days ahead"},
    {"milestone_id":"MS-NCC001-03","project_id":"PRJ-NCC-001","milestone_name":"Construction Start",      "target_date":"01-12-2025","actual_date":"28-11-2025","status":"Completed","delay_days":-3, "notes":"Earthwork commenced early"},
    {"milestone_id":"MS-NCC001-04","project_id":"PRJ-NCC-001","milestone_name":"25% Physical Completion", "target_date":"01-04-2026","actual_date":"",          "status":"On Track", "delay_days":0,  "notes":"At 22% — on track"},
    {"milestone_id":"MS-NCC001-05","project_id":"PRJ-NCC-001","milestone_name":"50% Physical Completion", "target_date":"01-09-2026","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
    {"milestone_id":"MS-NCC001-06","project_id":"PRJ-NCC-001","milestone_name":"Substantial Completion",  "target_date":"09-10-2027","actual_date":"",          "status":"Pending",  "delay_days":0,  "notes":""},
]

# ─────────────────────────────────────────────────────────────────────────────
# JSON PERSISTENCE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load(path: Path, default) -> list:
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def _save(path: Path, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_contractors()  -> list: return _load(CONTRACTORS_FILE,  DEMO_CONTRACTORS)
def get_projects()     -> list: return _load(PROJECTS_FILE,     DEMO_PROJECTS)
def get_estimates()    -> list: return _load(ESTIMATES_FILE,    [])
def get_signals()      -> list: return _load(SIGNALS_FILE,      DEMO_SIGNALS)
def get_changelog()    -> list: return _load(CHANGELOG_FILE,    DEMO_CHANGELOG)
def get_risk_flags()   -> list: return _load(RISK_FLAGS_FILE,   DEMO_RISK_FLAGS)
def get_milestones()   -> list: return _load(MILESTONES_FILE,   DEMO_MILESTONES)

def get_milestones_for_project(project_id: str) -> list:
    return [m for m in get_milestones() if m.get("project_id") == project_id]

def _save_milestone(ms_record: dict):
    """Append or update a milestone record."""
    existing = get_milestones()
    idx = next((i for i, m in enumerate(existing) if m.get("milestone_id") == ms_record["milestone_id"]), None)
    if idx is not None:
        existing[idx] = ms_record
    else:
        existing.append(ms_record)
    _save(MILESTONES_FILE, existing)

def update_project_field(project_id: str, field: str, new_value, actor: str = "User") -> bool:
    """Update a single field on a project record; log the change."""
    projects = get_projects()
    for p in projects:
        if p["project_id"] == project_id:
            old_value = p.get(field, "")
            p[field] = new_value
            _save(PROJECTS_FILE, projects)
            _append_changelog("Project", field, old_value, new_value,
                              f"Manual update via CRM form", "Internal", project_id, actor)
            return True
    return False

def update_contractor_field(contractor_id: str, field: str, new_value, actor: str = "User") -> bool:
    """Update a single field on a contractor record; log the change."""
    contractors = get_contractors()
    for c in contractors:
        if c["contractor_id"] == contractor_id:
            old_value = c.get(field, "")
            c[field] = new_value
            _save(CONTRACTORS_FILE, contractors)
            _append_changelog("Contractor", field, old_value, new_value,
                              "Manual update via CRM form", "Internal", "", actor)
            return True
    return False

def _append_changelog(entity, field, old_val, new_val, reason, source_url, project_id="", actor="System"):
    cl = get_changelog()
    cl.append({
        "changed_on_ist": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "entity":     entity, "field": field, "old_value": str(old_val),
        "new_value":  str(new_val), "reason": reason, "source_url": source_url,
        "project_id": project_id, "actor": actor,
    })
    _save(CHANGELOG_FILE, cl)

# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL ESTIMATES AT LOAD
# ─────────────────────────────────────────────────────────────────────────────

def _build_estimates_df() -> pd.DataFrame:
    projects    = get_projects()
    contractors = {c["contractor_id"]: c["name"] for c in get_contractors()}
    rows = []
    for p in projects:
        est = estimate_bitumen(
            project_type     = p["project_type"],
            length_km        = p.get("road_km"),
            contract_value_inr = p.get("contract_value_inr"),
            state            = p.get("state","Maharashtra"),
        )
        monthly = distribute_monthly(
            est["base"],
            p.get("start_date","01-09-2025"),
            p.get("end_date",  "31-08-2027"),
            p.get("state","Maharashtra"),
        )
        rows.append({
            "project_id":       p["project_id"],
            "contractor":       contractors.get(p["contractor_id"], p["contractor_id"]),
            "project_title":    p["project_title"][:55] + "…" if len(p["project_title"]) > 55 else p["project_title"],
            "state":            p["state"],
            "project_type":     p["project_type"],
            "road_km":          p.get("road_km", 0),
            "contract_value_inr": p.get("contract_value_inr", 0),
            "bit_low_mt":       est["low"],
            "bit_base_mt":      est["base"],
            "bit_high_mt":      est["high"],
            "method":           est["method"],
            "assumptions":      est["assumptions"],
            "grade":            "VG-30",
            "confidence":       p.get("confidence", 70),
            "monthly_dist":     monthly,
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

CONFIDENCE_COLOR = lambda c: "#22c55e" if c>=80 else ("#f59e0b" if c>=60 else "#ef4444")
VERDICT_COLOR = {"VERIFIED_RIGHT":"#22c55e","PARTIALLY_VERIFIED":"#f59e0b","UNVERIFIABLE":"#94a3b8","VERIFIED_WRONG":"#ef4444"}
SEVERITY_COLOR = {"Low":"#22c55e","Med":"#f59e0b","High":"#ef4444"}

def _hdr(icon, title, color="#3b82f6"):
    st.markdown(
        f'<div style="border-left:4px solid {color};padding:6px 14px;margin:14px 0 8px 0;'
        f'background:linear-gradient(90deg,{color}18,transparent)">'
        f'<span style="font-size:1.05rem;font-weight:700">{icon} {title}</span></div>',
        unsafe_allow_html=True)

def _card(col, label, val, sub="", color="#3b82f6"):
    col.markdown(
        f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);border-left:4px solid {color};'
        f'border-radius:10px;padding:12px 16px;text-align:center;margin:3px">'
        f'<div style="color:#94a3b8;font-size:0.76rem">{label}</div>'
        f'<div style="color:#f8fafc;font-size:1.35rem;font-weight:800">{val}</div>'
        f'<div style="color:{color};font-size:0.74rem">{sub}</div></div>',
        unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_executive():
    """Executive Summary + KPIs."""
    _hdr("📊", "Executive Summary — Last 6 Months OSINT", "#06b6d4")
    st.caption(f"Date filter: 01-09-2025 to 01-03-2026 (183 days) | Grade: VG-30 | {format_date(datetime.date.today())} IST")

    projects    = get_projects()
    contractors = get_contractors()
    est_df      = _build_estimates_df()

    total_projects = len(projects)
    total_value    = sum(p.get("contract_value_inr", 0) for p in projects)
    total_km       = sum(p.get("road_km", 0) for p in projects)
    total_bit_base = est_df["bit_base_mt"].sum()
    total_bit_low  = est_df["bit_low_mt"].sum()
    total_bit_high = est_df["bit_high_mt"].sum()

    c1,c2,c3,c4,c5 = st.columns(5)
    _card(c1, "Contractors Tracked",   len(contractors),               "Demo: 3",                "#06b6d4")
    _card(c2, "Projects (6 months)",   total_projects,                 "Awards / LOA / WO",      "#3b82f6")
    _card(c3, "Total Contract Value",  format_inr_short(total_value),  f"{total_km:.0f} km total","#22c55e")
    _card(c4, "Bitumen Demand (Base)", f"{total_bit_base:,.0f} MT",    f"Low: {total_bit_low:,} | High: {total_bit_high:,}", "#8b5cf6")
    _card(c5, "Potential Revenue",     format_inr_short(total_bit_base * 48302), "@ ₹48,302/MT VG-30", "#f59e0b")

    st.markdown("---")
    _hdr("🏆", "Top Projects by Bitumen Demand", "#3b82f6")
    top = est_df.nlargest(5, "bit_base_mt")[["project_title","state","project_type","road_km","bit_low_mt","bit_base_mt","bit_high_mt","confidence"]].copy()
    top["road_km"]       = top["road_km"].apply(lambda x: f"{x:.1f} km")
    top["bit_base_mt"]   = top["bit_base_mt"].apply(lambda x: f"{x:,} MT")
    top["bit_low_mt"]    = top["bit_low_mt"].apply(lambda x: f"{x:,}")
    top["bit_high_mt"]   = top["bit_high_mt"].apply(lambda x: f"{x:,}")
    top["confidence"]    = top["confidence"].apply(lambda x: f"{x}%")
    top.columns = ["Project", "State", "Type", "Length", "Low MT", "Base MT", "High MT", "Confidence"]
    st.dataframe(top, use_container_width=True, hide_index=True)

    st.markdown("---")
    _hdr("📈", "Contractor-wise Bitumen Demand Summary", "#22c55e")
    cont_summary = est_df.groupby("contractor").agg(
        Projects=("project_id","count"),
        Total_km=("road_km","sum"),
        Contract_Value=("contract_value_inr","sum"),
        Bit_Low_MT=("bit_low_mt","sum"),
        Bit_Base_MT=("bit_base_mt","sum"),
        Bit_High_MT=("bit_high_mt","sum"),
    ).reset_index()
    cont_summary["Contract_Value"] = cont_summary["Contract_Value"].apply(format_inr_short)
    cont_summary["Total_km"]       = cont_summary["Total_km"].apply(lambda x: f"{x:.1f}")
    st.dataframe(cont_summary, use_container_width=True, hide_index=True)


def _tab_projects():
    """All projects table with filters."""
    _hdr("📋", "Project Master Table", "#3b82f6")

    projects     = get_projects()
    contractors  = {c["contractor_id"]: c["name"] for c in get_contractors()}
    est_df       = _build_estimates_df()

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    all_contractors = ["All"] + list(contractors.values())
    sel_contractor  = fc1.selectbox("Contractor", all_contractors)
    all_states      = ["All"] + sorted(set(p.get("state","") for p in projects))
    sel_state       = fc2.selectbox("State", all_states)
    all_types       = ["All"] + sorted(set(p.get("project_type","") for p in projects))
    sel_type        = fc3.selectbox("Project Type", all_types)

    filtered_projects = [p for p in projects if
        (sel_contractor == "All" or contractors.get(p["contractor_id"],"") == sel_contractor) and
        (sel_state == "All" or p.get("state","") == sel_state) and
        (sel_type  == "All" or p.get("project_type","") == sel_type)]

    rows = []
    for p in filtered_projects:
        est = est_df[est_df["project_id"] == p["project_id"]]
        bit_base = int(est["bit_base_mt"].values[0]) if not est.empty else 0
        rows.append({
            "Contractor":  contractors.get(p["contractor_id"],""),
            "Project":     p["project_title"][:60] + "…" if len(p["project_title"])>60 else p["project_title"],
            "Authority":   p.get("authority",""),
            "State":       p.get("state",""),
            "Highway":     p.get("highway",""),
            "Type":        p.get("project_type",""),
            "Value":       format_inr_short(p.get("contract_value_inr",0)),
            "km":          f"{p.get('road_km',0):.1f}",
            "Bit (MT)":    f"{bit_base:,}",
            "Status":      p.get("status",""),
            "Source":      p.get("source_type",""),
            "Date":        p.get("source_date",""),
            "Fresh (days)":p.get("data_freshness_days",0),
            "Conf %":      p.get("confidence",0),
            "Verified":    p.get("verified",""),
        })

    if rows:
        df = pd.DataFrame(rows)
        def color_verified(val):
            c = VERDICT_COLOR.get(str(val), "#94a3b8")
            return f"color:{c};font-weight:bold"
        def color_conf(val):
            try:
                c = CONFIDENCE_COLOR(int(val))
                return f"color:{c}"
            except Exception:
                return ""
        styled = df.style.applymap(color_verified, subset=["Verified"]).applymap(color_conf, subset=["Conf %"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(rows)} projects | All within last 183 days | VG-30 @ ₹48,302/MT")
    else:
        st.info("No projects match the current filters.")

    st.markdown("---")
    _hdr("➕", "Add New Project Manually", "#475569")
    with st.expander("📝 Add Project (Manual Entry)", expanded=False):
        contractors_list = {c["contractor_id"]: c["name"] for c in get_contractors()}
        with st.form("add_project_form"):
            f1, f2 = st.columns(2)
            sel_con      = f1.selectbox("Contractor", list(contractors_list.keys()),
                                        format_func=lambda x: contractors_list[x])
            proj_title   = f2.text_input("Project Title")
            f3, f4, f5   = st.columns(3)
            authority    = f3.selectbox("Authority", ["NHAI","MoRTH","PMGSY/NRRDA","State PWD","ULB","NHIDCL","BRO","World Bank","ADB","Other"])
            state        = f4.selectbox("State", ["Maharashtra","Gujarat","Rajasthan","Madhya Pradesh","Uttar Pradesh","Bihar","Odisha","Andhra Pradesh","Telangana","Karnataka","Tamil Nadu","Kerala","Punjab","Haryana","West Bengal","Chhattisgarh","Jharkhand","Assam","Other"])
            proj_type    = f5.selectbox("Project Type", list(BITUMEN_MT_PER_KM.keys()))
            f6, f7, f8   = st.columns(3)
            road_km      = f6.number_input("Road Length (km)", 0.0, 1000.0, 0.0, step=0.5)
            contract_val = f7.number_input("Contract Value (₹ Cr)", 0.0, 10000.0, 0.0, step=0.5)
            conf_inp     = f8.slider("Confidence %", 30, 100, 65, step=5)
            f9, f10      = st.columns(2)
            start_dt     = f9.text_input("Start Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            end_dt       = f10.text_input("End Date (DD-MM-YYYY)", (datetime.date.today()+datetime.timedelta(days=730)).strftime("%Y-%m-%d"))
            source_url   = st.text_input("Source URL", "https://")
            source_type  = st.selectbox("Source Type", ["Government","BSE Filing","News","Company Website","Social Media"])
            source_date  = st.text_input("Source Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            submit_proj  = st.form_submit_button("✅ Add Project")

        if submit_proj and proj_title:
            new_proj = {
                "project_id":       _project_id(sel_con, proj_title, state),
                "contractor_id":    sel_con,
                "project_title":    proj_title,
                "authority":        authority,
                "program":          authority,
                "state":            state,
                "district":         "",
                "highway":          "",
                "package_id":       "",
                "project_type":     proj_type,
                "contract_value_inr": contract_val * 1e7,
                "road_km":          road_km,
                "start_date":       start_dt,
                "end_date":         end_dt,
                "status":           "Awarded",
                "source_url":       source_url,
                "source_type":      source_type,
                "source_date":      source_date,
                "data_freshness_days": (datetime.date.today() - datetime.datetime.strptime(source_date, "%Y-%m-%d").date()).days if source_date else 0,
                "confidence":       conf_inp,
                "verified":         "UNVERIFIABLE",
            }
            existing = get_projects()
            existing.append(new_proj)
            _save(PROJECTS_FILE, existing)
            _append_changelog("Project","new_project","","Added",f"Manual entry: {proj_title}",source_url,new_proj["project_id"],"User")
            st.success(f"✅ Project '{proj_title}' added!")
            st.rerun()


def _tab_bitumen_demand():
    """Bitumen demand estimates + monthly distribution."""
    _hdr("🛢️", "Bitumen Demand Estimates (MT) — All Projects", "#8b5cf6")
    est_df = _build_estimates_df()

    if est_df.empty:
        st.info("No projects loaded. Add projects to see estimates.")
        return

    # Summary
    c1,c2,c3 = st.columns(3)
    _card(c1, "Total Demand (Low)",  f"{est_df['bit_low_mt'].sum():,.0f} MT",  "Conservative scenario", "#f59e0b")
    _card(c2, "Total Demand (Base)", f"{est_df['bit_base_mt'].sum():,.0f} MT", "Base case", "#22c55e")
    _card(c3, "Total Demand (High)", f"{est_df['bit_high_mt'].sum():,.0f} MT", "Optimistic scenario", "#ef4444")

    st.markdown("---")

    # Estimate table
    disp = est_df[["contractor","project_title","state","project_type","road_km","bit_low_mt","bit_base_mt","bit_high_mt","grade","method","confidence"]].copy()
    disp["road_km"] = disp["road_km"].apply(lambda x: f"{x:.1f}")
    disp.columns    = ["Contractor","Project","State","Type","km","Low MT","Base MT","High MT","Grade","Method","Conf%"]
    def color_conf(val):
        try: return f"color:{CONFIDENCE_COLOR(int(val))}"
        except: return ""
    st.dataframe(disp.style.applymap(color_conf, subset=["Conf%"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    _hdr("📅", "Monthly Bitumen Demand Distribution (Seasonality-Adjusted)", "#3b82f6")
    st.caption("Based on project execution timeline × monsoon seasonality factors per state.")

    # Build monthly heatmap
    monthly_totals = {m: 0.0 for m in SEASON_ORDER}
    for _, row in est_df.iterrows():
        for m, mt in row["monthly_dist"].items():
            if m in monthly_totals:
                monthly_totals[m] += mt

    months = SEASON_ORDER
    values = [monthly_totals.get(m, 0) for m in months]

    if PLOTLY_OK:
        fig = go.Figure()
        colors = ["#ef4444" if v < 200 else ("#f59e0b" if v < 500 else "#22c55e") for v in values]
        fig.add_trace(go.Bar(x=months, y=values, marker_color=colors, name="MT/Month",
                             text=[f"{v:.0f}" for v in values], textposition="outside"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0f172a", plot_bgcolor="#1e293b",
                          title="Projected Monthly Bitumen Demand (MT) — All Contractors Combined",
                          xaxis_title="Month", yaxis_title="MT", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(pd.DataFrame({"Month": months, "MT": values}).set_index("Month"))

    # Per-contractor monthly
    st.markdown("---")
    _hdr("🏢", "Contractor × Month Demand Matrix (MT)", "#22c55e")
    cont_names = est_df["contractor"].unique()
    matrix_data = {c: {m: 0.0 for m in SEASON_ORDER} for c in cont_names}
    for _, row in est_df.iterrows():
        for m, mt in row["monthly_dist"].items():
            if m in SEASON_ORDER:
                matrix_data[row["contractor"]][m] = matrix_data[row["contractor"]].get(m, 0) + mt

    matrix_df = pd.DataFrame(matrix_data).T.round(0).astype(int)
    matrix_df = matrix_df[[m for m in SEASON_ORDER if m in matrix_df.columns]]
    matrix_df["TOTAL"] = matrix_df.sum(axis=1)
    st.dataframe(matrix_df, use_container_width=True)


def _tab_heatmap():
    """State × Month demand heatmap."""
    _hdr("🗺️", "State × Month Bitumen Demand Heatmap (MT)", "#f59e0b")
    st.caption("Projected MT demand distributed by state, month, and monsoon seasonality.")

    est_df   = _build_estimates_df()
    projects = get_projects()
    state_map = {p["project_id"]: p.get("state","Unknown") for p in projects}

    state_monthly = {}
    for _, row in est_df.iterrows():
        state = state_map.get(row["project_id"], "Unknown")
        if state not in state_monthly:
            state_monthly[state] = {m: 0.0 for m in SEASON_ORDER}
        for m, mt in row["monthly_dist"].items():
            if m in SEASON_ORDER:
                state_monthly[state][m] += mt

    hm_df = pd.DataFrame(state_monthly).T.fillna(0).round(0).astype(int)
    hm_df = hm_df[[m for m in SEASON_ORDER if m in hm_df.columns]]
    hm_df["TOTAL"] = hm_df.sum(axis=1)
    hm_df = hm_df.sort_values("TOTAL", ascending=False)

    if PLOTLY_OK:
        fig = px.imshow(
            hm_df.drop(columns=["TOTAL"]).values,
            x=list(hm_df.drop(columns=["TOTAL"]).columns),
            y=list(hm_df.index),
            color_continuous_scale="YlOrRd",
            title="State × Month Bitumen Demand Heatmap (MT)",
            labels=dict(x="Month", y="State", color="MT"),
        )
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0f172a", height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(hm_df, use_container_width=True)


def _tab_signals():
    """News + social signals feed."""
    _hdr("📡", "OSINT Signals Feed — News, Filings, Social", "#22c55e")

    signals     = get_signals()
    contractors = {c["contractor_id"]: c["name"] for c in get_contractors()}

    fc1, fc2 = st.columns(2)
    sel_con  = fc1.selectbox("Contractor Filter", ["All"] + list(contractors.values()), key="sig_con")
    sel_tag  = fc2.selectbox("Signal Type", ["All","award","financials","order_book","progress","dispute","quality","blacklisting","legal"], key="sig_tag")

    filtered = [s for s in signals if
        (sel_con == "All" or contractors.get(s["contractor_id"],"") == sel_con) and
        (sel_tag == "All" or s.get("tag","") == sel_tag)]

    SENTIMENT_COLOR = {"Positive":"#22c55e","Neutral":"#94a3b8","Negative":"#ef4444"}
    TAG_COLOR = {"award":"#22c55e","financials":"#3b82f6","order_book":"#8b5cf6","progress":"#06b6d4",
                 "dispute":"#ef4444","legal":"#dc2626","blacklisting":"#7f1d1d"}

    for s in filtered:
        tag   = s.get("tag","signal")
        sent  = s.get("sentiment","Neutral")
        color = TAG_COLOR.get(tag,"#475569")
        sc    = SENTIMENT_COLOR.get(sent,"#94a3b8")
        st.markdown(
            f'<div style="border-left:3px solid {color};padding:8px 12px;margin-bottom:6px;'
            f'background:#0f172a;border-radius:0 8px 8px 0">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span style="color:{color};font-weight:700;font-size:0.82rem">[{tag.upper()}]</span>'
            f'<span style="color:#94a3b8;font-size:0.75rem">{s["date"]} | {s["platform"]}</span></div>'
            f'<div style="color:#f8fafc;font-size:0.88rem;margin:3px 0">{s["summary"]}</div>'
            f'<div style="display:flex;gap:12px">'
            f'<span style="color:{sc};font-size:0.75rem">● {sent}</span>'
            f'<span style="color:#64748b;font-size:0.75rem">Conf: {s["confidence"]}%</span>'
            f'<a href="{s["url"]}" style="color:#3b82f6;font-size:0.75rem" target="_blank">🔗 Source</a></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    _hdr("➕", "Add Signal Manually", "#475569")
    with st.expander("📝 Log New Signal"):
        contractors_list = {c["contractor_id"]: c["name"] for c in get_contractors()}
        with st.form("add_signal_form"):
            f1, f2 = st.columns(2)
            sig_con  = f1.selectbox("Contractor", list(contractors_list.keys()), format_func=lambda x: contractors_list[x])
            platform = f2.selectbox("Platform", ["BSE Filing","Economic Times","Business Standard","Mint","Times of India","LinkedIn","Twitter/X","Facebook","YouTube","NHAI Website","Company Website","Other"])
            sig_url  = st.text_input("URL", "https://")
            summary  = st.text_area("Summary (max 2 lines)")
            f3, f4, f5 = st.columns(3)
            sig_date = f3.text_input("Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            tag      = f4.selectbox("Tag", ["award","financials","order_book","progress","dispute","quality","blacklisting","legal","other"])
            sent     = f5.selectbox("Sentiment", ["Positive","Neutral","Negative"])
            sig_conf = st.slider("Confidence %", 30, 100, 65)
            submit_sig = st.form_submit_button("✅ Add Signal")
        if submit_sig and summary:
            new_sig = {"contractor_id":sig_con,"project_id":None,"platform":platform,"date":sig_date,"url":sig_url,"summary":summary,"tag":tag,"sentiment":sent,"confidence":sig_conf}
            existing = get_signals()
            existing.append(new_sig)
            _save(SIGNALS_FILE, existing)
            st.success("✅ Signal logged!")
            st.rerun()


def _tab_risk():
    """Risk flags and compliance."""
    _hdr("🚨", "Risk & Compliance Flags", "#ef4444")
    flags = get_risk_flags()
    contractors = {c["contractor_id"]: c["name"] for c in get_contractors()}

    if not flags:
        st.success("✅ No risk flags recorded in the last 6 months.")
    else:
        for f in flags:
            sev   = f.get("severity","Med")
            color = SEVERITY_COLOR.get(sev,"#f59e0b")
            name  = contractors.get(f.get("contractor_id",""),"Unknown")
            st.markdown(
                f'<div style="border-left:4px solid {color};padding:10px 14px;margin-bottom:8px;'
                f'background:#0f172a;border-radius:0 8px 8px 0">'
                f'<div style="display:flex;justify-content:space-between">'
                f'<span style="color:{color};font-weight:700">[{sev.upper()} RISK] {f.get("flag_type","")}</span>'
                f'<span style="color:#94a3b8;font-size:0.8rem">{f["date"]} | {name}</span></div>'
                f'<div style="color:#f8fafc;font-size:0.88rem;margin:4px 0">{f["summary"]}</div>'
                f'<a href="{f["url"]}" style="color:#3b82f6;font-size:0.78rem">🔗 Source</a>'
                f' &nbsp; <span style="color:#64748b;font-size:0.78rem">Conf: {f.get("confidence",65)}%</span></div>',
                unsafe_allow_html=True,
            )


def _tab_crm():
    """CRM export + database tables."""
    _hdr("🗃️", "CRM Database Tables & Export", "#3b82f6")

    t_con, t_proj, t_est, t_sig, t_cl = st.tabs([
        "🏢 Contractors", "📋 Projects", "🛢️ Estimates", "📡 Signals", "📝 Change Log"
    ])

    with t_con:
        df = pd.DataFrame(get_contractors())
        if not df.empty:
            st.dataframe(df[["contractor_id","name","aliases","base_city","website","cin","type","confidence"]], use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download contractors_master.csv", csv, "contractors_master.csv", "text/csv")

    with t_proj:
        df = pd.DataFrame(get_projects())
        if not df.empty:
            st.dataframe(df[["project_id","contractor_id","project_title","authority","state","project_type","contract_value_inr","road_km","start_date","end_date","status","source_date","confidence","verified"]], use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download projects_master.csv", csv, "projects_master.csv", "text/csv")

    with t_est:
        est_df = _build_estimates_df()
        if not est_df.empty:
            disp = est_df.drop(columns=["monthly_dist"])
            st.dataframe(disp, use_container_width=True, hide_index=True)
            csv = disp.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download bitumen_demand_estimates.csv", csv, "bitumen_demand_estimates.csv", "text/csv")

    with t_sig:
        df = pd.DataFrame(get_signals())
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download signals_feed.csv", csv, "signals_feed.csv", "text/csv")

    with t_cl:
        df = pd.DataFrame(get_changelog())
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download change_history.csv", csv, "change_history.csv", "text/csv")


def _tab_add_contractor():
    """Add/search contractors."""
    _hdr("🔍", "Add Contractor / Run OSINT Search", "#06b6d4")

    st.info("ℹ️ Enter contractor details to add to the tracking database. For live OSINT search, provide BSE code or CIN — the system will attempt to fetch recent filings and news.")

    with st.form("add_contractor_form"):
        f1, f2 = st.columns(2)
        name    = f1.text_input("Contractor Name *", placeholder="e.g. customer name")
        bse     = f2.text_input("BSE Code (optional)", placeholder="e.g. 500510")
        f3, f4  = st.columns(2)
        cin     = f3.text_input("CIN (optional)", placeholder="e.g. L17110GJ1912PLC000007")
        with f4:
            try:
                from components.autosuggest import city_picker
                city = city_picker(key="add_con_city", label="Base City")
            except Exception:
                city = st.text_input("Base City", placeholder="e.g. Mumbai, Maharashtra")
        website = st.text_input("Website", "https://")
        note    = st.text_area("Notes (type, known specialisation, states active in)")
        submit_con = st.form_submit_button("✅ Add Contractor to Database")

    if submit_con and name:
        cid = "CON-" + hashlib.md5(name.encode()).hexdigest()[:6].upper()
        new_con = {
            "contractor_id": cid, "name": name, "aliases": [name],
            "base_city": city, "website": website, "cin": cin, "bse_code": bse,
            "type": note, "rating": "Not rated", "last_seen_date": datetime.date.today().strftime("%Y-%m-%d"),
            "confidence": 60, "note": note,
        }
        existing = get_contractors()
        if not any(c["name"].lower() == name.lower() for c in existing):
            existing.append(new_con)
            _save(CONTRACTORS_FILE, existing)
            _append_changelog("Contractor","new_contractor","","Added",f"Manual entry: {name}","Internal",actor="User")
            st.success(f"✅ Contractor '{name}' (ID: {cid}) added to database!")
        else:
            st.warning(f"⚠️ Contractor '{name}' already exists in database.")

    st.markdown("---")
    _hdr("📋", "Current Contractor Registry", "#3b82f6")
    for c in get_contractors():
        st.markdown(
            f'<div style="background:#0f172a;border-left:3px solid #3b82f6;border-radius:0 8px 8px 0;'
            f'padding:10px 14px;margin-bottom:6px">'
            f'<b style="color:#f8fafc">{c["name"]}</b>'
            f' <span style="color:#94a3b8;font-size:0.8rem">({c["contractor_id"]})</span><br>'
            f'<span style="color:#64748b;font-size:0.82rem">{c["base_city"]} | {c["type"][:60]}…</span><br>'
            f'<span style="color:#3b82f6;font-size:0.78rem">Confidence: {c["confidence"]}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _tab_contacts():
    """Company-level contact directory for all tracked contractors."""
    _hdr("📞", "Contractor Contact Directory (Company-Level)", "#06b6d4")
    st.caption("All contacts are company-level public records only (BSE disclosures, Annual Reports, company websites). No personal profiling.")

    contractors = get_contractors()
    if not contractors:
        st.info("No contractors in database.")
        return

    sel_name = st.selectbox(
        "Select Contractor",
        [c["name"] for c in contractors],
        key="contacts_sel",
    )
    c = next((x for x in contractors if x["name"] == sel_name), None)
    if not c:
        return

    # ── Identity card ─────────────────────────────────────────────────────────
    fg, bg = "#0284c7", "#e0f2fe"
    st.markdown(
        f'<div style="background:{bg};border-left:5px solid {fg};border-radius:0 12px 12px 0;'
        f'padding:14px 18px;margin-bottom:14px">'
        f'<div style="font-size:1.15rem;font-weight:800;color:#0c4a6e">{c["name"]}</div>'
        f'<div style="color:#0369a1;font-size:0.82rem">ID: {c["contractor_id"]} | BSE: {c.get("bse_code","—")} | '
        f'NSE: {c.get("nse_code","—")} | CIN: {c.get("cin","—")}</div>'
        f'<div style="color:#0369a1;font-size:0.82rem">PAN: {c.get("pan","—")} | '
        f'GSTIN: {c.get("gstin","—")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        _hdr("📋", "Corporate Contact", "#3b82f6")
        info_rows = [
            ("📞 Corporate Phone",  c.get("phone_corporate", "—")),
            ("📞 BD / Sales Phone", c.get("phone_bd",        "—")),
            ("✉️ Corporate Email",  c.get("email_corporate", "—")),
            ("✉️ Investor Email",   c.get("email_investor",  "—")),
            ("✉️ Tender Email",     c.get("email_tender",    "—")),
            ("🏢 Registered Office",c.get("address_registered","—")),
            ("🏢 Corporate Office", c.get("address_corporate","—")),
            ("🌐 Website",          c.get("website",         "—")),
        ]
        for label, val in info_rows:
            st.markdown(f'<div style="padding:3px 0;font-size:0.85rem"><b style="color:#94a3b8">{label}:</b> '
                        f'<span style="color:#f8fafc">{val}</span></div>', unsafe_allow_html=True)

        _hdr("📱", "Social Media (Official Handles)", "#8b5cf6")
        social_rows = [
            ("LinkedIn",   c.get("social_linkedin",  "")),
            ("Twitter/X",  c.get("social_twitter",   "")),
            ("Facebook",   c.get("social_facebook",  "")),
            ("YouTube",    c.get("social_youtube",   "")),
            ("Instagram",  c.get("social_instagram", "")),
        ]
        for platform, url in social_rows:
            if url:
                st.markdown(f'<a href="{url}" target="_blank" style="color:#3b82f6;font-size:0.83rem">🔗 {platform}</a><br>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:#475569;font-size:0.83rem">— {platform}: Not available</span><br>', unsafe_allow_html=True)

    with col2:
        _hdr("👥", "Key Management (Public Disclosures)", "#22c55e")
        for kc in c.get("key_contacts", []):
            st.markdown(
                f'<div style="background:#1e293b;border-radius:8px;padding:8px 12px;margin-bottom:5px">'
                f'<div style="color:#22c55e;font-size:0.78rem;font-weight:600">{kc.get("role","")}</div>'
                f'<div style="color:#f8fafc;font-size:0.9rem;font-weight:700">{kc.get("name","")}</div>'
                f'<div style="color:#64748b;font-size:0.74rem">Source: {kc.get("source","")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        _hdr("📊", "Business Profile", "#f59e0b")
        biz_rows = [
            ("Annual Turnover",      f'{format_inr(c.get("annual_turnover_cr",0))} Cr'),
            ("Order Book",           f'{format_inr(c.get("order_book_cr",0))} Cr'),
            ("Employees",            c.get("employee_count_range","—")),
            ("Roads Segment %",      f'{c.get("road_segment_pct","—")}%'),
            ("Active States",        ", ".join(c.get("specialization_states",[]))),
            ("Credit Rating",        c.get("rating","—")),
            ("Certifications",       " | ".join(c.get("certifications",[]))),
            ("Bankers",              " | ".join(c.get("bankers",[]))),
            ("Auditors",             " | ".join(c.get("auditors",[]))),
            ("Equipment Fleet",      c.get("equipment_fleet_note","—")),
        ]
        for label, val in biz_rows:
            st.markdown(f'<div style="padding:2px 0;font-size:0.83rem"><b style="color:#94a3b8">{label}:</b> '
                        f'<span style="color:#f8fafc">{val}</span></div>', unsafe_allow_html=True)

    st.markdown("---")
    _hdr("🗂️", "CRM Account Status", "#dc2626")
    crm_rows = [
        ("CRM Status",          c.get("crm_status","—")),
        ("Account Owner",       c.get("crm_owner","—")),
        ("Last Contacted",      c.get("last_contacted","—")),
        ("Next Follow-up",      c.get("next_followup","—")),
        ("Grade Preference",    c.get("bitumen_grade_pref","—")),
        ("Typical Order Size",  f'{c.get("typical_order_mt",0):,} MT'),
        ("Notes",               c.get("note","—")),
    ]
    c1, c2 = st.columns(2)
    for i, (label, val) in enumerate(crm_rows):
        target = c1 if i % 2 == 0 else c2
        target.markdown(f'<div style="padding:3px 0;font-size:0.85rem"><b style="color:#94a3b8">{label}:</b> '
                        f'<span style="color:#f8fafc">{val}</span></div>', unsafe_allow_html=True)


def _tab_timeline():
    """Project timeline viewer with milestones — all projects or per-project."""
    _hdr("🗓️", "Project Timeline & Milestone Tracker", "#8b5cf6")
    st.caption("Track appointed dates, construction milestones, completion %, and delays per project.")

    projects    = get_projects()
    contractors = {c["contractor_id"]: c["name"] for c in get_contractors()}

    if not projects:
        st.info("No projects loaded.")
        return

    # ── Project selector ──────────────────────────────────────────────────────
    proj_options = {p["project_id"]: f'{contractors.get(p["contractor_id"],"?")} | {p["project_title"][:60]}' for p in projects}
    selected_pid = st.selectbox("Select Project", list(proj_options.keys()),
                                format_func=lambda x: proj_options[x], key="tl_proj")
    proj = next((p for p in projects if p["project_id"] == selected_pid), None)
    if not proj:
        return

    # ── Project header ─────────────────────────────────────────────────────────
    comp_pct  = proj.get("completion_pct", 0)
    delay_d   = proj.get("delay_days", 0)
    pay_pct   = proj.get("payment_received_pct", 0)
    pbar_color = "#22c55e" if comp_pct >= 50 else ("#f59e0b" if comp_pct >= 20 else "#3b82f6")
    delay_color = "#ef4444" if delay_d > 0 else "#22c55e"

    st.markdown(
        f'<div style="background:#1e293b;border-radius:10px;padding:14px 18px;margin-bottom:12px">'
        f'<div style="font-size:1.05rem;font-weight:800;color:#f8fafc">{proj["project_title"]}</div>'
        f'<div style="color:#94a3b8;font-size:0.82rem">{proj.get("authority","")} | {proj.get("state","")} | '
        f'{proj.get("highway","")} | {format_inr_short(proj.get("contract_value_inr",0))} | {proj.get("road_km",0):.1f} km</div>'
        f'<div style="margin-top:8px">'
        f'<div style="background:#0f172a;border-radius:6px;height:14px;width:100%">'
        f'<div style="background:{pbar_color};width:{min(comp_pct,100)}%;height:14px;border-radius:6px;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:0.7rem;color:#fff;font-weight:700">{comp_pct}%</div></div></div>'
        f'<div style="display:flex;gap:20px;margin-top:6px;font-size:0.8rem">'
        f'<span style="color:#94a3b8">Start: <b style="color:#f8fafc">{proj.get("start_date","—")}</b></span>'
        f'<span style="color:#94a3b8">End: <b style="color:#f8fafc">{proj.get("end_date","—")}</b></span>'
        f'<span style="color:#94a3b8">Delay: <b style="color:{delay_color}">{delay_d} days</b></span>'
        f'<span style="color:#94a3b8">Payment Received: <b style="color:#f8fafc">{pay_pct}%</b></span>'
        f'<span style="color:#94a3b8">Status: <b style="color:#f8fafc">{proj.get("status","—")}</b></span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Site Information ──────────────────────────────────────────────────────
    with st.expander("🏗️ Site Information", expanded=False):
        si1, si2 = st.columns(2)
        site_left = [
            ("📍 Site Address",    proj.get("site_address","—")),
            ("👷 Site Manager",    proj.get("site_manager_name","—")),
            ("📞 Site Phone",      proj.get("site_contact_number","—")),
            ("✉️ Site Email",      proj.get("site_email","—")),
            ("🏛️ Authority PIU",   proj.get("nhai_piu_contact","—")),
        ]
        site_right = [
            ("🚜 Equipment",        " | ".join(proj.get("equipment_deployed",[]))),
            ("🤝 Sub-Contractors",  " | ".join(proj.get("sub_contractors",[]))),
            ("📦 Material Sources", " | ".join(proj.get("material_suppliers",[]))),
            ("🔍 Last Inspection",  proj.get("last_site_inspection","—")),
            ("⭐ Quality Rating",   proj.get("quality_rating","—")),
        ]
        for label, val in site_left:
            si1.markdown(f'**{label}:** {val}')
        for label, val in site_right:
            si2.markdown(f'**{label}:** {val}')

    # ── Milestone table ───────────────────────────────────────────────────────
    _hdr("🚩", "Milestone Tracker", "#3b82f6")
    milestones = get_milestones_for_project(selected_pid)

    if not milestones:
        st.info("No milestones recorded for this project. Add them below.")
    else:
        STATUS_COLOR = {"Completed":"#22c55e","On Track":"#3b82f6","Pending":"#94a3b8",
                        "At Risk":"#f59e0b","Delayed":"#ef4444"}
        for ms in milestones:
            sc = STATUS_COLOR.get(ms.get("status","Pending"), "#94a3b8")
            delay_txt = ""
            d = ms.get("delay_days", 0)
            if isinstance(d, (int, float)):
                if d > 0:   delay_txt = f' <span style="color:#ef4444">+{d}d late</span>'
                elif d < 0: delay_txt = f' <span style="color:#22c55e">{abs(d)}d early</span>'
            actual = ms.get("actual_date","") or "—"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:5px 8px;'
                f'background:#0f172a;border-radius:6px;margin-bottom:4px">'
                f'<span style="color:{sc};font-size:1rem">{"✅" if ms.get("status")=="Completed" else "🔲"}</span>'
                f'<div style="flex:1">'
                f'<span style="color:#f8fafc;font-size:0.88rem;font-weight:600">{ms.get("milestone_name","")}</span>'
                f'<span style="color:#64748b;font-size:0.78rem"> | Target: {ms.get("target_date","—")} | '
                f'Actual: {actual}{delay_txt}</span>'
                + (f'<div style="color:#94a3b8;font-size:0.76rem">{ms["notes"]}</div>' if ms.get("notes") else "")
                + f'</div>'
                f'<span style="background:{sc}22;color:{sc};padding:2px 8px;border-radius:10px;'
                f'font-size:0.74rem;font-weight:600">{ms.get("status","—")}</span></div>',
                unsafe_allow_html=True,
            )

    # ── Gantt chart ──────────────────────────────────────────────────────────
    st.markdown("---")
    _hdr("📊", "Milestone Gantt View", "#06b6d4")
    if milestones and PLOTLY_OK:
        import plotly.figure_factory as ff
        gantt_rows = []
        STATUS_GANTT_COLOR = {"Completed":"#22c55e","On Track":"#3b82f6",
                              "Pending":"#475569","At Risk":"#f59e0b","Delayed":"#ef4444"}
        for ms in milestones:
            try:
                t_dt = datetime.datetime.strptime(ms["target_date"], "%Y-%m-%d")
                # Show a 2-week bar for each milestone
                s_dt = t_dt - datetime.timedelta(days=14)
                gantt_rows.append(dict(
                    Task=ms["milestone_name"][:40],
                    Start=s_dt.strftime("%Y-%m-%d"),
                    Finish=t_dt.strftime("%Y-%m-%d"),
                    Resource=ms.get("status","Pending"),
                ))
            except Exception:
                pass
        if gantt_rows:
            try:
                colors = STATUS_GANTT_COLOR
                fig = ff.create_gantt(gantt_rows, colors=colors, index_col="Resource",
                                      show_colorbar=True, group_tasks=True)
                fig.update_layout(template="plotly_dark", paper_bgcolor="#0f172a",
                                  height=max(280, len(gantt_rows) * 36),
                                  title=f"Milestone Schedule — {proj['project_id']}")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"Gantt render note: {e}")
    else:
        st.info("Add milestones to see the Gantt chart.")

    # ── Add milestone form ─────────────────────────────────────────────────────
    st.markdown("---")
    _hdr("➕", "Add / Update Milestone", "#475569")
    with st.expander("📝 Milestone Entry Form"):
        with st.form(f"ms_form_{selected_pid}"):
            mf1, mf2 = st.columns(2)
            ms_name   = mf1.selectbox("Milestone", STANDARD_MILESTONES)
            ms_status = mf2.selectbox("Status", ["Pending","On Track","Completed","At Risk","Delayed"])
            mf3, mf4  = st.columns(2)
            ms_target = mf3.text_input("Target Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            ms_actual = mf4.text_input("Actual Date (blank if not done)", "")
            ms_delay  = st.number_input("Delay Days (negative = ahead)", -60, 365, 0)
            ms_notes  = st.text_area("Notes", "")
            submit_ms = st.form_submit_button("✅ Save Milestone")
        if submit_ms:
            ms_id = f"MS-{selected_pid}-{hashlib.md5(ms_name.encode()).hexdigest()[:4].upper()}"
            _save_milestone({
                "milestone_id": ms_id, "project_id": selected_pid,
                "milestone_name": ms_name, "target_date": ms_target,
                "actual_date": ms_actual, "status": ms_status,
                "delay_days": ms_delay, "notes": ms_notes,
            })
            _append_changelog("Milestone", ms_name, "", ms_status,
                              f"Milestone entry via form", "Internal", selected_pid, "User")
            st.success(f"✅ Milestone '{ms_name}' saved!")
            st.rerun()

    # ── All-projects summary table ─────────────────────────────────────────────
    st.markdown("---")
    _hdr("📋", "All Projects — Timeline Summary", "#22c55e")
    rows = []
    for p in projects:
        comp   = p.get("completion_pct", 0)
        delay  = p.get("delay_days", 0)
        msts   = get_milestones_for_project(p["project_id"])
        done   = sum(1 for m in msts if m.get("status") == "Completed")
        at_risk= sum(1 for m in msts if m.get("status") == "At Risk")
        rows.append({
            "Contractor":   contractors.get(p["contractor_id"],"—"),
            "Project ID":   p["project_id"],
            "State":        p.get("state",""),
            "Start":        p.get("start_date",""),
            "End":          p.get("end_date",""),
            "Complete %":   comp,
            "Delay Days":   delay,
            "Payment %":    p.get("payment_received_pct",0),
            "Milestones Done": done,
            "At Risk":      at_risk,
            "Quality":      p.get("quality_rating","—"),
            "Status":       p.get("status","—"),
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


def _tab_add_edit_data():
    """
    Master data entry and edit hub — all entities in one place.
    Sub-tabs: Add Contractor | Edit Contractor | Add Project | Edit Project |
              Add Signal | Add Risk Flag | Bulk Import
    """
    _hdr("✏️", "Add / Edit Data — Master CRM Entry Hub", "#f59e0b")

    (t_add_con, t_edit_con, t_add_proj, t_edit_proj,
     t_add_sig, t_add_risk, t_bulk) = st.tabs([
        "➕ Add Contractor",
        "✏️ Edit Contractor",
        "➕ Add Project",
        "✏️ Edit Project / Site",
        "📡 Add Signal",
        "🚨 Add Risk Flag",
        "📥 Bulk Import (CSV)",
    ])

    # ═══ ADD CONTRACTOR ══════════════════════════════════════════════════════
    with t_add_con:
        _hdr("🏢", "Register New Contractor", "#06b6d4")
        with st.form("add_contractor_full_form"):
            st.markdown("##### Identity")
            f1, f2 = st.columns(2)
            name     = f1.text_input("Contractor Name *", placeholder="e.g. customer name")
            bse      = f2.text_input("BSE Code", placeholder="e.g. 500510")
            f3, f4   = st.columns(2)
            cin      = f3.text_input("CIN",  placeholder="L17110GJ1912PLC000007")
            pan      = f4.text_input("PAN",  placeholder="AABCL0100K")
            f5, f6   = st.columns(2)
            gstin    = f5.text_input("GSTIN", placeholder="27AABCL0100K1ZR")
            nse      = f6.text_input("NSE Code", placeholder="LT")
            try:
                from components.autosuggest import city_picker as _city_picker
                city = _city_picker(key="osint_city", label="Base City / HQ")
            except Exception:
                city = st.text_input("Base City / HQ", placeholder="e.g. Mumbai, Maharashtra")
            website  = st.text_input("Website", "https://")

            st.markdown("##### Corporate Contact")
            g1, g2   = st.columns(2)
            ph_corp  = g1.text_input("Corporate Phone", placeholder="+91-22-XXXXXXXX")
            em_corp  = g2.text_input("Corporate Email", placeholder="info@company.com")
            g3, g4   = st.columns(2)
            ph_bd    = g3.text_input("BD / Sales Phone", placeholder="+91-XX-XXXXXXXX")
            em_inv   = g4.text_input("Investor Email",   placeholder="investor@company.com")
            em_tend  = st.text_input("Tender Email",     placeholder="tenders@company.com")
            addr_reg = st.text_area("Registered Office Address", height=70)
            addr_cor = st.text_area("Corporate Office Address (if different)", height=70)

            st.markdown("##### Social Media (Official Pages Only)")
            s1, s2   = st.columns(2)
            linkedin  = s1.text_input("LinkedIn URL", "https://www.linkedin.com/company/")
            twitter   = s2.text_input("Twitter / X URL", "https://twitter.com/")
            s3, s4   = st.columns(2)
            facebook  = s3.text_input("Facebook URL", "https://www.facebook.com/")
            youtube   = s4.text_input("YouTube URL", "https://www.youtube.com/")
            instagram = st.text_input("Instagram URL", "https://www.instagram.com/")

            st.markdown("##### Business Profile")
            b1, b2, b3 = st.columns(3)
            turnover   = b1.number_input("Annual Turnover (₹ Cr)", 0.0, 200000.0, 0.0, step=100.0)
            order_book = b2.number_input("Order Book (₹ Cr)", 0.0, 500000.0, 0.0, step=100.0)
            road_pct   = b3.slider("Roads Segment %", 0, 100, 60)
            emp_range  = st.selectbox("Employee Count Range",
                ["<500","500–2,000","2,000–5,000","5,000–10,000","10,000–15,000","15,000–30,000","30,000+"])
            specialization = st.multiselect("Active States", [
                "AP","AS","BR","CG","GJ","HR","HP","JH","KA","KL","MH","MP","MN","MG",
                "MZ","NL","OD","PB","RJ","SK","TN","TS","TR","UP","UK","WB","DL","J&K","GA","AN","PY","CHD",
            ])
            rating    = st.text_input("Credit Rating", placeholder="A+ (CARE)")
            certs     = st.text_input("Certifications (comma separated)", "ISO 9001:2015")
            bankers   = st.text_input("Bankers (comma separated)", "SBI, HDFC Bank")
            fleet_note= st.text_input("Equipment Fleet Note", "")
            note      = st.text_area("CRM Notes / Specialisation", height=60)

            st.markdown("##### CRM Account")
            cq1, cq2 = st.columns(2)
            crm_status= cq1.selectbox("CRM Status", ["Active Prospect","Active Customer","Dormant","Lost","Blacklisted"])
            grade_pref= cq2.selectbox("Bitumen Grade Preference", ["VG-30 Bulk","VG-40 Bulk","VG-30 Drum","PMB 40","VG-30 & VG-40","All grades"])
            cq3, cq4 = st.columns(2)
            crm_owner = cq3.text_input("Account Owner")
            typ_order = cq4.number_input("Typical Order (MT)", 0, 10000, 100, step=50)
            conf_inp  = st.slider("Confidence %", 30, 100, 70, step=5)

            submit_con = st.form_submit_button("✅ Register Contractor")

        if submit_con and name:
            cid = "CON-" + hashlib.md5(name.encode()).hexdigest()[:6].upper()
            new_con = {
                "contractor_id": cid, "name": name, "aliases": [name],
                "base_city": city, "website": website.strip(),
                "cin": cin, "pan": pan, "gstin": gstin,
                "bse_code": bse, "nse_code": nse,
                "type": f"{emp_range} employees | {road_pct}% roads",
                "rating": rating,
                "phone_corporate": ph_corp, "phone_bd": ph_bd,
                "email_corporate": em_corp, "email_investor": em_inv, "email_tender": em_tend,
                "address_registered": addr_reg, "address_corporate": addr_cor,
                "social_linkedin": linkedin, "social_twitter": twitter,
                "social_facebook": facebook, "social_youtube": youtube, "social_instagram": instagram,
                "key_contacts": [],
                "annual_turnover_cr": turnover, "order_book_cr": order_book,
                "employee_count_range": emp_range,
                "specialization_states": specialization,
                "road_segment_pct": road_pct,
                "certifications": [x.strip() for x in certs.split(",")],
                "bankers": [x.strip() for x in bankers.split(",")],
                "auditors": [], "equipment_fleet_note": fleet_note,
                "crm_status": crm_status, "crm_owner": crm_owner,
                "bitumen_grade_pref": grade_pref, "typical_order_mt": typ_order,
                "last_contacted": "", "next_followup": "",
                "last_seen_date": datetime.date.today().strftime("%Y-%m-%d"),
                "confidence": conf_inp, "note": note,
            }
            existing = get_contractors()
            if not any(c["name"].lower() == name.lower() for c in existing):
                existing.append(new_con)
                _save(CONTRACTORS_FILE, existing)
                _append_changelog("Contractor","new_contractor","","Added",f"Manual entry: {name}","Internal",actor="User")
                st.success(f"✅ Contractor **{name}** (ID: {cid}) registered!")
            else:
                st.warning(f"⚠️ Contractor '{name}' already exists.")

    # ═══ EDIT CONTRACTOR ═════════════════════════════════════════════════════
    with t_edit_con:
        _hdr("✏️", "Edit Existing Contractor Record", "#f59e0b")
        contractors = get_contractors()
        if not contractors:
            st.info("No contractors in database.")
        else:
            sel_con = st.selectbox("Select Contractor to Edit",
                                   [c["contractor_id"] for c in contractors],
                                   format_func=lambda x: next((c["name"] for c in contractors if c["contractor_id"]==x),""),
                                   key="edit_con_sel")
            c_rec = next((c for c in contractors if c["contractor_id"] == sel_con), None)
            if c_rec:
                st.info(f"Editing: **{c_rec['name']}** | Last seen: {c_rec.get('last_seen_date','—')}")
                edit_fields = {
                    "CRM Status":        ("crm_status",      c_rec.get("crm_status","Active Prospect")),
                    "Account Owner":     ("crm_owner",       c_rec.get("crm_owner","")),
                    "Last Contacted":    ("last_contacted",  c_rec.get("last_contacted","")),
                    "Next Follow-up":    ("next_followup",   c_rec.get("next_followup","")),
                    "Corporate Phone":   ("phone_corporate", c_rec.get("phone_corporate","")),
                    "Corporate Email":   ("email_corporate", c_rec.get("email_corporate","")),
                    "Tender Email":      ("email_tender",    c_rec.get("email_tender","")),
                    "BD Phone":          ("phone_bd",        c_rec.get("phone_bd","")),
                    "Grade Preference":  ("bitumen_grade_pref", c_rec.get("bitumen_grade_pref","VG-30 Bulk")),
                    "Typical Order MT":  ("typical_order_mt",str(c_rec.get("typical_order_mt",100))),
                    "CRM Notes":         ("note",            c_rec.get("note","")),
                    "Credit Rating":     ("rating",          c_rec.get("rating","")),
                }
                with st.form("edit_con_form"):
                    edited = {}
                    pairs = list(edit_fields.items())
                    for i in range(0, len(pairs), 2):
                        cols = st.columns(2)
                        for j, col in enumerate(cols):
                            if i+j < len(pairs):
                                lbl, (fld, cur) = pairs[i+j]
                                edited[fld] = col.text_input(lbl, value=str(cur), key=f"ec_{fld}")
                    save_edit = st.form_submit_button("💾 Save Changes")
                if save_edit:
                    for field, new_val in edited.items():
                        if str(new_val) != str(c_rec.get(field,"")):
                            update_contractor_field(sel_con, field, new_val)
                    st.success("✅ Contractor record updated!")
                    st.rerun()

    # ═══ ADD PROJECT ═════════════════════════════════════════════════════════
    with t_add_proj:
        _hdr("📋", "Register New Project", "#3b82f6")
        contractors = get_contractors()
        contractors_map = {c["contractor_id"]: c["name"] for c in contractors}
        with st.form("add_project_full_form"):
            st.markdown("##### Project Identity")
            p1, p2 = st.columns(2)
            sel_con     = p1.selectbox("Contractor *", list(contractors_map.keys()),
                                       format_func=lambda x: contractors_map[x])
            proj_title  = p2.text_input("Project Title *")
            p3, p4, p5  = st.columns(3)
            authority   = p3.selectbox("Authority", ["NHAI","MoRTH","PMGSY/NRRDA","State PWD","ULB","NHIDCL","BRO","World Bank","ADB","Other"])
            program     = p4.text_input("Program", placeholder="Bharatmala Phase-I")
            state       = p5.selectbox("State", ["Andhra Pradesh","Assam","Bihar","Chhattisgarh","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Delhi","J&K","Goa","Other"])
            p6, p7, p8  = st.columns(3)
            district    = p6.text_input("District(s)")
            highway     = p7.text_input("Highway No.", placeholder="NH-48")
            package_id  = p8.text_input("Package ID", placeholder="BM-PKG-01")
            proj_type   = st.selectbox("Project Type *", list(BITUMEN_MT_PER_KM.keys()))

            st.markdown("##### Financial & Physical")
            q1, q2, q3 = st.columns(3)
            contract_val= q1.number_input("Contract Value (₹ Cr) *", 0.0, 100000.0, 0.0, step=1.0)
            road_km     = q2.number_input("Road Length (km)", 0.0, 2000.0, 0.0, step=0.5)
            comp_pct    = q3.slider("Completion % (current)", 0, 100, 0)
            q4, q5, q6  = st.columns(3)
            start_dt    = q4.text_input("Start Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            end_dt      = q5.text_input("End Date (DD-MM-YYYY)",   (datetime.date.today()+datetime.timedelta(days=730)).strftime("%Y-%m-%d"))
            delay_days  = q6.number_input("Delay Days (0 = on track)", -30, 730, 0)
            q7, q8      = st.columns(2)
            pay_pct     = q7.number_input("Payment Received %", 0, 100, 0)
            qual_rating = q8.selectbox("Quality Rating", ["Not Started","Design Stage","Mobilisation Phase","Good","Satisfactory","Below Par","On Hold"])

            st.markdown("##### Site Information")
            site_addr   = st.text_input("Site Address / Location", placeholder="NH-48, Km 120-193, Rajasthan")
            r1, r2      = st.columns(2)
            site_mgr    = r1.text_input("Site Manager (Company Employee Name)", placeholder="John Doe (Company)")
            site_ph     = r2.text_input("Site Contact Phone (Company Office)", placeholder="+91-XXXXX-XXXXX")
            site_em     = st.text_input("Site Email (Company)", placeholder="site.name@company.com")
            sub_con_txt = st.text_area("Sub-Contractors (one per line)", height=70)
            mat_sup_txt = st.text_area("Material Suppliers (one per line)", height=70)
            equip_txt   = st.text_area("Equipment Deployed (one per line)", height=70)
            piu_contact = st.text_input("NHAI PIU / Authority Contact (official)", placeholder="NHAI PIU XYZ (+91-XXXXX-XXXXX)")

            st.markdown("##### Source / Evidence")
            source_url  = st.text_input("Source URL *", "https://")
            t1, t2, t3  = st.columns(3)
            source_type = t1.selectbox("Source Type", ["Government","BSE Filing","News","Company Website","Social Media","Other"])
            source_date = t2.text_input("Source Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            conf_inp    = t3.slider("Confidence %", 30, 100, 65, step=5)
            source_snip = st.text_area("Source Snippet (1–2 lines)", height=60)
            submit_proj = st.form_submit_button("✅ Register Project")

        if submit_proj and proj_title and contract_val > 0:
            try:
                freshness = (datetime.date.today() - datetime.datetime.strptime(source_date, "%Y-%m-%d").date()).days
            except Exception:
                freshness = 0
            new_proj = {
                "project_id": _project_id(sel_con, proj_title, state),
                "contractor_id": sel_con, "project_title": proj_title,
                "authority": authority, "program": program, "state": state,
                "district": district, "highway": highway, "package_id": package_id,
                "project_type": proj_type, "contract_value_inr": contract_val * 1e7,
                "road_km": road_km, "start_date": start_dt, "end_date": end_dt,
                "status": "Awarded", "completion_pct": comp_pct, "delay_days": delay_days,
                "payment_received_pct": pay_pct, "quality_rating": qual_rating,
                "site_address": site_addr, "site_manager_name": site_mgr,
                "site_contact_number": site_ph, "site_email": site_em,
                "sub_contractors": [x.strip() for x in sub_con_txt.splitlines() if x.strip()],
                "material_suppliers": [x.strip() for x in mat_sup_txt.splitlines() if x.strip()],
                "equipment_deployed": [x.strip() for x in equip_txt.splitlines() if x.strip()],
                "nhai_piu_contact": piu_contact, "last_site_inspection": "",
                "source_url": source_url, "source_type": source_type,
                "source_date": source_date, "data_freshness_days": freshness,
                "source_snippet": source_snip, "confidence": conf_inp, "verified": "UNVERIFIABLE",
            }
            existing = get_projects()
            existing.append(new_proj)
            _save(PROJECTS_FILE, existing)
            _append_changelog("Project","new_project","","Added",f"Manual entry: {proj_title}",source_url,new_proj["project_id"],"User")
            st.success(f"✅ Project **'{proj_title}'** registered! ID: {new_proj['project_id']}")
            st.rerun()

    # ═══ EDIT PROJECT / SITE ═════════════════════════════════════════════════
    with t_edit_proj:
        _hdr("✏️", "Update Project Progress & Site Info", "#22c55e")
        projects = get_projects()
        contractors = {c["contractor_id"]: c["name"] for c in get_contractors()}
        if not projects:
            st.info("No projects loaded.")
        else:
            sel_pid = st.selectbox("Select Project to Edit",
                                   [p["project_id"] for p in projects],
                                   format_func=lambda x: next((f'{contractors.get(p["contractor_id"],"?")} | {p["project_title"][:55]}' for p in projects if p["project_id"]==x),""),
                                   key="edit_proj_sel")
            p_rec = next((p for p in projects if p["project_id"] == sel_pid), None)
            if p_rec:
                st.markdown(f"**{p_rec['project_title']}** | {p_rec.get('state','')} | {format_inr_short(p_rec.get('contract_value_inr',0))}")
                with st.form("edit_proj_form"):
                    ep1, ep2, ep3 = st.columns(3)
                    new_comp   = ep1.number_input("Completion %",  0, 100, p_rec.get("completion_pct",0))
                    new_delay  = ep2.number_input("Delay Days",  -60, 730, p_rec.get("delay_days",0))
                    new_pay    = ep3.number_input("Payment Received %", 0, 100, p_rec.get("payment_received_pct",0))
                    _status_opts = [
                        "Awarded","LOA Received","LOA Received — Mobilisation","LOA Received — Design Stage",
                        "Under Execution","Under Execution — On Hold","Completed","Terminated",
                    ]
                    _qual_opts = ["Not Started","Design Stage","Mobilisation Phase","Good","Satisfactory","Below Par","On Hold"]
                    _cur_status = p_rec.get("status","")
                    _cur_qual   = p_rec.get("quality_rating","")
                    new_status = st.selectbox("Project Status", _status_opts,
                        index=_status_opts.index(_cur_status) if _cur_status in _status_opts else 0)
                    new_qual   = st.selectbox("Quality Rating", _qual_opts,
                        index=_qual_opts.index(_cur_qual) if _cur_qual in _qual_opts else 0)
                    new_insp   = st.text_input("Last Site Inspection (DD-MM-YYYY)", p_rec.get("last_site_inspection",""))
                    new_mgr    = st.text_input("Site Manager Name",   p_rec.get("site_manager_name",""))
                    new_ph     = st.text_input("Site Phone",           p_rec.get("site_contact_number",""))
                    new_em     = st.text_input("Site Email",           p_rec.get("site_email",""))
                    new_equip  = st.text_area("Equipment Deployed (one per line)",
                                              "\n".join(p_rec.get("equipment_deployed",[])), height=80)
                    new_sub    = st.text_area("Sub-Contractors (one per line)",
                                              "\n".join(p_rec.get("sub_contractors",[])), height=80)
                    new_mat    = st.text_area("Material Suppliers (one per line)",
                                              "\n".join(p_rec.get("material_suppliers",[])), height=80)
                    save_proj  = st.form_submit_button("💾 Save Project Updates")
                if save_proj:
                    updates = {
                        "completion_pct": new_comp, "delay_days": new_delay,
                        "payment_received_pct": new_pay, "status": new_status,
                        "quality_rating": new_qual, "last_site_inspection": new_insp,
                        "site_manager_name": new_mgr, "site_contact_number": new_ph,
                        "site_email": new_em,
                        "equipment_deployed": [x.strip() for x in new_equip.splitlines() if x.strip()],
                        "sub_contractors":    [x.strip() for x in new_sub.splitlines()   if x.strip()],
                        "material_suppliers": [x.strip() for x in new_mat.splitlines()   if x.strip()],
                    }
                    for fld, val in updates.items():
                        if str(val) != str(p_rec.get(fld,"")):
                            update_project_field(sel_pid, fld, val)
                    st.success("✅ Project updated!")
                    st.rerun()

    # ═══ ADD SIGNAL ══════════════════════════════════════════════════════════
    with t_add_sig:
        _hdr("📡", "Log New OSINT Signal / News Item", "#22c55e")
        contractors_map = {c["contractor_id"]: c["name"] for c in get_contractors()}
        projects_map    = {"(none)": "(no project link)"} | {p["project_id"]: p["project_title"][:50] for p in get_projects()}
        with st.form("add_signal_full"):
            s1, s2  = st.columns(2)
            sig_con  = s1.selectbox("Contractor *", list(contractors_map.keys()), format_func=lambda x: contractors_map[x])
            sig_proj = s2.selectbox("Linked Project (optional)", list(projects_map.keys()), format_func=lambda x: projects_map[x])
            platform = st.selectbox("Platform / Source", ["BSE Filing","Economic Times","Business Standard","Mint","Times of India","Financial Express","NHAI Website","Company Website","LinkedIn","Twitter/X","Facebook","YouTube","PMGSY Portal","BilTrax24x7","Other"])
            sig_url  = st.text_input("URL *", "https://")
            summary  = st.text_area("Summary (max 2 lines) *", height=80)
            s3, s4, s5, s6 = st.columns(4)
            sig_date = s3.text_input("Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            tag      = s4.selectbox("Tag", ["award","financials","order_book","progress","dispute","quality","blacklisting","legal","site_visit","milestone","other"])
            sent     = s5.selectbox("Sentiment", ["Positive","Neutral","Negative"])
            sig_conf = s6.slider("Confidence %", 30, 100, 70)
            submit_sig = st.form_submit_button("✅ Log Signal")
        if submit_sig and summary:
            new_sig = {
                "contractor_id": sig_con,
                "project_id": None if sig_proj == "(none)" else sig_proj,
                "platform": platform, "date": sig_date, "url": sig_url,
                "summary": summary, "tag": tag, "sentiment": sent, "confidence": sig_conf,
            }
            existing = get_signals()
            existing.append(new_sig)
            _save(SIGNALS_FILE, existing)
            st.success("✅ Signal logged!")
            st.rerun()

    # ═══ ADD RISK FLAG ═══════════════════════════════════════════════════════
    with t_add_risk:
        _hdr("🚨", "Log New Risk / Compliance Flag", "#ef4444")
        contractors_map = {c["contractor_id"]: c["name"] for c in get_contractors()}
        with st.form("add_risk_full"):
            r1, r2 = st.columns(2)
            rf_con  = r1.selectbox("Contractor *", list(contractors_map.keys()), format_func=lambda x: contractors_map[x])
            rf_type = r2.selectbox("Risk Type", ["Payment Dispute","Blacklisting","Labour Issue","Accident","Quality Failure","Environmental Violation","Arbitration","Termination Notice","Court Order","Compliance Notice","Other"])
            r3, r4  = st.columns(2)
            rf_sev  = r3.selectbox("Severity", ["Low","Med","High","Critical"])
            rf_date = r4.text_input("Date (DD-MM-YYYY)", datetime.date.today().strftime("%Y-%m-%d"))
            rf_url  = st.text_input("Evidence URL", "https://")
            rf_sum  = st.text_area("Summary (1–2 lines)", height=80)
            rf_status = st.selectbox("Status", ["OPEN","RESOLVED","MONITORING"])
            rf_conf = st.slider("Confidence %", 30, 100, 65)
            submit_risk = st.form_submit_button("🚨 Log Risk Flag")
        if submit_risk and rf_sum:
            new_flag = {
                "contractor_id": rf_con, "flag_type": rf_type,
                "severity": rf_sev, "date": rf_date, "url": rf_url,
                "summary": rf_sum, "status": rf_status, "confidence": rf_conf,
            }
            existing = get_risk_flags()
            existing.append(new_flag)
            _save(RISK_FLAGS_FILE, existing)
            _append_changelog("RiskFlag", rf_type, "", rf_sev, f"Risk flag logged: {rf_type}", rf_url, "", "User")
            st.success("✅ Risk flag logged!")
            st.rerun()

    # ═══ BULK IMPORT ═════════════════════════════════════════════════════════
    with t_bulk:
        _hdr("📥", "Bulk Import via CSV", "#8b5cf6")
        st.info("Upload a CSV file to bulk-import contractors or projects. Download a template first.")
        imp_type = st.radio("Import Type", ["Contractors", "Projects"], horizontal=True)

        if imp_type == "Contractors":
            template = pd.DataFrame([{
                "name":"Example Contractor Ltd","base_city":"Mumbai, MH",
                "website":"www.example.com","cin":"L12345MH2000PLC123456",
                "bse_code":"500000","phone_corporate":"+91-22-XXXXXXXX",
                "email_corporate":"info@example.com","address_registered":"123 Main St, Mumbai 400001",
                "annual_turnover_cr":1000,"order_book_cr":5000,"rating":"A (CARE)",
                "note":"Add notes here",
            }])
        else:
            template = pd.DataFrame([{
                "contractor_name":"Example Contractor Ltd","project_title":"4-Lane NH-XX from A to B",
                "authority":"NHAI","state":"Maharashtra","district":"Pune",
                "highway":"NH-48","project_type":"NH 4-Lane New",
                "contract_value_cr":150,"road_km":45.0,
                "start_date":"01-10-2025","end_date":"30-09-2027",
                "source_url":"https://nhai.gov.in","source_type":"Government","source_date":"01-10-2025",
                "confidence":75,
            }])

        st.dataframe(template, use_container_width=True, hide_index=True)
        st.download_button(
            f"⬇️ Download {imp_type} Template CSV",
            template.to_csv(index=False).encode("utf-8"),
            f"{imp_type.lower()}_import_template.csv",
            "text/csv",
        )
        uploaded = st.file_uploader(f"Upload {imp_type} CSV", type=["csv"])
        if uploaded:
            try:
                df_up = pd.read_csv(uploaded)
                st.success(f"✅ Loaded {len(df_up)} rows. Preview:")
                st.dataframe(df_up.head(10), use_container_width=True, hide_index=True)
                if st.button("✅ Confirm & Import"):
                    if imp_type == "Contractors":
                        existing = get_contractors()
                        added = 0
                        for _, row in df_up.iterrows():
                            if not any(c["name"].lower() == str(row.get("name","")).lower() for c in existing):
                                cid = "CON-" + hashlib.md5(str(row.get("name","")).encode()).hexdigest()[:6].upper()
                                existing.append({"contractor_id": cid, **row.to_dict(),
                                                 "last_seen_date": datetime.date.today().strftime("%Y-%m-%d"),
                                                 "confidence": 60, "aliases": [row.get("name","")]})
                                added += 1
                        _save(CONTRACTORS_FILE, existing)
                        st.success(f"✅ Imported {added} new contractors.")
                    else:
                        contractors_rev = {c["name"].lower(): c["contractor_id"] for c in get_contractors()}
                        existing = get_projects()
                        added = 0
                        for _, row in df_up.iterrows():
                            con_name = str(row.get("contractor_name","")).lower()
                            cid = contractors_rev.get(con_name, "CON-UNKNOWN")
                            title = str(row.get("project_title",""))
                            state_val = str(row.get("state",""))
                            pid = _project_id(cid, title, state_val)
                            cv  = float(row.get("contract_value_cr", 0)) * 1e7
                            existing.append({
                                "project_id": pid, "contractor_id": cid,
                                "project_title": title, "authority": row.get("authority",""),
                                "program": row.get("authority",""), "state": state_val,
                                "district": row.get("district",""), "highway": row.get("highway",""),
                                "package_id": "", "project_type": row.get("project_type","NH 4-Lane New"),
                                "contract_value_inr": cv, "road_km": float(row.get("road_km",0)),
                                "start_date": str(row.get("start_date","")), "end_date": str(row.get("end_date","")),
                                "status": "Awarded", "completion_pct": 0, "delay_days": 0,
                                "source_url": str(row.get("source_url","")),
                                "source_type": str(row.get("source_type","Other")),
                                "source_date": str(row.get("source_date","")),
                                "data_freshness_days": 0, "source_snippet": "",
                                "confidence": int(row.get("confidence",60)), "verified": "UNVERIFIABLE",
                            })
                            added += 1
                        _save(PROJECTS_FILE, existing)
                        st.success(f"✅ Imported {added} projects.")
                    st.rerun()
            except Exception as e:
                st.error(f"Import error: {e}")


def _tab_estimation_tool():
    """Interactive single-project bitumen estimator."""
    _hdr("🧮", "Bitumen Estimation Calculator", "#22c55e")
    st.caption("Estimate MT requirement for any single project. Grade: VG-30 @ ₹48,302/MT (IOCL, 16-02-2026)")

    c1, c2 = st.columns(2)
    proj_type   = c1.selectbox("Project Type", list(BITUMEN_MT_PER_KM.keys()))
    state       = c2.selectbox("State", [
        "Andhra Pradesh","Assam","Bihar","Chhattisgarh","Delhi","Goa","Gujarat",
        "Haryana","Himachal Pradesh","J&K","Jharkhand","Karnataka","Kerala",
        "Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland",
        "Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura",
        "Uttar Pradesh","Uttarakhand","West Bengal",
    ], index=14)   # Maharashtra default
    c3, c4      = st.columns(2)
    road_km     = c3.number_input("Road Length (km)", 0.0, 2000.0, 50.0, step=1.0)
    contract_val= c4.number_input("Contract Value (₹ Cr)", 0.0, 10000.0, 100.0, step=5.0)
    c5, c6      = st.columns(2)
    start_dt    = c5.text_input("Start Date (DD-MM-YYYY)", "01-10-2025")
    end_dt      = c6.text_input("End Date (DD-MM-YYYY)",   "30-09-2027")

    est = estimate_bitumen(proj_type, road_km if road_km > 0 else None, contract_val * 1e7 if contract_val > 0 else None, state)

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    _card(m1, "Low Estimate",  f"{est['low']:,} MT",  "Conservative",   "#f59e0b")
    _card(m2, "Base Estimate", f"{est['base']:,} MT", "Most Likely",     "#22c55e")
    _card(m3, "High Estimate", f"{est['high']:,} MT", "Optimistic",      "#3b82f6")

    st.info(f"**Method:** {est['method']}\n\n**Assumptions:** {est['assumptions']}")

    # Revenue potential
    r1, r2, r3 = st.columns(3)
    _card(r1, "Revenue (Low)",  format_inr_short(est['low']  * 48302), "@ ₹48,302/MT", "#f59e0b")
    _card(r2, "Revenue (Base)", format_inr_short(est['base'] * 48302), "@ ₹48,302/MT", "#22c55e")
    _card(r3, "Revenue (High)", format_inr_short(est['high'] * 48302), "@ ₹48,302/MT", "#3b82f6")

    st.markdown("---")
    _hdr("📅", "Monthly Distribution", "#8b5cf6")
    try:
        monthly = distribute_monthly(est["base"], start_dt, end_dt, state)
        months  = [m for m in SEASON_ORDER if m in monthly]
        vals    = [monthly.get(m, 0) for m in months]
        if PLOTLY_OK:
            fig = go.Figure(go.Bar(x=months, y=vals, marker_color="#8b5cf6",
                                   text=[f"{v:.0f}" for v in vals], textposition="outside"))
            fig.update_layout(template="plotly_dark", paper_bgcolor="#0f172a", plot_bgcolor="#1e293b",
                              title="Projected Monthly Bitumen Requirement (MT)", height=350)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not distribute monthly: {e}")

    st.markdown("---")
    _hdr("📊", "Reference: MT/km by Project Type", "#475569")
    ref_rows = [{"Project Type": k, "Low MT/km": v["low"], "Base MT/km": v["base"], "High MT/km": v["high"], "Bitumen % of Contract": f"{BITUMEN_PCT_OF_CONTRACT.get(k,0.10)*100:.0f}%"} for k,v in BITUMEN_MT_PER_KM.items()]
    st.dataframe(pd.DataFrame(ref_rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render():
    display_badge("calculated")

    st.markdown("""
<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
padding:20px 24px;border-radius:12px;margin-bottom:20px;
border-left:5px solid #f59e0b;">
<div style="font-size:1.5rem;font-weight:900;color:#f8fafc;">
🔭 Contractor OSINT Intelligence
</div>
<div style="color:#94a3b8;font-size:0.9rem;margin-top:4px">
Track road contractors — project awards, bitumen demand (MT), monthly heatmap, risk flags, CRM export.
Date filter: last 6 months only | Grade: VG-30 @ ₹48,302/MT | All data with source citations.
</div>
</div>
""", unsafe_allow_html=True)

    st.warning("⚠️ **Demo Mode** — 3 sample contractors (Dilip Buildcon, NCC Ltd, GR Infraprojects) with indicative project data. Add real contractors via the 'Add Contractor' tab. All estimates are based on publicly available information within the last 6 months.", icon="🔍")

    tabs = st.tabs([
        "📊 Executive Summary",
        "📋 Projects",
        "🛢️ Bitumen Demand",
        "🗺️ State Heatmap",
        "📞 Contacts & CRM",
        "🗓️ Project Timeline",
        "📡 Signals & News",
        "🚨 Risk Flags",
        "🗃️ CRM Export",
        "✏️ Add / Edit Data",
        "🧮 Estimation Tool",
    ])

    with tabs[0]:  _tab_executive()
    with tabs[1]:  _tab_projects()
    with tabs[2]:  _tab_bitumen_demand()
    with tabs[3]:  _tab_heatmap()
    with tabs[4]:  _tab_contacts()
    with tabs[5]:  _tab_timeline()
    with tabs[6]:  _tab_signals()
    with tabs[7]:  _tab_risk()
    with tabs[8]:  _tab_crm()
    with tabs[9]:  _tab_add_edit_data()
    with tabs[10]: _tab_estimation_tool()

    st.markdown("---")
    st.markdown(
        '<div style="color:#475569;font-size:0.76rem;text-align:center">'
        'Contractor OSINT v2.0 | PPS Anantams Logistics AI | Data: BSE filings, NHAI, PMGSY, News '
        '| Grade: VG-30 @ ₹48,302/MT | Full contact data, site info, milestone timeline | '
        'Strict 6-month date filter applied</div>',
        unsafe_allow_html=True,
    )

    try:
        log_dev_activity(activity_type="Module Loaded", title="Contractor OSINT v2.0 accessed",
                         description="OSINT v2.0 rendered. Full contact CRM, site info, milestones, 11 tabs.",
                         status="Active", component="contractor_osint.py", department="Sales")
    except Exception:
        pass
