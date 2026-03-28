# PPS Bitumen Dashboard v5.0 — Modular Rebuild Design Spec

## Overview

Complete modular rebuild of the PPS Bitumen Sales Dashboard. Same Streamlit framework, clean architecture, all 61+ features working, Clean Modern White theme, universal sharing to WhatsApp + Telegram + Email + PDF.

**Owner:** PPS Anantams Corporation (PACPL) — Prince P Shah
**Developer:** Rahul
**Current State:** v4.0 — 5200+ line dashboard.py, 56+ files, ~36 features working, ~25 skeleton
**Target State:** v5.0 — 500-line slim router, modular pages, all features working, share system, Telegram integration

## Decisions Made

| Decision | Choice |
|---|---|
| Navigation layout | Top Bar + Sidebar Combo (Option B) |
| Module count | 9 modules — 7 visible + 2 in "More ▾" |
| Sharing | Per-page share button + central Share Center |
| Filtering | Per-page local filters (no global filter bar) |
| Command Center | Executive Dashboard — KPIs, signals, quick actions only |
| Skeleton features | All must be working — no placeholders |
| UI Theme | Clean Modern White (Zoho/Notion style) |
| WhatsApp + Telegram | Both from Day 1 |
| Implementation | Modular Rebuild — same Streamlit, clean architecture |
| Future merge | WhatsApp Groups app + CRM v2 via API integration (later) |

---

## 1. Architecture

### File Structure

```
bitumen-sales-dashboard/
├── dashboard.py              # Slim router (~500 lines): session init, nav, page dispatch
├── theme.py                  # Clean White theme CSS (single source of truth)
├── nav_config.py             # 9 modules config + "More ▾" overflow (upgraded)
├── top_bar.py                # Top bar renderer (single row + overflow)
├── subtab_bar.py             # Sub-tab renderer with breadcrumb
├── share_system.py           # Universal share component (WA + TG + Email + PDF)
├── filter_components.py      # Reusable filter widgets (date, region, product, status)
│
├── engines/                  # Business logic (existing, mostly untouched)
│   ├── calculation_engine.py
│   ├── market_intelligence_engine.py
│   ├── crm_engine.py
│   ├── email_engine.py
│   ├── whatsapp_engine.py
│   ├── telegram_engine.py    # NEW
│   ├── recommendation_engine.py
│   └── ... (all existing engines)
│
├── pages/                    # UI pages (1 file per feature)
│   ├── home/
│   │   ├── command_center.py
│   │   ├── live_market.py
│   │   ├── top_targets.py
│   │   └── live_alerts.py
│   ├── pricing/
│   │   ├── pricing_calculator.py
│   │   ├── import_cost.py
│   │   ├── price_prediction.py
│   │   ├── manual_entry.py
│   │   ├── sos_pricing.py
│   │   └── past_predictions.py
│   ├── sales/
│   │   ├── crm_tasks.py
│   │   ├── sales_workspace.py
│   │   ├── negotiation.py
│   │   ├── comm_hub.py
│   │   ├── crm_automation.py
│   │   ├── daily_log.py
│   │   ├── contacts.py
│   │   └── comm_tracking.py
│   ├── intelligence/
│   │   ├── market_signals.py
│   │   ├── real_time_insights.py
│   │   ├── news_intel.py
│   │   ├── competitor_intel.py
│   │   ├── business_advisor.py
│   │   ├── purchase_advisor.py
│   │   ├── recommendations.py
│   │   └── global_markets.py
│   ├── documents/
│   │   ├── purchase_orders.py
│   │   ├── sales_orders.py
│   │   ├── payment_orders.py
│   │   ├── party_master.py
│   │   └── pdf_archive.py
│   ├── logistics/
│   │   ├── maritime_intel.py
│   │   ├── supply_chain.py
│   │   ├── port_tracker.py
│   │   ├── feasibility.py
│   │   ├── ecosystem.py
│   │   └── refinery_supply.py
│   ├── reports/
│   │   ├── financial_intel.py
│   │   ├── strategy_panel.py
│   │   ├── demand_analytics.py
│   │   ├── correlation.py
│   │   ├── road_budget.py
│   │   ├── risk_scoring.py
│   │   ├── export_reports.py
│   │   └── director_briefing.py
│   ├── compliance/
│   │   ├── govt_data_hub.py
│   │   ├── gst_legal.py
│   │   ├── alert_system.py
│   │   ├── change_log.py
│   │   └── procurement_dir.py
│   ├── system/
│   │   ├── ai_chatbot.py
│   │   ├── ai_fallback.py
│   │   ├── knowledge_base.py
│   │   ├── system_control.py
│   │   ├── api_dashboard.py
│   │   ├── api_hub.py
│   │   ├── health_monitor.py
│   │   ├── settings.py
│   │   ├── bug_tracker.py
│   │   ├── developer_ops.py
│   │   ├── dashboard_flow.py
│   │   └── ai_learning.py
│   └── sharing/
│       ├── share_center.py
│       ├── whatsapp_dashboard.py
│       └── telegram_dashboard.py
│
├── components/               # Reusable UI components
│   ├── kpi_card.py           # Metric card with share button
│   ├── data_table.py         # Filterable table with export
│   ├── chart_card.py         # Chart with share/download
│   ├── share_button.py       # Quick share dropdown (WA/TG/Email/PDF/Copy)
│   └── filter_bar.py         # Local filter component
│
├── data/                     # JSON data files + SQLite DB
└── command_intel/            # Existing files (gradually migrate to pages/)
```

