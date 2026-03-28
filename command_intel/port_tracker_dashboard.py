# command_intel/port_tracker_dashboard.py
# PPS Anantam Agentic AI Eco System — v3.2.3
# Port-wise Bitumen Import Tracker Dashboard (5-tab UI)

from __future__ import annotations

import datetime
from typing import Any, Dict, List

import streamlit as st

# ── safe imports ──────────────────────────────────────────────────────────────
try:
    import altair as alt
    _ALTAIR = True
except ImportError:
    _ALTAIR = False

try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    from port_tracker_engine import (
        allocate_imports_to_ports,
        get_port_summary,
        get_country_port_matrix,
        get_confidence_breakdown,
        get_top_port,
        get_avg_confidence,
        get_total_allocated_mt,
        load_allocation_rules,
        save_allocation_rules,
        reset_allocation_rules,
        init_port_tracker,
        PORTS_MASTER,
    )
    _ENGINE = True
except ImportError:
    _ENGINE = False
    PORTS_MASTER = []

try:
    from api_hub_engine import NormalizedTables, _ist_now
    _HUB = True
except ImportError:
    _HUB = False
    def _ist_now() -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# ── constants ─────────────────────────────────────────────────────────────────
_COAST_COLORS = {"West": "#1d6dd8", "East": "#d97706"}    # 4.6:1+ on white
_CONF_COLORS  = {"High (≥80)": "#16a34a", "Medium (60-79)": "#d97706", "Low (<60)": "#dc2626"}


# ─────────────────────────────────────────────────────────────────────────────
#  KPI BAR
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpi_bar() -> None:
    """Top KPI row: 4 metrics."""
    if not _ENGINE:
        st.warning("port_tracker_engine not available.")
        return

    total_mt   = get_total_allocated_mt()
    top_port   = get_top_port()
    avg_conf   = get_avg_confidence()
    last_upd   = _ist_now()

    # try to get last run timestamp from portwise table
    if _HUB:
        pw = NormalizedTables.imports_portwise(1)
        if pw:
            last_upd = pw[-1].get("fetch_date_ist", last_upd) if "fetch_date_ist" in pw[-1] else last_upd

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Allocated MT", f"{total_mt:,.1f}", help="Sum of all port-wise allocated import volume")
    c2.metric("Top Port",           top_port or "N/A",  help="Port with highest allocated volume")
    c3.metric("Avg Confidence",     f"{avg_conf:.0f}%", help="Average confidence score across all allocations")
    c4.metric("Last Update",        last_upd,           help="Timestamp of most recent allocation run")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB A — PORT RANKINGS
# ─────────────────────────────────────────────────────────────────────────────

