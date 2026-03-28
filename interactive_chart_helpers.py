"""
interactive_chart_helpers.py -- Interactive Chart Enhancement Utilities
======================================================================
Reusable helpers for date range pickers, rich hover tooltips, zoom/pan
controls, expandable detail panels, and alert tickers.

Usage:
    from interactive_chart_helpers import (
        add_date_range_selector,
        apply_interactive_defaults,
        create_alert_ticker,
        expandable_detail_panel,
        filter_df_by_date_range,
    )
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional, Tuple

import plotly.graph_objects as go

LOG = logging.getLogger("interactive_chart_helpers")


# ==============================================================================
# DATE RANGE SELECTOR
# ==============================================================================

def add_date_range_selector(
    container,
    key: str,
    default_days: int = 30,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None,
) -> Tuple[date, date]:
    """Add a date range picker to a Streamlit container.

    Returns (start_date, end_date) tuple.
    """
    import streamlit as st

    today = date.today()
    default_start = today - timedelta(days=default_days)

    if min_date is None:
        min_date = today - timedelta(days=365 * 3)
    if max_date is None:
        max_date = today

    # Quick range buttons
    col1, col2, col3, col4, col5 = container.columns([1, 1, 1, 1, 3])
    with col1:
        if st.button("7D", key=f"{key}_7d", use_container_width=True):
            st.session_state[f"{key}_range"] = (today - timedelta(days=7), today)
    with col2:
        if st.button("30D", key=f"{key}_30d", use_container_width=True):
            st.session_state[f"{key}_range"] = (today - timedelta(days=30), today)
    with col3:
        if st.button("90D", key=f"{key}_90d", use_container_width=True):
            st.session_state[f"{key}_range"] = (today - timedelta(days=90), today)
    with col4:
        if st.button("1Y", key=f"{key}_1y", use_container_width=True):
            st.session_state[f"{key}_range"] = (today - timedelta(days=365), today)

    # Custom date picker
    saved = st.session_state.get(f"{key}_range")
    if saved:
        default_start, default_end = saved
    else:
        default_end = today

    with col5:
        selected = st.date_input(
            "Date Range",
            value=(default_start, default_end if saved else today),
            min_value=min_date,
            max_value=max_date,
            key=f"{key}_picker",
            label_visibility="collapsed",
        )

    if isinstance(selected, tuple) and len(selected) == 2:
        return selected[0], selected[1]
    elif isinstance(selected, tuple) and len(selected) == 1:
        return selected[0], today
    return default_start, today


def filter_df_by_date_range(df, start_date, end_date, date_col: str = "date"):
    """Filter a DataFrame by date range. Handles various date column formats."""
    import pandas as pd

    if df is None or df.empty:
        return df

    df = df.copy()
    if date_col not in df.columns:
        # Try common alternatives
        for alt in ["ds", "Date", "timestamp", "ts"]:
            if alt in df.columns:
                date_col = alt
                break
        else:
            return df

    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date) + pd.Timedelta(days=1)
        mask = (df[date_col] >= start_dt) & (df[date_col] < end_dt)
        return df[mask].reset_index(drop=True)
    except Exception:
        return df


# ==============================================================================
# INTERACTIVE CHART DEFAULTS
# ==============================================================================

def apply_interactive_defaults(
    fig: go.Figure,
    show_rangeslider: bool = True,
    inr_format: bool = False,
    pct_format: bool = False,
) -> go.Figure:
    """Apply interactive enhancements to any Plotly figure.

    - Range slider on x-axis (for time series)
    - Scroll zoom enabled
    - Rich hover tooltips
    - Toolbar with zoom/pan/reset
    """
    config_updates = {
        "hovermode": "x unified",
        "dragmode": "zoom",
    }

    # Range slider for time-series
    if show_rangeslider:
        fig.update_xaxes(
            rangeslider_visible=True,
            rangeslider_thickness=0.05,
            rangeselector=dict(
                buttons=[
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="All"),
                ],
                bgcolor="rgba(30,58,95,0.05)",
                activecolor="rgba(30,58,95,0.2)",
                font=dict(size=10),
            ),
        )

    # Hover template formatting
    if inr_format:
        fig.update_traces(
            hovertemplate="<b>%{x|%d-%b-%Y}</b><br>"
                          "Value: ₹%{y:,.2f}<br>"
                          "<extra></extra>",
        )
    elif pct_format:
        fig.update_traces(
            hovertemplate="<b>%{x|%d-%b-%Y}</b><br>"
                          "Value: %{y:.2f}%<br>"
                          "<extra></extra>",
        )

    fig.update_layout(**config_updates)

    return fig


def get_chart_config() -> dict:
    """Return standard Plotly chart config with interactive tools enabled."""
    return {
        "displayModeBar": True,
        "scrollZoom": True,
        "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"],
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "pps_chart",
            "height": 600,
            "width": 1000,
            "scale": 2,
        },
    }


# ==============================================================================
# ALERT TICKER
# ==============================================================================

def create_alert_ticker(alerts: list[dict]) -> str:
    """Generate HTML for a rotating alert ticker banner.

    Each alert dict should have: severity (P0/P1/P2), message, category
    """
    if not alerts:
        return ""

    severity_colors = {
        "P0": "#f43f5e",   # Red — critical
        "P1": "#f59e0b",   # Amber — warning
        "P2": "#3b82f6",   # Blue — info
    }
    severity_icons = {
        "P0": "&#x1F534;",   # Red circle
        "P1": "&#x1F7E0;",   # Orange circle
        "P2": "&#x1F535;",   # Blue circle
    }

    items_html = ""
    for alert in alerts[:10]:  # Limit to 10
        sev = alert.get("severity", "P2")
        color = severity_colors.get(sev, "#3b82f6")
        icon = severity_icons.get(sev, "&#x2139;")
        msg = alert.get("message", "")
        cat = alert.get("category", "")
        items_html += (
            f'<span style="margin-right:40px;white-space:nowrap;">'
            f'{icon} <b style="color:{color}">[{sev}]</b> '
            f'<span style="color:#64748b;font-size:0.75rem">{cat}</span> '
            f'{msg}</span>'
        )

    return f"""
    <div style="
        overflow:hidden;
        background:linear-gradient(90deg,#faf7f2,#f0ebe1);
        border:1px solid #e2e8f0;
        border-radius:8px;
        padding:8px 16px;
        margin-bottom:12px;
        font-size:0.85rem;
        color:#1e3a5f;
    ">
        <div style="
            display:inline-block;
            white-space:nowrap;
            animation:ticker-scroll 30s linear infinite;
        ">
            {items_html}
        </div>
    </div>
    <style>
        @keyframes ticker-scroll {{
            0% {{ transform: translateX(100%); }}
            100% {{ transform: translateX(-100%); }}
        }}
    </style>
    """


# ==============================================================================
# EXPANDABLE DETAIL PANEL
# ==============================================================================

def expandable_detail_panel(
    title: str,
    content_fn: Callable,
    container=None,
    expanded: bool = False,
    icon: str = "",
) -> None:
    """Render a standardized expandable detail panel.

    Parameters
    ----------
    title : str — Panel header text
    content_fn : callable — Function that renders Streamlit content when expanded
    container : Streamlit container (default: st)
    expanded : bool — Whether panel starts expanded
    icon : str — Optional emoji/icon prefix
    """
    import streamlit as st

    if container is None:
        container = st

    label = f"{icon} {title}" if icon else title
    with container.expander(label, expanded=expanded):
        try:
            content_fn()
        except Exception as e:
            st.error(f"Error loading panel: {e}")


# ==============================================================================
# KPI CARD WITH TREND
# ==============================================================================

def render_kpi_card(
    container,
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None,
):
    """Render a styled KPI metric card."""
    import streamlit as st

    if container is None:
        container = st

    container.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text,
    )


# ==============================================================================
# LOADING SKELETON
# ==============================================================================

def show_loading_skeleton(container=None, rows: int = 3):
    """Show a shimmer loading skeleton while data loads."""
    import streamlit as st

    if container is None:
        container = st

    skeleton_css = """
    <style>
    .skeleton-line {
        height: 16px;
        background: linear-gradient(90deg, #f0ebe1 25%, #faf7f2 50%, #f0ebe1 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    </style>
    """
    lines = "".join(
        f'<div class="skeleton-line" style="width:{90 - i * 10}%"></div>'
        for i in range(rows)
    )
    container.markdown(skeleton_css + lines, unsafe_allow_html=True)