### Data Flow

```
Engines (pure Python, no Streamlit) → return data/calculations
    ↓
Pages (UI layer) → call engines, render with st.* and components
    ↓
Components (reusable widgets) → used by pages (KPI cards, share buttons, filters)
    ↓
Router (dashboard.py) → dispatches to correct page based on nav state
    ↓
Theme (theme.py) → injected once, applies to all pages
```

### Share Flow

```
Any Page → share_button component (dropdown)
    ↓
User selects: WhatsApp / Telegram / Email / PDF / Copy
    ↓
Page provides: format_for_share() → returns summary text + data
    ↓
share_system.py → formats message per channel, sends via engine
    ↓
Logs to share_history.json for tracking
```

---

## 2. Navigation System

### Top Bar (Single Row)

7 modules visible + "More ▾" dropdown:

| Position | Module | Icon | Features Count |
|---|---|---|---|
| 1 | Home | 🏠 | 4 |
| 2 | Pricing | 💰 | 6 |
| 3 | Sales & CRM | 🧾 | 8 |
| 4 | Intelligence | 🧠 | 8 |
| 5 | Documents | 📄 | 5 |
| 6 | Logistics | 🚚 | 6 |
| 7 | Reports | 📊 | 8 |
| More ▾ | Compliance | 🛡️ | 5 |
| More ▾ | System & AI | ⚙️ | 12 |

**Right side icons:** WhatsApp (📱), Telegram (✈️), Notifications (🔔 with badge), Search (🔍)

### Left Sidebar

- Shows features of the currently selected module
- Active feature highlighted with blue left border
- ★ marks starred/important features
- Bottom section: Quick Actions (Share WA, Share TG, Export PDF)
- Always visible, not collapsible

### Content Area

- Title + breadcrumb at top left
- Filter + Share buttons at top right
- Full width feature content below

---

## 3. Module Feature Map

### 🏠 Home (4 features)
1. **Command Center** — Executive Dashboard (landing page): KPIs (Brent, WTI, FX, VG30, AI Signal), Quick Actions grid, Recent Alerts, Stats (Deals, Tasks, Messages)
2. **Live Market** — Real-time market prices and charts
3. **Top Targets / Opportunities** — Auto-discovered profitable opportunities
4. **Live Alerts** — Color-coded alert feed (green/yellow/red)

### 💰 Pricing (6 features)
1. **Pricing Calculator ★** — 3-tier margin calculation (aggressive/balanced/premium), GST, transport
2. **Import Cost Model** — International + domestic landed cost breakdown
3. **Price Prediction** — 24-month forecast (1st & 16th cycle), dual-mode
4. **Manual Price Entry** — Manual IOCL/BPCL/HPCL price updates
5. **SOS Special Pricing** — Emergency/special pricing overrides
6. **Past Predictions** — Historical prediction accuracy tracking

