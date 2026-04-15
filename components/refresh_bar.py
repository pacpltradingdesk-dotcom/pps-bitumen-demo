"""
Refresh Bar — standard freshness indicator + manual refresh button.

Drop one line at the top of any Daily Core page:

    from components.refresh_bar import render_refresh_bar
    render_refresh_bar("command_center")

The bar shows:
  - Traffic-light dot (🟢 / 🟡 / 🔴 / ⚪) based on oldest attached cache
  - "Data X min old" label
  - Refresh button that clears + re-fetches the page's caches, then reruns.

DB-only pages (negotiation, documents, settings) get a muted bar with
just the Refresh button (clears st.cache_data).
"""
from __future__ import annotations

import streamlit as st

from freshness_guard import get_page_age_minutes, refresh_page


# Age thresholds in minutes
_GREEN_MAX = 10
_AMBER_MAX = 30


def _dot_and_label(age: float | None, *, is_db_only: bool,
                   missing: bool) -> tuple[str, str, str]:
    """Return (dot_emoji, color_hex, text_label)."""
    if is_db_only:
        return ("⚪", "#6B7280", "Live DB — always fresh")
    if missing or age is None:
        return ("🔴", "#EF4444", "Data missing — click Refresh")
    if age < _GREEN_MAX:
        return ("🟢", "#10B981", f"Data fresh · {age:.0f} min old")
    if age < _AMBER_MAX:
        return ("🟡", "#F59E0B", f"Data aging · {age:.0f} min old")
    # Red
    return ("🔴", "#EF4444", f"Data stale · {age:.0f} min old")


def render_refresh_bar(page_key: str, *, show_age: bool = True) -> None:
    """Render the uniform refresh bar at the top of a page.

    page_key must match a key in freshness_guard.PAGE_CACHES (unknown keys
    get the DB-only treatment — just a Refresh button, no age).
    """
    info = get_page_age_minutes(page_key)
    dot, color, label = _dot_and_label(
        info.get("max_age_min"),
        is_db_only=info.get("is_db_only", False),
        missing=info.get("missing", False),
    )

    # Compact 1-row layout — [dot + label] [spacer] [button]
    col_label, col_btn = st.columns([6, 1])
    with col_label:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;"
            f"padding:4px 2px;font-size:0.85rem;color:{color};"
            f"font-weight:500;'>"
            f"<span>{dot}</span>"
            f"<span>{label if show_age else 'Live'}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("🔄 Refresh", key=f"_refresh_{page_key}",
                     use_container_width=True, type="secondary"):
            with st.spinner("Refreshing…"):
                refresh_page(page_key)
            st.rerun()
