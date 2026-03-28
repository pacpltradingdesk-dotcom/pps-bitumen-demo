# PPS ANANTAM — COMPLETE SYSTEM AUDIT & IMPROVEMENT REPORT
### Senior AI System Architect Analysis | 04-Mar-2026
### Version: v4.0.0 | 93+ Files | 47,000+ LOC | 65 Pages | 14 APIs

---

# STEP 1 — FULL SYSTEM UNDERSTANDING

## 1.1 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PPS ANANTAM DASHBOARD v4.0                          │
│              Agentic AI Bitumen Sales Intelligence Platform                 │
├─────────────────┬──────────────────┬───────────────────┬───────────────────┤
│   PRESENTATION  │   INTELLIGENCE   │   DATA ENGINES    │   INFRASTRUCTURE  │
│                 │                  │                   │                   │
│ dashboard.py    │ calculation_eng  │ api_hub_engine    │ sre_engine        │
│ nav_config.py   │ opportunity_eng  │ sync_engine       │ database.py       │
│ subtab_bar.py   │ negotiation_eng  │ api_manager       │ settings_engine   │
│ top_bar.py      │ communication_e  │ 14 API connectors │ role_engine       │
│ chart_engine    │ crm_engine       │                   │ data_confidence   │
│ 41 cmd_intel/   │ market_intel_eng │ SQLite (20 tbl)   │ missing_inputs    │
│ ui_badges       │ price_prediction │ 23+ JSON files    │ pdf_generator     │
│ sales_workspace │ ml_forecast_eng  │                   │ optimizer         │
│                 │ risk_scoring     │                   │ source_master     │
└─────────────────┴──────────────────┴───────────────────┴───────────────────┘
```

## 1.2 What The Dashboard Does

PPS Anantam is an **enterprise AI-powered bitumen trading decision system** for a Vadodara (Gujarat) based company. It handles the complete bitumen sales lifecycle:

| Function | What It Does | Engine |
|----------|-------------|--------|
| **Price Discovery** | Calculates landed cost from 32 sources (16 refineries, 8 import terminals, 8 decanters) with GST, freight, customs duty | calculation_engine.py |
| **Opportunity Detection** | Auto-discovers profitable buying/selling opportunities from price gaps, dormant customers, seasonal patterns | opportunity_engine.py |
| **Negotiation Support** | Generates 3-tier offer prices, objection handling scripts, closing strategies per customer | negotiation_engine.py |
| **Communication** | Auto-generates WhatsApp, Email, Call scripts contextually | communication_engine.py |
| **CRM Management** | Auto-profile updates, hot/warm/cold scoring, task management | crm_engine.py |
| **Market Intelligence** | 10-signal composite (crude, FX, weather, news, infra, tenders, economic, search, ports, custom) | market_intelligence_engine.py |
| **Price Prediction** | 24-month forward forecast with confidence scoring + 3-year accuracy tracking | price_prediction.py + ml_forecast |
| **Import Costing** | Full Iraq-to-India landed cost calculator with sensitivity analysis | import_cost_model.py |
| **Supply Chain** | 8-stage shipment pipeline tracking (Loading → Payment) | supply_chain.py |
| **Risk Scoring** | 6-dimension risk assessment (Market, Supply, Financial, Compliance, Legal, Margin) | risk_scoring.py |
| **Financial Intelligence** | Vessel P&L, cashflow stress, receivable aging, what-if simulator | financial_intel.py |
| **Self-Healing** | Auto-detects API failures, data corruption, worker crashes + auto-repair | sre_engine.py |
| **Data Sync** | 18-step pipeline syncing 14 APIs → 23+ JSON tables every 60 minutes | sync_engine.py + api_hub_engine.py |

## 1.3 Key Calculations & Formulas

### International Landed Cost (₹/MT):
```
FOB (₹) = FOB_USD × USD/INR
+ Freight (₹) = Freight_USD × USD/INR
+ Insurance = CIF × 0.5%
+ Port Berthing = ₹10,000 / vessel_qty
+ CHA = ₹75/MT
+ Handling = ₹100/MT
+ Customs Duty = CIF × 2.5%
+ GST = total_before_gst × 18%
= LANDED COST
```

### Domestic Landed Cost (₹/MT):
```
Base Price × 1.18 (GST) + Distance_km × Rate/km
Bulk: ₹5.5/km | Drum: ₹6.0/km
```

### 3-Tier Offer Pricing:
```
Aggressive = Landed Cost + ₹500/MT margin
Balanced   = Landed Cost + ₹800/MT margin
Premium    = Landed Cost + ₹1,200/MT margin
```

### Price Prediction Model:
```
Price = prev + base_drift × seasonality + crude_factor + fx_factor
Crude-to-Bitumen: ₹ = 38,000 + (crude - 60) × 450 + (usdinr - 84) × 120
Confidence Decay: 84% - 1.4%/month - 5%(brent_unstable) - 4%(fx_unstable)
```

### Risk Health Score:
```
Weights: Market(0.20) + Supply(0.15) + Financial(0.20) + Compliance(0.15) + Legal(0.10) + Margin(0.20)
Health = 100 - weighted_risk (capped 10-95)
```

## 1.4 Current API Infrastructure

| API | Status | Data | Reliability |
|-----|--------|------|-------------|
| **yfinance** (Brent/WTI) | LIVE (fallback for EIA) | Crude prices | 90% |
| **Frankfurter FX** (ECB) | LIVE | USD/INR, EUR/INR | 96% |
| **Open-Meteo** | LIVE | Weather for 5 cities | 88% |
| **Google News RSS** | LIVE (fallback for NewsAPI) | Oil/bitumen headlines | 80% |
| **fawazahmed0 FX CDN** | LIVE | Backup FX rates | 85% |
| **World Bank** | LIVE | GDP, CPI for India | 90% |
| **PPAC Proxy** | LIVE (static ref) | Refinery production | 70% |
| **EIA Crude** | DISABLED (no key) | WTI, Brent, petroleum | — |
| **UN Comtrade** | FAILING | HS 271320 imports | 45% |
| **OpenWeather** | DISABLED (no key) | Detailed weather | — |
| **NewsAPI** | DISABLED (no key) | Global news | — |
| **data.gov.in** | DISABLED (no key) | NHAI highway data | — |
| **FRED** | DISABLED (no key) | Macro indicators | — |

## 1.5 Database Schema Summary

**20 Tables, 30 Indexes, SQLite WAL Mode:**
- Business: suppliers (63), customers (3), deals, inventory
- Market: price_history, fx_history
- Communications: email_queue, whatsapp_queue, whatsapp_sessions, whatsapp_incoming
- Intelligence: opportunities, alerts, director_briefings, daily_logs
- Operations: sync_logs, missing_inputs, source_registry
- RBAC: users, audit_log, recipient_lists

---

# STEP 2 — IDENTIFIED WEAK AREAS

## 2.1 Critical Weaknesses

| # | Area | Issue | Impact | Severity |
|---|------|-------|--------|----------|
| 1 | **Price Prediction** | Uses heuristic fallback (Prophet rarely available); mock historical data with seed(42) | Predictions unreliable; 72% accuracy claimed but not validated | 🔴 CRITICAL |
| 2 | **Risk Scoring** | Entirely simulated with `np.random.normal()` seeded by date — no real data | Risk scores are fake; not actionable | 🔴 CRITICAL |
| 3 | **Demand Analytics** | 8 hardcoded contractor profiles; no ML model; manual seasonal percentages | Cannot forecast real demand; no learning | 🔴 CRITICAL |
| 4 | **Supply Chain** | 5 hardcoded mock vessels; no real vessel tracking API | No real-time shipment visibility | 🔴 CRITICAL |
| 5 | **Financial Intel** | All data hardcoded (5 vessels, receivable buckets); no accounting integration | Financial metrics are fabricated | 🟡 HIGH |
| 6 | **Strategy Panel** | Recommendations based on random sampling + heuristics; no feedback loop | Strategic advice is unreliable | 🟡 HIGH |
| 7 | **UN Comtrade API** | Consistently failing; import data uses stale static cache | No live trade flow intelligence | 🟡 HIGH |
| 8 | **5 Disabled APIs** | EIA, OpenWeather, NewsAPI, data.gov.in, FRED — all have free tiers but keys not configured | Missing data sources that are easily available | 🟡 HIGH |
| 9 | **No Unit Tests** | Zero test coverage across 93+ files; no pytest or unittest | Regressions go undetected | 🟡 HIGH |
| 10 | **Home Page Performance** | Loads ALL data sources on every render; single point of failure | Slow page load; crashes if any API down | 🟡 HIGH |

## 2.2 Missing Data Sources

| Data | Currently | Should Be |
|------|-----------|-----------|
| IOCL published bitumen prices | Not integrated | Scrape/API for actual revision prices |
| Vessel AIS tracking | Mock data | MarineTraffic or VesselFinder free tier |
| Indian port schedules | Static estimates | Sagarmala/IPA port data |
| Freight rates (tanker) | Hardcoded $35/MT | Baltic Exchange / Freightos free API |
| India fuel/bitumen demand | Manual seasonal % | PPAC monthly reports (PDF scraping) |
| Tender data (NHAI/PWD) | Not live | GeM Portal / data.gov.in free API |
| Competitor pricing | Not tracked | Manual entry + web scraping |
| Indian inflation (CPI) | World Bank (yearly) | RBI API (monthly) |
| India PMI index | Not tracked | Trading Economics free tier |
| BIS standards updates | Not tracked | BIS portal monitoring |

## 2.3 Missing AI/ML Capabilities

| Gap | Impact |
|-----|--------|
| No trained ML model for bitumen price prediction | Heuristic gives ~72% accuracy vs 85%+ possible |
| No anomaly detection on live data | Price spikes, data corruption go undetected |
| No NLP for news sentiment scoring | News headlines not scored for market impact |
| No demand forecasting model | Seasonal patterns hardcoded, not learned |
| No recommendation learning | System doesn't learn from past decision outcomes |
| No supply chain disruption detection | No ML model for logistics risk prediction |
| No customer churn prediction | CRM doesn't predict which customers will go dormant |

## 2.4 UI/UX Inefficiencies

| Issue | Location |
|-------|----------|
| No bulk edit mode for pricing | Data Manager page |
| Mobile layout not optimized (3-col pricing) | Pricing Calculator |
| No undo/rollback for price changes | All edit pages |
| No saved search presets | Source Directory, CRM |
| Tables overflow on small screens | Throughout |
| Color-only status indicators (accessibility) | Risk scoring, alerts |
| No keyboard shortcuts | Navigation |

---

# STEP 3 — RECOMMENDED FREE APIs

## 3.1 Commodity & Crude Oil Prices

### API 1: Alpha Vantage (Commodities)
- **Purpose**: WTI, Brent, natural gas, heating oil prices
- **Data Fields**: date, open, high, low, close, volume
- **Free Tier**: 25 requests/day, 500/month
- **Integration**: `GET https://www.alphavantage.co/query?function=WTI&apikey=YOUR_KEY`
- **Improvement**: More reliable than yfinance for historical data; includes daily OHLCV

