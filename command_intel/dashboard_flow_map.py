"""
PPS Anantam — Dashboard Flow Map v1.0
======================================
Master System Blueprint: visual architecture of the entire dashboard.
9-layer flow diagram with color-coded blocks, live status lights,
clickable information panels, legend, health summary, and export.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

_BASE = Path(__file__).resolve().parent.parent

# ── Color scheme (user spec) ───────────────────────────────────────────────────
_CLR_API      = "#2563eb"   # Blue — API Data Sources
_CLR_AI       = "#7c3aed"   # Purple — AI Processing
_CLR_NEWS     = "#ea580c"   # Orange — News / Information Sources
_CLR_CRM      = "#16a34a"   # Green — CRM Data
_CLR_CALC     = "#ca8a04"   # Yellow — Auto Calculation Engine
_CLR_DB       = "#6b7280"   # Grey — Database
_CLR_OUTPUT   = "#166534"   # Dark Green — Output / Reports
_CLR_SYNC     = "#1e3a5f"   # Navy — Sync / Orchestration
_CLR_ALERT    = "#dc2626"   # Red — Alerts & Communication

# ── Status light colors ────────────────────────────────────────────────────────
_LIGHT_GREEN  = "#22c55e"   # Working
_LIGHT_YELLOW = "#eab308"   # Slow / Warning
_LIGHT_RED    = "#ef4444"   # Error
_LIGHT_BLUE   = "#3b82f6"   # Disabled


def _load_json(filename: str, default=None):
    try:
        fp = _BASE / filename
        if fp.exists():
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def _get_status_light(status: str) -> tuple[str, str]:
    """Return (color, label) for a status string."""
    s = str(status).upper()
    if s in ("OK", "LIVE", "SUCCESS", "RUNNING", "TRUE"):
        return _LIGHT_GREEN, "Working"
    elif s in ("WARN", "WARNING", "PARTIAL", "SLOW", "DEGRADED"):
        return _LIGHT_YELLOW, "Warning"
    elif s in ("FAIL", "ERROR", "FAILED", "CRASHED", "DOWN"):
        return _LIGHT_RED, "Error"
    elif s in ("DISABLED", "OFF", "FALSE", "IDLE"):
        return _LIGHT_BLUE, "Disabled"
    return _LIGHT_YELLOW, "Unknown"


def _file_freshness(path: Path) -> tuple[str, str]:
    """Return (status_light_color, age_label) based on file age."""
    try:
        delta = time.time() - path.stat().st_mtime
        if delta < 21600:      # < 6h
            return _LIGHT_GREEN, "Fresh"
        elif delta < 86400:    # < 24h
            return _LIGHT_YELLOW, "Aging"
        else:
            return _LIGHT_RED, "Stale"
    except Exception:
        return _LIGHT_RED, "Missing"


# ═════════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═════════════════════════════════════════════════════════════════════════════════

def render():
    """Render the Dashboard Flow Map — Master System Blueprint."""

    # ── S6: System Health Summary (top of page) ────────────────────────────
    _render_health_summary()

    # ── S1: System Flow Diagram + S2: Colors + S3: Status Lights ───────────
    _render_flow_diagram()

    # ── S5: Flow Legend ────────────────────────────────────────────────────
    _render_legend()

    # ── S4: Information Panels (clickable details) ─────────────────────────
    _render_info_panels()

    # ── S7: Export Option ──────────────────────────────────────────────────
    _render_export()


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SYSTEM HEALTH SUMMARY (TOP)
# ═════════════════════════════════════════════════════════════════════════════════

def _render_health_summary():
    """Top-of-page summary panel with key counts."""
    catalog = _load_json("hub_catalog.json", {})
    api_stats = _load_json("api_stats.json", {})
    sre_list = _load_json("sre_metrics.json", [])
    latest_sre = sre_list[-1] if sre_list else {}
    health_pct = latest_sre.get("health_pct", 0)

    total_apis = len(catalog)
    apis_ok = sum(1 for v in api_stats.values() if v.get("status") == "OK")

    # AI features count
    ai_count = 10  # known from FEATURE_MAP
    try:
        from ai_workers import get_feature_map
        fmap = get_feature_map()
        ai_count = len(fmap)
    except Exception:
        pass

    # Workers running
    workers_running = 0
    try:
        from ai_workers import get_worker_status
        ws = get_worker_status()
        workers_running = sum(1 for v in ws.values() if v.get("running"))
    except Exception:
        pass

    # Output files
    tbl_files = list(_BASE.glob("tbl_*.json"))
    output_count = len(tbl_files)

    # Data sources (unique categories)
    data_sources = len(set(m.get("category", "") for m in catalog.values()))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("APIs Connected", f"{apis_ok}/{total_apis}")
    c2.metric("AI Functions", ai_count)
    c3.metric("Data Sources", data_sources)
    c4.metric("Workers Running", workers_running)
    c5.metric("Output Tables", output_count)

    # Health bar
    if health_pct >= 90:
        bar_color = _LIGHT_GREEN
    elif health_pct >= 70:
        bar_color = _LIGHT_YELLOW
    else:
        bar_color = _LIGHT_RED

    st.markdown(f"""
