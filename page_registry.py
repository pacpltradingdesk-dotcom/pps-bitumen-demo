"""
page_registry.py — Page Registration & Dispatch
=================================================
Replaces monolithic if/elif dispatch chain with a decorator-based registry.
Pages register themselves → dashboard.py dispatches via render_page().

Usage:
    # In a page module:
    from page_registry import register_page

    @register_page("🏠 Home")
    def render_home():
        st.title("Home Page")
        ...

    # In dashboard.py:
    from page_registry import render_page, is_registered
    if is_registered(page):
        render_page(page)
    else:
        # fall through to legacy elif chain
"""
from __future__ import annotations

import logging
import time
from typing import Callable

LOG = logging.getLogger("page_registry")

_REGISTRY: dict[str, Callable] = {}


def register_page(page_name: str):
    """Decorator to register a page rendering function."""
    def decorator(fn: Callable):
        _REGISTRY[page_name] = fn
        return fn
    return decorator


def render_page(page_name: str) -> bool:
    """
    Render a registered page. Returns True if rendered, False if not found.
    Adds breadcrumb and timing automatically.
    """
    fn = _REGISTRY.get(page_name)
    if fn is None:
        return False

    try:
        import streamlit as st
        # Breadcrumb
        _render_breadcrumb(page_name)
        # Track in recent pages
        _track_recent_page(page_name)
        # Render with timing
        start = time.time()
        fn()
        elapsed = time.time() - start
        if elapsed > 2.0:
            LOG.debug("Slow page render: %s took %.1fs", page_name, elapsed)
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"Error rendering page '{page_name}': {e}")
        LOG.exception("Page render error: %s", page_name)
        return True  # We handled it (with error)


def is_registered(page_name: str) -> bool:
    """Check if a page is registered."""
    return page_name in _REGISTRY


def get_registered_pages() -> list[str]:
    """Return all registered page names."""
    return list(_REGISTRY.keys())


# ── Breadcrumb ────────────────────────────────────────────────────────────────

def _render_breadcrumb(page_name: str):
    """Render breadcrumb navigation."""
    try:
        import streamlit as st
        from nav_config import get_module_for_page
        module = get_module_for_page(page_name)
        if module:
            # Clean emoji from module name for breadcrumb
            mod_label = module.split(" ", 1)[-1] if " " in module else module
            st.markdown(
                f'<div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;">'
                f'{mod_label} &rsaquo; {page_name}</div>',
                unsafe_allow_html=True,
            )
    except Exception:
        pass


# ── Recent Pages Tracking ─────────────────────────────────────────────────────

def _track_recent_page(page_name: str):
    """Track last 5 visited pages in session_state."""
    try:
        import streamlit as st
        recent = st.session_state.get("_recent_pages", [])
        if recent and recent[-1] == page_name:
            return  # don't add duplicates
        recent.append(page_name)
        st.session_state["_recent_pages"] = recent[-5:]
    except Exception:
        pass


def get_recent_pages() -> list[str]:
    """Return recently visited pages."""
    try:
        import streamlit as st
        return list(st.session_state.get("_recent_pages", []))
    except Exception:
        return []


# ── Page Search ───────────────────────────────────────────────────────────────

def search_pages(query: str) -> list[str]:
    """Search registered + nav pages by keyword."""
    try:
        from nav_config import all_pages
        all_p = list(set(all_pages() + get_registered_pages()))
    except ImportError:
        all_p = get_registered_pages()

    if not query or not query.strip():
        return all_p[:10]

    query_lower = query.lower()
    matches = [p for p in all_p if query_lower in p.lower()]
    return matches[:10]
