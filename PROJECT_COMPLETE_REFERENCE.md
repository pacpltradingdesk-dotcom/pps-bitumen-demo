# PPS ANANTAM — BITUMEN SALES DASHBOARD v5.0
## Complete AI Reference Document
**Last Updated:** 24-Mar-2026 | **Company:** PPS Anantams Corporation Private Limited | **GST:** 24AAHCV1611L2ZD

---

## 1. WHAT IS THIS PROJECT?

Enterprise-grade B2B **bitumen trading intelligence platform** for PPS Anantam — India's bitumen trading company with 24+ years experience. Handles pricing, sales CRM, market intelligence, logistics, compliance, and AI-powered decision making.

**Tech Stack:** Streamlit (frontend) + SQLite (database) + Python engines (backend) + FastAPI (quotation microservice)

---

## 2. ARCHITECTURE OVERVIEW

```
dashboard.py (Main Router ~630 lines)
├── theme.py → CSS injection (Clean White Theme v5.0)
├── nav_config.py → 9 modules, 80+ pages
├── role_engine.py → RBAC (admin/manager/sales/ops/viewer/director)
├── top_bar.py → Navigation bar
├── subtab_bar.py → Sidebar features
│
├── pages/ (27 Streamlit page files)
│   ├── home/ → Command Center, Live Market, Opportunities
│   ├── pricing/ → Pricing Calculator
│   ├── sales/ → CRM Tasks, Comm Hub, Negotiation, Calendar
│   ├── intelligence/ → Telegram Analyzer
│   ├── logistics/ → Ecosystem Management
│   ├── reports/ → (stub)
│   ├── compliance/ → (stub)
│   ├── system/ → AI Learning, Knowledge Base, Settings, Sync
│   └── sharing/ → Share Center, Telegram Dashboard
│
├── command_intel/ (50+ specialized dashboard modules)
│   ├── command_center_home.py → Hero dashboard
│   ├── price_prediction.py → ML 24-month forecast
│   ├── alert_system.py → P0/P1/P2 alerts
│   ├── sre_dashboard.py → System reliability
│   ├── bug_tracker.py → Issue management
│   └── 45+ more dashboards...
│
├── components/ (Reusable UI)
│   ├── chart_card.py → Plotly wrapper
│   ├── data_table.py → Sortable/filterable tables
│   ├── kpi_card.py → KPI metric cards
│   ├── filter_bar.py → Multi-select filters
│   └── share_button.py → Share dialog
│
├── 150+ root engine files (business logic)
├── quotation_system/ (FastAPI microservice)
├── ml_models/ (trained LightGBM/Prophet models)
└── 80+ JSON config/data files
```

---

## 3. HOW TO RUN

```bash
pip install -r requirements.txt    # 60+ packages
python seed_data.py                # Populate initial data
streamlit run dashboard.py         # http://localhost:8501
```

---

## 4. NINE MODULES & ALL FEATURES

### MODULE 1: 🏠 HOME
| Tab | Page File | Features |
|-----|-----------|----------|
| Command Center | `pages/home/command_center.py` + `command_intel/command_center_home.py` | 5-KPI row (Brent, WTI, USD/INR, VG30, AI Signal), Quick Actions grid (6 buttons), Live Alerts (top 5), Bottom Stats (Active Deals, Pending Tasks, Open Alerts) |
| Live Market | `pages/home/live_market.py` | Market Pulse bar, 6-period price forecast, Cheapest sources ranked, Opportunities count, Task summary, API health status |
| Opportunities | `pages/home/opportunities.py` | AI-powered opportunity discovery, Priority badges (P0/P1/P2), Savings/MT metrics, WhatsApp templates, Call scripts, Scan trigger |
| Alerts | `command_intel/alert_center.py` + `alert_system.py` | 9 alert types (Supplier Risk, Crude Price, Margin, Shipment Delay, Payment Overdue, Freight Rate, GST Mismatch, Govt Tender, India VIX), P0/P1/P2 severity, Smart dedup, Snooze/Dismiss actions |

