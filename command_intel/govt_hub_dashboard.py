"""
PPS Anantam Agentic AI Eco System
Government Data Hub Dashboard v1.0
====================================
4-tab Streamlit UI for government data integration management.
Tab A: Gov API Catalog    — editable registry for 5 govt connectors
Tab B: Highway Data       — bar chart + table from tbl_highway_km
Tab C: Country Imports    — HS 271320 breakdown by origin country
Tab D: Excel Template     — downloadable Power Query M code templates
"""

import datetime
import streamlit as st

try:
    from api_hub_engine import HubCatalog, NormalizedTables, _load, BASE
    from govt_connectors import run_govt_connectors, init_govt_tables
except ImportError:
    HubCatalog = NormalizedTables = None
    def run_govt_connectors(**kw): return {"ok": 0, "total": 0, "results": {}}
    def init_govt_tables(): pass
    BASE = None


# ─── M Code templates for Excel Power Query ──────────────────────────────────

M_FN_FETCH = '''// fnFetch — reads one row from tbl_api_hub and fetches JSON/CSV
// Usage: = fnFetch(tbl_api_hub{[API_Name="EIA Crude"]}
let
  fnFetch = (apiRow as record) as table =>
  let
    apiName  = apiRow[API_Name],
    baseUrl  = apiRow[Base_URL],
    endpoint = apiRow[Endpoint],
    keyVal   = apiRow[Key_Value],
    params   = apiRow[Params_Template],
    authType = apiRow[Auth_Type],

    fullUrl  = baseUrl & endpoint & params,

    headers  = if authType = "API Key" and keyVal <> ""
               then [ Authorization = "Bearer " & keyVal ]
               else [],

    raw = try Json.Document(Web.Contents(fullUrl, [Headers=headers]))
          otherwise null,

    result = if raw = null then
               Table.FromRecords({[
                 api_name = apiName, status = "FAIL",
                 error    = "Fetch failed", rows = 0
               ]})
             else
               Table.FromList(
                 if raw is list then raw
                 else if raw is record then {raw}
                 else {},
                 Splitter.SplitByNothing(), null, null, ExtraValues.Ignore
               )
  in result
in fnFetch'''


M_MASTER_RUNNER = '''// qMasterRunner — iterates all Live APIs in tbl_api_hub and fetches each
let
  Source     = Excel.CurrentWorkbook(){[Name="tbl_api_hub"]}[Content],
  LiveAPIs   = Table.SelectRows(Source, each [Status] = "Live"),
  RunResults = Table.AddColumn(LiveAPIs, "FetchResult",
                 each fnFetch(_), type table),
  Expanded   = Table.ExpandTableColumn(RunResults, "FetchResult",
                 Table.ColumnNames(RunResults{0}[FetchResult]))
in Expanded'''


M_RUN_LOG = '''// qApiRunLog — captures run metadata for each API call
let
  Source = Excel.CurrentWorkbook(){[Name="tbl_api_hub"]}[Content],
  Live   = Table.SelectRows(Source, each [Status] = "Live"),
  WithTs = Table.AddColumn(Live, "run_time",
             each DateTime.LocalNow(), type datetime),
  WithStatus = Table.AddColumn(WithTs, "fetch_status",
             each try (if fnFetch(_) <> null then "OK" else "FAIL")
                  otherwise "ERROR"),
  Output = Table.SelectColumns(WithStatus,
             {"run_time","API_Name","fetch_status","Refresh_Frequency"})
in Output'''