### API 2: FRED (Federal Reserve Economic Data)
- **Purpose**: Brent (DCOILBRENTEU), WTI (DCOILWTICO), USD/INR (DEXINUS)
- **Data Fields**: date, value
- **Free Tier**: 120 requests/minute (free key from fred.stlouisfed.org)
- **Integration**: `GET https://api.stlouisfed.org/fred/series/observations?series_id=DCOILBRENTEU&api_key=KEY`
- **Improvement**: Official US government data; 30+ year history for backtesting

### API 3: EIA (US Energy Information Administration)
- **Purpose**: Petroleum supply/demand, refinery utilization, crude stocks
- **Data Fields**: 200+ petroleum series (weekly/monthly)
- **Free Tier**: Unlimited with free key from eia.gov
- **Integration**: Already in hub_catalog.json — just needs API key configured
- **Improvement**: Upstream supply intelligence; refinery utilization predicts bitumen availability

## 3.2 Currency Exchange Rates

### API 4: ExchangeRate-API
- **Purpose**: USD/INR real-time + historical (backup to Frankfurter)
- **Data Fields**: base, rates{}, time_last_update
- **Free Tier**: 1,500 requests/month
- **Integration**: `GET https://v6.exchangerate-api.com/v6/YOUR_KEY/latest/USD`
- **Improvement**: More frequent updates than ECB-backed Frankfurter (which updates once/day)

### API 5: RBI DBIE (Database on Indian Economy)
- **Purpose**: Official RBI reference rate for USD/INR
- **Data Fields**: date, reference_rate
- **Free Tier**: Unlimited (public data portal)
- **Integration**: `GET https://api.rbi.org.in/` or scrape from dbie.rbi.org.in
- **Improvement**: **Official RBI rate** — legally defensible for customs calculations

## 3.3 Weather & Logistics

### API 6: Open-Meteo (Enhanced Usage)
- **Purpose**: 7-day forecast + hourly precipitation (already integrated but underused)
- **Data Fields**: temperature, precipitation_probability, rain_sum, wind_speed
- **Free Tier**: Unlimited, no key needed
- **Integration**: Already in hub_catalog — extend to forecast mode: `&forecast_days=7`
- **Improvement**: **Monsoon prediction accuracy** — 7-day precipitation forecast enables "road condition" scoring

### API 7: OpenWeather — One Call API 3.0
- **Purpose**: Severe weather alerts, UV index, air quality (road visibility)
- **Data Fields**: alerts[], minutely[], hourly[], daily[]
- **Free Tier**: 1,000 calls/day (free key from openweathermap.org)
- **Integration**: Already in hub_catalog — just needs API key
- **Improvement**: Severe weather alerts trigger logistics disruption warnings

## 3.4 Infrastructure & Government Data

### API 8: data.gov.in (NHAI Highway Construction)
- **Purpose**: Highway KM constructed, road spending, NHAI awards
- **Data Fields**: state, highway_km, spending_cr, year
- **Free Tier**: Unlimited (free key from data.gov.in)
- **Integration**: Already in hub_catalog — just needs API key configured
- **Improvement**: **Demand correlation** — highway construction directly drives bitumen demand

