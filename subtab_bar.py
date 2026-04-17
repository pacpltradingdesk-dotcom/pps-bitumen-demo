"""
PPS Anantam — Sidebar Feature Navigation v6.0 (Crisp Light Edition)
================================================
Renders the features of the active module in the sidebar.
Features listed as buttons. Quick Actions. Sticky Notes (news/market).
"""
from __future__ import annotations

import streamlit as st
import json
from pathlib import Path
from nav_config import get_tabs, get_module_for_page, MODULE_NAV

_ROOT = Path(__file__).parent


def render_sidebar_features(module: str) -> str:
    """
    Render the feature list for the given module in st.sidebar.

    Returns the currently selected page string.
    """
    # Inject mobile sidebar CSS
    st.markdown("""<style>
    /* ── Mobile Sidebar Optimizations ── */
    @media (max-width: 768px) {
        /* Compact logo section */
        [data-testid="stSidebar"] img {
            height: 40px !important;
            margin-bottom: 8px !important;
        }
        /* Smaller sidebar buttons */
        [data-testid="stSidebar"] .stButton>button {
            font-size: 0.78rem !important;
            min-height: 38px !important;
            padding: 0.35rem 0.6rem !important;
        }
        /* Compact quick actions grid */
        [data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
            gap: 3px !important;
        }
        /* Smaller sticky notes */
        [data-testid="stSidebar"] div[style*="margin-bottom:24px"] {
            margin-bottom: 12px !important;
            padding: 12px !important;
        }
        /* Hide news cards on very small sidebar (keep market ticker) */
        [data-testid="stSidebar"] div[style*="LATEST INTEL"] {
            display: none;
        }
    }
    @media (max-width: 480px) {
        [data-testid="stSidebar"] img {
            height: 32px !important;
        }
        [data-testid="stSidebar"] .stButton>button {
            font-size: 0.72rem !important;
            min-height: 36px !important;
        }
    }
    </style>""", unsafe_allow_html=True)
    mod = MODULE_NAV.get(module)
    if not mod:
        return "🎯 Command Center"

    tabs = mod["tabs"]
    current_page = st.session_state.get("selected_page", tabs[0]["page"])

    # Ensure current_page belongs to this module, otherwise default to first feature
    module_pages = [t["page"] for t in tabs]
    if current_page not in module_pages:
        current_page = tabs[0]["page"]

    with st.sidebar:
        # ── Active Tour (floating tooltip — rendered near actual button) ──
        # Auto-open tutorial on first login (welcome flow)
        if st.session_state.pop("_welcome_pending", False):
            st.session_state["_show_tutorial"] = True
            st.session_state["_tour_step"] = 0
        if st.session_state.get("_show_tutorial"):
            try:
                from tutorial_engine import render_tour
                render_tour()
            except Exception as _e:
                st.error(f"Tour failed: {_e}")
                st.session_state["_show_tutorial"] = False
                st.session_state["_tour_step"] = 0

        # Brand logo (cached in session state)
        import base64
        _logo_path = _ROOT / "pps_logo_brand.jpg"
        if _logo_path.exists():
            if "_sidebar_logo_b64" not in st.session_state:
                with open(_logo_path, "rb") as _lf:
                    st.session_state["_sidebar_logo_b64"] = base64.b64encode(_lf.read()).decode()
            _logo_b64 = st.session_state["_sidebar_logo_b64"]
            st.markdown(f"""
<div style="text-align:center;padding:16px 12px;margin:-16px -16px 24px;
            background: #FAFAFA; border-bottom: 1px solid #E5E7EB; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);">
  <img src="data:image/jpeg;base64,{_logo_b64}"
       style="height:60px;margin-bottom:12px;border-radius:10px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.05); border: 1px solid #E5E7EB;" alt="PPS Anantams">
  <div style="font-size:0.9rem;font-weight:800;color:var(--text-main);letter-spacing:-0.02em;">
    Bitumen Dashboard
  </div>
  <div style="color:var(--text-blue);font-size:0.6rem;margin-top:4px;letter-spacing:0.1em;text-transform:uppercase; font-weight: 700;">
    AI Commander v6.0 Server
  </div>
</div>""", unsafe_allow_html=True)

        # Module header
        st.markdown(
            f'<div style="font-size:1.1rem; font-weight:800; letter-spacing:-0.02em; margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid #E5E7EB; color:var(--text-main);">{mod["icon"]} {mod["label"]}</div>',
            unsafe_allow_html=True,
        )

        # Phase 3: split into Daily Core (starred) + Advanced (rest).
        # Starred tabs render inline as before. The remaining tabs collapse
        # into a "Show all (N more) · Advanced" expander so the Daily Core
        # 14 are always the primary view, but nothing is hidden away.
        starred_tabs = [t for t in tabs if t.get("star")]
        other_tabs   = [t for t in tabs if not t.get("star")]

        # If current page lives inside the Advanced section, open the
        # expander by default so the user can see their selection.
        _current_in_advanced = any(t["page"] == current_page for t in other_tabs)

        # Phase 5 pill color palette
        _PILL_COLORS = {
            "red":     ("#EF4444", "#FEE2E2"),
            "gold":    ("#B45309", "#FEF3C7"),
            "indigo":  ("#4F46E5", "#E0E7FF"),
            "emerald": ("#047857", "#D1FAE5"),
        }

        def _render_tab_button(tab, i, key_prefix):
            star = " ✦" if tab.get("star") else ""
            is_active = (tab["page"] == current_page)
            btn_type = "primary" if is_active else "secondary"
            if st.button(
                f"{tab['label']}{star}",
                key=f"_sidebar_feat_{module}_{key_prefix}_{i}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state["selected_page"] = tab["page"]
                st.rerun()
            # Phase 5: feature pill (small right-aligned tag under button)
            pill = tab.get("pill")
            if pill:
                try:
                    label, color = pill
                    fg, bg = _PILL_COLORS.get(color, _PILL_COLORS["indigo"])
                    st.markdown(
                        f"<div style='margin:-4px 0 4px 0;text-align:right;'>"
                        f"<span style='background:{bg};color:{fg};"
                        f"font-size:0.58rem;font-weight:800;letter-spacing:0.04em;"
                        f"padding:1px 7px;border-radius:10px;"
                        f"border:1px solid {fg}33;'>"
                        f"{label}</span></div>",
                        unsafe_allow_html=True,
                    )
                except Exception:
                    pass

        # Render Daily Core first (preserves sub_group dividers among starred)
        last_group = None
        for i, tab in enumerate(starred_tabs):
            sub_group = tab.get("sub_group")
            if sub_group and sub_group != last_group:
                if last_group is not None:
                    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.65rem; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;">{sub_group}</div>', unsafe_allow_html=True)
                last_group = sub_group
            _render_tab_button(tab, i, "core")

        # Render Advanced (non-starred) behind an expander
        if other_tabs:
            st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
            with st.expander(f"➕ Show all ({len(other_tabs)} more) · Advanced",
                             expanded=_current_in_advanced):
                last_group = None
                for i, tab in enumerate(other_tabs):
                    sub_group = tab.get("sub_group")
                    if sub_group and sub_group != last_group:
                        if last_group is not None:
                            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
                        st.markdown(f'<div style="font-size:0.62rem; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">{sub_group}</div>', unsafe_allow_html=True)
                        last_group = sub_group
                    _render_tab_button(tab, i, "adv")

        # ── Active Customer Picker ─────────────────────────────────────
        st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
        try:
            from navigation_engine import render_customer_picker_sidebar
            render_customer_picker_sidebar()
        except Exception:
            pass

        # ── Quick Find + Tutorial buttons ──────────────────────────────
        st.markdown('<div style="margin-top:18px;"></div>', unsafe_allow_html=True)
        try:
            from command_palette import (render_command_palette_button,
                                         render_command_palette,
                                         inject_ctrl_k_listener)
            render_command_palette_button()
            render_command_palette()  # renders only if _show_cmd_palette is True
            inject_ctrl_k_listener()
        except Exception as _e_cp:
            st.caption(f"Quick Find unavailable: {_e_cp}")

        if st.button("📖 Tutorial", key="_sidebar_tutorial_btn",
                     use_container_width=True, help="Guided tour phir se shuru karo"):
            st.session_state["_show_tutorial"] = True
            st.session_state["_tour_step"] = 0
            st.rerun()

        # ── Quick Actions (functional popover actions) ─────────────────
        st.markdown('<div style="margin-top:32px; margin-bottom:12px; font-size:0.65rem; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; border-bottom:1px solid #E5E7EB; padding-bottom:8px;">QUICK ACTIONS</div>', unsafe_allow_html=True)

        page_name = current_page.split(" ", 1)[-1] if " " in current_page else current_page

        # Row 1: PDF, Print, Excel
        r1 = st.columns(3)
        with r1[0]:
            with st.popover("📄", use_container_width=True, help="Export PDF"):
                st.markdown(f"**Export: {page_name}**")
                st.caption("Generate PDF of current page")
                if st.button("Generate PDF", key="_qa_pdf_go", type="primary", use_container_width=True):
                    try:
                        from pdf_export_engine import PDFExportEngine
                        eng = PDFExportEngine()
                        eng.page_title = page_name
                        pdf = eng.build()
                        if pdf:
                            st.download_button("Download", data=pdf,
                                file_name=f"PPS_{page_name.replace(' ','_')}.pdf",
                                mime="application/pdf", key="_qa_pdf_dl")
                    except Exception:
                        st.info("Use Ctrl+P in browser to print as PDF")
        with r1[1]:
            with st.popover("🖨️", use_container_width=True, help="Print"):
                st.markdown("**Print Current Page**")
                st.caption("Opens browser print dialog")
                st.markdown("""
<script>function ppsPrint(){window.print()}</script>
<button onclick="ppsPrint()" style="background: var(--text-blue);color:white;border:none;
padding:8px 16px;border-radius:6px;cursor:pointer;width:100%;font-weight:600;box-shadow:var(--shadow-sm); transition: var(--transition);">
🖨️ Print Now</button>
""", unsafe_allow_html=True)
        with r1[2]:
            with st.popover("📊", use_container_width=True, help="Export Excel"):
                st.markdown(f"**Export: {page_name}**")
                st.caption("Download data as Excel/CSV")
                # Real action: jump to Reports / Export page where bulk
                # exports actually happen, instead of just showing a tip.
                if st.button("Open Export Reports", key="_qa_csv_go",
                             type="primary", use_container_width=True):
                    st.session_state["_nav_goto"] = "📤 Reports"
                    st.rerun()
                st.caption("Or hover any data table on the page and click ↓ to export inline.")

        # Row 2: Share, WA, TG
        r2 = st.columns(3)
        with r2[0]:
            with st.popover("🔗", use_container_width=True, help="Share"):
                st.markdown(f"**Share: {page_name}**")
                msg = f"🏛️ PPS ANANTAM — {page_name}\nCheck the latest data on PPS Bitumen Dashboard"
                st.code(msg, language=None)
                st.caption("Copy the text above and share")
        with r2[1]:
            with st.popover("📱", use_container_width=True, help="WhatsApp"):
                st.markdown(f"**WhatsApp Share**")
                wa_msg = f"🏛️ PPS ANANTAM — {page_name}\nLatest update from PPS Bitumen Dashboard"
                try:
                    from components.message_preview import render_msg_preview
                    render_msg_preview(wa_msg, channel="whatsapp")
                except Exception:
                    pass
                with st.expander("✏️ Edit message", expanded=False):
                    st.text_area("Message", value=wa_msg, key="_qa_wa_msg", height=100)
                phone = st.text_input("Phone (with +91)", placeholder="+919876543210", key="_qa_wa_ph")
                if st.button("Send via WA", key="_qa_wa_send", type="primary", use_container_width=True):
                    if phone:
                        try:
                            from database import _insert_row, _now_ist
                            _insert_row("whatsapp_queue", {
                                "to_number": phone, "message_type": "session",
                                "session_text": wa_msg, "status": "queued",
                                "created_at": _now_ist()
                            })
                            st.success("Queued for sending!")
                        except Exception:
                            st.info(f"Open WhatsApp: wa.me/{phone}")
                    else:
                        st.warning("Enter phone number")
        with r2[2]:
            with st.popover("✈️", use_container_width=True, help="Telegram"):
                st.markdown(f"**Telegram Share**")
                tg_msg = f"🏛️ PPS ANANTAM — {page_name}\nLatest update from PPS Bitumen Dashboard"
                try:
                    from components.message_preview import render_msg_preview
                    render_msg_preview(tg_msg, channel="telegram")
                except Exception:
                    pass
                with st.expander("✏️ Edit message", expanded=False):
                    st.text_area("Message", value=tg_msg, key="_qa_tg_msg", height=100)
                if st.button("Send to All Chats", key="_qa_tg_send", type="primary", use_container_width=True):
                    try:
                        from telegram_engine import broadcast_message
                        results = broadcast_message(tg_msg)
                        sent = sum(1 for r in results if r.get("ok"))
                        st.success(f"Sent to {sent} chat(s)!")
                    except Exception:
                        st.info("Configure Telegram bot in System > Telegram Dashboard first")

        # ── Sticky Notes (News + Market) ──────────────────────────────────
        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
        _render_sticky_notes()

        # ── User Profile + Logout ─────────────────────────────────────────
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        _display_name = st.session_state.get("_auth_display", "Director")
        _role = st.session_state.get("_auth_role", "director")
        _role_label = {"director": "Director", "sales": "Sales", "operations": "Operations", "viewer": "Viewer"}.get(_role, _role.title())
        _role_color = {"director": "#6366F1", "sales": "#10B981", "operations": "#F59E0B", "viewer": "#94A3B8"}.get(_role, "#94A3B8")

        st.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;padding:14px 16px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
<div style="display:flex;align-items:center;gap:10px;">
<div style="width:36px;height:36px;background:linear-gradient(135deg,#4F46E5,#7C3AED);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1rem;color:#fff;font-weight:800;">{_display_name[0].upper()}</div>
<div>
<div style="font-size:0.8rem;font-weight:700;color:#0F172A;">{_display_name}</div>
<div style="font-size:0.6rem;color:{_role_color};font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">{_role_label}</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True, key="_sidebar_logout"):
            try:
                from role_engine import logout
                logout()
            except Exception:
                for k in ["_auth_user", "_auth_role", "_auth_username", "_auth_display", "_auth_last_activity"]:
                    st.session_state.pop(k, None)
            st.rerun()

    return current_page


