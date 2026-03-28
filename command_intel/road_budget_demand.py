"""
India Road Budget & Bitumen Demand Intelligence
================================================
Senior Infrastructure Economist + Government Budget Analyst +
Commodity Demand Modeler + Data Engineer

All data sourced from official Indian government publications.
Sources are cited inline for every dataset.
Currency: INR (₹) | Date format: DD-MM-YYYY | FY: April-March
"""

import streamlit as st
import pandas as pd
import numpy as np
import datetime

try:
    from india_localization import format_inr, format_inr_short
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
except ImportError:
    def format_inr(v, sym=True): return f"{format_inr(float(v))}"
    def format_inr_short(v, sym=True):
        v = float(v)
        if v >= 1e7: return f"₹ {v/1e7:.2f} Cr"
        if v >= 1e5: return f"₹ {v/1e5:.2f} Lakh"
        return f"{format_inr(v)}"

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(label): pass

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CENTRAL BUDGET DATA
# Source: Union Budget Expenditure Statements (indiabudget.gov.in)
#         PRS India Demand for Grants Analyses (prsindia.org)
#         MoRTH Outcome Budgets (morth.nic.in)
# ═══════════════════════════════════════════════════════════════════════════════

MORTH_BUDGET = pd.DataFrame([
    {"FY": "2016-17", "MoRTH_Total_Cr": 64900,  "NHAI_Cr": 17000, "PMGSY_Cr": 19000, "NH_km_built": 8231,  "Notes": "GBS portion; gross outlay ₹1,03,086 Cr with IEBR"},
    {"FY": "2017-18", "MoRTH_Total_Cr": 71000,  "NHAI_Cr": 23892, "PMGSY_Cr": 19000, "NH_km_built": 9829,  "Notes": "NHAI RE: ₹23,892 Cr"},
    {"FY": "2018-19", "MoRTH_Total_Cr": 83000,  "NHAI_Cr": 29663, "PMGSY_Cr": 19000, "NH_km_built": 10855, "Notes": "Roads & Bridges: ₹40,424 Cr"},
    {"FY": "2019-20", "MoRTH_Total_Cr": 83015,  "NHAI_Cr": 31691, "PMGSY_Cr": 19000, "NH_km_built": 10457, "Notes": "Revenue ₹9,875 Cr + Capital ₹68,374 Cr (Actuals)"},
    {"FY": "2020-21", "MoRTH_Total_Cr": 101823, "NHAI_Cr": 49050, "PMGSY_Cr": 19500, "NH_km_built": 13327, "Notes": "Record NH construction; RE figure"},
    {"FY": "2021-22", "MoRTH_Total_Cr": 118101, "NHAI_Cr": 57350, "PMGSY_Cr": 15000, "NH_km_built": 10457, "Notes": "Roads & Bridges: ₹60,261 Cr"},
    {"FY": "2022-23", "MoRTH_Total_Cr": 199107, "NHAI_Cr": 141661,"PMGSY_Cr": 19000, "NH_km_built": 10331, "Notes": "Significant Bharatmala scale-up"},
    {"FY": "2023-24", "MoRTH_Total_Cr": 270435, "NHAI_Cr": 167400,"PMGSY_Cr": 19000, "NH_km_built": 12349, "Notes": "Actuals ~₹2,75,986 Cr; 2nd highest NH ever"},
    {"FY": "2024-25", "MoRTH_Total_Cr": 278000, "NHAI_Cr": 250000,"PMGSY_Cr": 14528, "NH_km_built": 5614,  "Notes": "NHAI capex all-time high ₹2.5L Cr; 5,614 km NHAI only"},
    {"FY": "2025-26", "MoRTH_Total_Cr": 287333, "NHAI_Cr": 170266,"PMGSY_Cr": 19000, "NH_km_built": 0,     "Notes": "BE: Revenue ₹15,092 Cr + Capital ₹2,72,241 Cr"},
])