### API 9: GeM Portal (Government e-Marketplace)
- **Purpose**: Government bitumen tenders, purchase orders
- **Data Fields**: tender_id, item_description, quantity, location, deadline
- **Free Tier**: Public data (scraping allowed for public tenders)
- **Integration**: Scrape `https://gem.gov.in/` bitumen category
- **Improvement**: **Live tender intelligence** — real-time demand signals from government procurement

### API 10: Sagarmala / Indian Ports Association
- **Purpose**: Port vessel schedules, berth occupancy, cargo volumes
- **Data Fields**: port, vessel_name, ETA, cargo_type, berth_status
- **Free Tier**: Public data from portals
- **Integration**: Scrape from indianports.gov.in or sagarmala.gov.in
- **Improvement**: **Real vessel tracking** — replaces hardcoded mock shipment data

## 3.5 Economic Indicators

### API 11: World Bank API (Enhanced)
- **Purpose**: India GDP growth, CPI inflation, construction sector output, FDI inflows
- **Data Fields**: indicator, country, date, value
- **Free Tier**: Unlimited, no key needed (already integrated)
- **Integration**: Extend current World Bank connector to fetch: NY.GDP.MKTP.KD.ZG, FP.CPI.TOTL.ZG, NV.IND.TOTL.ZS
- **Improvement**: **Economic context** for demand forecasting; construction sector GDP as demand proxy

### API 12: Trading Economics API (Indicators)
- **Purpose**: India PMI, industrial production, construction output
- **Data Fields**: country, indicator, latest_value, previous, forecast
- **Free Tier**: Limited (100 calls/month free, or scrape public pages)
- **Integration**: `GET https://api.tradingeconomics.com/country/india/indicator/pmi`
- **Improvement**: **PMI is leading indicator** — rises 2-3 months before demand increases

### API 13: OPEC Monthly Oil Market Report
- **Purpose**: OPEC production decisions, demand forecasts, supply outlook
- **Data Fields**: production_mbpd, demand_forecast, spare_capacity
- **Free Tier**: Monthly PDF (can scrape key tables)
- **Integration**: Parse OPEC MOMR PDF monthly from opec.org
- **Improvement**: **OPEC decisions directly impact crude prices** → bitumen cost

## 3.6 Shipping & Freight

### API 14: Freightos Baltic Index (FBX)
- **Purpose**: Container and bulk freight rates (Middle East → India route)
- **Data Fields**: route, rate_usd, date, change_pct
- **Free Tier**: Public index data (scrape from fbx.freightos.com)
- **Integration**: Scrape FBX route data for Persian Gulf → India West Coast
- **Improvement**: **Real freight rates** instead of hardcoded $35/MT

### API 15: MarineTraffic AIS (Free Tier)
- **Purpose**: Real vessel positions, ETA, route tracking
- **Data Fields**: vessel_name, MMSI, lat, lng, speed, destination, ETA
- **Free Tier**: 100 vessel positions/day
- **Integration**: `GET https://services.marinetraffic.com/api/exportvessel/v:5/YOUR_KEY`
- **Improvement**: **Replace mock shipment data** with real vessel AIS tracking

---

# STEP 4 — RECOMMENDED FREE AI MODELS

## 4.1 Price Forecasting

### Model 1: Prophet (Facebook/Meta)
- **Framework**: Python (fbprophet / prophet)
- **Purpose**: Time-series forecasting for bitumen price revisions
- **How It Works**: Additive model with trend + seasonality + holidays + regressors (crude, FX)
- **Accuracy Benefit**: 80-85% accuracy with proper training data (vs 72% current heuristic)
- **Integration**:
```python
from prophet import Prophet
model = Prophet(yearly_seasonality=True, weekly_seasonality=False)
model.add_regressor('brent_price')
model.add_regressor('usd_inr')
model.fit(historical_prices_df)  # Need 2+ years of IOCL revision data
forecast = model.predict(future_df)
```
- **Data Needed**: 3+ years of IOCL VG30 revision prices (1st & 16th of each month)

### Model 2: NeuralProphet
- **Framework**: Python (neuralprophet, PyTorch backend)
- **Purpose**: Neural network enhanced Prophet — better for non-linear crude-bitumen relationships
- **Accuracy Benefit**: 85-88% with lagged regressors (crude price lags bitumen by 15-30 days)
- **Key Feature**: Auto-regression (AR) + lagged regressor support — captures the delay between crude price changes and bitumen revision

### Model 3: XGBoost / LightGBM
- **Framework**: Python (xgboost / lightgbm)
- **Purpose**: Gradient boosting for price direction prediction (UP/DOWN/FLAT)
- **Features Used**: Crude price (lagged 7/14/30d), FX rate, season index, OPEC decision flag, monsoon flag
- **Accuracy Benefit**: 82-87% direction accuracy; fast training (seconds)
- **Best For**: Binary "BUY NOW vs WAIT" decisions

## 4.2 Demand Forecasting

### Model 4: ARIMA/SARIMAX
- **Framework**: Python (statsmodels)
- **Purpose**: Seasonal demand forecasting with exogenous variables
- **Features**: Monthly bitumen consumption + highway KM + budget allocation + monsoon dummy
- **Accuracy Benefit**: Captures seasonal patterns + trends automatically (vs hardcoded monthly %)
- **Integration**:
```python
from statsmodels.tsa.statespace.sarimax import SARIMAX
model = SARIMAX(demand_series, order=(1,1,1), seasonal_order=(1,1,1,12),
                exog=highway_km_series)
results = model.fit()
forecast = results.forecast(steps=6, exog=future_highway_km)
```

## 4.3 News & Sentiment Analysis

### Model 5: FinBERT (Hugging Face)
- **Framework**: Python (transformers, PyTorch)
- **Purpose**: Financial news sentiment scoring for oil/bitumen headlines
- **How It Works**: Pre-trained BERT fine-tuned on financial text → outputs positive/negative/neutral with confidence
- **Accuracy Benefit**: 87% accuracy on financial sentiment (vs keyword-matching in current system)
- **Integration**:
```python
from transformers import pipeline
classifier = pipeline("sentiment-analysis", model="ProsusAI/finbert")
result = classifier("OPEC cuts production by 1M barrels, oil prices surge")
# → {'label': 'positive', 'score': 0.92}  (positive for oil prices)
```
- **Use Case**: Score each news headline → aggregate into daily sentiment index → feed into price prediction

### Model 6: zero-shot-classification (Hugging Face)
- **Framework**: Python (transformers)
- **Purpose**: Classify news articles by impact category without training
- **Categories**: "crude oil supply", "bitumen demand", "infrastructure spending", "weather disruption", "geopolitics"
- **Integration**:
```python
from transformers import pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
result = classifier("NHAI awards 500km highway contract in Gujarat",
                    candidate_labels=["bitumen demand", "crude supply", "logistics"])
# → {'labels': ['bitumen demand'], 'scores': [0.89]}
```

## 4.4 Anomaly Detection

