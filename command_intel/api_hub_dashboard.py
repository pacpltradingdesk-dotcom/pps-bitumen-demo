"""
API HUB Dashboard — Streamlit UI
PPS Anantam Agentic AI Eco System v3.2.1
=========================================
Single control panel for all external API integrations.

Sections:
  A) API Catalog — editable table of all connectors
  B) Test All APIs — live connectivity test with results
  C) Switch / Replace API — hot-swap any connector
  D) Normalized Data Tables — view the 7 standard output tables
  E) Auto-Update Engine — scheduler status + activity log
"""

import sys
import os
import json
import datetime
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd

# ─── Engine import ────────────────────────────────────────────────────────────
try:
    from api_hub_engine import (
        HubCatalog, NormalizedTables, HubHealthMonitor,
        run_all_connectors, connect_eia, connect_comtrade,
        connect_weather, connect_news, connect_fx,
        connect_ports, connect_refinery,
        init_hub,
        DEFAULT_CATALOG,
    )
    _HUB_OK = True
except Exception as _e:
    _HUB_OK = False
    _HUB_ERR = str(_e)

# ─── Style constants ──────────────────────────────────────────────────────────
_STATUS_COLOR = {
    "Live":     "#16a34a",
    "Failing":  "#dc2626",
    "Disabled": "#64748b",
    "Unknown":  "#d97706",
}
_STATUS_BG = {
    "Live":     "#f0fdf4",
    "Failing":  "#fef2f2",
    "Disabled": "#f8fafc",
    "Unknown":  "#fffbeb",
}
_CAT_ICON = {
    "Crude":   "🛢️",
    "Trade":   "🚢",
    "Weather": "🌤️",
    "News":    "📰",
    "FX":      "💱",
    "Ports":   "⚓",
    "Refinery":"🏭",
    "Automation": "⚙️",
}
_FREQ_LABEL = {"5m": "5 min", "15m": "15 min", "1h": "1 hour", "1d": "Daily"}

CONNECTOR_FN_MAP = {
    "eia_crude":       (connect_eia,      "tbl_crude_prices"),
    "un_comtrade":     (connect_comtrade, "tbl_trade_imports"),
    "openweather":     (connect_weather,  "tbl_weather"),
    "open_meteo_hub":  (connect_weather,  "tbl_weather"),
    "newsapi":         (connect_news,     "tbl_news_feed"),
    "gnews_rss":       (connect_news,     "tbl_news_feed"),
    "frankfurter_fx":  (connect_fx,       "tbl_fx_rates"),
    "fawazahmed0_fx":  (connect_fx,       "tbl_fx_rates"),
    "ports_volume":    (connect_ports,    "tbl_ports_volume"),
    "refinery":        (connect_refinery, "tbl_refinery_production"),
}


def _badge(text: str, color: str = "#1e3a5f", bg: str = "#e8f0f8") -> str:
    return (
        f'<span style="background:{bg};color:{color};font-size:0.65rem;font-weight:700;'
        f'padding:2px 9px;border-radius:10px;border:1px solid {color}33;">{text}</span>'
    )


def _section_header(icon: str, title: str, subtitle: str = "") -> None:
    st.markdown(f"""
<div style="border-bottom:2px solid #e8dcc8;padding-bottom:8px;margin:18px 0 12px 0;
            display:flex;align-items:baseline;gap:10px;">
  <span style="font-size:1.05rem;font-weight:800;color:#1e3a5f;">{icon} {title}</span>
  {"<span style='font-size:0.72rem;color:#64748b;'>" + subtitle + "</span>" if subtitle else ""}
</div>""", unsafe_allow_html=True)