### MODULE 2: 💰 PRICING
| Tab | Page File | Features |
|-----|-----------|----------|
| Pricing Calculator | `pages/pricing/pricing_calculator.py` | 3-column layout: Parameters → Source Ranking → Landing Cost. Location/Customer search, State/City filters, Grade selection (VG30/VG10/VG40/CRMB/PMB/Emulsion), Bulk/Drum toggle, Feasibility assessment (Refinery vs Import vs Decanter), 3-tier offers (Aggressive/Balanced/Premium), PDF quote generation, WhatsApp share |
| Import Cost Model | `command_intel/` | FOB(USD) + Freight + Insurance + CIF + Port + CHA + Handling + Customs + GST = Landed INR |
| Price Prediction | `command_intel/price_prediction.py` | Prophet + ARIMA + Linear Regression + Ensemble. 24-month forecast, Confidence intervals (80%/95%), Scenario analysis, Backtesting accuracy |
| Manual Price Entry | `command_intel/manual_entry.py` | Admin override commodity prices, Lock prices for customers, Bulk CSV import, Validity period |
| SOS Special Pricing | `command_intel/sos_dashboard.py` | Emergency spot pricing, Ultra-premium tier (+40-60%), 2-4 hour validity, Auto WhatsApp notification |
| Past Predictions | `command_intel/` | Forecast accuracy review, Model comparison |

### MODULE 3: 🧾 SALES & CRM
| Tab | Page File | Features |
|-----|-----------|----------|
| CRM Tasks | `pages/sales/crm_tasks.py` | KPIs (Hot Leads, Due Today, Overdue, Closing). Today's Worklist with filter (Due/Overdue/Upcoming), Task cards with Done button, Add New Task form, Calendar view (color-coded month grid), Automation Rules (auto-call, auto-followup) |
| Sales Workspace | `command_intel/` | Deal pipeline, Active negotiations, Win probability tracking |
| Negotiation | `pages/sales/negotiation.py` | AI negotiation brief: Customer Profile, Best Landed Cost, Walk-Away Price, 3-Tier Pricing, Client Benefits, Market Context, Objection Library (quick/detailed replies + confidence boosters), Closing Strategy |
| Communication Hub | `pages/sales/comm_hub.py` | Message generator (Offer/Followup/Reactivation/Payment Reminder), 3 channels (WhatsApp/Email/Call Script), 5-touch follow-up sequence, Communication log |
| Sales Calendar | `pages/sales/sales_calendar.py` | Season planner by city/state, Monthly demand index, 12-month grid view, Holiday calendar (28 states), Weather remarks, Upcoming festivals (next 30 days) |
| Daily Log | `command_intel/` | Activity tracking |
| Contacts | `command_intel/contact_importer.py` | Bulk import (Excel/CSV/PDF), Contact directory |
| Comm Tracking | `command_intel/` | WhatsApp/Email/Call history |

### MODULE 4: 🧠 INTELLIGENCE
| Tab | Page File | Features |
|-----|-----------|----------|
| Market Signals | `command_intel/market_signals_dashboard.py` | 10-signal composite (Crude, FX, Weather, VIX, etc.), Buy/Hold/Sell recommendations with confidence |
| Real-time Insights | `command_intel/real_time_insights_dashboard.py` | Live market data + instant analysis |
| News Intel | `command_intel/news_dashboard.py` | 14-source RSS + API aggregator, Sentiment analysis (FinBERT/VADER), Dedup (72% threshold), Max 5000 articles, Impact scoring |
| Competitor Intel | `command_intel/competitor_intelligence.py` | IOCL/HPCL price tracking, OSINT on rival traders |
| Business Advisor | `command_intel/business_advisor_dashboard.py` | Strategic guidance on inventory, risk, timing |
| Purchase Advisor | `command_intel/recommendation_dashboard.py` | Supplier scoring, Procurement timing, Buy/Hold/Sell signals |
| Global Markets | `command_intel/` | FX, Crude, Refined products tracking |
| Telegram Analyzer | `pages/intelligence/telegram_analyzer.py` | 5 tabs: Price Intel (conclusion box + message feed), Connect Account (API ID/Hash/Phone), Channel Manager, Auto-Send (WhatsApp links + Telegram bot), Settings. Features: OTP/2FA auth flow, Multi-language translation, Price extraction (regex), Bitumen grade detection, Market mood analysis, Supply signal detection, One-click send to configured recipients |
| Demand Correlation | `command_intel/correlation_dashboard.py` | Highway KM vs Bitumen demand, Statsmodels regression, Granger causality |