<div style="background:#f8f9fa;border-radius:8px;padding:6px 16px;margin-bottom:14px;
            border-left:4px solid {bar_color};">
  <span style="font-size:0.78rem;color:#64748b;">System Health:</span>
  <span style="font-size:0.85rem;font-weight:700;color:{bar_color};"> {health_pct}%</span>
  <span style="font-size:0.72rem;color:#94a3b8;margin-left:12px;">
    Last updated: {latest_sre.get('timestamp_ist', '—')}
  </span>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — SYSTEM FLOW DIAGRAM (with S2 Colors + S3 Status Lights)
# ═════════════════════════════════════════════════════════════════════════════════

def _render_flow_diagram():
    """Full visual flow diagram: Sources → ... → Alerts."""

    # ── Compute live status for each layer ──────────────────────────────────
    api_stats = _load_json("api_stats.json", {})
    sync_logs = _load_json("sync_logs.json", [])
    sre_list = _load_json("sre_metrics.json", [])
    error_log = _load_json("api_error_log.json", [])

    # Layer statuses
    apis_ok = sum(1 for v in api_stats.values() if v.get("status") == "OK")
    apis_total = len(api_stats) if api_stats else 1
    api_light = _LIGHT_GREEN if apis_ok / apis_total > 0.8 else _LIGHT_YELLOW if apis_ok / apis_total > 0.5 else _LIGHT_RED

    last_sync = sync_logs[-1] if sync_logs else {}
    sync_light, _ = _get_status_light(last_sync.get("status", "UNKNOWN"))

    latest_sre = sre_list[-1] if sre_list else {}
    hp = latest_sre.get("health_pct", 0)
    sre_light = _LIGHT_GREEN if hp >= 90 else _LIGHT_YELLOW if hp >= 70 else _LIGHT_RED

    # Workers
    worker_light = _LIGHT_GREEN
    try:
        from ai_workers import get_worker_status
        ws = get_worker_status()
        running = sum(1 for v in ws.values() if v.get("running"))
        worker_light = _LIGHT_GREEN if running >= 5 else _LIGHT_YELLOW if running >= 2 else _LIGHT_RED
    except Exception:
        worker_light = _LIGHT_BLUE

    # DB
    db_path = _BASE / "bitumen_dashboard.db"
    db_light = _LIGHT_GREEN if db_path.exists() else _LIGHT_RED

    # Outputs
    tbl_files = list(_BASE.glob("tbl_*.json"))
    fresh = sum(1 for f in tbl_files if (time.time() - f.stat().st_mtime) < 21600)
    out_light = _LIGHT_GREEN if fresh > len(tbl_files) * 0.7 else _LIGHT_YELLOW if fresh > 0 else _LIGHT_RED

    # Errors
    open_errors = sum(1 for e in error_log if e.get("status") == "Open")
    err_light = _LIGHT_GREEN if open_errors == 0 else _LIGHT_YELLOW if open_errors < 5 else _LIGHT_RED

    # Communication
    comm_light = _LIGHT_GREEN  # baseline

    def _block(title, subtitle, color, light, items):
        items_html = "".join(f"<div style='font-size:0.6rem;color:rgba(255,255,255,0.85);'>{it}</div>" for it in items)
        return f"""
<div style="background:{color};color:white;border-radius:10px;padding:12px 14px;
            min-height:140px;position:relative;">
  <div style="position:absolute;top:8px;right:10px;width:10px;height:10px;
              border-radius:50%;background:{light};border:1px solid rgba(255,255,255,0.4);"></div>
  <div style="font-size:0.82rem;font-weight:700;">{title}</div>
  <div style="font-size:0.65rem;opacity:0.8;margin:3px 0 6px 0;">{subtitle}</div>
  {items_html}
</div>"""

    def _arrow():
        return f"""
<div style="display:flex;align-items:center;justify-content:center;padding:4px 0;">
  <div style="font-size:1.4rem;color:{_CLR_SYNC};font-weight:700;">▼</div>
</div>"""

    # ── Render flow ─────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="border:2px solid #e2e8f0;border-radius:14px;padding:18px;background:#fafbfc;">
  <div style="text-align:center;font-size:1rem;font-weight:700;color:{_CLR_SYNC};margin-bottom:14px;">
    📊 SYSTEM FLOW PIPELINE — End-to-End Architecture
  </div>
