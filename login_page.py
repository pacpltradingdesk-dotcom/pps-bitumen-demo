"""
PPS Anantam — Premium Login Page
=================================
Full-screen login with company branding. Works on both light and dark themes.
"""
import streamlit as st
from role_engine import login, _is_rate_limited, _failed_attempts


def render_login():
    """Render login page. Returns True if authenticated."""

    if st.session_state.get("_auth_user"):
        return True

    # ── Hide Streamlit chrome ──
    st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
footer { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding-top: 2rem !important; }
/* Fix helper text position so it doesn't overlap input */
div[data-testid="stForm"] .stTextInput div[data-testid="InputInstructions"] {
    position: relative !important;
    text-align: right !important;
    margin-top: 4px !important;
    font-size: 0.7rem !important;
    color: #94A3B8 !important;
}
</style>
""", unsafe_allow_html=True)

    # ── Center column ──
    _, col, _ = st.columns([1.3, 1, 1.3])

    with col:
        # Logo + branding using Streamlit components (no HTML overlap)
        st.markdown("""
<div style="text-align:center;padding:40px 0 20px;">
    <div style="width:72px;height:72px;background:linear-gradient(135deg,#4F46E5,#7C3AED);
                border-radius:18px;display:inline-flex;align-items:center;justify-content:center;
                font-size:2rem;margin-bottom:16px;box-shadow:0 8px 24px rgba(79,70,229,0.25);">🏛️</div>
    <div style="font-size:1.5rem;font-weight:800;color:#0F172A;">PPS Anantams</div>
    <div style="font-size:0.7rem;color:#94A3B8;margin-top:4px;
                letter-spacing:0.12em;text-transform:uppercase;">Enterprise Bitumen Desk</div>
    <div style="margin-top:20px;">
        <div style="font-size:1.05rem;font-weight:700;color:#334155;">Welcome Back</div>
        <div style="font-size:0.78rem;color:#94A3B8;margin-top:4px;">Sign in to access your dashboard</div>
    </div>
</div>
""", unsafe_allow_html=True)

        # Streamlit form (prevents rerun on each keystroke)
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            pin = st.text_input("Password / PIN", type="password", placeholder="Enter 4-digit PIN")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

        if submitted:
            uname = username.strip().lower()
            if not uname or not pin:
                st.error("Please enter username and PIN")
            elif _is_rate_limited(uname):
                st.error("Too many failed attempts. Please wait a few minutes before trying again.")
            elif login(uname, pin):
                st.rerun()
            else:
                st.error("Invalid username or PIN. Default: admin / 0000")

        # Footer
        st.markdown("""
<div style="text-align:center;margin-top:24px;">
<div style="font-size:0.6rem;color:#CBD5E1;line-height:1.8;">
PPS Anantams Corporation Pvt Ltd &bull; Vadodara, Gujarat &bull; v6.0<br>
Default login: <b>admin</b> / <b>0000</b>
</div>
</div>
""", unsafe_allow_html=True)

    return False