### MODULE 5: 📄 DOCUMENTS
| Tab | Features |
|-----|----------|
| Purchase Orders | SOW generation, e-way bill |
| Sales Orders | Quotation → PO conversion |
| Payment Orders | GST-compliant invoices |
| Party Master | Supplier + Customer CRUD |
| PDF Archive | Generated document storage |

### MODULE 6: 🚚 LOGISTICS
| Tab | Page File | Features |
|-----|-----------|----------|
| Maritime Logistics | `command_intel/maritime_logistics_dashboard.py` | Vessel tracking, Port capacity, Shipping routes, Ocean freight rates, Transit times |
| Supply Chain | `command_intel/` | End-to-end flow (Source → Warehouse → Customer) |
| Port Import Tracker | `command_intel/port_tracker_dashboard.py` | HS 271320 bitumen imports, Vessel ETA, Port congestion |
| Feasibility | `command_intel/` | Refinery vs Import vs Decanter cost comparison |
| Ecosystem | `pages/logistics/ecosystem.py` | 3 tabs (Source & Supply, Sales & Clients, Logistics & Services). Analytics by Category/City/State. Add/edit/filter suppliers, customers, service providers. Excel import. 24K+ contacts |
| Refinery Supply | `command_intel/` | PSU refinery allocation rules |

### MODULE 7: 📊 REPORTS
| Tab | Features |
|-----|----------|
| Financial Intel | Revenue, margin, receivables analysis, GDP/CPI/VIX macro metrics |
| Strategy Panel | Market positioning, competitive pricing analysis |
| Demand Analytics | State-wise demand forecast, seasonal patterns, contractor demand cycles |
| Demand Correlation | Crude ↔ Bitumen ↔ Construction spend analysis |
| Road Budget & Demand | Highway KM from MoRD, ministry spend projections |
| Risk Scoring | Multi-factor deal risk (credit, commodity, geographic) |
| PDF Export | Multi-page report generation |
| Director Briefing | Auto-generated 6-page executive summary |

### MODULE 8: 🛡️ COMPLIANCE
| Tab | Features |
|-----|----------|
| Govt Data Hub | MoRD, NHAI, GST authority data |
| GST & Legal Monitor | Compliance tracking, ITC reversal alerts, GSTR-2B discrepancy |
| Alerts | Compliance-specific alerts |
| Change Log | Full audit trail (who changed what, when, old → new value) |

### MODULE 9: ⚙️ SYSTEM & AI
| Tab | Page File | Features |
|-----|-----------|----------|
| AI Assistant | `command_intel/ai_dashboard_assistant.py` | Natural language Q&A on dashboard data. Multi-provider fallback: OpenAI → Ollama → HuggingFace → GPT4All → Claude. Context-aware, cost tracking |
| AI Fallback | `command_intel/ai_fallback_dashboard.py` | 5-provider chain management. Chat, Provider Hub, Switch & Test, Event Log |
| AI Setup | `command_intel/ai_setup_dashboard.py` | Environment detection (OS/RAM/CPU/GPU), Module registry with health, Workers control |
| AI Learning | `pages/system/ai_learning.py` | Model accuracy tracking, Learned weight factors (crude_trend, fx_trend, seasonal, refinery_util, import_vol), Daily/Weekly/Monthly learning cycles, Weights visualization |
| Health Monitor | `command_intel/health_monitor_dashboard.py` | System health scores (API, data freshness, error rate, latency, DB size) |
| SRE Dashboard | `command_intel/sre_dashboard.py` | 30-day health trends, CPU/memory/disk, API uptime %, Data audit, Performance profiling |
| Alert System | `command_intel/alert_system.py` | 9 configurable alert types with thresholds |
| API Hub | `command_intel/api_hub_dashboard.py` | 25-API monitoring, Data connectors |
| Bug Tracker | `command_intel/bug_tracker.py` | Report/track bugs (critical/high/medium/low), Screenshot upload, Status workflow |
| Change Log | `command_intel/change_log.py` | Full system audit trail |
| Settings | `pages/system/settings_page.py` | API keys, Market data APIs, Email/WhatsApp automation, Display/ticker, Smart logic rules, Unavailability overrides |
| Knowledge Base | `pages/system/knowledge_base.py` | Sales training Q&A, Search with confidence scoring, Browse by category, Stats |
| Sync Status | `pages/system/sync_status.py` | Full/quick sync triggers, Sync history, Missing inputs detection |
| Developer Ops | `command_intel/developer_ops_dashboard.py` | Dev activity, deployment status, logs |

