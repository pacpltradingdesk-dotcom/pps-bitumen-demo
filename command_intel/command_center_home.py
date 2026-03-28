"""
PPS Anantam — Command Center v3.0
==================================
Clean, modern dashboard with sidebar navigation, hero cards,
and organized feature categories.
"""

import streamlit as st
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _load_json(filename, default=None):
    try:
        p = ROOT / filename
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def _fmt(amount):
    try:
        amount = int(amount)
        s = str(abs(amount))
        if len(s) > 3:
            last3 = s[-3:]
            rest = s[:-3]
            parts = []
            while rest:
                parts.append(rest[-2:])
                rest = rest[:-2]
            parts.reverse()
            formatted = ",".join(parts) + "," + last3
        else:
            formatted = s
        return f"\u20b9{formatted}"
    except Exception:
        return str(amount)


def _go(page):
    st.session_state["_nav_goto"] = page
    st.session_state["_from_cc"] = True


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════

CATEGORIES = [
    {
        "id": "dashboard",
        "icon": "📋",
        "name": "Dashboard",
        "color": "#1e3a5f",
        "desc": "Business snapshot, KPIs, and daily briefings",
        "features": [
            {"icon": "🏠", "name": "Live Market", "page": "🏠 Home",
             "desc": "Market pulse, KPIs, predicted prices, top opportunities"},
            {"icon": "📋", "name": "Director Briefing", "page": "📋 Director Briefing",
             "desc": "Auto-generated daily executive summary with action items"},
            {"icon": "📅", "name": "Sales Calendar", "page": "📅 Sales Calendar",
             "desc": "Peak/off seasons, state holidays, demand planning"},
            {"icon": "📓", "name": "Daily Log", "page": "📓 Daily Log",
             "desc": "Activity tracking and daily work log"},
            {"icon": "🔍", "name": "Opportunities", "page": "🔍 Opportunities",
             "desc": "Auto-discovered profitable deals and arbitrage"},
        ],
    },
    {
        "id": "pricing",
        "icon": "💰",
        "name": "Pricing",
        "color": "#2d6a4f",
        "desc": "Calculate buy/sell prices for any route",
        "features": [
            {"icon": "🧮", "name": "Pricing Calculator", "page": "🧮 Pricing Calculator",
             "desc": "Landed cost from any source to any city with 3-tier offers", "star": True},
            {"icon": "📦", "name": "Import Cost Model", "page": "📦 Import Cost Model",
             "desc": "FOB to CIF to landed cost for international imports"},
            {"icon": "🏭", "name": "Feasibility Check", "page": "🏭 Feasibility",
             "desc": "Compare Refinery vs Import vs Decanter"},
            {"icon": "🔮", "name": "Price Prediction", "page": "🔮 Price Prediction",
             "desc": "AI-powered 24-month price forecast"},
            {"icon": "📝", "name": "Manual Price Entry", "page": "📝 Manual Price Entry",
             "desc": "Override prices for field quotes"},
            {"icon": "🚨", "name": "SOS Special Pricing", "page": "🚨 SPECIAL PRICE (SOS)",
             "desc": "Emergency pricing for urgent orders"},
        ],
    },
    {
        "id": "sales",
        "icon": "🧾",
        "name": "Sales & CRM",
        "color": "#c9a84c",
        "desc": "Manage customers, close deals, track follow-ups",
        "features": [
            {"icon": "🎯", "name": "CRM & Tasks", "page": "🎯 CRM & Tasks",
             "desc": "Customer database, tasks, VIP scoring, follow-up reminders", "star": True},
            {"icon": "💼", "name": "Sales Workspace", "page": "💼 Sales Workspace",
             "desc": "Deal room — structure deals, calculate margins"},
            {"icon": "🤝", "name": "Negotiation Assistant", "page": "🤝 Negotiation Assistant",
             "desc": "Pre-call briefing and objection handling"},
            {"icon": "💬", "name": "Communication Hub", "page": "💬 Communication Hub",
             "desc": "Auto-generated WhatsApp, Email and Call scripts"},
            {"icon": "🤖", "name": "CRM Automation", "page": "🤖 CRM Automation",
             "desc": "Auto-assign leads, schedule follow-ups"},
            {"icon": "📧", "name": "Email Setup", "page": "📧 Email Setup",
             "desc": "Configure SMTP, templates, auto-send rules"},
            {"icon": "📱", "name": "WhatsApp Setup", "page": "📱 WhatsApp Setup",
             "desc": "360dialog API, templates, campaigns"},
            {"icon": "📥", "name": "Contact Importer", "page": "📥 Contact Importer",
             "desc": "Bulk import contacts from Excel/CSV/PDF"},
        ],
    },
    {
        "id": "intelligence",
        "icon": "🧠",
        "name": "Intelligence",
        "color": "#7c3aed",
        "desc": "AI-powered market analysis and recommendations",
        "features": [
            {"icon": "📡", "name": "Market Signals", "page": "📡 Market Signals",
             "desc": "10-signal composite: crude, FX, weather, tenders, news", "star": True},
            {"icon": "💡", "name": "Recommendations", "page": "💡 Recommendations",
             "desc": "Buy/Sell/Hold signals with confidence %"},
            {"icon": "🛒", "name": "Purchase Advisor", "page": "🛒 Purchase Advisor",
             "desc": "6-signal urgency index for buy decisions"},
            {"icon": "🔴", "name": "Real-time Insights", "page": "🔴 Real-time Insights",
             "desc": "Live market data and instant analysis"},
            {"icon": "📰", "name": "News Intelligence", "page": "📰 News Intelligence",
             "desc": "14-source news aggregation with sentiment"},
            {"icon": "🕵️", "name": "Competitor Intel", "page": "🕵️ Competitor Intelligence",
             "desc": "IOCL/HPCL price tracking, benchmarks"},
            {"icon": "🌐", "name": "Global Markets", "page": "🌐 Global Markets",
             "desc": "Brent, WTI, crude oil charts and trends"},
            {"icon": "🧑\u200d💼", "name": "Business Advisor", "page": "🧑\u200d💼 Business Advisor",
             "desc": "Strategic guidance on inventory and risk"},
        ],
    },
    {
        "id": "documents",
        "icon": "📄",
        "name": "Documents",
        "color": "#0369a1",
        "desc": "Create POs, SOs, payments, manage parties",
        "features": [
            {"icon": "📋", "name": "Purchase Orders", "page": "📋 Purchase Orders",
             "desc": "Create and track purchase orders with PDF export"},
            {"icon": "📋", "name": "Sales Orders", "page": "📋 Sales Orders",
             "desc": "Create and track sales orders with line items"},
            {"icon": "💳", "name": "Payment Orders", "page": "💳 Payment Orders",
             "desc": "Payment tracking, aging analysis, reconciliation"},
            {"icon": "👥", "name": "Party Master", "page": "👥 Party Master",
             "desc": "Supplier/Customer/Transporter master data"},
            {"icon": "📁", "name": "PDF Archive", "page": "📁 PDF Archive",
             "desc": "All generated PDFs with search and download"},
        ],
    },
    {
        "id": "logistics",
        "icon": "🚚",
        "name": "Logistics",
        "color": "#b45309",
        "desc": "Track shipments, ports, routes, freight",
        "features": [
            {"icon": "🚢", "name": "Maritime Logistics", "page": "🚢 Maritime Logistics",
             "desc": "Vessel tracking, transit times, port schedules"},
            {"icon": "🚢", "name": "Supply Chain", "page": "🚢 Supply Chain",
             "desc": "End-to-end supply chain visibility"},
            {"icon": "⚓", "name": "Port Tracker", "page": "⚓ Port Import Tracker",
             "desc": "Port-wise HS 271320 import data"},
            {"icon": "👥", "name": "Ecosystem Management", "page": "👥 Ecosystem Management",
             "desc": "Manage suppliers, buyers, logistics partners"},
            {"icon": "🏭", "name": "Refinery Supply", "page": "🏭 Refinery Supply",
             "desc": "PSU refinery production and availability"},
            {"icon": "📋", "name": "Source Directory", "page": "📋 Source Directory",
             "desc": "Directory of refineries, terminals, decanters"},
        ],
    },
    {
        "id": "reports",
        "icon": "📊",
        "name": "Reports",
        "color": "#dc2626",
        "desc": "Financial analysis, demand forecasts, risk assessment",
        "features": [
            {"icon": "💰", "name": "Financial Intelligence", "page": "💰 Financial Intelligence",
             "desc": "P&L analysis, cashflow stress testing"},
            {"icon": "👷", "name": "Demand Analytics", "page": "👷 Demand Analytics",
             "desc": "Contractor demand cycles, seasonal patterns"},
            {"icon": "📈", "name": "Demand Correlation", "page": "📈 Demand Correlation",
             "desc": "Highway KM vs bitumen demand analysis"},
            {"icon": "🛣️", "name": "Road Budget", "page": "🛣️ Road Budget & Demand",
             "desc": "India road budget and state-wise demand"},
            {"icon": "⏳", "name": "Past Predictions", "page": "⏳ Past Predictions",
             "desc": "Prediction accuracy tracking over 10 years"},
            {"icon": "⚡", "name": "Risk Scoring", "page": "⚡ Risk Scoring",
             "desc": "Multi-factor deal risk assessment"},
            {"icon": "🎯", "name": "Strategy Panel", "page": "🎯 Strategy Panel",
             "desc": "What-if scenarios and strategic planning"},
            {"icon": "📤", "name": "Export Reports", "page": "📤 Reports",
             "desc": "Generate and download PDF/Excel reports"},
        ],
    },
    {
        "id": "compliance",
        "icon": "🛡️",
        "name": "Compliance",
        "color": "#059669",
        "desc": "GST, legal compliance, government data",
        "features": [
            {"icon": "🏗️", "name": "Govt Data Hub", "page": "🏗️ Govt Data Hub",
             "desc": "NHAI progress, UN Comtrade, budget data"},
            {"icon": "🛡️", "name": "GST & Legal", "page": "🛡️ GST & Legal Monitor",
             "desc": "GST compliance, e-way bills, regulatory updates"},
            {"icon": "🔔", "name": "Alert System", "page": "🔔 Alert System",
             "desc": "Configure price/supply alerts and rules"},
            {"icon": "🚨", "name": "Alert Center", "page": "🚨 Alert Center",
             "desc": "View all active P0/P1/P2 alerts"},
            {"icon": "🔔", "name": "Change Log", "page": "🔔 Change Notifications",
             "desc": "Audit trail of all system changes"},
            {"icon": "🗂️", "name": "Procurement Directory", "page": "🗂️ India Procurement Directory",
             "desc": "Govt procurement organizations and tenders"},
        ],
    },
    {
        "id": "system",
        "icon": "⚙️",
        "name": "System & AI",
        "color": "#475569",
        "desc": "System health, API status, AI engine, settings",
        "features": [
            {"icon": "💬", "name": "AI Chatbot", "page": "💬 Trading Chatbot",
             "desc": "Ask anything — AI connected to all your data", "star": True},
            {"icon": "🔄", "name": "AI Fallback Engine", "page": "🔄 AI Fallback Engine",
             "desc": "9-provider AI chain status and health"},
            {"icon": "📚", "name": "Knowledge Base", "page": "📚 Knowledge Base",
             "desc": "196 Q&A pairs about bitumen trading"},
            {"icon": "🌐", "name": "API Dashboard", "page": "🌐 API Dashboard",
             "desc": "Live API status, latency, health metrics"},
            {"icon": "🔗", "name": "API Hub", "page": "🔗 API HUB",
             "desc": "Central data integration and connectors"},
            {"icon": "🎛️", "name": "System Control", "page": "🎛️ System Control Center",
             "desc": "Master system controls and workers"},
            {"icon": "🏥", "name": "System Health", "page": "🏥 System Health",
             "desc": "SRE monitoring, self-healing, metrics"},
            {"icon": "⚙️", "name": "Settings", "page": "⚙️ Settings",
             "desc": "Margins, GST rates, transport rates, config"},
            {"icon": "🐞", "name": "Bug Tracker", "page": "🐞 Bug Tracker",
             "desc": "Known issues, failed APIs, auto-created bugs"},
        ],
    },
]

