"""
global_search.py — top-of-page command palette.
================================================
A single search box, rendered at the top of every page, that lets the user type
any word ("news", "contacts", "pricing", "tender"…) and instantly see every
matching page/feature as a clickable button that navigates there.

Results are filtered by the current user's role, so search only ever surfaces
pages the user can actually open (and never deep-links into a restricted page).
"""
from __future__ import annotations

import streamlit as st

from nav_config import MODULE_NAV

# Common business words that don't appear verbatim in a page label, mapped to the
# page(s) they should surface. Boosts recall for natural-language searches.
_ALIASES: dict[str, list[str]] = {
    "news":      ["📰 News Intelligence"],
    "contact":   ["📱 Contacts Directory", "👥 Party Master"],
    "contacts":  ["📱 Contacts Directory", "👥 Party Master"],
    "phone":     ["📱 Contacts Directory"],
    "customer":  ["👥 Party Master", "🎯 CRM & Tasks", "💳 Credit & Aging"],
    "client":    ["💬 Client Chat", "🌐 Client Showcase", "👥 Party Master"],
    "whatsapp":  ["💬 Communication Hub", "📡 Rate Broadcast"],
    "message":   ["💬 Communication Hub", "💬 Client Chat"],
    "share":     ["📤 Share Center", "📡 Rate Broadcast"],
    "broadcast": ["📡 Rate Broadcast", "📤 Share Center"],
    "price":     ["🧮 Pricing Calculator", "📝 Manual Price Entry", "🔮 Price Prediction"],
    "quote":     ["💎 One-Click Quote"],
    "tender":    ["🏗️ NHAI Tenders"],
    "invoice":   ["📋 Sales Orders", "💳 Payment Orders"],
    "payment":   ["💳 Payment Orders", "💳 Credit & Aging"],
    "order":     ["📋 Sales Orders", "📋 Purchase Orders"],
    "report":    ["📤 Reports"],
    "ai":        ["🔮 Price Prediction", "🤝 Negotiation Assistant", "💬 Trading Chatbot", "🤖 AI Learning"],
    "chat":      ["💬 Trading Chatbot", "💬 Client Chat"],
    "user":      ["👥 User Management"],
    "login":     ["👥 User Management", "⚙️ Settings"],
    "setting":   ["⚙️ Settings"],
    "api":       ["🌐 API Dashboard", "🔗 API HUB"],
    "alert":     ["🚨 Alert Center", "🔔 Alert System"],
}


def _index() -> list[dict]:
    """Flatten MODULE_NAV into a searchable list of {page, label, module}."""
    items, seen = [], set()
    for mod_key, mod in MODULE_NAV.items():
        for tab in mod.get("tabs", []):
            page = tab.get("page")
            if page and page not in seen:
                seen.add(page)
                items.append({"page": page, "label": tab.get("label", ""), "module": mod_key})
    return items


def _allowed(page: str) -> bool:
    """True if the current role may open this page (default open if RBAC absent)."""
    try:
        from role_engine import check_page_access
        return check_page_access(page)
    except Exception:
        return True


def _search(query: str) -> list[dict]:
    """Rank pages by relevance to the query (label/page/module substring + aliases)."""
    ql = query.strip().lower()
    if not ql:
        return []
    items = _index()

    # Pages promoted by alias keywords (substring match on the alias word).
    alias_pages: set[str] = set()
    for word, pages in _ALIASES.items():
        if word in ql or ql in word:
            alias_pages.update(pages)

    scored = []
    for it in items:
        label_l, page_l = it["label"].lower(), it["page"].lower()
        score = 0
        if ql == label_l or ql == page_l:
            score = 100
        elif label_l.startswith(ql) or page_l.startswith(ql):
            score = 80
        elif ql in label_l or ql in page_l:
            score = 60
        elif ql in it["module"].lower():
            score = 30
        if it["page"] in alias_pages:
            score = max(score, 70)
        if score and _allowed(it["page"]):
            scored.append((score, it))

    scored.sort(key=lambda x: (-x[0], x[1]["label"]))
    return [it for _s, it in scored]


def render_global_search(slot: str = "main"):
    """Render the search box + live results. `slot` keeps widget keys unique per call site."""
    q = st.text_input(
        "🔎 Search",
        key=f"_gsearch_{slot}",
        placeholder="🔎 Search anything — news, contacts, pricing, tenders, reports…",
        label_visibility="collapsed",
    )
    if not q or not q.strip():
        return

    results = _search(q)
    if not results:
        st.caption(f"No pages match “{q}”. Try a shorter word like *news* or *price*.")
        return

    st.caption(f"{len(results)} result{'s' if len(results) != 1 else ''} for “{q}” — click to open:")
    top = results[:18]
    cols = st.columns(3)
    for i, it in enumerate(top):
        with cols[i % 3]:
            if st.button(it["page"], key=f"_gsres_{slot}_{i}_{it['page']}",
                         use_container_width=True, help=f"in {it['module']}"):
                st.session_state["_nav_goto"] = it["page"]
                st.rerun()