---

## 5. CORE ENGINE FILES (Business Logic)

### Pricing & Calculation
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `calculation_engine.py` | All pricing formulas | `calculate_international_landed()`, `calculate_domestic_landed()`, `calculate_decanter_landed()`, `generate_offer_tiers()` |
| `feasibility_engine.py` | 3-route cost comparison | `get_feasibility_assessment(city, qty, grades)` → Refinery vs Import vs Decanter |
| `optimizer.py` | Cost optimization (Parquet) | `CostOptimizer.load_data()`, `get_cities()`, `update_source_price()` |
| `pdf_generator.py` | Quote PDF generation | `create_price_pdf()`, `get_next_quote_number()` |

### Market Data & APIs
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `api_manager.py` | 25-API registry + health | `get_brent_price()`, `get_usdinr()`, `start_auto_health()`, `auto_repair_api()` |
| `api_hub_engine.py` | Widget performance monitoring | `init_hub()`, `start_hub_scheduler()` |
| `market_pulse_engine.py` | Live price aggregation | SMA/EMA trends, momentum signals |
| `market_ticker.py` | Scrolling ticker (4 rows) | Tenders, Markets, Refinery, Import prices |
| `news_engine.py` | 14-source RSS + API aggregator | Dedup 72%, Max 5000 articles, Sentiment scoring |

### AI & ML
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `ml_forecast_engine.py` | Price forecasting | Prophet + ARIMA + sklearn, 3-tier fallback, 30/60/90 day forecast |
| `ml_boost_engine.py` | Buyer/opportunity/risk scoring | LightGBM pre-trained models |
| `ai_assistant_engine.py` | Context-aware Q&A chatbot | Multi-provider fallback chain |
| `ai_fallback_engine.py` | LLM fallback chain | Ollama → GPT4All → HuggingFace |
| `ai_learning_engine.py` | Weight learning from feedback | `daily_learn()`, `weekly_learn()`, `monthly_learn()` |
| `ai_reply_engine.py` | Intent classification | price_inquiry, order_placement, complaint, etc. |
| `rag_engine.py` | Semantic search (FAISS) | `index_documents()`, `search()`, hybrid keyword+semantic |
| `finbert_engine.py` | Financial sentiment | FinBERT pre-trained model |
| `anomaly_engine.py` | Outlier detection | Z-score based |
| `correlation_engine.py` | Demand correlation | Statsmodels regression, Granger causality |

### CRM & Sales
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `crm_engine.py` | Customer relationship management | `get_tasks()`, `add_task()`, `complete_task()`, VIP scoring (Platinum/Gold/Silver/Standard) |
| `communication_engine.py` | Multi-channel orchestration | `whatsapp_offer()`, `email_offer()`, `call_script_offer()`, `generate_followup_sequence()` |
| `negotiation_engine.py` | AI negotiation coaching | `prepare_negotiation_brief()`, `get_full_objection_library()` |
| `opportunity_engine.py` | Auto-deal alerts | Cost reduction, Supply gap, Demand spike triggers |
| `discussion_guidance_engine.py` | Pre-call briefing | Objection handling, confidence boosters |

### Communication
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `email_engine.py` | SMTP queue + scheduling | `send_email()`, `start_email_scheduler()`, Templates: quotation, followup, payment reminder, director report |
| `whatsapp_engine.py` | WhatsApp Business API | `send_text_message()`, `send_template_message()`, `send_bulk_whatsapp()`, Rate limiting |
| `telegram_engine.py` | Telegram Bot API | `send_message()`, `broadcast_message()`, `configure_bot()`, `send_document()` |
| `telegram_channel_analyzer.py` | Telegram channel reading | `fetch_channel_messages()`, `analyze_messages()`, `send_otp()`, `verify_otp()`, `_generate_conclusion()` |

### Logistics & Supply
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `port_tracker_engine.py` | Maritime intelligence | Vessel tracking, port capacity, shipping routes |
| `maritime_intelligence_engine.py` | Vessel tracking | Inbound bitumen manifests |
| `infra_demand_engine.py` | Road budget forecasting | Highway KM from MoRD, ministry spend |