TOTAL_FEATURES = sum(len(c["features"]) for c in CATEGORIES)


# ═══════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════

def _inject_styles():
    st.markdown("""<style>
/* ══════════════════════════════════════════════════════════════════════
   COMMAND CENTER v3.0 — CSS Overrides
   These MUST override the Vastu Design System defaults
   ══════════════════════════════════════════════════════════════════════ */

/* ── Force sidebar visible ────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    display: block !important;
    width: 270px !important;
    min-width: 270px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #fafbfd 0%, #f1f4f9 100%) !important;
    padding-top: 0.5rem !important;
}
button[data-testid="stSidebarCollapsedControl"] {
    display: block !important;
}

/* ── Main area ────────────────────────────────────────────────────── */
.main .block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 0.5rem !important;
}

/* ── CRITICAL: Override Vastu button styles for CC ────────────────── */
/* All buttons in main content: white bg, dark text, visible border */
section.main div[data-testid="stHorizontalBlock"] .stButton > button,
section.main div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"],
section.main div[data-testid="stHorizontalBlock"] .stButton > button[kind="secondary"],
section.main .stButton > button,
section.main .stButton > button[kind="primary"],
section.main .stButton > button[kind="secondary"] {
    background: #ffffff !important;
    color: #1e3a5f !important;
    border: 1.5px solid #c9d4e0 !important;
    border-bottom: 1.5px solid #c9d4e0 !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    border-radius: 8px !important;
    min-height: 34px !important;
    padding: 5px 14px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
    text-shadow: none !important;
}
section.main div[data-testid="stHorizontalBlock"] .stButton > button:hover,
section.main .stButton > button:hover {
    background: #f0f4ff !important;
    border-color: #1e3a5f !important;
    color: #1e3a5f !important;
    box-shadow: 0 2px 6px rgba(30,58,95,0.15) !important;
}

/* ── Sidebar nav buttons ──────────────────────────────────────────── */
section[data-testid="stSidebar"] .stButton > button {
    font-size: 0.8rem !important;
    padding: 6px 12px !important;
    border-radius: 8px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    min-height: 36px !important;
    border: none !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #dbeafe 0%, #eff6ff 100%) !important;
    color: #1e3a5f !important;
    font-weight: 700 !important;
    border-left: 3px solid #1e3a5f !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #334155 !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: #f1f5f9 !important;
    color: #1e3a5f !important;
}

/* ── Card hover ───────────────────────────────────────────────────── */
.cc-hero, .cc-feat, .cc-catgrid { transition: all 0.2s ease; }
.cc-hero:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important; }
.cc-feat:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(0,0,0,0.08) !important; }
.cc-catgrid:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.10) !important; }

/* ── Column gap ───────────────────────────────────────────────────── */
div[data-testid="stHorizontalBlock"] { gap: 0.6rem !important; }
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

def _render_sidebar():
    active = st.session_state.get("_cc_category", "home")

    with st.sidebar:
        st.markdown("""
<div style="text-align:center;padding:12px 8px 14px 8px;border-bottom:2px solid #e2e8f0;
            margin:0 -8px 10px -8px;">
  <div style="font-size:1.2rem;font-weight:800;color:#1e3a5f;letter-spacing:-0.01em;">
    🏛️ PPS Anantam
  </div>
  <div style="font-size:0.68rem;color:#64748b;margin-top:2px;letter-spacing:0.04em;
              text-transform:uppercase;">Command Center</div>
</div>""", unsafe_allow_html=True)

        if st.button("🏠  Overview", use_container_width=True,
                     type="primary" if active == "home" else "secondary",
                     key="cc_nav_home"):
            st.session_state["_cc_category"] = "home"
            st.rerun()

        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

        for cat in CATEGORIES:
            is_active = active == cat["id"]
            count = len(cat["features"])
            label = f"{cat['icon']}  {cat['name']} ({count})"
            if st.button(label, use_container_width=True,
                         type="primary" if is_active else "secondary",
                         key=f"cc_nav_{cat['id']}"):
                st.session_state["_cc_category"] = cat["id"]
                st.rerun()

        st.markdown(f"""
<div style="border-top:1px solid #e2e8f0;margin-top:14px;padding-top:10px;
            text-align:center;font-size:0.68rem;color:#94a3b8;">
  v3.0 &bull; {TOTAL_FEATURES} features
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# HOME OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════

def _render_home_overview():
    now = datetime.datetime.now()
    today = datetime.date.today()
    greeting = ("Good Morning" if now.hour < 12
                else "Good Afternoon" if now.hour < 17
                else "Good Evening")

    # ── Load market data ──────────────────────────────────────────────────
    hub_cache = _load_json("hub_cache.json", {})
    brent, wti, usdinr = "—", "—", "—"
    try:
        crude_data = hub_cache.get("eia_crude", {}).get("data", [])
        if isinstance(crude_data, list):
            for rec in crude_data:
                if isinstance(rec, dict):
                    b = rec.get("benchmark", "").lower()
                    if "brent" in b:
                        brent = rec.get("price", "—")
                    elif "wti" in b:
                        wti = rec.get("price", "—")
        fx_data = hub_cache.get("frankfurter_fx", hub_cache.get("fx", {})).get("data", [])
        if isinstance(fx_data, list):
            for rec in fx_data:
                if isinstance(rec, dict) and "INR" in rec.get("pair", "").upper():
                    usdinr = rec.get("rate", "—")
    except Exception:
        pass

    live_prices = _load_json("live_prices.json", {})
    vg30_k = live_prices.get("DRUM_KANDLA_VG30", 35500)

    pa_raw = _load_json("tbl_purchase_advisor.json", {})
    pa = pa_raw.get("latest", pa_raw) if isinstance(pa_raw, dict) else {}
    pa_action = pa.get("recommendation", pa.get("action", "—"))
    pa_urgency = pa.get("urgency_index", "—")

    # ── Header banner ─────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#1e3a5f 0%,#0f2744 100%);border-radius:12px;
            padding:18px 24px;margin-bottom:16px;box-shadow:0 3px 15px rgba(30,58,95,0.22);">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <div>
      <div style="font-size:1.35rem;font-weight:800;color:#fff;">{greeting}, Sir</div>
      <div style="font-size:0.78rem;color:#93c5fd;margin-top:3px;">
        PPS Anantam Command Center &mdash; {today.strftime('%d %b %Y, %A')}
      </div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <div style="text-align:center;background:rgba(255,255,255,0.09);padding:6px 14px;
                  border-radius:8px;min-width:72px;">
        <div style="font-size:0.55rem;color:#93c5fd;text-transform:uppercase;letter-spacing:0.05em;">
          Brent</div>
        <div style="font-size:1rem;font-weight:700;color:#fcd34d;">${brent}</div>
      </div>
      <div style="text-align:center;background:rgba(255,255,255,0.09);padding:6px 14px;
                  border-radius:8px;min-width:72px;">
        <div style="font-size:0.55rem;color:#93c5fd;text-transform:uppercase;letter-spacing:0.05em;">
          WTI</div>
        <div style="font-size:1rem;font-weight:700;color:#e2e8f0;">${wti}</div>
      </div>
      <div style="text-align:center;background:rgba(255,255,255,0.09);padding:6px 14px;
                  border-radius:8px;min-width:72px;">
        <div style="font-size:0.55rem;color:#93c5fd;text-transform:uppercase;letter-spacing:0.05em;">
          USD/INR</div>
        <div style="font-size:1rem;font-weight:700;color:#86efac;">{usdinr}</div>
      </div>
      <div style="text-align:center;background:rgba(255,255,255,0.09);padding:6px 14px;
                  border-radius:8px;min-width:72px;">
        <div style="font-size:0.55rem;color:#93c5fd;text-transform:uppercase;letter-spacing:0.05em;">
          VG30</div>
        <div style="font-size:1rem;font-weight:700;color:#fbbf24;">{_fmt(vg30_k)}</div>
      </div>
      <div style="text-align:center;background:rgba(255,255,255,0.09);padding:6px 14px;
                  border-radius:8px;min-width:72px;">
        <div style="font-size:0.55rem;color:#93c5fd;text-transform:uppercase;letter-spacing:0.05em;">
          Signal</div>
        <div style="font-size:0.95rem;font-weight:700;color:#86efac;">{pa_action}</div>
        <div style="font-size:0.5rem;color:#93c5fd;">Urgency {pa_urgency}/100</div>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Quick Access — starred hero cards ─────────────────────────────────
    st.markdown("""<div style="font-size:0.95rem;font-weight:700;color:#1e3a5f;
                margin:4px 0 8px 0;">⭐ Quick Access</div>""", unsafe_allow_html=True)

    starred = []
    for cat in CATEGORIES:
        for feat in cat["features"]:
            if feat.get("star"):
                starred.append((feat, cat["color"], cat["id"]))

    if starred:
        qa_cols = st.columns(len(starred), gap="small")
        for i, (feat, color, cat_id) in enumerate(starred):
            with qa_cols[i]:
                st.markdown(f"""
<div class="cc-hero" style="
    background:linear-gradient(145deg, {color}0c 0%, {color}1a 100%);
    border:1px solid {color}28;
    border-left:5px solid {color};
    border-radius:10px;
    padding:16px;
    min-height:130px;
    box-shadow:0 2px 6px rgba(0,0,0,0.04);">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="font-size:1.5rem;">{feat['icon']}</span>
    <span style="background:#fef3c7;color:#92400e;font-size:0.6rem;font-weight:700;
                 padding:2px 8px;border-radius:8px;">★ TOP</span>
  </div>
  <div style="font-size:1rem;font-weight:800;color:#1e3a5f;margin-bottom:5px;">
    {feat['name']}</div>
  <div style="font-size:0.78rem;color:#475569;line-height:1.45;">
    {feat['desc']}</div>
</div>""", unsafe_allow_html=True)
                if st.button(f"Open {feat['name']}", key=f"cc_qa_{cat_id}_{i}",
                             use_container_width=True):
                    _go(feat["page"])
                    st.rerun()

    # ── Category Grid (3 x 3) ────────────────────────────────────────────
    st.markdown("""<div style="font-size:0.95rem;font-weight:700;color:#1e3a5f;
                margin:12px 0 8px 0;">📂 All Categories</div>""", unsafe_allow_html=True)

    for row_start in range(0, len(CATEGORIES), 3):
        row_cats = CATEGORIES[row_start:row_start + 3]
        cols = st.columns(3, gap="small")
        for idx, cat in enumerate(row_cats):
            with cols[idx]:
                color = cat["color"]
                count = len(cat["features"])
                top_feat = next(
                    (f for f in cat["features"] if f.get("star")),
                    cat["features"][0]
                )
                st.markdown(f"""
<div class="cc-catgrid" style="
    background:#fff;
    border:1px solid #e8dcc8;
    border-top:4px solid {color};
    border-radius:10px;
    padding:16px;
    min-height:155px;
    box-shadow:0 1px 5px rgba(0,0,0,0.04);">
  <div style="font-size:1.8rem;margin-bottom:8px;">{cat['icon']}</div>
  <div style="font-size:0.95rem;font-weight:800;color:#1e3a5f;margin-bottom:4px;">
    {cat['name']}</div>
  <div style="font-size:0.76rem;color:#475569;line-height:1.4;margin-bottom:10px;">
    {cat['desc']}</div>
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:0.7rem;color:#94a3b8;font-weight:500;">{count} features</span>
    <span style="font-size:0.68rem;color:{color};font-weight:600;">★ {top_feat['name']}</span>
  </div>
</div>""", unsafe_allow_html=True)
                if st.button("Explore", key=f"cc_catgrid_{cat['id']}",
                             use_container_width=True):
                    st.session_state["_cc_category"] = cat["id"]
                    st.rerun()

    # ── Footer ────────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="text-align:center;margin-top:18px;padding:10px 0;font-size:0.68rem;
            color:#94a3b8;border-top:1px solid #e8dcc8;">
  PPS Anantams Corporation Pvt Ltd &bull; Vadodara, Gujarat &bull;
  GST: 24AAHCV1611L2ZD &bull; Command Center v3.0 &bull; {now.strftime('%H:%M IST')}
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# CATEGORY VIEW
# ═══════════════════════════════════════════════════════════════════════════

def _render_category_view(cat):
    color = cat["color"]
    features = cat["features"]
    starred = [f for f in features if f.get("star")]
    regular = [f for f in features if not f.get("star")]

    # Back button
    if st.button("← Overview", key="cc_back"):
        st.session_state["_cc_category"] = "home"
        st.rerun()

    # ── Category banner ───────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,{color} 0%,{color}cc 100%);border-radius:12px;
            padding:20px 24px;margin-bottom:14px;box-shadow:0 3px 12px {color}25;">
  <div style="display:flex;align-items:center;gap:14px;">
    <div style="font-size:2.2rem;background:rgba(255,255,255,0.15);width:54px;height:54px;
                border-radius:12px;display:flex;align-items:center;justify-content:center;">
      {cat['icon']}</div>
    <div>
      <div style="font-size:1.2rem;font-weight:800;color:#fff;">{cat['name']}</div>
      <div style="font-size:0.8rem;color:rgba(255,255,255,0.85);margin-top:2px;">
        {cat['desc']}</div>
      <div style="font-size:0.68rem;color:rgba(255,255,255,0.6);margin-top:4px;">
        {len(features)} features available</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Starred features (hero cards, 2-col) ──────────────────────────────
    if starred:
        st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#1e3a5f;
                    margin-bottom:6px;">⭐ Top Features</div>""", unsafe_allow_html=True)

        star_cols = st.columns(2, gap="small")
        for i, feat in enumerate(starred):
            with star_cols[i % 2]:
                st.markdown(f"""
<div class="cc-hero" style="
    background:linear-gradient(145deg, {color}0c 0%, {color}1a 100%);
    border:1px solid {color}28;
    border-left:5px solid {color};
    border-radius:10px;
    padding:16px;
    min-height:110px;
    box-shadow:0 2px 8px rgba(0,0,0,0.05);">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="font-size:1.5rem;">{feat['icon']}</span>
    <span style="background:#fef3c7;color:#92400e;font-size:0.6rem;font-weight:700;
                 padding:2px 8px;border-radius:8px;">★ TOP</span>
  </div>
  <div style="font-size:1rem;font-weight:800;color:#1e3a5f;margin-bottom:5px;">
    {feat['name']}</div>
  <div style="font-size:0.78rem;color:#475569;line-height:1.45;">
    {feat['desc']}</div>
</div>""", unsafe_allow_html=True)
                if st.button(f"Open {feat['name']}", key=f"cc_star_{cat['id']}_{i}",
                             use_container_width=True):
                    _go(feat["page"])
                    st.rerun()

    # ── All other features (3-col grid) ───────────────────────────────────
    grid_features = regular if starred else features
    section_title = "All Features" if starred else "Features"

    st.markdown(f"""<div style="font-size:0.9rem;font-weight:700;color:#1e3a5f;
                margin:8px 0 6px 0;">📋 {section_title}</div>""", unsafe_allow_html=True)

    for row_start in range(0, len(grid_features), 3):
        row = grid_features[row_start:row_start + 3]
        cols = st.columns(3, gap="small")
        for idx, feat in enumerate(row):
            with cols[idx]:
                st.markdown(f"""
<div class="cc-feat" style="
    background:#fff;
    border:1px solid #e8dcc8;
    border-left:3px solid {color};
    border-radius:8px;
    padding:12px 14px;
    min-height:100px;
    box-shadow:0 1px 3px rgba(0,0,0,0.03);">
  <div style="font-size:1.1rem;margin-bottom:5px;">{feat['icon']}</div>
  <div style="font-size:0.88rem;font-weight:700;color:#1e3a5f;margin-bottom:4px;">
    {feat['name']}</div>
  <div style="font-size:0.75rem;color:#475569;line-height:1.4;">
    {feat['desc']}</div>
</div>""", unsafe_allow_html=True)
                if st.button("Open", key=f"cc_feat_{cat['id']}_{row_start + idx}",
                             use_container_width=True):
                    _go(feat["page"])
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════

def render():
    if "_cc_category" not in st.session_state:
        st.session_state["_cc_category"] = "home"

    _inject_styles()
    _render_sidebar()

    active = st.session_state.get("_cc_category", "home")

    if active == "home":
        _render_home_overview()
    else:
        cat = next((c for c in CATEGORIES if c["id"] == active), None)
        if cat:
            _render_category_view(cat)
        else:
            st.session_state["_cc_category"] = "home"
            _render_home_overview()
