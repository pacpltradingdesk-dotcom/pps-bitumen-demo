"""
Tutorial Engine — In-App User Guide
====================================
Renders a role-aware tutorial dialog accessible via the sidebar button.
Content mirrors USER_GUIDE.md but condensed for on-screen consumption.

Entry point:
    from tutorial_engine import render_tutorial_dialog
    render_tutorial_dialog()  # call when user clicks the Tutorial button
"""
from __future__ import annotations

import streamlit as st


# ── Content blocks ──────────────────────────────────────────────────────────

_INTRO = """
**PPS Anantam Dashboard** — Prince P Shah sir ki bitumen trading business ka
unified command center. 9 modules, 80+ pages, 60+ engines.

**Login:** Default `admin / 0000` — 24hr session.
**Navigate:** Top bar = 9 modules. Sidebar = features for active module.
Sidebar ke neeche Quick Actions (PDF/Print/Excel/Share/WA/TG).
"""

_JOURNEYS = {
    "👔 Director": [
        ("🏠 Home → Command Center", "5 KPIs + alerts scan (Brent, WTI, USD/INR, VG30, AI Signal)"),
        ("🏠 Home → Director Cockpit", "Yesterday summary + today priorities + 15-day outlook"),
        ("🧠 Intelligence → Market Signals", "10-signal composite — BULLISH / NEUTRAL / BEARISH"),
        ("📊 Reports → Director Brief", "Download 6-page executive PDF briefing"),
        ("📊 Reports → Risk Scoring", "Overall Health Score — Market/Supply/Financial/Compliance"),
    ],
    "💼 Sales": [
        ("💼 Sales → CRM Tasks", "Today's worklist — Due / Overdue / Upcoming"),
        ("💼 Sales → Daily Log", "Log yesterday's customer meetings"),
        ("🧠 Intelligence → News", "Market news scan"),
        ("💰 Pricing → Pricing Calculator", "Customer pe quote banao — 3-column cost flow"),
        ("💼 Sales → Comm Hub", "WhatsApp / Email / Call template generate karo"),
        ("💼 Sales → Negotiation AI", "Bade deal se pehle 3-tier offer brief"),
    ],
    "🚚 Operations": [
        ("💰 Pricing → Pricing Calculator", "Finalize pricing after order confirmed"),
        ("📄 Documents → Document Mgmt", "Create PO / SO (FY2526/PO/0001 format)"),
        ("🚚 Logistics → Feasibility Engine", "3-route comparison — kaunsa source best?"),
        ("🚚 Logistics → Tanker Tracking", "Track dispatch real-time"),
        ("🏛️ Compliance → E-Way Bill", "Generate e-way bill for transport"),
        ("🚚 Logistics → Maritime Logistics", "Import shipment — vessel + port tracking"),
    ],
    "👀 Viewer / Customer": [
        ("🏠 Home → Client Showcase", "Marketing landing page"),
        ("🏠 Home → Live Market", "Current prices — Brent, WTI, VG30, USD/INR"),
        ("🧠 Intelligence → News", "Latest market news"),
        ("🏠 Home → Subscription Pricing", "SaaS pricing plans"),
    ],
}