""", unsafe_allow_html=True)

    # Layer 1: Data Sources (3 columns)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_block("📡 API Data Sources", "External APIs", _CLR_API, api_light, [
            "• yfinance (Crude/FX)",
            "• Open-Meteo (Weather)",
            "• UN Comtrade (Trade)",
            "• World Bank (Macro)",
            "• Frankfurter (FX)",
        ]), unsafe_allow_html=True)
    with c2:
        st.markdown(_block("📰 News & Info Sources", "RSS + APIs", _CLR_NEWS, api_light, [
            "• Google News RSS",
            "• NewsAPI Headlines",
            "• Google Trends",
            "• GDELT Events",
            "• Govt Portals",
        ]), unsafe_allow_html=True)
    with c3:
        st.markdown(_block("👥 CRM & Manual Data", "Business Input", _CLR_CRM, _LIGHT_GREEN, [
            "• 63 Suppliers (SQLite)",
            "• 3 Customers (SQLite)",
            "• Contact Imports (Excel)",
            "• Daily Log Entries",
            "• Settings & Config",
        ]), unsafe_allow_html=True)

    st.markdown(_arrow(), unsafe_allow_html=True)

    # Layer 2: Collection
    st.markdown(_block("📥 DATA COLLECTION LAYER", "api_hub_engine.py — 14 connectors with retry, caching, fallback chains",
                        _CLR_API, api_light, [
        "• API Fetch + Retry (3 attempts, exponential backoff)",
        "• Web Scraping (RSS feeds, govt portals)",
        "• Fallback chains: EIA → yfinance, OpenWeather → Open-Meteo",
        "• Response caching (hub_cache.json) with TTL",
        "• Data validation (min/max range checks)",
    ]), unsafe_allow_html=True)

    st.markdown(_arrow(), unsafe_allow_html=True)

    # Layer 3: Sync & Processing (2 columns)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_block("🔄 SYNC & ORCHESTRATION", "sync_engine.py — 18 Steps, Daily 6 AM IST",
                            _CLR_SYNC, sync_light, [
            "• Step 1-3: Market, News, Trade data",
            "• Step 4: SRE data validation",
            "• Step 5-9: Calc, Opps, CRM, Alerts, Comms",
            "• Step 10-12: Briefing, AI Learning, Smart Alerts",
            "• Step 13-18: Infra, Health, Insights, RAG, ML, Signals",
        ]), unsafe_allow_html=True)
    with c2:
        st.markdown(_block("🧹 DATA PROCESSING", "Cleaning + Normalization",
                            _CLR_SYNC, sync_light, [
            "• Deduplication (crude prices, FX)",
            "• IST timestamp normalization",
            "• JSON → Normalized tbl_*.json tables",
            "• Missing data gap detection",
            "• Data confidence scoring",
        ]), unsafe_allow_html=True)

    st.markdown(_arrow(), unsafe_allow_html=True)

    # Layer 4: AI Analysis (2 columns)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_block("🤖 AI ANALYSIS LAYER", "7 Background Workers",
                            _CLR_AI, worker_light, [
            "• News Summarizer (1h interval)",
            "• Tender NER Extractor (1h)",
            "• Price Forecaster — ARIMA/Prophet (2h)",
            "• Opportunity Scorer — XGBoost (1h)",
            "• Anomaly Detector — IsolationForest (30m)",
            "• Report Writer — LLM Insights (24h)",
            "• Market Signals — 10-signal composite (2h)",
        ]), unsafe_allow_html=True)
    with c2:
        st.markdown(_block("🧠 AI MODELS", "10 Feature Modules",
                            _CLR_AI, worker_light, [
            "• ai_fallback_engine (multi-provider LLM)",
            "• finbert_engine (financial sentiment)",
            "• rag_engine (FAISS semantic search)",
            "• ml_boost_engine (XGBoost/LightGBM)",
            "• ml_forecast_engine (ARIMA/Prophet)",
            "• market_intelligence_engine (10 signals)",
            "• anomaly_engine (IsolationForest/Z-score)",
        ]), unsafe_allow_html=True)

    st.markdown(_arrow(), unsafe_allow_html=True)

    # Layer 5: Calculation Engine
    st.markdown(_block("🧮 AUTO CALCULATION ENGINE", "calculation_engine.py — Pricing & Margin Analysis",
                        _CLR_CALC, _LIGHT_GREEN, [
        "• International Landed Cost: FOB + Freight + Insurance + Port + CHA + Customs(2.5%) + GST(18%)",
        "• Domestic Landed Cost: Base Rate × 1.18 GST + Freight (Bulk Rs.5.5/km, Drum Rs.6/km)",
        "• Decanter Cost: Drum Cost + Transport + Rs.500 Conversion",
        "• 3-Tier Offers: Aggressive(+Rs.500), Balanced(+Rs.800), Premium(+Rs.1200)",
        "• Deal Profitability: Margin %, Total Value, Break-even Analysis",
    ]), unsafe_allow_html=True)

    st.markdown(_arrow(), unsafe_allow_html=True)

    # Layer 6: Database (2 columns)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_block("🗄️ DATABASE (SQLite)", "bitumen_dashboard.db — 21 Tables",
                            _CLR_DB, db_light, [
            "• suppliers (63), customers (3), deals",
            "• price_history, fx_history, inventory",
            "• email_queue, whatsapp_queue, sessions",
            "• opportunities, alerts, daily_logs",
            "• sync_logs, audit_log, users, briefings",
        ]), unsafe_allow_html=True)
    with c2:
        st.markdown(_block("📁 JSON CACHE FILES", f"{len(tbl_files)} tbl_*.json + System Logs",
                            _CLR_DB, out_light, [
            "• tbl_crude_prices, tbl_fx_rates, tbl_weather",
            "• tbl_news_feed, tbl_ports_volume, tbl_refinery",
            "• tbl_market_signals, tbl_world_bank",
            "• api_stats, api_health_log, api_error_log",
            "• sre_metrics, sre_alerts, sync_logs",
        ]), unsafe_allow_html=True)

    st.markdown(_arrow(), unsafe_allow_html=True)

    # Layer 7: Dashboard Visualization
    st.markdown(_block("📊 DASHBOARD VISUALIZATION", "Streamlit + Plotly — 61 Pages across 11 Modules",
                        _CLR_OUTPUT, sre_light, [
        "• Home, Director Briefing, Procurement, Sales, Logistics",
        "• Intelligence (Market Signals, News, Infra, Forecast)",
        "• Compliance (Govt Hub, GST, Risk), Reports (Financial, Strategy)",
        "• AI & Knowledge (Assistant, RAG, Learning)",
        "• System Control, Developer (Ops Map, Flow Map, Health)",
    ]), unsafe_allow_html=True)

    st.markdown(_arrow(), unsafe_allow_html=True)

    # Layer 8+9: Reports + Alerts (2 columns)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(_block("📄 REPORT GENERATION", "PDF + Director Briefing",
                            _CLR_OUTPUT, _LIGHT_GREEN, [
            "• Director Daily Briefing (7 sections)",
            "• PDF Export (ReportLab A4, INR format)",
            "• Quote PDFs (HSN 27132000)",
            "• Strategy Panels & Financial Reports",
            "• PDF Archive (pdf_exports/ folder)",
        ]), unsafe_allow_html=True)
    with c2:
        st.markdown(_block("🚨 ALERTS & COMMUNICATION", "Email + WhatsApp + In-App",
                            _CLR_ALERT, err_light, [
            "• Email: SMTP queue, auto-triggers, templates",
            "• WhatsApp: 360dialog API, HSM templates",
            "• P0/P1/P2 Smart Alerts (SRE engine)",
            "• Anomaly-based alerting (IsolationForest)",
            "• Director report daily 8:30 AM IST",
        ]), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — FLOW LEGEND
# ═════════════════════════════════════════════════════════════════════════════════

def _render_legend():
    """Color legend + status light legend."""
    st.markdown(f"""
