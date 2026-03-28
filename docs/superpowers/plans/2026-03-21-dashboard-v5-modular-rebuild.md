# PPS Bitumen Dashboard v5.0 — Modular Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Bitumen Sales Dashboard with clean modular architecture, Clean White theme, all 64 features working, and universal sharing to WhatsApp + Telegram + Email + PDF.

**Architecture:** Slim 500-line router (dashboard.py) dispatching to modular page files in pages/ directory. Business logic stays in existing engine files. Reusable UI components in components/. Single theme.py for CSS. Universal share_system.py for all sharing.

**Tech Stack:** Python 3.11, Streamlit, SQLite, Plotly, Telegram Bot API, 360dialog WhatsApp API, SMTP Email, ReportLab PDF

**Spec:** `docs/superpowers/specs/2026-03-21-dashboard-v5-modular-rebuild-design.md`

---

## Phase 1: Foundation (Theme + Router + Navigation)

### Task 1: Create Backup

**Files:**
- None modified — safety backup only

- [ ] **Step 1: Create full project backup**

```bash
cp -r "D:/rahul/sirs project/bitumen-sales-dashboard" "D:/rahul/sirs project/bitumen-sales-dashboard-BACKUP-v4-pre-rebuild"
```

- [ ] **Step 2: Verify backup**

```bash
ls "D:/rahul/sirs project/bitumen-sales-dashboard-BACKUP-v4-pre-rebuild/dashboard.py"
```
Expected: file exists

- [ ] **Step 3: Commit current state**

```bash
cd "D:/rahul/sirs project/bitumen-sales-dashboard"
git add -A
git commit -m "chore: snapshot v4.0 before v5.0 modular rebuild"
```

---

### Task 2: Create Directory Structure

**Files:**
- Create: `pages/` and all subdirectories
- Create: `components/`
- Create: `pages/__init__.py` and all sub-init files

- [ ] **Step 1: Create all directories**

```bash
cd "D:/rahul/sirs project/bitumen-sales-dashboard"
mkdir -p pages/home pages/pricing pages/sales pages/intelligence pages/documents pages/logistics pages/reports pages/compliance pages/system pages/sharing components
```

- [ ] **Step 2: Create __init__.py files**

Create empty `__init__.py` in: `pages/`, `pages/home/`, `pages/pricing/`, `pages/sales/`, `pages/intelligence/`, `pages/documents/`, `pages/logistics/`, `pages/reports/`, `pages/compliance/`, `pages/system/`, `pages/sharing/`, `components/`

- [ ] **Step 3: Commit**

```bash
git add pages/ components/
git commit -m "chore: create pages/ and components/ directory structure"
```

---

### Task 3: Create theme.py — Clean White Theme

**Files:**
- Create: `theme.py`

This is the single source of truth for all CSS. Replaces the ~350 lines of inline CSS in dashboard.py and the Vastu Design CSS.

- [ ] **Step 1: Create theme.py**