_MODULES = [
    ("🏠 Home", [
        "**Command Center** — Executive dashboard, 5 KPIs + alerts + quick actions",
        "**Live Market** — Real-time crude + FX + VG30 prices, BUY/SELL signals",
        "**Opportunities** — AI auto-discovered deals with WhatsApp templates",
        "**Director Cockpit** — Yesterday / Today / 15-day outlook (role-gated)",
        "**Client Showcase** — Public marketing page",
        "**Subscription Pricing** — SaaS tiers display",
    ]),
    ("💰 Pricing", [
        "**Pricing Calculator** — 3-column quote generator with PDF",
        "**One-Click Quote** — 5-step wizard for urgent quotes",
        "**Import Cost Model** — FOB → CIF → Landed simulator",
        "**Price Prediction** — 24-month forecast calendar",
        "**Manual Entry** — Admin override with calendar picker",
        "**SOS Pricing** — Emergency quick quotes",
        "**Past Revisions** — Prediction accuracy review",
    ]),
    ("💼 Sales & CRM", [
        "**CRM Tasks** — Daily worklist + calendar view",
        "**Sales Workspace** — Deal room for active negotiations",
        "**Negotiation AI** — 3-tier offer brief + objections",
        "**Comm Hub** — WA / Email / Call template generator",
        "**CRM Automation** — 24K contacts, festival broadcasts",
        "**Contacts Directory** — 25K+ searchable database",
        "**Contact Importer** — Bulk import (Excel/CSV/PDF)",
        "**Daily Log** — Meeting notes + AI annotations",
        "**Sales Calendar** — State seasons + holidays (28 states)",
        "**Comm Tracking** — Unified WA/Email/Call logs",
    ]),
    ("🧠 Intelligence", [
        "**Market Signals** — 10-signal composite BULLISH/BEARISH",
        "**Real-Time Insights** — Live monitor + disruption map",
        "**News Dashboard** — International + Domestic feeds",
        "**Business Advisor** — Buy/Sell advisory + 6 risk types",
        "**Purchase Advisor** — Urgency scoring + supplier rankings",
        "**Recommendation Engine** — Today's recs + forecasts",
        "**Global Markets** — Crude + Bitumen + FX charts",
        "**Competitor Intel** — IOCL/HPCL OSINT tracking",
        "**Telegram Analyzer** — Channel monitoring for price intel",
        "**Intelligence Hub** — Central KPI aggregation",
    ]),
    ("📄 Documents", [
        "**Document Mgmt** — PO / SO / Payment orders (FY-based numbering)",
        "**Party Master** — Supplier + customer master data",
        "**PDF Archive** — All generated PDFs (download/delete)",
    ]),
    ("🚚 Logistics", [
        "**Maritime Logistics** — Vessel map + port congestion",
        "**Supply Chain** — Iraq→Port→Tanker→Delivery→Payment",
        "**Port Tracker** — HS 271320 bitumen imports",
        "**Feasibility Engine** — 3-route cost comparison",
        "**Ecosystem Management** — Suppliers + Clients + Logistics",
        "**Refinery Supply** — Production heatmap + shutdown alerts",
        "**Tanker Tracking** — Real-time tanker location",
        "**Infra Demand** — Highway projects → bitumen demand",
    ]),
    ("📊 Reports", [
        "**Financial Intel** — P&L + cashflow + aging + scenarios",
        "**Strategy Panel** — Trade recommendations with confidence",
        "**Demand Analytics** — Contractor profiles + patterns",
        "**Correlation Dashboard** — Highway KM vs Bitumen demand",
        "**Road Budget** — NHAI pipeline + state allocation",
        "**Risk Scoring** — Overall Health Score composite",
        "**Director Brief** — 6-page executive PDF",
        "**Profitability** — Deal-wise margin analysis",
        "**Credit Aging** — 30/60/90/120-day receivables",
    ]),
    ("🏛️ Compliance (in 'More ▾')", [
        "**Govt Hub** — PPAC, MoRTH, NHAI, data.gov.in catalog",
        "**GST Legal Monitor** — GST status + e-invoice + GSTR match",
        "**Change Log** — Live + API + SRE history",
        "**NHAI Tender Dashboard** — Highway tender tracking",
        "**E-Way Bill** — Generation + tracking",
    ]),
    ("⚙️ System & AI (in 'More ▾')", [
        "**AI Chat** — Trading chatbot multi-turn",
        "**AI Fallback** — 5-provider chain (OpenAI→Claude)",
        "**AI Setup** — Environment + module registry",
        "**AI Learning** — Model accuracy + weight tuning",
        "**Health Monitor** — Traffic light system health",
        "**API Hub** — 25 connectors management",
        "**Settings** — 200+ config keys (margins, GST, APIs)",
        "**Bug Tracker** — P0-P3 bug tracking",
        "**Developer Ops** — Workers + models + errors",
        "**Flow Map** — 9-layer architecture view",
        "**SRE Dashboard** — Reliability metrics",
        "**Sync Status** — Data freshness + missing inputs",
        "**Knowledge Base** — FAQs + search",
        "**System Control** — Advanced admin (9 sections)",
    ]),
]