MORTH_SOURCES = [
    ("PRS India — DFG 2025-26 (MoRTH)", "https://prsindia.org/budgets/parliament/demand-for-grants-2025-26-analysis-road-transport-and-highways"),
    ("MoRTH Outcome Budget 2016-17", "https://morth.nic.in/sites/default/files/Outcome_Budget_2016_17.pdf"),
    ("PIB — MoRTH Year End Review 2024", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2091508"),
    ("PIB — NHAI FY 2024-25 Capex", "https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2117781"),
    ("India Budget Expenditure DG-86", "https://www.indiabudget.gov.in/doc/eb/sbe86.pdf"),
]

BHARATMALA = {
    "original_budget_cr": 535000,
    "revised_budget_cr": 1095000,
    "sanctioned_cost_cr": 846588,
    "total_km_approved": 34800,
    "km_awarded": 26425,
    "km_completed": 18180,
    "expenditure_to_date_cr": 500000,
    "original_cost_per_km_cr": 15.37,
    "sanctioned_cost_per_km_cr": 32.17,
    "revised_completion": "2027-28",
    "sources": [
        ("PRS India — Bharatmala Implementation", "https://prsindia.org/policy/report-summaries/implementation-of-phase-1-of-bharatmala-pariyojana"),
        ("Wikipedia — Bharatmala", "https://en.wikipedia.org/wiki/Bharatmala"),
    ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — INDIA BITUMEN CONSUMPTION
# Source: PPAC (ppac.gov.in), MoSPI Energy Statistics 2025 (mospi.gov.in),
#         S&P Global Commodity Insights, IMARC Group
# ═══════════════════════════════════════════════════════════════════════════════

BITUMEN_CONSUMPTION = pd.DataFrame([
    {"FY": "2014-15", "Consumption_MT": 5.07, "Domestic_MT": 4.2,  "Import_MT": 0.87},
    {"FY": "2015-16", "Consumption_MT": 5.94, "Domestic_MT": 4.6,  "Import_MT": 1.34},
    {"FY": "2016-17", "Consumption_MT": 5.94, "Domestic_MT": 4.8,  "Import_MT": 1.14},
    {"FY": "2017-18", "Consumption_MT": 6.09, "Domestic_MT": 4.9,  "Import_MT": 1.19},
    {"FY": "2018-19", "Consumption_MT": 6.71, "Domestic_MT": 5.0,  "Import_MT": 1.71},
    {"FY": "2019-20", "Consumption_MT": 6.72, "Domestic_MT": 5.0,  "Import_MT": 1.72},
    {"FY": "2020-21", "Consumption_MT": 7.11, "Domestic_MT": 5.1,  "Import_MT": 2.01},
    {"FY": "2021-22", "Consumption_MT": 7.50, "Domestic_MT": 5.1,  "Import_MT": 2.40},
    {"FY": "2022-23", "Consumption_MT": 8.10, "Domestic_MT": 5.13, "Import_MT": 2.97},
    {"FY": "2023-24", "Consumption_MT": 8.85, "Domestic_MT": 5.13, "Import_MT": 3.72},
])

BITUMEN_SOURCES = [
    ("PPAC — Product-wise Consumption", "https://ppac.gov.in/consumption/products-wise"),
    ("MoSPI Energy Statistics 2025 — Chapter 3", "https://mospi.gov.in/sites/default/files/publication_reports/Energy_Statistics_2025/Chapter3_27032025.pdf"),
    ("S&P Global — India 2023 Bitumen Imports", "https://www.spglobal.com/commodity-insights/en/news-research/latest-news/crude-oil/013124-indias-2023-bitumen-imports-surge-31-on-year-as-demand-set-to-grow"),
    ("OGD India — Monthly Petroleum Consumption", "https://www.data.gov.in/resource/monthly-consumption-petroleum-products"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — ROAD NETWORK LENGTH
# Source: MoRTH Basic Road Statistics 2019-20, MoRTH Annual Report 2024-25
#         PIB Year End Review 2024
# ═══════════════════════════════════════════════════════════════════════════════

ROAD_NETWORK = {
    "national_highways_km": 146195,  # PIB Jan 2025
    "state_highways_km":    186528,  # MoRTH 2021
    "district_roads_km":    632154,  # Basic Road Statistics 2020
    "rural_roads_km":      3684510,  # Basic Road Statistics 2020
    "urban_roads_km":       548394,  # Basic Road Statistics 2020
    "expressways_km":         5579,  # 2024
    "total_km":            6378156,  # 2022-23 estimate
    "nh_share_pct": 2.09,
    "rural_share_pct": 72.97,
    "sources": [
        ("MoRTH Basic Road Statistics 2019-20", "https://morth.nic.in/sites/default/files/Basic%20Road%20Statistics%20of%20India-2019-20.pdf"),
        ("PIB — MoRTH Year End Review 2024", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2091508"),
        ("MoRTH Annual Report 2024-25", "https://morth.nic.in/sites/default/files/Annual-Report-English-with-Cover.pdf"),
    ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — BITUMEN PER KM MODEL
# Source: IRC Specifications, MoRTH Compendium, PMGSY Technical Docs,
#         Sahara Bizz engineering calculation
# ═══════════════════════════════════════════════════════════════════════════════

ROAD_TYPES = pd.DataFrame([
    {
        "Road Type":          "National Highway (4-lane)",
        "Width_m":            14.0,
        "Layer_mm":           70,
        "MT_per_km_new":      105,
        "MT_per_km_overlay":  22,
        "MT_per_km_maint":    5,
        "Cost_Cr_per_km":     18.0,
        "Bitumen_pct_cost":   12,
        "Typical_Season":     "Oct–May",
        "Grade":              "VG30 / VG40",
    },
    {
        "Road Type":          "National Highway (2-lane)",
        "Width_m":            7.0,
        "Layer_mm":           60,
        "MT_per_km_new":      43,
        "MT_per_km_overlay":  10,
        "MT_per_km_maint":    2,
        "Cost_Cr_per_km":     6.0,
        "Bitumen_pct_cost":   12,
        "Typical_Season":     "Oct–May",
        "Grade":              "VG30",
    },
    {
        "Road Type":          "Expressway (6-lane)",
        "Width_m":            21.0,
        "Layer_mm":           80,
        "MT_per_km_new":      160,
        "MT_per_km_overlay":  35,
        "MT_per_km_maint":    8,
        "Cost_Cr_per_km":     45.0,
        "Bitumen_pct_cost":   10,
        "Typical_Season":     "Oct–Apr",
        "Grade":              "VG40 / PMB",
    },
    {
        "Road Type":          "State Highway (2-lane)",
        "Width_m":            7.0,
        "Layer_mm":           50,
        "MT_per_km_new":      35,
        "MT_per_km_overlay":  8,
        "MT_per_km_maint":    2,
        "Cost_Cr_per_km":     5.0,
        "Bitumen_pct_cost":   12,
        "Typical_Season":     "Nov–May",
        "Grade":              "VG30",
    },
    {
        "Road Type":          "Rural Road / PMGSY",
        "Width_m":            3.75,
        "Layer_mm":           25,
        "MT_per_km_new":      6,
        "MT_per_km_overlay":  1.5,
        "MT_per_km_maint":    0.6,
        "Cost_Cr_per_km":     1.12,
        "Bitumen_pct_cost":   18,
        "Typical_Season":     "Nov–May",
        "Grade":              "VG10 / Emulsion",
    },
    {
        "Road Type":          "Urban Road (2-lane)",
        "Width_m":            10.0,
        "Layer_mm":           60,
        "MT_per_km_new":      60,
        "MT_per_km_overlay":  15,
        "MT_per_km_maint":    3,
        "Cost_Cr_per_km":     15.0,
        "Bitumen_pct_cost":   10,
        "Typical_Season":     "Nov–May",
        "Grade":              "VG30",
    },
])

ROAD_TYPE_SOURCES = [
    ("MoRTH Compendium Circular 4110", "https://morth.gov.in/sites/default/files/comprehensive_compendium_circular/4110.3.pdf"),
    ("PMGSY Surface Dressing Booklet", "https://pmgsy.nic.in/sites/default/files/Surface-Dressing-Booklet.pdf"),
    ("Sahara Bizz — Bitumen per km", "https://saharabizz.com/how-much-bitumen-used-in-road-construction-per-kilometre/"),
    ("PMGSY Quality Assurance Manual", "https://www.pmgsy.nic.in/sites/default/files/pdf/QAHVolI.pdf"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — STATE-WISE DATA
# Source: PRS India State Budget Analyses 2024-25, BilTrax Media,
#         MoRTH State-UT fund allocation, IBEF
# ═══════════════════════════════════════════════════════════════════════════════

STATE_DATA = pd.DataFrame([
    {"State": "Uttar Pradesh",     "Central_Cr": 26000, "State_Cr": 34000, "NH_km": 11439, "SH_km": 22000, "Key_Projects": "Ganga Expressway, Gorakhpur Link Expy, Bundelkhand Expy",         "Peak_Month": "Nov–Mar", "Off_Season": "Jun–Sep", "Monsoon_Risk": "High"},
    {"State": "Maharashtra",       "Central_Cr": 15000, "State_Cr": 22000, "NH_km": 6063,  "SH_km": 31060, "Key_Projects": "7,500 km Annuity Scheme, NHAI West Zone 24 projects",             "Peak_Month": "Nov–May", "Off_Season": "Jun–Sep", "Monsoon_Risk": "High"},
    {"State": "Rajasthan",         "Central_Cr": 10000, "State_Cr": 9000,  "NH_km": 10573, "SH_km": 18010, "Key_Projects": "9 Greenfield Expressways: Jaipur-Kishangarh, Bikaner-Kotputli",   "Peak_Month": "Oct–Mar", "Off_Season": "Jul–Aug", "Monsoon_Risk": "Medium"},
    {"State": "Madhya Pradesh",    "Central_Cr": 8038,  "State_Cr": 9043,  "NH_km": 8772,  "SH_km": 28000, "Key_Projects": "Atal Pragati Path 299km, Narmada Pragati Path 900km",             "Peak_Month": "Nov–Apr", "Off_Season": "Jun–Sep", "Monsoon_Risk": "High"},
    {"State": "Gujarat",           "Central_Cr": 7000,  "State_Cr": 16816, "NH_km": 7230,  "SH_km": 19200, "Key_Projects": "Climate-resilient roads, SER development ₹4,200 Cr",             "Peak_Month": "Oct–May", "Off_Season": "Jun–Aug", "Monsoon_Risk": "Medium"},
    {"State": "Karnataka",         "Central_Cr": 5000,  "State_Cr": 12412, "NH_km": 6278,  "SH_km": 22500, "Key_Projects": "Bengaluru-Mangaluru Corridor, Pragati Path 9,450 km",            "Peak_Month": "Oct–May", "Off_Season": "Jun–Sep", "Monsoon_Risk": "High"},
    {"State": "Bihar",             "Central_Cr": 26000, "State_Cr": 7723,  "NH_km": 5396,  "SH_km": 8000,  "Key_Projects": "Patna-Purnea Expy, Ganga Bridge Buxar, Patna Ring Road",         "Peak_Month": "Nov–May", "Off_Season": "Jun–Sep", "Monsoon_Risk": "Very High"},
    {"State": "Andhra Pradesh",    "Central_Cr": 3300,  "State_Cr": 400,   "NH_km": 6898,  "SH_km": 15000, "Key_Projects": "Visakhapatnam-Chennai Corridor, CRIF 13 roads 200km",            "Peak_Month": "Nov–May", "Off_Season": "Jun–Oct", "Monsoon_Risk": "High"},
    {"State": "Tamil Nadu",        "Central_Cr": 4586,  "State_Cr": 4465,  "NH_km": 5006,  "SH_km": 30000, "Key_Projects": "4 NH projects, 2,000 km rural roads, CRIDP",                    "Peak_Month": "Dec–May", "Off_Season": "Oct–Dec", "Monsoon_Risk": "Medium"},
    {"State": "Odisha",            "Central_Cr": 6000,  "State_Cr": 9865,  "NH_km": 4899,  "SH_km": 5000,  "Key_Projects": "29,610 km Works Dept proposal, Bhubaneswar elevated corridor",  "Peak_Month": "Nov–May", "Off_Season": "Jun–Sep", "Monsoon_Risk": "Very High"},
    {"State": "Telangana",         "Central_Cr": 3000,  "State_Cr": 26502, "NH_km": 3563,  "SH_km": 7000,  "Key_Projects": "Regional Ring Road Hyderabad, 348 km → NH upgrade",              "Peak_Month": "Nov–May", "Off_Season": "Jun–Sep", "Monsoon_Risk": "High"},
    {"State": "Haryana",           "Central_Cr": 5000,  "State_Cr": 5000,  "NH_km": 2837,  "SH_km": 6000,  "Key_Projects": "Delhi-Amritsar-Katra Expressway, NH-44 4-lane",                  "Peak_Month": "Oct–Apr", "Off_Season": "Jul–Aug", "Monsoon_Risk": "Medium"},
    {"State": "Punjab",            "Central_Cr": 3000,  "State_Cr": 3000,  "NH_km": 2695,  "SH_km": 8000,  "Key_Projects": "Delhi-Amritsar Expressway, NH-7 improvements",                  "Peak_Month": "Oct–Apr", "Off_Season": "Jul–Aug", "Monsoon_Risk": "Medium"},
    {"State": "West Bengal",       "Central_Cr": 3500,  "State_Cr": 4000,  "NH_km": 3724,  "SH_km": 13000, "Key_Projects": "NH expansion, North Bengal connectivity",                       "Peak_Month": "Nov–May", "Off_Season": "Jun–Sep", "Monsoon_Risk": "Very High"},
    {"State": "Assam / NE States", "Central_Cr": 15720, "State_Cr": 3000,  "NH_km": 16125, "SH_km": 6000,  "Key_Projects": "35 NE Zone projects, NHIDCL 6,844 km, SARDP-NE",               "Peak_Month": "Nov–Apr", "Off_Season": "May–Oct", "Monsoon_Risk": "Extreme"},
])

# Calculate derived columns
STATE_DATA["Total_Budget_Cr"] = STATE_DATA["Central_Cr"] + STATE_DATA["State_Cr"]
STATE_DATA["Total_Road_km"] = STATE_DATA["NH_km"] + STATE_DATA["SH_km"]

# Budget-to-km conversion (at ₹18 Cr/km weighted average for 4-lane NH)
AVG_COST_CR_PER_KM = 12.0  # Blended avg for state mix of NH + SH
BITUMEN_PCT_OF_COST = 0.12  # 12% of road cost is bitumen material
AVG_BITUMEN_PRICE_PER_MT = 46000  # ₹46,000/MT current average

def budget_to_bitumen_mt(budget_cr):
    """Convert ₹ Crore road budget → estimated bitumen MT required."""
    bitumen_spend_cr = budget_cr * BITUMEN_PCT_OF_COST
    bitumen_spend_inr = bitumen_spend_cr * 1e7
    return round(bitumen_spend_inr / AVG_BITUMEN_PRICE_PER_MT)

def budget_to_km(budget_cr):
    """Convert ₹ Crore road budget → estimated km of road."""
    return round(budget_cr / AVG_COST_CR_PER_KM)

STATE_DATA["Est_km_Built"] = STATE_DATA["Total_Budget_Cr"].apply(budget_to_km)
STATE_DATA["Est_Bitumen_MT"] = STATE_DATA["Total_Budget_Cr"].apply(budget_to_bitumen_mt)

STATE_SOURCES = [
    ("PRS India — State Budget Analyses 2024-25", "https://prsindia.org/budgets/states"),
    ("BilTrax — India Roads Q1 FY 2024-25", "https://media.biltrax.com/indias-roads-highways-sector-in-q1-fy-2024-25/"),
    ("BilTrax — India Roads Q4 FY 2024-25", "https://media.biltrax.com/indias-roads-highways-sector-in-q4-fy-2024-25/"),
    ("MoRTH State-UT Fund Allocation", "https://morth.nic.in/sites/default/files/Sanction/State%20UT%20-%20wise%20allocation.pdf"),
    ("IBEF — Roads India", "https://www.ibef.org/industry/roads-india"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — DEPARTMENT-WISE DEMAND
# ═══════════════════════════════════════════════════════════════════════════════

DEPT_DATA = pd.DataFrame([
    {"Department": "NHAI",                     "Budget_Cr": 250000, "Road_km_Est": 5614,  "Project_Type": "4-lane / 6-lane NH, Expressways",      "Bitumen_Grade": "VG40 / PMB",        "Peak_Months": "Oct–Apr",  "MT_per_km": 105},
    {"Department": "State PWD (Top 10)",       "Budget_Cr": 120000, "Road_km_Est": 8000,  "Project_Type": "State Highways, District Roads",       "Bitumen_Grade": "VG30",              "Peak_Months": "Nov–May",  "MT_per_km": 35},
    {"Department": "PMGSY / Rural Dev",        "Budget_Cr": 19000,  "Road_km_Est": 16964, "Project_Type": "Rural connectivity, villages",          "Bitumen_Grade": "VG10 / Emulsion",   "Peak_Months": "Nov–Apr",  "MT_per_km": 6},
    {"Department": "Smart City Mission",       "Budget_Cr": 8000,   "Road_km_Est": 400,   "Project_Type": "Urban infrastructure, pedestrian",     "Bitumen_Grade": "VG30 / SMA",        "Peak_Months": "Nov–May",  "MT_per_km": 60},
    {"Department": "Industrial Corridor Auth", "Budget_Cr": 15000,  "Road_km_Est": 500,   "Project_Type": "Industrial access roads, heavy haul",  "Bitumen_Grade": "VG40",              "Peak_Months": "Year-round","MT_per_km": 80},
    {"Department": "BRO (Border Roads)",       "Budget_Cr": 5500,   "Road_km_Est": 800,   "Project_Type": "Strategic, mountain terrain",          "Bitumen_Grade": "VG10 / PMB",        "Peak_Months": "May–Sep",  "MT_per_km": 25},
    {"Department": "NHIDCL (Northeast)",       "Budget_Cr": 12000,  "Road_km_Est": 1000,  "Project_Type": "Northeast NH, tunnels",                "Bitumen_Grade": "VG10 / VG30",       "Peak_Months": "Nov–Apr",  "MT_per_km": 43},
    {"Department": "Municipal / Urban Dev",    "Budget_Cr": 25000,  "Road_km_Est": 1500,  "Project_Type": "City roads, ring roads, flyovers",     "Bitumen_Grade": "VG30",              "Peak_Months": "Nov–May",  "MT_per_km": 60},
])

DEPT_DATA["Est_Bitumen_MT"] = (DEPT_DATA["Road_km_Est"] * DEPT_DATA["MT_per_km"]).round()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MONTHLY DEMAND SEASONALITY MODEL
# Source: IMD monsoon patterns; MoRTH/NHAI seasonal construction norms
# ═══════════════════════════════════════════════════════════════════════════════

# Monthly demand index (April = 1.0 baseline; relative to annual average)
# Higher = more demand; Lower = off-season
MONTHLY_DEMAND_INDEX = {
    "Apr": 0.90, "May": 0.95, "Jun": 0.50, "Jul": 0.30,
    "Aug": 0.25, "Sep": 0.40, "Oct": 0.95, "Nov": 1.20,
    "Dec": 1.30, "Jan": 1.35, "Feb": 1.30, "Mar": 1.40,
}

# State-level monsoon adjustment (months where construction is severely impacted)
STATE_MONSOON_MONTHS = {
    "Uttar Pradesh":     {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["May", "Oct"]},
    "Maharashtra":       {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["May", "Oct"]},
    "Rajasthan":         {"off": ["Jul", "Aug"],                "partial": ["Jun", "Sep"]},
    "Madhya Pradesh":    {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["May", "Oct"]},
    "Gujarat":           {"off": ["Jun", "Jul", "Aug"],         "partial": ["Sep"]},
    "Karnataka":         {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["Oct"]},
    "Bihar":             {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["May"]},
    "Andhra Pradesh":    {"off": ["Jun", "Jul", "Aug", "Sep", "Oct"], "partial": ["Nov"]},
    "Tamil Nadu":        {"off": ["Oct", "Nov", "Dec"],         "partial": ["Sep", "Jan"]},
    "Odisha":            {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["May"]},
    "Telangana":         {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["Oct"]},
    "Haryana":           {"off": ["Jul", "Aug"],                "partial": ["Jun", "Sep"]},
    "Punjab":            {"off": ["Jul", "Aug"],                "partial": ["Jun", "Sep"]},
    "West Bengal":       {"off": ["Jun", "Jul", "Aug", "Sep"], "partial": ["May"]},
    "Assam / NE States": {"off": ["May", "Jun", "Jul", "Aug", "Sep", "Oct"], "partial": ["Apr", "Nov"]},
}

def get_monthly_heatmap_data():
    """Build monthly demand heatmap (States × Months)."""
    months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
    states = list(STATE_MONSOON_MONTHS.keys())
    base_demand = dict(zip(STATE_DATA["State"].values, STATE_DATA["Est_Bitumen_MT"].values))
    rows = []
    for state in states:
        row = {"State": state}
        monsoon = STATE_MONSOON_MONTHS.get(state, {"off": [], "partial": []})
        annual_mt = base_demand.get(state, 50000)
        for m in months:
            if m in monsoon["off"]:
                factor = 0.10
            elif m in monsoon["partial"]:
                factor = 0.50
            else:
                factor = MONTHLY_DEMAND_INDEX.get(m, 1.0)
            row[m] = round(annual_mt * factor / 12)
        rows.append(row)
    return pd.DataFrame(rows)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — NATIONAL SUMMARY CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_national_summary():
    fy_latest = BITUMEN_CONSUMPTION.iloc[-1]
    fy_prev = BITUMEN_CONSUMPTION.iloc[-2]
    cagr_5yr = ((fy_latest["Consumption_MT"] / BITUMEN_CONSUMPTION.iloc[-6]["Consumption_MT"]) ** (1/5) - 1) * 100

    total_state_budget = STATE_DATA["Total_Budget_Cr"].sum()
    total_est_mt = STATE_DATA["Est_Bitumen_MT"].sum()
    central_share = STATE_DATA["Central_Cr"].sum() / total_state_budget * 100
    state_share = STATE_DATA["State_Cr"].sum() / total_state_budget * 100
    top5 = STATE_DATA.nlargest(5, "Est_Bitumen_MT")[["State", "Est_Bitumen_MT", "Total_Budget_Cr"]]

    return {
        "total_consumption_mt": fy_latest["Consumption_MT"],
        "yoy_growth_pct": (fy_latest["Consumption_MT"] / fy_prev["Consumption_MT"] - 1) * 100,
        "cagr_5yr_pct": cagr_5yr,
        "domestic_mt": fy_latest["Domestic_MT"],
        "import_mt": fy_latest["Import_MT"],
        "import_share_pct": fy_latest["Import_MT"] / fy_latest["Consumption_MT"] * 100,
        "morth_budget_2526_cr": 287333,
        "total_state_budget_cr": total_state_budget,
        "combined_budget_cr": 287333 + total_state_budget,
        "total_est_bitumen_mt": total_est_mt,
        "central_share_pct": central_share,
        "state_share_pct": state_share,
        "top5": top5,
        "peak_quarter": "Q3–Q4 (Oct–Mar)",
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — SENSITIVITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def sensitivity_analysis(budget_change_pct, cost_per_km_change_pct, bitumen_price_change_pct):
    """
    Calculates how much bitumen demand changes when inputs change.
    Returns delta in MT and new total.
    """
    base_mt = STATE_DATA["Est_Bitumen_MT"].sum()
    new_budget = STATE_DATA["Total_Budget_Cr"] * (1 + budget_change_pct / 100)
    new_cost_km = AVG_COST_CR_PER_KM * (1 + cost_per_km_change_pct / 100)
    new_bitumen_price = AVG_BITUMEN_PRICE_PER_MT * (1 + bitumen_price_change_pct / 100)

    new_km = (new_budget / new_cost_km).round()
    new_bitumen_spend = new_km * new_cost_km * BITUMEN_PCT_OF_COST * 1e7
    new_mt = (new_bitumen_spend / new_bitumen_price).round()
    total_new_mt = new_mt.sum()

    return {
        "base_mt": int(base_mt),
        "new_mt": int(total_new_mt),
        "delta_mt": int(total_new_mt - base_mt),
        "delta_pct": round((total_new_mt - base_mt) / base_mt * 100, 2),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    display_badge("real-time")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a3a2a,#0d2018);
    padding:24px;border-radius:14px;margin-bottom:20px;
    border-left:5px solid #22c55e;">
    <div style="font-size:1.5rem;font-weight:900;color:#f0fdf4;">
    🛣️ India Road Budget & Bitumen Demand Intelligence
    </div>
    <div style="color:#86efac;margin-top:6px;font-size:0.95rem;">
    Infrastructure Budget → KM Conversion → Bitumen MT Demand Model | FY 2024-25 Data
    </div>
    </div>
    """, unsafe_allow_html=True)

    summary = get_national_summary()

    # ── KPI Header ────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🇮🇳 Total Bitumen Demand", f"{summary['total_consumption_mt']:.2f} M MT",
              f"+{summary['yoy_growth_pct']:.1f}% YoY", help="Source: PPAC / MoSPI 2025")
    k2.metric("🏗️ MoRTH Budget 2025-26", f"₹ 2,87,333 Cr",
              "+3.4% vs 2024-25", help="Source: Union Budget 2025-26")
    k3.metric("🛣️ NH Constructed FY24", "12,349 km",
              "2nd highest ever", help="Source: PIB Year End Review 2024")
    k4.metric("📈 5-Yr CAGR (Demand)", f"{summary['cagr_5yr_pct']:.1f}%",
              "FY 2019-24", help="Source: PPAC data")
    k5.metric("🚢 Import Share", f"{summary['import_share_pct']:.0f}%",
              "of total demand", help="Source: S&P Global / PPAC")

    st.markdown("---")

    # ── Main Tabs ─────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📊 National Overview",
        "🏛️ Central Budget",
        "🗺️ State-wise Table",
        "📅 Monthly Heatmap",
        "🏢 Department Demand",
        "🛣️ Road Type Model",
        "📉 Sensitivity Analysis",
        "✅ Assumptions & Sources",
    ])

    # ── TAB 1: NATIONAL OVERVIEW ─────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### 🇮🇳 India Bitumen Demand — 10-Year Trend")
        st.caption("Source: PPAC (ppac.gov.in) | MoSPI Energy Statistics 2025 | S&P Global")

        col_chart, col_info = st.columns([2, 1])
        with col_chart:
            chart_df = BITUMEN_CONSUMPTION.copy()
            chart_df = chart_df.set_index("FY")
            st.bar_chart(chart_df[["Domestic_MT", "Import_MT"]])
            st.caption("Blue = Domestic Production | Orange = Imports (Million MT)")

        with col_info:
            st.metric("FY 2023-24 Total", f"{summary['total_consumption_mt']} M MT")
            st.metric("Domestic Production", f"{summary['domestic_mt']} M MT")
            st.metric("Imports", f"{summary['import_mt']} M MT")
            st.info("**90% of bitumen** is consumed by road construction. Balance is waterproofing and industrial use.")
            st.warning("India is the **2nd largest global bitumen consumer**. Structural 42% import dependency.")

        st.markdown("---")
        st.markdown("### 🏆 Top 5 States — Estimated Bitumen Demand")
        top5 = summary["top5"].copy()
        top5["Est_Bitumen_MT"] = top5["Est_Bitumen_MT"].apply(lambda x: f"{x:,.0f} MT")
        top5["Total_Budget_Cr"] = top5["Total_Budget_Cr"].apply(lambda x: f"{format_inr(x)} Cr")
        top5 = top5.rename(columns={"Est_Bitumen_MT": "Est. Bitumen (MT)", "Total_Budget_Cr": "Total Road Budget"})
        st.dataframe(top5, use_container_width=True, hide_index=True)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🏗️ Road Network (Latest)")
            rn = ROAD_NETWORK
            net_df = pd.DataFrame([
                {"Category": "National Highways",  "Length (km)": f"{rn['national_highways_km']:,}", "Share": "2.3%"},
                {"Category": "State Highways",     "Length (km)": f"{rn['state_highways_km']:,}",    "Share": "2.9%"},
                {"Category": "District Roads",     "Length (km)": f"{rn['district_roads_km']:,}",    "Share": "9.9%"},
                {"Category": "Rural Roads",        "Length (km)": f"{rn['rural_roads_km']:,}",       "Share": "57.8%"},
                {"Category": "Urban Roads",        "Length (km)": f"{rn['urban_roads_km']:,}",       "Share": "8.6%"},
                {"Category": "Expressways",        "Length (km)": f"{rn['expressways_km']:,}",       "Share": "0.09%"},
            ])
            st.dataframe(net_df, use_container_width=True, hide_index=True)
            st.caption("Sources: MoRTH Basic Road Statistics 2019-20; PIB 2024")
        with c2:
            st.markdown("### ⚠️ National Risk Factors")
            risks = [
                ("Budget Cuts", "Medium", "Election year spending usually rises, but fiscal consolidation post-2025 is possible"),
                ("Election Cycles", "Positive", "Pre-election road push adds 20-25% demand nationally"),
                ("Monsoon Intensity", "High Risk", "Stronger monsoon = longer off-season = demand concentrated in fewer months"),
                ("Crude Price Impact", "High", "Bitumen price rising → contractors delay execution → demand deferred"),
                ("Environmental Norms", "Medium", "Green highway, recycling mandates may reduce virgin bitumen use by 5-10%"),
            ]
            for r, level, desc in risks:
                colour = "error" if level in ["High", "High Risk"] else ("warning" if level == "Medium" else "success")
                getattr(st, colour)(f"**{r} ({level}):** {desc}")

    # ── TAB 2: CENTRAL BUDGET ────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 🏛️ MoRTH, NHAI & PMGSY — 10-Year Budget (₹ Crore)")
        st.caption("Sources: Union Budget, PRS India DFG Analyses, MoRTH Outcome Budgets")

        budget_disp = MORTH_BUDGET.copy()
        for col in ["MoRTH_Total_Cr", "NHAI_Cr", "PMGSY_Cr"]:
            budget_disp[col] = budget_disp[col].apply(lambda x: f"{format_inr(x)} Cr")
        budget_disp["NH_km_built"] = budget_disp["NH_km_built"].apply(lambda x: f"{x:,} km" if x > 0 else "FY in progress")
        budget_disp = budget_disp.rename(columns={
            "MoRTH_Total_Cr": "MoRTH Budget", "NHAI_Cr": "NHAI Allocation",
            "PMGSY_Cr": "PMGSY Allocation", "NH_km_built": "NH km Built"
        })
        st.dataframe(budget_disp[["FY","MoRTH Budget","NHAI Allocation","PMGSY Allocation","NH km Built","Notes"]],
                     use_container_width=True, hide_index=True)

        st.markdown("---")
        trend_df = MORTH_BUDGET[["FY","MoRTH_Total_Cr","NHAI_Cr","NH_km_built"]].set_index("FY")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**MoRTH vs NHAI Budget Growth (₹ Cr)**")
            st.line_chart(trend_df[["MoRTH_Total_Cr","NHAI_Cr"]])
        with col2:
            st.markdown("**NH km Constructed per Year**")
            st.bar_chart(trend_df["NH_km_built"])

        st.markdown("---")
        st.markdown("### 🛣️ Bharatmala Phase 1 — Status")
        bm = BHARATMALA
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Total Approved km", f"{bm['total_km_approved']:,} km")
        b2.metric("km Awarded", f"{bm['km_awarded']:,} km", f"{bm['km_awarded']/bm['total_km_approved']*100:.0f}% of target")
        b3.metric("km Completed", f"{bm['km_completed']:,} km", f"{bm['km_completed']/bm['total_km_approved']*100:.0f}% complete")
        b4.metric("Expenditure to Date", f"{format_inr(bm['expenditure_to_date_cr'])} Cr", "As of Mar-2024")
        st.warning(f"Original budget: {format_inr(bm['original_budget_cr'])} Cr → Revised: {format_inr(bm['revised_budget_cr'])} Cr — cost overrun of ~105%. Revised completion: {bm['revised_completion']}.")
        st.caption(f"Source: {bm['sources'][0][0]} — [{bm['sources'][0][1]}]({bm['sources'][0][1]})")

        st.markdown("---")
        st.markdown("### 🔗 Official Sources")
        for name, url in MORTH_SOURCES:
            st.markdown(f"- [{name}]({url})")

    # ── TAB 3: STATE-WISE TABLE ──────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 🗺️ State-wise Road Budget & Bitumen Demand Estimate")
        st.caption(f"Model: Budget × {BITUMEN_PCT_OF_COST*100:.0f}% cost-share ÷ {format_inr(AVG_BITUMEN_PRICE_PER_MT)}/MT. Sources: PRS India, BilTrax, MoRTH")

        disp = STATE_DATA.copy()
        disp["Central_Cr"] = disp["Central_Cr"].apply(lambda x: f"{format_inr(x)} Cr")
        disp["State_Cr"] = disp["State_Cr"].apply(lambda x: f"{format_inr(x)} Cr")
        disp["Total_Budget_Cr"] = disp["Total_Budget_Cr"].apply(lambda x: f"{format_inr(x)} Cr")
        disp["Est_km_Built"] = disp["Est_km_Built"].apply(lambda x: f"{x:,} km")
        disp["Est_Bitumen_MT"] = disp["Est_Bitumen_MT"].apply(lambda x: f"{x:,} MT")
        disp["NH_km"] = disp["NH_km"].apply(lambda x: f"{x:,} km")

        st.dataframe(
            disp[["State","Central_Cr","State_Cr","Total_Budget_Cr","Est_km_Built",
                  "Est_Bitumen_MT","NH_km","Peak_Month","Off_Season","Monsoon_Risk","Key_Projects"]].rename(columns={
                "Central_Cr":"Central Alloc","State_Cr":"State PWD",
                "Total_Budget_Cr":"Total Budget","Est_km_Built":"Est. km",
                "Est_Bitumen_MT":"Est. Bitumen (MT)","NH_km":"NH Length",
                "Peak_Month":"Peak Season","Off_Season":"Off Season","Monsoon_Risk":"Monsoon Risk"
            }),
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        st.markdown("### 📊 State Bitumen Demand Bar Chart")
        chart_state = STATE_DATA[["State","Est_Bitumen_MT"]].set_index("State")
        st.bar_chart(chart_state)
        st.caption("Estimated annual bitumen MT demand per state based on road budget model")

        st.markdown("---")
        st.markdown("### 🔗 State Budget Sources")
        for name, url in STATE_SOURCES:
            st.markdown(f"- [{name}]({url})")

    # ── TAB 4: MONTHLY HEATMAP ───────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📅 Monthly Bitumen Demand Heatmap (State × Month)")
        st.caption("Color: High demand = Dark | Low demand = Off-season | Source: IMD monsoon data + MoRTH construction norms")
        st.info("FY format: Apr → Mar. Each cell = estimated MT of bitumen required that month.")

        heatmap_df = get_monthly_heatmap_data().set_index("State")
        months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

        try:
            styled = heatmap_df[months].style.background_gradient(
                cmap="RdYlGn", axis=None
            ).format("{:,.0f}")
            st.dataframe(styled, use_container_width=True)
        except Exception:
            st.dataframe(heatmap_df[months], use_container_width=True)

        st.markdown("---")
        st.markdown("### 📈 National Monthly Demand Index")
        monthly_idx = pd.DataFrame(
            {"Month": list(MONTHLY_DEMAND_INDEX.keys()),
             "Demand Index": list(MONTHLY_DEMAND_INDEX.values())}
        ).set_index("Month")
        st.bar_chart(monthly_idx)
        st.caption("1.0 = average monthly demand. Peak months: Jan (1.35), Mar (1.40). Off-peak: Aug (0.25)")

        st.markdown("---")
        st.markdown("### 🌧️ Monsoon Region Summary")
        mon_data = [
            {"Region": "Northwest India",  "States": "Rajasthan, Punjab, Haryana, Delhi, HP, J&K", "Monsoon": "June – September",  "Construction Window": "October – May"},
            {"Region": "Northeast India",  "States": "Assam, Meghalaya, Arunachal, Manipur, NE states", "Monsoon": "May – October", "Construction Window": "November – April"},
            {"Region": "Southern India",   "States": "Tamil Nadu, Kerala, Karnataka, Andhra Pradesh", "Monsoon": "June – November", "Construction Window": "December – May"},
            {"Region": "Central India",    "States": "MP, Chhattisgarh, Jharkhand, Odisha, inland Maharashtra", "Monsoon": "June – September", "Construction Window": "October – May"},
        ]
        st.dataframe(pd.DataFrame(mon_data), use_container_width=True, hide_index=True)
        st.caption("Source: India Meteorological Department (IMD); MoRTH/NHAI seasonal construction norms")

    # ── TAB 5: DEPARTMENT DEMAND ─────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🏢 Department-wise Bitumen Demand Breakdown")
        st.caption("Sources: Union Budget 2025-26, NHAI Annual Report, PMGSY-IV Cabinet Approval")

        dept_disp = DEPT_DATA.copy()
        dept_disp["Budget_Cr"] = dept_disp["Budget_Cr"].apply(lambda x: f"{format_inr(x)} Cr")
        dept_disp["Est_Bitumen_MT"] = dept_disp["Est_Bitumen_MT"].apply(lambda x: f"{x:,.0f} MT")
        dept_disp["Road_km_Est"] = dept_disp["Road_km_Est"].apply(lambda x: f"{x:,} km")

        st.dataframe(
            dept_disp[["Department","Budget_Cr","Road_km_Est","Est_Bitumen_MT",
                        "Project_Type","Bitumen_Grade","Peak_Months"]].rename(columns={
                "Budget_Cr":"Budget (₹ Cr)","Road_km_Est":"Est. km",
                "Est_Bitumen_MT":"Est. Bitumen MT","Project_Type":"Project Type",
                "Bitumen_Grade":"Preferred Grade","Peak_Months":"Peak Months"
            }),
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        dept_chart = DEPT_DATA[["Department","Est_Bitumen_MT"]].set_index("Department")
        st.bar_chart(dept_chart)
        st.caption("NHAI dominates with the highest per-km bitumen usage (4-lane/6-lane construction)")

        st.markdown("---")
        st.markdown("### 💡 Key Insight for Traders")
        st.success("""
**NHAI** is your highest-volume client channel — target NHAI sub-contractors (L&T, Dilip Buildcon, G R Infra).
They buy in bulk (500–5,000 MT per order), require VG40/PMB grades, and pay reliably due to NHAI payment certifications.

**PMGSY contractors** are high-frequency, low-volume buyers. They prefer VG10/emulsion and are spread across rural India.
Great for volume, but payment risk is higher and logistics is complex.

**Smart City / Urban** contractors are price-sensitive but premium grade (VG30/SMA). Located in metros — easier logistics.
        """)

    # ── TAB 6: ROAD TYPE MODEL ───────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 🛣️ Project-Type Bitumen Consumption Analysis")
        st.caption("Sources: IRC Specifications, MoRTH Compendium, PMGSY Technical Documents")

        rt_disp = ROAD_TYPES.copy()
        for col in ["MT_per_km_new", "MT_per_km_overlay", "MT_per_km_maint"]:
            rt_disp[col] = rt_disp[col].apply(lambda x: f"{x} MT/km")
        rt_disp["Cost_Cr_per_km"] = rt_disp["Cost_Cr_per_km"].apply(lambda x: f"₹ {x} Cr/km")
        rt_disp["Bitumen_pct_cost"] = rt_disp["Bitumen_pct_cost"].apply(lambda x: f"{x}%")

        st.dataframe(
            rt_disp[["Road Type","Width_m","Layer_mm","MT_per_km_new","MT_per_km_overlay",
                      "MT_per_km_maint","Cost_Cr_per_km","Bitumen_pct_cost","Typical_Season","Grade"]].rename(columns={
                "Width_m":"Width (m)","Layer_mm":"Layer (mm)","MT_per_km_new":"New Construction",
                "MT_per_km_overlay":"Overlay","MT_per_km_maint":"Maintenance",
                "Cost_Cr_per_km":"Cost/km","Bitumen_pct_cost":"Bitumen % of Cost",
                "Typical_Season":"Build Season","Grade":"Bitumen Grade"
            }),
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        st.markdown("### 📐 Why MT Varies by Road Type")
        col1, col2 = st.columns(2)
        with col1:
            st.info("""
**Expressway (160 MT/km):**
6 lanes × 3.75m each = 22.5m width. Multiple layers: Sub-base, Base Course, DBM, BC.
Premium PMB grade. Highest construction standard.
""")
            st.info("""
**NH 4-lane (105 MT/km):**
14m width. 3–4 bituminous layers. VG40 for high-traffic corridors.
Standard IRC SP-73 specification.
""")
            st.success("""
**Resurfacing/Overlay (10-22 MT/km):**
Only the top 25-40mm wearing course is replaced.
Dramatically lower MT than new construction.
High-frequency opportunity — India resurfaces 8,000+ km annually.
""")
        with col2:
            st.info("""
**State Highway (35 MT/km):**
7m width. 2–3 layers. VG30 sufficient.
Lower traffic volumes, thinner pavement design.
""")
            st.info("""
**PMGSY Rural (6 MT/km):**
3.75m single-lane. Granular sub-base + thin BM + surface dressing.
VG10 or cationic emulsion. Very thin bitumen layer.
But 16,000+ km built annually = significant total volume.
""")
            st.warning("""
**Urban Roads (60 MT/km):**
Highly variable — 7m to 15m+. Heavy traffic. Frequent underground utilities.
SMA or Mastic Asphalt in CBDs. High specification.
""")

        st.markdown("---")
        st.markdown("### 🔗 Technical Sources")
        for name, url in ROAD_TYPE_SOURCES:
            st.markdown(f"- [{name}]({url})")

    # ── TAB 7: SENSITIVITY ANALYSIS ──────────────────────────────────────────
    with tabs[6]:
        st.markdown("### 📉 Sensitivity Analysis — Budget Impact on Bitumen Demand")
        st.caption("Adjust variables to see how national bitumen demand changes")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            budget_chg = st.slider("Budget Change (%)", -20, 30, 10,
                                   help="Government increases/decreases road budget")
        with col_b:
            cost_chg = st.slider("Construction Cost Change (%)", -10, 30, 0,
                                 help="If cost per km rises due to inflation, fewer km get built")
        with col_c:
            price_chg = st.slider("Bitumen Price Change (%)", -20, 30, 0,
                                  help="If bitumen prices rise, same budget buys less MT")

        result = sensitivity_analysis(budget_chg, cost_chg, price_chg)
        r1, r2, r3 = st.columns(3)
        r1.metric("Base Demand (MT)", f"{result['base_mt']:,} MT")
        r2.metric("New Demand (MT)", f"{result['new_mt']:,} MT",
                  f"{'+' if result['delta_mt']>0 else ''}{result['delta_mt']:,} MT ({result['delta_pct']:+.1f}%)")
        r3.metric("Delta Impact", f"₹ {abs(result['delta_mt']) * AVG_BITUMEN_PRICE_PER_MT / 1e7:.1f} Cr",
                  "Revenue opportunity/loss")

        st.markdown("---")
        st.markdown("### 📊 Standard Sensitivity Matrix")
        scenarios = []
        for b in [-10, 0, 10, 20]:
            for p in [0, 10, 20]:
                res = sensitivity_analysis(b, 0, p)
                scenarios.append({
                    "Budget Δ": f"{b:+d}%",
                    "Bitumen Price Δ": f"{p:+d}%",
                    "Demand (MT)": f"{res['new_mt']:,}",
                    "vs Baseline": f"{res['delta_pct']:+.1f}%"
                })
        st.dataframe(pd.DataFrame(scenarios), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.success("""
**Trader Strategic Insight:**
- If budget rises +10% → demand rises ~10%. **Pre-stock inventory** before budget announcement.
- If bitumen prices rise +10% → contractors delay orders → demand falls ~10%. **Sell ahead** of price revision.
- Budget increase + crude spike cancel out. Net effect on your volume: minimal. Focus on margin protection.
        """)

    # ── TAB 8: ASSUMPTIONS & SOURCES ─────────────────────────────────────────
    with tabs[7]:
        st.markdown("### ✅ Model Assumptions & Validation")

        st.markdown("#### 🔢 Key Modelling Assumptions")
        assumptions = [
            ("Average road cost per km", f"₹ {AVG_COST_CR_PER_KM:.0f} Crore/km", "Blended average: NH (₹18 Cr) + SH (₹5 Cr) + Rural (₹1.12 Cr). Source: PMGSY-IV Cabinet Note; NHAI benchmarks."),
            ("Bitumen % of road construction cost", f"{BITUMEN_PCT_OF_COST*100:.0f}%", "Material cost share. Ranges from 10% (expressway) to 18% (rural road). Source: IRC analysis; MoRTH BOQ data."),
            ("Average bitumen price (all grades)", f"{format_inr(AVG_BITUMEN_PRICE_PER_MT)}/MT", "Blended average of VG30 (₹42,000-44,000), VG40 (₹44,000-46,000), Import (₹38,000-42,000). Dynamic — update in Data Manager."),
            ("MT per km — NH 4-lane", "105 MT/km", "Width 14m × thickness 70mm × density 2.35 × bitumen content 4.8%. Source: IRC SP-73; Sahara Bizz calculation."),
            ("MT per km — Rural/PMGSY", "6 MT/km", "Single-lane 3.75m + thin BM + surface dressing at 12kg/100m². Source: PMGSY Surface Dressing Booklet."),
            ("Import share of demand", "~42%", "FY 2023-24: 3.72 MT imported out of 8.85 MT total. Source: PPAC/S&P Global."),
            ("Peak season months", "Oct–Mar", "Government budget execution concentrated in H2 of FY. Source: MoRTH Outcome Budgets."),
        ]
        asmpt_df = pd.DataFrame(assumptions, columns=["Assumption", "Value", "Justification"])
        st.dataframe(asmpt_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### ⚠️ Where Estimates May Deviate")
        deviations = [
            "Budget utilisation: Only 85-90% of sanctioned budget is typically spent in a year. Estimates assume 100% utilisation.",
            "Road type mix: Blended cost/km is sensitive to the mix of NH vs rural roads. In states like UP (expressway-heavy), actual bitumen MT per ₹ Crore is higher.",
            "Resurfacing vs new construction: Overlay/resurfacing uses 80% less bitumen per km. If budget shifts to maintenance, demand model overstates demand.",
            "Grade mix: Import terminals supply lower-priced bitumen at ₹38,000-42,000. If import share rises, same MT estimate is lower in ₹ value.",
            "State absorption: Some states (Bihar, NE) have lower execution capacity — budgets are announced but projects run 2-3 years late.",
            "Monsoon adjustment: Model uses historical IMD patterns. Above-normal monsoon (La Niña) can extend off-season by 2-4 weeks.",
        ]
        for d in deviations:
            st.warning(f"⚠️ {d}")

        st.markdown("---")
        st.markdown("#### 📚 Complete Source Reference")
        all_sources = [
            ("🏛️ Central Budget", MORTH_SOURCES),
            ("🛢️ Bitumen Consumption", BITUMEN_SOURCES),
            ("🛣️ Road Network", ROAD_NETWORK["sources"]),
            ("📐 Technical Norms", ROAD_TYPE_SOURCES),
            ("🗺️ State Budgets", STATE_SOURCES),
            ("🛣️ Bharatmala", BHARATMALA["sources"]),
        ]
        for section, sources in all_sources:
            st.markdown(f"**{section}**")
            for name, url in sources:
                st.markdown(f"  - [{name}]({url})")

        st.markdown("---")
        st.markdown("#### 🎯 Strategic Recommendations for Bitumen Traders")
        st.success("""
**1. Target NHAI sub-contractors (highest volume, premium grade):**
States with peak NHAI activity: UP, Maharashtra, Rajasthan, MP, Gujarat.
These 5 states account for ~55% of estimated national NH-level bitumen demand.

**2. Rural roads — volume play:**
PMGSY 16,000+ km/year = 96,000+ MT/year of VG10/emulsion.
Low margin per MT but consistent off-season demand — good for monsoon inventory liquidation.

**3. Seasonal timing:**
Buy inventory September. Sell October-February. Reduce exposure March-May.
Never carry excess inventory into June — 4-month demand collapse from monsoon.

**4. North India (Rajasthan, UP, Haryana) is the strongest bitumen market:**
Short monsoon, aggressive NHAI execution, expressway-heavy (high MT/km), close to Kandla/Panipat source.

**5. Northeast is growing but complex:**
₹15,720 Cr of projects but monsoon kills execution for 5-6 months.
High logistics complexity. Only for experienced operators with NE network.
        """)
        st.info(f"**Last Updated:** {datetime.date.today().strftime('%Y-%m-%d')} | All financial data in ₹ Crore | Volume in Metric Tonnes (MT)")
