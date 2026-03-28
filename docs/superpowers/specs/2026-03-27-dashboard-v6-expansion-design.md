# PPS Anantam Bitumen Dashboard v6.0 — Expansion Design Spec

**Date:** 2026-03-27
**Author:** Claude + Rahul
**Status:** Approved
**Scope:** 5 waves — gap fixes, communication, new features, client-facing, polish & deploy

---

## Context

Dashboard v5.0 is production-ready with 80+ pages, 60+ engines, 9 modules. However:
- 3 page directories are empty stubs (Reports, Documents, Compliance)
- 4 communication channels are disabled (Email, WhatsApp, Chat, Share Links)
- 7 roadmap features not started
- No client-facing shareable pages or subscription model
- Mobile responsiveness and UI consistency need work
- Not deployed to cloud

This spec covers everything needed to take v5.0 → v6.0.

---

## Architecture Principles

- **Reuse existing engines.** Most command_intel dashboards and root engines already exist. New pages are wrappers/routers.
- **SQLite remains the database.** New tables added for credit, e-way bills, tenders, tankers, shared links, chat.
- **Theme consistency.** All new pages use v5 Clean SaaS Light (Indigo #4F46E5, white cards, Inter font).
- **Lazy imports.** All new pages follow `__import__` pattern from dashboard.py.
- **Mobile-first CSS.** All new CSS includes `@media` breakpoints at 768px and 480px.

---

## Wave 1: Fix Gaps (Existing Incomplete Pages)

### 1.1 Reports Module (`pages/reports/`)

Currently a stub handler that shows "success". Needs 8 real page files, each wrapping an existing command_intel module.

| Page File | Wraps | command_intel Module |
|-----------|-------|---------------------|
| `financial.py` | Financial P&L, cashflow, receivable aging | `financial_intel.py` |
| `strategy.py` | Trade recommendations with confidence | `strategy_panel.py` |
| `demand.py` | State-wise demand heatmap, contractor profiles | `demand_analytics.py` |
| `correlation.py` | Highway KM vs Bitumen demand regression | `correlation_dashboard.py` |
| `road_budget.py` | NHAI project pipeline, state allocation | `road_budget_dashboard.py` (enhance from 97 lines) |
| `risk.py` | 6-risk composite health score | `risk_scoring.py` |
| `export_reports.py` | One-click PDF/Excel export of any report | `pdf_export_engine.py` |
| `director_brief.py` | Daily auto-generated exec summary | `director_dashboard.py` |

**Data dependency:** Populate `tbl_highway_km.json` with NHAI state-wise data (28 states) for road_budget.

**Nav update:** Wire all 8 pages in `nav_config.py` Reports module and `dashboard.py` PAGE_DISPATCH.

### 1.2 Documents Module (`pages/documents/`)

5 page files wrapping `document_management.py` (1411 lines, already complete with tabs).

| Page File | Tab/Function |
|-----------|-------------|
| `purchase_orders.py` | PO tab from document_management |
| `sales_orders.py` | SO tab |
| `payment_orders.py` | Payment tab |
| `party_master.py` | Party Master from `party_master.py` engine |
| `pdf_archive.py` | PDF browser from `pdf_archive.py` |

**Approach:** Each page file calls the relevant render function from command_intel. document_management.py already handles FY-based numbering (FY2526/PO/0001), email/WhatsApp send buttons.

### 1.3 Compliance Module (`pages/compliance/`)

5 page files wrapping existing command_intel modules.

| Page File | Wraps |
|-----------|-------|
| `govt_hub.py` | `govt_hub_dashboard.py` |
| `gst_legal.py` | `gst_legal_monitor.py` |
| `alert_system.py` | `alert_system.py` |
| `change_log.py` | `change_log.py` |
| `procurement_dir.py` | `directory_dashboard.py` |

### 1.4 Thin Dashboard Enhancements

**`data_manager_dashboard.py` (60 → ~200 lines):**
- Add real file upload (Excel/CSV) with pandas validation
- Wire to `sync_engine.py` for data sync
- Show last sync status, row counts, data quality score from `data_confidence_engine.py`

**`contacts_directory_dashboard.py` (82 → ~200 lines):**
- Populate `tbl_contacts.json` from seed_data.py's `tbl_contacts` table
- Add search by name/city/state, filter by category (buyer/seller/transporter)
- Add export to Excel button
- Wire to `contact_importer.py` for bulk import

**`road_budget_dashboard.py` (97 → ~250 lines):**
- Populate `tbl_highway_km.json` with 28-state NHAI data
- Add Plotly bar chart (state-wise km), pie chart (zone distribution)
- Add budget-to-demand correlation section from `road_budget_demand.py`

---

## Wave 2: Communication Channels

### 2.1 WhatsApp Integration

**Engine:** `whatsapp_engine.py` — 360dialog API, phone validation, queue, 20/min rate limit.
**Setup UI:** `whatsapp_setup_dashboard.py` — config, templates, send, log, opt-in, rate limits.

**Changes needed:**
- Enable WhatsApp toggle in `comm_tracking_dashboard.py` (line ~307)
- Wire all "Send WhatsApp" buttons across pages to call `whatsapp_engine.send_message()`
- Add delivery status tracking: sent → delivered → read (webhook endpoint in FastAPI)
- Add broadcast function for price updates to customer segments

**Pages affected:** Pricing Calculator, Director Cockpit Step 4, Negotiation, Comm Hub, Share Center.

### 2.2 Email Integration

**Engine:** `email_engine.py` — SMTP + SendGrid, 5 types, 50/hr rate limit.
**Setup UI:** `email_setup_dashboard.py` — SMTP config, recipients, send, log, schedule.

**Changes needed:**
- Enable Email toggle in `comm_tracking_dashboard.py` (line ~289)
- Wire "Send Email" buttons to `email_engine.send_email()`
- New: **Drip Campaign Scheduler**
  - 5-touch sequence: Day 0 (Intro offer) → Day 3 (Rate card) → Day 7 (Case study) → Day 14 (Special offer) → Day 30 (Check-in)
  - Templates from `communication_engine.py` (already has 5-touch logic)
  - New `drip_campaigns` table: campaign_id, customer_id, step (1-5), scheduled_at, sent_at, status
  - Scheduler: runs every 2 hours via `sync_engine.py` pattern, sends due emails

### 2.3 Client Chat

**New page:** `command_intel/client_chat_dashboard.py`

**Sections:**
- Chat inbox (list of active conversations)
- Chat window (Streamlit `chat_input` + `chat_message`)
- Auto-reply using `trading_chatbot_engine.py` (simplified for customer queries)
- Log every message to CRM as "Chat" channel

**New SQLite table:**
```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    customer_name TEXT,
    direction TEXT,  -- 'inbound' or 'outbound'
    message TEXT,
    timestamp TEXT,
    auto_replied BOOLEAN DEFAULT 0
);
```

**Enable:** Toggle in `comm_tracking_dashboard.py` (line ~340).

### 2.4 Shareable Links

**New engine:** `shareable_links_engine.py`

**How it works:**
1. User clicks "Share" on any quote/report/showcase
2. Engine generates unique token (UUID4), stores mapping in SQLite
3. Returns URL: `http://host:port/share/{token}`
4. FastAPI endpoint serves read-only HTML content
5. Auto-expires after 24 hours (configurable)

**New SQLite table:**
```sql
CREATE TABLE shared_links (
    id INTEGER PRIMARY KEY,
    token TEXT UNIQUE,
    content_type TEXT,  -- 'quote', 'report', 'showcase', 'rate_card'
    content_json TEXT,
    created_at TEXT,
    expires_at TEXT,
    views INTEGER DEFAULT 0,
    created_by TEXT
);
```

**FastAPI route:** Add to `quotation_system/api.py` — `GET /share/{token}` returns rendered HTML.

**Integration:** Add "Get Link" button to Share Center, Director Cockpit, Client Showcase.

---

## Wave 3: New Features

### 3.1 Profitability Analytics

**New files:**
- `command_intel/profitability_dashboard.py` (~400 lines)
- `pages/reports/profitability.py` (wrapper)

**Sections:**
1. **Deal P&L Table** — revenue, landed cost, transport, GST, margin per deal. Sortable. Color-coded (green = profitable, red = loss).
2. **Customer Ranking** — Top 20 customers by total margin. Bar chart.
3. **Route Profitability** — Source → Destination heatmap. Which routes make money?
4. **Monthly Trend** — Revenue/Cost/Margin line chart (Plotly). Last 12 months.

**Data source:** `deals` table in SQLite + `calculation_engine.py` for cost computation.

**Nav:** Add to Reports module.

### 3.2 Credit Limit & Aging Warning

**New files:**
- `command_intel/credit_aging_dashboard.py` (~350 lines)
- `credit_engine.py` (~150 lines)

**New SQLite table:**
```sql
CREATE TABLE credit_limits (
    id INTEGER PRIMARY KEY,
    customer_id TEXT,
    customer_name TEXT,
    credit_limit REAL DEFAULT 0,
    outstanding REAL DEFAULT 0,
    last_payment_date TEXT,
    status TEXT DEFAULT 'active'
);
```

**Sections:**
1. **KPI Row** — Total outstanding, overdue amount, customers at risk, average days outstanding
2. **Customer Credit Table** — Limit, used, available, aging bucket (0-30, 31-60, 61-90, 90+). Color-coded.
3. **Overdue Alerts** — Auto-generate P0 alert when customer >80% credit or >60 days overdue (wire to `alert_center.py`)
4. **Payment History** — Timeline per customer

**Nav:** Add to Sales & CRM module.

### 3.3 E-Way Bill Automation

**New files:**
- `command_intel/eway_bill_dashboard.py` (~300 lines)
- `eway_bill_engine.py` (~200 lines)

**New SQLite table:**
```sql
CREATE TABLE eway_bills (
    id INTEGER PRIMARY KEY,
    bill_no TEXT,
    so_id TEXT,
    from_gstin TEXT,
    to_gstin TEXT,
    from_city TEXT,
    to_city TEXT,
    vehicle_no TEXT,
    hsn_code TEXT DEFAULT '27132000',
    value REAL,
    valid_from TEXT,
    valid_until TEXT,
    distance_km INTEGER,
    status TEXT DEFAULT 'active'
);
```

**Sections:**
1. **Generate from SO** — Select sales order → auto-fill all fields from document_management
2. **Active Bills** — List with expiry countdown (green >24hr, yellow <24hr, red expired)
3. **Expiry Alerts** — Auto-alert when bill expires in <12 hours
4. **Bulk Generate** — Select multiple SOs → generate all at once
5. **PDF Export** — E-way bill format PDF for manual NIC upload

**Note:** Phase 1 = data generation + PDF. Phase 2 (future) = direct NIC/GSP API integration.

**Nav:** Add to Compliance module.

### 3.4 Competitor Price Tracker (Enhancement)

**Enhance:** `command_intel/competitor_intelligence.py` (existing) + `competitor_intelligence.py` engine.

**New sections to add:**
1. **Revision History Chart** — IOCL/HPCL/BPCL bitumen price revisions last 12 months (Plotly line chart)
2. **Price Comparison Table** — Our price vs competitors by city/grade. Highlight where we're cheaper.
3. **Revision Alerts** — Auto-alert when any competitor revises price
4. **Advantage Calculator** — "You save ₹X/MT vs IOCL in {city}" auto-generated per city

**New SQLite table:**
```sql
CREATE TABLE competitor_revisions (
    id INTEGER PRIMARY KEY,
    competitor TEXT,
    grade TEXT,
    region TEXT,
    old_price REAL,
    new_price REAL,
    change REAL,
    revision_date TEXT,
    source TEXT
);
```

**Data:** OSINT from `competitor_intelligence.py` engine (already scrapes IOCL/HPCL).

### 3.5 NHAI Tender Feed

**New files:**
- `command_intel/nhai_tender_dashboard.py` (~350 lines)
- `tender_engine.py` (~200 lines)

**New SQLite table:**
```sql
CREATE TABLE tenders (
    id INTEGER PRIMARY KEY,
    tender_id TEXT,
    title TEXT,
    authority TEXT,
    state TEXT,
    district TEXT,
    road_length_km REAL,
    estimated_bitumen_mt REAL,
    deadline TEXT,
    value_cr REAL,
    status TEXT DEFAULT 'open',
    source_url TEXT,
    fetched_at TEXT
);
```

**Sections:**
1. **Live Tenders** — Table with filters (state, authority, deadline). Sortable.
2. **State-wise Map** — Plotly choropleth showing tender density
3. **Bitumen Demand Estimate** — Auto-calculate MT needed per tender (road_length_km * 45 MT/km factor)
4. **Opportunity Alerts** — New tender in your territory → P1 alert
5. **History** — Past tenders with win/loss tracking

**Data:** `govt_connectors.py` already has NHAI connector. Enhance to fetch tender listings.

**Nav:** Add to Intelligence module.

### 3.6 Real-Time Tanker Tracking

**New files:**
- `command_intel/tanker_tracking_dashboard.py` (~400 lines)
- `tanker_engine.py` (~200 lines)

**New SQLite table:**
```sql
CREATE TABLE tankers (
    id INTEGER PRIMARY KEY,
    vehicle_no TEXT,
    driver_name TEXT,
    driver_phone TEXT,
    source TEXT,
    destination TEXT,
    customer TEXT,
    grade TEXT,
    qty_mt REAL,
    status TEXT DEFAULT 'loading',  -- loading, in_transit, delivered, delayed
    departed_at TEXT,
    eta TEXT,
    delivered_at TEXT,
    lat REAL,
    lng REAL,
    last_updated TEXT
);
```

**Sections:**
1. **Live Map** — Plotly `scatter_mapbox` showing tanker positions (colored by status)
2. **Tanker List** — Table with status badges, ETA, customer. Click to expand details.
3. **Add/Update** — Form to add new tanker dispatch or update status
4. **ETA Calculator** — Uses `distance_matrix.py` (Haversine * 1.3 road factor) + avg speed 40km/hr
5. **Delay Alerts** — Auto-alert when tanker is >4 hours past ETA
6. **Delivery Log** — Completed deliveries with on-time % metric

**Phase 1:** Manual status updates via form.
**Phase 2 (future):** GPS API integration for live lat/lng.

**Nav:** Add to Logistics module.

---

## Wave 4: Client-Facing

### 4.1 Subscription Pricing Page

**New file:** `pages/home/subscription_pricing.py` (~350 lines)

**Based on:** `PPS_Pricing_Guide_v5.html` (2700 lines, 4 tiers already defined).

**Sections:**
1. **Hero** — "India's Smartest Bitumen Trading Platform" headline + CTA
2. **4-Tier Cards** — Essential ₹14,999 | Plus ₹34,999 | Premium ₹64,999 | Ultimate ₹89,999. Highlight "Plus" as recommended. Annual pricing with "25% below market" badge.
3. **Feature Comparison** — 64-feature toggle table. Click tier to highlight included features.
4. **Market Comparison** — Our pricing vs generic ERP vs manual process
5. **FAQ Accordion** — 10 common questions
6. **Inquiry Form** — Name, Company, Phone, Email, Tier Interest → stores in SQLite `inquiries` table + sends WhatsApp notification to owner

**New SQLite table:**
```sql
CREATE TABLE inquiries (
    id INTEGER PRIMARY KEY,
    name TEXT,
    company TEXT,
    phone TEXT,
    email TEXT,
    tier TEXT,
    message TEXT,
    created_at TEXT,
    status TEXT DEFAULT 'new'
);
```

**Nav:** Add to Home module.

### 4.2 Client Showcase as Standalone

**New file:** `showcase_standalone.py` (~200 lines)

**How it works:**
1. FastAPI route `GET /showcase` serves a self-contained HTML page
2. HTML generated from `client_showcase.py` data (company_config, live_prices, business_context)
3. No Streamlit dependency for viewer — pure HTML/CSS
4. Open Graph meta tags for WhatsApp/LinkedIn preview:
   - `og:title` = "PPS Anantams — Bitumen Trading"
   - `og:description` = "24 years | 24K contacts | Pan-India"
   - `og:image` = company logo

**Additional features:**
- QR code generation (using `qrcode` library) — PNG for printing on business cards
- "Request Quote" button → `wa.me` deep link with pre-filled message
- Auto-refresh rates every 6 hours

**Integration:** Button in Client Showcase page: "Get Shareable Link" + "Download QR Code"

### 4.3 PDF Brochure Generator

**New file:** `brochure_engine.py` (~300 lines)

**Output:** A4 PDF, 4-6 pages, ReportLab.

**Pages:**
1. **Cover** — Logo, company name, tagline, year
2. **About Us** — Experience, owner, network stats, address
3. **Products** — 6 grades with descriptions and use cases
4. **Today's Rates** — Live rates table (from `live_prices.json`)
5. **Why PPS** — 4 stats + 6 reasons (from client_showcase data)
6. **Contact** — Phone, WhatsApp, Email, Address, Bank details, GST/PAN/CIN

**Trigger locations:**
- Client Showcase → "Download Brochure" button
- Share Center → "Generate Brochure" option
- Director Cockpit Step 4 → "Attach Brochure" option

### 4.4 WhatsApp Catalog Card

**New function in:** `communication_engine.py` (add `generate_rate_card_message()`)

**Output:** Pre-formatted WhatsApp message:
```
PPS Anantams - Today's Rates
━━━━━━━━━━━━━━━━━━━
VG30 Bulk: ₹XX,XXX/MT
VG30 Drum: ₹XX,XXX/MT
VG10 Bulk: ₹XX,XXX/MT
VG10 Drum: ₹XX,XXX/MT
━━━━━━━━━━━━━━━━━━━
100% Advance | 24hr Validity
Ex-Terminal | GST 18% Extra

Call: +91 7795242424
━━━━━━━━━━━━━━━━━━━
PPS Anantams Corporation Pvt Ltd
Vadodara, Gujarat
```

**Trigger:** `wa.me/?text={encoded_message}` link.
**Locations:** Client Showcase, Director Cockpit, Command Center Quick Actions, sidebar.

---

## Wave 5: Polish & Deploy

### 5.1 Mobile Responsive

**File:** `theme.py` (global) + per-page CSS fixes.

**Breakpoints:**
- `>1024px` — Desktop (current, no change)
- `768px-1024px` — Tablet (2-col grids, smaller fonts)
- `<768px` — Mobile (1-col, stacked layout, hamburger-style nav)

**Priority pages for mobile (test first):**
1. Director Cockpit
2. Client Showcase
3. Pricing Calculator
4. Command Center
5. CRM Tasks
6. Live Market
7. Subscription Pricing
8. Negotiation
9. Share Center
10. Reports

**CSS changes:**
- KPI grids: `grid-template-columns: repeat(4,1fr)` → `repeat(2,1fr)` → `1fr`
- Tables: horizontal scroll wrapper on mobile
- Sidebar: collapsible on mobile (Streamlit default)
- Top bar: module names truncate or wrap

### 5.2 UI Consistency Pass

**Scan all 80 files** for:
- Hardcoded colors not matching theme.py tokens (e.g., old `#1e3a5f` navy, `#c9a84c` gold)
- Inline `<style>` blocks — extract common patterns to theme.py
- `margin-top: -80px` hacks — remove, fix root cause (Streamlit header gap)
- Font inconsistencies — ensure Inter everywhere
- Card border-radius — standardize to 12px (some have 8px, 16px, 18px)
- Shadow styles — standardize hover shadow

**Result:** Every page uses `theme.py` tokens. No orphan CSS.

### 5.3 Loading & Performance

**Caching strategy:**
- `@st.cache_data(ttl=300)` — market prices, AI signal, news, alerts (5-min cache)
- `@st.cache_data(ttl=3600)` — seed data, contacts, highway data (1-hour cache)
- `@st.cache_resource` — database connections, engine instances

**Lazy loading:**
- Verify all command_intel imports use `__import__()` pattern (some may have top-level imports)
- Heavy engines (ML, NLP, FAISS) must NOT load at startup

**Target:** Every page loads under 2 seconds on localhost.

### 5.4 Error Handling

**Pattern for all pages:**
```python
try:
    data = engine.get_data()
except Exception as e:
    st.warning(f"Data unavailable. Last updated: {last_update_time}")
    log_engine.log_error("page_name", str(e))
    data = fallback_data
```

**Changes:**
- Replace empty `except: pass` with user-friendly messages
- Show stale data with "Last updated X ago" badge instead of blank
- Log all errors to `log_engine.py` for debugging
- Add "Retry" button for network-dependent data

### 5.5 Production Deployment

**Option A: Streamlit Cloud (Recommended for Phase 1)**
- Free tier, easy setup
- Push to GitHub → connect Streamlit Cloud → auto-deploy
- Secrets via Streamlit Cloud secrets management
- Limitation: single instance, cold starts

**Option B: Railway/Render (Phase 2)**
- More control, persistent instance
- `Dockerfile` + `Procfile`
- Custom domain support
- ~$5-15/month

**Deployment checklist:**
1. Clean `requirements.txt` — remove unused packages, pin versions
2. Move secrets from `settings.json` to `.env` / environment variables
3. Add `.gitignore` — exclude `*.db`, `*.json` caches, `__pycache__`, `.env`
4. Add health check: `/health` FastAPI endpoint returning status + version
5. Convert `run_dashboard.bat` → `Procfile`: `web: streamlit run dashboard.py --server.port $PORT`
6. Test on fresh machine (clean Python env)

**Custom domain:** `dashboard.ppsanantams.com` (if sir wants — DNS + SSL setup)

### 5.6 Final Testing

**Automated smoke test:** `test_all_pages.py`
```python
# Import every page's render function — crash = fail
for module in ALL_PAGES:
    __import__(module, fromlist=["render"])
    print(f"OK: {module}")
```

**Manual testing checklist (top 20 pages):**
- [ ] Every nav link loads correctly
- [ ] No blank sections or raw HTML showing
- [ ] All buttons are functional
- [ ] PDF generation works (quote, brochure, e-way bill)
- [ ] WhatsApp/Email send works (sandbox)
- [ ] Mobile layout on 3 screen sizes
- [ ] Director Cockpit 4-step wizard end-to-end
- [ ] Client Showcase shareable link works
- [ ] Subscription pricing inquiry form submits
- [ ] Tanker tracking map renders

---

## New SQLite Tables Summary

| Table | Wave | Purpose |
|-------|------|---------|
| `chat_messages` | 2 | Client chat messages |
| `shared_links` | 2 | Shareable link tokens |
| `drip_campaigns` | 2 | Email drip campaign scheduler |
| `credit_limits` | 3 | Customer credit tracking |
| `eway_bills` | 3 | E-way bill records |
| `competitor_revisions` | 3 | Competitor price history |
| `tenders` | 3 | NHAI tender listings |
| `tankers` | 3 | Tanker/truck tracking |
| `inquiries` | 4 | Subscription inquiry form |

**Migration:** Add tables via `database.py` init function (CREATE TABLE IF NOT EXISTS pattern, same as existing tables).

---

## New Files Summary

| File | Wave | Type | Est. Lines |
|------|------|------|-----------|
| `pages/reports/financial.py` | 1 | Page wrapper | ~30 |
| `pages/reports/strategy.py` | 1 | Page wrapper | ~30 |
| `pages/reports/demand.py` | 1 | Page wrapper | ~30 |
| `pages/reports/correlation.py` | 1 | Page wrapper | ~30 |
| `pages/reports/road_budget.py` | 1 | Page wrapper | ~30 |
| `pages/reports/risk.py` | 1 | Page wrapper | ~30 |
| `pages/reports/export_reports.py` | 1 | Page wrapper | ~30 |
| `pages/reports/director_brief.py` | 1 | Page wrapper | ~30 |
| `pages/documents/purchase_orders.py` | 1 | Page wrapper | ~30 |
| `pages/documents/sales_orders.py` | 1 | Page wrapper | ~30 |
| `pages/documents/payment_orders.py` | 1 | Page wrapper | ~30 |
| `pages/documents/party_master.py` | 1 | Page wrapper | ~30 |
| `pages/documents/pdf_archive.py` | 1 | Page wrapper | ~30 |
| `pages/compliance/govt_hub.py` | 1 | Page wrapper | ~30 |
| `pages/compliance/gst_legal.py` | 1 | Page wrapper | ~30 |
| `pages/compliance/alert_system.py` | 1 | Page wrapper | ~30 |
| `pages/compliance/change_log.py` | 1 | Page wrapper | ~30 |
| `pages/compliance/procurement_dir.py` | 1 | Page wrapper | ~30 |
| `shareable_links_engine.py` | 2 | Engine | ~150 |
| `command_intel/client_chat_dashboard.py` | 2 | Dashboard | ~250 |
| `command_intel/profitability_dashboard.py` | 3 | Dashboard | ~400 |
| `credit_engine.py` | 3 | Engine | ~150 |
| `command_intel/credit_aging_dashboard.py` | 3 | Dashboard | ~350 |
| `eway_bill_engine.py` | 3 | Engine | ~200 |
| `command_intel/eway_bill_dashboard.py` | 3 | Dashboard | ~300 |
| `command_intel/nhai_tender_dashboard.py` | 3 | Dashboard | ~350 |
| `tender_engine.py` | 3 | Engine | ~200 |
| `command_intel/tanker_tracking_dashboard.py` | 3 | Dashboard | ~400 |
| `tanker_engine.py` | 3 | Engine | ~200 |
| `pages/home/subscription_pricing.py` | 4 | Page | ~350 |
| `showcase_standalone.py` | 4 | FastAPI | ~200 |
| `brochure_engine.py` | 4 | Engine | ~300 |
| `pages/reports/profitability.py` | 3 | Page wrapper | ~30 |
| `test_all_pages.py` | 5 | Test | ~100 |

**Total new files:** ~34
**Total new lines:** ~4,500 estimated

---

## Files Modified

| File | Wave | Changes |
|------|------|---------|
| `nav_config.py` | 1-4 | Add new pages to modules |
| `dashboard.py` | 1-4 | Add PAGE_DISPATCH entries |
| `database.py` | 2-4 | Add 9 new tables |
| `theme.py` | 5 | Mobile breakpoints, consistency tokens |
| `comm_tracking_dashboard.py` | 2 | Enable all 4 channel toggles |
| `communication_engine.py` | 4 | Add `generate_rate_card_message()` |
| `competitor_intelligence.py` | 3 | Add revision history, alerts |
| `road_budget_dashboard.py` | 1 | Enhance from 97 to ~250 lines |
| `data_manager_dashboard.py` | 1 | Enhance from 60 to ~200 lines |
| `contacts_directory_dashboard.py` | 1 | Enhance from 82 to ~200 lines |
| `seed_data.py` | 1 | Ensure tbl_contacts + tbl_highway_km populated |
| `quotation_system/api.py` | 2,4 | Add `/share/{token}` and `/showcase` routes |
| `requirements.txt` | 4-5 | Add `qrcode` library |
| `settings.json` | 2 | Enable email/whatsapp toggles |
| `80+ command_intel + page files` | 5 | CSS consistency fixes |

---

## Dependencies & Ordering

```
Wave 1 (no dependencies — can start immediately)
  └── Wave 2 (depends on Wave 1 for enabled comm channels in fixed pages)
        └── Wave 3 (depends on Wave 2 for alert integration)
              └── Wave 4 (depends on Wave 3 for complete feature set in pricing page)
                    └── Wave 5 (depends on all waves for final polish + deploy)
```

Each wave is independently testable and demoable after completion.