Create `theme.py` with:
- Color constants: NAVY_DARK = "#0f172a", BLUE_PRIMARY = "#2563eb", GREEN = "#059669", RED = "#dc2626", AMBER = "#f59e0b", GOLD = "#c9a84c", WHITE = "#ffffff", SLATE_50 = "#f8fafc", SLATE_200 = "#e2e8f0", SLATE_500 = "#64748b", SLATE_900 = "#0f172a"
- `inject_theme()` function that calls `st.markdown(CSS, unsafe_allow_html=True)` with:
  - Hide Streamlit header/toolbar/footer
  - Top bar styling (navy dark background)
  - Sidebar styling (#f8fafc bg, active item blue left border, hide collapse button)
  - Content area (white bg, Inter font)
  - Card styles (white bg, subtle border, hover lift)
  - Button styles (blue primary, slate secondary)
  - Table styles (alternating rows)
  - Input styles (white bg, slate border)
  - KPI card styles
  - Responsive breakpoints (1024px, 768px)

Reference current CSS from dashboard.py lines 191-1476 for structure, but replace all Vastu colors with Clean White palette.

- [ ] **Step 2: Test theme injection**

```python
# Quick test: add to dashboard.py temporarily
from theme import inject_theme
inject_theme()
```

Run `streamlit run dashboard.py` and verify the new theme applies without breaking existing pages.

- [ ] **Step 3: Commit**

```bash
git add theme.py
git commit -m "feat: add Clean White theme system (theme.py)"
```

---

### Task 4: Upgrade nav_config.py — 9 Modules

**Files:**
- Modify: `nav_config.py`

- [ ] **Step 1: Rewrite MODULE_NAV with 9 modules**

Replace current 12-module config with 9 modules. Each module has format:
```python
MODULE_NAV = {
    "🏠 Home": {
        "icon": "🏠", "label": "Home",
        "tabs": [
            {"label": "Command Center", "page": "🎯 Command Center"},
            {"label": "Live Market", "page": "🏠 Home"},
            {"label": "Top Targets", "page": "🔍 Opportunities"},
            {"label": "Live Alerts", "page": "🚨 Alert Center"},
        ]
    },
    # ... 8 more modules
}

OVERFLOW_MODULES = ["🛡️ Compliance", "⚙️ System & AI"]  # shown in "More ▾"
```

Map ALL 64 features to their modules. System & AI gets sub-groups via metadata.

Keep helper functions: `get_module_for_page()`, `get_subtab_idx_for_page()`, `get_default_page()`, `get_tabs()`.

Add new: `get_overflow_modules()`, `is_overflow_module()`.

For System & AI (14 features), add `sub_group` metadata:
```python
{"label": "AI Chatbot", "page": "💬 Trading Chatbot", "sub_group": "AI"},
{"label": "System Control", "page": "🎛️ System Control Center", "sub_group": "System"},
```

- [ ] **Step 2: Verify all page names match existing session_state dispatch**

Cross-check every `page` value in new nav_config against existing page dispatch in dashboard.py (the `if selected_page ==` blocks).

- [ ] **Step 3: Commit**

```bash
git add nav_config.py
git commit -m "feat: restructure nav_config to 9 modules with overflow"
```

---

### Task 5: Upgrade top_bar.py — Single Row + More Dropdown

**Files:**
- Modify: `top_bar.py`

- [ ] **Step 1: Rewrite render_top_bar()**

Replace current 2-row layout with single-row:
- Left: PPS logo + 7 module buttons (from SIDEBAR_ORDER minus OVERFLOW_MODULES)
- "More ▾" button that expands to show Compliance + System & AI
- Right: WhatsApp icon (📱), Telegram icon (✈️), Notification bell (🔔) with count badge, Search (🔍)
- Update all hardcoded colors from Vastu (NAVY #1e3a5f) to Clean White (NAVY_DARK #0f172a)
- Import colors from theme.py constants

- [ ] **Step 2: Add top-right icon click handlers**

WhatsApp icon → `st.session_state["_nav_goto"] = "📱 WhatsApp Setup"` (goes to Share Center WA tab)
Telegram icon → `st.session_state["_nav_goto"] = "✈️ Telegram Dashboard"`
Bell icon → `st.session_state["_nav_goto"] = "🚨 Alert Center"`
Search icon → toggle search bar visibility (`_search_visible` session state)

- [ ] **Step 3: Test**

Run `streamlit run dashboard.py`, verify single-row nav, More dropdown, icon clicks.

- [ ] **Step 4: Commit**

```bash
git add top_bar.py
git commit -m "feat: single-row top bar with More dropdown and action icons"
```

---

### Task 6: Upgrade subtab_bar.py — Sidebar-Based Sub-Features

**Files:**
- Modify: `subtab_bar.py`
- Modify: `dashboard.py` (sidebar section)

- [ ] **Step 1: Create render_sidebar_features() in subtab_bar.py**

New function that renders in `st.sidebar`:
- Module name header (small caps, muted)
- List all features of active module as buttons
- Active feature = white bg + blue left border
- ★ marks for starred features
- For System & AI: add section dividers using `st.caption("AI")`, `st.caption("System")`, `st.caption("Dev")`
- Bottom section: "Quick Actions" with Share WA, Share TG, Export PDF buttons

- [ ] **Step 2: Update dashboard.py sidebar section**

Replace existing sidebar code (lines ~1618-1637) with call to `render_sidebar_features(current_module)`.
Remove sidebar hiding CSS. Keep sidebar visible.
Hide collapse button via CSS.

- [ ] **Step 3: Test navigation**

Click module in top bar → sidebar updates with that module's features.
Click feature in sidebar → main content changes.

- [ ] **Step 4: Commit**

```bash
git add subtab_bar.py dashboard.py
git commit -m "feat: sidebar shows sub-features of active module"
```

---

### Task 7: Slim dashboard.py Router

**Files:**
- Modify: `dashboard.py` (major refactor)

This is the biggest task — extract inline page code and create a clean dispatch.

- [ ] **Step 1: Extract inline Pricing Calculator code**

Find the Pricing Calculator section in dashboard.py (~500 lines inline). Cut it out and create `pages/pricing/pricing_calculator.py` with a `render()` function. Replace the inline code with:
```python
if selected_page == "🧮 Pricing Calculator":
    from pages.pricing.pricing_calculator import render
    render()
```

Test that Pricing Calculator still works.

- [ ] **Step 2: Extract other inline page code**

Repeat for any other pages that have inline code in dashboard.py (check Home page, Sales Workspace, Communication Hub, etc.). Each gets a file in `pages/{category}/`.

For pages that already call `command_intel.X.render()`, keep as-is — just update the dispatch.

- [ ] **Step 3: Create page dispatch dict**

Replace 80+ `elif` branches with a clean dispatch:
```python
from pages.home.command_center import render as render_cc
# ... imports

PAGE_DISPATCH = {
    "🎯 Command Center": render_cc,
    "🏠 Home": render_home,
    "🧮 Pricing Calculator": render_pricing_calc,
    # ... all 64 features
}

# Dispatch
handler = PAGE_DISPATCH.get(selected_page)
if handler:
    handler()
else:
    st.warning(f"Page not found: {selected_page}")
```

- [ ] **Step 4: Add redirect aliases for dropped pages**

Add a redirect map for consolidated pages so old routes don't break:
```python
PAGE_REDIRECTS = {
    "📅 Sales Calendar": "🎯 CRM & Tasks",
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
    "🔄 Sync Status": "🔄 Sync & Data Manager",
    "🖥️ Ops Dashboard": "🛠️ Developer Ops Map",
}

# In dispatch: check redirects first
if selected_page in PAGE_REDIRECTS:
    selected_page = PAGE_REDIRECTS[selected_page]
```

- [ ] **Step 5: Clean up imports and engine startup**

Keep engine startup code (email_engine, whatsapp_engine, sync_engine, etc.) at top of dashboard.py.
Remove all inline CSS — replace with single `inject_theme()` call.
Remove old Vastu CSS block.

- [ ] **Step 5: Verify all pages still work**

Run dashboard, click through every module and feature. Check:
- Command Center loads
- Pricing Calculator works
- CRM works
- All working features render correctly

- [ ] **Step 6: Commit**

```bash
git add dashboard.py pages/
git commit -m "refactor: slim dashboard.py to 500-line router with page dispatch"
```

---

## Phase 2: Reusable Components

### Task 8: Create share_button.py Component

**Files:**
- Create: `components/share_button.py`
- Migrate: existing `share_button.py` (root) → `components/share_button.py`

- [ ] **Step 1: Create components/share_button.py**

```python
def render_share_button(page_name: str, data_fn: callable = None):
    """
    Renders a Share dropdown button.

    Args:
        page_name: Name of the current page (for message header)
        data_fn: Optional callable that returns dict with share data
                 {"summary": str, "table": pd.DataFrame, "chart": fig}
    """
```

Implement dropdown with 6 options using `st.popover("📤 Share")`:
- 📱 WhatsApp → calls share_system.share_whatsapp()
- ✈️ Telegram → calls share_system.share_telegram()
- ✉️ Email → calls share_system.share_email()
- 📄 PDF → calls pdf_export_engine.export_page_pdf()
- 📋 Copy → st.code() with copy button
- ⏰ Schedule Share → opens scheduler dialog (date/time picker + channel selector, saves to share_schedules.json)

- [ ] **Step 2: Create components/filter_bar.py**

```python
def render_date_filter(key_prefix: str) -> tuple[date, date]:
    """Date range filter with presets (Today, 7d, 30d, 90d, Custom)"""

def render_status_filter(key_prefix: str, options: list) -> list:
    """Multi-select status filter"""

def render_region_filter(key_prefix: str) -> list:
    """Region/state filter for India"""
```

- [ ] **Step 3: Create components/kpi_card.py**

```python
def render_kpi_card(label: str, value: str, change: str = None,
                    change_color: str = "green", icon: str = ""):
    """Renders a KPI metric card in Clean White style"""
```

Uses `st.markdown()` with theme colors. Shows label, big value, change indicator.

- [ ] **Step 4: Create components/data_table.py**

```python
def render_data_table(df: pd.DataFrame, key: str,
                      searchable: bool = True, exportable: bool = True):
    """Filterable, searchable data table with export options"""
```

Adds search box above table, pagination for large datasets (25K+ rows), export buttons.

- [ ] **Step 5: Create components/chart_card.py**

```python
def render_chart_card(fig, title: str, page_name: str = "",
                      downloadable: bool = True, shareable: bool = True):
    """Chart wrapper with download PNG + share buttons"""
```

Wraps a Plotly figure with:
- Title header
- Plotly chart (st.plotly_chart)
- Download PNG button (fig.to_image via kaleido)
- Share button (uses share_button component)

- [ ] **Step 6: Commit**

```bash
git add components/
git commit -m "feat: add reusable UI components (share_button, filter_bar, kpi_card, data_table, chart_card)"
```

---

### Task 9: Create telegram_engine.py

**Files:**
- Create: `telegram_engine.py`

NOTE: This must come before share_system.py since share_system imports telegram_engine.

- [ ] **Step 1: Create telegram_engine.py**

```python
"""Telegram Bot API integration for PPS Bitumen Dashboard"""
import json, requests
from pathlib import Path
from datetime import datetime

_SETTINGS_FILE = Path(__file__).parent / "telegram_settings.json"

def _load_settings() -> dict:
    """Load bot token, chat IDs from settings file"""

def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> dict:
    """Send text message via Bot API"""

def send_document(chat_id: str, file_bytes: bytes, filename: str, caption: str = "") -> dict:
    """Send PDF/file via Bot API"""

def send_photo(chat_id: str, image_bytes: bytes, caption: str = "") -> dict:
    """Send chart image via Bot API"""

def get_updates(offset: int = 0) -> list:
    """Get incoming messages (for bot setup verification)"""

def verify_bot(token: str) -> dict:
    """Verify bot token is valid, return bot info"""

def get_chat_list() -> list:
    """Get list of known chats/channels from settings"""
```

Uses `requests` (already in dependencies). Settings file at project root (not `data/` — that directory doesn't exist).

- [ ] **Step 2: Commit**

```bash
git add telegram_engine.py
git commit -m "feat: add Telegram Bot API engine"
```

---

### Task 10: Create share_system.py

**Files:**
- Create: `share_system.py`

- [ ] **Step 1: Create share_system.py**

```python
"""Universal sharing system for WhatsApp, Telegram, Email, PDF"""

def format_message(page_name: str, data: dict, format: str = "compact") -> str:
    """Format data as shareable message.
    format: 'compact' (WA/TG) or 'detailed' (Email/PDF)
    """

def share_whatsapp(page_name: str, data: dict, recipient: str = None):
    """Send via WhatsApp engine (360dialog API)"""

def share_telegram(page_name: str, data: dict, chat_id: str = None):
    """Send via Telegram Bot API"""

def share_email(page_name: str, data: dict, to: list = None):
    """Send via Email engine (SMTP)"""

def share_pdf(page_name: str, data: dict) -> bytes:
    """Generate PDF and return bytes for download"""

def log_share(channel: str, page: str, recipient: str, status: str):
    """Log share event to share_history.json"""

def get_share_history(limit: int = 100) -> list:
    """Get recent share history"""
```

Compact format (WA/TG):
```
🏛️ PPS ANANTAM — {page_name}
{date}, {time} IST
━━━━━━━━━━━━━━
{key data points}
━━━━━━━━━━━━━━
Generated by PPS Bitumen Dashboard
```

- [ ] **Step 2: Commit**

```bash
git add share_system.py
git commit -m "feat: add universal share system (WA/TG/Email/PDF)"
```

---

## Phase 3: Command Center Rebuild

### Task 11: Rebuild Command Center as Executive Dashboard

**Files:**
- Create: `pages/home/command_center.py`
- Modify: `command_intel/command_center_home.py` (reference, then replace)

- [ ] **Step 1: Create pages/home/command_center.py**

New clean Command Center with:
- Greeting header + date/time + Share Dashboard button
- 5 KPI cards row: Brent, WTI, USD/INR, VG30, AI Signal
- 2-column: Quick Actions grid (6 cards) + Recent Alerts list
- Stats row: Active Deals, Pending Tasks, Messages Sent

Use `components/kpi_card.py` for KPI cards.
Use `components/share_button.py` for Share button.

Data sources:
- Brent/WTI/FX: load from `hub_cache.json`
- VG30: load from `live_prices.json`
- Signal: load from `tbl_purchase_advisor.json`
- Alerts: load from `market_alerts.json` (via market_pulse_engine)
- Deals/Tasks: load from `crm_engine`

Quick Action cards navigate via `st.session_state["_nav_goto"]`:
- 🧮 Price Calc → "🧮 Pricing Calculator"
- 🎯 CRM → "🎯 CRM & Tasks"
- 📡 Signals → "📡 Market Signals"
- 📋 Director Brief → "📋 Director Briefing"
- 💬 AI Chat → "💬 Trading Chatbot"
- 📤 Share Center → Share Center page

- [ ] **Step 2: Remove ticker from CC**

CC is now executive dashboard — no ticker. Ticker can be added to Live Market page if needed.

- [ ] **Step 3: Update dashboard.py dispatch**

Point "🎯 Command Center" to new `pages/home/command_center.render()`.

- [ ] **Step 4: Test**

Run dashboard, verify CC loads as clean executive dashboard with working KPIs.

- [ ] **Step 5: Commit**

```bash
git add pages/home/command_center.py dashboard.py
git commit -m "feat: rebuild Command Center as Executive Dashboard"
```

---

## Phase 4: Complete Skeleton Features (25 features)

Each task below completes one skeleton feature. Pattern for each:
1. Check if engine exists and is complete
2. If skeleton engine → complete the engine logic
3. Create/update the UI page with proper rendering
4. Add share button + local filters
5. Test and commit

### Task 12: Sales — Negotiation Assistant

**Files:**
- Modify: `negotiation_engine.py` (complete skeleton)
- Create: `pages/sales/negotiation.py`

- [ ] **Step 1: Complete negotiation_engine.py**

Add functions:
- `get_negotiation_script(customer_type, product, scenario)` → returns script with talking points
- `get_objection_responses(objection_category)` → returns counter-arguments
- `get_price_justification(source, price, market_data)` → returns why this price is fair
- Use business_knowledge_base.py and sales_knowledge_base.py for content

- [ ] **Step 2: Create pages/sales/negotiation.py**

UI with tabs:
1. Script Generator — select customer type, product, scenario → get AI script
2. Objection Handler — browse/search objection responses
3. Price Justification — enter price + source → get market-backed justification
4. Tips & Scripts — reference library from sales_knowledge_base

Add share button (share scripts to WA/TG).

- [ ] **Step 3: Test and commit**

---

### Task 13: Sales — Comm Tracking

**Files:**
- Modify: `command_intel/comm_tracking_dashboard.py` (complete skeleton)
- Create: `pages/sales/comm_tracking.py`

- [ ] **Step 1: Complete comm_tracking_dashboard.py**

Dashboard showing:
- Total messages sent (WA/Email/SMS breakdown)
- Daily/weekly/monthly charts (Plotly bar charts)
- Response rates
- Top contacts by communication volume
- Channel effectiveness comparison

Data from: `whatsapp_engine` logs, `email_engine` logs, `sms_engine` logs

- [ ] **Step 2: Add filters (date range, channel type) and share button**

- [ ] **Step 3: Test and commit**

---

### Task 14: Intelligence — Competitor Intel

**Files:**
- Create: `pages/intelligence/competitor_intel.py`

- [ ] **Step 1: Create competitor intel dashboard**

Uses existing `competitor_intelligence.py` engine (complete). Build UI:
- Latest MEE bulletin display (parsed WhatsApp text)
- Competitor price comparison table
- Price trend chart (our price vs competitor)
- Market share indicators

- [ ] **Step 2: Add filters and share button**

- [ ] **Step 3: Test and commit**

---

### Task 15: Intelligence — Infra Demand

**Files:**
- Modify: `command_intel/infra_demand_dashboard.py` (complete skeleton)

- [ ] **Step 1: Complete infra demand dashboard**

UI showing:
- Highway KM data by state (bar chart)
- Active tenders matching bitumen demand
- NHAI project pipeline
- Demand heat map by region
- Seasonal demand patterns

Data from: `tbl_highway_km.json`, `tbl_demand_proxy.json`, correlation_engine

- [ ] **Step 2: Add filters (state, year) and share button**

- [ ] **Step 3: Test and commit**

---

### Task 16: Documents — PDF Archive

**Files:**
- Modify: `command_intel/pdf_archive.py` (complete skeleton)

- [ ] **Step 1: Complete PDF archive page**

- File browser showing all PDFs in `pdf_exports/` directory
- Search by filename, date
- Sort by date (newest first)
- Download button per file
- Preview (show first page info)
- Bulk delete option

- [ ] **Step 2: Test and commit**

---

### Task 17: Logistics — Maritime Intel

**Files:**
- Modify: `command_intel/maritime_logistics_dashboard.py` (complete skeleton)

- [ ] **Step 1: Complete maritime dashboard**

Uses `maritime_intelligence_engine.py` (complete). Build UI:
- Vessel tracking table (vessel name, status, ETA, origin, destination)
- Port congestion indicators
- Marine weather alerts
- Route map placeholder (text-based route display)
- Freight rate trends

- [ ] **Step 2: Add filters and share button**

- [ ] **Step 3: Test and commit**

---

### Task 18: Logistics — Port Tracker

**Files:**
- Modify: `command_intel/port_tracker_dashboard.py` (complete skeleton)

- [ ] **Step 1: Complete port tracker**

Uses `port_tracker_engine.py`. Build UI:
- Port-wise import volumes (bar chart)
- Active shipments with ETA
- Port congestion status (green/yellow/red)
- Historical volume trends
- Customs clearance status

- [ ] **Step 2: Test and commit**

---

### Task 19: Logistics — Ecosystem Management

**Files:**
- Create: `pages/logistics/ecosystem.py`

- [ ] **Step 1: Create ecosystem management page**

Card-based view of business ecosystem:
- Suppliers section (refineries, importers, manufacturers) — from party_master data
- Transporters section — from `purchase_parties.json`
- Terminals & Ports — from `tbl_ports_master.json`
- Service providers — from `service_providers.json`

Each card shows: name, type, location, contact, last transaction date.
Search and filter by type/region.

- [ ] **Step 2: Test and commit**

---

### Task 20: Logistics — Refinery Supply

**Files:**
- Modify: `command_intel/refinery_supply_dashboard.py` (complete skeleton)

- [ ] **Step 1: Complete refinery supply dashboard**

- Refinery list with production capacity
- Current supply status (normal/tight/surplus)
- PSU price circulars (IOCL, BPCL, HPCL)
- Price revision history chart
- Supply risk indicators

Data from: `source_master.py`, `live_prices.json`, hub_cache

- [ ] **Step 2: Test and commit**

---

### Task 21: Reports — Risk Scoring

**Files:**
- Modify: `command_intel/risk_scoring.py` (engine complete, UI skeleton)

- [ ] **Step 1: Complete risk scoring dashboard UI**

Uses existing risk_scoring engine. Build:
- Overall business health score (gauge/meter)
- 6 risk dimensions as cards (Market, Supply, Financial, Compliance, Legal, Margin)
- Each dimension: score (0-100), trend arrow, key factors
- Historical risk trend chart
- Risk alerts list

- [ ] **Step 2: Add share button**

- [ ] **Step 3: Test and commit**

---

### Task 22: Reports — Export Reports + Director Briefing

**Files:**
- Create: `pages/reports/export_reports.py`
- Reference: `command_intel/director_dashboard.py` (working, just wire up)

- [ ] **Step 1: Create export reports page**

Batch export interface:
- Checkbox list of available reports
- Format selector (PDF / Excel / Both)
- Date range for report data
- "Export Selected" button → generates zip of selected reports
- Recent exports list

- [ ] **Step 2: Wire Director Briefing**

Ensure `command_intel/director_dashboard.py` is in dispatch map under Reports module.

- [ ] **Step 3: Test and commit**

---

### Task 23: Compliance — All 5 Features

**Files:**
- Modify: `command_intel/govt_hub_dashboard.py`
- Modify: `command_intel/gst_legal_monitor.py`
- Modify: `command_intel/alert_system.py`
- Modify: `command_intel/change_log.py`
- Modify: `command_intel/directory_dashboard.py`

- [ ] **Step 1: Complete Govt Data Hub**

- Government officer directory (searchable table)
- Tender portal links (clickable cards)
- Recent government notifications
- NHAI/MoRTH updates feed

- [ ] **Step 2: Complete GST & Legal Monitor**

- Current GST rates for bitumen products
- Input credit rules summary
- Recent legal/regulatory updates
- Compliance checklist

- [ ] **Step 3: Complete Alert System UI**

Engine is complete (`alert_system.py`). Build config UI:
- Alert rules list (add/edit/delete)
- Alert types: price_change, margin_warning, payment_due, freight_spike
- Threshold config per rule
- Notification channel (WA/TG/Email)
- Alert history log

- [ ] **Step 4: Enhance Change Log UI**

Engine complete. Add:
- Filter by date range, category, user
- Search in change descriptions
- Export change log

- [ ] **Step 5: Polish Procurement Directory**

Engine complete. Add:
- Full-text search across all directory entries
- Filter by state, org type, category
- Card view + table view toggle
- Share directory entry to WA/TG

- [ ] **Step 6: Test all 5 and commit**

---

### Task 24: System & AI — All Skeleton Features

**Files:**
- Modify: `command_intel/` various files
- Create: `pages/system/knowledge_base.py`
- Create: `pages/system/settings.py`
- Create: `pages/system/bug_tracker.py`

- [ ] **Step 1: Complete Knowledge Base**

- Browse 196+ Q&A entries from `qa_*.json`
- Search by keyword
- Category filter (pricing, logistics, market, etc.)
- Expandable Q&A cards
- "Ask AI" button → routes to AI Chatbot

- [ ] **Step 2: Complete Settings page**

Extract from dashboard.py's settings section. Organize as tabs:
- General: Company info, timezone, currency
- API Keys: WhatsApp (360dialog), Telegram Bot, Email SMTP, Claude API, OpenAI
- Notifications: Alert preferences, channels
- Sharing: Default recipients, scheduled shares
- AI: Provider priority, model selection, fallback chain config
- System: Sync frequency, cache TTL, data retention

- [ ] **Step 3: Complete Bug Tracker**

- Bug report form (title, description, severity, steps to reproduce)
- Bug list with status (Open, In Progress, Resolved)
- Filter by severity, status
- Resolution notes

- [ ] **Step 4: Complete Dashboard Flow Map**

- Text-based architecture diagram (mermaid-style rendered as HTML)
- Module dependency graph
- Data flow visualization
- File count per directory

- [ ] **Step 5: Complete AI Learning dashboard**

- Learning metrics from `ai_learned_weights.json`
- Prediction accuracy over time
- Signal weight adjustments
- Deal outcome analysis

- [ ] **Step 6: Test all and commit**

---

## Phase 5: Share Center + Telegram Dashboard

### Task 25: Create Share Center Page

**Files:**
- Create: `pages/sharing/share_center.py`

- [ ] **Step 1: Create Share Center with 5 tabs**

Tab 1 — Quick Share:
- Checkbox list of data sources (Market Signals, Prices, Director Brief, etc.)
- Recipient selector (WA contacts, TG channels, email lists)
- "Send Now" button
- Preview before send

Tab 2 — Scheduled:
- List of scheduled shares (daily market update, weekly report)
- Add new schedule (data source, channel, frequency, time)
- Enable/disable toggle
- Uses `share_automation_engine.py`

Tab 3 — Templates:
- Saved message templates
- Create/edit/delete templates
- Template preview

Tab 4 — History:
- Share history from `share_history.json`
- Filter by channel, date, status
- Resend button

Tab 5 — Contacts:
- Manage recipient lists per channel
- WA contacts, TG chat IDs, Email addresses
- Import from CRM contacts

- [ ] **Step 2: Wire into navigation**

Add Share Center to dispatch. Accessible via:
- 📤 icon in top bar
- Sidebar Quick Actions
- CC Quick Actions grid

- [ ] **Step 3: Test and commit**

---

### Task 26: Create Telegram Dashboard

**Files:**
- Create: `pages/sharing/telegram_dashboard.py`

- [ ] **Step 1: Create Telegram Dashboard**

Tabs:
1. Setup — Bot token input, verify button, bot info display
2. Channels — List of channels/groups, add new, test send
3. Send — Manual message compose + send
4. Logs — Delivery history
5. Settings — Rate limits, default parse mode, auto-send rules

- [ ] **Step 2: Wire into navigation**

Accessible via ✈️ icon in top bar and Settings > Telegram.

- [ ] **Step 3: Test and commit**

---

## Phase 6: Integration & Polish

### Task 27: Add Share Button to Every Page

**Files:**
- Modify: All page files in `pages/` and `command_intel/`

- [ ] **Step 1: Add share_button to all working pages**

For each page, add at the top:
```python
from components.share_button import render_share_button

def render():
    col1, col2 = st.columns([8, 2])
    with col1:
        st.markdown("## Page Title")
    with col2:
        render_share_button("Page Name", data_fn=get_page_data)
    # ... rest of page
```

Where `get_page_data()` returns the key data for sharing.

Do this for all 64 feature pages.

- [ ] **Step 2: Test share from 5 different pages**

- [ ] **Step 3: Commit**

---

### Task 28: Add Local Filters to Key Pages

**Files:**
- Modify: Key pages that need filtering

- [ ] **Step 1: Add date filter to time-series pages**

Pages: Financial Intel, Demand Analytics, Price Prediction, Market Signals, Correlation, News Intel

```python
from components.filter_bar import render_date_filter
start, end = render_date_filter("page_prefix")
```

- [ ] **Step 2: Add status/category filters**

Pages: CRM Tasks (status filter), Alerts (severity filter), Bug Tracker (status filter), Contacts (region filter)

- [ ] **Step 3: Test and commit**

---

### Task 29: Smoke Test Script

**Files:**
- Create: `test_smoke.py`

- [ ] **Step 1: Create test_smoke.py**

```python
"""Smoke test — verify all page modules import without errors"""
import importlib
import sys

PAGES = [
    "pages.home.command_center",
    "pages.pricing.pricing_calculator",
    # ... all 64+ page modules
]

errors = []
for page in PAGES:
    try:
        importlib.import_module(page)
        print(f"✅ {page}")
    except Exception as e:
        errors.append((page, str(e)))
        print(f"❌ {page}: {e}")

if errors:
    print(f"\n{len(errors)} FAILURES")
    sys.exit(1)
else:
    print(f"\n✅ All {len(PAGES)} pages import OK")
```

- [ ] **Step 2: Run smoke test**

```bash
cd "D:/rahul/sirs project/bitumen-sales-dashboard"
python test_smoke.py
```

Fix any import errors.

- [ ] **Step 3: Commit**

---

### Task 30: Final Polish & Cleanup

**Files:**
- Various cleanup across project

- [ ] **Step 1: Remove old CSS from dashboard.py**

Delete the ~350 lines of Vastu CSS. Only `inject_theme()` call remains.

- [ ] **Step 2: Update .streamlit/config.toml**

Set Streamlit theme to white base:
```toml
[theme]
base = "light"
primaryColor = "#2563eb"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8fafc"
textColor = "#0f172a"
font = "sans serif"
```

- [ ] **Step 3: Test full flow**

1. Open dashboard → CC loads as Executive Dashboard
2. Click every module in top bar → sidebar updates
3. Click every feature → page loads
4. Test share from 3 pages (WA, TG, PDF)
5. Test filters on 3 pages
6. Open Share Center → all tabs work
7. Open Telegram Dashboard → setup works

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: PPS Bitumen Dashboard v5.0 — Modular Rebuild complete"
```

---

## Summary

| Phase | Tasks | Effort |
|---|---|---|
| 1. Foundation | Tasks 1-7 | Theme + Router + Nav |
| 2. Components | Tasks 8-10 | Share, Filter, KPI, Table, Telegram |
| 3. CC Rebuild | Task 11 | Executive Dashboard |
| 4. Features | Tasks 12-24 | 25 skeleton → working |
| 5. Share Pages | Tasks 25-26 | Share Center + TG Dashboard |
| 6. Polish | Tasks 27-30 | Integration + Testing |

**Total: 30 tasks across 6 phases**

---

## Deferred Items (Post v5.0)

1. **Move engines to `engines/` directory** — Spec mentions this but too risky mid-rebuild. Engine files stay in root for now. Can reorganize after v5.0 is stable.
2. **WhatsApp Dashboard page** (`pages/sharing/whatsapp_dashboard.py`) — WhatsApp setup is handled under Settings for now. Dedicated dashboard can come later when WhatsApp Groups app merges.
3. **`page_registry.py` decorator pattern** — Existing file in root. Can adopt after slim router is working.
4. **Working features inline style cleanup** — `inject_theme()` CSS overrides handle 95% of styling. Any remaining hardcoded Vastu colors in `command_intel/` files should be fixed file-by-file as they're touched in Phase 4+. Not worth a dedicated sweep.
5. **MODULE_ROLE_MAP update** — Update in Task 4 alongside nav_config restructuring (add to Step 1 scope).