### System & Operations
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `sync_engine.py` | Daily data refresh | `run_full_sync()`, 8-step pipeline, 6 AM IST schedule |
| `sre_engine.py` | Self-healing + observability | Health checks (API/Data/Calc/Export), Auto-bug creation, P0/P1/P2 alerts |
| `role_engine.py` | RBAC authentication | PIN-based, 6 roles, session timeout, rate limiting |
| `vault_engine.py` | Secrets encryption | Fernet encryption, base64 fallback |
| `settings_engine.py` | Business rules config | 100+ configurable keys in settings.json |
| `resilience_manager.py` | Heartbeat + circuit breaker | Background health monitoring |

### Data & Geography
| Engine | Purpose | Key Functions |
|--------|---------|---------------|
| `database.py` | SQLite3 with connection pooling | WAL mode, Foreign keys, Transaction wrappers, Auto-rounding monetary fields |
| `distance_matrix.py` | Haversine distance calculation | 20 source coords, 60+ destination cities, State mappings |
| `source_master.py` | Master sourcing data | 16 refineries, 8 import terminals, 10 decanters |
| `india_localization.py` | INR formatting + IST | `format_inr()` → "₹1,23,456", `get_financial_year()` → "FY 2025-26" |
| `sales_calendar.py` | Seasonal demand model | Monthly index by season, 28-state profiles, Holiday calendar |

---

## 6. DATABASE SCHEMA (SQLite3)

**File:** `bitumen_dashboard.db` | **Mode:** WAL | **Foreign Keys:** ON | **Pool:** Max 5 connections

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `customers` | name, credit_limit, outstanding, preferred_grades, monthly_demand, peak_months, relationship_stage | Customer master |
| `suppliers` | name, category, credit_limit, payment_reliability, preferred_grades, last_deal_price, relationship_stage | Supplier master |
| `deals` | deal_number, qty_mt, grade, buy_price, sell_price, landed_cost, margin, source, destination, stage, status, gst, win_probability | Transactions |
| `price_history` | date_time, benchmark, price, currency, source, validated | Historical prices |
| `fx_history` | date_time, from_currency, to_currency, rate, source | Exchange rates |
| `inventory` | location, grade, qty_mt, cost_per_mt, status, vessel_name, expected_arrival | Stock levels |
| `communications` | customer_id, supplier_id, channel, direction, content, template_used, sent_at, status | Message logs |
| `opportunities` | type, title, customer_id, estimated_margin, estimated_volume, trigger_reason, priority, status | Deal alerts |
| `email_queue` | to_email, cc, bcc, subject, body_html, email_type, status, retry_count | Outbound email staging |
| `whatsapp_queue` | to_number, message_type, template_id, language, status, retry_count | Outbound WA staging |
| `crm_tasks` | client, type, note, priority, due_date, status | Task management |
| `sync_logs` | sync_type, started_at, completed_at, apis_called, apis_succeeded, records_updated, errors | Sync audit |
| `contacts` | name, phone, email, company, city, state, category | Contact directory |
| `missing_inputs` | field_name, entity_type, entity_id, reason, priority, status | Data quality |

---

## 7. CONFIGURATION FILES

### settings.json (Business Rules — 100+ keys)
```
Margin: min=₹500/MT, balanced=1.6x, premium=2.4x
GST: 18%, Customs: 2.5%
Transport: Bulk ₹5.5/km, Drum ₹6.0/km
Decanter conversion: ₹500/MT
Import defaults: FOB $380, Freight $35, Insurance 0.5%
Port charges: ₹10,000, CHA: ₹75/MT, Handling: ₹100/MT
CRM: Hot=7 days, Warm=30 days, Cold=90 days
Price alert: 5% swing threshold
Crude range: $40-150, Bitumen range: ₹15K-120K, FX: 50-120
Email: rate limit 50/hr, WhatsApp: rate limit 100/hr
Data retention: 5000 prices, 5000 news, 1000 sync logs
```

### api_config.json (25 API Widgets)
```
USD/INR: fawazahmed0 CDN → Frankfurter ECB (fallback)
Brent: yfinance BZ=F
WTI: yfinance CL=F
Nifty: yfinance ^NSEI
India VIX: yfinance ^INDIAVIX
Weather: Open-Meteo
GDP/Infra: World Bank API
News: 14 RSS feeds + NewsAPI/GNews
Each widget: endpoint, refresh interval, fallback, auth, reliability rating (A+/A/B)
```