### Model 7: Isolation Forest
- **Framework**: Python (scikit-learn)
- **Purpose**: Detect anomalous price movements, data corruption, API errors
- **How It Works**: Builds random forests that isolate outliers faster than normal points
- **Use Cases**:
  - Price spike detection (Brent jumps >5% in 1 day)
  - Data corruption (negative prices, FX rate = 0)
  - API response anomalies (latency spikes, error bursts)
- **Integration**:
```python
from sklearn.ensemble import IsolationForest
model = IsolationForest(contamination=0.05)
model.fit(price_history[['price', 'change_pct', 'volume']])
anomalies = model.predict(new_data)  # -1 = anomaly
```

### Model 8: ADTK (Anomaly Detection Toolkit)
- **Framework**: Python (adtk)
- **Purpose**: Time-series specific anomaly detection
- **Detectors**: Level shift, spike, seasonal anomaly, persist change
- **Best For**: Detecting when bitumen price deviates from crude correlation (divergence alert)

## 4.5 Supply Chain Disruption

### Model 9: Random Forest Classifier
- **Framework**: Python (scikit-learn)
- **Purpose**: Predict supply chain disruption probability
- **Features**: Weather severity, port congestion, geopolitical risk score, freight rate change, vessel ETA deviation
- **Output**: Disruption probability 0-100% + risk category (LOW/MEDIUM/HIGH)

## 4.6 Recommendation Engine

### Model 10: Multi-Armed Bandit (Thompson Sampling)
- **Framework**: Python (custom implementation)
- **Purpose**: Learn optimal purchase timing from historical outcomes
- **How It Works**: Each "arm" = a decision (buy now / wait 3d / wait 7d / wait 14d); system learns which decisions lead to better prices over time
- **Accuracy Benefit**: Improves with each transaction; converges to optimal strategy within 50-100 decisions
- **Key Advantage**: No training data needed — learns online from real outcomes

---

# STEP 5 — IMPROVED DASHBOARD ANALYTICS

## 5.1 New Heatmaps

### Heatmap 1: Regional Price Heatmap
- **What**: India map colored by landed cost per MT by destination city
- **How**: Use Plotly choropleth or folium with state-level pricing data
- **Decision Value**: Instantly identify cheapest delivery regions → focus sales there
- **Data**: calculation_engine output for all cities × all sources

### Heatmap 2: Demand Seasonality Calendar
- **What**: 12-month × 7-day heatmap showing demand intensity
- **Colors**: Red (high demand) → Yellow (moderate) → Blue (low/monsoon)
- **Decision Value**: Plan inventory procurement 2-4 weeks before demand peaks

### Heatmap 3: Supplier Performance Matrix
- **What**: Suppliers × metrics (price stability, delivery time, quality, payment terms)
- **Colors**: Green (best) → Red (worst) per metric
- **Decision Value**: Quick supplier comparison for procurement decisions

### Heatmap 4: Port Congestion Heatmap
- **What**: 8 ports × 12 months showing historical congestion/delays
- **Decision Value**: Route shipments to least congested ports

## 5.2 New Trend Graphs

### Graph 1: Crude-to-Bitumen Price Transmission
- **What**: Dual-axis chart — Brent crude (left) vs Bitumen VG30 (right) with lag overlay
- **Why**: Shows 15-30 day lag between crude movement and bitumen revision
- **Decision Value**: "Crude dropped 5% last week → bitumen revision will drop in ~15 days → wait to buy"

### Graph 2: Margin Waterfall Over Time
- **What**: Monthly waterfall showing margin composition: base price, crude impact, FX impact, freight, GST
- **Decision Value**: Identifies which cost component is squeezing margins most

### Graph 3: Volatility Bands Chart
- **What**: Price chart with Bollinger Bands (20-day MA ± 2σ)
- **Decision Value**: When price touches upper band → overbought → wait; lower band → buy signal

### Graph 4: Supply-Demand Balance Indicator
- **What**: Stacked area chart — domestic production + imports vs estimated consumption
- **Decision Value**: Supply surplus → prices fall; supply deficit → prices rise

## 5.3 New Index Indicators

### Index 1: Procurement Urgency Index (0-100)
```
= 0.25 × (price_trend_score)     # rising = urgent
+ 0.20 × (demand_season_score)    # peak season = urgent
+ 0.20 × (inventory_days_score)   # low stock = urgent
+ 0.15 × (crude_momentum_score)   # crude rising = urgent
+ 0.10 × (fx_pressure_score)      # INR weakening = urgent
+ 0.10 × (supply_risk_score)      # disruption = urgent
```
- **Display**: Large gauge on home page with recommendation text
- **Thresholds**: >70 = "BUY NOW" (red), 40-70 = "MONITOR" (yellow), <40 = "WAIT" (green)

### Index 2: Market Volatility Index (Custom VIX for Bitumen)
```
= 0.35 × crude_30d_volatility
+ 0.25 × fx_30d_volatility
+ 0.20 × freight_30d_volatility
+ 0.20 × demand_uncertainty
```
- **Display**: Thermometer gauge with LOW/MEDIUM/HIGH/EXTREME zones

### Index 3: Supply Chain Risk Score
```
= 0.30 × weather_disruption_probability
+ 0.25 × port_congestion_level
+ 0.20 × freight_rate_trend
+ 0.15 × geopolitical_risk
+ 0.10 × vessel_delay_probability
```

## 5.4 Correlation Analysis Additions

### Correlation 1: Crude Price → Bitumen Revision Lag Analysis
- Cross-correlation at lags 0-30 days to find optimal prediction window
- Plotly heatmap showing correlation strength by lag

### Correlation 2: Monsoon Intensity → Demand Drop
- Rainfall mm vs monthly bitumen consumption by region
- Helps predict exact demand recovery timing post-monsoon

### Correlation 3: Highway Awards → Future Demand
- NHAI new highway awards (KM) vs bitumen imports (MT) at 3-6 month lag
- Leading indicator for demand surge

---

# STEP 6 — IMPROVED PRICE PREDICTION

## 6.1 Current vs Proposed Model

| Aspect | Current (Heuristic) | Proposed (Ensemble ML) |
|--------|---------------------|----------------------|
| **Method** | Base drift + seasonality + random walk | Prophet + XGBoost + ARIMA ensemble |
| **Training Data** | None (mock with seed 42) | 3+ years IOCL revisions + crude + FX |
| **Features** | Crude price, FX rate, month | 15+ features (see below) |
| **Accuracy** | ~72% (claimed, unvalidated) | Target: 85%+ (validated monthly) |
| **Confidence** | Linear decay formula | Bayesian confidence intervals |
| **Horizon** | 24 months | 6 months (accurate), 12 months (directional) |

## 6.2 Feature Engineering (15 Predictive Features)