<div style="display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 6px 0;">
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_API};display:inline-block;"></span> API Sources
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_AI};display:inline-block;"></span> AI Processing
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_NEWS};display:inline-block;"></span> News / Info
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_CRM};display:inline-block;"></span> CRM Data
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_CALC};display:inline-block;"></span> Calculations
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_DB};display:inline-block;"></span> Database
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_OUTPUT};display:inline-block;"></span> Outputs
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:12px;height:12px;border-radius:3px;background:{_CLR_ALERT};display:inline-block;"></span> Alerts
  </div>
</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:8px;height:8px;border-radius:50%;background:{_LIGHT_GREEN};display:inline-block;"></span> Working
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:8px;height:8px;border-radius:50%;background:{_LIGHT_YELLOW};display:inline-block;"></span> Warning
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:8px;height:8px;border-radius:50%;background:{_LIGHT_RED};display:inline-block;"></span> Error
  </div>
  <div style="display:flex;align-items:center;gap:4px;background:#f1f5f9;padding:4px 10px;border-radius:6px;font-size:0.68rem;">
    <span style="width:8px;height:8px;border-radius:50%;background:{_LIGHT_BLUE};display:inline-block;"></span> Disabled
  </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — INFORMATION PANELS (clickable details)
# ═════════════════════════════════════════════════════════════════════════════════

