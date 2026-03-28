"""
PPS Anantam — Developer Ops Map v1.0
=====================================
Unified single-pane developer operations dashboard.
9 sections: Summary, Sources, Workers, AI Models, Outputs,
Data Flow, Errors, Config Checklist, Export.
Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
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
_NAVY  = "#1e3a5f"
_GOLD  = "#c9a84c"
_GREEN = "#2d6a4f"
_FIRE  = "#b85c38"
_SLATE = "#64748b"

# ── JSON helpers ────────────────────────────────────────────────────────────────

def _load_json(filename: str, default=None):
    """Safely load a JSON file from project root."""
    try:
        fp = _BASE / filename
        if fp.exists():
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def _fmt_size(n: int) -> str:
    """Format byte size to human-readable."""
    if n < 1024:
        return f"{n} B"
    elif n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    else:
        return f"{n / (1024 * 1024):.1f} MB"


def _file_age(path: Path) -> str:
    """Return human-readable age of a file."""
    try:
        mt = path.stat().st_mtime
        delta = time.time() - mt
        if delta < 60:
            return "just now"
        elif delta < 3600:
            return f"{int(delta // 60)}m ago"
        elif delta < 86400:
            return f"{int(delta // 3600)}h ago"
        else:
            return f"{int(delta // 86400)}d ago"
    except Exception:
        return "—"


# ═════════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═════════════════════════════════════════════════════════════════════════════════

def render():
    """Render the Developer Ops Map page."""

    # ── Section A: Top Summary Bar ──────────────────────────────────────────
    _render_summary_bar()

    # ── Section F: Data Flow Map (always visible) ───────────────────────────
    _render_data_flow_map()

    # ── Sections B–E, G–I in expanders ──────────────────────────────────────
    with st.expander("📡 B — Incoming Data Sources", expanded=True):
        _render_incoming_sources()

    with st.expander("⚙️ C — Processing Workers", expanded=True):
        _render_workers()

    with st.expander("🤖 D — AI Models & Features", expanded=False):
        _render_ai_models()

    with st.expander("📦 E — Outgoing Outputs", expanded=False):
        _render_outputs()

    with st.expander("🚨 G — Error Center", expanded=False):
        _render_error_center()

    with st.expander("✅ H — Config Checklist", expanded=False):
        _render_config_checklist()

    with st.expander("📤 I — Export & Share", expanded=False):
        _render_export()

    # ── Refresh button ──────────────────────────────────────────────────────
    if st.button("🔄 Refresh Ops Map", key="_devops_refresh"):
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION A — TOP SUMMARY BAR
# ═════════════════════════════════════════════════════════════════════════════════

def _render_summary_bar():
    """Gradient banner with key health metrics."""
    # SRE metrics
    sre_list = _load_json("sre_metrics.json", [])
    latest_sre = sre_list[-1] if sre_list else {}
    health_pct = latest_sre.get("health_pct", 0)
    overall = latest_sre.get("overall", "UNKNOWN")
    total_checks = latest_sre.get("total", 0)
    ok_checks = latest_sre.get("ok", 0)
    warn_checks = latest_sre.get("warn", 0)
    fail_checks = latest_sre.get("fail", 0)

    # API stats
    api_stats = _load_json("api_stats.json", {})
    total_apis = len(api_stats)
    api_errors = sum(1 for v in api_stats.values() if v.get("status") == "FAIL")

    # Last sync
    sync_logs = _load_json("sync_logs.json", [])
    last_sync = sync_logs[-1] if sync_logs else {}
    sync_time = last_sync.get("completed_at", "Never")
    sync_status = last_sync.get("status", "—")

    # Error log
    error_log = _load_json("api_error_log.json", [])
    open_errors = sum(1 for e in error_log if e.get("status") == "Open")

    # Color based on health
    if health_pct >= 90:
        bar_color, grade = _GREEN, "A"
    elif health_pct >= 75:
        bar_color, grade = _GOLD, "B"
    elif health_pct >= 50:
        bar_color, grade = "#e6a817", "C"
    else:
        bar_color, grade = _FIRE, "D"

    st.markdown(f"""
