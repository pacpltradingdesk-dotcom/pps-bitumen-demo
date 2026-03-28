"""
PPS Bitumen Dashboard v5.0 — Filter Bar Component
Clean White Theme | Date, status, and region filters with compact layout.
"""

import streamlit as st
from datetime import datetime, date, timedelta

# ── Theme Colors ──────────────────────────────────────────────
BLUE_PRIMARY = "#2563eb"
BLUE_HOVER   = "#1d4ed8"
BLUE_LIGHT   = "#dbeafe"
GREEN        = "#059669"
RED          = "#dc2626"
AMBER        = "#f59e0b"
SLATE_50     = "#f8fafc"
SLATE_200    = "#e2e8f0"
SLATE_500    = "#64748b"
SLATE_700    = "#334155"
SLATE_900    = "#0f172a"
WHITE        = "#ffffff"

# ── Indian States ─────────────────────────────────────────────
INDIA_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal",
]

INDIA_REGIONS = {
    "North":  ["Delhi", "Haryana", "Himachal Pradesh", "Jammu & Kashmir",
               "Punjab", "Rajasthan", "Uttarakhand", "Uttar Pradesh"],
    "South":  ["Andhra Pradesh", "Karnataka", "Kerala", "Tamil Nadu",
               "Telangana"],
    "East":   ["Bihar", "Jharkhand", "Odisha", "West Bengal",
               "Arunachal Pradesh", "Assam", "Manipur", "Meghalaya",
               "Mizoram", "Nagaland", "Sikkim", "Tripura"],
    "West":   ["Goa", "Gujarat", "Maharashtra"],
    "Central":["Chhattisgarh", "Madhya Pradesh"],
}


def _inject_filter_css():
    """Inject CSS for filter bar styling."""
    st.markdown(f"""
    <style>
    .pps-filter-bar {{
        background: {WHITE};
        border: 1px solid {SLATE_200};
        border-radius: 0.75rem;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }}
    .pps-filter-label {{
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {SLATE_500};
        margin-bottom: 0.25rem;
    }}
    .pps-filter-preset {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s;
    }}
    .pps-filter-preset-active {{
        background: {BLUE_PRIMARY};
        color: {WHITE};
    }}
    .pps-filter-preset-inactive {{
        background: {SLATE_50};
        color: {SLATE_700};
        border: 1px solid {SLATE_200};
    }}
    </style>
    """, unsafe_allow_html=True)


def render_date_filter(key_prefix: str) -> tuple:
    """
    Date range filter with presets (Today, 7d, 30d, 90d, Custom).

    Args:
        key_prefix: Unique prefix for widget keys to avoid collisions.

    Returns:
        Tuple of (start_date, end_date) as date objects.
    """
    _inject_filter_css()

    today = date.today()
    preset_key = f"{key_prefix}_date_preset"
    start_key = f"{key_prefix}_date_start"
    end_key = f"{key_prefix}_date_end"

    # Initialize session state defaults
    if preset_key not in st.session_state:
        st.session_state[preset_key] = "30d"

    col_preset, col_start, col_end = st.columns([2, 1, 1])

    with col_preset:
        st.markdown(
            '<p class="pps-filter-label">Date Range</p>',
            unsafe_allow_html=True,
        )
        preset = st.radio(
            "Preset",
            options=["Today", "7d", "30d", "90d", "Custom"],
            index=["Today", "7d", "30d", "90d", "Custom"].index(
                st.session_state[preset_key]
            ),
            key=preset_key,
            horizontal=True,
            label_visibility="collapsed",
        )

    # Compute dates from preset
    if preset == "Today":
        default_start = today
        default_end = today
    elif preset == "7d":
        default_start = today - timedelta(days=7)
        default_end = today
    elif preset == "30d":
        default_start = today - timedelta(days=30)
        default_end = today
    elif preset == "90d":
        default_start = today - timedelta(days=90)
        default_end = today
    else:  # Custom
        default_start = today - timedelta(days=30)
        default_end = today

    with col_start:
        st.markdown(
            '<p class="pps-filter-label">From</p>',
            unsafe_allow_html=True,
        )
        start_date = st.date_input(
            "Start",
            value=default_start,
            max_value=today,
            key=start_key,
            label_visibility="collapsed",
            disabled=(preset != "Custom"),
        )

    with col_end:
        st.markdown(
            '<p class="pps-filter-label">To</p>',
            unsafe_allow_html=True,
        )
        end_date = st.date_input(
            "End",
            value=default_end,
            max_value=today,
            key=end_key,
            label_visibility="collapsed",
            disabled=(preset != "Custom"),
        )

    # Validate range
    if start_date > end_date:
        st.warning("Start date cannot be after end date.")
        end_date = start_date

    return (start_date, end_date)