### 🧾 Sales & CRM (8 features)
1. **CRM & Tasks ★** — Contact management, relationship scoring, task management
2. **Sales Workspace** — Quoting, objection handling, competitor response
3. **Negotiation Assistant** — AI-powered negotiation scripts and strategies
4. **Communication Hub** — WhatsApp/Email/Call message generation with templates
5. **CRM Automation** — Contact rotation, broadcasts, auto-reply, AI providers
6. **Daily Log** — Team daily activity logging
7. **Contacts Directory** — 25K+ contacts browser with search/filter
8. **Comm Tracking** — Communication analytics (messages sent, response rates)

### 🧠 Intelligence (8 features)
1. **Market Signals ★** — 10-signal composite AI intelligence visualization
2. **Real-time Insights** — Live KPIs, disruption alerts (Market Pulse Engine)
3. **News Intelligence** — Multi-source news with sentiment analysis
4. **Competitor Intel** — MEE bulletin parser, competitor price tracking
5. **Business Advisor** — WHAT/WHEN/FROM WHOM to buy/sell/hold
6. **Purchase Advisor** — Procurement urgency index from 6 real-time signals
7. **Recommendations** — Unified buy/sell/hold with confidence scores
8. **Global Markets** — Crude, bitumen, FX with date-range selectors

### 📄 Documents (5 features)
1. **Purchase Orders** — PO creation with FY numbering, auto-fill, email/WA send
2. **Sales Orders** — SO management with deal linkage
3. **Payment Orders** — Payment tracking with mode/status
4. **Party Master** — Supplier/Customer/Service provider master data
5. **PDF Archive** — Browse, search, download generated PDFs

### 🚚 Logistics (6 features)
1. **Maritime Intel** — Vessel tracking, port congestion, marine weather
2. **Supply Chain** — Shipment tracking: Iraq → Port → Tanker → Delivery → Payment
3. **Port Tracker** — Port import tracking with ETA and congestion data
4. **Feasibility** — Source comparison (PSU/import/decanter), distance matrix
5. **Ecosystem Management** — Supplier/transporter/terminal ecosystem view
6. **Refinery Supply** — Refinery production, capacity, supply outlook

### 📊 Reports (8 features)
1. **Financial Intelligence** — Shipment P&L, cashflow, receivable aging
2. **Strategy Panel** — Strategic sourcing/pricing/promotion recommendations
3. **Demand Analytics** — Contractor consumption, seasonal demand, predictive scoring
4. **Correlation Analysis** — Highway KM vs bitumen demand correlation
5. **Road Budget & Demand** — NHAI project pipeline, state-wise allocation
6. **Risk Scoring** — Multi-dimension risk dashboard (market, supply, financial, compliance)
7. **Export Reports** — Batch export to Excel/PDF
8. **Director Briefing** — Executive summary for MD/Director

### 🛡️ Compliance (5 features) — in "More ▾"
1. **Govt Data Hub** — Government contacts, tender portals, regulations
2. **GST & Legal Monitor** — GST compliance, legal updates, regulatory changes
3. **Alert System** — Configurable alerts for price, freight, margin, payment
4. **Change Log** — Version history and data change tracking
5. **Procurement Directory** — India bitumen & roads procurement directory (56+ entries)

### ⚙️ System & AI (12 features) — in "More ▾"
1. **AI Chatbot ★** — Trading chatbot with Claude/Ollama fallback
2. **AI Fallback Engine** — Multi-provider AI chain monitoring
3. **Knowledge Base** — Q&A browser + search (196+ entries)
4. **System Control** — Master control panel, scheduler, manual sync
5. **API Dashboard** — API health, status, configuration
6. **API Hub** — Normalized data tables browser (7 tables)
7. **Health Monitor** — System health (CPU, memory, disk, API)
8. **Settings** — Full settings management (API keys, preferences)
9. **Bug Tracker** — Bug report and tracking
10. **Developer Ops** — DevOps monitoring, change log, activity
11. **Dashboard Flow** — Architecture flowchart visualization
12. **AI Learning** — Learning dashboard from deal outcomes

---

## 4. Share System

### Per-Page Share Button

Every feature page has a "Share" button (top-right) with dropdown:
- 📱 **WhatsApp** — send summary to contact/group
- ✈️ **Telegram** — send to channel/group
- ✉️ **Email** — send as formatted email
- 📄 **PDF Download** — save as PDF locally
- 📋 **Copy Summary** — formatted text to clipboard
- ⏰ **Schedule Share** — set future date/time