_QUICK_TIPS = [
    "🔄 **Auto-refresh**: Home page pe caches 30 min+ purane ho to auto refresh ho jate hain.",
    "🔐 **24hr Login**: Ek baar login karo, 24 hours tak session zinda rahega (tab close karke bhi).",
    "📱 **Sidebar Quick Actions**: Har page se PDF, Print, Excel, WhatsApp, Telegram direct ho sakta hai.",
    "🎯 **Command Center** is home — yahan se sab alerts + KPIs ek jagah.",
    "🔔 **Alerts**: P0 (red) = turant dekho, P1 (yellow) = aaj dekho, P2 (blue) = info only.",
    "💬 **AI Chat**: System > AI Chat mein kuch bhi pucho — trading context samajhta hai.",
    "📊 **Data Issues?**: System > Sync Status > 'Run Sync' click karo.",
    "🆘 **Mushkil mein?**: System > Knowledge Base mein FAQ search karo.",
]


# ── Dialog renderer ─────────────────────────────────────────────────────────

def _render_tutorial_content():
    """Core content — role-aware tabs + module reference + tips."""

    # Role detect
    role = st.session_state.get("_auth_role", "director").lower()
    if role == "admin":
        role = "director"
    role_title = role.title()

    st.markdown("### 📖 PPS Anantam — Dashboard Tutorial")
    st.caption(f"Logged in as: **{role_title}**  |  24hr session active")

    # Intro
    with st.expander("🎯 Yeh dashboard kya hai? (Start here)", expanded=True):
        st.markdown(_INTRO)

    # Journey tabs
    st.markdown("#### 🚶 Day-in-the-life — Apna role chuno")
    journey_keys = list(_JOURNEYS.keys())

    # Default to user's role
    role_map = {"director": 0, "sales": 1, "operations": 2, "viewer": 3}
    _default_idx = role_map.get(role, 0)

    _tabs = st.tabs(journey_keys)
    for idx, (journey_name, steps) in enumerate(_JOURNEYS.items()):
        with _tabs[idx]:
            for i, (page, desc) in enumerate(steps, 1):
                st.markdown(
                    f"""
<div style="background:#F9FAFB;border-left:3px solid #4F46E5;padding:10px 14px;margin:8px 0;border-radius:6px;">
<div style="font-size:0.75rem;color:#6B7280;font-weight:600;">STEP {i}</div>
<div style="font-size:0.9rem;font-weight:600;color:#111827;margin:2px 0;">{page}</div>
<div style="font-size:0.8rem;color:#4B5563;">{desc}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    # Modules reference
    st.markdown("---")
    st.markdown("#### 🗂️ All modules & pages (1-line reference)")
    for mod_name, pages in _MODULES:
        with st.expander(mod_name, expanded=False):
            for line in pages:
                st.markdown(f"- {line}")

    # Quick tips
    st.markdown("---")
    st.markdown("#### 💡 Quick Tips")
    for tip in _QUICK_TIPS:
        st.markdown(f"- {tip}")

    st.markdown("---")
    st.caption("📄 Full reference: `USER_GUIDE.md` in project root.")


# ── Public API ──────────────────────────────────────────────────────────────

def render_tutorial_dialog():
    """
    Call this when the Tutorial button is clicked.
    Uses st.dialog if available (Streamlit 1.35+), else inline container.
    """
    # Prefer native dialog for cleaner UX
    try:
        @st.dialog("📖 Tutorial — PPS Anantam Dashboard", width="large")
        def _dlg():
            _render_tutorial_content()
        _dlg()
        return
    except Exception:
        pass

    # Fallback: inline container (for older Streamlit)
    with st.container(border=True):
        _render_tutorial_content()
        if st.button("Close", key="_tut_close", type="secondary"):
            st.session_state["_show_tutorial"] = False
            st.rerun()
