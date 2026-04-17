"""
PPS Anantam — Autosuggest Input Components
============================================
Smart pickers for the 3 most-entered fields across the dashboard:
  - customer_picker : 5,890 customers from DB + "Add new" fallback
  - city_picker     : 247 Indian cities from distance_matrix
  - state_picker    : 22 states/UTs from distance_matrix
  - date_picker     : thin wrapper on st.date_input (kept here so every
                       form ends up using the same helpers).

All pickers use st.selectbox which has built-in typeahead search in
Streamlit 1.26+. Item lists are memoised with @st.cache_data so a big
Customer list doesn't hit the DB on every rerun.

Usage:
    from components.autosuggest import customer_picker, city_picker, state_picker
    cust = customer_picker(key="quote_cust", default="")
    city = city_picker(key="quote_city", default="Ahmedabad")
    state = state_picker(key="quote_state")
"""
from __future__ import annotations

import streamlit as st


# ──────────────────────────────────────────────────────────────────────
# Cached option loaders
# ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _load_customers() -> list[str]:
    """Return sorted unique customer names from DB + JSON fallback."""
    names: set[str] = set()
    try:
        from database import get_all_customers
        for c in get_all_customers() or []:
            n = (c.get("name") or "").strip()
            if n:
                names.add(n)
    except Exception:
        pass
    try:
        from customer_source import load_customers
        for c in load_customers() or []:
            n = (c.get("name") or "").strip()
            if n:
                names.add(n)
    except Exception:
        pass
    return sorted(names)


@st.cache_data(ttl=3600, show_spinner=False)
def _load_cities() -> list[str]:
    """Return sorted Indian cities from distance_matrix.CITY_STATE_MAP."""
    try:
        from distance_matrix import CITY_STATE_MAP
        return sorted(CITY_STATE_MAP.keys())
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def _load_states() -> list[str]:
    """Return sorted Indian states/UTs."""
    try:
        from distance_matrix import ALL_STATES
        return sorted(ALL_STATES)
    except Exception:
        return [
            "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi",
            "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
            "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
            "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
            "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
        ]


# ──────────────────────────────────────────────────────────────────────
# Pickers
# ──────────────────────────────────────────────────────────────────────

_ADD_NEW = "➕ Add new…"


def customer_picker(
    key: str,
    default: str = "",
    label: str = "Customer",
    placeholder: str = "Start typing customer name…",
    allow_new: bool = True,
    help: str | None = None,
) -> str:
    """Type-to-search combobox for existing customers + optional 'Add new'.

    If allow_new and user selects the '➕ Add new…' row, a text_input appears
    below to capture the new name. Returned value is the final string.
    """
    names = _load_customers()
    options = ([_ADD_NEW] + names) if allow_new else names
    # Resolve default index
    try:
        idx = options.index(default) if default in options else None
    except Exception:
        idx = None
    pick = st.selectbox(
        label,
        options=options,
        index=idx,
        key=f"{key}__sel",
        placeholder=placeholder,
        help=help or f"{len(names):,} customers on file. Type to search.",
    )
    if pick == _ADD_NEW:
        new_name = st.text_input(
            f"{label} (new)",
            value=default if default and default not in names else "",
            key=f"{key}__new",
            placeholder="Type the full customer name",
        )
        return (new_name or "").strip()
    return (pick or "").strip()


def city_picker(
    key: str,
    default: str = "",
    label: str = "City",
    placeholder: str = "Ahmedabad, Pune, Mumbai…",
    help: str | None = None,
) -> str:
    """Searchable dropdown of 247 Indian cities."""
    cities = _load_cities()
    try:
        idx = cities.index(default) if default in cities else None
    except Exception:
        idx = None
    pick = st.selectbox(
        label,
        options=cities,
        index=idx,
        key=f"{key}__sel",
        placeholder=placeholder,
        help=help or f"{len(cities)} cities. Type to search.",
    )
    return (pick or "").strip()


def state_picker(
    key: str,
    default: str = "",
    label: str = "State",
    placeholder: str = "Select state…",
    help: str | None = None,
) -> str:
    """Searchable dropdown of Indian states/UTs."""
    states = _load_states()
    try:
        idx = states.index(default) if default in states else None
    except Exception:
        idx = None
    pick = st.selectbox(
        label,
        options=states,
        index=idx,
        key=f"{key}__sel",
        placeholder=placeholder,
        help=help or f"{len(states)} states/UTs. Type to search.",
    )
    return (pick or "").strip()


def date_picker(
    key: str,
    default=None,
    label: str = "Date",
    help: str | None = None,
):
    """Thin wrapper around st.date_input so every form uses the same helper."""
    import datetime
    if default is None:
        default = datetime.date.today()
    return st.date_input(label, value=default, key=key, help=help)