### Share Message Format

**WhatsApp/Telegram** (compact):
```
🏛️ PPS ANANTAM — [Page Name]
[Date, Time IST]
━━━━━━━━━━━━━━
[Key data points, 5-8 lines]
━━━━━━━━━━━━━━
Generated by PPS Bitumen Dashboard
```

**Email/PDF** (detailed):
- Company header with logo
- Table format with all data
- Charts as images (Plotly PNG via kaleido)
- Footer: CONFIDENTIAL + data source + timestamp

### Share Center (Dedicated Page)

Tabs:
1. **Quick Share** — select data sources + recipients → send now
2. **Scheduled** — manage recurring shares (daily market update, weekly report)
3. **Templates** — saved share templates for common scenarios
4. **History** — log of all shares sent (channel, recipient, timestamp, status)
5. **Contacts** — manage share recipient lists per channel

---

## 5. Communication Engines

### WhatsApp (Existing — 360dialog API)
- HSM templates, 24h session window, opt-in tracking
- Queue-based background sending
- Delivery tracking and status
- Future: merge with WhatsApp Groups app for group automation

### Telegram (NEW — Bot API)
- **telegram_engine.py**: Bot API integration (free, unlimited messages)
- Channel posting for broadcast updates
- Group messaging support
- Send: text + PDF attachment + chart images
- Bot setup wizard in Settings page
- Queue-based sending with rate limiting

### Email (Existing — SMTP)
- 7 email types with templates
- Queue-based background sending
- Delivery tracking

### SMS (Existing — Fast2SMS)
- Transactional + promotional SMS
- 100/day free tier

---

## 6. UI Theme — Clean Modern White

### Color Tokens

| Token | Hex | Usage |
|---|---|---|
| Navy Dark | #0f172a | Top bar background |
| Blue Primary | #2563eb | Active states, CTAs, links |
| Green | #059669 | Positive values, BUY signal |
| Red | #dc2626 | Negative values, SELL signal, errors |
| Amber | #f59e0b | Warning, HOLD signal |
| Gold | #c9a84c | Brand accent (PPS logo, header) |
| White | #ffffff | Content background |
| Slate 50 | #f8fafc | Card backgrounds, sidebar |
| Slate 200 | #e2e8f0 | Borders, dividers |
| Slate 500 | #64748b | Muted text, labels |
| Slate 900 | #0f172a | Headings, primary text |

### Typography
- **Font:** Inter / Segoe UI / system
- **Headings:** 700-800 weight, #0f172a
- **Body:** 400 weight, #475569
- **Labels:** 10px uppercase, #64748b, letter-spacing 0.5px
- **Border-radius:** 8-10px everywhere

### Component Styles
- **Cards:** White bg, 1px #e2e8f0 border, no heavy shadows, hover: subtle lift
- **Buttons:** Primary = #2563eb bg white text, Secondary = #f1f5f9 bg #475569 text
- **Tables:** Alternating #f8fafc rows, sticky header
- **Charts:** Plotly with theme colors (blue, green, red, amber, purple)
- **Inputs:** White bg, #e2e8f0 border, 8px radius, focus: blue border
- **Sidebar:** #f8fafc bg, active item = blue left border + white bg

---

## 7. Command Center (Executive Dashboard)

Landing page — clean, focused, no clutter.

### Layout
```
┌─────────────────────────────────────────────┐
│ Greeting + Date/Time          [Share Button] │
├─────────────────────────────────────────────┤
│ [Brent] [WTI] [USD/INR] [VG30] [AI Signal] │  ← 5 KPI cards
├──────────────────────┬──────────────────────┤
│ ⚡ Quick Actions     │ 🔔 Recent Alerts     │
│ ┌────┐ ┌────┐       │ 🟢 IOCL revision...  │
│ │Calc│ │CRM │       │ 🟡 Crude rising...   │
│ └────┘ └────┘       │ 🔴 3 follow-ups...   │
│ ┌────┐ ┌────┐       │                      │
│ │Sig │ │Dir │       │                      │
│ └────┘ └────┘       │                      │
│ ┌────┐ ┌────┐       │                      │
│ │Chat│ │Share│      │                      │
│ └────┘ └────┘       │                      │
├──────────────────────┴──────────────────────┤
│ [Active Deals: 23] [Pending Tasks: 8] [Msgs: 47] │  ← Stats row
└─────────────────────────────────────────────┘
```

