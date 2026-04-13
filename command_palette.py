"""
Command Palette — Global Fuzzy Search
======================================
Ctrl+K / Cmd+K opens a palette dialog with all 77 pages + all 25K
contacts searchable by name. Selecting a result navigates directly.

Also accessible via a sidebar "🔍 Quick Find" button.

Public API:
    render_command_palette_button()  — sidebar trigger button
    render_command_palette()         — modal dialog (st.dialog)
    inject_ctrl_k_listener()         — JS to catch Ctrl+K/Cmd+K
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as _components

from nav_config import MODULE_NAV, all_pages, get_module_for_page


# ═══════════════════════════════════════════════════════════════════════════
# Index builders
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def _build_page_index() -> list[dict]:
    """Flat list of all pages with module + label for searching."""
    out = []
    for mod_key, mod in MODULE_NAV.items():
        for tab in mod["tabs"]:
            out.append({
                "type":   "page",
                "page":   tab["page"],
                "label":  tab["label"],
                "module": mod.get("label", mod_key),
                "icon":   mod.get("icon", "📄"),
                "star":   tab.get("star", False),
            })
    return out


@st.cache_data(ttl=600)
def _build_contact_index(limit: int = 500) -> list[dict]:
    """Top contacts by recency/score from the DB (cached)."""
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT name, phone, city, state, category
                FROM tbl_contacts
                WHERE name IS NOT NULL AND name != ''
                ORDER BY rowid DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            return [{
                "type":  "contact",
                "name":  r[0] or "",
                "phone": r[1] or "",
                "city":  r[2] or "",
                "state": r[3] or "",
                "category": r[4] or "",
            } for r in rows if r[0]]
        finally:
            try: cur.close()
            except Exception: pass
    except Exception:
        return []


def _score_match(query: str, text: str) -> int:
    """Simple substring + token ranker. Higher = better match."""
    if not query or not text:
        return 0
    q = query.lower().strip()
    t = text.lower()
    if not q:
        return 0
    # Exact match
    if q == t:
        return 1000
    # Starts-with
    if t.startswith(q):
        return 500
    # Contains full query
    if q in t:
        return 250
    # Token overlap
    q_tokens = set(q.split())
    t_tokens = set(t.split())
    overlap = len(q_tokens & t_tokens)
    if overlap > 0:
        return 50 * overlap
    # All chars present in order (fuzzy)
    i = 0
    for ch in t:
        if i < len(q) and ch == q[i]:
            i += 1
    if i == len(q):
        return 10
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════════

def render_command_palette_button():
    """Render the 🔍 Quick Find button in the sidebar."""
    if st.button("🔍 Quick Find (Ctrl+K)", key="_cmd_palette_btn",
                 use_container_width=True,
                 help="Find any page or contact fast"):
        st.session_state["_show_cmd_palette"] = True


def render_command_palette():
    """Render the palette as a modal dialog when open."""
    if not st.session_state.get("_show_cmd_palette"):
        return

    try:
        @st.dialog("🔍 Quick Find — Pages & Contacts", width="large")
        def _dlg():
            _render_palette_content()
        _dlg()
    except Exception:
        # Fallback for older Streamlit
        with st.container(border=True):
            _render_palette_content()


def _render_palette_content():
    st.caption("Koi bhi page ya customer dhundo — typing karte hi results dikhenge. Press Escape to close.")

    query = st.text_input(
        "Search",
        key="_cmd_palette_query",
        placeholder="e.g. 'pricing', 'rohan', 'iocl', 'market signals'",
        label_visibility="collapsed",
    )

    # Index
    pages = _build_page_index()
    contacts = _build_contact_index(limit=500)

    # Rank
    if query and query.strip():
        scored_pages = []
        for p in pages:
            text = f'{p["label"]} {p["module"]} {p["page"]}'
            score = _score_match(query, text)
            if score > 0:
                scored_pages.append((score, p))
        scored_pages.sort(key=lambda x: -x[0])
        top_pages = [p for _, p in scored_pages[:8]]

        scored_contacts = []
        for c in contacts:
            text = f'{c["name"]} {c["city"]} {c["state"]} {c["category"]}'
            score = _score_match(query, text)
            if score > 0:
                scored_contacts.append((score, c))
        scored_contacts.sort(key=lambda x: -x[0])
        top_contacts = [c for _, c in scored_contacts[:8]]
    else:
        # Default: show starred pages + recent contacts
        top_pages = [p for p in pages if p.get("star")][:8]
        top_contacts = contacts[:5]

    # Render results
    if top_pages:
        st.markdown("**📄 Pages**")
        for i, p in enumerate(top_pages):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f'<div style="padding:6px 0;">'
                    f'<span style="font-weight:600;color:#111827;">{p["icon"]} {p["label"]}</span>'
                    f'<span style="color:#6B7280;font-size:0.75rem;margin-left:8px;">— {p["module"]}</span>'
                    + (' <span style="color:#F59E0B;">★</span>' if p.get("star") else '')
                    + "</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("Open", key=f"_cp_page_{i}",
                             use_container_width=True, type="primary"):
                    from navigation_engine import navigate_to
                    st.session_state["_show_cmd_palette"] = False
                    navigate_to(p["page"])

    if top_contacts:
        st.markdown("---")
        st.markdown("**👥 Contacts**")
        for i, c in enumerate(top_contacts):
            col1, col2 = st.columns([4, 1])
            with col1:
                loc = " · ".join(x for x in [c["city"], c["state"]] if x)
                cat = f" ({c['category']})" if c["category"] else ""
                phone = f" · {c['phone']}" if c["phone"] else ""
                st.markdown(
                    f'<div style="padding:6px 0;">'
                    f'<span style="font-weight:600;color:#111827;">👤 {c["name"]}</span>{cat}<br>'
                    f'<span style="color:#6B7280;font-size:0.75rem;">{loc}{phone}</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("Go to Contacts", key=f"_cp_contact_{i}",
                             use_container_width=True):
                    from navigation_engine import navigate_to
                    # Store the selected contact name for pre-filtering
                    st.session_state["_filter_contact_name"] = c["name"]
                    st.session_state["_show_cmd_palette"] = False
                    navigate_to("📱 Contacts Directory")

    if not top_pages and not top_contacts and query:
        st.info(f"'{query}' ke liye kuch nahi mila. Aur specific try karo.")

    if st.button("Close", key="_cp_close"):
        st.session_state["_show_cmd_palette"] = False
        st.rerun()


def inject_ctrl_k_listener():
    """
    Inject JS that opens the palette when user presses Ctrl+K / Cmd+K.
    Achieved by JS-clicking the hidden sidebar 'Quick Find' button.
    """
    html = """
<script>
(function() {
  try {
    var doc = window.parent.document;
    // Guard: only wire listener once per page load
    if (doc._ppsCmdKWired) return;
    doc._ppsCmdKWired = true;

    doc.addEventListener('keydown', function(e) {
      var isMac = (navigator.platform || '').toLowerCase().indexOf('mac') !== -1;
      var combo = (isMac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === 'k';
      if (combo) {
        e.preventDefault();
        // Find the sidebar "Quick Find" button by text
        var btns = doc.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = (btns[i].textContent || '').trim();
          if (t.indexOf('Quick Find') !== -1) {
            btns[i].click();
            break;
          }
        }
      }
    });
  } catch (err) { console.warn('Ctrl+K wire failed:', err); }
})();
</script>
"""
    _components.html(html, height=0)