### nav_config.py (Navigation Structure)
```
9 modules, 80+ pages
TOPBAR_MODULES: 7 visible
OVERFLOW_MODULES: 2 in "More ▾"
MODULE_ROLE_MAP: role → allowed modules
PAGE_ROLE_MAP: page → required role
```

### company_config.py (PPS Anantam Details)
```
Legal: PPS Anantams Corporation Private Limited
GST: 24AAHCV1611L2ZD
Bank: ICICI Bank (account + IFSC)
9 standard T&Cs for quotations
Declaration, interest, complaint, driver clauses
```

### sre_config.json (Monitoring Rules)
```
Alert thresholds: API latency, error rate, stale data, scheduler overdue
Auto-heal: retries, backoff (5s/15s/30s), bug trigger
Pricing sanity: min/max for bitumen, freight, margin, brent, USD/INR
```

---

## 8. BACKGROUND SERVICES (Auto-started)

| Service | Engine | Interval | Purpose |
|---------|--------|----------|---------|
| API Health Monitor | `api_manager.py` | 5 min | Ping all 25 APIs, log failures, attempt repairs |
| SRE Monitor | `sre_engine.py` | 15 min | System health checks, auto-bug creation |
| Data Hub Sync | `api_hub_engine.py` | 60 min | Widget data refresh |
| Full Ecosystem Sync | `sync_engine.py` | Daily 6 AM IST | 8-step full data pipeline |
| Email Queue | `email_engine.py` | 30 sec | Process pending emails |
| WhatsApp Queue | `whatsapp_engine.py` | 30 sec | Process pending messages |
| Heartbeat | `resilience_manager.py` | Continuous | Service liveness checks |
| Port Tracker | `port_tracker_engine.py` | On-demand | Vessel/port data refresh |

---

## 9. DATA FLOW EXAMPLES

### Pricing Quote Generation
```
User input (source, destination, qty, grade)
→ distance_matrix.get_distance(source, dest)
→ feasibility_engine.get_feasibility_assessment()
  ├── calculate_refinery_cost() → Base + GST 18% + Transport
  ├── calculate_import_cost() → FOB(INR) + Freight + Insurance + CIF + Port + CHA + Handling + Customs + GST
  └── calculate_decanter_cost() → Drum + GST + Transport + ₹500 conversion
→ calculation_engine.generate_offer_tiers() → Aggressive/Balanced/Premium
→ pdf_generator.create_price_pdf() → Quote PDF
→ database.insert_deal()
→ crm_engine.add_task() → Auto-create followup task
```

### Telegram Intel Flow
```
User clicks "Fetch & Analyze"
→ telegram_channel_analyzer.fetch_channel_messages(config, limit=30)
  → TelegramClient.connect() → check is_user_authorized()
  → If not authorized → TelegramOTPRequired → send_otp() → UI shows OTP input
  → iter_dialogs() → filter channels → iter_messages()
→ analyze_messages()
  → _translate_to_english() (GoogleTranslator)
  → _is_price_related() (regex + keyword matching)
  → _extract_prices() (multi-currency patterns)
→ _generate_conclusion()
  → Extract dollar/MT prices, FX rates, Brent mentions
  → Detect bitumen grades (VG30, 60/70, 40/60, etc.)
  → Count product categories & supply signals
  → Determine market mood (bullish/bearish/neutral)
  → Generate action items
→ save_analysis() → telegram_price_intel.json + sre_alerts.json
→ UI renders: KPIs → Conclusion Box → Price Feed
→ Auto-Send tab: WhatsApp links (wa.me) + Telegram Bot API
```

### Daily Sync Pipeline
```
sync_engine.run_full_sync() [6 AM IST]
Step 1: Market data → api_manager.get_brent_price(), get_usdinr()
Step 2: News refresh → news_engine.fetch_all_sources()
Step 3: Trade data → UN Comtrade API, port_tracker
Step 4: Validation → SRE sanity checks
Step 5: Calculated tables → demand correlations
Step 6: Opportunity scan → opportunity_engine
Step 7: CRM updates → crm_engine.update_relationship_scores()
Step 8: Alert generation → alert_center
→ sync_logs.json (audit trail)
```

---

## 10. KEY DATA FILES (80+ JSON)

