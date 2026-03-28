"""
PPS Anantam -- Refinery Supply Dashboard v1.0
================================================
2-tab UI: Production Heatmap, Shutdown Alerts.
Monitors Indian refinery production data and scans news
for supply disruption events (shutdowns, maintenance, fires).

Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

LOG = logging.getLogger("refinery_supply_dashboard")

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

# ── Shutdown / disruption keywords ──────────────────────────────────────────
_SHUTDOWN_KEYWORDS = [
    "shutdown", "maintenance", "fire", "explosion",
    "refinery", "outage", "turnaround", "closure",
    "blast", "accident", "force majeure",
]


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


# ── Tab A: Production Heatmap ───────────────────────────────────────────────

def _render_production_heatmap(st) -> None:
    """State x Refinery production heatmap from tbl_refinery_production.json."""
    st.subheader("Refinery Production Heatmap")

    raw = _load_json("tbl_refinery_production.json")
    if not raw:
        st.info("No refinery production data available. Run the API Hub sync to fetch data.")
        return

    if not _PANDAS:
        st.warning("pandas is required for the production heatmap.")
        return

    df = pd.DataFrame(raw)

    # Identify relevant columns
    state_col = next((c for c in df.columns if "state" in c.lower()), None)
    refinery_col = next((c for c in df.columns if "refinery" in c.lower() or "name" in c.lower()), None)
    prod_col = next((c for c in df.columns
                     if "production" in c.lower() or "output" in c.lower()
                     or "capacity" in c.lower() or "qty" in c.lower()), None)

    if not state_col or not refinery_col:
        # Fallback: show raw data table
        st.markdown("##### Refinery Production Data")
        st.dataframe(df.tail(30), use_container_width=True, hide_index=True)
        return

    if prod_col:
        df[prod_col] = pd.to_numeric(df[prod_col], errors="coerce").fillna(0)

    # KPI row
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Refineries", f"{df[refinery_col].nunique()}")
    c2.metric("States Covered", f"{df[state_col].nunique()}")
    if prod_col:
        c3.metric("Total Production", f"{df[prod_col].sum():,.0f} MT")

    # Heatmap via Plotly
    if _PLOTLY and prod_col:
        pivot = df.pivot_table(
            index=state_col, columns=refinery_col,
            values=prod_col, aggfunc="sum", fill_value=0,
        )
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[
                [0.0, _IVORY],
                [0.25, "#d4e4c7"],
                [0.5, _GREEN],
                [0.75, _GOLD],
                [1.0, _FIRE],
            ],
            hovertemplate="State: %{y}<br>Refinery: %{x}<br>Production: %{z:,.0f} MT<extra></extra>",
        ))
        fig.update_layout(
            title="Production by State & Refinery",
            xaxis_title="Refinery",
            yaxis_title="State",
            template="plotly_white",
            height=max(350, len(pivot.index) * 35 + 120),
            xaxis=dict(tickangle=-45),
        )
        st.plotly_chart(fig, use_container_width=True)
    elif prod_col:
        # Fallback: grouped bar via st.bar_chart
        agg = df.groupby(state_col)[prod_col].sum().sort_values(ascending=False)
        st.bar_chart(agg)

    # Data table
    with st.expander("View Detailed Production Data", expanded=False):
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(f"Last updated: {_ist_now()}")


# ── Tab B: Shutdown Alerts ──────────────────────────────────────────────────

def _render_shutdown_alerts(st) -> None:
    """Filter tbl_news_feed.json for shutdown/maintenance keywords."""
    st.subheader("Refinery Shutdown & Disruption Alerts")

    raw = _load_json("tbl_news_feed.json")
    if not raw:
        st.info("No news feed data available. Run the API Hub sync to fetch data.")
        return

    # Filter for supply disruption keywords
    alerts: List[dict] = []
    for article in raw:
        text_fields = " ".join(
            str(article.get(f, ""))
            for f in ("title", "headline", "summary", "description", "content", "source")
        ).lower()
        matched = [kw for kw in _SHUTDOWN_KEYWORDS if kw in text_fields]
        if matched:
            alerts.append({**article, "_matched_keywords": ", ".join(matched)})

    if not alerts:
        st.success("No refinery shutdown or disruption alerts detected in the news feed.")
        st.caption(f"Scanned {len(raw)} articles for keywords: {', '.join(_SHUTDOWN_KEYWORDS)}")
        return

    # Severity badge
    st.markdown(
        f'<div style="background:{_FIRE};color:white;padding:10px 16px;border-radius:8px;'
        f'margin-bottom:12px;font-weight:600;">'
        f'Found {len(alerts)} potential supply disruption alert(s) in {len(raw)} articles'
        f'</div>',
        unsafe_allow_html=True,
    )

    if _PANDAS:
        df_alerts = pd.DataFrame(alerts)
        # Select display columns
        display_cols = []
        for preferred in ("title", "headline", "date", "source", "summary", "_matched_keywords"):
            if preferred in df_alerts.columns:
                display_cols.append(preferred)
        if not display_cols:
            display_cols = list(df_alerts.columns[:5])

        rename_map = {
            "title": "Headline", "headline": "Headline",
            "date": "Date", "source": "Source",
            "summary": "Summary", "_matched_keywords": "Matched Keywords",
        }
        st.dataframe(
            df_alerts[display_cols].rename(columns=rename_map),
            use_container_width=True,
            hide_index=True,
        )
    else:
        for a in alerts[:20]:
            title = a.get("title") or a.get("headline", "Untitled")
            date_str = a.get("date", "")
            source = a.get("source", "")
            st.markdown(
                f"- **{title}** ({source}, {date_str}) "
                f"-- Keywords: {a.get('_matched_keywords', '')}"
            )

    # Detailed view in expanders
    with st.expander("View Alert Details", expanded=False):
        for i, alert in enumerate(alerts[:15]):
            title = alert.get("title") or alert.get("headline", f"Alert #{i+1}")
            keywords = alert.get("_matched_keywords", "")
            summary = alert.get("summary") or alert.get("description", "")
            source = alert.get("source", "Unknown")
            st.markdown(
                f"**{title}**  \n"
                f"Source: {source} | Keywords: `{keywords}`  \n"
                f"{summary[:300]}{'...' if len(summary) > 300 else ''}"
            )
            st.markdown("---")

    st.caption(f"Last updated: {_ist_now()}")


# ── Main Render ──────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function -- called from dashboard.py routing."""
    import streamlit as st

    st.title("Refinery & Supply Dashboard")
    st.caption("Indian refinery production tracking and supply disruption monitoring")

    tabs = st.tabs([
        "Production Heatmap",
        "Shutdown Alerts",
    ])

    with tabs[0]:
        _render_production_heatmap(st)

    with tabs[1]:
        _render_shutdown_alerts(st)
