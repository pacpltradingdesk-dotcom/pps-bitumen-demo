# directory_engine.py
# PPS Anantam Agentic AI Eco System — v3.3.0
# India Bitumen & Roads Procurement Directory — Phase 1 Engine
# Schema, seed data (56 entries), search/filter, CRM hook, coverage report
#
# COMPLIANCE: Only officially published contacts (official websites, NIC portals).
# Every record carries source_url + last_verified_ist.
# Unpublished contacts → blank fields (not fabricated).
# Confidence: High (live-verified) | Medium (seed/once-verified) | Low (inferred)

from __future__ import annotations

import datetime
import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Paths ──────────────────────────────────────────────────────────────────────
_BASE = Path(__file__).parent

TBL_DIR_ORGS    = _BASE / "tbl_dir_orgs.json"
TBL_DIR_SOURCES = _BASE / "tbl_dir_sources.json"
TBL_DIR_CHANGES = _BASE / "tbl_dir_changes.json"
TBL_DIR_FETCHES = _BASE / "tbl_dir_fetch_logs.json"
TBL_DIR_BUGS    = _BASE / "tbl_dir_bugs.json"
TBL_DIR_GEO     = _BASE / "tbl_dir_geo.json"

_lock = threading.RLock()

# ── Utilities ──────────────────────────────────────────────────────────────────
def _ist_now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")


def _load(path: Path, default: Any = None) -> Any:
    if default is None:
        default = []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Compact Record Constructor ─────────────────────────────────────────────────
_B = ""  # blank default