def _kpi_card(title: str, value: str, sub: str = "", color: str = "#1e3a5f") -> str:
    return f"""
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;
            padding:14px 16px;text-align:center;">
  <div style="font-size:0.6rem;color:#64748b;font-weight:600;text-transform:uppercase;
              letter-spacing:0.06em;margin-bottom:4px;">{title}</div>
  <div style="font-size:1.5rem;font-weight:800;color:{color};">{value}</div>
  <div style="font-size:0.67rem;color:#94a3b8;margin-top:2px;">{sub}</div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    if not _HUB_OK:
        st.error(f"API HUB Engine failed to load: {_HUB_ERR}")
        st.info("Ensure `api_hub_engine.py` is in the dashboard root directory.")
        return

    init_hub()

    # ── Page-level KPI bar ────────────────────────────────────────────────────
    cat = HubCatalog.load()
    total_apis  = len(cat)
    live_apis   = sum(1 for v in cat.values() if v.get("status") == "Live")
    fail_apis   = sum(1 for v in cat.values() if v.get("status") == "Failing")
    dis_apis    = sum(1 for v in cat.values() if v.get("status") == "Disabled")
    tbl_summary = NormalizedTables.summary()
    total_rows  = sum(v for k, v in tbl_summary.items() if k != "last_updated")

    hk1, hk2, hk3, hk4, hk5 = st.columns(5)
    hk1.markdown(_kpi_card("Total Connectors", str(total_apis), "in catalog"), unsafe_allow_html=True)
    hk2.markdown(_kpi_card("✅ Live",  str(live_apis), "connected", "#16a34a"), unsafe_allow_html=True)
    hk3.markdown(_kpi_card("❌ Failing", str(fail_apis), "need attention", "#dc2626"), unsafe_allow_html=True)
    hk4.markdown(_kpi_card("⚪ Disabled", str(dis_apis), "key not set"), unsafe_allow_html=True)
    hk5.markdown(_kpi_card("📊 Total Rows", f"{total_rows:,}", "across 7 tables"), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs([
        "📋 A  API Catalog",
        "🧪 B  Test APIs",
        "🔄 C  Switch / Replace",
        "🗄️ D  Data Tables",
        "⏱️ E  Auto-Update Engine",
    ])

    with tab_a:
        _render_catalog(cat)
    with tab_b:
        _render_test_panel(cat)
    with tab_c:
        _render_switch_panel(cat)
    with tab_d:
        _render_data_tables(tbl_summary)
    with tab_e:
        _render_scheduler_panel()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB A — API CATALOG (Editable)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_catalog(cat: dict) -> None:
    _section_header("📋", "API Catalog", "Editable registry of all connectors — single source of truth")

    st.info(
        "**Keys are never hardcoded.** Enter API keys in the Key_Value column below. "
        "Status updates automatically after testing. Disabled = key missing or manually turned off."
    )

    # Build DataFrame
    rows = []
    for cid, v in cat.items():
        status = v.get("status", "Unknown")
        rows.append({
            "connector_id":    cid,
            "API_Name":        v.get("api_name", cid),
            "Category":        v.get("category", ""),
            "Provider":        v.get("provider", ""),
            "Base_URL":        v.get("base_url", ""),
            "Auth_Type":       v.get("auth_type", "None"),
            "Key_Value":       v.get("key_value", ""),
            "Status":          status,
            "Refresh_Freq":    v.get("refresh_frequency", "1h"),
            "Cache_TTL_sec":   v.get("cache_ttl_sec", 3600),
            "Last_Success":    v.get("last_success_time") or "Never",
            "Last_Error":      v.get("last_error_message", "")[:80],
            "Fallback_API":    v.get("fallback_api", ""),
            "Output_Tables":   ", ".join(v.get("data_output_tables", [])),
            "Notes":           v.get("notes", "")[:100],
        })

    df = pd.DataFrame(rows)

    # Category filter
    cat_filter = st.selectbox("Filter by Category",
                              ["All"] + sorted(df["Category"].unique().tolist()), key="cat_filter_a")
    if cat_filter != "All":
        df_show = df[df["Category"] == cat_filter].copy()
    else:
        df_show = df.copy()

    # Style Status column
    def _status_style(val: str):
        color = {"Live": "green", "Failing": "red", "Disabled": "gray"}.get(val, "orange")
        return f"color: {color}; font-weight: bold"

    # Editable grid via st.data_editor
    st.markdown("**Edit Key_Value to add/update API keys. Changes are saved on click of 'Save Changes'.**")
    edited = st.data_editor(
        df_show[[
            "API_Name", "Category", "Auth_Type", "Key_Value",
            "Status", "Refresh_Freq", "Last_Success", "Last_Error",
            "Fallback_API", "Output_Tables", "Notes", "connector_id",
        ]],
        use_container_width=True,
        hide_index=True,
        disabled=["API_Name", "Category", "Auth_Type", "Status",
                  "Last_Success", "Last_Error", "Output_Tables", "connector_id"],
        column_config={
            "Key_Value": st.column_config.TextColumn(
                "Key_Value (masked)",
                help="Enter API key here. Saved securely in hub_catalog.json.",
                width="medium",
            ),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "connector_id": st.column_config.TextColumn("ID", width="small"),
        },
        key="catalog_editor",
    )

    if st.button("💾 Save Catalog Changes", type="primary"):
        saved = 0
        for _, row in edited.iterrows():
            cid      = row["connector_id"]
            new_key  = str(row.get("Key_Value", "")).strip()
            new_freq = str(row.get("Refresh_Freq", "1h")).strip()
            new_note = str(row.get("Notes", "")).strip()
            HubCatalog.update_field(cid, "key_value",          new_key)
            HubCatalog.update_field(cid, "refresh_frequency",  new_freq)
            HubCatalog.update_field(cid, "notes",              new_note)
            # If key just set for a disabled connector, mark it as Unknown (needs test)
            if new_key and HubCatalog.get(cid).get("status") == "Disabled":
                HubCatalog.update_field(cid, "status", "Unknown")
            saved += 1
        st.success(f"Saved changes to {saved} connectors. Click 'Test All APIs' to verify keys.")
        st.rerun()

    # Read-only full detail table
    with st.expander("📊 Full Catalog Details (read-only)"):
        st.dataframe(
            df[["API_Name", "Category", "Provider", "Base_URL", "Auth_Type",
                "Status", "Refresh_Freq", "Fallback_API", "Output_Tables", "Notes"]],
            use_container_width=True, hide_index=True,
        )

    # Key setup guide
    with st.expander("🔑 How to Get Free API Keys"):
        st.markdown("""