M_PAGINATION = '''// fnPaginate — generic pagination handler for offset-based APIs
// Usage: = fnPaginate("https://api.example.com/data", "api_key_here", "page", 100)
let
  fnPaginate = (baseUrl as text, apiKey as text,
                pageParam as text, pageSize as number) as table =>
  let
    GetPage = (pageNum as number) =>
      let
        url  = baseUrl & "?" & pageParam & "=" & Text.From(pageNum)
                       & "&limit=" & Text.From(pageSize)
                       & "&api-key=" & apiKey,
        data = try Json.Document(Web.Contents(url)) otherwise null,
        rows = if data = null then {}
               else if data is list then data
               else if Record.HasFields(data, "records") then data[records]
               else if Record.HasFields(data, "data")    then data[data]
               else {}
      in rows,

    // Fetch pages until empty
    AllPages = List.Generate(
      ()         => [page=1, rows=GetPage(1)],
      each List.Count([rows]) > 0,
      each [page=[page]+1, rows=GetPage([page]+1)],
      each [rows]
    ),
    Combined = List.Combine(AllPages),
    Result   = Table.FromList(Combined,
                 Splitter.SplitByNothing(), null, null, ExtraValues.Ignore)
  in Result
in fnPaginate'''


# ─────────────────────────────────────────────────────────────────────────────
# GOVT CONNECTOR IDs
# ─────────────────────────────────────────────────────────────────────────────

GOVT_CONNECTOR_IDS = [
    "comtrade_hs271320",
    "rbi_fx_historical",
    "ppac_proxy",
    "data_gov_in_highways",
    "fred_macro",
]


# ─────────────────────────────────────────────────────────────────────────────
# KPI BAR
# ─────────────────────────────────────────────────────────────────────────────

def _kpi(label: str, value: str, color: str = "#2d6a4f") -> str:
    return f"""
<div style="background:#fff;border:1px solid #e8dcc8;border-left:4px solid {color};
            border-radius:8px;padding:10px 14px;text-align:center;">
  <div style="font-size:0.62rem;font-weight:700;color:#64748b;
              text-transform:uppercase;letter-spacing:0.07em;margin-bottom:3px;">{label}</div>
  <div style="font-size:1.05rem;font-weight:800;color:#1e3a5f;">{value}</div>
</div>"""