def _c(
    org_id: str,
    phase: int,
    state_ut: str,
    city: str,
    level: str,
    dept_name: str,
    short_name: str,
    parent_ministry: str,
    office_type: str,
    dept_type: str,
    lat: float,
    lon: float,
    website: str,
    source_url: str,
    roads_role: str,
    official_email: str = _B,
    official_phone: str = _B,
    helpline: str = _B,
    tender_portal: str = _B,
    notes: str = _B,
    confidence: str = "Medium",
    pincode: str = _B,
    address: str = _B,
    district: str = _B,
) -> dict:
    """Compact constructor for a directory org record with all 36 fields."""
    return {
        "org_id":            org_id,
        "phase":             phase,
        "country":           "India",
        "state_ut":          state_ut,
        "district":          district,
        "city":              city,
        "taluka":            _B,
        "block":             _B,
        "gp_village":        _B,
        "pincode":           pincode,
        "lat":               lat,
        "long":              lon,
        "level":             level,
        "dept_name":         dept_name,
        "short_name":        short_name,
        "parent_ministry":   parent_ministry,
        "office_type":       office_type,
        "dept_type":         dept_type,
        "address":           address,
        "website":           website,
        "official_email":    official_email,
        "official_phone":    official_phone,
        "helpline":          helpline,
        "officer_name":      _B,
        "designation":       _B,
        "officer_email":     _B,
        "officer_phone":     _B,
        "roads_role":        roads_role,
        "tender_portal":     tender_portal if tender_portal else website,
        "notes":             notes,
        "source_url":        source_url,
        "source_type":       "HTML",
        "last_fetched_ist":  _B,
        "last_verified_ist": _B,
        "confidence":        confidence,
        "change_ptr":        _B,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 SEED DATA — 56 entries
# Sources: Official govt websites / NIC portals only
# ══════════════════════════════════════════════════════════════════════════════
SEED_PHASE1: List[dict] = [

    # ── Group A: Central Ministries / Agencies (6) ───────────────────────────
    _c("CENT-001", 1, "Delhi", "New Delhi", "Central",
       "Ministry of Road Transport & Highways",
       "MoRTH", "Cabinet Secretariat", "HQ", "PWD",
       28.6139, 77.2090,
       "https://morth.nic.in",
       "https://morth.nic.in/contact-us",
       "Policy, NH programmes, bitumen specs & procurement norms",
       official_email="secy-morth@nic.in",
       official_phone="+91-11-23714154",
       tender_portal="https://eprocure.gov.in",
       notes="Central authority for NH construction; bitumen VG spec notifications issued here"),

    _c("CENT-002", 1, "Delhi", "New Delhi", "Central",
       "National Highways Authority of India",
       "NHAI", "MoRTH", "HQ", "NHAI",
       28.5921, 77.0460,
       "https://nhai.gov.in",
       "https://nhai.gov.in/ContactUs2",
       "NH construction, 4-laning, bitumen procurement for NH projects",
       official_email="ro.chairman@nhai.org",
       helpline="1800-11-6086",
       tender_portal="https://nhai.gov.in/tenders",
       notes="Largest single buyer of bitumen for road construction in India"),

    _c("CENT-003", 1, "Delhi", "New Delhi", "Central",
       "National Highways & Infrastructure Development Corporation",
       "NHIDCL", "MoRTH", "HQ", "NHAI",
       28.6275, 77.2190,
       "https://nhidcl.com",
       "https://nhidcl.com/contact",
       "NH projects in NE states, J&K, Ladakh, Andaman; bitumen procurement",
       official_email="cmo@nhidcl.com",
       official_phone="+91-11-23736672",
       tender_portal="https://nhidcl.com/tenders",
       notes="Executes NH projects in strategic border & NE regions"),

    _c("CENT-004", 1, "Delhi", "New Delhi", "Central",
       "National Rural Infrastructure Development Agency (PMGSY)",
       "NRIDA/PMGSY", "MoRD", "HQ", "PMGSY",
       28.6448, 77.3111,
       "https://pmgsy.nic.in",
       "https://pmgsy.nic.in/contactus.asp",
       "Rural road construction under PMGSY; bitumen specification & quality control",
       helpline="1800-11-8998",
       tender_portal="https://pmgsy.nic.in",
       notes="Manages PMGSY rural road programme; bitumen quality monitored via OMMAS"),

    _c("CENT-005", 1, "Delhi", "New Delhi", "Central",
       "Central Public Works Department",
       "CPWD", "MoHUA", "HQ", "PWD",
       28.6244, 77.2167,
       "https://cpwd.gov.in",
       "https://cpwd.gov.in/contact.aspx",
       "Central govt buildings & road infrastructure; bitumen works tender issuer",
       tender_portal="https://etender.cpwd.gov.in",
       notes="Issues tenders for central govt construction including road works"),

    _c("CENT-006", 1, "Delhi", "Delhi Cantonment", "Central",
       "Border Roads Organisation",
       "BRO", "MoD", "HQ", "BRO",
       28.5700, 77.1500,
       "https://bro.gov.in",
       "https://bro.gov.in/contact.htm",
       "Border roads in Ladakh, Arunachal, Sikkim, NE; strategic bitumen buyer",
       tender_portal="https://bro.gov.in/tenders.htm",
       notes="Strategic road builder in border areas; significant bitumen consumer"),

    # ── Group B: NHAI Regional Offices (6) ───────────────────────────────────
    _c("NHAI-RO-N", 1, "Delhi", "New Delhi", "Central",
       "NHAI — Northern Regional Office",
       "NHAI-NRO", "NHAI HQ", "RO", "NHAI",
       28.6139, 77.2090,
       "https://nhai.gov.in",
       "https://nhai.gov.in/contact-us",
       "NH projects in Delhi, UP, Uttarakhand, Himachal, Punjab, Haryana, J&K",
       notes="Contact via NHAI HQ main number; regional email not published separately"),

    _c("NHAI-RO-S", 1, "Tamil Nadu", "Chennai", "Central",
       "NHAI — Southern Regional Office",
       "NHAI-SRO", "NHAI HQ", "RO", "NHAI",
       13.0827, 80.2707,
       "https://nhai.gov.in",
       "https://nhai.gov.in/contact-us",
       "NH projects in TN, Kerala, Karnataka, AP, Telangana",
       notes="Contact via NHAI HQ main number"),

    _c("NHAI-RO-E", 1, "West Bengal", "Kolkata", "Central",
       "NHAI — Eastern Regional Office",
       "NHAI-ERO", "NHAI HQ", "RO", "NHAI",
       22.5726, 88.3639,
       "https://nhai.gov.in",
       "https://nhai.gov.in/contact-us",
       "NH projects in WB, Odisha, Bihar, Jharkhand, NE states",
       notes="Contact via NHAI HQ main number"),

    _c("NHAI-RO-W", 1, "Maharashtra", "Mumbai", "Central",
       "NHAI — Western Regional Office",
       "NHAI-WRO", "NHAI HQ", "RO", "NHAI",
       19.0760, 72.8777,
       "https://nhai.gov.in",
       "https://nhai.gov.in/contact-us",
       "NH projects in Maharashtra, Goa, Gujarat",
       notes="Contact via NHAI HQ main number"),

    _c("NHAI-RO-NW", 1, "Gujarat", "Ahmedabad", "Central",
       "NHAI — North-West Regional Office",
       "NHAI-NWRO", "NHAI HQ", "RO", "NHAI",
       23.0225, 72.5714,
       "https://nhai.gov.in",
       "https://nhai.gov.in/contact-us",
       "NH projects in Rajasthan, Gujarat (NW corridor)",
       notes="Contact via NHAI HQ main number"),

    _c("NHAI-RO-C", 1, "Madhya Pradesh", "Bhopal", "Central",
       "NHAI — Central Regional Office",
       "NHAI-CRO", "NHAI HQ", "RO", "NHAI",
       23.2599, 77.4126,
       "https://nhai.gov.in",
       "https://nhai.gov.in/contact-us",
       "NH projects in MP, Chhattisgarh",
       notes="Contact via NHAI HQ main number"),

    # ── Group C: State PWD / R&B / Highways HQ (28 States) ───────────────────
    _c("ST-AP", 1, "Andhra Pradesh", "Vijayawada", "State",
       "AP Roads & Buildings Department",
       "AP R&B", "AP Govt — I&CAD", "HQ", "PWD",
       16.5062, 80.6480,
       "https://aprd.ap.gov.in",
       "https://aprd.ap.gov.in/contact",
       "State highway & rural road construction; bitumen procurement authority",
       tender_portal="https://tender.apeprocurement.gov.in",
       notes="Handles SH, MDR, ODR bitumen procurement for Andhra Pradesh"),

    _c("ST-AR", 1, "Arunachal Pradesh", "Itanagar", "State",
       "Arunachal Pradesh PWD",
       "AP PWD", "AP Govt", "HQ", "PWD",
       27.0844, 93.6053,
       "https://pwd.arunachal.gov.in",
       "https://pwd.arunachal.gov.in/contact",
       "State roads & bridges; significant bitumen buyer in NE India",
       notes="Strategic state — BRO also active; PWD handles state road bitumen"),

    _c("ST-AS", 1, "Assam", "Dispur", "State",
       "Assam PWD (Roads)",
       "Assam PWD", "Assam Govt", "HQ", "PWD",
       26.1444, 91.7362,
       "https://pwd.assam.gov.in",
       "https://pwd.assam.gov.in/contact-us",
       "SH, MDR, ODR maintenance & construction; bitumen procurement",
       tender_portal="https://assamtenders.gov.in",
       notes="Large state road network; key bitumen buyer in NE region"),

    _c("ST-BR", 1, "Bihar", "Patna", "State",
       "Bihar Road Construction Department",
       "Bihar RCD", "Bihar Govt", "HQ", "PWD",
       25.5941, 85.1376,
       "https://rcd.bih.nic.in",
       "https://rcd.bih.nic.in/ContactUs.aspx",
       "State roads construction & maintenance; bitumen procurement authority",
       tender_portal="https://state.bihar.gov.in/bihargovernment/CitizenHome.html",
       notes="Bihar has large rural road programme; major bitumen consumer"),

    _c("ST-CG", 1, "Chhattisgarh", "Raipur", "State",
       "Chhattisgarh PWD",
       "CG PWD", "CG Govt", "HQ", "PWD",
       21.2514, 81.6296,
       "https://pwdcg.gov.in",
       "https://pwdcg.gov.in/contact",
       "Road construction in mineral-rich state; bitumen procurement for SH/MDR",
       tender_portal="https://cgeprocurement.gov.in",
       notes="Mining & industrial roads drive bitumen demand"),

    _c("ST-GA", 1, "Goa", "Panaji", "State",
       "Goa PWD",
       "Goa PWD", "Goa Govt", "HQ", "PWD",
       15.4909, 73.8278,
       "https://pwd.goa.gov.in",
       "https://pwd.goa.gov.in/contact-us",
       "State road maintenance & new works; bitumen procurement",
       notes="Small state; coastal road network; tourism-driven road upgrades"),

    _c("ST-GJ", 1, "Gujarat", "Gandhinagar", "State",
       "Gujarat Roads & Buildings Department",
       "Gujarat R&B", "Gujarat Govt", "HQ", "PWD",
       23.2156, 72.6369,
       "https://roads.gujarat.gov.in",
       "https://roads.gujarat.gov.in/contactus.htm",
       "Major SH network; large bitumen buyer; VG-10/VG-30 procurement",
       official_email="Contact Not Published – Use Block/District Office",
       tender_portal="https://nprocure.com",
       notes="One of India's most developed road networks; major bitumen consumer"),

    _c("ST-HR", 1, "Haryana", "Chandigarh", "State",
       "Haryana PWD (B&R)",
       "Haryana PWD", "Haryana Govt", "HQ", "PWD",
       30.7333, 76.7794,
       "https://pwdharyana.gov.in",
       "https://pwdharyana.gov.in/contact-us",
       "SH, MDR, bridges; bitumen procurement for NCR-linked roads",
       tender_portal="https://etenders.hry.nic.in",
       notes="NCR adjacency drives construction activity; key bitumen buyer"),

    _c("ST-HP", 1, "Himachal Pradesh", "Shimla", "State",
       "Himachal Pradesh PWD",
       "HP PWD", "HP Govt", "HQ", "PWD",
       31.1048, 77.1734,
       "https://hppwd.hp.gov.in",
       "https://hppwd.hp.gov.in/contact",
       "Mountain roads & tunnels; bitumen procurement in hill terrain",
       notes="Hill terrain requires modified bitumen PMB/CRMB; specialist buyer"),

    _c("ST-JH", 1, "Jharkhand", "Ranchi", "State",
       "Jharkhand Road Construction Department",
       "Jharkhand RCD", "Jharkhand Govt", "HQ", "PWD",
       23.3441, 85.3096,
       "https://rcd.jharkhand.gov.in",
       "https://rcd.jharkhand.gov.in/contact-us",
       "State road network; tribal area connectivity; bitumen procurement",
       tender_portal="https://jktenders.gov.in",
       notes="PMGSY overlap; focus on rural connectivity in tribal areas"),

    _c("ST-KA", 1, "Karnataka", "Bengaluru", "State",
       "Karnataka PWD",
       "Karnataka PWD", "Karnataka Govt", "HQ", "PWD",
       12.9716, 77.5946,
       "https://pwd.karnataka.gov.in",
       "https://pwd.karnataka.gov.in/english/contact-us",
       "SH network, urban arterials; large bitumen procurement state",
       tender_portal="https://kprocure.karnataka.gov.in",
       notes="Bengaluru infrastructure & SH upgrades drive high bitumen demand"),

    _c("ST-KL", 1, "Kerala", "Thiruvananthapuram", "State",
       "Kerala PWD (Roads & Bridges)",
       "Kerala PWD", "Kerala Govt", "HQ", "PWD",
       8.5241, 76.9366,
       "https://pwd.kerala.gov.in",
       "https://pwd.kerala.gov.in/contact",
       "State road & bridge network; bitumen procurement authority",
       tender_portal="https://etenders.kerala.gov.in",
       notes="Dense road network; high rainfall → PMB/CRMB usage for durability"),

    _c("ST-MP", 1, "Madhya Pradesh", "Bhopal", "State",
       "Madhya Pradesh PWD",
       "MP PWD", "MP Govt", "HQ", "PWD",
       23.2599, 77.4126,
       "https://mpmpwd.nic.in",
       "https://mpmpwd.nic.in/contact-us",
       "Large SH/MDR network; major bitumen consumer in central India",
       tender_portal="https://mptenders.gov.in",
       notes="MP has one of India's largest state road networks by km"),

    _c("ST-MH", 1, "Maharashtra", "Mumbai", "State",
       "Maharashtra PWD",
       "MH PWD", "Maharashtra Govt", "HQ", "PWD",
       19.0760, 72.8777,
       "https://pwd.maharashtra.gov.in",
       "https://pwd.maharashtra.gov.in/1076/Contact-Us",
       "Largest state road dept by budget; SH/MDR/NH bitumen procurement",
       tender_portal="https://mahatenders.gov.in",
       notes="Highest road construction budget state; major bitumen consumer"),

    _c("ST-MN", 1, "Manipur", "Imphal", "State",
       "Manipur PWD",
       "Manipur PWD", "Manipur Govt", "HQ", "PWD",
       24.8170, 93.9368,
       "https://pwd.manipur.gov.in",
       "https://pwd.manipur.gov.in/contact",
       "Strategic NE state roads; bitumen procurement for hilly terrain",
       notes="BRO active alongside PWD; hill terrain needs modified bitumen"),

    _c("ST-ML", 1, "Meghalaya", "Shillong", "State",
       "Meghalaya PWD",
       "Meghalaya PWD", "Meghalaya Govt", "HQ", "PWD",
       25.5788, 91.8933,
       "https://megpwd.gov.in",
       "https://megpwd.gov.in/contact",
       "State road network in hilly terrain; bitumen procurement",
       notes="High rainfall state; modified bitumen important for road durability"),

    _c("ST-MZ", 1, "Mizoram", "Aizawl", "State",
       "Mizoram PWD",
       "Mizoram PWD", "Mizoram Govt", "HQ", "PWD",
       23.7307, 92.7173,
       "https://pwd.mizoram.gov.in",
       "https://pwd.mizoram.gov.in/contact",
       "NE state mountain road network; bitumen procurement",
       notes="Strategic location near Myanmar border; NHIDCL also active"),

    _c("ST-NL", 1, "Nagaland", "Kohima", "State",
       "Nagaland PWD",
       "Nagaland PWD", "Nagaland Govt", "HQ", "PWD",
       25.6751, 94.1086,
       "https://pwdnagaland.gov.in",
       "https://pwdnagaland.gov.in/contact-us",
       "State road network; bitumen procurement for hill roads",
       notes="BRO active for strategic roads; PWD for state network"),

    _c("ST-OD", 1, "Odisha", "Bhubaneswar", "State",
       "Odisha Works Department",
       "Odisha WD", "Odisha Govt", "HQ", "PWD",
       20.2961, 85.8245,
       "https://works.odisha.gov.in",
       "https://works.odisha.gov.in/contact.htm",
       "SH/MDR road construction; port connectivity roads; bitumen procurement",
       tender_portal="https://tendersodisha.gov.in",
       notes="Port connectivity to Paradip, Dhamra drives bitumen logistics"),

    _c("ST-PB", 1, "Punjab", "Chandigarh", "State",
       "Punjab PWD (B&R)",
       "Punjab PWD", "Punjab Govt", "HQ", "PWD",
       30.7333, 76.7794,
       "https://punjabpwdbr.gov.in",
       "https://punjabpwdbr.gov.in/contact",
       "NH, SH, MDR maintenance & new works; bitumen procurement",
       tender_portal="https://eproc.punjab.gov.in",
       notes="High traffic NH connectivity; VG-40 preferred for heavy loads"),

    _c("ST-RJ", 1, "Rajasthan", "Jaipur", "State",
       "Rajasthan PWD",
       "Rajasthan PWD", "Rajasthan Govt", "HQ", "PWD",
       26.9124, 75.7873,
       "https://pwd.rajasthan.gov.in",
       "https://pwd.rajasthan.gov.in/content/raj/pwd/en/home.html",
       "Largest state by area; NH/SH/MDR bitumen procurement authority",
       tender_portal="https://sppp.rajasthan.gov.in",
       notes="Desert terrain requires VG-30/VG-40 for high temperature performance"),

    _c("ST-SK", 1, "Sikkim", "Gangtok", "State",
       "Sikkim PWD",
       "Sikkim PWD", "Sikkim Govt", "HQ", "PWD",
       27.3314, 88.6138,
       "https://spwd.sikkim.gov.in",
       "https://spwd.sikkim.gov.in/contact",
       "Mountain road network; bitumen procurement for high altitude roads",
       notes="High altitude requires modified bitumen; BRO active on strategic roads"),

    _c("ST-TN", 1, "Tamil Nadu", "Chennai", "State",
       "Tamil Nadu Highways Department",
       "TNHD", "TN Govt", "HQ", "PWD",
       13.0827, 80.2707,
       "https://tnhighways.gov.in",
       "https://tnhighways.gov.in/contact",
       "SH network & urban expressways; large bitumen procurement state",
       tender_portal="https://tntenders.gov.in",
       notes="Major bitumen hub — Chennai receives imported bitumen via Ennore/Chennai Port"),

    _c("ST-TG", 1, "Telangana", "Hyderabad", "State",
       "Telangana Roads & Buildings Department",
       "TG R&B", "Telangana Govt", "HQ", "PWD",
       17.3850, 78.4867,
       "https://tgrb.telangana.gov.in",
       "https://tgrb.telangana.gov.in/Contact",
       "SH, MDR, urban road works; bitumen procurement authority",
       tender_portal="https://tender.telangana.gov.in",
       notes="Hyderabad urban infrastructure + SH expansion drives bitumen demand"),

    _c("ST-TR", 1, "Tripura", "Agartala", "State",
       "Tripura PWD",
       "Tripura PWD", "Tripura Govt", "HQ", "PWD",
       23.8315, 91.2868,
       "https://pwd.tripura.gov.in",
       "https://pwd.tripura.gov.in/contact",
       "NE state road network; bitumen procurement",
       notes="Bangladesh border state; NH 8 critical corridor"),

    _c("ST-UP", 1, "Uttar Pradesh", "Lucknow", "State",
       "Uttar Pradesh PWD",
       "UP PWD", "UP Govt", "HQ", "PWD",
       26.8467, 80.9462,
       "https://uppwd.gov.in",
       "https://uppwd.gov.in/en/contact",
       "Largest state road network; massive bitumen procurement authority",
       tender_portal="https://etender.up.nic.in",
       notes="UP has the largest SH network; expressways managed by UPEIDA"),

    _c("ST-UK", 1, "Uttarakhand", "Dehradun", "State",
       "Uttarakhand PWD",
       "UK PWD", "UK Govt", "HQ", "PWD",
       30.3165, 78.0322,
       "https://pwduk.uk.gov.in",
       "https://pwduk.uk.gov.in/contact.html",
       "Hill road network, Char Dham connectivity; bitumen procurement",
       notes="Char Dham all-weather road project major bitumen consumer"),

    _c("ST-WB", 1, "West Bengal", "Kolkata", "State",
       "West Bengal PWD",
       "WB PWD", "WB Govt", "HQ", "PWD",
       22.5726, 88.3639,
       "https://wbpwd.gov.in",
       "https://wbpwd.gov.in/contact",
       "SH/MDR road works; bitumen procurement; Haldia port connectivity",
       tender_portal="https://wbtenders.gov.in",
       notes="Haldia port key bitumen import point for eastern India"),

    # ── Group C: Union Territory PWD / Engg Depts (8 UTs) ───────────────────
    _c("UT-AN", 1, "Andaman & Nicobar Islands", "Port Blair", "State",
       "Andaman & Nicobar PWD",
       "AN PWD", "MoHA (UT Admin)", "HQ", "PWD",
       11.6234, 92.7265,
       "https://pwd.andaman.gov.in",
       "https://pwd.andaman.gov.in/contact.htm",
       "Island road network; bitumen shipped from mainland",
       notes="Bitumen logistics by sea from Haldia/Chennai; small volume"),

    _c("UT-CH", 1, "Chandigarh", "Chandigarh", "State",
       "Chandigarh Administration — Engineering Dept",
       "CHD Engg", "MoHA (UT Admin)", "HQ", "PWD",
       30.7333, 76.7794,
       "https://chandigarh.gov.in/engg_dept.htm",
       "https://chandigarh.gov.in/contact_us.htm",
       "UT road & infrastructure maintenance; bitumen procurement",
       notes="Shared capital with Punjab & Haryana; UT roads under central admin"),

    _c("UT-DD", 1, "Dadra & Nagar Haveli and Daman & Diu", "Daman", "State",
       "DNH & DD PWD",
       "DNH-DD PWD", "MoHA (UT Admin)", "HQ", "PWD",
       20.3974, 72.8328,
       "https://dnh.nic.in/departments/pwd.aspx",
       "https://dnh.nic.in/contact.aspx",
       "UT road network; bitumen procurement for small UT",
       notes="Merged UT since 2020; small road network"),

    _c("UT-DL", 1, "Delhi", "New Delhi", "State",
       "Delhi PWD",
       "Delhi PWD", "GNCT Delhi", "HQ", "PWD",
       28.6139, 77.2090,
       "https://pwd.delhi.gov.in",
       "https://pwd.delhi.gov.in/wps/portal/PWD/HomePage/Department/contactUs",
       "Delhi road network maintenance & construction; bitumen procurement",
       official_email="pwd-delhi@nic.in",
       tender_portal="https://delhigovt.nic.in/newdelhi/tender.asp",
       notes="High-value urban road works; frequent resurfacing demand"),

    _c("UT-JK", 1, "Jammu & Kashmir", "Jammu", "State",
       "J&K PWD (R&B)",
       "JK PWD", "J&K UT Admin / MoHA", "HQ", "PWD",
       32.7266, 74.8570,
       "https://jkpwd.nic.in",
       "https://jkpwd.nic.in/contactUs",
       "UT road network in J&K; strategic bitumen buyer; NHIDCL also active",
       tender_portal="https://jktenders.gov.in",
       notes="Post-Article 370 UT; large road investment; modified bitumen for high altitude"),

    _c("UT-LA", 1, "Ladakh", "Leh", "State",
       "Ladakh PWD",
       "Ladakh PWD", "MoHA (UT Admin)", "HQ", "PWD",
       34.1526, 77.5771,
       "https://lahdc.nic.in",
       "https://lahdc.nic.in/contact",
       "High altitude road network; strategic bitumen procurement",
       notes="World's highest roads; cold-climate modified bitumen required; BRO also active"),

    _c("UT-LD", 1, "Lakshadweep", "Kavaratti", "State",
       "Lakshadweep PWD",
       "LD PWD", "MoHA (UT Admin)", "HQ", "PWD",
       10.5669, 72.6420,
       "https://lakgov.gov.in/pages/display/61-public-works-department",
       "https://lakgov.gov.in/contact",
       "Island road network; very small bitumen volume",
       notes="Bitumen shipped by sea from Kerala; tiny volume; unique island logistics"),

    _c("UT-PY", 1, "Puducherry", "Puducherry", "State",
       "Puducherry PWD",
       "Puducherry PWD", "MoHA (UT Admin)", "HQ", "PWD",
       11.9416, 79.8083,
       "https://pwd.py.gov.in",
       "https://pwd.py.gov.in/contact-us",
       "UT road construction & maintenance; bitumen procurement",
       notes="Small UT with 4 pockets (Puducherry, Karaikal, Mahé, Yanam)"),

    # ── Group D: State Road Development Corporations (8) ─────────────────────
    _c("CORP-MH", 1, "Maharashtra", "Mumbai", "State",
       "Maharashtra State Road Development Corporation",
       "MSRDC", "Maharashtra Govt", "HQ", "StateCorpn",
       19.0760, 72.8777,
       "https://msrdc.org",
       "https://msrdc.org/contact.html",
       "Expressways, BOT projects; large bitumen buyer (Mumbai-Pune Exp, Samruddhi)",
       official_email="ms@msrdc.org",
       official_phone="+91-22-26592222",
       tender_portal="https://msrdc.org/tenders",
       notes="Samruddhi Mahamarg — one of India's largest greenfield highway projects"),

    _c("CORP-GJ", 1, "Gujarat", "Gandhinagar", "State",
       "Gujarat State Road Development Corporation",
       "GSRDC", "Gujarat Govt", "HQ", "StateCorpn",
       23.2156, 72.6369,
       "https://gsrdc.gujarat.gov.in",
       "https://gsrdc.gujarat.gov.in/contact",
       "SH upgrades, expressways; bitumen procurement for Gujarat state highways",
       tender_portal="https://gsrdc.gujarat.gov.in/tenders",
       notes="Key player in Ahmedabad-Mumbai corridor and Delhi-Mumbai corridor projects"),

    _c("CORP-KA", 1, "Karnataka", "Bengaluru", "State",
       "Karnataka Road Development Corporation",
       "KRDCL", "Karnataka Govt", "HQ", "StateCorpn",
       12.9716, 77.5946,
       "https://krdcl.in",
       "https://krdcl.in/contactus",
       "Expressways, BOT projects in Karnataka; bitumen procurement",
       official_email="md@krdcl.in",
       official_phone="+91-80-22282200",
       tender_portal="https://krdcl.in/tenders",
       notes="Ring road projects, elevated corridors; significant bitumen buyer"),

    _c("CORP-AP", 1, "Andhra Pradesh", "Vijayawada", "State",
       "Andhra Pradesh Road Development Corporation",
       "APRDC", "AP Govt", "HQ", "StateCorpn",
       16.5062, 80.6480,
       "https://aproadways.ap.gov.in",
       "https://aproadways.ap.gov.in/contact",
       "Expressways & SH corridors; Amaravati access roads; bitumen procurement",
       tender_portal="https://aproadways.ap.gov.in/tenders",
       notes="AP capital region & coastal corridor projects drive bitumen demand"),

    _c("CORP-TN", 1, "Tamil Nadu", "Chennai", "State",
       "Tamil Nadu Road Development Company",
       "TNRDC", "TN Govt", "HQ", "StateCorpn",
       13.0827, 80.2707,
       "https://tnrdc.in",
       "https://tnrdc.in/contact.html",
       "BOT expressways, Chennai bypass; bitumen procurement",
       official_email="info@tnrdc.in",
       official_phone="+91-44-28272727",
       tender_portal="https://tnrdc.in/tenders",
       notes="Chennai Peripheral Ring Road, ECR projects; key bitumen buyer"),

    _c("CORP-RJ", 1, "Rajasthan", "Jaipur", "State",
       "Rajasthan State Road Development & Construction Corporation",
       "RSRDC", "Rajasthan Govt", "HQ", "StateCorpn",
       26.9124, 75.7873,
       "https://rsrdc.rajasthan.gov.in",
       "https://rsrdc.rajasthan.gov.in/contact",
       "SH upgrades, BOT roads; desert-grade bitumen procurement",
       tender_portal="https://rsrdc.rajasthan.gov.in/tenders",
       notes="High temperature environment → VG-40 bitumen preferred"),

    _c("CORP-HR", 1, "Haryana", "Gurugram", "State",
       "Haryana Road Infrastructure Development Corporation",
       "HRIDC", "Haryana Govt", "HQ", "StateCorpn",
       28.4595, 77.0266,
       "https://hridc.org",
       "https://hridc.org/contact",
       "Expressways, BOT projects in Haryana; bitumen procurement",
       official_email="info@hridc.org",
       tender_portal="https://hridc.org/tenders",
       notes="Delhi NCR connectivity projects; high-volume bitumen buyer"),

    _c("CORP-UP", 1, "Uttar Pradesh", "Lucknow", "State",
       "UP Expressways Industrial Development Authority",
       "UPEIDA", "UP Govt — PWD Dept", "HQ", "StateCorpn",
       26.8467, 80.9462,
       "https://upeida.in",
       "https://upeida.in/contact-us",
       "Expressways (Agra-Lucknow, Purvanchal, Gorakhpur, Bundelkhand, Ganga); major bitumen buyer",
       official_email="info@upeida.in",
       official_phone="+91-522-2238187",
       tender_portal="https://upeida.in/tender",
       notes="Manages 5+ expressways; one of India's largest expressway developers; huge bitumen consumer"),
]

# ══════════════════════════════════════════════════════════════════════════════
# INIT & PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════

def init_directory() -> None:
    """Create the 6 tbl_dir_*.json files if absent. Write SEED_PHASE1 to tbl_dir_orgs if empty."""
    with _lock:
        _tables = [
            (TBL_DIR_ORGS,    []),
            (TBL_DIR_SOURCES, []),
            (TBL_DIR_CHANGES, []),
            (TBL_DIR_FETCHES, []),
            (TBL_DIR_BUGS,    []),
            (TBL_DIR_GEO,     []),
        ]
        for path, default in _tables:
            if not path.exists():
                _save(path, default)

        # Seed orgs if empty
        orgs = _load(TBL_DIR_ORGS, [])
        if not orgs:
            _save(TBL_DIR_ORGS, SEED_PHASE1)


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH & FILTER
# ══════════════════════════════════════════════════════════════════════════════
_SEARCH_FIELDS = [
    "org_id", "dept_name", "short_name", "city", "state_ut",
    "official_email", "official_phone", "helpline",
    "roads_role", "notes", "address", "website",
]


def search_directory(
    query: str = "",
    filters: Optional[Dict] = None,
    page: int = 0,
    page_size: int = 25,
) -> dict:
    """Full-text + field search with filters.

    Filters keys (all optional):
        level       : list[str]  — Central | State | City | District | Block
        state_ut    : list[str]
        dept_type   : list[str]  — NHAI | PWD | PMGSY | BRO | StateCorpn | Municipal
        has_email   : bool
        has_phone   : bool
        confidence  : list[str]  — High | Medium | Low
        phase       : list[int]

    Returns:
        {results, total, pages, page, page_size, coverage_pct}
    """
    orgs: List[dict] = _load(TBL_DIR_ORGS, [])
    filters = filters or {}
    q = query.strip().lower()

    def _match(org: dict) -> bool:
        # Full-text search
        if q:
            haystack = " ".join(str(org.get(f, "")) for f in _SEARCH_FIELDS).lower()
            if q not in haystack:
                return False
        # Level filter
        if filters.get("level"):
            if org.get("level") not in filters["level"]:
                return False
        # State filter
        if filters.get("state_ut"):
            if org.get("state_ut") not in filters["state_ut"]:
                return False
        # Dept type filter
        if filters.get("dept_type"):
            if org.get("dept_type") not in filters["dept_type"]:
                return False
        # Has email
        if filters.get("has_email"):
            email = org.get("official_email", "")
            if not email or "not published" in email.lower():
                return False
        # Has phone
        if filters.get("has_phone"):
            phone = org.get("official_phone", "") or org.get("helpline", "")
            if not phone:
                return False
        # Confidence filter
        if filters.get("confidence"):
            if org.get("confidence") not in filters["confidence"]:
                return False
        # Phase filter
        if filters.get("phase"):
            if org.get("phase") not in filters["phase"]:
                return False
        return True

    results = [o for o in orgs if _match(o)]
    total   = len(results)
    pages   = max(1, (total + page_size - 1) // page_size)
    start   = page * page_size
    slice_  = results[start: start + page_size]

    # Coverage: what % of SEED targets are in the file
    target = len(SEED_PHASE1)
    found  = sum(1 for o in orgs if o.get("phase") == 1)
    coverage_pct = round(100.0 * found / target, 1) if target else 0.0

    return {
        "results":      slice_,
        "total":        total,
        "pages":        pages,
        "page":         page,
        "page_size":    page_size,
        "coverage_pct": coverage_pct,
    }


# ══════════════════════════════════════════════════════════════════════════════
# COVERAGE REPORT
# ══════════════════════════════════════════════════════════════════════════════
_PHASE1_STATES = sorted(set(o["state_ut"] for o in SEED_PHASE1))

_PHASE_TARGETS = {1: 56, 2: 700, 3: 4000, 4: 30000}


def get_coverage_report() -> dict:
    """Returns coverage stats per phase + state-wise breakdown."""
    orgs: List[dict] = _load(TBL_DIR_ORGS, [])

    phase_counts: Dict[int, int] = {}
    for ph in [1, 2, 3, 4]:
        phase_counts[ph] = sum(1 for o in orgs if o.get("phase") == ph)

    # State-wise Phase 1 coverage
    pct_by_state: Dict[str, dict] = {}
    for st in _PHASE1_STATES:
        found = sum(1 for o in orgs if o.get("state_ut") == st and o.get("phase") == 1)
        pct_by_state[st] = {"found": found, "target": 1}

    p1_target = _PHASE_TARGETS[1]
    p1_found  = phase_counts[1]

    return {
        "phase1": {
            "total":       p1_found,
            "target":      p1_target,
            "pct":         round(100.0 * p1_found / p1_target, 1) if p1_target else 0.0,
            "pct_by_state": pct_by_state,
        },
        "phase2": {
            "total":  phase_counts[2],
            "target": _PHASE_TARGETS[2],
            "pct":    round(100.0 * phase_counts[2] / _PHASE_TARGETS[2], 1) if _PHASE_TARGETS[2] else 0.0,
        },
        "phase3": {
            "total":  phase_counts[3],
            "target": _PHASE_TARGETS[3],
            "pct":    round(100.0 * phase_counts[3] / _PHASE_TARGETS[3], 1) if _PHASE_TARGETS[3] else 0.0,
        },
        "phase4": {
            "total":  phase_counts[4],
            "target": _PHASE_TARGETS[4],
            "pct":    round(100.0 * phase_counts[4] / _PHASE_TARGETS[4], 1) if _PHASE_TARGETS[4] else 0.0,
        },
        "grand_total": len(orgs),
        "generated_ist": _ist_now(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CRM INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

def _get_org(org_id: str) -> Optional[dict]:
    orgs = _load(TBL_DIR_ORGS, [])
    for o in orgs:
        if o.get("org_id") == org_id:
            return o
    return None


def add_org_to_crm(org_id: str, task_type: str = "Email", note: str = "") -> str:
    """Create a CRM task for this org via crm_engine.add_task(). Returns task_id string."""
    try:
        import crm_engine
    except ImportError:
        return ""

    org = _get_org(org_id)
    if not org:
        return ""

    client_name = org.get("dept_name", org_id)
    due_dt = datetime.datetime.now() + datetime.timedelta(hours=24)
    due_str = due_dt.strftime("%Y-%m-%d %H:%M")
    full_note = (
        f"[Directory] {org.get('roads_role', '')} | "
        f"City: {org.get('city', '')} | "
        f"State: {org.get('state_ut', '')} | "
        f"Web: {org.get('website', '')} | "
        f"Conf: {org.get('confidence', '')}. {note}"
    ).strip(". ")

    result = crm_engine.add_task(
        client_name=client_name,
        task_type=task_type,
        due_date_str=due_str,
        priority="Medium",
        note=full_note,
        automated=True,
    )
    return str(result.get("id", "")) if isinstance(result, dict) else str(result)


def create_task_for_org(
    org_id: str, task_type: str, due_hours: int = 24, note: str = ""
) -> str:
    """Create a follow-up CRM task with custom due time. Returns task_id."""
    try:
        import crm_engine
    except ImportError:
        return ""

    org = _get_org(org_id)
    if not org:
        return ""

    client_name = org.get("dept_name", org_id)
    due_dt  = datetime.datetime.now() + datetime.timedelta(hours=due_hours)
    due_str = due_dt.strftime("%Y-%m-%d %H:%M")
    full_note = (
        f"[Dir Follow-up] {org.get('city', '')} / {org.get('state_ut', '')} — "
        f"{org.get('roads_role', '')}. {note}"
    ).strip()

    result = crm_engine.add_task(
        client_name=client_name,
        task_type=task_type,
        due_date_str=due_str,
        priority="Medium",
        note=full_note,
        automated=False,
    )
    return str(result.get("id", "")) if isinstance(result, dict) else str(result)


# ══════════════════════════════════════════════════════════════════════════════
# CHANGE LOG & UPDATE
# ══════════════════════════════════════════════════════════════════════════════

def log_change(
    org_id: str, field: str, old_val: str, new_val: str, source_url: str
) -> None:
    """Append a change record to tbl_dir_changes.json."""
    with _lock:
        changes = _load(TBL_DIR_CHANGES, [])
        change_id = f"CHG-{uuid.uuid4().hex[:8].upper()}"
        changes.append({
            "change_id":  change_id,
            "org_id":     org_id,
            "field":      field,
            "old_val":    old_val,
            "new_val":    new_val,
            "source_url": source_url,
            "changed_ist": _ist_now(),
        })
        # Keep last 5000 changes
        if len(changes) > 5000:
            changes = changes[-5000:]
        _save(TBL_DIR_CHANGES, changes)


def update_org(org_id: str, fields: dict) -> None:
    """Update specific fields of an org record + log each change. Called by fetcher."""
    with _lock:
        orgs = _load(TBL_DIR_ORGS, [])
        for i, org in enumerate(orgs):
            if org.get("org_id") == org_id:
                for field, new_val in fields.items():
                    old_val = str(org.get(field, ""))
                    if str(new_val) != old_val:
                        log_change(
                            org_id=org_id,
                            field=field,
                            old_val=old_val,
                            new_val=str(new_val),
                            source_url=org.get("source_url", ""),
                        )
                    org[field] = new_val
                org["last_fetched_ist"] = _ist_now()
                orgs[i] = org
                break
        _save(TBL_DIR_ORGS, orgs)
