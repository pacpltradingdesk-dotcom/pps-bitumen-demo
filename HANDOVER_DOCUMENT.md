
# PPS ANANTAM — BITUMEN SALES DASHBOARD
## Complete Project Handover Document
**Version:** v5.0.0
**Date:** 05-Mar-2026
**Owner:** Prince P Shah | PPS Anantam / PACPL, Vadodara, Gujarat
**Contact:** +91 7795242424 | princepshah@gmail.com

---

## TABLE OF CONTENTS
1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Installation & Setup](#4-installation--setup)
5. [Architecture Overview](#5-architecture-overview)
6. [Navigation & Modules (15 Modules, 84 Pages)](#6-navigation--modules)
7. [Core Engines (Detailed)](#7-core-engines)
8. [AI & Intelligence Stack](#8-ai--intelligence-stack)
9. [Database Schema (46 Tables)](#9-database-schema)
10. [API Connectors (15+ Sources)](#10-api-connectors)
11. [Settings & Configuration (170+ Keys)](#11-settings--configuration)
12. [Business Rules & Formulas](#12-business-rules--formulas)
13. [Security & Access Control](#13-security--access-control)
14. [File-by-File Reference](#14-file-by-file-reference)
15. [Data Files & Caches](#15-data-files--caches)
16. [Known Issues & Open Items](#16-known-issues--open-items)
17. [Deployment & Operations](#17-deployment--operations)
18. [Development History](#18-development-history)

---

## 1. PROJECT OVERVIEW

### What It Does
A comprehensive bitumen trading management platform for PPS Anantam (PACPL), handling:
- **International Import Pricing** — CFR calculation from FOB + freight + insurance + customs + landing charges
- **Domestic Sales Pricing** — 3-tier offers (aggressive/balanced/premium) with GST, freight
- **CRM & Contact Management** — 132+ contacts, deals, tasks, communication tracking
- **Market Intelligence** — Real-time crude oil, forex, news, infrastructure demand
- **AI-Powered Analytics** — 9-provider AI fallback chain, sentiment analysis, forecasting
- **Director Briefing** — Daily automated executive summary with market position
- **Document Management** — SO, PO, Payment Orders, Quotations with PDF export
- **Logistics & Maritime** — Port tracking, vessel monitoring, route optimization
- **Compliance** — GST, customs duty, DPDP compliance, audit logging

### Scale
| Metric | Value |
|--------|-------|
| Total Python Files | 238 |
| Total Lines of Code | 110,578 |
| Root-level Engines | 137 .py files |
| Dashboard Pages (command_intel/) | 55 .py files |
| Quotation System | 5 .py files |
| JSON Data/Cache Files | 73+ |
| Database Tables | 46 |
| Database Records | ~14,000+ |
| Navigation Modules | 15 |
| Sidebar Pages | 84 |
| Settings Keys | 170+ |
| AI Providers | 9 |
| API Connectors | 15+ |
| Knowledge Base Q&A | 196 pairs |

---

## 2. TECHNOLOGY STACK

### Core Framework
| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | Streamlit | 1.53.1 |
| Language | Python | 3.12 |
| Database | SQLite | WAL mode |
| Charts | Plotly | 5.18+ |
| PDF Generation | fpdf2 + ReportLab | 2.8.7 / 4.0.8+ |
| Data Processing | Pandas + NumPy | 2.1+ / 1.26+ |

### AI & ML
| Component | Technology |
|-----------|-----------|
| Sentiment Analysis | FinBERT → DistilBERT → VADER → Keyword (4-tier fallback) |
| Forecasting | Prophet + SARIMAX + ARIMA (ensemble) |
| Boosting | XGBoost + LightGBM |
| NLP Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Search | FAISS (faiss-cpu) |
| Text Search | TF-IDF + RRF fusion |
| AI Providers | 9 providers (see Section 8) |

### Key Dependencies (requirements.txt)
```
streamlit>=1.31.0       # Web framework
pandas>=2.1.4           # Data processing
numpy>=1.26.3           # Numerical computing
reportlab>=4.0.8        # PDF generation
fpdf2>=2.7.6            # PDF generation (alternate)
sqlmodel>=0.0.14        # ORM layer
yfinance>=0.2.35        # Market data
openpyxl>=3.1.2         # Excel read/write
xlrd>=2.0.1             # Legacy Excel
plotly>=5.18.0          # Interactive charts
requests>=2.31.0        # HTTP client
prophet>=1.1.5          # Time series forecasting
scikit-learn>=1.4.0     # ML algorithms
statsmodels>=0.14.1     # Statistical models
scipy>=1.12.0           # Scientific computing
xgboost>=2.0.3          # Gradient boosting
lightgbm>=4.2.0         # Light gradient boosting
transformers>=4.37.0    # NLP models (FinBERT)
torch>=2.1.0            # PyTorch backend
vaderSentiment>=3.3.2   # Sentiment (lightweight)
faiss-cpu>=1.7.4        # Vector similarity search
sentence-transformers>=2.3.0  # Embeddings
cryptography>=42.0.0    # Vault encryption
psutil>=5.9.0           # System monitoring
pytrends>=4.9.0         # Google Trends
```

---

## 3. PROJECT STRUCTURE

```
bitumen sales dashboard/
├── .streamlit/
│   └── config.toml              # Streamlit theme & server config
├── command_intel/               # 55 dashboard page files
│   ├── __init__.py
│   ├── action_bar.py            # Universal action bar (email/WA/PDF/share)
│   ├── ai_dashboard_assistant.py
│   ├── ai_fallback_dashboard.py # AI provider status & management
│   ├── ai_setup_dashboard.py    # AI setup wizard
│   ├── alert_center.py          # Alert management
│   ├── api_hub_dashboard.py     # API connector management
│   ├── business_advisor_dashboard.py
│   ├── correlation_dashboard.py
│   ├── crm_automation_dashboard.py  # CRM main dashboard
│   ├── developer_ops_dashboard.py
│   ├── director_dashboard.py
│   ├── directory_dashboard.py
│   ├── discussion_guidance_dashboard.py
│   ├── document_management.py   # 1411 lines — SO/PO/Payment docs
│   ├── infra_demand_dashboard.py
│   ├── intelligence_hub_dashboard.py
│   ├── maritime_logistics_dashboard.py
│   ├── news_dashboard.py
│   ├── port_tracker_dashboard.py
│   ├── price_prediction.py
│   ├── sre_dashboard.py         # System reliability dashboard
│   ├── system_control_center.py
│   └── ... (55 total)
├── quotation_system/            # Quotation subsystem
│   ├── api.py
│   ├── db.py
│   ├── models.py
│   ├── pdf_maker.py
│   └── __init__.py
├── lkg_cache/                   # Last-Known-Good API cache
│   ├── eia_crude.json
│   ├── fx.json
│   ├── gold_price.json
│   ├── news.json
│   ├── ports.json
│   ├── refinery.json
│   ├── weather.json
│   └── ...
├── ml_models/                   # ML prediction logs
│   ├── business_advisory.json
│   ├── predictions_log.json
│   ├── recommendations.json
│   └── model_health.json
├── rag_index/                   # RAG search index
│   ├── documents.json
│   └── tfidf_index.pkl
├── news_data/                   # News article storage
├── logs/                        # Application logs (JSON lines)
├── pdf_exports/                 # Generated PDF documents
├── osint_data/                  # OSINT intelligence data
│
├── dashboard.py                 # ★ MAIN APP — 5193 lines
├── database.py                  # ★ DATABASE LAYER — 3611 lines
├── calculation_engine.py        # ★ PRICING ENGINE — 1343 lines
├── ai_fallback_engine.py        # ★ AI 9-PROVIDER CHAIN — 1200 lines
├── api_hub_engine.py            # ★ API HUB — 2186 lines
├── sre_engine.py                # ★ SRE MONITORING — 1644 lines
├── sales_knowledge_base.py      # ★ 196 Q&A PAIRS — 1451 lines
├── trading_chatbot_engine.py    # ★ AI CHATBOT — 1155 lines
├── chart_engine.py              # ★ PLOTLY CHARTS — 1273 lines
├── settings_engine.py           # ★ 170+ SETTINGS — 485 lines
├── nav_config.py                # ★ NAVIGATION — 258 lines
├── ... (137 root .py files)
│
├── bitumen_dashboard.db         # SQLite database (46 tables)
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git exclusions
└── HANDOVER_DOCUMENT.md         # This file
```

---

## 4. INSTALLATION & SETUP

### Prerequisites
- Python 3.12+
- pip (Python package manager)
- Git

### Quick Start
```bash
# 1. Clone repository
git clone <repo-url>
cd "bitumen sales dashboard"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dashboard
streamlit run dashboard.py

# Opens automatically at http://localhost:8501
```

### Optional AI Setup
```bash
# For local AI (Ollama — FREE, offline)
# Download from: https://ollama.com
ollama pull llama3

# For GPT4All (fully offline)
pip install gpt4all
# First run downloads ~2GB model automatically

# For cloud AI providers, add API keys in Settings > AI Providers:
# - Groq (FREE): https://console.groq.com/keys
# - Gemini (FREE): https://aistudio.google.com/apikey
# - Mistral (FREE): https://console.mistral.ai/api-keys
# - DeepSeek (FREE, research only): https://platform.deepseek.com/api_keys
# - OpenAI (PAID): https://platform.openai.com/api-keys
# - Claude (PAID): https://console.anthropic.com
```

### Streamlit Configuration (.streamlit/config.toml)
```toml
[theme]
primaryColor = "#059669"          # Green — matches PPS branding
backgroundColor = "#f8fafc"       # Light gray
secondaryBackgroundColor = "#e2e8f0"
textColor = "#1e293b"
font = "sans serif"

[server]
headless = true
port = 8501
enableCORS = false

[browser]
gatherUsageStats = false
```

---

## 5. ARCHITECTURE OVERVIEW

### Layered Architecture
```
┌─────────────────────────────────────────────────────┐
│                  PRESENTATION LAYER                  │
│  dashboard.py (5193 LOC) → Streamlit UI + Routing   │
│  command_intel/ (55 pages) → Page Components         │
│  news_ticker.py → Dual-stream ticker (Intl + India)  │
│  chart_engine.py → 15+ Plotly chart types            │
│  top_bar.py, subtab_bar.py → Navigation UI           │
├─────────────────────────────────────────────────────┤
│                 BUSINESS LOGIC LAYER                 │
│  calculation_engine.py → Pricing (CFR + Domestic)    │
│  crm_engine.py → CRM v3.0 (tasks, activities)       │
│  recommendation_engine.py → Purchase recommendations │
│  opportunity_engine.py → Deal opportunity scoring    │
│  negotiation_engine.py → Negotiation strategies      │
│  communication_engine.py → Comm templates            │
│  rotation_engine.py → Contact rotation scheduling    │
├─────────────────────────────────────────────────────┤
│                 INTELLIGENCE LAYER                   │
│  ai_fallback_engine.py → 9-provider AI chain         │
│  trading_chatbot_engine.py → AI chatbot              │
│  sales_knowledge_base.py → 196 Q&A pairs             │
│  finbert_engine.py → 4-tier sentiment pipeline       │
│  ml_forecast_engine.py → Prophet+SARIMAX+ARIMA       │
│  rag_engine.py → Hybrid FAISS+TF-IDF search          │
│  business_advisor_engine.py → Strategic advisories    │
│  market_intelligence_engine.py → Market analysis      │
│  infra_demand_engine.py → Infrastructure demand       │
├─────────────────────────────────────────────────────┤
│                    DATA LAYER                        │
│  database.py → SQLite (46 tables, WAL, pooling)      │
│  api_hub_engine.py → 15+ API connectors              │
│  settings_engine.py → 170+ config keys               │
│  vault_engine.py → Fernet encryption (API keys)      │
│  sync_engine.py → Data synchronization               │
├─────────────────────────────────────────────────────┤
│                INFRASTRUCTURE LAYER                  │
│  sre_engine.py → Self-healing + health monitoring    │
│  log_engine.py → JSON-lines centralized logging      │
│  role_engine.py → RBAC (4 roles)                     │
│  model_monitor.py → ML drift detection (PSI)         │
│  resilience_manager.py → Circuit breaker, retry      │
└─────────────────────────────────────────────────────┘
```

### Data Flow
```
External APIs → api_hub_engine.py → lkg_cache/*.json → database.py → SQLite DB
                                                           ↓
User Input → dashboard.py → calculation_engine.py → pricing output
                          → crm_engine.py → contacts/deals/tasks
                          → trading_chatbot_engine.py → AI response
                          → chart_engine.py → Plotly visualization
                          → pdf_export_engine.py → PDF document
```

---

## 6. NAVIGATION & MODULES

### Sidebar Structure (15 Modules)
| # | Module | Pages | Description |
|---|--------|-------|-------------|
| 1 | **Home** | Executive Dashboard | KPI cards, market overview, alerts |
| 2 | **Director Briefing** | Daily Brief | Auto-generated executive summary |
| 3 | — | _divider_ | — |
| 4 | **Procurement** | Import Calculator, Price History, Purchase Advisor, Global Market, Supply Chain | International import cost modeling |
| 5 | **Sales** | Domestic Pricing, Quotation, CRM, Contact Directory, Discussion Guidance | Sales operations & customer management |
| 6 | **Documents** | Document Management (SO/PO/PAY), PDF Archive | Business document generation |
| 7 | **Logistics** | Maritime Intel, Port Tracker, Route Optimizer | Shipping & logistics management |
| 8 | **Intelligence** | News, Market Signals, Correlation, Infra Demand, Competitor Intel, Financial Intel | Market research & analytics |
| 9 | — | _divider_ | — |
| 10 | **Compliance** | GST Monitor, Audit Log, DPDP Compliance | Regulatory compliance |
| 11 | **Reports** | Daily Log, Analytics, PDF Reports, Strategy Panel | Business reporting |
| 12 | — | _divider_ | — |
| 13 | **System Control** | Settings, Health Monitor, SRE Dashboard, Alert Center | System administration |
| 14 | **Developer** | Dev Ops, API Hub, Bug Tracker, System Requirements | Developer tools |
| 15 | **AI & Knowledge** | AI Setup, AI Assistant, Chatbot, Knowledge Base | AI management |

### Page Dispatch (dashboard.py)
- 77 `if/elif` page handlers in main dispatch
- 11 `st.tabs()` groups — all verified matching
- 51 `st.columns()` calls — all verified matching unpacking
- 151 interactive widgets — all have action logic

---

## 7. CORE ENGINES (DETAILED)

### 7.1 dashboard.py — Main Application (5193 lines)
The central Streamlit app with:
- Session state initialization (all keys with defaults)
- Sidebar navigation rendering (from nav_config.py)
- 77 page dispatchers
- News ticker injection (top of every page)
- 19 optional imports with try/except fallback definitions
- Global error handling

### 7.2 database.py — Data Layer (3611 lines)
- SQLite with **WAL mode** for concurrent reads
- **Connection pooling** via `queue.Queue(maxsize=5)`
- **80+ CRUD functions**: get_all_suppliers(), get_all_customers(), get_contacts_count(), add_contact(), update_contact(), etc.
- **Transaction handling** with commit/rollback
- **Schema migrations** via `_schema_version` table (7 migrations)
- **Parameterized queries** throughout (SQL injection prevention)
- Key tables: suppliers(63), customers(3), contacts(132), crm_tasks(8), deals, price_history, fx_history, infra_demand_scores(13,260)

### 7.3 calculation_engine.py — Pricing Engine (1343 lines)
`BitumenCalculationEngine` class handles:

**International Import (CFR → Landed Cost):**
```
FOB (USD/MT)
+ Ocean Freight (USD/MT)
+ Insurance (% of CFR)
= CIF Value
+ Landing Charges (1% of CIF)
= Assessable Value
+ Customs Duty (2.5% on Assessable Value)
+ Port Charges + CHA + Handling
= Total Landed Cost (INR/MT)
```

**Domestic Sales (3-Tier Offers):**
```
Base Price (INR/MT)
+ Margin:
  - Aggressive: +500/MT
  - Balanced: +800/MT
  - Premium: +1200/MT
+ Freight (bulk: ₹5.5/km, drum: ₹6/km)
+ GST (18% on base_price + freight)
= Final Offer Price
```

**Key Business Rules:**
- Minimum margin: ₹500/MT
- GST: 18% (on base + freight for domestic)
- Customs duty: 2.5% (on assessable value = CIF + landing charges)
- Landing charges: 1% of CIF
- Quote validity: 24 hours
- Payment terms: 100% Advance (default)

### 7.4 settings_engine.py — Configuration (485 lines)
- `DEFAULT_SETTINGS` dict with 170+ keys
- JSON file persistence (`settings.json`)
- `load_settings()` / `save_settings()` / `reset_settings()`
- Categories: pricing, GST, customs, freight, CRM, email, WhatsApp, AI, sync, maritime, rotation, broadcast, voice, compliance, scheduling

### 7.5 nav_config.py — Navigation (258 lines)
- `MODULE_NAV` — dict of all 15 modules with icons, labels, pages
- `SIDEBAR_ORDER` — ordered list for sidebar rendering
- `MODULE_ROLE_MAP` — which roles can access which modules
- `PAGE_ROLE_MAP` — granular page-level access control

### 7.6 crm_engine.py — CRM v3.0 (739 lines)
- Tasks stored in SQLite (migrated from JSON)
- Activities stored in JSON
- Contact lifecycle: hot (≤7d) → warm (≤30d) → cold (≤90d) → dormant
- Deal pipeline with stages
- Communication tracking

### 7.7 chart_engine.py — Visualizations (1273 lines)
- 15+ Plotly chart types
- `_format_inr()` — Indian Rupee formatting
- KPI sparklines
- Comparison charts
- Volatility bands, correlation heatmaps
- Export: CSV, PNG
- `procurement_urgency_gauge()`, `volatility_thermometer()`

### 7.8 news_ticker.py — Market News (245 lines)
- **2 ticker rows**: International (crude/forex/logistics) + Domestic India (NHAI/MoRTH/PMGSY)
- CSS animation with hover-to-pause
- Speed configurable via `ticker_speed` setting (default: 600ms)
- Demo fallback headlines when no live data

### 7.9 sync_engine.py — Data Synchronization (949 lines)
- Scheduled data fetching from all API sources
- Configurable intervals per source
- Dead letter queue for failed syncs
- Retry logic with exponential backoff

### 7.10 pdf_export_engine.py — PDF Generation (778 lines)
- Multiple PDF templates: Market Intel, Director Briefing, Alert Center, etc.
- ReportLab + fpdf2 backends
- A4 landscape/portrait
- Automatic header/footer with PPS branding
- Metadata JSON sidecar files

---

## 8. AI & INTELLIGENCE STACK

### 8.1 AI Provider Chain (ai_fallback_engine.py — 1200 lines)
9 providers in priority order with automatic fallback:

| # | Provider | Model | Type | Cost | PII Safe |
|---|----------|-------|------|------|----------|
| 1 | **Ollama** | Llama3 | Local Offline | FREE | Yes |
| 2 | **HuggingFace** | Zephyr-7B | Cloud API | FREE | Yes |
| 3 | **GPT4All** | Phi-3 Mini | Fully Offline | FREE | Yes |
| 4 | **Groq** | Llama-3.3-70B | Cloud (Speed) | FREE | Yes |
| 5 | **Gemini** | 2.0 Flash | Cloud (Analysis) | FREE | Yes |
| 6 | **Mistral** | Small | Cloud (EU-safe) | FREE | Yes |
| 7 | **DeepSeek** | Chat | Cloud (Research) | FREE | **RESTRICTED** |
| 8 | **OpenAI** | GPT-4o-mini | Paid Optional | PAID | Yes |
| 9 | **Claude** | Haiku | Paid Fallback | PAID | Yes |

### 8.2 Task-Based Routing (10 Task Types)
| Task | Primary | Fallback |
|------|---------|----------|
| whatsapp_reply | Groq | Ollama → Gemini |
| email_draft | Gemini | Ollama → Mistral |
| market_analysis | Gemini | DeepSeek → Ollama |
| customer_chat | Groq | Ollama → Gemini |
| director_brief | Gemini | Ollama → Groq |
| call_script | Ollama | Groq → Gemini |
| price_inquiry | Groq | Ollama → Gemini |
| hindi_regional | Gemini | Ollama → Groq |
| private_data | Ollama | GPT4All |
| research_only | DeepSeek | Gemini → Mistral |

### 8.3 PII Filter
- Strips Indian mobile numbers (with/without spaces)
- Strips email addresses
- Strips PAN numbers (ABCDE1234F pattern)
- Strips GSTIN numbers
- Strips Aadhaar numbers
- Applied automatically to restricted providers (DeepSeek)

### 8.4 Sentiment Analysis (finbert_engine.py — 341 lines)
4-tier fallback pipeline:
1. **FinBERT** — Financial domain-specific BERT model
2. **DistilBERT** — General sentiment (lighter)
3. **VADER** — Rule-based sentiment (no model download)
4. **Keyword** — Pattern matching (always available)

### 8.5 Forecasting (ml_forecast_engine.py — 937 lines)
Ensemble of 3 models:
- **Prophet** — Facebook's time series (seasonality, holidays)
- **SARIMAX** — Seasonal ARIMA with exogenous variables
- **ARIMA** — Classic autoregressive model
- Weighted ensemble with confidence intervals
- State-level demand forecasting
- FX rate prediction

### 8.6 RAG Engine (rag_engine.py — 576 lines)
Hybrid search:
- **FAISS** — Dense vector similarity (sentence-transformers embeddings)
- **TF-IDF** — Sparse keyword matching
- **RRF (Reciprocal Rank Fusion)** — Merges both result sets
- Synonym expansion for bitumen domain terms
- Cross-encoder reranking for top results

### 8.7 Knowledge Base (sales_knowledge_base.py — 1451 lines)
- **196 Q&A pairs** across 13 sections
- Sections: company(27), territory(34), sales(24), market(20), technical(16), modified_bitumen(15), grades(13), pricing(13), product(13), payment(9), objections(6), fy26(5), logistics(1)
- Fuzzy matching via `SequenceMatcher`
- `find_best_match(query)` → returns (answer, score, question)
- `get_chatbot_response(query)` → formatted response with confidence

### 8.8 Trading Chatbot (trading_chatbot_engine.py — 1155 lines)
- Combines knowledge base + AI provider responses
- Context-aware: knows current prices, market conditions
- Can handle Hindi/Hinglish queries
- Escalation to human for low-confidence answers

### 8.9 Additional Intelligence Engines
| Engine | Lines | Purpose |
|--------|-------|---------|
| business_advisor_engine.py | 1059 | Strategic business advisories |
| market_intelligence_engine.py | 1025 | Market analysis & signals |
| market_pulse_engine.py | 1138 | Real-time market pulse |
| infra_demand_engine.py | 1253 | India infrastructure demand scoring |
| competitor_intelligence.py | 981 | Competitor tracking |
| recommendation_engine.py | 1214 | Purchase timing recommendations |
| correlation_engine.py | 640 | Price correlation analysis |
| opportunity_engine.py | 482 | Deal opportunity scoring |
| anomaly_engine.py | 343 | Price anomaly detection |
| signal_weight_learner.py | 222 | Dynamic signal weighting (Ridge regression) |
| model_monitor.py | 273 | ML drift detection (PSI) |

---

## 9. DATABASE SCHEMA (46 Tables)

### Database: bitumen_dashboard.db (SQLite, WAL mode)

| Table | Records | Purpose |
|-------|---------|---------|
| **suppliers** | 63 | Supplier master (refineries, traders) |
| **customers** | 3 | Customer master |
| **contacts** | 132 | All contacts (customers, prospects, suppliers) |
| **crm_tasks** | 8 | CRM task tracking |
| **deals** | 0 | Sales deal pipeline |
| **price_history** | 8 | Historical price records |
| **fx_history** | 76 | Forex rate history |
| **infra_demand_scores** | 13,260 | State-wise infra demand data |
| **infra_news** | 444 | Infrastructure news articles |
| **infra_budgets** | 15 | State infrastructure budgets |
| **director_briefings** | 176 | Generated briefing records |
| **alerts** | 12 | System alerts |
| **users** | 1 | User accounts |
| **terms_master** | 16 | Payment/delivery terms |
| **daily_logs** | 2 | Daily activity logs |
| **email_queue** | 2 | Pending emails |
| **whatsapp_queue** | 2 | Pending WhatsApp messages |
| **communications** | 0 | Communication records |
| **comm_tracking** | 0 | Communication analytics |
| **chat_messages** | 0 | Chat history |
| **inventory** | 0 | Stock inventory |
| **opportunities** | 0 | Sales opportunities |
| **sales_orders** | 0 | Sales order documents |
| **purchase_orders** | 0 | Purchase order documents |
| **payment_orders** | 0 | Payment order documents |
| **company_master** | 1 | Company info (PPS Anantam) |
| **bank_master** | 1 | Bank account details |
| **transporters** | 1 | Transporter details |
| **recipient_lists** | 2 | Broadcast recipient lists |
| **_schema_version** | 7 | Migration tracking |
| **_doc_counters** | 3 | Document numbering (SO/PO/PAY) |
| **sqlite_sequence** | 27 | Auto-increment tracking |
| **audit_log** | 1 | System audit trail |
| **contact_rotation_log** | 0 | Contact rotation history |
| **festival_broadcasts** | 0 | Festival message records |
| **infra_alerts** | 2 | Infrastructure alerts |
| **infra_sources** | 1 | Data source registry |
| **missing_inputs** | 0 | Missing data tracker |
| **price_update_log** | 0 | Price change audit |
| **share_links** | 0 | Shareable report links |
| **share_schedules** | 0 | Scheduled shares |
| **sms_queue** | 0 | Pending SMS messages |
| **source_registry** | 0 | API source registry |
| **sync_logs** | 0 | Sync operation logs |
| **whatsapp_incoming** | 0 | Incoming WA messages |
| **whatsapp_sessions** | 0 | WA session tracking |

---

## 10. API CONNECTORS (15+ Sources)

### api_hub_engine.py (2186 lines)

| Connector | Source | Data | TTL |
|-----------|--------|------|-----|
| eia_crude | US EIA API | WTI/Brent crude prices | Varies |
| fawazahmed0_fx | fawazahmed0 | Live forex rates | Short |
| frankfurter_fx | Frankfurter API | EUR/USD/INR rates | Short |
| fred_macro | US Federal Reserve | Macro indicators | Long |
| rbi_fx_historical | RBI | Historical INR rates | Long |
| newsapi | NewsAPI.org | Global news articles | 10 min |
| gnews_rss | Google News RSS | Free news feed | 10 min |
| openweather | OpenWeatherMap | Weather (port regions) | 15 min |
| open_meteo_hub | Open-Meteo | Free weather data | 15 min |
| maritime_intel | Multiple | Vessel & port data | 15 min |
| world_bank_india | World Bank | India economic data | Long |
| un_comtrade | UN Comtrade | Trade statistics | Long |
| comtrade_hs271320 | UN Comtrade | HS 271320 (bitumen) | Long |
| data_gov_in_highways | data.gov.in | India highway data | Long |
| ppac_proxy | PPAC India | Petroleum prices | Varies |

### Cache Strategy
- **Last-Known-Good (LKG)**: All API responses cached in `lkg_cache/*.json`
- **Smart TTL**: Different refresh intervals per data type
- **Dead Letter Queue**: Failed API calls queued for retry
- **Fallback**: If API fails, LKG cache serves stale data with warning

---

## 11. SETTINGS & CONFIGURATION (170+ Keys)

### Key Categories

**Pricing & Business Rules:**
- `margin_min_per_mt`: 500 (minimum margin ₹/MT)
- `gst_rate_pct`: 18
- `customs_duty_pct`: 2.5
- `landing_charges_pct`: 1.0
- `bulk_rate_per_km`: 5.5, `drum_rate_per_km`: 6.0
- `quote_validity_hours`: 24
- `payment_default_terms`: "100% Advance"

**API Keys (stored encrypted via vault_engine):**
- `api_key_eia`, `api_key_fred`, `api_key_data_gov_in`
- `api_key_openweather`, `api_key_newsapi`
- `groq_api_key`, `gemini_api_key`, `mistral_api_key`, `deepseek_api_key`
- `sendgrid_api_key`, `fast2sms_api_key`, `bhashini_api_key`

**Communication:**
- Email: `email_enabled`, rate limits, auto-send toggles
- WhatsApp: `whatsapp_enabled`, rate limits (20/min, 1000/day)
- SMS: `sms_enabled`, Fast2SMS integration
- Rotation: `daily_rotation_enabled`, count(2400), cycle(10 days)

**AI Configuration:**
- `ai_enabled`: True
- `ai_provider_auto_disable_threshold`: 50 (errors before disable)
- `ai_provider_cooldown_minutes`: 15
- `ai_deepseek_pii_filter`: True
- `ai_auto_reply_enabled`: False
- `ai_auto_reply_confidence_threshold`: 0.7

**News Ticker:**
- `ticker_speed`: 600 (CSS animation duration in ms)

**CRM Thresholds:**
- `crm_hot_threshold_days`: 7
- `crm_warm_threshold_days`: 30
- `crm_cold_threshold_days`: 90

**Maritime:**
- `maritime_enabled`: True
- `maritime_priority_ports`: ['Mundra', 'Kandla', 'Mumbai']
- `maritime_vessel_count`: 12

**Owner Identity:**
- `owner_name`: "PRINCE P SHAH"
- `owner_mobile`: "+91 7795242424"
- `owner_email`: "princepshah@gmail.com"
- `company_trade_name`: "PACPL"

---

## 12. BUSINESS RULES & FORMULAS

### International Import Cost (CFR → Landed)
```python
CIF = FOB + Ocean_Freight + Insurance
Landing_Charges = CIF × 1%
Assessable_Value = CIF + Landing_Charges
Customs_Duty = Assessable_Value × 2.5%
Port_Charges = per-port rates (Kandla: ₹8000 berthing)
CHA = per-MT rate (Kandla: ₹70/MT)
Handling = per-MT rate (Kandla: ₹90/MT)
Landed_Cost_INR = (Assessable_Value + Customs_Duty) × FX_Rate + Port_Charges + CHA + Handling
```

### Domestic Sales Pricing
```python
Base_Price = Landed_Cost or Market_Price
Freight = Distance_km × Rate_per_km  (bulk: 5.5, drum: 6.0)

Aggressive_Offer = Base_Price + 500 + Freight + GST(18% of Base+Freight)
Balanced_Offer  = Base_Price + 800 + Freight + GST(18% of Base+Freight)
Premium_Offer   = Base_Price + 1200 + Freight + GST(18% of Base+Freight)
```

### CRM Contact Temperature
```python
if last_contact_days <= 7:   → HOT 🔴
if last_contact_days <= 30:  → WARM 🟡
if last_contact_days <= 90:  → COLD 🔵
else:                        → DORMANT ⚪
```

### Bitumen Grades
VG10, VG30, VG40, Emulsion, CRMB-55, CRMB-60, PMB

### Ports
Kandla, Mundra, Mangalore, JNPT, Karwar, Haldia, Ennore, Paradip

---

## 13. SECURITY & ACCESS CONTROL

### Role-Based Access Control (role_engine.py — 367 lines)
| Role | Access Level |
|------|-------------|
| **director** | Full access — all modules, all settings |
| **sales** | Sales, CRM, Documents, Intelligence — no system control |
| **operations** | Procurement, Logistics, Documents — no AI settings |
| **viewer** | Read-only — dashboards and reports only |

- Session timeout: 30 minutes (configurable)
- Login rate limiting: 5 attempts per 5 minutes
- RBAC default: disabled (all users = director)

### Vault Encryption (vault_engine.py — 218 lines)
- **Fernet symmetric encryption** for API keys
- **PBKDF2** key derivation from master password
- Encrypted at rest in `vault.dat`
- Transparent encrypt/decrypt in settings engine

### Data Protection
- DPDP compliance mode (configurable)
- Unsubscribe footer: "To unsubscribe, reply STOP."
- Consent required for broadcasts
- PII filter for AI providers (strips phone/email/PAN/GSTIN/Aadhaar)
- Parameterized SQL queries throughout (no SQL injection)
- `unsafe_allow_html=True` only for internal HTML (no user input flows)

---

## 14. FILE-BY-FILE REFERENCE

### Top-Level Engines (by category)

#### Core Application
| File | Lines | Purpose |
|------|-------|---------|
| dashboard.py | 5193 | Main Streamlit app, routing, UI |
| database.py | 3611 | SQLite CRUD, pooling, migrations |
| calculation_engine.py | 1343 | Pricing formulas (import + domestic) |
| settings_engine.py | 485 | 170+ configuration keys |
| nav_config.py | 258 | Module/page navigation structure |
| company_config.py | 54 | Company identity constants |

#### AI & Intelligence
| File | Lines | Purpose |
|------|-------|---------|
| ai_fallback_engine.py | 1200 | 9-provider AI chain + PII filter |
| trading_chatbot_engine.py | 1155 | AI chatbot with context |
| sales_knowledge_base.py | 1451 | 196 Q&A pairs, fuzzy search |
| business_knowledge_base.py | 1852 | Extended business knowledge |
| ai_assistant_engine.py | 486 | AI assistant wrapper |
| ai_data_layer.py | 565 | AI data access layer |
| ai_learning_engine.py | 339 | Learning from interactions |
| ai_message_engine.py | 176 | AI message generation |
| ai_reply_engine.py | 761 | Auto-reply engine |
| ai_setup_engine.py | 773 | AI provider setup wizard |
| ai_workers.py | 568 | Background AI workers |
| finbert_engine.py | 341 | 4-tier sentiment pipeline |
| ml_forecast_engine.py | 937 | Prophet+SARIMAX+ARIMA ensemble |
| ml_boost_engine.py | 768 | XGBoost/LightGBM boosting |
| rag_engine.py | 576 | Hybrid FAISS+TF-IDF search |
| nlp_extraction_engine.py | 445 | NLP entity extraction |
| signal_weight_learner.py | 222 | Dynamic signal weighting |
| model_monitor.py | 273 | ML drift detection (PSI) |
| business_context.py | 1210 | Business context for AI |

#### Market & Intelligence
| File | Lines | Purpose |
|------|-------|---------|
| api_hub_engine.py | 2186 | 15+ API connectors with LKG cache |
| market_intelligence_engine.py | 1025 | Market analysis |
| market_pulse_engine.py | 1138 | Real-time market pulse |
| news_engine.py | 1037 | News fetching & processing |
| infra_demand_engine.py | 1253 | India infrastructure demand |
| competitor_intelligence.py | 981 | Competitor tracking |
| recommendation_engine.py | 1214 | Purchase recommendations |
| correlation_engine.py | 640 | Price correlation analysis |
| business_advisor_engine.py | 1059 | Strategic advisories |
| contractor_osint.py | 2294 | Contractor OSINT intelligence |
| maritime_intelligence_engine.py | 1108 | Maritime intel & vessel tracking |

#### CRM & Communication
| File | Lines | Purpose |
|------|-------|---------|
| crm_engine.py | 739 | CRM v3.0 (tasks, activities, pipeline) |
| communication_engine.py | 876 | Communication templates |
| email_engine.py | 788 | Email sending (SendGrid) |
| whatsapp_engine.py | 822 | WhatsApp Business API |
| sms_engine.py | 397 | SMS via Fast2SMS |
| rotation_engine.py | 727 | Contact rotation scheduling |
| contact_import_engine.py | 700 | Bulk contact import |
| discussion_guidance_engine.py | 1333 | Sales discussion guidance |
| negotiation_engine.py | 394 | Negotiation strategies |
| opportunity_engine.py | 482 | Deal opportunity scoring |
| recipient_selector.py | 268 | Broadcast recipient selection |
| bhashini_engine.py | 154 | Hindi/regional translation |

#### UI & Visualization
| File | Lines | Purpose |
|------|-------|---------|
| chart_engine.py | 1273 | 15+ Plotly chart types |
| news_ticker.py | 245 | Dual-stream market ticker |
| market_ticker.py | 523 | Market data ticker |
| top_bar.py | 248 | Top navigation bar |
| subtab_bar.py | 164 | Sub-tab navigation |
| pdf_export_engine.py | 778 | PDF report generation |
| pdf_export_bar.py | 293 | PDF export action bar |
| pdf_generator.py | 195 | FPDF-based PDF creation |
| document_pdf_engine.py | 927 | Document PDF templates |
| share_button.py | 323 | Share/export button |
| interactive_chart_helpers.py | 354 | Chart interaction helpers |

#### Infrastructure & Ops
| File | Lines | Purpose |
|------|-------|---------|
| sre_engine.py | 1644 | Self-healing, health monitoring |
| sync_engine.py | 949 | Data synchronization |
| resilience_manager.py | 714 | Circuit breaker, retry logic |
| resilience_config.py | 555 | Resilience configuration |
| log_engine.py | 157 | Centralized JSON-lines logging |
| role_engine.py | 367 | RBAC (4 roles) |
| vault_engine.py | 218 | Fernet encryption for keys |
| page_registry.py | 140 | Decorator-based page dispatch |
| anomaly_engine.py | 343 | Price anomaly detection |
| system_control_engine.py | 690 | System control panel |

#### Data & Utilities
| File | Lines | Purpose |
|------|-------|---------|
| seed_data.py | 360 | Initial data seeding |
| distance_matrix.py | 412 | City-to-city distances |
| india_localization.py | 107 | India-specific formatting |
| free_api_registry.py | 315 | Free API source registry |
| google_sheets_engine.py | 238 | Google Sheets integration |
| data_confidence_engine.py | 536 | Data quality scoring |
| missing_inputs_engine.py | 453 | Missing data detection |

---

## 15. DATA FILES & CACHES

### LKG Cache (lkg_cache/)
| File | Content |
|------|---------|
| eia_crude.json | WTI/Brent crude oil prices |
| fx.json | USD/INR forex rates |
| gold_price.json | Gold spot prices |
| news.json | Cached news articles |
| ports.json | Port status data |
| refinery.json | Refinery output data |
| weather.json | Weather for port regions |
| cement_index.json | Cement price index |
| eia_steo.json | EIA short-term outlook |
| fred_macro.json | Fed macro indicators |
| iocl_circular.json | IOCL price circulars |
| maritime_intel.json | Maritime intelligence |

### ML Models (ml_models/)
| File | Content |
|------|---------|
| business_advisory.json | Advisory model state |
| predictions_log.json | Prediction history |
| recommendations.json | Recommendation cache |
| model_health.json | Model health metrics |

### Log/State Files (root)
| File | Content |
|------|---------|
| ai_fallback_log.json | AI provider usage log |
| ai_learning_log.json | AI learning records |
| api_cache.json | API response cache |
| api_health_log.json | API health tracking |
| api_stats.json | API usage statistics |
| sre_metrics.json | SRE health metrics |
| sre_health_status.json | Current health state |
| sre_audit_log.json | SRE audit trail |
| sync_logs.json | Sync operation logs |
| market_alerts.json | Active market alerts |
| auto_insights.json | Auto-generated insights |
| hub_cache.json | Hub connector cache |
| hub_catalog.json | Connector catalog |
| hub_activity_log.json | Hub activity log |

### Table Cache Files (root, tbl_*)
| File | Content |
|------|---------|
| tbl_crude_prices.json | Crude oil price history |
| tbl_fx_rates.json | Forex rate history |
| tbl_news_feed.json | News feed cache |
| tbl_market_signals.json | Market signal data |
| tbl_insights.json | Generated insights |
| tbl_corr_results.json | Correlation results |
| tbl_maritime_intel.json | Maritime intelligence |
| tbl_maritime_routes.json | Shipping routes |
| tbl_weather.json | Weather data |
| tbl_world_bank.json | World Bank indicators |
| tbl_purchase_advisor.json | Purchase advisor data |

---

## 16. KNOWN ISSUES & OPEN ITEMS

### Fixed Issues (05-Mar-2026)
| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| 1 | CRITICAL | `finbert_engine.py` — `_HAS_VADER` used before definition | Moved VADER detection block before usage |
| 2 | HIGH | CRM dashboard contacts showing 0 (key mismatch) | Corrected key mapping in crm_automation_dashboard.py |
| 3 | MEDIUM | Missing `ticker_speed` in DEFAULT_SETTINGS | Added `"ticker_speed": 600` |

### Open Items
| # | Severity | Issue | Notes |
|---|----------|-------|-------|
| 1 | MEDIUM | News ticker has 2 rows, spec says 6 | Current: International + Domestic. Could split into: Crude, Forex, Logistics, NHAI, MoRTH, PMGSY |
| 2 | MEDIUM | `save_settings()` no error handling for write failure | Add try/except around JSON write |
| 3 | MEDIUM | `party_matching_engine.py` SQL table names via f-strings | Currently safe (internal constants), but should use whitelist validation |
| 4 | LOW | `pickle.load()` in rag_engine.py | Local cache files only — low risk |
| 5 | LOW | No hard delete functions in database.py | Design decision — all deletes are soft-delete |
| 6 | LOW | `unsafe_allow_html=True` in multiple locations | All HTML from internal data — no user input flows in |

---

## 17. DEPLOYMENT & OPERATIONS

### Running the Application
```bash
# Development
streamlit run dashboard.py

# Production (headless, custom port)
streamlit run dashboard.py --server.port 8501 --server.headless true
```

### Database Backup
```bash
# SQLite backup (while running — WAL mode handles concurrent access)
cp bitumen_dashboard.db bitumen_dashboard_backup_$(date +%Y%m%d).db
```

### Monitoring
- **SRE Dashboard**: System Control > SRE Dashboard — real-time health
- **API Health**: Developer > API Hub — connector status & TTL
- **AI Health**: AI & Knowledge > AI Setup — provider status
- **Logs**: `logs/` directory — JSON-lines format, auto-rotated

### Key Operational Commands
```bash
# Check database integrity
python -c "from database import get_all_suppliers; print(len(get_all_suppliers()), 'suppliers')"

# Verify AI providers
python -c "from ai_fallback_engine import get_provider_status; print(len(get_provider_status()), 'providers')"

# Check knowledge base
python -c "from sales_knowledge_base import get_knowledge_count; print(get_knowledge_count(), 'Q&A pairs')"

# Compile check (all files)
python -m py_compile dashboard.py && echo "OK"
```

### Environment Variables (Optional)
```bash
GROQ_API_KEY=gsk_...          # Groq (free)
GEMINI_API_KEY=AI...          # Google Gemini (free)
MISTRAL_API_KEY=...           # Mistral (free)
DEEPSEEK_API_KEY=sk-...       # DeepSeek (free, research only)
OPENAI_API_KEY=sk-...         # OpenAI (paid)
ANTHROPIC_API_KEY=sk-ant-...  # Claude (paid)
HUGGINGFACE_TOKEN=hf_...      # HuggingFace (optional)
```

---

## 18. DEVELOPMENT HISTORY

### Phase 1 — Foundation (Initial)
- Basic Streamlit dashboard
- WTI/Brent price display
- Excel data import
- Seed data (63 suppliers, 3 customers)

### Phase 2 — Database Migration
- JSON → SQLite migration
- Calculation engine (CFR + domestic pricing)
- Settings engine
- Connection pooling, WAL mode

### Phase 3 — New Homepage & Navigation
- Executive dashboard with KPI cards
- 8-category navigation
- 4 new pages (Director Briefing, CRM, Market Intel, Reports)

### Phase 4 — Intelligence Engines
- Opportunity engine, communication engine
- Negotiation strategies
- CRM v2.0 with pipeline

### Phase 5 — System Improvement (04-Mar-2026)
- **1.1-1.3**: DB transactions, schema migrations, vault encryption
- **1.4**: Role-based auth (4 roles, timeout, rate limiting)
- **1.5**: CRM JSON → SQLite migration
- **2.1**: Customs duty formula fix (landing charges on assessable value)
- **2.2**: GST on domestic freight fix
- **3.1**: FinBERT+VADER sentiment pipeline
- **3.2-3.5**: SARIMAX, ensemble forecasting, state demand, FX, signal weights
- **3.6-3.8**: RAG hybrid search, model monitor, backtesting
- **4**: Page registry, smart API scheduling, connection pooling
- **5**: Chart exports, KPI sparklines, resource monitoring
- **6**: Centralized logging, BDI/Gold connectors, .gitignore security

### Phase 6 — Multi-AI Provider Stack (05-Mar-2026)
- 9-provider fallback chain (Ollama → Claude)
- Task-based routing (10 task types)
- PII filter for restricted providers
- Health tracking with auto-disable/recover
- Provider setup wizard

### Phase 7 — Knowledge Base Expansion (05-Mar-2026)
- Expanded from 58 → 196 Q&A pairs
- 13 sections covering full sales training
- Sourced from 55-page training document

### Phase 8 — Full Audit & QA (05-Mar-2026)
- Comprehensive audit across 238 files
- 28/28 smoke tests passed
- 3 critical/high bugs fixed
- 6 open items documented

---

## EMERGENCY CONTACTS & SUPPORT

| Role | Name | Contact |
|------|------|---------|
| Business Owner | Prince P Shah | +91 7795242424 |
| Email | — | princepshah@gmail.com |
| Company | PPS Anantam / PACPL | Vadodara, Gujarat |

---

*Document generated: 05-Mar-2026 | PPS Anantam Bitumen Sales Dashboard v5.0.0*
*Total Codebase: 238 Python files | 110,578 lines of code | 46 database tables | 15 modules | 84 pages*
