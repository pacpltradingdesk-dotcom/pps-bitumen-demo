"""
PPS Anantam — Premium Login Page
=================================
Full-screen animated login with company branding.
"""
import streamlit as st
from role_engine import login, _is_rate_limited


def render_login():
    """Render full-screen premium login. Returns True if authenticated."""

    # Already logged in?
    if st.session_state.get("_auth_user"):
        return True

    # ── Hide all Streamlit chrome + animated background ──
    st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
footer { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }
section.main .block-container {
    padding: 0 !important; max-width: 100% !important;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh;
}
/* Animated gradient background on body */
section.main {
    background: linear-gradient(-45deg, #0F172A, #1E1B4B, #312E81, #1E3A5F, #14532D) !important;
    background-size: 400% 400% !important;
    animation: gradShift 15s ease infinite !important;
    min-height: 100vh !important;
}
@keyframes gradShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
/* Style ALL inputs on this page */
section.main input {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 12px !important;
    color: #fff !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
}
section.main input:focus {
    border-color: #818CF8 !important;
    box-shadow: 0 0 0 3px rgba(129,140,248,0.25) !important;
}
section.main input::placeholder { color: rgba(255,255,255,0.35) !important; }
section.main label, section.main .stTextInput > label {
    color: rgba(255,255,255,0.7) !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
}
/* Primary button */
section.main button[kind="primary"],
section.main button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #4F46E5, #7C3AED) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #fff !important;
    box-shadow: 0 4px 20px rgba(79,70,229,0.4) !important;
    transition: all 0.2s !important;
    letter-spacing: 0.02em;
}
section.main button[kind="primary"]:hover,
section.main button[data-testid="baseButton-primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(79,70,229,0.5) !important;
}
/* Error/success messages */
section.main div[data-testid="stAlert"] {
    background: rgba(255,255,255,0.05) !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}
</style>
""", unsafe_allow_html=True)

    # ── Center column for login card ──
    _, col, _ = st.columns([1.2, 1, 1.2])

    with col:
        # Glass card header (HTML)
        st.markdown("""
<div style="text-align:center;margin-bottom:8px;animation:cardIn 0.6s cubic-bezier(0.34,1.56,0.64,1);">
    <div style="width:72px;height:72px;background:linear-gradient(135deg,#4F46E5,#7C3AED);
                border-radius:18px;display:inline-flex;align-items:center;justify-content:center;
                font-size:2rem;margin-bottom:16px;box-shadow:0 8px 24px rgba(79,70,229,0.35);">🏛️</div>
    <div style="font-size:1.4rem;font-weight:800;color:#fff;letter-spacing:0.02em;">PPS Anantams</div>
    <div style="font-size:0.72rem;color:rgba(255,255,255,0.45);margin-top:4px;
                letter-spacing:0.12em;text-transform:uppercase;">Enterprise Bitumen Desk</div>
    <div style="margin-top:24px;">
        <div style="font-size:1.1rem;font-weight:700;color:#fff;">Welcome Back</div>
        <div style="font-size:0.78rem;color:rgba(255,255,255,0.4);margin-top:4px;">Sign in to access your dashboard</div>
    </div>
</div>
<style>
@keyframes cardIn {
    from { opacity:0; transform:translateY(30px) scale(0.95); }
    to { opacity:1; transform:translateY(0) scale(1); }
}
</style>
""", unsafe_allow_html=True)

        # Streamlit form inputs
        username = st.text_input("Username", key="_login_user", placeholder="Enter username")
        pin = st.text_input("Password / PIN", type="password", key="_login_pin", placeholder="Enter PIN")

        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

        if st.button("Sign In", type="primary", use_container_width=True, key="_login_btn"):
            uname = username.strip().lower()
            if not uname or not pin:
                st.error("Please enter username and PIN")
            elif _is_rate_limited(uname):
                st.error("Too many failed attempts. Wait 5 minutes.")
            elif login(username, pin):
                st.rerun()
            else:
                st.error("Invalid username or PIN")

        # Footer hint
        st.markdown("""
<div style="text-align:center;margin-top:28px;">
<div style="font-size:0.6rem;color:rgba(255,255,255,0.2);line-height:1.8;">
PPS Anantams Corporation Pvt Ltd &bull; Vadodara, Gujarat &bull; v6.0<br>
Default: admin / 0000
</div>
</div>
""", unsafe_allow_html=True)

    return False