| # | Feature | Source | Lag | Weight |
|---|---------|--------|-----|--------|
| 1 | Brent crude price | yfinance/EIA | 0, 7, 14, 30d | 0.25 |
| 2 | Brent 30-day momentum | calculated | 0 | 0.10 |
| 3 | USD/INR exchange rate | Frankfurter | 0, 7d | 0.15 |
| 4 | FX 30-day volatility | calculated | 0 | 0.05 |
| 5 | Seasonal demand index | demand model | 0 | 0.10 |
| 6 | Monsoon indicator (0/1) | calendar + weather | 0 | 0.05 |
| 7 | Highway KM awarded (lagged) | data.gov.in | 90d | 0.05 |
| 8 | India PMI (manufacturing) | Trading Economics | 30d | 0.05 |
| 9 | Freight rate (ME→India) | FBX/manual | 0 | 0.05 |
| 10 | OPEC decision flag | news/manual | 0 | 0.03 |
| 11 | India VIX | yfinance | 0 | 0.03 |
| 12 | Previous revision change | historical | 0 | 0.04 |
| 13 | Election year flag | calendar | 0 | 0.02 |
| 14 | News sentiment score | FinBERT | 7d avg | 0.02 |
| 15 | Inventory level estimate | manual/model | 0 | 0.01 |

## 6.3 Ensemble Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    ENSEMBLE PREDICTOR                      │
│                                                           │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ Prophet  │  │ XGBoost  │  │ SARIMAX  │  │ Heuristic │ │
│  │ (trend + │  │ (non-    │  │ (ARIMA + │  │ (current  │ │
│  │ seasonal)│  │ linear)  │  │ external)│  │ fallback) │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬─────┘ │
│       │              │              │               │       │
│       ▼              ▼              ▼               ▼       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            WEIGHTED AVERAGE (dynamic weights)        │   │
│  │  Prophet: 0.35  XGBoost: 0.30  SARIMAX: 0.25       │   │
│  │  Heuristic: 0.10                                     │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  OUTPUT:                                             │   │
│  │  • Predicted price: ₹42,500/MT                       │   │
│  │  • Direction: UP (+₹800)                             │   │
│  │  • Probability: 78%                                  │   │
│  │  • Confidence interval: ₹41,200 - ₹43,800           │   │
│  │  • Risk score: MEDIUM (crude volatile)               │   │
│  │  • Key drivers: Crude +3%, FX stable, Peak season    │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

## 6.4 Monthly Accuracy Validation

```python
# Auto-runs on 2nd and 17th of each month (after revision published)
def validate_prediction(revision_date, actual_price):
    predicted = get_prediction_for_date(revision_date)
    error = abs(actual_price - predicted.price)
    error_pct = error / actual_price * 100

    # PASS/FAIL criteria
    passed = error <= 800 or error_pct <= 2.0

    # Update model weights based on which sub-model was most accurate
    update_ensemble_weights(revision_date, actual_price)

    # Store for accuracy tracking
    store_accuracy_record(revision_date, predicted, actual_price, passed)
```

---

# STEP 7 — PURCHASE RECOMMENDATION ENGINE

## 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              INTELLIGENT PURCHASE ADVISOR                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  INPUTS:                                                     │
│  ├── Price prediction (next 30 days)                         │
│  ├── Current inventory level                                 │
│  ├── Demand forecast (next 30 days)                          │
│  ├── Procurement urgency index                               │
│  ├── Market volatility index                                 │
│  ├── Crude oil momentum (7d, 14d, 30d)                       │
│  ├── FX trend (USD/INR 7d direction)                         │
│  ├── Weather forecast (7-day road conditions)                │
│  ├── Active tenders / government procurement                 │
│  └── Competitor pricing intelligence                         │
│                                                              │
│  DECISION ENGINE:                                            │
│  ├── Rule 1: IF price_prediction = DOWN AND urgency < 40    │
│  │           → "WAIT — price correction expected in X days"  │
│  ├── Rule 2: IF price_prediction = UP AND inventory < 15d   │
│  │           → "BUY NOW — price rising, stock running low"   │
│  ├── Rule 3: IF monsoon_ending AND demand_spike_expected     │
│  │           → "PRE-BUY — demand surge in 2-3 weeks"         │
│  ├── Rule 4: IF volatility = HIGH AND no urgent need         │
│  │           → "HOLD — market unstable, wait for clarity"    │
│  └── Rule 5: IF tender_awarded AND nearby_project            │
│              → "STOCKPILE — large project demand incoming"   │
│                                                              │
│  OUTPUTS:                                                    │
│  ├── Action: "BUY NOW" / "WAIT X DAYS" / "PRE-BUY" / "HOLD"│
│  ├── Confidence: 45-95%                                      │
│  ├── Reasoning: 3-5 bullet points                            │
│  ├── Risk: What could go wrong                               │
│  ├── Optimal quantity: X MT (based on demand forecast)       │
│  ├── Optimal source: Best supplier for current conditions    │
│  └── Price target: Expected price at recommended time        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 7.2 Example Outputs

```
╔══════════════════════════════════════════════════════════════╗
║  🟢 RECOMMENDATION: BUY WITHIN NEXT 3 DAYS                  ║
║  Confidence: 82%                                             ║
║                                                              ║
║  Reasoning:                                                  ║
║  • Crude oil dropped 4.2% this week — bitumen revision       ║
║    expected to drop ₹400-600/MT on March 16th                ║
║  • USD/INR stable at 92.15 (no FX pressure)                  ║
║  • Peak construction season starting — demand rising         ║
║  • Current stock: 12 days supply (below 15-day threshold)    ║
║  • Freight rates stable at $34/MT                            ║
║                                                              ║
║  Suggested Purchase:                                         ║
║  • Quantity: 3,000 MT (30 days coverage)                     ║
║  • Best Source: Kandla Port Import (₹38,200/MT landed)       ║
║  • Expected Price after 16th revision: ₹37,600-38,000/MT    ║
║  • Savings if buy post-revision: ₹200-600/MT                ║
║                                                              ║
║  ⚠️ Risk: OPEC meeting on March 12 could reverse crude drop  ║
╚══════════════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════════════╗
║  🟡 RECOMMENDATION: WAIT FOR PRICE CORRECTION                ║
║  Confidence: 71%                                             ║
║                                                              ║
║  Reasoning:                                                  ║
║  • Brent crude trending down (-2.1% weekly momentum)         ║
║  • Next revision (April 1) likely to drop ₹300-500/MT       ║
║  • Current stock: 22 days supply (sufficient)                ║
║  • Monsoon approaching — demand will soften in 6 weeks       ║
║                                                              ║
║  Wait Until: April 2nd (post-revision)                       ║
║  Expected Saving: ₹300-500/MT × estimated demand             ║
║                                                              ║
║  ⚠️ Risk: Supply disruption at Kandla port could spike prices ║
╚══════════════════════════════════════════════════════════════╝
```

## 7.3 Stock Level Recommendation

```python
def recommend_stock_level(demand_forecast_30d, supply_risk, season):
    base_days = 15  # default safety stock

    # Adjust for season
    if season == 'peak':      base_days = 20
    elif season == 'monsoon': base_days = 10  # lower demand

    # Adjust for supply risk
    if supply_risk == 'HIGH':     base_days += 10
    elif supply_risk == 'MEDIUM': base_days += 5

    # Adjust for price trend
    if price_trending_up:         base_days += 5  # stock up before price rises
    elif price_trending_down:     base_days -= 3  # buy less, wait for cheaper

    recommended_mt = (demand_forecast_30d / 30) * base_days
    return {
        'days_cover': base_days,
        'recommended_mt': recommended_mt,
        'current_stock_mt': get_current_inventory(),
        'shortfall_mt': max(0, recommended_mt - get_current_inventory())
    }
```