### Market & Pricing
| File | Content |
|------|---------|
| `live_prices.json` | Current refinery/import/decanter prices per source |
| `tbl_crude_prices.json` | 5-year Brent/WTI price history |
| `tbl_fx_rates.json` | Historical USD/INR rates |
| `market_alerts.json` | Active price/supply alerts |
| `tbl_market_signals.json` | Buy/sell signal log |

### CRM & Sales
| File | Content |
|------|---------|
| `sales_parties.json` | 24K+ customer records |
| `purchase_parties.json` | Supplier records |
| `service_providers.json` | Transporters, decanters, brokers |
| `tbl_contacts.json` | Contact directory |
| `crm_tasks.json` | Task data (legacy, migrating to SQLite) |
| `crm_activities.json` | Activity log |
| `opportunities.json` | Current profitable deals |

### Intelligence
| File | Content |
|------|---------|
| `tbl_news_feed.json` | News archive (max 5000) |
| `tbl_demand_proxy.json` | 28-state seasonal demand signals |
| `telegram_price_intel.json` | Telegram channel analysis results |
| `telegram_channel_messages.json` | Raw fetched messages |
| `telegram_account_config.json` | Telegram API credentials |
| `telegram_intel_send_config.json` | Auto-send recipients (WhatsApp + Telegram) |

### Logistics
| File | Content |
|------|---------|
| `tbl_ports_master.json` | 8 ports (capacity, draft, berths, handling rate) |
| `tbl_maritime_intel.json` | Vessel schedules |
| `tbl_ports_volume.json` | Port throughput history |

### System & Monitoring
| File | Content |
|------|---------|
| `api_config.json` | 25-API registry |
| `api_cache.json` | Response cache (15-min TTL) |
| `api_stats.json` | API performance metrics |
| `api_error_log.json` | API error trail |
| `sre_health_status.json` | 8-entity health scores |
| `sre_alerts.json` | P0/P1/P2 severity alerts |
| `sre_bugs.json` | Auto-created bugs |
| `sync_logs.json` | Sync audit trail |
| `ai_learned_weights.json` | ML weight factors |
| `ai_fallback_log.json` | AI provider fallback trail |

---

## 11. EXTERNAL API INTEGRATIONS (25 Free APIs)

| API | Provider | Data | Refresh | Fallback |
|-----|----------|------|---------|----------|
| USD/INR | fawazahmed0 CDN | Forex rate | 1h | Frankfurter ECB |
| Brent Crude | yfinance (BZ=F) | Oil price USD/bbl | 15m | Mock data |
| WTI Crude | yfinance (CL=F) | Oil price USD/bbl | 15m | Mock data |
| Nifty 50 | yfinance (^NSEI) | Index value | 1h | None |
| India VIX | yfinance (^INDIAVIX) | Volatility | 1h | None |
| Gold | yfinance (GC=F) | Gold USD/oz | 1h | None |
| Natural Gas | yfinance (NG=F) | NG USD/MMBtu | 1h | None |
| Weather | Open-Meteo | Rainfall, temperature | 1h | None |
| GDP | World Bank API | India GDP growth | 24h | None |
| Infrastructure | World Bank API | Infra spend data | 24h | None |
| CPI | World Bank API | Inflation rate | 24h | None |
| News (14 sources) | RSS + NewsAPI | Oil/energy news | 10m | Cached articles |
| Google Trends | pytrends | Search interest | 24h | None |
| Time | timeapi.io | Server time | 1m | Local datetime |

---

## 12. ML MODELS

| Model | Library | Purpose | Files |
|-------|---------|---------|-------|
| Price Forecast | Prophet + ARIMA | 30/60/90 day Brent/bitumen prediction | `ml_forecast_engine.py` |
| Buyer Scoring | LightGBM | Customer purchase probability | `ml_models/boost_buyer_lgb.pkl` |
| Opportunity Scoring | LightGBM | Deal win probability | `ml_models/boost_opportunity_lgb.pkl` |
| Risk Scoring | LightGBM | Deal risk assessment | `ml_models/boost_risk_lgb.pkl` |
| State Ranking | LightGBM | State-wise demand ranking | `ml_models/boost_state_ranker_lgb.pkl` |
| Financial Sentiment | FinBERT | News sentiment (positive/negative/neutral) | `finbert_engine.py` |
| Text Sentiment | VADER | Lightweight fallback sentiment | `vaderSentiment` |
| Semantic Search | FAISS + sentence-transformers | RAG over business docs | `rag_engine.py` |
| Anomaly Detection | Z-score | Price/demand outliers | `anomaly_engine.py` |

