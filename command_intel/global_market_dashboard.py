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
import math
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

    # Normalise date column. `date_time` is the column the API hub actually
    # writes (e.g. "2026-06-16 15:15:09 IST") — it was missing from this list,
    # so the tracker showed "No data" even though the file was fresh.
    date_col = None
    for col in ("date", "date_time", "ds", "Date", "timestamp", "fetch_date_ist"):
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        st.warning("No date column found in crude price data.")
        return

    # Strip trailing timezone text ("... IST") so pandas can parse it.
    _date_raw = df[date_col].astype(str).str.replace(r"\s*IST$", "", regex=True)
    df["date"] = pd.to_datetime(_date_raw, errors="coerce", dayfirst=False)
    df = df.dropna(subset=["date"]).sort_values("date")

    # The hub stores crude prices in LONG format (one row per benchmark:
    # columns benchmark + price). Pivot to WIDE so we get Brent / WTI columns.
    bench_col = next((c for c in df.columns if c.lower() in ("benchmark", "symbol", "instrument")), None)
    price_col = next((c for c in df.columns if c.lower() in ("price", "value", "close")), None)
    if bench_col and price_col:
        df["_b"] = df[bench_col].astype(str).str.lower()
        wide = df.pivot_table(index="date", columns="_b", values=price_col, aggfunc="last")
        wide = wide.rename(columns={c: ("Brent" if "brent" in c else "WTI" if "wti" in c else c)
                                    for c in wide.columns}).reset_index()
        df = wide

    # Identify price columns
    brent_col = next((c for c in df.columns if "brent" in str(c).lower()), None)
    wti_col = next((c for c in df.columns if "wti" in str(c).lower()), None)

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
        if latest_brent is None or (isinstance(latest_brent, float) and math.isnan(latest_brent)):
            latest_brent = 0.0
        if latest_brent is not None:
            c1.metric("Brent (Latest)", f"${latest_brent:,.2f}")
            if len(df) >= 2:
                prev = df[brent_col].dropna().iloc[-2]
                c2.metric("Brent Change", f"${latest_brent - prev:+,.2f}")
    if wti_col:
        latest_wti = df[wti_col].dropna().iloc[-1] if not df[wti_col].dropna().empty else None
        if latest_wti is None or (isinstance(latest_wti, float) and math.isnan(latest_wti)):
            latest_wti = 0.0
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
                        config=get_chart_config() if _HELPERS else {"displayModeBar": False})
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
        # opec_monthly arrives as {'data': {'records':[...], 'latest':..}} (or
        # directly as that data). The real keys are opec_basket_usd / period —
        # the old code read 'price'/'month'/'change' which never existed -> N/A.
        node = opec_data.get("data", opec_data) if isinstance(opec_data, dict) else opec_data
        recs = node.get("records") if isinstance(node, dict) else (node if isinstance(node, list) else [])
        latest = recs[-1] if isinstance(recs, list) and recs else (node if isinstance(node, dict) else {})
        if not isinstance(latest, dict):
            latest = {}
        basket = latest.get("opec_basket_usd", node.get("latest") if isinstance(node, dict) else None)
        month = latest.get("period", "N/A")
        change = "—"
        if isinstance(recs, list) and len(recs) >= 2:
            try:
                change = f"{float(basket) - float(recs[-2].get('opec_basket_usd')):+.2f}"
            except Exception:
                change = "—"
        st.markdown("##### OPEC Basket Price")
        c1, c2, c3 = st.columns(3)
        c1.metric("OPEC Basket", f"${basket}" if basket not in (None, "N/A") else "N/A")
        c2.metric("Month", str(month))
        c3.metric("Change", str(change))
    else:
        st.info("OPEC basket data not available. Ensure API Hub is synced.")

    st.markdown("---")

    # PSU refinery prices — sourced from live_prices.json, the SAME values the
    # Command Center refinery ticker shows, so refinery prices match on every
    # page. (Previously this read tbl_refinery_production.json and showed
    # production VOLUMES under a "Prices" heading.)
    st.markdown("##### PSU Refinery Prices (India)")
    st.markdown(
        "Indian PSU refineries (IOCL, BPCL, HPCL) revise bitumen prices "
        "fortnightly (1st and 16th of each month)."
    )

    # Same real, base-consistent prices as the Command Center ticker.
    try:
        from price_board import build_price_board
        from market_data import get_unified_prices
        _lp = {}
        _lp_path = BASE / "live_prices.json"
        if _lp_path.exists():
            _lp = json.loads(_lp_path.read_text(encoding="utf-8")) or {}
        _base = float(get_unified_prices().get("vg30") or 76870)
        refineries = build_price_board(_base, _lp)["refinery"]
    except Exception:
        refineries = []
    rows = [{"Refinery": n, "Grade": g, "Price (₹/MT)": f"₹{int(p):,}"}
            for n, g, p in refineries if p]
    if rows and _PANDAS:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    elif rows:
        for r in rows:
            st.write(r)
    else:
        st.info("No refinery price data available.")

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

    # Keep only USD/INR if a pair column is present (data is long format).
    pair_col = next((c for c in df.columns if c.lower() in ("pair", "symbol", "benchmark")), None)
    if pair_col is not None:
        mask = df[pair_col].astype(str).str.upper().str.replace(" ", "").str.contains("USD/INR")
        if mask.any():
            df = df[mask]

    # Normalise date column (`date_time` is what the hub writes — was missing).
    date_col = None
    for col in ("date", "date_time", "ds", "Date", "timestamp", "fetch_date_ist"):
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        st.warning("No date column found in FX data.")
        return

    _date_raw = df[date_col].astype(str).str.replace(r"\s*IST$", "", regex=True)
    df["date"] = pd.to_datetime(_date_raw, errors="coerce", dayfirst=False)
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
    if latest_rate is None or (isinstance(latest_rate, float) and math.isnan(latest_rate)):
        latest_rate = 0.0
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
                        config=get_chart_config() if _HELPERS else {"displayModeBar": False})
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