---

# STEP 8 — AUTO-HEALING SYSTEM DESIGN

## 8.1 Current vs Proposed

| Capability | Current (sre_engine.py) | Proposed Enhancement |
|-----------|------------------------|---------------------|
| API failure detection | ✅ Checks health every 30 min | Add circuit breaker pattern |
| Auto-retry | ✅ 3x with exponential backoff | Add jitter + fallback chain |
| Data corruption | ❌ Not detected | Add Isolation Forest anomaly detection |
| Worker crash detection | ⚠️ JSON timestamp checking | Add heartbeat monitoring |
| Performance monitoring | ⚠️ Basic latency tracking | Add percentile tracking (p50/p95/p99) |
| Alert escalation | ⚠️ P0/P1/P2 classification | Add auto-escalation rules + SLA |
| Self-repair | ✅ Basic restart | Add data backfill + cache warmup |
| Root cause analysis | ❌ Not available | Add error correlation + pattern matching |

## 8.2 Enhanced Auto-Healing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  ENHANCED SRE AUTO-HEALER                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LAYER 1: DETECTION (every 5 minutes)                        │
│  ├── API Health Checker                                      │
│  │   ├── HTTP status code monitoring (200/4xx/5xx)           │
│  │   ├── Response time percentiles (p50 < 500ms, p99 < 3s)  │
│  │   ├── Data freshness check (< configured TTL)             │
│  │   └── Response schema validation (fields exist, types OK) │
│  ├── Data Integrity Scanner                                  │
│  │   ├── Price range validation (Brent: $40-150)             │
│  │   ├── FX rate sanity check (USD/INR: 60-120)              │
│  │   ├── Duplicate detection (same timestamp + value)        │
│  │   ├── Null/NaN detection in critical fields               │
│  │   └── Isolation Forest anomaly scoring                    │
│  ├── Worker Heartbeat Monitor                                │
│  │   ├── Last heartbeat timestamp per worker                 │
│  │   ├── Expected interval vs actual                         │
│  │   └── Memory/CPU usage per worker (psutil)                │
│  └── Performance Monitor                                     │
│      ├── Page load time tracking                             │
│      ├── Database query duration                             │
│      └── Memory usage trending                               │
│                                                              │
│  LAYER 2: DIAGNOSIS (on failure detected)                    │
│  ├── Error pattern matching (known error → known fix)        │
│  ├── Dependency graph analysis (which downstream affected?)  │
│  ├── Root cause classification:                              │
│  │   ├── NETWORK — API unreachable, DNS failure              │
│  │   ├── AUTH — API key expired, rate limited                │
│  │   ├── DATA — Corrupted response, schema change            │
│  │   ├── WORKER — Process crashed, memory leak               │
│  │   └── INFRA — Disk full, CPU overload                     │
│  └── Impact assessment (which pages/features affected?)      │
│                                                              │
│  LAYER 3: REPAIR (automatic)                                 │
│  ├── API Failures:                                           │
│  │   ├── Retry with exponential backoff + jitter             │
│  │   ├── Switch to fallback API (yfinance → EIA → cache)     │
│  │   ├── Circuit breaker: stop calling after 5 consecutive   │
│  │   │   failures (check again in 30 min)                    │
│  │   └── Serve cached data with "STALE" warning badge        │
│  ├── Data Corruption:                                        │
│  │   ├── Revert to last known good snapshot                  │
│  │   ├── Backfill from secondary source                      │
│  │   └── Mark as "UNVERIFIED" in confidence engine           │
│  ├── Worker Crashes:                                         │
│  │   ├── Auto-restart with fresh state                       │
│  │   ├── If crash loops (>3x in 15min) → disable + alert     │
│  │   └── Log crash dump for debugging                        │
│  └── Performance Issues:                                     │
│      ├── Clear stale cache entries                           │
│      ├── Compact JSON files (remove old records)             │
│      └── Restart Streamlit server (last resort)              │
│                                                              │
│  LAYER 4: NOTIFICATION                                       │
│  ├── In-dashboard alert banner (real-time)                   │
│  ├── Log to sre_alerts.json (persistent)                     │
│  ├── Email to admin (P0 only)                                │
│  └── WhatsApp alert (P0 only, if configured)                 │
│                                                              │
│  LAYER 5: LEARNING                                           │
│  ├── Track MTTR (mean time to repair) per error type         │
│  ├── Track recurrence frequency                              │
│  ├── Auto-update circuit breaker thresholds                  │
│  └── Weekly health report generation                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 8.3 Circuit Breaker Implementation

```python
class CircuitBreaker:
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, skip calls
    HALF_OPEN = "half_open"  # Testing recovery

    def __init__(self, failure_threshold=5, recovery_timeout=1800):
        self.state = self.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # 30 min
        self.last_failure_time = None

    def call(self, api_function, *args, **kwargs):
        if self.state == self.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = self.HALF_OPEN  # Try one request
            else:
                raise CircuitOpenException("API circuit breaker OPEN")

        try:
            result = api_function(*args, **kwargs)
            if self.state == self.HALF_OPEN:
                self.state = self.CLOSED  # Recovery confirmed
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
            raise
```

---

# STEP 9 — BUG DETECTION

## 9.1 Logic Errors Found

| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | **price_prediction.py** | Mock data uses `seed(42)` — all "historical accuracy" is fabricated | Replace with real IOCL revision tracking; store actual predictions and compare monthly |
| 2 | **risk_scoring.py** | All 6 risk scores use `np.random.normal()` seeded by date — completely fake | Connect to real data sources: Brent volatility for market risk, actual receivables for financial risk |
| 3 | **strategy_panel.py** | Confidence % is `np.random.normal(mean, std)` — randomized between page loads | Make deterministic based on actual data quality + model confidence |
| 4 | **demand_analytics.py** | Election year hardcoded as `2024, 2029` — misses state elections | Use dynamic election calendar API or manual config in settings.json |
| 5 | **financial_intel.py** | Margin sensitivity coefficients (-0.4, -0.15, -0.3) not validated | Derive from historical regression of actual margin vs crude/freight/FX |
| 6 | **supply_chain.py** | Vessel dates use `timedelta` from today — resets every page load | Store vessel data in database with fixed dates; update on sync |
| 7 | **import_cost_model.py** | Port charges fixed at ₹10,000 regardless of port | Use port-specific charges from settings.json (Kandla ≠ Mangalore ≠ JNPT) |
| 8 | **calculation_engine.py** | Decanter conversion cost hardcoded at ₹500 | Move to settings.json; varies by decanter location |
| 9 | **alert_system.py** | ALT-005 payment overdue hardcoded ("Ashoka Buildcon 1.5 Cr, 12d late") | Query from deals table: `WHERE payment_date IS NULL AND delivery_date < NOW() - 7d` |
| 10 | **correlation_dashboard.py** | Requires ≥24 months data but doesn't validate before running regression | Add `if len(data) < 24: st.warning("Insufficient data")` check |

