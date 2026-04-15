"""
PPS Anantam — Navigation Configuration v6.0
=============================================
Single source of truth for the enterprise navigation structure.
6 sections — all visible in top bar, no overflow.
Each module lists its features. "page" = exact page string used by dispatch.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE NAVIGATION MAP (6 sections)
# ═══════════════════════════════════════════════════════════════════════════════

MODULE_NAV: dict[str, dict] = {
    "📊 Price & Info": {
        "icon": "📊", "label": "Price & Info",
        "tabs": [
            {"label": "Command Center", "page": "🎯 Command Center", "star": True},
            {"label": "Live Market", "page": "🏠 Home", "star": True, "pill": ("LIVE", "red")},
            {"label": "Market Signals", "page": "📡 Market Signals", "star": True, "pill": ("10-SIG", "indigo")},
            {"label": "News", "page": "📰 News Intelligence", "star": True},
            {"label": "Telegram Analyzer", "page": "📡 Telegram Analyzer", "star": True, "pill": ("24K", "emerald")},
            {"label": "Price Prediction", "page": "🔮 Price Prediction", "star": True, "pill": ("AI", "gold")},
            {"label": "Director Briefing", "page": "📋 Director Briefing", "star": True, "pill": ("08:30", "gold")},
            {"label": "Competitor Intel", "page": "🕵️ Competitor Intelligence"},
            {"label": "Real-time Insights", "page": "🔴 Real-time Insights"},
            {"label": "Business Advisor", "page": "🧑‍💼 Business Advisor"},
            {"label": "Purchase Advisor", "page": "🛒 Purchase Advisor"},
            {"label": "Recommendations", "page": "💡 Recommendations"},
            {"label": "Global Markets", "page": "🌐 Global Markets"},
            {"label": "NHAI Tenders", "page": "🏗️ NHAI Tenders"},
            {"label": "Import Cost Model", "page": "📦 Import Cost Model"},
            {"label": "Past Predictions", "page": "⏳ Past Predictions"},
            {"label": "Demand Analytics", "page": "👷 Demand Analytics"},
            {"label": "Correlation", "page": "📈 Demand Correlation"},
            {"label": "Road Budget", "page": "🛣️ Road Budget & Demand"},
            {"label": "Live Alerts", "page": "🚨 Alert Center"},
        ],
    },
    "🧾 Sales": {
        "icon": "🧾", "label": "Sales",
        "tabs": [
            {"label": "Pricing Calculator", "page": "🧮 Pricing Calculator", "star": True, "pill": ("3-TIER", "indigo")},
            {"label": "CRM & Tasks", "page": "🎯 CRM & Tasks", "star": True},
            {"label": "Opportunities", "page": "🔍 Opportunities", "star": True},
            {"label": "Negotiation", "page": "🤝 Negotiation Assistant", "star": True, "pill": ("AI", "gold")},
            {"label": "Daily Log", "page": "📓 Daily Log", "star": True},
            {"label": "One-Click Quote", "page": "💎 One-Click Quote"},
            {"label": "Sales Workspace", "page": "💼 Sales Workspace"},
            {"label": "Communication Hub", "page": "💬 Communication Hub"},
            {"label": "Client Chat", "page": "💬 Client Chat"},
            {"label": "CRM Automation", "page": "🤖 CRM Automation"},
            {"label": "Credit & Aging", "page": "💳 Credit & Aging"},
            {"label": "SOS Pricing", "page": "🚨 SPECIAL PRICE (SOS)"},
            {"label": "Financial Intel", "page": "💰 Financial Intelligence"},
            {"label": "Strategy Panel", "page": "🎯 Strategy Panel"},
            {"label": "Risk Scoring", "page": "⚡ Risk Scoring"},
            {"label": "Profitability", "page": "💰 Profitability Analytics"},
            {"label": "Sales Calendar", "page": "📅 Sales Calendar"},
        ],
    },
    "🚚 Logistics": {
        "icon": "🚚", "label": "Logistics",
        "tabs": [
            {"label": "Maritime Intel", "page": "🚢 Maritime Logistics"},
            {"label": "Supply Chain", "page": "🚢 Supply Chain"},
            {"label": "Port Tracker", "page": "⚓ Port Import Tracker"},
            {"label": "Feasibility", "page": "🏭 Feasibility"},
            {"label": "Ecosystem", "page": "👥 Ecosystem Management"},
            {"label": "Refinery Supply", "page": "🏭 Refinery Supply"},
            {"label": "Tanker Tracking", "page": "🚛 Tanker Tracking"},
            {"label": "E-Way Bills", "page": "📄 E-Way Bills"},
        ],
    },
    "📋 Purchasers": {
        "icon": "📋", "label": "Purchasers",
        "tabs": [
            {"label": "Purchase Orders", "page": "📋 Purchase Orders", "star": True},
            {"label": "Sales Orders", "page": "📋 Sales Orders"},
            {"label": "Payment Orders", "page": "💳 Payment Orders"},
            {"label": "Party Master", "page": "👥 Party Master"},
            {"label": "PDF Archive", "page": "📁 PDF Archive"},
            {"label": "Contacts Directory", "page": "📱 Contacts Directory"},
            {"label": "Manual Price Entry", "page": "📝 Manual Price Entry"},
            {"label": "Govt Data Hub", "page": "🏗️ Govt Data Hub"},
            {"label": "GST & Legal", "page": "🛡️ GST & Legal Monitor"},
            {"label": "Procurement Dir", "page": "🗂️ India Procurement Directory"},
            {"label": "Data Manager", "page": "🛠️ Data Manager"},
        ],
    },
    "📤 Sharing": {
        "icon": "📤", "label": "Sharing",
        "tabs": [
            {"label": "Share Center", "page": "📤 Share Center"},
            {"label": "Telegram", "page": "✈️ Telegram Dashboard"},
            {"label": "Rate Broadcast", "page": "📡 Rate Broadcast"},
            {"label": "Comm Tracking", "page": "📊 Comm Tracking"},
            {"label": "Client Showcase", "page": "🌐 Client Showcase"},
            {"label": "Subscription Pricing", "page": "💎 Subscription Pricing"},
            {"label": "Export Reports", "page": "📤 Reports"},
        ],
    },
    "⚙️ Settings": {
        "icon": "⚙️", "label": "Settings",
        "tabs": [
            {"label": "Settings", "page": "⚙️ Settings", "star": True},
            {"label": "Import Wizard", "page": "📥 Import Wizard"},
            {"label": "Import History", "page": "🗂️ Import History"},
            {"label": "AI Chatbot", "page": "💬 Trading Chatbot"},
            {"label": "AI Fallback", "page": "🔄 AI Fallback Engine"},
            {"label": "Knowledge Base", "page": "📚 Knowledge Base"},
            {"label": "AI Learning", "page": "🤖 AI Learning"},
            {"label": "System Control", "page": "🎛️ System Control Center"},
            {"label": "API Dashboard", "page": "🌐 API Dashboard"},
            {"label": "API Hub", "page": "🔗 API HUB"},
            {"label": "Health Monitor", "page": "🏥 Health Monitor"},
            {"label": "Bug Tracker", "page": "🐞 Bug Tracker"},
            {"label": "Developer Ops", "page": "🛠️ Developer Ops Map"},
            {"label": "Dashboard Flow", "page": "🗺️ Dashboard Flow Map"},
            {"label": "Alert System", "page": "🔔 Alert System"},
            {"label": "Change Log", "page": "🔔 Change Notifications"},
        ],
    },
}

# ── No overflow needed — all 6 sections visible ─────────────────────────────
OVERFLOW_MODULES: list[str] = []

# ── Top bar order (6 visible sections) ──────────────────────────────────────
TOPBAR_MODULES: list[str] = [
    "📊 Price & Info",
    "🧾 Sales",
    "🚚 Logistics",
    "📋 Purchasers",
    "📤 Sharing",
    "⚙️ Settings",
]

# ── Page redirects for consolidated/dropped pages ────────────────────────────
PAGE_REDIRECTS: dict[str, str] = {
    "📋 Discussion Guide": "🤝 Negotiation Assistant",
    "🔭 Contractor OSINT": "👷 Demand Analytics",
    "🏛️ Business Intelligence": "💡 Recommendations",
    "📋 Source Directory": "🗂️ India Procurement Directory",
    "📧 Email Setup": "⚙️ Settings",
    "📱 WhatsApp Setup": "⚙️ Settings",
    "🔗 Integrations": "⚙️ Settings",
    "📥 Contact Importer": "📱 Contacts Directory",
    "🤖 AI Assistant": "💬 Trading Chatbot",
    "🧠 AI Dashboard Assistant": "💬 Trading Chatbot",
    "🏥 System Health": "🏥 Health Monitor",
    "📦 System Requirements": "⚙️ Settings",
    "🔄 Sync Status": "🎛️ System Control Center",
    "🖥️ Ops Dashboard": "🛠️ Developer Ops Map",
    "🤖 AI Setup & Workers": "🎛️ System Control Center",
    "🎯 Intelligence Hub": "📡 Market Signals",
    "⚙️ Dev & System Activity": "🛠️ Developer Ops Map",
    "🏗️ Infra Demand Intelligence": "👷 Demand Analytics",
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_tabs(module: str) -> list[dict]:
    """Return the tab/feature definitions for a module."""
    mod = MODULE_NAV.get(module)
    return mod["tabs"] if mod else []


def get_default_page(module: str) -> str:
    """Return the first tab's default page for a module."""
    tabs = get_tabs(module)
    return tabs[0]["page"] if tabs else "🎯 Command Center"