def render_status_filter(key_prefix: str, options: list) -> list:
    """
    Multi-select status filter.

    Args:
        key_prefix: Unique prefix for widget keys.
        options:    List of status options to display.

    Returns:
        List of selected status values.
    """
    _inject_filter_css()

    st.markdown(
        '<p class="pps-filter-label">Status</p>',
        unsafe_allow_html=True,
    )

    select_key = f"{key_prefix}_status_filter"

    selected = st.multiselect(
        "Filter by status",
        options=options,
        default=options,
        key=select_key,
        label_visibility="collapsed",
    )

    return selected


def render_region_filter(key_prefix: str) -> list:
    """
    Region / state filter for India.

    Args:
        key_prefix: Unique prefix for widget keys.

    Returns:
        List of selected state names.
    """
    _inject_filter_css()

    region_key = f"{key_prefix}_region"
    state_key = f"{key_prefix}_states"

    col_region, col_state = st.columns(2)

    with col_region:
        st.markdown(
            '<p class="pps-filter-label">Region</p>',
            unsafe_allow_html=True,
        )
        selected_regions = st.multiselect(
            "Region",
            options=["All"] + list(INDIA_REGIONS.keys()),
            default=["All"],
            key=region_key,
            label_visibility="collapsed",
        )

    # Build available states from selected regions
    if "All" in selected_regions or len(selected_regions) == 0:
        available_states = INDIA_STATES
    else:
        available_states = []
        for r in selected_regions:
            available_states.extend(INDIA_REGIONS.get(r, []))
        available_states = sorted(set(available_states))

    with col_state:
        st.markdown(
            '<p class="pps-filter-label">State</p>',
            unsafe_allow_html=True,
        )
        selected_states = st.multiselect(
            "State",
            options=available_states,
            default=[],
            key=state_key,
            label_visibility="collapsed",
        )

    # If no state explicitly selected, return all from the region
    if len(selected_states) == 0:
        return available_states

    return selected_states


def render_filter_bar(
    key_prefix: str,
    show_date: bool = True,
    show_status: bool = False,
    status_options: list = None,
    show_region: bool = False,
) -> dict:
    """
    All-in-one filter bar combining date, status, and region filters.

    Args:
        key_prefix:     Unique prefix for all widget keys.
        show_date:      Whether to show date filter.
        show_status:    Whether to show status filter.
        status_options: List of status options (required if show_status).
        show_region:    Whether to show region filter.

    Returns:
        Dict with keys: "date_range", "status", "region" (based on what is shown).
    """
    _inject_filter_css()

    result = {}

    st.markdown(
        f"""
        <div style="background:{WHITE};border:1px solid {SLATE_200};
        border-radius:0.75rem;padding:0.75rem 1rem;margin-bottom:1rem;">
        <span style="font-size:0.8rem;font-weight:600;color:{SLATE_700};">
        \U0001f50d Filters</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if show_date:
        result["date_range"] = render_date_filter(key_prefix)

    if show_status and status_options:
        result["status"] = render_status_filter(key_prefix, status_options)

    if show_region:
        result["region"] = render_region_filter(key_prefix)

    return result