## 9.2 Data Integrity Issues

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 1 | No input validation on manual price entry | Data Manager | Add range checks: VG30 ₹30,000-60,000/MT |
| 2 | Duplicate supplier detection missing | database.py insert_supplier | Add UNIQUE constraint on (name, city, gstin) |
| 3 | Brent price anomaly in sre_alerts: "24389.30 USD/bbl" | api_hub_engine | This is INR conversion leaking into USD field — add unit check |
| 4 | FX rate 92.15 for USD/INR but calculation_engine uses 83.25 default | import_cost_model defaults | Fetch live rate instead of hardcoded default |
| 5 | `tbl_ports_volume.json` confidence only 65% — BDI-adjusted estimates | api_hub_engine | Integrate real port data from Indian Ports Association |

## 9.3 Performance Issues

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 1 | Home page loads ALL data sources on every render | 3-5 second load time | Lazy-load sections; cache results for 5 min |
| 2 | JSON files grow unbounded (500-1000 records) | Disk + parse time | Implement retention policy: keep last 500 records, archive older |
| 3 | CSS injected on every page load (800+ lines) | DOM bloat | Move to static CSS file served via Streamlit static_folder |
| 4 | No pagination on Opportunities/History tabs | DOM rendering slow with 50+ items | Add pagination: 20 items per page |
| 5 | `api_error_log.json` has 768 entries parsed on every Developer Ops load | Slow page render | Index by date; only load last 24h by default |

## 9.4 UI Bugs

| # | Issue | Page | Fix |
|---|-------|------|-----|
| 1 | Calendar grid unreadable on mobile (7 columns too narrow) | Sales Calendar | Use responsive grid: 7-col on desktop, 1-col list on mobile |
| 2 | Pricing Calculator 3-column layout breaks under 1024px | Pricing Calculator | Switch to stacked layout on tablet/mobile |
| 3 | Color-only status indicators (no labels for colorblind users) | Risk Scoring | Add text labels: "LOW RISK", "HIGH RISK" alongside colors |
| 4 | Font size 0.58rem on sidebar footer — too small to read | Brand header | Minimum 0.68rem for body text |

---

# STEP 10 — PERFORMANCE OPTIMIZATION

## 10.1 Database Optimization

| # | Optimization | Impact |
|---|-------------|--------|
| 1 | **Add compound indexes**: `(customer_id, stage)` on deals, `(date_time, benchmark)` on price_history | 2-5x faster queries on filtered views |
| 2 | **Enable WAL mode** (already done ✅) | Concurrent reads during writes |
| 3 | **Add materialized views** for dashboard KPIs (supplier count, deal stats) | Eliminate repeated full-table scans on home page |
| 4 | **Partition price_history by year** | Faster queries when only recent data needed |
| 5 | **Add VACUUM schedule** (weekly) | Reclaim deleted space, defragment |

## 10.2 API Call Optimization

| # | Optimization | Impact |
|---|-------------|--------|
| 1 | **Batch API calls** — fetch all FX pairs in one request (Frankfurter supports multiple bases) | 3 calls → 1 call |
| 2 | **Cache with TTL** — crude prices (5 min), FX (30 min), weather (60 min), news (120 min) | 80% fewer API calls |
| 3 | **Parallel fetching** — use `concurrent.futures.ThreadPoolExecutor` for independent APIs | 14 serial → 14 parallel = 3-5x faster sync |
| 4 | **Circuit breaker** — stop calling failing APIs (UN Comtrade) after 5 failures | Eliminate wasted timeout waits |
| 5 | **ETag / If-Modified-Since headers** — skip download if data unchanged | 30-50% bandwidth savings |

## 10.3 Caching Strategy