def _render_kpi_bar() -> None:
    if HubCatalog is None:
        return
    cat = HubCatalog.load()
    govt_entries = {k: v for k, v in cat.items() if k in GOVT_CONNECTOR_IDS}
    live     = sum(1 for v in govt_entries.values() if v.get("status") == "Live")
    disabled = sum(1 for v in govt_entries.values() if v.get("status") == "Disabled")
    failing  = sum(1 for v in govt_entries.values() if v.get("status") == "Failing")

    hw_rows  = len(_load(BASE / "tbl_highway_km.json", [])) if BASE else 0
    imp_rows = len(_load(BASE / "tbl_imports_countrywise.json", [])) if BASE else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(_kpi("Govt APIs Live",     f"✅ {live} / {len(GOVT_CONNECTOR_IDS)}", "#2d6a4f"), unsafe_allow_html=True)
    k2.markdown(_kpi("Disabled (key req)", f"⚪ {disabled}",  "#94a3b8"), unsafe_allow_html=True)
    k3.markdown(_kpi("Failing",            f"❌ {failing}",   "#f43f5e"), unsafe_allow_html=True)
    k4.markdown(_kpi("Highway Rows",       str(hw_rows),     "#1e3a5f"), unsafe_allow_html=True)
    k5.markdown(_kpi("Import Rows",        str(imp_rows),    "#c9a84c"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB A — GOV API CATALOG
# ─────────────────────────────────────────────────────────────────────────────

def _render_gov_catalog() -> None:
    st.markdown("#### 🏛️ Government API Catalog — Phase 1 & 2")
    st.caption(
        "Phase 1 (no key): comtrade_hs271320, rbi_fx_historical, ppac_proxy | "
        "Phase 2 (free key): data_gov_in_highways, fred_macro"
    )

    if HubCatalog is None:
        st.error("HubCatalog not available.")
        return

    cat = HubCatalog.load()
    govt_cat = {k: v for k, v in cat.items() if k in GOVT_CONNECTOR_IDS}

    # Build display rows
    rows = []
    for cid, entry in govt_cat.items():
        rows.append({
            "connector_id":     cid,
            "API Name":         entry.get("api_name", ""),
            "Category":         entry.get("category", ""),
            "Auth Type":        entry.get("auth_type", "None"),
            "API Key":          entry.get("key_value", ""),
            "Status":           entry.get("status", "Disabled"),
            "Refresh Freq":     entry.get("refresh_frequency", "1d"),
            "Output Table":     ", ".join(entry.get("data_output_tables", [])),
            "Last Success":     entry.get("last_success_time") or "—",
            "Last Error":       entry.get("last_error_message", "")[:60],
            "Notes":            entry.get("notes", ""),
        })

    try:
        import pandas as pd
        df = pd.DataFrame(rows)
        edited = st.data_editor(
            df,
            column_config={
                "connector_id": st.column_config.TextColumn("ID", disabled=True, width="small"),
                "API Name":     st.column_config.TextColumn("API Name", disabled=True),
                "Category":     st.column_config.TextColumn("Category", disabled=True, width="small"),
                "Auth Type":    st.column_config.TextColumn("Auth", disabled=True, width="small"),
                "API Key":      st.column_config.TextColumn("Key (paste here)", width="medium"),
                "Status":       st.column_config.SelectboxColumn(
                                    "Status", options=["Live","Disabled","Failing"], width="small"),
                "Refresh Freq": st.column_config.TextColumn("Refresh", width="small"),
                "Output Table": st.column_config.TextColumn("Output Table", disabled=True),
                "Last Success": st.column_config.TextColumn("Last OK", disabled=True, width="small"),
                "Last Error":   st.column_config.TextColumn("Last Error", disabled=True),
                "Notes":        st.column_config.TextColumn("Notes"),
            },
            use_container_width=True,
            hide_index=True,
            key="govt_catalog_editor",
        )

        if st.button("💾 Save Govt API Catalog", type="primary"):
            for _, row in edited.iterrows():
                cid = row["connector_id"]
                HubCatalog.update_field(cid, "key_value", str(row["API Key"]).strip())
                HubCatalog.update_field(cid, "status",    str(row["Status"]))
                HubCatalog.update_field(cid, "notes",     str(row["Notes"]))
            st.success("✅ Catalog saved.")
            st.rerun()

    except ImportError:
        st.warning("pandas not installed — install with: pip install pandas")

    # Key registration guide
    with st.expander("📋 How to get free API keys"):
        st.markdown("""
| Connector | Register at | Time | Notes |
|---|---|---|---|
| `data_gov_in_highways` | [data.gov.in/user/register](https://data.gov.in/user/register) | 5 min | Free, instant |
| `fred_macro` | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) | 2 min | Free, instant |
| `comtrade_hs271320` | No key needed | — | Public preview |
| `rbi_fx_historical` | No key needed | — | ECB proxy |
| `ppac_proxy` | No key needed | — | Static reference |
        """)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh All Govt Connectors", use_container_width=True):
            with st.spinner("Running govt connectors…"):
                result = run_govt_connectors(force=True)
            ok    = result.get("ok", 0)
            total = result.get("total", 0)
            if ok == total:
                st.success(f"✅ All {total} connectors OK")
            else:
                st.warning(f"⚠️ {ok}/{total} OK — check disabled connectors above")
    with c2:
        if st.button("🧪 Phase 1 Quick Test (no-key only)", use_container_width=True):
            with st.spinner("Testing no-key connectors…"):
                from govt_connectors import (
                    connect_comtrade_hs271320,
                    connect_rbi_fx_historical,
                    connect_ppac_proxy,
                )
                r1 = connect_comtrade_hs271320()
                r2 = connect_rbi_fx_historical()
                r3 = connect_ppac_proxy()
            for name, res in [("Comtrade HS 271320", r1),
                               ("RBI FX Historical",  r2),
                               ("PPAC Proxy",         r3)]:
                icon = "✅" if res.get("ok") else "⚠️"
                st.write(f"{icon} **{name}** — {res.get('records', 0)} records | {res.get('source', '')}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB B — HIGHWAY DATA
# ─────────────────────────────────────────────────────────────────────────────

def _render_highway_data() -> None:
    st.markdown("#### 🛣️ Highway Construction Progress — NHAI / MoRTH")

    rows = _load(BASE / "tbl_highway_km.json", []) if BASE else []

    if not rows:
        st.info("No highway data yet. Enable `data_gov_in_highways` connector and enter key in Tab A.")
        st.caption(
            "Phase 1 uses built-in NHAI Annual Report 2023-24 reference data when connector is disabled. "
            "Click **Refresh** in Tab A to populate."
        )
        return

    # KPI pills
    all_india = [r for r in rows if r.get("state", "").startswith("All India")]
    latest    = all_india[-1] if all_india else rows[-1]
    k1, k2, k3 = st.columns(3)
    k1.metric("KM Completed (latest)", f"{latest.get('km_completed', 0):,.0f} km",
              delta=None)
    k2.metric("Target", f"{latest.get('km_target', 0):,.0f} km")
    k3.metric("Achievement %", f"{latest.get('pct_achievement', 0):.1f}%")

    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        df = df[df["state"].str.startswith("All India")].copy() if "state" in df.columns else df
        df = df.sort_values("period_label")

        if not df.empty:
            st.markdown("**KM Completed by Month (All India)**")
            try:
                import altair as alt
                chart = alt.Chart(df).mark_bar(color="#2d6a4f").encode(
                    x=alt.X("period_label:N", title="Period"),
                    y=alt.Y("km_completed:Q", title="KM Completed"),
                    tooltip=["period_label", "agency", "km_completed", "km_target", "pct_achievement"],
                ).properties(height=280)
                target_line = alt.Chart(df).mark_line(
                    color="#c9a84c", strokeDash=[4, 4], strokeWidth=2
                ).encode(
                    x="period_label:N",
                    y=alt.Y("km_target:Q", title="KM Target"),
                )
                st.altair_chart(chart + target_line, use_container_width=True)
            except ImportError:
                st.line_chart(df.set_index("period_label")["km_completed"])

        # State breakdown
        state_df = pd.DataFrame(rows)
        state_df = state_df[~state_df["state"].str.startswith("All India")]
        if not state_df.empty:
            with st.expander(f"📊 State-wise Breakdown ({len(state_df)} records)"):
                st.dataframe(state_df[[
                    "period_label", "state", "agency", "km_completed",
                    "km_target", "pct_achievement", "source", "confidence"
                ]], use_container_width=True, hide_index=True)

        # Full table
        with st.expander(f"📋 Full Highway Table ({len(rows)} rows)"):
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    except ImportError:
        st.warning("pandas not installed.")
        for r in rows[-10:]:
            st.write(f"Period: {r.get('period_label')} | KM: {r.get('km_completed')} | Source: {r.get('source')}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB C — COUNTRY-WISE IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

def _render_countrywise() -> None:
    st.markdown("#### 🌍 HS 271320 Imports into India — By Origin Country")
    st.caption("Source: UN Comtrade public preview API (no key required)")

    rows = _load(BASE / "tbl_imports_countrywise.json", []) if BASE else []

    if not rows:
        st.info("No import data yet. Click 'Refresh' in Tab A to fetch from UN Comtrade.")
        return

    try:
        import pandas as pd

        df = pd.DataFrame(rows)

        # Latest period
        latest_period = df["period_label"].max() if "period_label" in df.columns else "—"
        st.caption(f"Showing data for period: **{latest_period}**")
        df_period = df[df["period_label"] == latest_period] if "period_label" in df.columns else df

        # KPIs
        total_mt  = df_period["qty_kg"].sum() / 1e9 if "qty_kg" in df_period.columns else 0
        total_usd = df_period["value_usd"].sum() / 1e6 if "value_usd" in df_period.columns else 0
        n_ctry    = df_period["origin_country"].nunique() if "origin_country" in df_period.columns else 0
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Imports", f"{total_mt:,.2f} MMT")
        k2.metric("Total Value", f"${total_usd:,.1f} M")
        k3.metric("Origin Countries", str(n_ctry))

        # Pie / bar chart
        if not df_period.empty and "origin_country" in df_period.columns:
            chart_df = df_period.groupby("origin_country")["qty_kg"].sum().reset_index()
            chart_df["qty_mt"]  = (chart_df["qty_kg"] / 1e6).round(1)
            chart_df = chart_df.sort_values("qty_mt", ascending=False)

            st.markdown("**Import Volume by Origin Country (MT)**")
            try:
                import altair as alt
                bar = alt.Chart(chart_df).mark_bar(color="#1e3a5f").encode(
                    x=alt.X("qty_mt:Q", title="Volume (MT)"),
                    y=alt.Y("origin_country:N", sort="-x", title="Country"),
                    tooltip=["origin_country", "qty_mt"],
                ).properties(height=max(200, len(chart_df) * 26))
                st.altair_chart(bar, use_container_width=True)
            except ImportError:
                st.bar_chart(chart_df.set_index("origin_country")["qty_mt"])

        # Full table
        with st.expander(f"📋 Full Countrywise Table ({len(df)} rows)"):
            st.dataframe(df[[
                "period_label", "origin_country", "hs_code",
                "qty_kg", "value_usd", "source"
            ]], use_container_width=True, hide_index=True)

    except ImportError:
        for r in rows[-20:]:
            st.write(f"Period: {r.get('period_label')} | Country: {r.get('origin_country')} | Qty: {r.get('qty_kg'):,.0f} kg")


# ─────────────────────────────────────────────────────────────────────────────
# TAB D — EXCEL POWER QUERY TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

def _render_excel_template() -> None:
    st.markdown("#### 📊 Excel Power Query M Code Templates")
    st.caption(
        "Ready-to-paste M code for Excel. API keys read from sheet 'API HUB (Connections & Keys)' "
        "— never hardcoded. Follow setup steps below."
    )

    with st.expander("📋 Excel Setup Steps", expanded=True):
        st.markdown("""
**Step 1** — Create sheet named: `API HUB (Connections & Keys)`

**Step 2** — Insert Excel Table named `tbl_api_hub` with columns:
`API_Name | Base_URL | Endpoint | Auth_Type | Key_Value | Params_Template | Refresh_Frequency | Cache_TTL | Status | Output_Table`

**Step 3** — Open **Data → Get Data → Launch Power Query Editor**

**Step 4** — Create a **Blank Query**, paste each template below

**Step 5** — Set each query to **Load To** → your target worksheet

**Step 6** — Set **Data → Queries & Connections → Properties → Refresh Every**: 60 minutes
        """)

    templates = [
        ("fnFetch — API Row Fetcher",    M_FN_FETCH),
        ("qMasterRunner — All APIs",     M_MASTER_RUNNER),
        ("qApiRunLog — Run Log",         M_RUN_LOG),
        ("fnPaginate — Pagination",      M_PAGINATION),
    ]

    for title, code in templates:
        st.markdown(f"**{title}**")
        st.code(code, language="plaintext")
        # Download button
        st.download_button(
            label=f"⬇️ Download {title.split(' — ')[0]}.m",
            data=code,
            file_name=f"{title.split(' — ')[0].replace(' ','_')}.m",
            mime="text/plain",
            key=f"dl_{title[:12]}",
        )
        st.markdown("---")

    st.info(
        "💡 **Tip:** Set `Status = 'Live'` for APIs you want active; "
        "`'Disabled'` for inactive. Only 'Live' rows are fetched by qMasterRunner."
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Entry point called from dashboard.py page routing."""
    try:
        init_govt_tables()
    except Exception:
        pass

    _render_kpi_bar()
    st.markdown("<div style='height:var(--s8,8px)'></div>", unsafe_allow_html=True)

    tab_a, tab_b, tab_c, tab_d = st.tabs([
        "🏛️ Gov Catalog",
        "🛣️ Highway Data",
        "🌍 Country Imports",
        "📊 Excel Template",
    ])

    with tab_a:
        _render_gov_catalog()
    with tab_b:
        _render_highway_data()
    with tab_c:
        _render_countrywise()
    with tab_d:
        _render_excel_template()
