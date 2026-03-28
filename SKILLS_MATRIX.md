# PPS Anantam — Skills Matrix & Operational Runbook

## 1. System Architecture

```
Dashboard (Streamlit 1.53)
├── 11 Sidebar Modules → 44 Sub-tabs → 66+ Pages
├── 13 Background Daemon Threads
│   ├── AutoHealthChecker (30 min)
│   ├── SREBackground (15 min)
│   ├── HubScheduler (60 min)
│   ├── SyncScheduler (60 min)
│   ├── EmailScheduler (5 min)
│   ├── WhatsAppScheduler (2 min)
│   ├── HeartbeatChecker (30 sec)
│   └── 6 AI Workers (30 min - 24 hr)
├── Engines (15+)
│   ├── calculation_engine, opportunity_engine, negotiation_engine
│   ├── crm_engine, communication_engine, sync_engine
│   ├── market_intelligence_engine, purchase_advisor_engine
│   ├── sre_engine, anomaly_engine, data_confidence_engine
│   ├── resilience_manager, resilience_config (NEW)
│   └── api_manager, api_hub_engine, settings_engine
└── Data Layer
    ├── SQLite: bitumen_dashboard.db (27 tables, 44 indexes)
    ├── JSON: 70+ data/cache/log files
    └── LKG Cache: lkg_cache/ directory (snapshots)
```

## 2. Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| UI Framework | Streamlit | 1.53.1 |
| Language | Python | 3.11+ |
| Database | SQLite (WAL mode) | 3.x |
| Charts | Plotly | 5.x |
| Market Data | yfinance | 0.2.x |
| HTTP | requests | 2.x |
| Timezone | pytz | 2024.x |
| ML (optional) | Prophet, scikit-learn, XGBoost, LightGBM | various |
| NLP (optional) | transformers (FinBERT), spaCy | various |

## 3. For New Developers

### Setup
```bash
cd "bitumen sales dashboard"
pip install -r requirements.txt
streamlit run dashboard.py
```

### Key File Patterns
- **Engines** (`*_engine.py`): Business logic, no UI. Pure Python.
- **Command Intel** (`command_intel/*.py`): Streamlit page renderers. Each has `render()`.
- **Config** (`settings_engine.py`, `resilience_config.py`): Centralized settings.
- **Data** (`tbl_*.json`): Normalized API data tables.
- **Logs** (`*_log.json`): Append-only audit trails (max capped).
- **Cache** (`*_cache.json`): TTL-based response cache.

### Navigation Flow
1. `dashboard.py` → reads `nav_config.py` MODULE_NAV
2. Sidebar renders modules, sub-tabs render pages
3. `if/elif selected_page ==` chain dispatches to `command_intel/*.py`

## 4. Operational Runbook

### Daily Checks
1. Open System Control Center → verify health score >= 80
2. Check Health Monitor → all traffic lights green
3. Review SRE Dashboard → Alerts tab for P0/P1

### Common Issues & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| Stale data | Yellow/Red traffic lights | Check API health, restart hub scheduler |
| Dead thread | Worker shows "Dead" in Health Monitor | HeartbeatMonitor auto-restarts (3x/hr) |
| API rate limit | 429 errors in API error log | Wait for backoff; check api_stats.json |
| Circuit breaker open | "OPEN" in fallback chain | Wait for recovery_timeout; check API endpoint |
| DLQ growing | Pending jobs in Dead Letter Queue | Review dead_letter_queue.json; fix root cause |

### Restart Procedures
```bash
# Restart Streamlit (restarts all daemon threads)
# Press Ctrl+C then:
streamlit run dashboard.py

# Force re-sync all data
# Use UI: System Control Center → Sync button
```

## 5. Data Sources (39 Total)

### Free (No Key Required) — 25 Sources
- **yfinance**: Brent, WTI, OPEC, DXY, Nifty, Sensex, VIX, Gold, BDI
- **Frankfurter**: ECB FX rates (USD/INR, EUR/INR, GBP/INR)
- **fawazahmed0**: CDN-based currency rates
- **Open-Meteo**: Weather for 5 port cities
- **Google News RSS**: Oil/bitumen headlines
- **12 RSS feeds**: OilPrice, EIA, Reuters, CNBC, PIB, etc.
- **World Bank**: GDP, CPI, infrastructure investment
- **TimeAPI**: IST system clock

### Optional (Free with API Key) — 5 Sources
- **EIA**: Crude oil spot prices (eia.gov)
- **FRED**: Federal Reserve macro indicators
- **data.gov.in**: NHAI highway data
- **OpenWeather**: Enhanced weather data
- **NewsAPI**: Professional news aggregation

## 6. SRE Procedures

### Alert Response SLA
| Severity | Response | Escalation |
|----------|----------|------------|
| P0 (Critical) | Immediate | Auto-created by HeartbeatMonitor |
| P1 (High) | 30 min | Auto-escalate to P0 after 24h |
| P2 (Medium) | 4 hours | Daily review |

### Self-Healing Workflow
```
1. Health Check detects issue
2. SelfHealEngine retries (3x with [5, 15, 30]s backoff)
3. If healed → resolved, logged
4. If not healed → Bug created + Alert fired
5. Failed job → Dead Letter Queue (retry at 5m, 30m, 2h)
6. After 3 DLQ failures → Archived, manual review needed
```

### Recovery Chain
```
Live API → Fallback API → LKG Cache → Static Reference → Emergency Value
   95%         85%           60%           30%              25%
```