```
┌─────────────────────────────────────────────────────────┐
│                   3-TIER CACHE                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  TIER 1: Session State (Streamlit)                      │
│  ├── TTL: Per session (user's browser tab)              │
│  ├── Use for: User selections, UI state, page data      │
│  └── Already in place ✅                                │
│                                                         │
│  TIER 2: @st.cache_data (Streamlit built-in)            │
│  ├── TTL: Configurable per function                     │
│  ├── Use for: API responses, computed tables            │
│  ├── Example:                                           │
│  │   @st.cache_data(ttl=300)  # 5 min for prices       │
│  │   def get_crude_prices(): ...                        │
│  │   @st.cache_data(ttl=3600)  # 1 hr for weather      │
│  │   def get_weather_data(): ...                        │
│  └── Missing — needs implementation ⚠️                  │
│                                                         │
│  TIER 3: File Cache (JSON files)                        │
│  ├── TTL: Until next sync cycle (60 min default)        │
│  ├── Use for: Persistent data between server restarts   │
│  └── Already in place ✅ (tbl_*.json files)             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 10.4 Background Worker Optimization

| # | Worker | Current | Proposed |
|---|--------|---------|----------|
| 1 | API Hub Scheduler | 60 min (all APIs) | Tiered: prices 5min, FX 30min, weather 60min, news 120min |
| 2 | SRE Self-Healing | 15 min | Keep 15 min, add circuit breaker to skip known-down APIs |
| 3 | Sync Engine | 60 min (full sync) | Incremental sync: only changed data; full sync daily at 2AM |
| 4 | Email Queue | 5 min polling | Event-driven: trigger on new email queued (use threading.Event) |
| 5 | News Fetcher | 10 min | 30 min (news doesn't change that fast); batch RSS feeds |

## 10.5 Dashboard Loading Speed

| # | Optimization | Expected Improvement |
|---|-------------|---------------------|
| 1 | **Lazy-load tab content** — only render active tab, not all 65 pages | 10x faster initial load |
| 2 | **Compress CSS** — minify 800+ lines of injected CSS | 30% smaller HTML payload |
| 3 | **Use @st.cache_data** on all data-fetching functions | 80% fewer file reads |
| 4 | **Defer non-critical sections** — AI Command Centre, Missing Inputs on home | 2s faster home page |
| 5 | **Static assets** — move CSS to file, serve via static folder | Eliminates re-injection overhead |
| 6 | **Pagination** — limit tables to 20 rows with "Load More" | Faster DOM rendering |

---

# STEP 11 — FINAL STRUCTURED REPORT

## 11.1 Current System Architecture Score

| Dimension | Score | Grade |
|-----------|-------|-------|
| Database Design | 9/10 | A |
| API Infrastructure | 6/10 | C+ |
| UI/UX Design | 7/10 | B |
| Price Prediction Accuracy | 3/10 | D (mock data) |
| Risk Assessment | 2/10 | F (simulated) |
| Demand Forecasting | 3/10 | D (hardcoded) |
| Supply Chain Tracking | 2/10 | F (mock vessels) |
| Financial Intelligence | 3/10 | D (hardcoded) |
| Self-Healing/SRE | 7/10 | B |
| Data Quality | 5/10 | C |
| Performance | 5/10 | C |
| Test Coverage | 0/10 | F |
| **Overall** | **4.3/10** | **D+** |

## 11.2 Missing Features (Priority Ranked)

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | Real price prediction model (Prophet + XGBoost) | 2 weeks | Transforms prediction from fake to actionable |
| P0 | Real IOCL price tracking (actual revision data) | 1 week | Foundation for all prediction accuracy |
| P0 | Configure existing disabled API keys (EIA, FRED, data.gov.in) | 1 day | 5 new data sources for free |
| P1 | Purchase recommendation engine | 2 weeks | Core business value — when to buy |
| P1 | Real risk scoring (connected to actual data) | 1 week | Replace simulated scores with real assessments |
| P1 | Demand forecasting model (SARIMAX) | 1 week | Replace hardcoded seasonal patterns |
| P1 | News sentiment analysis (FinBERT) | 3 days | Add intelligence signal to predictions |
| P2 | Unit test suite (pytest) | 2 weeks | Prevent regressions, enable CI/CD |
| P2 | Real vessel tracking (MarineTraffic) | 1 week | Replace mock supply chain |
| P2 | Procurement urgency index gauge | 3 days | Visual BUY/WAIT indicator on home page |
| P2 | Regional price heatmap | 3 days | Instant visual pricing intelligence |
| P3 | Enhanced auto-healing (circuit breaker, anomaly detection) | 1 week | Better reliability |
| P3 | Performance optimization (@st.cache_data, lazy loading) | 3 days | 5-10x faster page loads |
| P3 | Mobile responsive layout | 1 week | Better mobile experience |

## 11.3 Recommended APIs (Summary)

| # | API | Cost | Key Data | Action |
|---|-----|------|----------|--------|
| 1 | EIA (eia.gov) | FREE | Crude, petroleum, refinery | Configure existing key |
| 2 | FRED (stlouisfed.org) | FREE | Brent, WTI, USD/INR | Configure existing key |
| 3 | data.gov.in | FREE | NHAI highway KM | Configure existing key |
| 4 | OpenWeather | FREE | Weather alerts | Configure existing key |
| 5 | NewsAPI | FREE | Global news | Configure existing key |
| 6 | Alpha Vantage | FREE | Commodity OHLCV | New integration |
| 7 | ExchangeRate-API | FREE | Real-time FX | New backup FX source |
| 8 | RBI DBIE | FREE | Official INR rates | New integration |
| 9 | Trading Economics | FREE (limited) | India PMI | New integration |
| 10 | MarineTraffic | FREE (100/day) | Vessel AIS tracking | New integration |
| 11 | Freightos FBX | FREE (public) | Freight rates | New integration |
| 12 | GeM Portal | FREE (public) | Government tenders | New scraper |
| 13 | OPEC MOMR | FREE (public) | Production decisions | New parser |

## 11.4 Recommended AI Models (Summary)

| # | Model | Framework | Purpose | Accuracy Target |
|---|-------|-----------|---------|----------------|
| 1 | Prophet | fbprophet | Price trend + seasonality | 80-85% |
| 2 | XGBoost | xgboost | Price direction (UP/DOWN) | 82-87% |
| 3 | SARIMAX | statsmodels | Demand forecasting | 75-80% |
| 4 | FinBERT | transformers | News sentiment | 87% |
| 5 | Isolation Forest | scikit-learn | Anomaly detection | 90%+ |
| 6 | NeuralProphet | neuralprophet | Enhanced price forecast | 85-88% |
| 7 | Random Forest | scikit-learn | Disruption prediction | 80% |
| 8 | BART zero-shot | transformers | News classification | 85% |
| 9 | Thompson Sampling | custom | Purchase timing | Improves over time |
| 10 | ADTK | adtk | Time-series anomalies | 92% |

## 11.5 New Dashboard Features (Summary)

| # | Feature | Type | Page |
|---|---------|------|------|
| 1 | Procurement Urgency Gauge (0-100) | Index | Home |
| 2 | Regional Price Heatmap (India map) | Heatmap | Home / Intelligence |
| 3 | Crude-to-Bitumen Lag Chart | Trend Graph | Price Prediction |
| 4 | Margin Waterfall Over Time | Waterfall | Financial Intel |
| 5 | Volatility Bands (Bollinger) | Chart | Price Prediction |
| 6 | Supply-Demand Balance Area | Area Chart | Demand Analytics |
| 7 | Supplier Performance Matrix | Heatmap | Source Directory |
| 8 | Port Congestion Calendar | Heatmap | Port Ops |
| 9 | Market Volatility Thermometer | Gauge | Home |
| 10 | Purchase Recommendation Card | Decision Card | Home |

## 11.6 Auto-Healing System Design (Summary)

5 Layers:
1. **Detection** — 5-min health checks (API, data integrity, workers, performance)
2. **Diagnosis** — Pattern matching, dependency analysis, root cause classification
3. **Repair** — Retry, fallback, circuit breaker, cache serving, worker restart
4. **Notification** — In-dashboard, JSON logs, email/WhatsApp for P0
5. **Learning** — MTTR tracking, recurrence analysis, threshold auto-tuning

## 11.7 Performance Improvements (Summary)

| Area | Action | Impact |
|------|--------|--------|
| Database | Compound indexes + materialized views | 2-5x faster queries |
| APIs | Parallel fetching + tiered TTL caching | 3-5x faster sync |
| Caching | @st.cache_data on all data functions | 80% fewer file reads |
| Rendering | Lazy-load tabs + pagination | 10x faster initial load |
| CSS | Static file + minification | 30% smaller payload |
| Workers | Event-driven + incremental sync | 50% less CPU usage |

## 11.8 Future Expansion Suggestions

| Phase | Feature | Timeline |
|-------|---------|----------|
| **Phase 5** | Real ML prediction + configured APIs + purchase advisor | 4-6 weeks |
| **Phase 6** | pytest suite (80%+ coverage) + Docker deployment | 3-4 weeks |
| **Phase 7** | Mobile PWA + push notifications | 4-6 weeks |
| **Phase 8** | Multi-tenant (support multiple trading companies) | 6-8 weeks |
| **Phase 9** | Real-time collaboration (multiple users editing) | 4-6 weeks |
| **Phase 10** | External API (REST endpoints for accounting integration) | 3-4 weeks |

---

## CONCLUSION

The PPS Anantam dashboard is an **ambitious and architecturally sound** system with excellent database design, comprehensive page coverage (65 pages), and a solid self-healing infrastructure. However, the **intelligence layer is critically undermined by mock/simulated data** in price prediction, risk scoring, demand analytics, and supply chain tracking.

### The Three Highest-Impact Actions:

1. **Configure the 5 disabled API keys** (EIA, FRED, data.gov.in, OpenWeather, NewsAPI) — **1 day effort, 5 new data sources free**
2. **Build real price prediction** with Prophet + XGBoost using actual IOCL revision history — **2 weeks effort, transforms the system from demo to production**
3. **Add Purchase Recommendation Engine** — **2 weeks effort, delivers the core business value: WHEN to buy**

These three actions alone would elevate the system score from **4.3/10 to ~7.5/10** and make it a genuinely actionable AI-powered decision system.

---
*Report generated: 04-Mar-2026 | Analyst: Senior AI System Architect*
*System: PPS Anantam v4.0.0 | 93+ files | 47,000+ LOC | 65 pages*