def _render_port_rankings() -> None:
    """Sorted table + Altair bar chart of port volumes."""
    if not _ENGINE:
        st.warning("port_tracker_engine not available.")
        return

    summary = get_port_summary()
    if not summary:
        st.info("No port allocation data yet.  Click **▶ Run Allocation** to generate data.")
        if st.button("▶ Run Allocation", key="alloc_btn_rankings"):
            with st.spinner("Allocating imports to ports…"):
                result = allocate_imports_to_ports()
            st.success(f"Allocated {result.get('records_written', 0)} records across ports.")
            st.rerun()
        return

    if _PANDAS:
        df = pd.DataFrame(summary)

        # ── chart ──────────────────────────────────────────────────────────
        if _ALTAIR and not df.empty and "total_qty_mt" in df.columns:
            chart = (
                alt.Chart(df.head(10))
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(
                    x=alt.X("port_name:N", sort="-y", title="Port", axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y("total_qty_mt:Q", title="Allocated Volume (MT)", axis=alt.Axis(format=".0f")),
                    color=alt.Color("coast:N",
                        scale=alt.Scale(domain=["West","East"], range=["#1d6dd8","#d97706"]),
                        legend=alt.Legend(title="Coast")),
                    tooltip=[
                        alt.Tooltip("port_name:N",  title="Port"),
                        alt.Tooltip("coast:N",       title="Coast"),
                        alt.Tooltip("total_qty_mt:Q",title="Volume MT", format=".1f"),
                        alt.Tooltip("country_count:Q",title="Countries"),
                        alt.Tooltip("avg_confidence:Q",title="Avg Conf %", format=".0f"),
                    ],
                )
                .properties(height=320, title="Port-wise Allocated Import Volume (MT)")
            )
            st.altair_chart(chart, use_container_width=True)
        elif not _ALTAIR:
            st.bar_chart(df.set_index("port_name")["total_qty_mt"])

        # ── table ──────────────────────────────────────────────────────────
        st.markdown("##### Port Rankings")
        display_cols = [c for c in ["port_name","state","coast","total_qty_mt","country_count","avg_confidence","pct_share"] if c in df.columns]
        rename_map = {
            "port_name":"Port","state":"State","coast":"Coast",
            "total_qty_mt":"Volume MT","country_count":"Countries",
            "avg_confidence":"Avg Confidence %","pct_share":"Share %",
        }
        st.dataframe(df[display_cols].rename(columns=rename_map), use_container_width=True, hide_index=True)

        # ── coast split ────────────────────────────────────────────────────
        if "coast" in df.columns and "total_qty_mt" in df.columns:
            coast_df = df.groupby("coast")["total_qty_mt"].sum().reset_index()
            total    = coast_df["total_qty_mt"].sum()
            if total > 0:
                coast_df["pct"] = (coast_df["total_qty_mt"] / total * 100).round(1)
            st.markdown("**West vs East Coast Split**")
            c1, c2 = st.columns(2)
            for _, row in coast_df.iterrows():
                col = c1 if row["coast"] == "West" else c2
                col.metric(f"{row['coast']} Coast MT", f"{row['total_qty_mt']:,.1f}", f"{row.get('pct',0):.1f}%")
    else:
        # fallback: plain list
        for s in summary[:10]:
            st.write(f"**{s['port_name']}** — {s.get('total_qty_mt',0):,.1f} MT  (conf {s.get('avg_confidence',0):.0f}%)")

    # re-run button
    if st.button("↺ Re-run Allocation", key="alloc_rerun_rankings"):
        with st.spinner("Allocating…"):
            r = allocate_imports_to_ports()
        st.success(f"Done — {r.get('records_written',0)} records written.")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB B — COUNTRY → PORT FLOW
# ─────────────────────────────────────────────────────────────────────────────

def _render_country_port_flow() -> None:
    """Pivot matrix: rows = origin countries, cols = ports."""
    if not _ENGINE:
        st.warning("port_tracker_engine not available.")
        return

    matrix = get_country_port_matrix()
    if not matrix:
        st.info("No allocation data yet.  Run allocation from **Port Rankings** tab.")
        return

    if _PANDAS:
        # Build pivot DataFrame
        df = pd.DataFrame(matrix).T.fillna(0)
        df.index.name = "Origin Country"

        # Nicely ordered columns (top ports first)
        summary = get_port_summary()
        ordered_ports = [s["port_name"] for s in summary if s["port_name"] in df.columns]
        remaining     = [c for c in df.columns if c not in ordered_ports]
        df = df[ordered_ports + remaining]

        # Row total
        df["TOTAL MT"] = df.sum(axis=1)
        df = df.sort_values("TOTAL MT", ascending=False)

        st.markdown("##### Country → Port Flow Matrix (MT)")
        st.dataframe(df.style.format("{:.1f}").background_gradient(cmap="Blues", axis=None),
                     use_container_width=True)

        # ── stacked bar ──────────────────────────────────────────────────
        if _ALTAIR:
            # melt for altair
            plot_df = df.drop(columns=["TOTAL MT"]).reset_index()
            melted  = plot_df.melt(id_vars="Origin Country", var_name="Port", value_name="MT")
            melted  = melted[melted["MT"] > 0]

            if not melted.empty:
                chart = (
                    alt.Chart(melted)
                    .mark_bar()
                    .encode(
                        x=alt.X("Origin Country:N", sort="-y", title="Origin Country",
                                axis=alt.Axis(labelAngle=-30)),
                        y=alt.Y("MT:Q", title="Allocated MT", stack="normalize",
                                axis=alt.Axis(format="%")),
                        color=alt.Color("Port:N", legend=alt.Legend(title="Port")),
                        tooltip=[
                            alt.Tooltip("Origin Country:N"),
                            alt.Tooltip("Port:N"),
                            alt.Tooltip("MT:Q", format=".1f"),
                        ],
                    )
                    .properties(height=320, title="Country → Port Split (Normalised)")
                )
                st.altair_chart(chart, use_container_width=True)
    else:
        for country, ports in matrix.items():
            parts = ", ".join(f"{p}: {v:.0f}" for p, v in sorted(ports.items(), key=lambda x: -x[1]) if v > 0)
            st.write(f"**{country}** → {parts}")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB C — PORT TRENDS
# ─────────────────────────────────────────────────────────────────────────────

def _render_port_trends() -> None:
    """Line chart of selected port volume over time."""
    if not _HUB:
        st.warning("api_hub_engine not available.")
        return

    pw_data = NormalizedTables.imports_portwise(500) if _HUB else []
    if not pw_data:
        st.info("No portwise data yet.  Run allocation from **Port Rankings** tab.")
        return

    if not _PANDAS:
        st.warning("pandas not available — trend chart unavailable.")
        return

    df = pd.DataFrame(pw_data)
    if "port_name" not in df.columns or "period_label" not in df.columns:
        st.warning("Unexpected data schema in tbl_imports_portwise.")
        return

    # port selector
    all_ports = sorted(df["port_name"].dropna().unique().tolist())
    if not all_ports:
        st.info("No port names found in allocation data.")
        return

    selected_port = st.selectbox("Select Port", all_ports, key="trend_port_selector")
    port_df = df[df["port_name"] == selected_port].copy()

    if port_df.empty:
        st.info(f"No data for {selected_port}.")
        return

    # aggregate by period
    if "qty_allocated_kg" in port_df.columns:
        port_df["qty_mt"] = port_df["qty_allocated_kg"].fillna(0) / 1000
        agg = port_df.groupby("period_label")["qty_mt"].sum().reset_index()
        agg = agg.sort_values("period_label")

        if _ALTAIR:
            chart = (
                alt.Chart(agg)
                .mark_line(point=True, color="#2196F3")
                .encode(
                    x=alt.X("period_label:N", sort=None, title="Period",
                            axis=alt.Axis(labelAngle=-30)),
                    y=alt.Y("qty_mt:Q", title="Allocated Volume (MT)",
                            axis=alt.Axis(format=".0f")),
                    tooltip=[
                        alt.Tooltip("period_label:N", title="Period"),
                        alt.Tooltip("qty_mt:Q", title="MT", format=".1f"),
                    ],
                )
                .properties(height=320, title=f"{selected_port} — Monthly Allocated Volume")
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.line_chart(agg.set_index("period_label")["qty_mt"])

        # country breakdown for selected port
        st.markdown(f"##### Country Breakdown — {selected_port}")
        if "origin_country" in port_df.columns:
            ctry = port_df.groupby("origin_country")["qty_mt"].sum().reset_index()
            ctry = ctry.sort_values("qty_mt", ascending=False)
            ctry.columns = ["Origin Country", "Volume MT"]
            ctry["Volume MT"] = ctry["Volume MT"].round(1)
            st.dataframe(ctry, use_container_width=True, hide_index=True)
    else:
        st.warning("qty_allocated_kg column missing from portwise data.")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB D — DATA CONFIDENCE
# ─────────────────────────────────────────────────────────────────────────────

def _render_data_confidence() -> None:
    """Confidence score bar chart + direct vs proxy breakdown."""
    if not _ENGINE:
        st.warning("port_tracker_engine not available.")
        return

    breakdown = get_confidence_breakdown()
    if not breakdown or sum(breakdown.values()) == 0:
        st.info("No confidence data yet.  Run allocation first.")
        return

    # KPIs
    total = sum(breakdown.values())
    c1, c2, c3 = st.columns(3)
    c1.metric("High Confidence (≥80%)",   breakdown.get("High (≥80)", 0),
              help="Records where confidence score ≥ 80 — typically direct country allocation rules")
    c2.metric("Medium Confidence (60-79)", breakdown.get("Medium (60-79)", 0),
              help="Records using allocation rules with moderate certainty")
    c3.metric("Low Confidence (<60)",      breakdown.get("Low (<60)", 0),
              help="Records using default distribution fallback")

    # Chart
    if _ALTAIR and _PANDAS:
        chart_data = pd.DataFrame([
            {"Band": k, "Records": v, "Color": _CONF_COLORS.get(k, "#5a6474")}
            for k, v in breakdown.items()
        ])
        chart = (
            alt.Chart(chart_data)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("Band:N", sort=list(breakdown.keys()), title="Confidence Band"),
                y=alt.Y("Records:Q", title="No. of Allocation Records"),
                color=alt.Color("Color:N", scale=None),
                tooltip=["Band:N", "Records:Q"],
            )
            .properties(height=280, title="Confidence Score Distribution")
        )
        st.altair_chart(chart, use_container_width=True)

    # Method breakdown from raw portwise data
    if _HUB and _PANDAS:
        pw_data = NormalizedTables.imports_portwise(500)
        if pw_data:
            df = pd.DataFrame(pw_data)
            if "method" in df.columns:
                method_counts = df["method"].value_counts().reset_index()
                method_counts.columns = ["Method", "Records"]
                st.markdown("##### Allocation Method Breakdown")
                st.dataframe(method_counts, use_container_width=True, hide_index=True)

            if "confidence_score" in df.columns and not df.empty:
                st.markdown("##### Confidence Score Distribution Detail")
                try:
                    df["confidence_score"] = pd.to_numeric(df["confidence_score"], errors="coerce")
                    hist_data = df["confidence_score"].dropna()
                    if not hist_data.empty:
                        st.markdown(
                            f"**Min:** {hist_data.min():.0f}  |  "
                            f"**Max:** {hist_data.max():.0f}  |  "
                            f"**Avg:** {hist_data.mean():.1f}  |  "
                            f"**Records:** {len(hist_data)}"
                        )
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────────────────────
#  TAB E — PORT MAPPING HUB (editable allocation rules)
# ─────────────────────────────────────────────────────────────────────────────

def _render_port_mapping_hub() -> None:
    """Editable st.data_editor for tbl_port_allocation_rules + Save button."""
    if not _ENGINE:
        st.warning("port_tracker_engine not available.")
        return

    st.markdown(
        "Edit the country → port allocation percentages below.  "
        "Each country's rows must sum to **100%**.  "
        "Click **💾 Save Rules** when done."
    )

    rules = load_allocation_rules()
    if not rules:
        st.info("No allocation rules found.  Resetting to defaults…")
        reset_allocation_rules()
        rules = load_allocation_rules()

    if not _PANDAS:
        st.warning("pandas not available — editor unavailable.")
        st.json(rules[:20])
        return

    df_rules = pd.DataFrame(rules)
    expected_cols = ["origin_country","product","port_name","split_pct","confidence_score","method","notes"]
    for col in expected_cols:
        if col not in df_rules.columns:
            df_rules[col] = "" if col not in ("split_pct","confidence_score") else 0

    # port options for select
    port_names = [p["port_name"] for p in PORTS_MASTER] + ["Others"]

    edited = st.data_editor(
        df_rules[expected_cols],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "origin_country": st.column_config.TextColumn("Origin Country", width="medium"),
            "product":        st.column_config.TextColumn("Product", width="small"),
            "port_name":      st.column_config.SelectboxColumn("Port", options=port_names, width="medium"),
            "split_pct":      st.column_config.NumberColumn("Split %", min_value=0, max_value=100, step=1, format="%d%%"),
            "confidence_score": st.column_config.NumberColumn("Confidence", min_value=0, max_value=100, step=5),
            "method":         st.column_config.TextColumn("Method", width="small"),
            "notes":          st.column_config.TextColumn("Notes", width="large"),
        },
        key="port_rules_editor",
    )

    col_save, col_reset, col_validate, _ = st.columns([2, 2, 2, 4])

    with col_save:
        if st.button("💾 Save Rules", type="primary", key="save_port_rules"):
            try:
                save_allocation_rules(edited.to_dict("records"))
                st.success("Allocation rules saved successfully.")
            except Exception as exc:
                st.error(f"Save failed: {exc}")

    with col_reset:
        if st.button("↺ Reset to Defaults", key="reset_port_rules"):
            reset_allocation_rules()
            st.success("Rules reset to defaults.")
            st.rerun()

    with col_validate:
        if st.button("✔ Validate Totals", key="validate_port_rules"):
            issues: List[str] = []
            for country in edited["origin_country"].dropna().unique():
                mask = (edited["origin_country"] == country) & (edited["product"].str.lower().isin(["bitumen",""]))
                total = edited.loc[mask, "split_pct"].fillna(0).sum()
                if abs(total - 100) > 0.5:
                    issues.append(f"**{country}**: total = {total:.0f}% (expected 100%)")
            if issues:
                st.warning("Validation issues:\n" + "\n".join(issues))
            else:
                st.success("All countries sum to 100% ✔")

    # Info boxes
    with st.expander("ℹ Confidence Score Guide", expanded=False):
        st.markdown(
            """
| Score | Meaning |
|-------|---------|
| 90-100 | Direct data — actual bill-of-lading port of entry |
| 70-89  | Strong allocation rule — well-established trade lane |
| 60-69  | Moderate allocation rule — based on historical patterns |
| 45-59  | Default distribution — country not in rules, global average used |
"""
        )

    with st.expander("ℹ Allocation Rule Format", expanded=False):
        st.markdown(
            """
- Each row = one country + port combination.
- `split_pct` must total **100** per `origin_country + product` group.
- `product` = `Bitumen` (default), `VG30`, `VG10`, etc.
- Leave `product` blank to apply rule to all bitumen grades.
- `method` = `allocation_rule` (manual) | `direct_data` (from actual manifest).
"""
        )


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN ENTRY
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function — called from dashboard.py routing."""
    # ensure tables exist
    if _ENGINE:
        try:
            init_port_tracker()
        except Exception:
            pass

    # KPI bar
    _render_kpi_bar()
    st.markdown("---")

    # Tabs
    tabs = st.tabs([
        "⚓ Port Rankings",
        "🔀 Country→Port Flow",
        "📈 Port Trends",
        "🎯 Data Confidence",
        "🗺️ PORT MAPPING HUB",
    ])

    with tabs[0]:
        _render_port_rankings()

    with tabs[1]:
        _render_country_port_flow()

    with tabs[2]:
        _render_port_trends()

    with tabs[3]:
        _render_data_confidence()

    with tabs[4]:
        _render_port_mapping_hub()