def _render_sticky_notes():
    """Render market ticker + news cards in sidebar using minimalist light aesthetic."""

    # ── MARKET TICKER ──────────────────────────────────────────────────
    market_items = []
    try:
        hub_path = _ROOT / "hub_cache.json"
        if hub_path.exists():
            with open(hub_path, "r", encoding="utf-8") as f:
                hub = json.load(f)
            for c in hub.get("eia_crude", {}).get("data", []):
                if isinstance(c, dict) and c.get("benchmark") and c.get("price"):
                    market_items.append((c["benchmark"], f"${c['price']}", "#111827")) 
            for r in hub.get("frankfurter_fx", {}).get("data", []):
                if isinstance(r, dict) and "INR" in r.get("pair", "").upper():
                    market_items.append(("USD/INR", str(r.get("rate", "—")), "#059669")) # Emerald 600
    except Exception:
        pass
    try:
        lp_path = _ROOT / "live_prices.json"
        if lp_path.exists():
            with open(lp_path, "r", encoding="utf-8") as f:
                lp = json.load(f)
            vg30 = lp.get("DRUM_KANDLA_VG30", 0)
            if vg30:
                market_items.append(("VG30", f"\u20b9{vg30:,}", "var(--text-blue)"))
    except Exception:
        pass

    if market_items:
        rows_html = ""
        for label, value, color in market_items:
            rows_html += (
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:8px 0;border-bottom:1px solid #F3F4F6;">'
                f'<span style="color:var(--text-muted);font-size:0.75rem;font-weight:600;">{label}</span>'
                f'<span style="color:{color};font-size:0.95rem;font-weight:800;">{value}</span>'
                f'</div>'
            )
        st.markdown(
            '<div style="background:#FFFFFF; border-radius:12px;'
            'padding:20px;margin-bottom:24px;box-shadow:var(--shadow-sm); border:1px solid var(--border-subtle);">'
            '<div style="display:flex; align-items:center; gap:8px; font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;'
            'margin-bottom:12px;font-weight:800;">'
            '<div style="width:6px; height:6px; background:#10B981; border-radius:50%;"></div>'
            'LIVE MARKET</div>'
            + rows_html +
            '</div>',
            unsafe_allow_html=True,
        )

    # ── NEWS HEADLINES ──────────────────────────────────────────────────
    news_items = []
    try:
        news_path = _ROOT / "tbl_news_feed.json"
        if news_path.exists():
            with open(news_path, "r", encoding="utf-8") as f:
                all_news = json.load(f)
            seen = set()
            for n in reversed(all_news):
                h = n.get("headline", "")
                if h and h[:60] not in seen:
                    seen.add(h[:60])
                    news_items.append(n)
                if len(news_items) >= 3:
                    break
    except Exception:
        pass

    if news_items:
        cards_html = ""
        for i, n in enumerate(news_items):
            headline = n.get("headline", "")[:80] + "..." if len(n.get("headline", "")) > 80 else n.get("headline", "")
            src = n.get("publisher", n.get("source", ""))[:25]
            cards_html += (
                f'<div style="background:#FFFFFF;border:1px solid var(--border-subtle);'
                f'border-radius:8px;padding:12px;margin-bottom:10px; box-shadow:var(--shadow-sm);'
                f'transition: transform 0.2s ease, border-color 0.2s ease;" onmouseover="this.style.transform=\'translateY(-1px)\'; this.style.borderColor=\'var(--border-hover)\';" onmouseout="this.style.transform=\'translateY(0)\'; this.style.borderColor=\'var(--border-subtle)\';">'
                f'<div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">'
                f'<span style="font-size:0.8rem;">📰</span>'
                f'<span style="color:var(--text-blue);font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">{src}</span>'
                f'</div>'
                f'<div style="color:var(--text-main);font-size:0.75rem;font-weight:600;'
                f'line-height:1.4;word-wrap:break-word;">{headline}</div>'
                f'</div>'
            )

        st.markdown(
            '<div style="margin-bottom:12px;">'
            '<div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;'
            'margin-bottom:12px;font-weight:800;border-bottom:1px solid #E5E7EB;padding-bottom:8px;">LATEST INTEL</div>'
            + cards_html +
            '</div>',
            unsafe_allow_html=True,
        )