| Connector | Provider | URL | Free Tier |
|-----------|---------|-----|-----------|
| `eia_crude` | US Energy Info Admin | [eia.gov/opendata](https://www.eia.gov/opendata/register.php) | Free — unlimited |
| `un_comtrade` | UN Statistics | [comtradeapi.un.org](https://comtradeapi.un.org) | Preview free; full requires subscription |
| `openweather` | OpenWeather | [openweathermap.org/api](https://openweathermap.org/api) | Free — 1,000 calls/day |
| `newsapi` | NewsAPI.org | [newsapi.org](https://newsapi.org) | Free dev — 100 req/day |
| `frankfurter_fx` | Frankfurter ECB | No key required | — |
| `open_meteo_hub` | Open-Meteo | No key required | — |
| `gnews_rss` | Google News RSS | No key required | — |
| `fawazahmed0_fx` | fawazahmed0 CDN | No key required | — |

**Steps:** Register → Get key → Paste in Key_Value above → Save → Test All.
""")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB B — TEST ALL APIs
# ═══════════════════════════════════════════════════════════════════════════════

def _render_test_panel(cat: dict) -> None:
    _section_header("🧪", "Test All APIs", "Live connectivity test — updates Status, Last_Success_Time, Last_Error")

    col_a, col_b = st.columns([2, 2])
    with col_a:
        test_mode = st.radio(
            "Test mode",
            ["Quick ping (URL only)", "Full data fetch (writes to tables)"],
            key="test_mode",
        )
    with col_b:
        specific = st.selectbox("Test single connector", ["All"] + list(cat.keys()),
                                key="test_specific")

    if st.button("▶ Run Tests Now", type="primary", use_container_width=True):
        full_fetch = (test_mode == "Full data fetch (writes to tables)")

        if specific != "All":
            # Single connector test
            with st.spinner(f"Testing {specific}…"):
                if full_fetch:
                    fn_entry = CONNECTOR_FN_MAP.get(specific)
                    if fn_entry:
                        result = fn_entry[0]()
                        results = [{"connector_id": specific,
                                    "ok": result.get("ok"), "status": "Live" if result.get("ok") else "Fail",
                                    "latency_ms": "—",
                                    "error": result.get("error", "")}]
                    else:
                        results = [HubHealthMonitor.test_one(specific)]
                else:
                    results = [HubHealthMonitor.test_one(specific)]
        else:
            # All connectors
            if full_fetch:
                with st.spinner("Running all connectors — fetching real data…"):
                    summary = run_all_connectors(force=True)
                results = []
                for cid, r in summary["results"].items():
                    results.append({
                        "connector_id": cid,
                        "ok":           r.get("ok", False),
                        "status":       "Live" if r.get("ok") else "Fail",
                        "latency_ms":   "—",
                        "error":        r.get("error", ""),
                        "records":      r.get("records", 0),
                        "source":       r.get("source", ""),
                    })
            else:
                with st.spinner("Pinging all API endpoints…"):
                    results = HubHealthMonitor.test_all()

        # Display results
        passed = sum(1 for r in results if r.get("ok"))
        failed = len(results) - passed

        if failed == 0:
            st.success(f"✅ All {passed} connectors reachable / operational")
        else:
            st.warning(f"⚠️ {passed} OK — {failed} failed (may need API key or is Disabled)")

        for r in results:
            cid    = r.get("connector_id", "?")
            ok     = r.get("ok", False)
            status = r.get("status", "?")
            lat    = r.get("latency_ms", "—")
            err    = r.get("error", "")
            recs   = r.get("records", "")
            src    = r.get("source", "")
            entry  = cat.get(cid, {})

            color = "#16a34a" if ok else ("#64748b" if status == "Disabled" else "#dc2626")
            icon  = "✅" if ok else ("⚪" if status == "Disabled" else "❌")

            detail = ""
            if recs:
                detail += f" · {recs} records"
            if src:
                detail += f" · via {src}"
            if err:
                detail += f" · ⚠️ {err[:60]}"

            st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:7px 12px;
            border-left:4px solid {color};background:#f8fafc;
            border-radius:0 6px 6px 0;margin-bottom:5px;">
  <span style="font-size:1rem;">{icon}</span>
  <span style="font-weight:700;color:#1e293b;font-size:0.85rem;width:160px;">{cid}</span>
  <span style="font-size:0.75rem;color:#475569;">{entry.get('api_name','')[:40]}</span>
  <span style="margin-left:auto;font-size:0.68rem;color:{color};font-weight:700;">{status}</span>
  {"<span style='font-size:0.65rem;color:#94a3b8;'>⏱ " + str(lat) + "ms</span>" if lat != "—" else ""}
  <span style="font-size:0.68rem;color:#64748b;">{detail}</span>
</div>""", unsafe_allow_html=True)

        st.caption(f"Last tested: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB C — SWITCH / REPLACE API
# ═══════════════════════════════════════════════════════════════════════════════

def _render_switch_panel(cat: dict) -> None:
    _section_header("🔄", "Switch / Replace API", "Hot-swap any connector without editing dashboard pages")

    st.info("""
**How it works:**
- Select a failing connector
- Enter the new Base_URL and optionally a new Endpoint
- The engine auto-maps the new API output to the same normalized table
- No other dashboard page needs modification — all pages read from `tbl_*` tables
""")

    # Select connector to replace
    cid = st.selectbox("Select connector to reconfigure", list(cat.keys()), key="switch_cid")
    entry = cat.get(cid, {})

    if not entry:
        st.warning("Connector not found")
        return

    st.markdown(f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;margin-bottom:12px;">
  <div style="font-weight:700;color:#1e3a5f;margin-bottom:6px;">{entry.get('api_name','')}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:0.75rem;color:#475569;">
    <div><b>Status:</b> {entry.get('status','?')}</div>
    <div><b>Auth:</b> {entry.get('auth_type','?')}</div>
    <div><b>Category:</b> {entry.get('category','?')}</div>
    <div><b>Current URL:</b> {entry.get('base_url','')[:50]}</div>
    <div><b>Fallback:</b> {entry.get('fallback_api','none')}</div>
    <div><b>Output:</b> {', '.join(entry.get('data_output_tables',[]))}</div>
  </div>
</div>""", unsafe_allow_html=True)

    with st.form(key="switch_form"):
        new_url      = st.text_input("New Base_URL",
                                     value=entry.get("base_url", ""),
                                     help="Full URL of replacement API provider")
        new_endpoint = st.text_input("New Endpoint(s) (comma-separated)",
                                     value=", ".join(entry.get("endpoints", [])))
        new_key      = st.text_input("New API Key (leave blank if not needed)",
                                     type="password")
        new_fallback = st.text_input("New Fallback connector ID",
                                     value=entry.get("fallback_api", ""))
        new_notes    = st.text_area("Notes / reason for change",
                                    value=entry.get("notes", ""))
        submitted    = st.form_submit_button("💾 Apply Replacement", type="primary")

    if submitted:
        HubCatalog.update_field(cid, "base_url",    new_url.strip())
        HubCatalog.update_field(cid, "endpoints",   [e.strip() for e in new_endpoint.split(",") if e.strip()])
        HubCatalog.update_field(cid, "fallback_api", new_fallback.strip())
        HubCatalog.update_field(cid, "notes",        new_notes.strip())
        if new_key.strip():
            HubCatalog.update_field(cid, "key_value", new_key.strip())
            HubCatalog.update_field(cid, "status",    "Unknown")
        st.success(f"✅ Connector `{cid}` updated. Click 'Test APIs' to verify the new endpoint.")
        st.rerun()

    # Bulk enable/disable
    st.markdown("---")
    _section_header("🔧", "Bulk Enable / Disable", "Toggle connectors without deleting config")

    for _cid, _entry in cat.items():
        _status = _entry.get("status", "Disabled")
        _col1, _col2 = st.columns([5, 1])
        with _col1:
            _color = _STATUS_COLOR.get(_status, "#64748b")
            st.markdown(
                f'<span style="font-size:0.8rem;color:{_color};font-weight:600;">'
                f'{"✅" if _status=="Live" else "❌"} {_cid}</span> '
                f'<span style="font-size:0.7rem;color:#94a3b8;">{_entry.get("api_name","")[:50]}</span>',
                unsafe_allow_html=True,
            )
        with _col2:
            if _status != "Disabled":
                if st.button("Disable", key=f"dis_{_cid}"):
                    HubCatalog.update_field(_cid, "status", "Disabled")
                    HubCatalog.update_field(_cid, "last_error_message", "Manually disabled by user")
                    st.rerun()
            else:
                if st.button("Enable", key=f"en_{_cid}"):
                    HubCatalog.update_field(_cid, "status", "Unknown")
                    HubCatalog.update_field(_cid, "last_error_message", "")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB D — NORMALIZED DATA TABLES
# ═══════════════════════════════════════════════════════════════════════════════

def _render_data_tables(tbl_summary: dict) -> None:
    _section_header("🗄️", "Normalized Data Tables", "7 standard output tables — same schema regardless of API source")

    # Table summary cards
    table_defs = [
        ("tbl_crude_prices",       "tbl_crude_prices",        "🛢️ Crude Prices",      ["date_time","benchmark","price","currency","source"]),
        ("tbl_fx_rates",           "tbl_fx_rates",            "💱 FX Rates",           ["date_time","pair","rate","source"]),
        ("tbl_trade_imports",      "tbl_trade_imports",       "🚢 Trade Imports",      ["date","country","product","hs_code","quantity","unit","value","currency","source"]),
        ("tbl_ports_volume",       "tbl_ports_volume",        "⚓ Ports Volume",       ["date","port_name","commodity","quantity","unit","source"]),
        ("tbl_refinery_production","tbl_refinery_production", "🏭 Refinery Prod.",    ["date","refinery_or_region","product","quantity","unit","source"]),
        ("tbl_weather",            "tbl_weather",             "🌤️ Weather",           ["date_time","location","temp","rain_mm","humidity","source"]),
        ("tbl_news_feed",          "tbl_news_feed",           "📰 News Feed",          ["date_time","headline","publisher","url","sentiment_score","source"]),
    ]

    # Quick summary row
    sc = st.columns(7)
    for idx, (key, _, label, _) in enumerate(table_defs):
        count = tbl_summary.get(key, 0)
        color = "#16a34a" if count > 0 else "#dc2626"
        sc[idx].markdown(
            f'<div style="text-align:center;padding:8px;border:1px solid #e2e8f0;border-radius:8px;">'
            f'<div style="font-size:0.6rem;color:#64748b;">{label}</div>'
            f'<div style="font-size:1.2rem;font-weight:800;color:{color};">{count}</div>'
            f'<div style="font-size:0.55rem;color:#94a3b8;">rows</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Refresh button
    rc1, rc2 = st.columns([3, 1])
    with rc1:
        st.markdown("**Select table to view:**")
    with rc2:
        if st.button("🔄 Refresh All Tables Now", use_container_width=True):
            with st.spinner("Fetching data from all connectors…"):
                summary = run_all_connectors(force=True)
            ok_c = summary.get("ok", 0)
            tot  = summary.get("total", 0)
            st.success(f"Refresh complete: {ok_c}/{tot} connectors OK")
            st.rerun()

    # Table viewer
    table_choice = st.selectbox(
        "Table",
        [f"{label} ({key})" for key, _, label, _ in table_defs],
        key="tbl_choice",
    )
    chosen_idx = [f"{label} ({key})" for key, _, label, _ in table_defs].index(table_choice)
    chosen_key, chosen_file, chosen_label, schema_cols = table_defs[chosen_idx]

    # Show schema
    with st.expander(f"📐 Schema: {chosen_label}"):
        schema_df = pd.DataFrame({
            "Column": schema_cols,
            "Type":   ["str" if "date" in c.lower() or c in ("benchmark","pair","country","product","hs_code","unit","source","currency","location","headline","publisher","url","refinery_or_region","port_name","commodity") else "float" if c in ("price","rate","quantity","value","temp","rain_mm","sentiment_score","humidity") else "str" for c in schema_cols],
        })
        st.dataframe(schema_df, use_container_width=True, hide_index=True)

    # Load data
    loader_map = {
        "tbl_crude_prices":        NormalizedTables.crude_prices,
        "tbl_fx_rates":            NormalizedTables.fx_rates,
        "tbl_trade_imports":       NormalizedTables.trade_imports,
        "tbl_ports_volume":        NormalizedTables.ports_volume,
        "tbl_refinery_production": NormalizedTables.refinery_production,
        "tbl_weather":             NormalizedTables.weather,
        "tbl_news_feed":           NormalizedTables.news_feed,
    }
    loader = loader_map.get(chosen_key)
    records = loader(n=200) if loader else []

    if not records:
        st.markdown("""
<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;
            padding:16px;text-align:center;color:#92400e;">
  <b>📭 No data yet</b><br/>
  Click <b>Refresh All Tables Now</b> above to populate this table from live APIs.
</div>""", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(records)
        # Ensure all schema columns are present
        for col in schema_cols:
            if col not in df.columns:
                df[col] = None

        n_rows = st.slider("Show last N rows", 5, min(200, len(df)), min(50, len(df)), key="tbl_rows")
        st.dataframe(
            df[schema_cols].tail(n_rows).iloc[::-1].reset_index(drop=True),
            use_container_width=True, hide_index=True,
        )
        st.caption(f"{len(df)} total records in {chosen_key} · Newest first · Last refreshed: {tbl_summary.get('last_updated', '—')}")

    # Cross-table relationships doc
    with st.expander("🔗 Table-to-API Mapping"):
        st.markdown("""
| Table | Primary API | Fallback API | Notes |
|-------|------------|-------------|-------|
| `tbl_crude_prices` | EIA (key required) | yfinance BZ=F/CL=F | yfinance always works |
| `tbl_fx_rates` | Frankfurter (no key) | fawazahmed0 CDN | Both work without key |
| `tbl_trade_imports` | UN Comtrade preview | Static cache | Preview endpoint = no key |
| `tbl_ports_volume` | BDI yfinance estimate | Static port estimates | No free real-time port API |
| `tbl_refinery_production` | EIA + PPAC reference | Static PPAC data | PPAC data always populated |
| `tbl_weather` | OpenWeather (key req) | Open-Meteo (no key) | Open-Meteo always works |
| `tbl_news_feed` | NewsAPI (key req) | Google News RSS | RSS always works |
""")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB E — AUTO-UPDATE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _render_scheduler_panel() -> None:
    _section_header("⏱️", "Auto-Update Engine", "Background scheduler status + connector activity log")

    # Scheduler status (read from hub_activity_log.json)
    log = NormalizedTables.hub_log(n=500)
    sched_entries = [r for r in log if r.get("connector_id") == "hub_scheduler"]

    sl1, sl2, sl3, sl4 = st.columns(4)
    total_runs  = len([r for r in log if r.get("connector_id") == "hub_orchestrator"])
    ok_runs     = len([r for r in log if r.get("connector_id") == "hub_orchestrator" and r.get("status") == "OK"])
    last_run    = next((r.get("timestamp_ist", "Never") for r in log if r.get("connector_id") == "hub_orchestrator"), "Never")
    total_recs  = sum(r.get("records_written", 0) for r in log)

    sl1.metric("Auto-Refresh Runs",   total_runs)
    sl2.metric("Successful Runs",     ok_runs)
    sl3.metric("Records Written",     f"{total_recs:,}")
    sl4.metric("Last Full Refresh",   last_run[-8:] if len(last_run) > 8 else last_run)

    st.markdown("---")

    # Scheduler info
    st.markdown("""
<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:12px 16px;margin-bottom:12px;">
  <b style="color:#16a34a;">⏱️ Auto-Update Schedule</b>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:8px;font-size:0.8rem;color:#166534;">
    <div>🛢️ Crude prices — every <b>1 hour</b></div>
    <div>💱 FX rates — every <b>1 hour</b></div>
    <div>🌤️ Weather — every <b>1 hour</b></div>
    <div>📰 News — every <b>1 hour</b></div>
    <div>🚢 Trade (Comtrade) — every <b>24 hours</b></div>
    <div>⚓ Ports + 🏭 Refinery — every <b>24 hours</b></div>
  </div>
</div>""", unsafe_allow_html=True)

    # Manual trigger
    if st.button("▶ Force Refresh All Tables Now", type="primary", use_container_width=True):
        with st.spinner("Refreshing all connectors — please wait…"):
            summary = run_all_connectors(force=True)
        ok_c = summary.get("ok", 0)
        tot  = summary.get("total", 0)
        if ok_c == tot:
            st.success(f"✅ All {tot} connectors refreshed successfully")
        else:
            st.warning(f"⚠️ {ok_c}/{tot} connectors OK — {tot - ok_c} failed (see log below)")
        st.rerun()

    st.markdown("---")

    # Activity log
    _section_header("📋", "Connector Activity Log", f"Last {len(log)} events (newest first)")

    if not log:
        st.info("No activity yet. Click 'Force Refresh All Tables Now' to populate.")
        return

    # Filter
    lf1, lf2 = st.columns(2)
    with lf1:
        conn_filter = st.selectbox("Filter by connector",
                                   ["All"] + sorted(set(r.get("connector_id", "") for r in log)),
                                   key="log_conn_f")
    with lf2:
        status_filter = st.selectbox("Filter by status",
                                     ["All", "OK", "FAIL", "Fallback", "INFO"],
                                     key="log_status_f")

    filtered_log = log
    if conn_filter != "All":
        filtered_log = [r for r in filtered_log if r.get("connector_id") == conn_filter]
    if status_filter != "All":
        filtered_log = [r for r in filtered_log if r.get("status") == status_filter]

    rows = []
    for r in filtered_log[:200]:
        s = r.get("status", "?")
        icon = "✅" if s == "OK" else ("⚠️" if s == "Fallback" else ("❌" if s == "FAIL" else "ℹ️"))
        rows.append({
            "Timestamp (IST)": r.get("timestamp_ist", ""),
            "Connector":       r.get("connector_id", ""),
            "Status":          f"{icon} {s}",
            "Records":         r.get("records_written", 0),
            "Message":         r.get("message", "")[:100],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Message": st.column_config.TextColumn(width="large"),
                 })

    # Connector health summary donut-style
    st.markdown("---")
    _section_header("📊", "Connector Summary (Current Snapshot)")
    cat = HubCatalog.load()
    for cid, entry in cat.items():
        status = entry.get("status", "Unknown")
        color  = _STATUS_COLOR.get(status, "#64748b")
        bg     = _STATUS_BG.get(status, "#f8fafc")
        icon_c = _CAT_ICON.get(entry.get("category", ""), "⚙️")
        last_ok   = entry.get("last_success_time") or "Never"
        last_err  = entry.get("last_error_message", "")[:80]

        st.markdown(f"""
<div style="background:{bg};border:1px solid {color}33;border-left:4px solid {color};
            border-radius:6px;padding:8px 12px;margin-bottom:5px;
            display:flex;align-items:center;gap:12px;">
  <span style="font-size:1.1rem;">{icon_c}</span>
  <div style="flex:1;">
    <div style="font-weight:700;font-size:0.8rem;color:#1e293b;">{cid}</div>
    <div style="font-size:0.67rem;color:#64748b;">{entry.get('api_name','')[:50]}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:0.7rem;font-weight:700;color:{color};">{status}</div>
    <div style="font-size:0.6rem;color:#94a3b8;">Last OK: {last_ok[-8:] if last_ok != 'Never' else 'Never'}</div>
  </div>
  {"<div style='font-size:0.65rem;color:#dc2626;max-width:200px;text-align:right;'>" + last_err[:60] + "</div>" if last_err else ""}
</div>""", unsafe_allow_html=True)
