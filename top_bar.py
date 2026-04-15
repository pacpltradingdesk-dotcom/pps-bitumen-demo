"""
PPS Anantam — Top Navigation Bar v6.0 (Clean SaaS Edition)
White pill-shaped branded header with logo + Streamlit button navigation.
"""
import streamlit as st
import base64
from nav_config import MODULE_NAV, TOPBAR_MODULES, OVERFLOW_MODULES
import json
from pathlib import Path

_ROOT = Path(__file__).parent


def _get_logo_b64():
    """Load logo as base64 string (cached in session)."""
    if "_logo_b64" not in st.session_state:
        logo_path = _ROOT / "pps_logo_brand.jpg"
        if logo_path.exists():
            with open(logo_path, "rb") as f:
                st.session_state["_logo_b64"] = base64.b64encode(f.read()).decode()
        else:
            st.session_state["_logo_b64"] = ""
    return st.session_state["_logo_b64"]


def render_top_bar() -> None:
    """Render sleek light pill header with logo + clickable module navigation."""

    current_module = st.session_state.get("_active_module", "\U0001f3e0 Home")
    current_label = MODULE_NAV.get(current_module, {}).get("label", "Home")
    logo_b64 = _get_logo_b64()

    # 1. Clean white header with logo (Crisp Pill Design)
    logo_html = (f'<img src="data:image/jpeg;base64,{logo_b64}" '
                  'style="height:40px;border-radius:10px;background:#FFF;'
                  'margin-right:16px;box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #E5E7EB;" alt="PPS">'
                  if logo_b64 else '')

    st.markdown(
        '<style>'
        '@keyframes ping { 75%, 100% { transform: scale(1.5); opacity: 0; } }'
        '.pps-topbar { background: rgba(255,255,255,0.9); backdrop-filter: blur(16px); '
        '-webkit-backdrop-filter: blur(16px); padding:16px 32px; border-radius: 100px; '
        'margin-bottom:24px; margin-top: 8px; border: 1px solid #E5E7EB; '
        'display:flex; align-items:center; justify-content:space-between; '
        'box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -2px rgba(0,0,0,0.025); '
        'transition: transform 0.2s ease, box-shadow 0.2s ease; }'
        '.pps-topbar:hover { transform: translateY(-2px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.05); }'
        '.pps-topbar-right { text-align:right; display:flex; flex-direction:column; align-items:flex-end; gap:2px; }'
        '.pps-topbar-subtitle { color:var(--text-muted); font-size:0.75rem; font-weight:500; letter-spacing:0.02em; margin-top:2px; }'
        '.pps-topbar-location { color:var(--text-muted); font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; }'
        '@media (max-width: 768px) {'
        '  .pps-topbar { padding:10px 16px; border-radius:16px; margin-bottom:12px; margin-top:4px; }'
        '  .pps-topbar:hover { transform:none; }'
        '  .pps-topbar-subtitle, .pps-topbar-location { display:none; }'
        '  .pps-topbar img { height:32px !important; margin-right:10px !important; }'
        '  .pps-topbar .pps-brand-name { font-size:1rem !important; }'
        '  .pps-topbar .pps-badge { display:none; }'
        '}'
        '@media (max-width: 480px) {'
        '  .pps-topbar { padding:8px 12px; border-radius:12px; margin-bottom:8px; }'
        '  .pps-topbar img { height:28px !important; margin-right:8px !important; }'
        '  .pps-topbar .pps-brand-name { font-size:0.9rem !important; }'
        '  .pps-topbar .pps-live-market { font-size:0.75rem !important; }'
        '}'
        '</style>'

        '<div class="pps-topbar">'
        '<div style="display:flex;align-items:center;">'
        + logo_html +
        '<div>'
        '<div style="display:flex; align-items:center; gap:8px;">'
        '<span class="pps-brand-name" style="color:var(--text-main);font-weight:800;font-size:1.2rem;letter-spacing:-0.03em;">'
        'PPS Anantams</span>'
        ''
        '</div>'
        '<div class="pps-topbar-subtitle">ENTERPRISE BITUMEN DESK</div>'
        '</div></div>'

        '<div class="pps-topbar-right">'
        '<div class="pps-topbar-location">Vadodara, GJ \u2022 IN</div>'
        '<div class="pps-live-market" style="color:var(--text-main);font-size:0.85rem;font-weight:700;">Live Market <div style="display:inline-block; width:8px; height:8px; background:#10B981; border-radius:50%; margin-left:4px; box-shadow:0 0 0 3px #D1FAE5; animation: ping 2s cubic-bezier(0,0,0.2,1) infinite;"></div></div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 2. Module navigation (native Streamlit buttons — responsive via CSS)
    # Inject mobile CSS for nav buttons
    st.markdown("""<style>
    /* Mobile: nav buttons wrap into 2-col grid */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > .stButton) {
            flex-wrap: wrap !important;
            gap: 4px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > .stButton) > div[data-testid="column"] {
            flex: 0 0 calc(50% - 4px) !important;
            min-width: calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > .stButton) > div[data-testid="column"] .stButton > button {
            font-size: 0.72rem !important;
            padding: 0.4rem 0.3rem !important;
            min-height: 40px !important;
        }
    }
    @media (max-width: 480px) {
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"] > div > div > .stButton) > div[data-testid="column"] .stButton > button {
            font-size: 0.68rem !important;
            padding: 0.35rem 0.2rem !important;
        }
    }
    </style>""", unsafe_allow_html=True)
    num_modules = len(TOPBAR_MODULES)
    if OVERFLOW_MODULES:
        cols = st.columns(num_modules + 1)  # +1 for More
    else:
        cols = st.columns(num_modules)

    for i, mod_key in enumerate(TOPBAR_MODULES):
        mod = MODULE_NAV.get(mod_key, {})
        is_active = (mod_key == current_module)
        with cols[i]:
            if st.button(
                mod.get("label", ""),
                key=f"_tnav_{i}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["_active_module"] = mod_key
                st.session_state["selected_page"] = mod["tabs"][0]["page"]
                st.rerun()

    # More button (only if overflow modules exist)
    if OVERFLOW_MODULES:
        with cols[num_modules]:
            more_active = current_module in OVERFLOW_MODULES
            if st.button(
                "More \u25be" if not st.session_state.get("_more_open") else "More \u25b4",
                key="_tnav_more",
                use_container_width=True,
                type="primary" if more_active else "secondary",
            ):
                st.session_state["_more_open"] = not st.session_state.get("_more_open", False)
                st.rerun()

        # Overflow row (only when More is clicked)
        if st.session_state.get("_more_open", False):
            st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)
            ov_cols = st.columns(len(OVERFLOW_MODULES))
            for j, mod_key in enumerate(OVERFLOW_MODULES):
                mod = MODULE_NAV.get(mod_key, {})
                with ov_cols[j]:
                    if st.button(
                        f"{mod.get('icon','')} {mod.get('label','')}",
                        key=f"_tnav_ov_{j}",
                        use_container_width=True,
                        type="primary" if mod_key == current_module else "secondary",
                    ):
                        st.session_state["_active_module"] = mod_key
                        st.session_state["selected_page"] = mod["tabs"][0]["page"]
                        st.session_state["_more_open"] = False
                        st.rerun()
            st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)

    # ── Compact user strip (top-right) with logout ─────────────────────────
    if st.session_state.get("_auth_user"):
        _name = st.session_state.get("_auth_display", "User")
        _role = st.session_state.get("_auth_role", "viewer").title()
        _spacer, _user_col, _logout_col = st.columns([6, 2, 1])
        with _user_col:
            st.markdown(
                f'<div style="text-align:right;padding-top:6px;font-size:0.78rem;'
                f'color:#475569;"><b style="color:#0F172A;">{_name}</b>'
                f' <span style="color:#94A3B8;">·</span> '
                f'<span style="color:#6366F1;font-weight:600;">{_role}</span></div>',
                unsafe_allow_html=True,
            )
        with _logout_col:
            if st.button("🚪 Logout", key="_topbar_logout",
                         use_container_width=True,
                         help="Session khatam karo"):
                try:
                    from role_engine import logout
                    logout()
                except Exception:
                    for k in ["_auth_user", "_auth_role", "_auth_username",
                              "_auth_display", "_auth_last_activity"]:
                        st.session_state.pop(k, None)
                st.rerun()

    # Phase 5 — Power Stats ribbon (global, under top bar)
    try:
        from components.power_stats_ribbon import render_power_stats_ribbon
        render_power_stats_ribbon()
    except Exception:
        pass
