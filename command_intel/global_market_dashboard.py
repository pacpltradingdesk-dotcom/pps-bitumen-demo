"""
PPS Anantam -- Global Market Dashboard v1.0
=============================================
3-tab UI: Crude Markets, Bitumen Prices, FX Monitor.
Real-time crude oil, bitumen pricing, and currency tracking
with interactive date-range selectors and Plotly charts.

Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("global_market_dashboard")

# ── Vastu Design System ─────────────────────────────────────────────────────
_NAVY  = "#1e3a5f"
_GREEN = "#2d6a4f"
_GOLD  = "#c9a84c"
_FIRE  = "#b85c38"
_IVORY = "#faf7f2"

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent.parent

# ── Safe imports ─────────────────────────────────────────────────────────────
try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

try:
    from interactive_chart_helpers import (
        add_date_range_selector,
        apply_interactive_defaults,
        filter_df_by_date_range,
        get_chart_config,
    )
    _HELPERS = True
except ImportError:
    _HELPERS = False

try:
    from api_hub_engine import HubCache
    _HUB = True
except ImportError:
    _HUB = False


# ── Data loaders ─────────────────────────────────────────────────────────────

def _load_json(filename: str) -> list:
    """Load a JSON table file from the project root."""
    path = BASE / filename
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as exc:
        LOG.warning("Failed to load %s: %s", filename, exc)
    return []


def _ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


# ── Tab A: Crude Markets ────────────────────────────────────────────────────

def _render_crude_markets(st) -> None:
    """Brent/WTI multi-line chart with date range selector."""
    st.subheader("Crude Oil Price Tracker")

    raw = _load_json("tbl_crude_prices.json")
    if not raw:
        st.info("No crude price data available. Run the API Hub sync to fetch data.")
        return

    if not _PANDAS:
        st.warning("pandas is required for charts. Install it with `pip install pandas`.")
        return

    df = pd.DataFrame(raw)

    # Normalise date column
    date_col = None
    for col in ("date", "ds", "Date", "timestamp", "fetch_date_ist"):
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        st.warning("No date column found in crude price data.")
        return

    df["date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["date"]).sort_values("date")

    # Identify price columns
    brent_col = next((c for c in df.columns if "brent" in c.lower()), None)
    wti_col = next((c for c in df.columns if "wti" in c.lower()), None)

    if not brent_col and not wti_col:
        st.warning("No Brent or WTI columns found in crude price data.")
        return

    # Date range selector
    if _HELPERS:
        start_date, end_date = add_date_range_selector(st, key="crude_dr", default_days=90)
        df = filter_df_by_date_range(df, start_date, end_date, date_col="date")

    if df.empty:
        st.info("No data in the selected date range.")
        return

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)
    if brent_col:
        latest_brent = df[brent_col].dropna().iloc[-1] if not df[brent_col].dropna().empty else None
        if latest_brent is not None:
            c1.metric("Brent (Latest)", f"${latest_brent:,.2f}")
            if len(df) >= 2:
                prev = df[brent_col].dropna().iloc[-2]
                c2.metric("Brent Change", f"${latest_brent - prev:+,.2f}")
    if wti_col:
        latest_wti = df[wti_col].dropna().iloc[-1] if not df[wti_col].dropna().empty else None
        if latest_wti is not None:
            c3.metric("WTI (Latest)", f"${latest_wti:,.2f}")
            if len(df) >= 2:
                prev = df[wti_col].dropna().iloc[-2]
                c4.metric("WTI Change", f"${latest_wti - prev:+,.2f}")

    # Plotly chart
    if _PLOTLY:
        fig = go.Figure()
        if brent_col:
            fig.add_trace(go.Scatter(
                x=df["date"], y=df[brent_col],
                name="Brent", mode="lines",
                line=dict(color=_NAVY, width=2),
            ))
        if wti_col:
            fig.add_trace(go.Scatter(
                x=df["date"], y=df[wti_col],
                name="WTI", mode="lines",
                line=dict(color=_FIRE, width=2),
            ))
        fig.update_layout(
            title="Crude Oil Prices (USD/bbl)",
            xaxis_title="Date", yaxis_title="USD / barrel",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=420,
        )
        if _HELPERS:
            fig = apply_interactive_defaults(fig)
        st.plotly_chart(fig, use_container_width=True,
                        config=get_chart_config() if _HELPERS else {})
    else:
        st.line_chart(df.set_index("date")[[c for c in [brent_col, wti_col] if c]])

    # Data table
    with st.expander("View Raw Data", expanded=False):
        display_cols = ["date"] + [c for c in [brent_col, wti_col] if c]
        st.dataframe(df[display_cols].tail(50), use_container_width=True, hide_index=True)

    st.caption(f"Last updated: {_ist_now()}")


# ── Tab B: Bitumen Prices ───────────────────────────────────────────────────

def _render_bitumen_prices(st) -> None:
    """OPEC basket from HubCache + PSU refinery prices summary."""
    st.subheader("Bitumen Pricing Intelligence")

    # OPEC basket
    opec_data = None
    if _HUB:
        try:
            opec_data = HubCache.get("opec_monthly")
        except Exception as exc:
            LOG.debug("OPEC cache miss: %s", exc)

    if opec_data:
        st.markdown("##### OPEC Basket Price")
        if isinstance(opec_data, dict):
            c1, c2, c3 = st.columns(3)
            c1.metric("OPEC Basket", f"${opec_data.get('price', 'N/A')}")
            c2.metric("Month", str(opec_data.get("month", "N/A")))
            c3.metric("Change", str(opec_data.get("change", "N/A")))
        elif isinstance(opec_data, list) and _PANDAS:
            df_opec = pd.DataFrame(opec_data)
            st.dataframe(df_opec.tail(12), use_container_width=True, hide_index=True)
    else:
        st.info("OPEC basket data not available. Ensure API Hub is synced.")

    st.markdown("---")

    # PSU refinery prices
    st.markdown("##### PSU Refinery Prices (India)")
    st.markdown(
        "Indian PSU refineries (IOCL, BPCL, HPCL) revise bitumen prices "
        "fortnightly (1st and 16th of each month)."
    )

    refinery_data = _load_json("tbl_refinery_production.json")
    if refinery_data and _PANDAS:
        df_ref = pd.DataFrame(refinery_data)
        price_cols = [c for c in df_ref.columns if "price" in c.lower() or "rate" in c.lower()]
        if price_cols:
            st.dataframe(df_ref.tail(20), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_ref.tail(20), use_container_width=True, hide_index=True)
    elif refinery_data:
        for row in refinery_data[-10:]:
            st.write(row)
    else:
        st.info("No refinery price data available. Run the API Hub sync.")

    st.caption(f"Last updated: {_ist_now()}")


# ── Tab C: FX Monitor ───────────────────────────────────────────────────────

def _render_fx_monitor(st) -> None:
    """USD/INR trend from tbl_fx_rates.json with impact calculator."""
    st.subheader("USD/INR Currency Monitor")

    raw = _load_json("tbl_fx_rates.json")
    if not raw:
        st.info("No FX rate data available. Run the API Hub sync to fetch data.")
        return

    if not _PANDAS:
        st.warning("pandas is required for FX charts.")
        return

    df = pd.DataFrame(raw)

    # Normalise date column
    date_col = None
    for col in ("date", "ds", "Date", "timestamp", "fetch_date_ist"):
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        st.warning("No date column found in FX data.")
        return

    df["date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["date"]).sort_values("date")

    # Identify rate column
    rate_col = None
    for col in df.columns:
        if "usd" in col.lower() and "inr" in col.lower():
            rate_col = col
            break
    if rate_col is None:
        rate_col = next((c for c in df.columns if "rate" in c.lower() or "close" in c.lower()), None)
    if rate_col is None:
        st.warning("No USD/INR rate column found.")
        return

    df[rate_col] = pd.to_numeric(df[rate_col], errors="coerce")
    df = df.dropna(subset=[rate_col])

    # Date range selector
    if _HELPERS:
        start_date, end_date = add_date_range_selector(st, key="fx_dr", default_days=90)
        df = filter_df_by_date_range(df, start_date, end_date, date_col="date")

    if df.empty:
        st.info("No FX data in the selected date range.")
        return

    # KPI row
    latest_rate = df[rate_col].iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("USD/INR (Latest)", f"{latest_rate:,.2f}")
    if len(df) >= 2:
        prev_rate = df[rate_col].iloc[-2]
        change = latest_rate - prev_rate
        c2.metric("Change", f"{change:+,.2f}",
                  delta_color="inverse")
    c3.metric("Data Points", f"{len(df)}")

    # Plotly chart
    if _PLOTLY:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["date"], y=df[rate_col],
            name="USD/INR", mode="lines",
            line=dict(color=_GOLD, width=2),
            fill="tozeroy",
            fillcolor="rgba(201,168,76,0.08)",
        ))
        fig.update_layout(
            title="USD/INR Exchange Rate",
            xaxis_title="Date", yaxis_title="INR per USD",
            template="plotly_white",
            height=380,
        )
        if _HELPERS:
            fig = apply_interactive_defaults(fig, inr_format=True)
        st.plotly_chart(fig, use_container_width=True,
                        config=get_chart_config() if _HELPERS else {})
    else:
        st.line_chart(df.set_index("date")[[rate_col]])

    # Impact calculator
    st.markdown("---")
    st.markdown("##### Import Cost Impact Calculator")
    calc_c1, calc_c2, calc_c3 = st.columns(3)
    with calc_c1:
        cargo_usd = st.number_input("Cargo Value (USD)", min_value=0, value=100000,
                                     step=5000, key="fx_cargo_usd")
    with calc_c2:
        base_rate = st.number_input("Base FX Rate (INR/USD)", min_value=50.0,
                                     value=float(round(latest_rate, 2)), step=0.25,
                                     key="fx_base_rate")
    with calc_c3:
        scenario_rate = st.number_input("Scenario FX Rate", min_value=50.0,
                                         value=float(round(latest_rate + 1.0, 2)),
                                         step=0.25, key="fx_scenario_rate")

    base_cost = cargo_usd * base_rate
    scenario_cost = cargo_usd * scenario_rate
    impact = scenario_cost - base_cost

    r1, r2, r3 = st.columns(3)
    r1.metric("Base Cost (INR)", f"{base_cost:,.0f}")
    r2.metric("Scenario Cost (INR)", f"{scenario_cost:,.0f}")
    r3.metric("Impact (INR)", f"{impact:+,.0f}",
              delta_color="inverse")

    st.caption(f"Last updated: {_ist_now()}")


# ── Main Render ──────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function -- called from dashboard.py routing."""
    import streamlit as st

    st.title("Global Market Dashboard")
    st.caption("Real-time crude oil, bitumen pricing, and currency intelligence")

    tabs = st.tabs([
        "Crude Markets",
        "Bitumen Prices",
        "FX Monitor",
    ])

    with tabs[0]:
        _render_crude_markets(st)

    with tabs[1]:
        _render_bitumen_prices(st)

    with tabs[2]:
        _render_fx_monitor(st)