def _render_info_panels():
    """Expandable detail panels for each flow layer."""

    # ── Panel 1: Data Sources ───────────────────────────────────────────────
    with st.expander("📡 Data Sources — Full API Connector Details", expanded=False):
        catalog = _load_json("hub_catalog.json", {})
        api_stats = _load_json("api_stats.json", {})
        rows = []
        for cid, meta in sorted(catalog.items()):
            stats = api_stats.get(cid, {})
            rows.append({
                "Connector": cid,
                "Provider": meta.get("provider", "—"),
                "Category": meta.get("category", "—"),
                "Status": stats.get("status", meta.get("status", "—")),
                "Latency (ms)": stats.get("avg_latency_ms", "—"),
                "Auth": "API Key" if meta.get("api_key") else "Free",
                "Purpose": meta.get("description", "—"),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("""
**How it works:** `api_hub_engine.py` manages 14 connectors. Each connector has:
- **Retry logic** (3 attempts with exponential backoff)
- **Response caching** via `hub_cache.json` with configurable TTL
- **Fallback chains** (e.g., EIA crude → yfinance, OpenWeather → Open-Meteo)
- **Data validation** with min/max range checks before storage
- **Output** → Normalized `tbl_*.json` files for downstream consumption
""")

    # ── Panel 2: Sync & Orchestration ───────────────────────────────────────
    with st.expander("🔄 Sync & Orchestration — 18-Step Pipeline", expanded=False):
        steps = [
            ("Step 1", "Market Data Sync", "Crude prices, FX rates, weather via api_hub_engine"),
            ("Step 2", "News Feeds Sync", "RSS + NewsAPI headlines via news_engine"),
            ("Step 3", "Trade Data Sync", "UN Comtrade bitumen imports (HS 271320)"),
            ("Step 4", "Data Validation", "SRE sanity checks on all fetched data"),
            ("Step 5", "Calculations Refresh", "Demand proxy, correlations, forecasts"),
            ("Step 6", "Opportunity Scanning", "Price-drop reactivations, new cities, route changes"),
            ("Step 7", "CRM Profile Updates", "Auto-update relationship stages (hot/warm/cold)"),
            ("Step 8", "Alert Generation", "Create P0/P1/P2 alerts based on thresholds"),
            ("Step 9", "Communication Triggers", "Queue WhatsApp/Email based on rules"),
            ("Step 10", "Director Briefing", "Generate daily executive summary"),
            ("Step 11", "AI Learning", "Process deals & patterns for model improvement"),
            ("Step 12", "Smart Alert Scan", "Anomaly-based P0/P1/P2 alerting"),
            ("Step 13", "Infra Demand Intel", "GDELT + budget + demand scores"),
            ("Step 14", "Source Health Update", "Supplier/port reliability scores"),
            ("Step 15", "Auto Daily Insights", "LLM-generated daily analysis"),
            ("Step 16", "RAG Index Refresh", "Update FAISS/TF-IDF search index"),
            ("Step 17", "ML Model Training", "Retrain XGBoost/LightGBM models"),
            ("Step 18", "Market Signals", "Compute 10-signal composite intelligence"),
        ]
        df = pd.DataFrame(steps, columns=["#", "Step", "Purpose"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("Runs daily at 6 AM IST + on-demand via Sync Status page.")

    # ── Panel 3: AI Analysis Layer ──────────────────────────────────────────
    with st.expander("🤖 AI Analysis — 10 Features, 7 Workers", expanded=False):
        ai_features = [
            ("News Summarization", "ai_fallback_engine", "summarizer", "1h", "Summarizes articles to 2 sentences"),
            ("Tender Extraction", "nlp_extraction_engine", "extractor", "1h", "NER extraction from procurement text"),
            ("Demand Scoring", "ml_boost_engine", "scoring", "1h", "XGBoost/LightGBM opportunity scoring"),
            ("Price Forecasting", "ml_forecast_engine", "forecast", "2h", "ARIMA/Prophet 30-day forecasts"),
            ("Anomaly Detection", "anomaly_engine", "alert", "30m", "IsolationForest + Z-score detection"),
            ("Daily Reports", "auto_insight_engine", "report_writer", "24h", "LLM auto-generated insights"),
            ("Sentiment Analysis", "finbert_engine", "summarizer", "1h", "FinBERT financial sentiment scoring"),
            ("RAG Search", "rag_engine", "on-demand", "—", "FAISS semantic → TF-IDF → keyword fallback"),
            ("Communication Intel", "auto_comm_intelligence", "on-demand", "—", "Intelligent message optimization"),
            ("Market Intelligence", "market_intelligence_engine", "market_signals", "2h", "10-signal composite (crude+FX+weather+news+govt+tenders+economic+search+ports)"),
        ]
        df = pd.DataFrame(ai_features, columns=["Feature", "Module", "Worker", "Interval", "Description"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("""
**AI Fallback Chain:** Ollama (LOCAL, FREE) → HuggingFace (cloud) → GPT4All → OpenAI → Claude

**Resource Tiers:** LOW (all systems), MEDIUM (better servers), HIGH (enterprise)
""")

    # ── Panel 4: Calculation Engine ─────────────────────────────────────────
    with st.expander("🧮 Calculation Engine — Pricing & Margin Formulas", expanded=False):
        st.markdown("""
#### International (Imported) Bitumen Landed Cost
```
Landed Cost/MT = (FOB + Freight + Insurance) × USD/INR
    + Port Charges (Rs.10,000 per shipment / vessel qty)
    + CHA per MT (Rs.75)
    + Handling per MT (Rs.100)
    + Customs Duty (2.5% on landed value)
    + GST (18% on total)
```

#### Domestic (Refinery) Bitumen Landed Cost
```
Landed Cost/MT = (Base Rate × 1.18 GST) + (Distance km × Rate/km)
    Bulk: Rs.5.5/km  |  Drum: Rs.6.0/km
```

#### Decanter Bitumen Landed Cost
```
Landed Cost/MT = (Drum Cost × 1.18 GST) + Drum Transport
    + Rs.500 conversion + Local Transport
```

#### 3-Tier Offer Pricing (Min Margin: Rs.500/MT)
| Tier | Margin | Example (Landed Rs.40,000) |
|------|--------|---------------------------|
| Aggressive | +Rs.500 | Rs.40,500 |
| Balanced | +Rs.800 | Rs.40,800 |
| Premium | +Rs.1,200 | Rs.41,200 |
""")

    # ── Panel 5: Database & Storage ─────────────────────────────────────────
    with st.expander("🗄️ Database & Storage — 21 Tables + 27 JSON Files", expanded=False):
        db_tables = [
            ("suppliers", "63 records", "Supplier master: name, city, GSTIN, credit terms, last quote"),
            ("customers", "3 records", "Buyer master: name, city, demand, peak months"),
            ("deals", "Transaction log", "PO, qty, buy/sell price, margin, source, destination, stage"),
            ("opportunities", "Auto-discovered", "Type, margin estimate, trigger, templates"),
            ("price_history", "Time-series", "Brent, WTI prices with timestamps"),
            ("fx_history", "Time-series", "USD/INR, EUR/INR daily rates"),
            ("inventory", "Stock tracking", "Location, grade, quantity, cost, status"),
            ("communications", "Message log", "Channel, subject, content, status"),
            ("email_queue", "Outbound queue", "To, subject, body, type, status, retry count"),
            ("whatsapp_queue", "Outbound queue", "Number, template, status, WA ID"),
            ("whatsapp_sessions", "Active chats", "Phone, expiry, last message"),
            ("whatsapp_incoming", "Received msgs", "From, type, text, processed flag"),
            ("sync_logs", "Sync history", "Started, completed, status, APIs called, errors"),
            ("missing_inputs", "Data gaps", "Field, entity, priority, collection status"),
            ("director_briefings", "Daily briefs", "Date, briefing JSON, sent flags"),
            ("daily_logs", "Manual entries", "Date, author, type, customer, notes"),
            ("alerts", "System alerts", "Type, priority, title, status"),
            ("users", "Login", "Username, password hash, role"),
            ("audit_log", "Compliance", "Action, user, entity, timestamp"),
            ("recipient_lists", "Broadcast groups", "Email/WhatsApp groups"),
            ("source_registry", "Source health", "Supplier/port health, reliability score"),
        ]
        df = pd.DataFrame(db_tables, columns=["Table", "Size/Type", "Description"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Panel 6: CRM & Business Intelligence ───────────────────────────────
    with st.expander("👥 CRM & Business Intelligence", expanded=False):
        st.markdown("""
#### CRM Pipeline Stages
| Stage | Rule | Action |
|-------|------|--------|
| **Hot** | Last contact ≤ 7 days | Priority follow-up |
| **Warm** | Last contact ≤ 30 days | Regular engagement |
| **Cold** | Last contact ≤ 90 days | Reactivation campaign |
| **Dormant** | Last contact > 90 days | Win-back strategy |

#### Opportunity Engine — 4 Auto-Discovery Types
1. **Price-Drop Reactivation** — When landed cost drops, reactivate dormant buyers
2. **New Viable Cities** — When new routes become cost-effective
3. **Cheapest Route Changes** — When alternate suppliers offer better pricing
4. **Tender Matches** — Government tender keywords matched to capabilities

#### Negotiation Engine
- 7 common objections with scripted responses
- Confidence boosters with market data
- WhatsApp/Email/Call templates auto-generated
""")

    # ── Panel 7: Dashboard Visualization ────────────────────────────────────
    with st.expander("📊 Dashboard Visualization — 61 Pages, 11 Modules", expanded=False):
        modules = [
            ("Home", 4, "Live Market, Top Targets, Live Alerts, Quick Send"),
            ("Director Briefing", 4, "Today Focus, Sales Calendar, Alert System, Daily Log"),
            ("Procurement", 4, "Pricing Desk, Supplier Directory, Import Costing, Price Alerts"),
            ("Sales", 4, "Buyer CRM, Quotations, Follow-ups, Channels Setup"),
            ("Logistics", 4, "Freight Calculator, Supply Chain, Port Ops, Ecosystem"),
            ("Intelligence", 4, "Market Signals, Tender & Infra, News Center, Forecast"),
            ("Compliance", 4, "Govt Data Hub, GST & Legal, Risk Scoring, Change Log"),
            ("Reports", 4, "Financial Intel, Strategy & Export, Past Predictions, Road Budget"),
            ("System Control", 4, "Control Center, API Status, Sync & Ops, Settings"),
            ("Developer", 4, "Ops Map, Flow Map, Bug Tracker, Dev Logs"),
            ("AI & Knowledge", 4, "AI Assistant, Fallback Engine, Knowledge Base, AI Learning"),
        ]
        df = pd.DataFrame(modules, columns=["Module", "Tabs", "Sub-Pages"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("Chart engine uses Vastu Design colors: Navy #1e3a5f, Gold #c9a84c, Green #2d6a4f, Fire #b85c38")

    # ── Panel 8: Reports & Communication ────────────────────────────────────
    with st.expander("📄 Reports & Communication — PDF + Email + WhatsApp", expanded=False):
        st.markdown("""
#### Report Generation
- **Director Daily Briefing** — 7 sections: yesterday summary, today actions, 15-day outlook, sparklines, opportunities, alerts, market signals
- **PDF Export** — ReportLab A4, company header/footer, INR formatting (Rs.1,23,456), IST timestamps
- **Quote PDFs** — HSN 27132000, GPS tracking, PSU refinery sourcing, 24-hour dispatch
- **PDF Archive** — Saved to `pdf_exports/` with IST filename

#### Communication Channels
| Channel | Engine | Features |
|---------|--------|----------|
| **Email** | email_engine.py (SMTP) | Queue, scheduling, 7 template types, retry (max 3), delivery tracking |
| **WhatsApp** | whatsapp_engine.py (360dialog) | HSM templates, session msgs, broadcasts, queue |
| **Call Scripts** | communication_engine.py | Auto-generated with objection handling |

#### Auto-Triggers
- New quote → Email + WhatsApp to buyer
- Payment overdue 7/14/30 days → Reminder
- Director report → Daily 8:30 AM IST
- Weekly summary → Monday 9 AM IST
""")

    # ── Panel 9: Observability & Self-Healing ───────────────────────────────
    with st.expander("🛡️ Observability & Self-Healing (SRE)", expanded=False):
        st.markdown("""
#### SRE Engine — 6 Phases
| Phase | Component | Purpose |
|-------|-----------|---------|
| 1 | AuditLogger | Track all system events with IST timestamps |
| 2 | HealthCheckEngine | Monitor 8 entity types (DB, API, calc, exports, scheduler, config, endpoints, files) |
| 3 | SelfHealEngine | Auto-repair with retry backoff (5s, 15s, 30s) |
| 4 | SmartAlertEngine | P0/P1/P2 alerts with 30-min dedup suppression |
| 5 | BugAutoCreator | Auto-create bugs after 3 consecutive failures |
| 6 | ConflictProtector | Prevent concurrent write conflicts |

#### Alert Priorities
- **P0 (Critical):** API failures, pricing sanity check failures → immediate action
- **P1 (Warning):** Stale data (>2h), high error rates (>10%) → investigate
- **P2 (Info):** Opportunities, market signals → review when convenient
""")


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION 7 — EXPORT & SHARE
# ═════════════════════════════════════════════════════════════════════════════════

def _render_export():
    """Export buttons for system documentation."""
    st.markdown("---")
    st.markdown("#### 📤 Export System Documentation")

    c1, c2, c3 = st.columns(3)

    # 1. Full system architecture JSON
    with c1:
        report = {
            "title": "PPS Anantam — Dashboard System Architecture",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
            "engines": 40,
            "api_connectors": len(_load_json("hub_catalog.json", {})),
            "ai_features": 10,
            "sync_steps": 18,
            "db_tables": 21,
            "json_cache_files": len(list(_BASE.glob("tbl_*.json"))),
            "dashboard_pages": 61,
            "nav_modules": 11,
            "communication_channels": ["Email (SMTP)", "WhatsApp (360dialog)", "In-App Alerts"],
            "sre_phases": 6,
            "health": _load_json("sre_metrics.json", [{}])[-1] if _load_json("sre_metrics.json", []) else {},
            "api_stats": _load_json("api_stats.json", {}),
        }
        st.download_button(
            "📄 Architecture Report (JSON)",
            json.dumps(report, indent=2, ensure_ascii=False),
            file_name="system_architecture.json",
            mime="application/json",
            key="_flow_export_json",
        )

    # 2. Print-friendly version
    with c2:
        st.download_button(
            "📊 System Summary (CSV)",
            _generate_summary_csv(),
            file_name="system_summary.csv",
            mime="text/csv",
            key="_flow_export_csv",
        )

    # 3. Print button (browser)
    with c3:
        st.markdown("""
<button onclick="window.print()" style="
    background:#1e3a5f;color:white;border:none;padding:8px 20px;
    border-radius:6px;cursor:pointer;font-size:0.82rem;font-weight:600;
    margin-top:2px;">
    🖨️ Print This Page
</button>
""", unsafe_allow_html=True)

    st.caption("Use browser Print (Ctrl+P) to save as PDF or print a hard copy for documentation.")


def _generate_summary_csv() -> str:
    """Generate a CSV summary of the system architecture."""
    lines = ["Category,Item,Details"]
    lines.append("Engines,Total,40 Python engines in root directory")
    lines.append("APIs,Total Connectors,14 (with fallback chains)")
    lines.append("AI,Features,10 ML/AI features")
    lines.append("AI,Background Workers,7 daemon threads")
    lines.append("Sync,Steps,18 sequential steps (daily 6 AM IST)")
    lines.append("Database,SQLite Tables,21 tables")
    lines.append("Database,JSON Cache Files,27+ tbl_*.json files")
    lines.append("Dashboard,Pages,61 unique pages")
    lines.append("Dashboard,Navigation Modules,11 sidebar modules")
    lines.append("Communication,Email,SMTP queue with scheduling and templates")
    lines.append("Communication,WhatsApp,360dialog API with HSM templates")
    lines.append("Communication,Alerts,P0/P1/P2 smart alerts with dedup")
    lines.append("SRE,Phases,6 (Audit+Health+Heal+Alert+Bug+Conflict)")
    lines.append("Pricing,International,FOB+Freight+Insurance+Port+CHA+Customs+GST")
    lines.append("Pricing,Domestic,Base Rate x 1.18 GST + Freight")
    lines.append("Pricing,Offers,3-tier: Aggressive(+500) Balanced(+800) Premium(+1200)")
    return "\n".join(lines)