### Data Sources
- Brent/WTI: `hub_cache.json` (API Hub)
- USD/INR: `hub_cache.json`
- VG30: `live_prices.json`
- AI Signal: `tbl_purchase_advisor.json` (recommendation + urgency_index)
- Deals/Tasks: `crm_engine.py`
- Alerts: `market_pulse_engine.py` + `alert_system`
- Messages: `whatsapp_engine.py` + `telegram_engine.py` logs

---

## 8. Complete Feature Status Map

Every feature explicitly listed with status. Total: 64 features + 2 new pages + 1 new component.

### 🏠 Home (4 features)
| # | Feature | Status | Notes |
|---|---|---|---|
| 1 | Command Center | ✅ Working | Rewrite as Executive Dashboard |
| 2 | Live Market | ✅ Working | Theme update |
| 3 | Top Targets / Opportunities | ✅ Working | Theme update |
| 4 | Live Alerts | ✅ Working | Theme update |

### 💰 Pricing (6 features)
| # | Feature | Status | Notes |
|---|---|---|---|
| 5 | Pricing Calculator ★ | ✅ Working | Extract from dashboard.py inline code |
| 6 | Import Cost Model | ✅ Working | Theme update |
| 7 | Price Prediction | ✅ Working | Theme update |
| 8 | Manual Price Entry | ✅ Working | Theme update |
| 9 | SOS Special Pricing | ✅ Working | Theme update |
| 10 | Past Predictions | ✅ Working | Theme update |

### 🧾 Sales & CRM (8 features)
| # | Feature | Status | Notes |
|---|---|---|---|
| 11 | CRM & Tasks ★ | ✅ Working | Theme update |
| 12 | Sales Workspace | ✅ Working | Theme update |
| 13 | Negotiation Assistant | 🔨 Build | Complete engine + AI negotiation scripts UI |
| 14 | Communication Hub | ✅ Working | Theme update |
| 15 | CRM Automation | ✅ Working | Theme update |
| 16 | Daily Log | ✅ Working | Theme update |
| 17 | Contacts Directory | ✅ Working | Theme update, pagination for 25K+ contacts |
| 18 | Comm Tracking | 🔨 Build | Analytics dashboard for WA/Email/Call history |

### 🧠 Intelligence (8 features)
| # | Feature | Status | Notes |
|---|---|---|---|
| 19 | Market Signals ★ | ✅ Working | Theme update |
| 20 | Real-time Insights | ✅ Working | Theme update |
| 21 | News Intelligence | ✅ Working | Theme update |
| 22 | Competitor Intel | 🔨 Build | UI dashboard for MEE bulletins (engine complete) |
| 23 | Business Advisor | ✅ Working | Theme update |
| 24 | Purchase Advisor | ✅ Working | Theme update |
| 25 | Recommendations | ✅ Working | Theme update |
| 26 | Global Markets | ✅ Working | Theme update |

### 📄 Documents (5 features)
| # | Feature | Status | Notes |
|---|---|---|---|
| 27 | Purchase Orders | ✅ Working | Theme update |
| 28 | Sales Orders | ✅ Working | Theme update |
| 29 | Payment Orders | ✅ Working | Theme update |
| 30 | Party Master | ✅ Working | Theme update |
| 31 | PDF Archive | 🔨 Build | File browser + search + download UI |

### 🚚 Logistics (6 features)
| # | Feature | Status | Notes |
|---|---|---|---|
| 32 | Maritime Intel | 🔨 Build | Vessel tracking + port congestion UI |
| 33 | Supply Chain | ✅ Working | Theme update |
| 34 | Port Tracker | 🔨 Build | Port import tracking with ETA UI |
| 35 | Feasibility | ✅ Working | Theme update |
| 36 | Ecosystem Management | 🔨 Build | New: supplier/transporter/terminal cards |
| 37 | Refinery Supply | 🔨 Build | Refinery production + capacity dashboard |