def get_module_for_page(page: str) -> str | None:
    """Reverse lookup: given a page string, find which module owns it."""
    # Check redirects first
    page = PAGE_REDIRECTS.get(page, page)
    for mod_key, mod in MODULE_NAV.items():
        for tab in mod["tabs"]:
            if tab["page"] == page:
                return mod_key
    return None


def get_feature_idx_for_page(module: str, page: str) -> int:
    """Given a module and a page, return the feature index that owns it."""
    page = PAGE_REDIRECTS.get(page, page)
    for i, tab in enumerate(get_tabs(module)):
        if tab["page"] == page:
            return i
    return 0


def get_overflow_modules() -> list[str]:
    """Return the list of overflow module keys."""
    return OVERFLOW_MODULES


def is_overflow_module(module: str) -> bool:
    """Check if a module is in the overflow (More ▾) section."""
    return module in OVERFLOW_MODULES


def all_pages() -> list[str]:
    """Return a flat list of ALL page strings reachable through the nav."""
    pages: list[str] = []
    for mod in MODULE_NAV.values():
        for tab in mod["tabs"]:
            pages.append(tab["page"])
    return pages


def resolve_page(page: str) -> str:
    """Resolve a page string through redirects."""
    return PAGE_REDIRECTS.get(page, page)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE-LEVEL ROLE REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════════════

MODULE_ROLE_MAP: dict[str, str] = {
    "📊 Price & Info":  "viewer",
    "🧾 Sales":         "sales",
    "🚚 Logistics":     "operations",
    "📋 Purchasers":    "operations",
    "📤 Sharing":       "sales",
    "⚙️ Settings":      "director",
}


def _build_page_role_map() -> dict[str, str]:
    """Build a flat page → required role mapping from MODULE_ROLE_MAP."""
    mapping: dict[str, str] = {}
    for mod_key, mod in MODULE_NAV.items():
        required = MODULE_ROLE_MAP.get(mod_key, "viewer")
        for tab in mod["tabs"]:
            mapping[tab["page"]] = required
    return mapping


PAGE_ROLE_MAP: dict[str, str] = _build_page_role_map()