<div style="background:linear-gradient(135deg,{bar_color},{_NAVY});
            color:white;padding:22px 28px;border-radius:14px;margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <div>
      <div style="font-size:1.5rem;font-weight:800;">
        🛠️ Developer Ops Map
      </div>
      <div style="font-size:0.82rem;opacity:0.88;margin-top:4px;">
        System Grade: <b>{grade}</b> | Overall: <b>{overall}</b>
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:2.2rem;font-weight:700;">{health_pct}%</div>
      <div style="font-size:0.7rem;opacity:0.7;">System Health</div>
    </div>
  </div>
  <div style="display:flex;gap:28px;margin-top:14px;font-size:0.78rem;flex-wrap:wrap;">
    <div>Checks: <b>{ok_checks}</b>✅ <b>{warn_checks}</b>⚠️ <b>{fail_checks}</b>❌ / {total_checks}</div>
    <div>APIs: <b>{total_apis}</b> total | <b>{api_errors}</b> failing</div>
    <div>Open Errors: <b>{open_errors}</b></div>
    <div>Last Sync: <b>{sync_status}</b> — {sync_time}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION B — INCOMING DATA SOURCES
# ═════════════════════════════════════════════════════════════════════════════════

def _render_incoming_sources():
    """Table of all API connectors with status, latency, last call."""
    catalog = _load_json("hub_catalog.json", {})
    api_stats = _load_json("api_stats.json", {})

    rows = []
    for cid, meta in sorted(catalog.items()):
        stats = api_stats.get(cid, {})
        status = stats.get("status", meta.get("status", "—"))
        latency = stats.get("avg_latency_ms", "—")
        last_call = stats.get("last_call_time", "—")
        calls = stats.get("calls", 0)
        failures = stats.get("failures", 0)
        plan = stats.get("plan", meta.get("plan", "Free"))
        ttl = meta.get("ttl_seconds", "—")

        if isinstance(ttl, (int, float)):
            if ttl >= 86400:
                ttl_str = f"{int(ttl // 86400)}d"
            elif ttl >= 3600:
                ttl_str = f"{int(ttl // 3600)}h"
            else:
                ttl_str = f"{int(ttl // 60)}m"
        else:
            ttl_str = str(ttl)

        rows.append({
            "Connector": cid,
            "Provider": meta.get("provider", "—"),
            "Status": status,
            "Latency (ms)": latency,
            "Calls": calls,
            "Failures": failures,
            "Last Call": last_call,
            "TTL": ttl_str,
            "Plan": plan,
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No API connectors found in catalog.")

    # Summary metrics
    total = len(rows)
    ok_count = sum(1 for r in rows if r["Status"] in ("OK", "Live"))
    warn_count = sum(1 for r in rows if r["Status"] == "WARN")
    fail_count = sum(1 for r in rows if r["Status"] in ("FAIL", "Disabled"))
    st.caption(f"Total: {total} | ✅ OK: {ok_count} | ⚠️ Warn: {warn_count} | ❌ Fail/Disabled: {fail_count}")


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION C — PROCESSING WORKERS
# ═════════════════════════════════════════════════════════════════════════════════

def _render_workers():
    """Table of all AI workers + sync engine status."""
    rows = []

    # Try to get live worker status
    try:
        from ai_workers import get_worker_status
        worker_status = get_worker_status()
        for name, info in worker_status.items():
            rows.append({
                "Worker": name,
                "Interval": info.get("interval_display", "—"),
                "Status": "🟢 Running" if info.get("running") else "⚪ Idle",
                "Last Run": info.get("last_run", "—"),
                "Errors (24h)": info.get("errors_24h", 0),
                "Tier": info.get("tier", "—"),
            })
    except Exception:
        # Fallback: read worker log
        worker_log = _load_json("ai_worker_log.json", [])
        seen = {}
        for entry in reversed(worker_log):
            wname = entry.get("worker", "")
            if wname and wname not in seen:
                seen[wname] = entry
        for wname, entry in sorted(seen.items()):
            rows.append({
                "Worker": wname,
                "Interval": "—",
                "Status": "⚪ Last seen",
                "Last Run": entry.get("timestamp", "—"),
                "Errors (24h)": "—",
                "Tier": "—",
            })

    # Sync engine status
    sync_logs = _load_json("sync_logs.json", [])
    last_sync = sync_logs[-1] if sync_logs else {}
    rows.append({
        "Worker": "sync_engine",
        "Interval": "60 min",
        "Status": "🟢 OK" if last_sync.get("status") == "success" else "⚠️ " + last_sync.get("status", "Unknown"),
        "Last Run": last_sync.get("completed_at", "—"),
        "Errors (24h)": len(last_sync.get("errors", [])),
        "Tier": "CORE",
    })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No worker data available.")


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION D — AI MODELS & FEATURES
# ═════════════════════════════════════════════════════════════════════════════════

def _render_ai_models():
    """AI feature map with module status and health."""
    rows = []

    try:
        from ai_workers import get_feature_map
        fmap = get_feature_map()
        for feat_name, info in fmap.items():
            rows.append({
                "Feature": feat_name,
                "Module": info.get("module", "—"),
                "Import": "✅" if info.get("module_loaded") else "❌",
                "Worker": info.get("worker", "—"),
                "Worker Status": "🟢" if info.get("worker_running") else "⚪",
                "Health": info.get("health", "—"),
            })
    except Exception:
        # Fallback: list known modules
        _KNOWN_MODULES = [
            ("News Summarization", "ai_fallback_engine"),
            ("Tender Extraction", "nlp_extraction_engine"),
            ("Demand Scoring", "ml_boost_engine"),
            ("Price Forecasting", "ml_forecast_engine"),
            ("Anomaly Alerts", "anomaly_engine"),
            ("Daily Reports", "auto_insight_engine"),
            ("Sentiment Analysis", "finbert_engine"),
            ("RAG Search", "rag_engine"),
            ("Communication Intel", "auto_comm_intelligence"),
            ("Market Intelligence", "market_intelligence_engine"),
        ]
        for feat, mod in _KNOWN_MODULES:
            importable = False
            try:
                __import__(mod)
                importable = True
            except Exception:
                pass
            rows.append({
                "Feature": feat,
                "Module": mod,
                "Import": "✅" if importable else "❌",
                "Worker": "—",
                "Worker Status": "—",
                "Health": "—",
            })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        ok = sum(1 for r in rows if r["Import"] == "✅")
        st.caption(f"Modules loaded: {ok}/{len(rows)}")
    else:
        st.info("No AI feature data available.")


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION E — OUTGOING OUTPUTS
# ═════════════════════════════════════════════════════════════════════════════════

def _render_outputs():
    """Scan all tbl_*.json and key output files."""
    rows = []

    # Scan tbl_*.json files
    for fp in sorted(_BASE.glob("tbl_*.json")):
        try:
            size = fp.stat().st_size
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                records = len(data)
            elif isinstance(data, dict):
                records = len(data)
            else:
                records = 1
        except Exception:
            size = 0
            records = 0

        rows.append({
            "File": fp.name,
            "Size": _fmt_size(size),
            "Records": records,
            "Updated": _file_age(fp),
        })

    # Scan news_data/ folder
    news_dir = _BASE / "news_data"
    if news_dir.exists():
        for fp in sorted(news_dir.glob("*.json")):
            try:
                size = fp.stat().st_size
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = len(data) if isinstance(data, list) else len(data) if isinstance(data, dict) else 1
            except Exception:
                size, records = 0, 0
            rows.append({
                "File": f"news_data/{fp.name}",
                "Size": _fmt_size(size),
                "Records": records,
                "Updated": _file_age(fp),
            })

    # Key system logs
    for fname in ["api_stats.json", "api_health_log.json", "api_error_log.json",
                   "sre_health_status.json", "sre_metrics.json", "sre_alerts.json",
                   "sync_logs.json", "ai_worker_log.json", "hub_activity_log.json"]:
        fp = _BASE / fname
        if fp.exists():
            try:
                size = fp.stat().st_size
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = len(data) if isinstance(data, (list, dict)) else 1
            except Exception:
                size, records = 0, 0
            rows.append({
                "File": fname,
                "Size": _fmt_size(size),
                "Records": records,
                "Updated": _file_age(fp),
            })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        total_size = sum((_BASE / r["File"]).stat().st_size for r in rows
                         if (_BASE / r["File"]).exists())
        st.caption(f"Total files: {len(rows)} | Total size: {_fmt_size(total_size)}")
    else:
        st.info("No output files found.")


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION F — DATA FLOW MAP
# ═════════════════════════════════════════════════════════════════════════════════

def _render_data_flow_map():
    """Visual 3-column data flow: Sources → Processing → Outputs."""
    st.markdown(f"""
<div style="border:1px solid #e0d8cc;border-radius:12px;padding:16px;margin-bottom:14px;
            background:#fafafa;">
  <div style="font-size:0.85rem;font-weight:700;color:{_NAVY};margin-bottom:10px;">
    📊 Data Flow Pipeline
  </div>
  <div style="display:flex;gap:8px;align-items:stretch;flex-wrap:wrap;">
    <div style="flex:1;min-width:180px;background:#e8f4f8;border-radius:8px;padding:10px;
                border-left:4px solid {_NAVY};">
      <div style="font-size:0.72rem;font-weight:700;color:{_NAVY};margin-bottom:6px;">
        📡 SOURCES (Incoming)
      </div>
      <div style="font-size:0.65rem;color:{_SLATE};line-height:1.6;">
        • yfinance (Crude/FX)<br>
        • Open-Meteo (Weather)<br>
        • Google News RSS<br>
        • UN Comtrade (Trade)<br>
        • World Bank (Macro)<br>
        • Frankfurter (FX)<br>
        • Google Trends (Search)<br>
        • data.gov.in (Infra)
      </div>
    </div>
    <div style="display:flex;align-items:center;font-size:1.2rem;color:{_GOLD};">➜</div>
    <div style="flex:1;min-width:180px;background:#fef9e7;border-radius:8px;padding:10px;
                border-left:4px solid {_GOLD};">
      <div style="font-size:0.72rem;font-weight:700;color:{_GOLD};margin-bottom:6px;">
        ⚙️ PROCESSING (18 Steps)
      </div>
      <div style="font-size:0.65rem;color:{_SLATE};line-height:1.6;">
        • Sync Engine (18 steps)<br>
        • 7 AI Workers<br>
        • Market Intelligence<br>
        • Opportunity Scanner<br>
        • CRM Auto-Update<br>
        • Alert Generator<br>
        • SRE Self-Healing<br>
        • RAG Index Builder
      </div>
    </div>
    <div style="display:flex;align-items:center;font-size:1.2rem;color:{_GREEN};">➜</div>
    <div style="flex:1;min-width:180px;background:#e8f5e9;border-radius:8px;padding:10px;
                border-left:4px solid {_GREEN};">
      <div style="font-size:0.72rem;font-weight:700;color:{_GREEN};margin-bottom:6px;">
        📦 OUTPUTS (Data Tables)
      </div>
      <div style="font-size:0.65rem;color:{_SLATE};line-height:1.6;">
        • tbl_crude_prices.json<br>
        • tbl_fx_rates.json<br>
        • tbl_weather.json<br>
        • tbl_news_feed.json<br>
        • tbl_market_signals.json<br>
        • tbl_ports_volume.json<br>
        • tbl_refinery_production.json<br>
        • 20+ more tables
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION G — ERROR CENTER
# ═════════════════════════════════════════════════════════════════════════════════

def _render_error_center():
    """P0/P1/P2 errors with severity, auto-fix status."""
    error_log = _load_json("api_error_log.json", [])
    sre_alerts = _load_json("sre_alerts.json", [])

    rows = []
    for e in error_log:
        rows.append({
            "Time": e.get("datetime_ist", "—"),
            "Severity": e.get("severity", "—"),
            "Source": e.get("api_id", e.get("component", "—")),
            "Error": (e.get("message", "—"))[:80],
            "Auto-Fixed": "✅" if e.get("auto_fixed") else "❌",
            "Status": e.get("status", "—"),
        })

    for a in sre_alerts:
        rows.append({
            "Time": a.get("timestamp_ist", a.get("datetime_ist", "—")),
            "Severity": a.get("severity", a.get("priority", "—")),
            "Source": a.get("entity", a.get("source", "SRE")),
            "Error": (a.get("message", a.get("detail", "—")))[:80],
            "Auto-Fixed": "—",
            "Status": a.get("status", "—"),
        })

    if rows:
        # Sort by time descending (most recent first)
        rows.sort(key=lambda x: x["Time"], reverse=True)
        df = pd.DataFrame(rows[:100])  # Cap at 100 most recent
        st.dataframe(df, use_container_width=True, hide_index=True)

        open_count = sum(1 for r in rows if r["Status"] == "Open")
        p0 = sum(1 for r in rows if r["Severity"] == "P0")
        p1 = sum(1 for r in rows if r["Severity"] == "P1")
        p2 = sum(1 for r in rows if r["Severity"] == "P2")
        st.caption(f"Total: {len(rows)} | Open: {open_count} | P0: {p0} | P1: {p1} | P2: {p2}")
    else:
        st.success("No errors recorded. System clean.")


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION H — CONFIG CHECKLIST
# ═════════════════════════════════════════════════════════════════════════════════

def _render_config_checklist():
    """Verify key settings, paths, and feature flags."""
    checks = []

    # Database exists
    db_path = _BASE / "bitumen_dashboard.db"
    checks.append(("Database (SQLite)", db_path.exists()))

    # Settings file
    settings_path = _BASE / "settings.json"
    settings = _load_json("settings.json", {})
    checks.append(("settings.json exists", settings_path.exists()))

    # Key settings present
    checks.append(("Business rules configured", bool(settings.get("business_rules") or settings.get("min_margin"))))

    # Hub catalog
    catalog = _load_json("hub_catalog.json", {})
    checks.append(("API catalog loaded", len(catalog) > 0))

    # Key data tables exist
    for tbl in ["tbl_crude_prices.json", "tbl_fx_rates.json", "tbl_weather.json",
                 "tbl_news_feed.json", "tbl_ports_volume.json"]:
        path = _BASE / tbl
        checks.append((f"{tbl}", path.exists() and path.stat().st_size > 10))

    # Market signals
    signals_path = _BASE / "tbl_market_signals.json"
    checks.append(("Market signals computed", signals_path.exists() and signals_path.stat().st_size > 10))

    # News data folder
    news_dir = _BASE / "news_data"
    checks.append(("news_data/ folder", news_dir.exists()))

    # Python modules importable
    for mod_name in ["database", "calculation_engine", "sync_engine", "sre_engine",
                     "api_hub_engine", "market_intelligence_engine"]:
        try:
            __import__(mod_name)
            checks.append((f"Module: {mod_name}", True))
        except Exception:
            checks.append((f"Module: {mod_name}", False))

    # Render checklist
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    for label, ok in checks:
        icon = "✅" if ok else "❌"
        st.markdown(f"{icon} **{label}**")

    st.markdown("---")
    pct = int(passed / total * 100) if total else 0
    color = _GREEN if pct >= 90 else _GOLD if pct >= 70 else _FIRE
    st.markdown(f"**Config Score: <span style='color:{color};'>{passed}/{total} ({pct}%)</span>**",
                unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════════
# SECTION I — EXPORT & SHARE
# ═════════════════════════════════════════════════════════════════════════════════

def _render_export():
    """Download buttons for system reports."""

    c1, c2, c3 = st.columns(3)

    # 1. Full system report JSON
    with c1:
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M IST"),
            "sre_metrics": _load_json("sre_metrics.json", [])[-5:] if _load_json("sre_metrics.json", []) else [],
            "api_stats": _load_json("api_stats.json", {}),
            "last_sync": (_load_json("sync_logs.json", []) or [{}])[-1],
            "hub_catalog_count": len(_load_json("hub_catalog.json", {})),
            "open_errors": sum(1 for e in _load_json("api_error_log.json", [])
                               if e.get("status") == "Open"),
        }
        st.download_button(
            "📄 System Report (JSON)",
            json.dumps(report, indent=2, ensure_ascii=False),
            file_name="system_report.json",
            mime="application/json",
            key="_devops_export_json",
        )

    # 2. Error log CSV
    with c2:
        error_log = _load_json("api_error_log.json", [])
        if error_log:
            df_err = pd.DataFrame(error_log)
            csv_data = df_err.to_csv(index=False)
        else:
            csv_data = "No errors"
        st.download_button(
            "🚨 Error Log (CSV)",
            csv_data,
            file_name="error_log.csv",
            mime="text/csv",
            key="_devops_export_errors",
        )

    # 3. Health snapshot CSV
    with c3:
        health = _load_json("sre_health_status.json", [])
        if health:
            df_health = pd.DataFrame(health)
            csv_health = df_health.to_csv(index=False)
        else:
            csv_health = "No health data"
        st.download_button(
            "💚 Health Snapshot (CSV)",
            csv_health,
            file_name="health_snapshot.csv",
            mime="text/csv",
            key="_devops_export_health",
        )