### 📊 Reports (8 features)
| # | Feature | Status | Notes |
|---|---|---|---|
| 38 | Financial Intelligence | ✅ Working | Theme update |
| 39 | Strategy Panel | ✅ Working | Theme update |
| 40 | Demand Analytics | ✅ Working | Theme update |
| 41 | Correlation Analysis | ✅ Working | Theme update |
| 42 | Road Budget & Demand | ✅ Working | Theme update |
| 43 | Infra Demand Intelligence | 🔨 Build | Highway KM + tender matching (separate from Correlation) |
| 44 | Risk Scoring | 🔨 Build | Multi-dimension risk dashboard (engine complete) |
| 45 | Director Briefing | ✅ Working | Theme update, move from old Director module |

### 🛡️ Compliance (5 features) — in "More ▾"
| # | Feature | Status | Notes |
|---|---|---|---|
| 46 | Govt Data Hub | 🔨 Build | Govt contacts + tender portals UI |
| 47 | GST & Legal Monitor | 🔨 Build | Compliance monitoring UI |
| 48 | Alert System | 🔨 Build | Configurable alert rules UI (engine complete) |
| 49 | Change Log | 🔨 Build | Enhanced UI with filters (engine complete) |
| 50 | Procurement Directory | 🔨 Build | Polish UI + search/filter (engine complete) |

### ⚙️ System & AI (14 features) — in "More ▾"
| # | Feature | Status | Notes |
|---|---|---|---|
| 51 | AI Chatbot ★ | ✅ Working | Theme update |
| 52 | AI Fallback Engine | ✅ Working | Theme update |
| 53 | Knowledge Base | 🔨 Build | Q&A search + browse UI |
| 54 | System Control | ✅ Working | Theme update |
| 55 | API Dashboard | ✅ Working | Theme update |
| 56 | API Hub | ✅ Working | Theme update |
| 57 | Health Monitor | ✅ Working | Theme update |
| 58 | Settings | 🔨 Build | Extract from dashboard.py, full settings page |
| 59 | Bug Tracker | 🔨 Build | Bug report form + tracking list |
| 60 | Developer Ops | ✅ Working | Polish + integrate |
| 61 | Dashboard Flow Map | 🔨 Build | Architecture visualization |
| 62 | AI Learning | 🔨 Build | Learning metrics dashboard |
| 63 | AI Setup & Workers | ✅ Working | Theme update |
| 64 | Sync & Data Manager | ✅ Working | Theme update |

**Sidebar sub-grouping for System & AI (14 features):** Use section dividers:
- "AI" section: Chatbot, Fallback, Knowledge Base, AI Learning, AI Setup
- "System" section: Control, API Dashboard, API Hub, Health, Settings, Sync
- "Dev" section: Bug Tracker, Developer Ops, Flow Map

### New Pages (2) — accessed via top-bar icons + sidebar Quick Actions
| # | Feature | Access Point | Notes |
|---|---|---|---|
| 65 | Share Center | 📤 icon in top-bar + sidebar Quick Actions | Bulk share + scheduling + history |
| 66 | Telegram Dashboard | ✈️ icon in top-bar + System > Settings sub-page | Bot setup + channel management |

### New Components (1) — not a page, reusable widget
| Component | Location | Notes |
|---|---|---|
| Share Button | components/share_button.py | Replaces existing share_button.py in root. Per-page dropdown (WA/TG/Email/PDF/Copy) |

### Summary Count
- ✅ Working (theme update only): **39**
- 🔨 Need to Build: **25**
- New pages: **2**
- New components: **1**
- **Total: 66 items (64 features + 2 new pages)**

---

## 9. Migration Map (v4 → v5)

### Module Consolidation: 12 → 9

| v4 Module | v5 Destination | Notes |
|---|---|---|
| 🏠 Home | 🏠 Home | Kept |
| 📌 Director Briefing | 📊 Reports (Director Briefing feature) | Dissolved — Sales Calendar → removed (use CRM Tasks), Alert System → Compliance, Daily Log → Sales |
| 💰 Procurement | 💰 Pricing | Renamed |
| 🧾 Sales | 🧾 Sales & CRM | Kept |
| 📄 Documents | 📄 Documents | Kept |
| 🚚 Logistics | 🚚 Logistics | Kept |
| 🧠 Intelligence | 🧠 Intelligence | Kept |
| 🛡 Compliance | 🛡️ Compliance (More ▾) | Moved to overflow |
| 📊 Reports | 📊 Reports | Kept |
| ⚙ System Control | ⚙️ System & AI (More ▾) | Merged with Developer + AI |
| 🛠 Developer | ⚙️ System & AI (More ▾) | Merged into System & AI |
| 🤖 AI & Knowledge | ⚙️ System & AI (More ▾) | Merged into System & AI |