---

## 13. RBAC (Role-Based Access Control)

| Role | Level | Access |
|------|-------|--------|
| Director | 4 | Full access — all modules, system config, user management |
| Admin | 4 | Full access (alias for Director) |
| Sales | 3 | Home, Pricing, CRM, Communication, Negotiation |
| Operations | 2 | Pricing, Documents, Logistics, Sync, Alerts |
| Viewer | 1 | Home, Intelligence, Reports (read-only) |

**Auth:** PIN-based (SHA-256 hashed), Session timeout 30 min, Rate limit 5 failed attempts → 5 min lockout

---

## 14. QUOTATION SYSTEM (FastAPI Microservice)

```
quotation_system/
├── api.py → FastAPI endpoints
│   POST /quotations/ → Create quotation
│   GET /quotations/{id} → Fetch quotation
│   GET /quotations/{id}/pdf → Generate PDF
│   GET /quotations/latest-number → Next quote number
├── models.py → Pydantic/SQLModel schemas (Quotation, QuotationItem)
├── db.py → SQLModel session management
└── pdf_maker.py → PDF rendering (reportlab)
```

---

## 15. THEME SYSTEM (Clean White v5.0)

| Token | Color | Usage |
|-------|-------|-------|
| BLUE_PRIMARY | #2563eb | Buttons, links, active tabs |
| BLUE_HOVER | #1d4ed8 | Button hover |
| BLUE_LIGHT | #dbeafe | Light backgrounds, badges |
| NAVY_DARK | #0f172a | Top bar, dark sections |
| GREEN | #059669 | Success, positive metrics |
| RED | #dc2626 | Errors, negative metrics |
| AMBER | #f59e0b | Warnings, pending items |
| GOLD | #c9a84c | Premium elements |
| SLATE_50 | #f8fafc | Page background |
| SLATE_700 | #334155 | Primary text |
| SLATE_900 | #0f172a | Headings |
| WHITE | #ffffff | Cards, containers |

**Font Stack:** Inter, Segoe UI, Roboto, Helvetica Neue
**Hides:** Streamlit header, footer, toolbar completely

---

## 16. KEY BUSINESS METRICS

| Metric | Value |
|--------|-------|
| Company Experience | 24+ years in bitumen trading |
| Contact Database | 24,000+ parties |
| Sourcing Routes | 3 (Refinery, Import, Decanter) |
| Grades Supported | 7 (VG30, VG10, VG40, Emulsion, CRMB-55, CRMB-60, PMB) |
| Indian Refineries | 16 PSU (IOCL, BPCL, HPCL, CPCL, MRPL, NRL, ONGC, BORL, Nayara, RIL) |
| Import Terminals | 8 major ports (Kandla, Mundra, Mangalore, JNPT, Karwar, Haldia, Ennore, Paradip) |
| Private Decanters | 10 local decanters |
| Destination Cities | 60+ coordinates mapped |
| API Endpoints | 25 live integrations |
| Dashboard Pages | 80+ specialized |
| Engine Files | 150+ |
| JSON Data Files | 80+ |

---

## 17. DEPENDENCIES (requirements.txt)

### Core
`streamlit>=1.31.0`, `pandas>=2.1.4`, `numpy>=1.26.3`, `plotly>=5.18.0`

### ML/AI
`scikit-learn>=1.4.0`, `prophet>=1.1.5`, `xgboost>=2.0.3`, `lightgbm>=4.2.0`, `faiss-cpu>=1.7.4`, `sentence-transformers>=2.3.0`, `transformers>=4.37.0`, `torch>=2.1.0`, `vaderSentiment>=3.3.2`

### Data & APIs
`yfinance>=0.2.35`, `pytrends>=4.9.0`, `requests>=2.31.0`, `feedparser`, `deep-translator`

### Communication
`telethon` (Telegram client), `pytz`, `python-dateutil`

### Security & PDF
`cryptography>=42.0.0`, `reportlab`, `fpdf2`, `openpyxl`, `xlrd`

### System
`psutil>=5.9.0`, `sqlmodel>=0.0.14`, `fastapi`, `uvicorn`

---

*This document provides complete coverage of the PPS Anantam Bitumen Sales Dashboard v5.0 for AI understanding, onboarding, and development reference.*
