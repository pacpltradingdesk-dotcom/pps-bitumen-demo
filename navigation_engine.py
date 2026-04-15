"""
Navigation Engine — Smart Cross-Links + Journey Maps
=====================================================
Stitches 80+ pages into coherent user journeys so features flow
naturally. Any page can call render_next_step_cards() at the bottom
to show 2-3 contextual "what to do next" buttons.

Also tracks recent page visits + provides a home widget to resume
wherever the user left off.

Public API:
  navigate_to(page)                    — jump to a page (updates module + rerun)
  track_page_visit(page)               — log current page to history
  get_recent_pages(n=5)                — list of (page, module, last_visit)
  render_next_step_cards(current_page) — 2-3 contextual next buttons
  render_continue_widget()             — home resume widget
  render_breadcrumb(current_page)      — thin location strip
"""
from __future__ import annotations

import time
import streamlit as st

from nav_config import MODULE_NAV, get_module_for_page, resolve_page


# ═══════════════════════════════════════════════════════════════════════════
# USER JOURNEYS — ordered page sequences for common business flows
# ═══════════════════════════════════════════════════════════════════════════

USER_JOURNEYS: dict[str, dict] = {
    "customer_call_to_quote": {
        "label":  "Customer Call → Quote Sent",
        "icon":   "📞",
        "pages":  ["🎯 CRM & Tasks", "📱 Contacts Directory",
                   "🧮 Pricing Calculator", "💬 Communication Hub"],
    },
    "deal_close_to_dispatch": {
        "label":  "Deal Close → Dispatch",
        "icon":   "🚚",
        "pages":  ["🧮 Pricing Calculator", "🤝 Negotiation Assistant",
                   "📋 Purchase Orders", "🏭 Feasibility",
                   "🚛 Tanker Tracking"],
    },
    "morning_intel": {
        "label":  "Morning Intel Round",
        "icon":   "🌅",
        "pages":  ["🎯 Command Center", "📡 Market Signals",
                   "📰 News Intelligence", "🛒 Purchase Advisor",
                   "📋 Director Briefing"],
    },
    "month_end_review": {
        "label":  "Month-End Review",
        "icon":   "📊",
        "pages":  ["💰 Financial Intelligence", "💳 Credit & Aging",
                   "💰 Profitability Analytics", "⚡ Risk Scoring"],
    },
    "broadcast_campaign": {
        "label":  "Broadcast Campaign",
        "icon":   "📡",
        "pages":  ["📱 Contacts Directory", "🔍 Opportunities",
                   "💬 Communication Hub", "📤 Share Center",
                   "📡 Rate Broadcast"],
    },
    "import_decision": {
        "label":  "Import Planning",
        "icon":   "🚢",
        "pages":  ["📦 Import Cost Model", "🚢 Maritime Logistics",
                   "⚓ Port Import Tracker", "🏭 Refinery Supply"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# NEXT-STEP CARDS — per-page contextual next actions
# Each entry: dict(label, target_page, icon, helper_text)
# ═══════════════════════════════════════════════════════════════════════════

NEXT_STEPS: dict[str, list[dict]] = {
    # ── HOME / COMMAND CENTER ────────────────────────────────────────
    "🎯 Command Center": [
        {"label": "Check Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "10-signal BULLISH/BEARISH composite"},
        {"label": "Scan News", "page": "📰 News Intelligence",
         "icon": "📰", "helper": "Latest oil/bitumen headlines"},
        {"label": "Today's Tasks", "page": "🎯 CRM & Tasks",
         "icon": "✅", "helper": "Due / overdue worklist"},
    ],
    "🏠 Home": [
        {"label": "Full Command Center", "page": "🎯 Command Center",
         "icon": "🎯", "helper": "5 KPIs + alerts + quick actions"},
        {"label": "Price Prediction", "page": "🔮 Price Prediction",
         "icon": "🔮", "helper": "24-month forecast calendar"},
        {"label": "Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "Composite directional view"},
    ],

    # ── SALES / CRM ──────────────────────────────────────────────────
    "🎯 CRM & Tasks": [
        {"label": "Make a Quote", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Customer aaya? Yahan price nikalo"},
        {"label": "Quick Quote (wizard)", "page": "💎 One-Click Quote",
         "icon": "💎", "helper": "5-step guided quote"},
        {"label": "Log Today's Calls", "page": "📓 Daily Log",
         "icon": "📓", "helper": "Customer interaction log"},
    ],
    "🧮 Pricing Calculator": [
        {"label": "Send Quote on WhatsApp", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "Template auto-pre-filled"},
        {"label": "Prep Negotiation", "page": "🤝 Negotiation Assistant",
         "icon": "🤝", "helper": "3-tier offers + objection handling"},
        {"label": "Create Purchase Order", "page": "📋 Purchase Orders",
         "icon": "📋", "helper": "Convert quote to formal PO"},
    ],
    "💎 One-Click Quote": [
        {"label": "Send to Customer", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "WhatsApp / Email the quote"},
        {"label": "Advanced Calc", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Full 3-column pricing breakdown"},
        {"label": "Save as PO", "page": "📋 Purchase Orders",
         "icon": "📋", "helper": "Formalize the deal"},
    ],
    "🔍 Opportunities": [
        {"label": "Contact via WhatsApp", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "Reactivation template ready"},
        {"label": "Price for this Customer", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Quick quote"},
        {"label": "Log Outreach", "page": "📓 Daily Log",
         "icon": "📓", "helper": "Record the attempt"},
    ],
    "🤝 Negotiation Assistant": [
        {"label": "Finalize Price", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Lock in the agreed number"},
        {"label": "Send Counter-Offer", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "Respond via WhatsApp"},
        {"label": "Create PO", "page": "📋 Purchase Orders",
         "icon": "📋", "helper": "Deal closed? Formalize now"},
    ],
    "💬 Communication Hub": [
        {"label": "Log Sent Message", "page": "📓 Daily Log",
         "icon": "📓", "helper": "Track outreach"},
        {"label": "Track Replies", "page": "📊 Comm Tracking",
         "icon": "📊", "helper": "Who responded"},
        {"label": "Create PO (if confirmed)", "page": "📋 Purchase Orders",
         "icon": "📋", "helper": "Customer confirmed deal"},
    ],
    "📓 Daily Log": [
        {"label": "Back to Tasks", "page": "🎯 CRM & Tasks",
         "icon": "✅", "helper": "Continue worklist"},
        {"label": "New Quote", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Next customer"},
        {"label": "Communication Hub", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Send follow-ups"},
    ],

    # ── INTELLIGENCE ─────────────────────────────────────────────────
    "📡 Market Signals": [
        {"label": "Dive into News", "page": "📰 News Intelligence",
         "icon": "📰", "helper": "What's driving the signals"},
        {"label": "Check Purchase Advisor", "page": "🛒 Purchase Advisor",
         "icon": "🛒", "helper": "Should I buy now?"},
        {"label": "Competitor Prices", "page": "🕵️ Competitor Intelligence",
         "icon": "🕵️", "helper": "IOCL / HPCL benchmarks"},
    ],
    "📰 News Intelligence": [
        {"label": "Market Signal Impact", "page": "📡 Market Signals",
         "icon": "📡", "helper": "How news affects composite"},
        {"label": "Broadcast to Clients", "page": "📡 Rate Broadcast",
         "icon": "📡", "helper": "Share top headlines"},
        {"label": "Director Brief", "page": "📋 Director Briefing",
         "icon": "📋", "helper": "Package into PDF"},
    ],
    "🛒 Purchase Advisor": [
        {"label": "Explore Feasibility", "page": "🏭 Feasibility",
         "icon": "🏭", "helper": "Best source routing"},
        {"label": "Check Import Cost", "page": "📦 Import Cost Model",
         "icon": "📦", "helper": "FOB → Landed calc"},
        {"label": "Refinery Supply", "page": "🏭 Refinery Supply",
         "icon": "🏭", "helper": "Domestic availability"},
    ],
    "📋 Director Briefing": [
        {"label": "Financial Deep-Dive", "page": "💰 Financial Intelligence",
         "icon": "💰", "helper": "P&L + cashflow + aging"},
        {"label": "Risk Score Check", "page": "⚡ Risk Scoring",
         "icon": "⚡", "helper": "Overall health score"},
        {"label": "Share with Team", "page": "📤 Share Center",
         "icon": "📤", "helper": "Distribute the briefing"},
    ],

    # ── PURCHASERS / DOCS ────────────────────────────────────────────
    "📋 Purchase Orders": [
        {"label": "Plan Logistics", "page": "🏭 Feasibility",
         "icon": "🏭", "helper": "Best source → destination"},
        {"label": "Track Payment", "page": "💳 Payment Orders",
         "icon": "💳", "helper": "Collections tracking"},
        {"label": "Create Sales Order", "page": "📋 Sales Orders",
         "icon": "📋", "helper": "Sister document"},
    ],
    "📋 Sales Orders": [
        {"label": "Generate E-Way Bill", "page": "📄 E-Way Bills",
         "icon": "📄", "helper": "Transport compliance"},
        {"label": "Track Dispatch", "page": "🚛 Tanker Tracking",
         "icon": "🚛", "helper": "Real-time tanker location"},
        {"label": "Payment Order", "page": "💳 Payment Orders",
         "icon": "💳", "helper": "Collection reminder"},
    ],
    "👥 Party Master": [
        {"label": "Contact a Party", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Send message"},
        {"label": "New Quote", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Offer to this party"},
        {"label": "CRM Timeline", "page": "🎯 CRM & Tasks",
         "icon": "🎯", "helper": "See all interactions"},
    ],
    "📱 Contacts Directory": [
        {"label": "Create Quote", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Offer to selected contact"},
        {"label": "Send WhatsApp", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "Template-based message"},
        {"label": "Schedule Broadcast", "page": "📡 Rate Broadcast",
         "icon": "📡", "helper": "Bulk campaign"},
    ],
    "💰 Profitability Analytics": [
        {"label": "Financial Intel", "page": "💰 Financial Intelligence",
         "icon": "💰", "helper": "Cashflow + aging + P&L"},
        {"label": "Risk Score", "page": "⚡ Risk Scoring",
         "icon": "⚡", "helper": "Overall health"},
        {"label": "Director Brief", "page": "📋 Director Briefing",
         "icon": "📋", "helper": "Package for Prince sir"},
    ],
    "⚡ Risk Scoring": [
        {"label": "Financial Intel", "page": "💰 Financial Intelligence",
         "icon": "💰", "helper": "Where's the stress?"},
        {"label": "Credit Aging", "page": "💳 Credit & Aging",
         "icon": "💳", "helper": "Receivables risk"},
        {"label": "GST & Legal", "page": "🛡️ GST & Legal Monitor",
         "icon": "🛡️", "helper": "Compliance risk"},
    ],
    "🎯 Strategy Panel": [
        {"label": "Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "Directional conviction"},
        {"label": "Recommendations", "page": "💡 Recommendations",
         "icon": "💡", "helper": "Today's trade recs"},
        {"label": "Director Brief", "page": "📋 Director Briefing",
         "icon": "📋", "helper": "Executive summary"},
    ],
    "💡 Recommendations": [
        {"label": "Strategy Panel", "page": "🎯 Strategy Panel",
         "icon": "🎯", "helper": "Longer-term plays"},
        {"label": "Purchase Advisor", "page": "🛒 Purchase Advisor",
         "icon": "🛒", "helper": "Buy-side urgency"},
        {"label": "Price Forecast", "page": "🔮 Price Prediction",
         "icon": "🔮", "helper": "24-month view"},
    ],
    "🚨 Alert Center": [
        {"label": "Command Center", "page": "🎯 Command Center",
         "icon": "🎯", "helper": "Full dashboard"},
        {"label": "Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "Driver of the alert"},
        {"label": "Broadcast Clients", "page": "📡 Rate Broadcast",
         "icon": "📡", "helper": "Inform customers"},
    ],
    "🛡️ GST & Legal Monitor": [
        {"label": "Party Master", "page": "👥 Party Master",
         "icon": "👥", "helper": "Check supplier GST status"},
        {"label": "Payment Orders", "page": "💳 Payment Orders",
         "icon": "💳", "helper": "Outstanding invoices"},
        {"label": "Risk Scoring", "page": "⚡ Risk Scoring",
         "icon": "⚡", "helper": "Compliance risk view"},
    ],
    "📄 E-Way Bills": [
        {"label": "Sales Orders", "page": "📋 Sales Orders",
         "icon": "📋", "helper": "Parent order"},
        {"label": "Tanker Tracking", "page": "🚛 Tanker Tracking",
         "icon": "🚛", "helper": "Monitor dispatch"},
        {"label": "Payment Orders", "page": "💳 Payment Orders",
         "icon": "💳", "helper": "Collection tracking"},
    ],
    "💳 Payment Orders": [
        {"label": "Credit Aging", "page": "💳 Credit & Aging",
         "icon": "💳", "helper": "Aging analysis"},
        {"label": "Send Reminder", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "Payment reminder template"},
        {"label": "Party Master", "page": "👥 Party Master",
         "icon": "👥", "helper": "Customer details"},
    ],

    # ── LOGISTICS ────────────────────────────────────────────────────
    "🏭 Feasibility": [
        {"label": "Check Maritime", "page": "🚢 Maritime Logistics",
         "icon": "🚢", "helper": "Vessel + port data"},
        {"label": "Import Cost Model", "page": "📦 Import Cost Model",
         "icon": "📦", "helper": "Full FOB → CIF simulator"},
        {"label": "Track Dispatch", "page": "🚛 Tanker Tracking",
         "icon": "🚛", "helper": "Active deliveries"},
    ],
    "🚢 Maritime Logistics": [
        {"label": "Port Imports", "page": "⚓ Port Import Tracker",
         "icon": "⚓", "helper": "HS 271320 bitumen"},
        {"label": "Refinery Supply", "page": "🏭 Refinery Supply",
         "icon": "🏭", "helper": "Alternative domestic"},
        {"label": "Feasibility Compare", "page": "🏭 Feasibility",
         "icon": "🏭", "helper": "Best route"},
    ],
    "⚓ Port Import Tracker": [
        {"label": "Refinery Supply", "page": "🏭 Refinery Supply",
         "icon": "🏭", "helper": "Compare with domestic"},
        {"label": "Import Cost Model", "page": "📦 Import Cost Model",
         "icon": "📦", "helper": "Landed cost calc"},
        {"label": "Maritime Intel", "page": "🚢 Maritime Logistics",
         "icon": "🚢", "helper": "Vessel & route view"},
    ],
    "🏭 Refinery Supply": [
        {"label": "Feasibility", "page": "🏭 Feasibility",
         "icon": "🏭", "helper": "Route comparison"},
        {"label": "Pricing Calc", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Quote with domestic"},
        {"label": "Port Imports", "page": "⚓ Port Import Tracker",
         "icon": "⚓", "helper": "Import alternative"},
    ],
    "📦 Import Cost Model": [
        {"label": "Check Feasibility", "page": "🏭 Feasibility",
         "icon": "🏭", "helper": "Vs other sources"},
        {"label": "Port Tracker", "page": "⚓ Port Import Tracker",
         "icon": "⚓", "helper": "Live port data"},
        {"label": "Lock Customer Quote", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Pass on the landed cost"},
    ],
    "🚛 Tanker Tracking": [
        {"label": "E-Way Bill", "page": "📄 E-Way Bills",
         "icon": "📄", "helper": "Required for transport"},
        {"label": "Back to Sales Order", "page": "📋 Sales Orders",
         "icon": "📋", "helper": "Parent document"},
        {"label": "Payment Reminder", "page": "💳 Payment Orders",
         "icon": "💳", "helper": "Collect on delivery"},
    ],

    # ── REPORTS / FINANCIAL ──────────────────────────────────────────
    "💰 Financial Intelligence": [
        {"label": "Credit Aging", "page": "💳 Credit & Aging",
         "icon": "💳", "helper": "30/60/90/120-day receivables"},
        {"label": "Profitability", "page": "💰 Profitability Analytics",
         "icon": "💰", "helper": "Deal-wise margin"},
        {"label": "Risk Overview", "page": "⚡ Risk Scoring",
         "icon": "⚡", "helper": "Overall health"},
    ],
    "💳 Credit & Aging": [
        {"label": "Send Reminder", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "Payment reminder template"},
        {"label": "Check Party Master", "page": "👥 Party Master",
         "icon": "👥", "helper": "Customer credit history"},
        {"label": "Profitability View", "page": "💰 Profitability Analytics",
         "icon": "💰", "helper": "Impact on margins"},
    ],

    # ── SHARING ──────────────────────────────────────────────────────
    "📤 Share Center": [
        {"label": "Schedule Broadcast", "page": "📡 Rate Broadcast",
         "icon": "📡", "helper": "To 25K contacts"},
        {"label": "Telegram Channels", "page": "✈️ Telegram Dashboard",
         "icon": "✈️", "helper": "Bot-driven broadcast"},
        {"label": "Track Delivery", "page": "📊 Comm Tracking",
         "icon": "📊", "helper": "Who received"},
    ],
    "📡 Rate Broadcast": [
        {"label": "Back to Share Center", "page": "📤 Share Center",
         "icon": "📤", "helper": "More options"},
        {"label": "Comm Tracking", "page": "📊 Comm Tracking",
         "icon": "📊", "helper": "Delivery report"},
        {"label": "Opportunities", "page": "🔍 Opportunities",
         "icon": "🔍", "helper": "Follow up leads"},
    ],

    # ── Price & Info (intel drill-downs) ────────────────────────────────
    "🕵️ Competitor Intelligence": [
        {"label": "Pricing Calculator", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Beat their rate"},
        {"label": "Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "Driver context"},
        {"label": "Negotiation Assistant", "page": "🤝 Negotiation Assistant",
         "icon": "🤝", "helper": "Counter their offer"},
    ],
    "🔴 Real-time Insights": [
        {"label": "Alert Center", "page": "🚨 Alert Center",
         "icon": "🚨", "helper": "Active alerts"},
        {"label": "Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "Composite view"},
        {"label": "News Feed", "page": "📰 News Intelligence",
         "icon": "📰", "helper": "Story context"},
    ],
    "🧑‍💼 Business Advisor": [
        {"label": "Purchase Advisor", "page": "🛒 Purchase Advisor",
         "icon": "🛒", "helper": "Buy-side advice"},
        {"label": "Strategy Panel", "page": "🎯 Strategy Panel",
         "icon": "🎯", "helper": "Longer-term plan"},
        {"label": "Risk Scoring", "page": "⚡ Risk Scoring",
         "icon": "⚡", "helper": "Risk context"},
    ],
    "🌐 Global Markets": [
        {"label": "Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "India impact"},
        {"label": "Import Cost Model", "page": "📦 Import Cost Model",
         "icon": "📦", "helper": "FX+FOB simulator"},
        {"label": "News Intelligence", "page": "📰 News Intelligence",
         "icon": "📰", "helper": "Drivers behind moves"},
    ],
    "📡 Telegram Analyzer": [
        {"label": "News Intelligence", "page": "📰 News Intelligence",
         "icon": "📰", "helper": "Cross-reference"},
        {"label": "Competitor Intel", "page": "🕵️ Competitor Intelligence",
         "icon": "🕵️", "helper": "Other sources"},
        {"label": "Telegram Dashboard", "page": "✈️ Telegram Dashboard",
         "icon": "✈️", "helper": "Bot management"},
    ],
    "🏗️ NHAI Tenders": [
        {"label": "Road Budget & Demand", "page": "🛣️ Road Budget & Demand",
         "icon": "🛣️", "helper": "Budget allocation"},
        {"label": "Demand Analytics", "page": "👷 Demand Analytics",
         "icon": "👷", "helper": "Contractor profiles"},
        {"label": "Govt Data Hub", "page": "🏗️ Govt Data Hub",
         "icon": "🏗️", "helper": "More govt sources"},
    ],
    "🔮 Price Prediction": [
        {"label": "Past Predictions", "page": "⏳ Past Predictions",
         "icon": "⏳", "helper": "Accuracy track record"},
        {"label": "AI Learning", "page": "🤖 AI Learning",
         "icon": "🤖", "helper": "Model weights tuning"},
        {"label": "Pricing Calculator", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Use forecast in quote"},
    ],
    "⏳ Past Predictions": [
        {"label": "Current Forecast", "page": "🔮 Price Prediction",
         "icon": "🔮", "helper": "24-month outlook"},
        {"label": "AI Learning", "page": "🤖 AI Learning",
         "icon": "🤖", "helper": "Improve accuracy"},
        {"label": "Market Signals", "page": "📡 Market Signals",
         "icon": "📡", "helper": "Why predictions moved"},
    ],
    "👷 Demand Analytics": [
        {"label": "NHAI Tenders", "page": "🏗️ NHAI Tenders",
         "icon": "🏗️", "helper": "Project pipeline"},
        {"label": "Road Budget", "page": "🛣️ Road Budget & Demand",
         "icon": "🛣️", "helper": "Budget allocation"},
        {"label": "Correlation", "page": "📈 Demand Correlation",
         "icon": "📈", "helper": "Highway-to-demand"},
    ],
    "📈 Demand Correlation": [
        {"label": "Demand Analytics", "page": "👷 Demand Analytics",
         "icon": "👷", "helper": "Contractor detail"},
        {"label": "Price Prediction", "page": "🔮 Price Prediction",
         "icon": "🔮", "helper": "Price impact"},
        {"label": "Road Budget", "page": "🛣️ Road Budget & Demand",
         "icon": "🛣️", "helper": "Funding side"},
    ],
    "🛣️ Road Budget & Demand": [
        {"label": "NHAI Tenders", "page": "🏗️ NHAI Tenders",
         "icon": "🏗️", "helper": "Active tenders"},
        {"label": "Demand Analytics", "page": "👷 Demand Analytics",
         "icon": "👷", "helper": "Who's bidding"},
        {"label": "Correlation", "page": "📈 Demand Correlation",
         "icon": "📈", "helper": "Demand impact"},
    ],

    # ── Sales (remaining) ───────────────────────────────────────────────
    "💼 Sales Workspace": [
        {"label": "Open Tasks", "page": "🎯 CRM & Tasks",
         "icon": "✅", "helper": "Today's worklist"},
        {"label": "New Quote", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Price a deal"},
        {"label": "Communications", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Send messages"},
    ],
    "💬 Client Chat": [
        {"label": "Communication Hub", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Template-based sends"},
        {"label": "Comm Tracking", "page": "📊 Comm Tracking",
         "icon": "📊", "helper": "Message log"},
        {"label": "CRM Tasks", "page": "🎯 CRM & Tasks",
         "icon": "🎯", "helper": "Convert to task"},
    ],
    "🤖 CRM Automation": [
        {"label": "Communication Hub", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Manual messages"},
        {"label": "Rate Broadcast", "page": "📡 Rate Broadcast",
         "icon": "📡", "helper": "Bulk campaign"},
        {"label": "Contacts Directory", "page": "📱 Contacts Directory",
         "icon": "📱", "helper": "Manage 25K contacts"},
    ],
    "🚨 SPECIAL PRICE (SOS)": [
        {"label": "Pricing Calculator", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Full breakdown"},
        {"label": "Negotiation", "page": "🤝 Negotiation Assistant",
         "icon": "🤝", "helper": "Lock the deal"},
        {"label": "Communication Hub", "page": "💬 Communication Hub",
         "icon": "📱", "helper": "Send urgent quote"},
    ],
    "📅 Sales Calendar": [
        {"label": "CRM Tasks", "page": "🎯 CRM & Tasks",
         "icon": "✅", "helper": "Today's schedule"},
        {"label": "Daily Log", "page": "📓 Daily Log",
         "icon": "📓", "helper": "Log interactions"},
        {"label": "Communication Hub", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Send reminders"},
    ],

    # ── Logistics (remaining) ──────────────────────────────────────────
    "🚢 Supply Chain": [
        {"label": "Maritime Intel", "page": "🚢 Maritime Logistics",
         "icon": "🚢", "helper": "Vessel tracking"},
        {"label": "Feasibility", "page": "🏭 Feasibility",
         "icon": "🏭", "helper": "Route comparison"},
        {"label": "Tanker Tracking", "page": "🚛 Tanker Tracking",
         "icon": "🚛", "helper": "Dispatch monitor"},
    ],
    "👥 Ecosystem Management": [
        {"label": "Party Master", "page": "👥 Party Master",
         "icon": "👥", "helper": "Master records"},
        {"label": "Contacts Directory", "page": "📱 Contacts Directory",
         "icon": "📱", "helper": "Full contact list"},
        {"label": "Feasibility", "page": "🏭 Feasibility",
         "icon": "🏭", "helper": "Route planning"},
    ],

    # ── Purchasers (remaining) ──────────────────────────────────────────
    "📁 PDF Archive": [
        {"label": "Purchase Orders", "page": "📋 Purchase Orders",
         "icon": "📋", "helper": "Create new PO"},
        {"label": "Sales Orders", "page": "📋 Sales Orders",
         "icon": "📋", "helper": "Create new SO"},
        {"label": "Share Center", "page": "📤 Share Center",
         "icon": "📤", "helper": "Send archived docs"},
    ],
    "📝 Manual Price Entry": [
        {"label": "Pricing Calculator", "page": "🧮 Pricing Calculator",
         "icon": "🧮", "helper": "Use overridden price"},
        {"label": "Price Prediction", "page": "🔮 Price Prediction",
         "icon": "🔮", "helper": "Forecast view"},
        {"label": "Settings", "page": "⚙️ Settings",
         "icon": "⚙️", "helper": "Pricing config"},
    ],
    "🏗️ Govt Data Hub": [
        {"label": "NHAI Tenders", "page": "🏗️ NHAI Tenders",
         "icon": "🏗️", "helper": "Live tenders"},
        {"label": "GST & Legal", "page": "🛡️ GST & Legal Monitor",
         "icon": "🛡️", "helper": "Compliance"},
        {"label": "Procurement Dir.", "page": "🗂️ India Procurement Directory",
         "icon": "🗂️", "helper": "Agency directory"},
    ],
    "🗂️ India Procurement Directory": [
        {"label": "Govt Data Hub", "page": "🏗️ Govt Data Hub",
         "icon": "🏗️", "helper": "API catalog"},
        {"label": "NHAI Tenders", "page": "🏗️ NHAI Tenders",
         "icon": "🏗️", "helper": "Live opportunities"},
        {"label": "Demand Analytics", "page": "👷 Demand Analytics",
         "icon": "👷", "helper": "Agency profiles"},
    ],
    "🛠️ Data Manager": [
        {"label": "Sync Status", "page": "🔔 Change Notifications",
         "icon": "🔔", "helper": "Recent changes"},
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "System status"},
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Data sources"},
    ],

    # ── Sharing (remaining) ─────────────────────────────────────────────
    "✈️ Telegram Dashboard": [
        {"label": "Share Center", "page": "📤 Share Center",
         "icon": "📤", "helper": "Cross-channel"},
        {"label": "Telegram Analyzer", "page": "📡 Telegram Analyzer",
         "icon": "📡", "helper": "Inbound intel"},
        {"label": "Comm Tracking", "page": "📊 Comm Tracking",
         "icon": "📊", "helper": "Delivery logs"},
    ],
    "📊 Comm Tracking": [
        {"label": "Communication Hub", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Send more"},
        {"label": "CRM Tasks", "page": "🎯 CRM & Tasks",
         "icon": "🎯", "helper": "Follow-ups"},
        {"label": "Share Center", "page": "📤 Share Center",
         "icon": "📤", "helper": "Bulk broadcast"},
    ],
    "🌐 Client Showcase": [
        {"label": "Subscription Pricing", "page": "💎 Subscription Pricing",
         "icon": "💎", "helper": "SaaS plans"},
        {"label": "Share Center", "page": "📤 Share Center",
         "icon": "📤", "helper": "Send to prospects"},
        {"label": "Communication Hub", "page": "💬 Communication Hub",
         "icon": "💬", "helper": "Personal outreach"},
    ],
    "💎 Subscription Pricing": [
        {"label": "Client Showcase", "page": "🌐 Client Showcase",
         "icon": "🌐", "helper": "Marketing page"},
        {"label": "Share Center", "page": "📤 Share Center",
         "icon": "📤", "helper": "Send to leads"},
        {"label": "Settings", "page": "⚙️ Settings",
         "icon": "⚙️", "helper": "Business rules"},
    ],
    "📤 Reports": [
        {"label": "Director Briefing", "page": "📋 Director Briefing",
         "icon": "📋", "helper": "Executive PDF"},
        {"label": "Financial Intel", "page": "💰 Financial Intelligence",
         "icon": "💰", "helper": "P&L + cashflow"},
        {"label": "Share Center", "page": "📤 Share Center",
         "icon": "📤", "helper": "Distribute"},
    ],

    # ── Settings / System ───────────────────────────────────────────────
    "⚙️ Settings": [
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Data connectors"},
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "System status"},
        {"label": "Knowledge Base", "page": "📚 Knowledge Base",
         "icon": "📚", "helper": "FAQs & journeys"},
    ],
    "💬 Trading Chatbot": [
        {"label": "AI Fallback", "page": "🔄 AI Fallback Engine",
         "icon": "🔄", "helper": "Provider chain"},
        {"label": "AI Learning", "page": "🤖 AI Learning",
         "icon": "🤖", "helper": "Accuracy tracking"},
        {"label": "Knowledge Base", "page": "📚 Knowledge Base",
         "icon": "📚", "helper": "FAQ reference"},
    ],
    "🔄 AI Fallback Engine": [
        {"label": "AI Chatbot", "page": "💬 Trading Chatbot",
         "icon": "💬", "helper": "Test providers"},
        {"label": "AI Learning", "page": "🤖 AI Learning",
         "icon": "🤖", "helper": "Model tuning"},
        {"label": "Settings", "page": "⚙️ Settings",
         "icon": "⚙️", "helper": "API keys"},
    ],
    "📚 Knowledge Base": [
        {"label": "AI Chatbot", "page": "💬 Trading Chatbot",
         "icon": "💬", "helper": "Ask questions"},
        {"label": "Command Center", "page": "🎯 Command Center",
         "icon": "🎯", "helper": "Back to home"},
        {"label": "Settings", "page": "⚙️ Settings",
         "icon": "⚙️", "helper": "Configure"},
    ],
    "🤖 AI Learning": [
        {"label": "Price Prediction", "page": "🔮 Price Prediction",
         "icon": "🔮", "helper": "See forecast"},
        {"label": "Past Predictions", "page": "⏳ Past Predictions",
         "icon": "⏳", "helper": "Accuracy history"},
        {"label": "AI Fallback", "page": "🔄 AI Fallback Engine",
         "icon": "🔄", "helper": "Provider settings"},
    ],
    "🎛️ System Control Center": [
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "Traffic lights"},
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Connector status"},
        {"label": "Bug Tracker", "page": "🐞 Bug Tracker",
         "icon": "🐞", "helper": "Open issues"},
    ],
    "🌐 API Dashboard": [
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Full catalog"},
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "Status check"},
        {"label": "Change Notifications", "page": "🔔 Change Notifications",
         "icon": "🔔", "helper": "API changelog"},
    ],
    "🔗 API HUB": [
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "Connector health"},
        {"label": "Settings", "page": "⚙️ Settings",
         "icon": "⚙️", "helper": "API keys"},
        {"label": "Developer Ops", "page": "🛠️ Developer Ops Map",
         "icon": "🛠️", "helper": "Worker status"},
    ],
    "🏥 Health Monitor": [
        {"label": "System Control", "page": "🎛️ System Control Center",
         "icon": "🎛️", "helper": "Admin actions"},
        {"label": "Bug Tracker", "page": "🐞 Bug Tracker",
         "icon": "🐞", "helper": "Known issues"},
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Source status"},
    ],
    "🐞 Bug Tracker": [
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "System health"},
        {"label": "System Control", "page": "🎛️ System Control Center",
         "icon": "🎛️", "helper": "Service control"},
        {"label": "Change Log", "page": "🔔 Change Notifications",
         "icon": "🔔", "helper": "Recent changes"},
    ],
    "🛠️ Developer Ops Map": [
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Data connectors"},
        {"label": "Flow Map", "page": "🗺️ Dashboard Flow Map",
         "icon": "🗺️", "helper": "Architecture view"},
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "Live status"},
    ],
    "🗺️ Dashboard Flow Map": [
        {"label": "Developer Ops", "page": "🛠️ Developer Ops Map",
         "icon": "🛠️", "helper": "Worker detail"},
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Data layer"},
        {"label": "Command Center", "page": "🎯 Command Center",
         "icon": "🎯", "helper": "Back to home"},
    ],
    "🔔 Alert System": [
        {"label": "Alert Center", "page": "🚨 Alert Center",
         "icon": "🚨", "helper": "Active alerts"},
        {"label": "Settings", "page": "⚙️ Settings",
         "icon": "⚙️", "helper": "Thresholds config"},
        {"label": "Change Log", "page": "🔔 Change Notifications",
         "icon": "🔔", "helper": "Recent activity"},
    ],
    "🔔 Change Notifications": [
        {"label": "Bug Tracker", "page": "🐞 Bug Tracker",
         "icon": "🐞", "helper": "Issue log"},
        {"label": "Health Monitor", "page": "🏥 Health Monitor",
         "icon": "🏥", "helper": "System status"},
        {"label": "API Hub", "page": "🔗 API HUB",
         "icon": "🔗", "helper": "Connector changes"},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# Core navigation helper
# ═══════════════════════════════════════════════════════════════════════════

def navigate_to(page: str, ctx: dict | None = None):
    """
    Programmatically jump to a page. Sets module + page + rerun.
    Optionally merges a context dict (customer, grade, etc.) into
    the global context bucket so the target page can pre-fill.
    """
    if ctx:
        for k, v in ctx.items():
            set_context(k, v)
    page = resolve_page(page)
    module = get_module_for_page(page)
    if module:
        st.session_state["_active_module"] = module
    st.session_state["selected_page"] = page
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Global Context — shared data bucket that persists across pages
# ═══════════════════════════════════════════════════════════════════════════
# Standard keys:
#   customer_name   — primary customer full name
#   customer_id     — DB row id (if known)
#   customer_phone  — 10-digit or +91-prefixed
#   customer_email
#   customer_city
#   customer_state
#   customer_category — "Purchase Party" / "Sales Client" / etc
#   customer_grade  — preferred bitumen grade (VG30 / VG10)
#   active_deal_id
#   active_quote_id

_CTX_KEY = "_ctx"


def set_context(key: str, value):
    """Set a global context value that persists across pages."""
    st.session_state.setdefault(_CTX_KEY, {})[key] = value


def get_context(key: str, default=None):
    """Read a context value. Returns default if not set."""
    return st.session_state.get(_CTX_KEY, {}).get(key, default)


def clear_context(key: str | None = None):
    """Clear one key or (if key is None) the entire context bucket."""
    ctx = st.session_state.get(_CTX_KEY, {})
    if key is None:
        st.session_state[_CTX_KEY] = {}
    elif key in ctx:
        del ctx[key]


def all_context() -> dict:
    """Return a shallow copy of the full context bucket."""
    return dict(st.session_state.get(_CTX_KEY, {}))


def set_active_customer(name: str, phone: str = "", email: str = "",
                        city: str = "", state: str = "",
                        category: str = "", cid=None, grade: str = ""):
    """Convenience: set all customer-related context fields at once."""
    set_context("customer_name",  name or "")
    set_context("customer_phone", phone or "")
    set_context("customer_email", email or "")
    set_context("customer_city",  city or "")
    set_context("customer_state", state or "")
    set_context("customer_category", category or "")
    if cid is not None:
        set_context("customer_id", cid)
    if grade:
        set_context("customer_grade", grade)


def clear_active_customer():
    """Remove all customer context fields."""
    for k in ("customer_name", "customer_id", "customer_phone", "customer_email",
              "customer_city", "customer_state", "customer_category",
              "customer_grade"):
        clear_context(k)


# ═══════════════════════════════════════════════════════════════════════════
# Recent history tracking
# ═══════════════════════════════════════════════════════════════════════════

_MAX_HISTORY = 15


def track_page_visit(page: str):
    """Push current page to the session history (dedupes consecutive)."""
    if not page:
        return
    hist = st.session_state.get("_page_history", [])
    if hist and hist[-1].get("page") == page:
        # Already last — just refresh timestamp
        hist[-1]["ts"] = time.time()
    else:
        hist.append({"page": page, "ts": time.time()})
    st.session_state["_page_history"] = hist[-_MAX_HISTORY:]


def get_recent_pages(n: int = 5, exclude_current: bool = True) -> list[dict]:
    """Return the n most-recent visited pages (newest first)."""
    hist = st.session_state.get("_page_history", [])
    current = st.session_state.get("selected_page", "")
    out = []
    seen = set()
    for entry in reversed(hist):
        p = entry.get("page")
        if not p or p in seen:
            continue
        if exclude_current and p == current:
            continue
        seen.add(p)
        out.append({
            "page":   p,
            "module": get_module_for_page(p) or "",
            "ts":     entry.get("ts", 0),
        })
        if len(out) >= n:
            break
    return out


def _time_ago(ts: float) -> str:
    """Human-readable relative time."""
    if not ts:
        return ""
    delta = max(0, time.time() - ts)
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)} min ago"
    if delta < 86400:
        return f"{int(delta // 3600)} hr ago"
    return f"{int(delta // 86400)} days ago"


# ═══════════════════════════════════════════════════════════════════════════
# UI renderers
# ═══════════════════════════════════════════════════════════════════════════

def render_next_step_cards(current_page: str):
    """Render 2-3 contextual next-step buttons at the bottom of a page.

    Each card links to the next logical page in the user's flow.
    If the page has no entry in NEXT_STEPS, nothing renders.
    """
    steps = NEXT_STEPS.get(current_page)
    if not steps:
        return

    st.markdown(
        '<div style="margin-top:40px;padding-top:20px;border-top:1px solid #E5E7EB;">'
        '<div style="font-size:0.72rem;font-weight:700;color:#6B7280;'
        'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">'
        '✨ Next Step — jaahan aaram se jaa sakte ho'
        '</div></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(steps))
    for i, step in enumerate(steps):
        with cols[i]:
            st.markdown(
                f"""
<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;
            padding:16px 14px;min-height:110px;box-shadow:0 1px 3px rgba(0,0,0,0.04);
            transition:all 0.2s;">
  <div style="font-size:1.5rem;margin-bottom:6px;">{step['icon']}</div>
  <div style="font-size:0.88rem;font-weight:700;color:#111827;margin-bottom:4px;">
    {step['label']}
  </div>
  <div style="font-size:0.72rem;color:#6B7280;line-height:1.4;">
    {step.get('helper', '')}
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
            if st.button(f"Go →", key=f"_ns_{current_page}_{i}",
                         use_container_width=True):
                navigate_to(step["page"])


def render_continue_widget():
    """Home-page widget: 'Continue where you left off' with 3 resume links."""
    recent = get_recent_pages(n=3, exclude_current=True)
    if not recent:
        return

    st.markdown(
        '<div style="background:linear-gradient(135deg,#F5F3FF,#EEF2FF);'
        'border:1px solid #DDD6FE;border-radius:12px;padding:16px 18px;'
        'margin:16px 0 20px 0;">'
        '<div style="font-size:0.78rem;font-weight:800;color:#4F46E5;'
        'margin-bottom:10px;text-transform:uppercase;letter-spacing:0.06em;">'
        '⏱️ Continue where you left off'
        '</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(recent))
    for i, r in enumerate(recent):
        with cols[i]:
            label = r["page"]
            # Strip emoji prefix if present for cleaner title in button
            short = label.split(" ", 1)[-1] if " " in label else label
            if st.button(
                f"{label}\n\n{_time_ago(r['ts'])}",
                key=f"_cont_{i}",
                use_container_width=True,
            ):
                navigate_to(r["page"])

    st.markdown("</div>", unsafe_allow_html=True)


def render_breadcrumb(current_page: str):
    """Thin breadcrumb bar: Module > Page, clickable."""
    module = get_module_for_page(current_page)
    if not module:
        return
    mod_label = MODULE_NAV.get(module, {}).get("label", module)
    page_label = current_page.split(" ", 1)[-1] if " " in current_page else current_page

    st.markdown(
        f"""
<div style="display:flex;align-items:center;gap:8px;padding:6px 14px;
            background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
            margin:-8px 0 16px 0;font-size:0.78rem;color:#6B7280;">
  <span style="color:#9CA3AF;">📍</span>
  <span style="color:#4F46E5;font-weight:600;cursor:pointer;">{mod_label}</span>
  <span style="color:#D1D5DB;">›</span>
  <span style="color:#111827;font-weight:700;">{page_label}</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_active_context_strip():
    """
    If a customer is set in context, show a compact strip under the
    breadcrumb: "👤 <Customer Name> · <City> · <Grade> · [Clear]"
    Nothing rendered when context is empty.
    """
    name = get_context("customer_name")
    if not name:
        return

    parts = [f"👤 <b>{name}</b>"]
    city  = get_context("customer_city")
    state = get_context("customer_state")
    loc = " · ".join(x for x in [city, state] if x)
    if loc:
        parts.append(f"<span style='color:#6B7280;'>{loc}</span>")
    grade = get_context("customer_grade")
    if grade:
        parts.append(f"<span style='color:#059669;font-weight:600;'>{grade}</span>")
    phone = get_context("customer_phone")
    if phone:
        parts.append(f"<span style='color:#6B7280;'>📞 {phone}</span>")

    content = " · ".join(parts)
    st.markdown(
        f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            background:linear-gradient(90deg,#ECFDF5,#F0FDF4);
            border:1px solid #BBF7D0;border-radius:10px;padding:8px 16px;
            margin:-8px 0 14px 0;font-size:0.82rem;color:#064E3B;">
  <div>{content}</div>
  <div style="font-size:0.7rem;color:#059669;font-weight:600;">
    Active Customer · sab pages pe use hogi
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Clear button (small, right-aligned)
    _sp, _btn = st.columns([9, 1])
    with _btn:
        if st.button("Clear", key="_ctx_clear_btn", use_container_width=True,
                     help="Reset active customer — sab pages ka pre-fill hat jayega"):
            clear_active_customer()
            st.rerun()


@st.cache_data(ttl=600)
def _load_contact_options(limit: int = 1000) -> list[dict]:
    """Load top contacts for the picker dropdown (cached)."""
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT rowid, name, phone, email, city, state, category
                FROM tbl_contacts
                WHERE name IS NOT NULL AND name != ''
                ORDER BY rowid DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            return [{
                "id":    r[0],
                "name":  r[1] or "",
                "phone": r[2] or "",
                "email": r[3] or "",
                "city":  r[4] or "",
                "state": r[5] or "",
                "category": r[6] or "",
            } for r in rows if r[1]]
        finally:
            try: cur.close()
            except Exception: pass
    except Exception:
        return []


def render_customer_picker_sidebar():
    """
    Compact customer picker for the sidebar. Uses a searchable selectbox
    over the contacts DB. Setting here updates global context immediately.
    """
    with st.expander("🎯 Active Customer", expanded=bool(get_context("customer_name"))):
        current = get_context("customer_name") or ""
        if current:
            st.caption(f"Currently: **{current}**")

        contacts = _load_contact_options(1000)
        if not contacts:
            st.caption("Koi contact nahi mila — DB empty.")
            return

        # Build option labels
        options = ["(none)"] + [
            f'{c["name"]}  ·  {c["city"]}' if c["city"] else c["name"]
            for c in contacts
        ]
        # Find current index
        default_idx = 0
        if current:
            for i, c in enumerate(contacts):
                if c["name"] == current:
                    default_idx = i + 1
                    break

        sel = st.selectbox(
            "Pick customer",
            options,
            index=default_idx,
            key="_ctx_picker",
            label_visibility="collapsed",
        )
        if sel and sel != "(none)":
            # Find selected contact
            for c in contacts:
                label = f'{c["name"]}  ·  {c["city"]}' if c["city"] else c["name"]
                if label == sel:
                    if c["name"] != current:
                        set_active_customer(
                            name=c["name"], phone=c["phone"], email=c["email"],
                            city=c["city"], state=c["state"],
                            category=c["category"], cid=c["id"],
                        )
                        st.rerun()
                    break
        elif sel == "(none)" and current:
            clear_active_customer()
            st.rerun()


def render_journey_tips(current_page: str):
    """If current page is part of a journey, show the mini-map at top."""
    journeys = []
    for jid, jdata in USER_JOURNEYS.items():
        if current_page in jdata["pages"]:
            idx = jdata["pages"].index(current_page)
            journeys.append((jid, jdata, idx))

    if not journeys:
        return

    # Show the most relevant journey (first match for now)
    jid, jdata, idx = journeys[0]
    total = len(jdata["pages"])
    pcs = []
    for i, p in enumerate(jdata["pages"]):
        dot = "●" if i == idx else ("✓" if i < idx else "○")
        color = "#4F46E5" if i == idx else ("#10B981" if i < idx else "#D1D5DB")
        pcs.append(f'<span style="color:{color};font-size:0.85rem;">{dot}</span>')

    st.markdown(
        f"""
<div style="background:#FFFBEB;border-left:3px solid #F59E0B;
            padding:8px 14px;margin:-4px 0 14px 0;border-radius:6px;
            font-size:0.78rem;color:#92400E;display:flex;
            align-items:center;gap:10px;flex-wrap:wrap;">
  <span style="font-weight:700;">{jdata['icon']} {jdata['label']}</span>
  <span style="color:#D97706;">Step {idx+1} of {total}</span>
  <span style="display:flex;gap:4px;">{" ".join(pcs)}</span>
</div>
""",
        unsafe_allow_html=True,
    )