### Dropped/Consolidated Pages (v4 → v5)

| v4 Page | v5 Action | Reason |
|---|---|---|
| Sales Calendar | Merged into CRM & Tasks | Calendar view inside CRM |
| Discussion Guide | Merged into Negotiation Assistant | Same purpose |
| Contractor OSINT | Merged into Demand Analytics | Contractor data in one place |
| Business Intelligence | Merged into Recommendations | Overlapping scope |
| Source Directory | Merged into Procurement Directory | Same data |
| Email Setup | Merged into Settings | Channel setup under Settings |
| WhatsApp Setup | Merged into Settings | Channel setup under Settings |
| Integrations | Merged into Settings | API integrations under Settings |
| Contact Importer | Merged into Contacts Directory | Import tab inside Contacts |
| AI Assistant / AI Dashboard Assistant | Merged into AI Chatbot | One chatbot page |
| SRE Dashboard | Merged into Health Monitor | System health in one place |
| Ops Dashboard | Merged into Developer Ops | DevOps in one place |
| System Health | Merged into Health Monitor | Same scope |
| System Requirements | Merged into Settings | System info under Settings |
| Sync Status | Merged into Sync & Data Manager | Data management in one place |

### Migration Strategy for dashboard.py (5380 lines → 500 lines)

**Step 1: Extract inline page code**
- Pricing Calculator (~500 lines inline) → `pages/pricing/pricing_calculator.py`
- Other inline page sections → respective `pages/` files
- Each page file exports a single `render()` function

**Step 2: Extract CSS to theme.py**
- Move ~350 lines of inline CSS from dashboard.py to `theme.py`
- `theme.py` exports `inject_theme()` function using `st.markdown(css, unsafe_allow_html=True)`
- Update hardcoded colors in `top_bar.py` to use theme constants
- Remove Vastu CSS overrides (replaced by Clean White theme)

**Step 3: Slim the router**
- Keep: session state init, engine startup, nav rendering, page dispatch
- dispatch = simple dict mapping: `{"page_name": module.render}`
- Use `page_registry.py` pattern (decorator-based) if cleaner

**Step 4: Streamlit sidebar handling**
- Sidebar uses `st.sidebar` (Streamlit native)
- Hide collapse button via CSS: `button[kind="headerNoDivider"] { display: none }`
- Sidebar always shows sub-features of active module
- For System & AI (14 features): use section dividers (st.caption) for sub-groups

**Step 5: Engine directory**
- Move engine files to `engines/` subdirectory
- Update all import paths
- Sub-organize: `engines/ai/`, `engines/market/`, `engines/comm/` (optional, can be flat)

---

## 10. Future Integration Points

### WhatsApp Groups App (D:\rahul\whats app groups)
- **Stack:** Node.js + Express + whatsapp-web.js
- **Integration:** API bridge from dashboard → localhost:3010
- **Features:** Group automation, bulk send to groups
- **When:** After v5.0 stable

### CRM v2 (D:\rahul\New folder (3)\pps-bitumen-crm-v2-final\latest)
- **Stack:** React + Cloudflare Workers + D1
- **Integration:** API calls to pps-crm-api.pacpl-api.workers.dev
- **Features:** Deals pipeline, lead intelligence, campaign analytics
- **When:** After v5.0 stable

### Integration Architecture
```
Dashboard (Streamlit :8501)
    ├── API → WhatsApp Groups (Node.js :3010)
    ├── API → CRM v2 (Cloudflare Workers)
    └── Direct → Telegram Bot API
```

---

## 11. Non-Goals (Out of Scope)

- No framework migration (staying on Streamlit)
- No React/Angular frontend
- No mobile app
- No multi-user real-time collaboration
- No dark mode toggle (clean white only for now)
- No full automated test suite — but add a smoke test script (`test_smoke.py`) that imports each page module and verifies no import errors
