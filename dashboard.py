"""
PPS Anantam — Bitumen Sales Dashboard
Coming Soon / Demo Preview
"""
import streamlit as st
import base64
import os

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PPS Anantam — Bitumen Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
# HIDE STREAMLIT DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    .stDeployButton {display: none;}
    .stApp {background: #0f172a;}

    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    [data-testid="stAppViewBlockContainer"] {
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGO HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def get_logo_base64():
    logo_path = os.path.join(os.path.dirname(__file__), "pps_logo_brand.jpg")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def render_login():
    logo_b64 = get_logo_base64()
    if logo_b64:
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="width:90px; height:90px; border-radius:20px; object-fit:cover; box-shadow: 0 8px 32px rgba(79, 70, 229, 0.3);">'
    else:
        logo_html = '<div style="width:90px; height:90px; border-radius:20px; background: linear-gradient(135deg, #4F46E5, #7C3AED); display:flex; align-items:center; justify-content:center; font-size:2.2rem; color:white; font-weight:900; box-shadow: 0 8px 32px rgba(79, 70, 229, 0.3);">PP</div>'

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

        .login-container {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0f172a;
            font-family: 'Inter', -apple-system, sans-serif;
            position: relative;
            overflow: hidden;
        }}

        .login-container::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image:
                linear-gradient(rgba(79, 70, 229, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(79, 70, 229, 0.03) 1px, transparent 1px);
            background-size: 60px 60px;
            animation: gridMove 20s linear infinite;
        }}

        @keyframes gridMove {{
            0% {{ transform: translate(0, 0); }}
            100% {{ transform: translate(60px, 60px); }}
        }}

        .login-container::after {{
            content: '';
            position: absolute;
            width: 400px; height: 400px;
            background: radial-gradient(circle, rgba(79, 70, 229, 0.15), transparent 70%);
            top: -100px; right: -100px;
            border-radius: 50%;
            animation: float 8s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translate(0, 0) scale(1); }}
            50% {{ transform: translate(-30px, 30px) scale(1.1); }}
        }}

        .login-card {{
            background: rgba(30, 41, 59, 0.8);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(79, 70, 229, 0.2);
            border-radius: 24px;
            padding: 48px 40px;
            width: 420px;
            max-width: 90vw;
            position: relative;
            z-index: 10;
            box-shadow: 0 24px 48px rgba(0, 0, 0, 0.4), 0 0 120px rgba(79, 70, 229, 0.1);
        }}

        .login-logo {{
            text-align: center;
            margin-bottom: 32px;
        }}

        .login-title {{
            text-align: center;
            color: #f8fafc;
            font-size: 1.6rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin: 16px 0 4px;
        }}

        .login-subtitle {{
            text-align: center;
            color: #94a3b8;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 36px;
        }}

        .login-badge {{
            display: inline-block;
            background: rgba(79, 70, 229, 0.15);
            color: #a5b4fc;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 20px;
            letter-spacing: 0.1em;
            border: 1px solid rgba(79, 70, 229, 0.3);
            margin-top: 8px;
        }}

        .login-footer {{
            text-align: center;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid rgba(148, 163, 184, 0.1);
        }}

        .login-footer-text {{
            color: #64748b;
            font-size: 0.75rem;
            font-weight: 500;
        }}

        .login-footer-company {{
            color: #94a3b8;
            font-size: 0.7rem;
            font-weight: 600;
            margin-top: 4px;
            letter-spacing: 0.05em;
        }}

        .login-gst {{
            display: inline-block;
            background: rgba(5, 150, 105, 0.1);
            color: #34d399;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 6px;
            margin-top: 8px;
            letter-spacing: 0.05em;
        }}

        .stTextInput > div > div > input {{
            background: rgba(15, 23, 42, 0.8) !important;
            border: 1px solid rgba(79, 70, 229, 0.3) !important;
            border-radius: 12px !important;
            color: #f8fafc !important;
            padding: 14px 16px !important;
            font-size: 1.1rem !important;
            font-family: 'Inter', monospace !important;
            letter-spacing: 0.3em !important;
            text-align: center !important;
            font-weight: 600 !important;
        }}

        .stTextInput > div > div > input:focus {{
            border-color: #4F46E5 !important;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2) !important;
        }}

        .stTextInput > div > div > input::placeholder {{
            color: #475569 !important;
            letter-spacing: 0.15em !important;
            font-weight: 400 !important;
        }}

        .stTextInput label {{
            color: #94a3b8 !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
        }}

        .stButton > button {{
            background: linear-gradient(135deg, #4F46E5, #7C3AED) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 14px 32px !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            width: 100% !important;
            letter-spacing: 0.05em !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 16px rgba(79, 70, 229, 0.3) !important;
            font-family: 'Inter', sans-serif !important;
        }}

        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 24px rgba(79, 70, 229, 0.4) !important;
        }}

        .stAlert {{
            background: rgba(239, 68, 68, 0.1) !important;
            border: 1px solid rgba(239, 68, 68, 0.3) !important;
            border-radius: 12px !important;
        }}

        div[data-testid="stForm"] {{
            border: none !important;
            padding: 0 !important;
        }}
    </style>

    <div class="login-container">
        <div class="login-card">
            <div class="login-logo">
                {logo_html}
                <div class="login-title">PPS Anantams</div>
                <div class="login-subtitle">Enterprise Bitumen Desk</div>
                <div class="login-badge">AI COMMANDER v6.1</div>
            </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=True):
        pin = st.text_input("Enter Access PIN", type="password", placeholder="* * * *", max_chars=6)
        submitted = st.form_submit_button("Access Dashboard")

        if submitted:
            if pin and len(pin) >= 4:
                st.session_state["authenticated"] = True
                st.rerun()
            elif pin:
                st.error("Invalid PIN. Please try again.")

    st.markdown("""
            <div class="login-footer">
                <div class="login-footer-text">Vadodara, Gujarat &bull; India</div>
                <div class="login-footer-company">PPS Anantams Corporation Pvt Ltd</div>
                <div class="login-gst">GST: 24AAHCV1611L2ZD</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PROCESSING / COMING SOON PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def render_coming_soon():
    logo_b64 = get_logo_base64()
    if logo_b64:
        logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="width:70px; height:70px; border-radius:16px; object-fit:cover; box-shadow: 0 4px 20px rgba(79, 70, 229, 0.3);">'
    else:
        logo_html = '<div style="width:70px; height:70px; border-radius:16px; background: linear-gradient(135deg, #4F46E5, #7C3AED); display:flex; align-items:center; justify-content:center; font-size:1.8rem; color:white; font-weight:900;">PP</div>'

    messages = [
        "Initializing AI Commander...",
        "Connecting to Market Data APIs...",
        "Loading 25,000+ CRM Contacts...",
        "Syncing Brent Crude & VG30 Prices...",
        "Calibrating Price Prediction Engine...",
        "Loading Refinery Supply Data...",
        "Processing Market Intelligence Signals...",
        "Connecting to News Aggregator...",
        "Loading Logistics & Port Data...",
        "Syncing NHAI Tender Pipeline...",
        "Initializing Communication Hub...",
        "Loading Financial Intelligence...",
        "Warming up ML Forecast Models...",
        "Connecting to Telegram Channels...",
        "Loading Competitor Price Data...",
        "Almost Ready — Final Checks...",
    ]

    import json
    messages_js = json.dumps(messages)

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

        .cs-wrapper {{
            min-height: 100vh;
            background: #0f172a;
            font-family: 'Inter', -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }}

        .cs-wrapper::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image:
                linear-gradient(rgba(79, 70, 229, 0.04) 1px, transparent 1px),
                linear-gradient(90deg, rgba(79, 70, 229, 0.04) 1px, transparent 1px);
            background-size: 50px 50px;
            animation: gridMove 25s linear infinite;
        }}

        @keyframes gridMove {{
            0% {{ transform: translate(0, 0); }}
            100% {{ transform: translate(50px, 50px); }}
        }}

        .cs-orb-1 {{
            position: absolute;
            width: 500px; height: 500px;
            background: radial-gradient(circle, rgba(79, 70, 229, 0.12), transparent 70%);
            top: -150px; left: -100px;
            border-radius: 50%;
            animation: orbFloat1 10s ease-in-out infinite;
        }}

        .cs-orb-2 {{
            position: absolute;
            width: 400px; height: 400px;
            background: radial-gradient(circle, rgba(124, 58, 237, 0.1), transparent 70%);
            bottom: -100px; right: -80px;
            border-radius: 50%;
            animation: orbFloat2 12s ease-in-out infinite;
        }}

        @keyframes orbFloat1 {{
            0%, 100% {{ transform: translate(0, 0) scale(1); }}
            50% {{ transform: translate(40px, 20px) scale(1.15); }}
        }}

        @keyframes orbFloat2 {{
            0%, 100% {{ transform: translate(0, 0) scale(1); }}
            50% {{ transform: translate(-30px, -20px) scale(1.1); }}
        }}

        .cs-content {{
            position: relative;
            z-index: 10;
            text-align: center;
            max-width: 600px;
            padding: 40px;
        }}

        .cs-logo {{
            margin-bottom: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
        }}

        .cs-logo-text {{ text-align: left; }}

        .cs-logo-title {{
            color: #f8fafc;
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}

        .cs-logo-sub {{
            color: #64748b;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}

        .cs-spinner-box {{
            margin: 40px auto;
            position: relative;
            width: 120px;
            height: 120px;
        }}

        .cs-spinner {{
            width: 120px; height: 120px;
            border-radius: 50%;
            border: 3px solid rgba(79, 70, 229, 0.1);
            border-top: 3px solid #4F46E5;
            animation: spin 1.2s linear infinite;
            position: absolute;
        }}

        .cs-spinner-2 {{
            width: 90px; height: 90px;
            border-radius: 50%;
            border: 3px solid rgba(124, 58, 237, 0.1);
            border-top: 3px solid #7C3AED;
            animation: spin 1.8s linear infinite reverse;
            position: absolute;
            top: 15px; left: 15px;
        }}

        .cs-spinner-3 {{
            width: 60px; height: 60px;
            border-radius: 50%;
            border: 3px solid rgba(99, 102, 241, 0.1);
            border-top: 3px solid #6366F1;
            animation: spin 0.9s linear infinite;
            position: absolute;
            top: 30px; left: 30px;
        }}

        .cs-spinner-dot {{
            width: 12px; height: 12px;
            background: #4F46E5;
            border-radius: 50%;
            position: absolute;
            top: 54px; left: 54px;
            box-shadow: 0 0 20px rgba(79, 70, 229, 0.6);
            animation: pulse 2s ease-in-out infinite;
        }}

        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.3); opacity: 0.7; }}
        }}

        .cs-status {{
            color: #94a3b8;
            font-size: 0.85rem;
            font-weight: 500;
            margin-top: 24px;
            min-height: 24px;
        }}

        .cs-status-line {{
            animation: fadeInUp 0.5s ease forwards;
            opacity: 0;
        }}

        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .cs-progress-track {{
            width: 300px;
            height: 4px;
            background: rgba(79, 70, 229, 0.1);
            border-radius: 4px;
            margin: 32px auto 0;
            overflow: hidden;
        }}

        .cs-progress-bar {{
            height: 100%;
            width: 30%;
            background: linear-gradient(90deg, #4F46E5, #7C3AED, #4F46E5);
            background-size: 200% 100%;
            border-radius: 4px;
            animation: progressSlide 2s ease-in-out infinite;
        }}

        @keyframes progressSlide {{
            0% {{ transform: translateX(-100%); background-position: 0% 0%; }}
            50% {{ background-position: 100% 0%; }}
            100% {{ transform: translateX(400%); background-position: 0% 0%; }}
        }}

        .cs-badge {{
            display: inline-block;
            background: rgba(79, 70, 229, 0.15);
            color: #a5b4fc;
            font-size: 0.7rem;
            font-weight: 800;
            padding: 6px 20px;
            border-radius: 24px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            border: 1px solid rgba(79, 70, 229, 0.3);
            margin-top: 40px;
            animation: badgePulse 3s ease-in-out infinite;
        }}

        @keyframes badgePulse {{
            0%, 100% {{ box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.2); }}
            50% {{ box-shadow: 0 0 0 12px rgba(79, 70, 229, 0); }}
        }}

        .cs-features {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-top: 48px;
            max-width: 500px;
        }}

        .cs-feature {{
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(79, 70, 229, 0.1);
            border-radius: 12px;
            padding: 16px 12px;
            text-align: center;
        }}

        .cs-feature-icon {{ font-size: 1.5rem; margin-bottom: 6px; }}

        .cs-feature-label {{
            color: #64748b;
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .cs-footer {{
            position: absolute;
            bottom: 24px;
            left: 0; right: 0;
            text-align: center;
            z-index: 10;
        }}

        .cs-footer-text {{
            color: #334155;
            font-size: 0.7rem;
            font-weight: 500;
        }}

        .cs-footer-ver {{
            display: inline-block;
            background: rgba(30, 41, 59, 0.5);
            color: #475569;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 6px;
            margin-top: 4px;
            border: 1px solid rgba(51, 65, 85, 0.3);
        }}

        .cs-modules {{
            display: flex;
            gap: 8px;
            justify-content: center;
            margin-top: 48px;
        }}

        .cs-module-dot {{
            width: 8px; height: 8px;
            border-radius: 50%;
            animation: dotPulse 3s ease-in-out infinite;
        }}

        .cs-module-dot:nth-child(1) {{ background: #4F46E5; animation-delay: 0s; }}
        .cs-module-dot:nth-child(2) {{ background: #7C3AED; animation-delay: 0.3s; }}
        .cs-module-dot:nth-child(3) {{ background: #06b6d4; animation-delay: 0.6s; }}
        .cs-module-dot:nth-child(4) {{ background: #10b981; animation-delay: 0.9s; }}
        .cs-module-dot:nth-child(5) {{ background: #f59e0b; animation-delay: 1.2s; }}
        .cs-module-dot:nth-child(6) {{ background: #ef4444; animation-delay: 1.5s; }}

        @keyframes dotPulse {{
            0%, 100% {{ opacity: 0.3; transform: scale(1); }}
            50% {{ opacity: 1; transform: scale(1.5); }}
        }}
    </style>

    <div class="cs-wrapper">
        <div class="cs-orb-1"></div>
        <div class="cs-orb-2"></div>

        <div class="cs-content">
            <div class="cs-logo">
                {logo_html}
                <div class="cs-logo-text">
                    <div class="cs-logo-title">PPS Anantams</div>
                    <div class="cs-logo-sub">Enterprise Bitumen Desk</div>
                </div>
            </div>

            <div class="cs-spinner-box">
                <div class="cs-spinner"></div>
                <div class="cs-spinner-2"></div>
                <div class="cs-spinner-3"></div>
                <div class="cs-spinner-dot"></div>
            </div>

            <div class="cs-status" id="cs-status-msg">
                <div class="cs-status-line" style="animation-delay: 0s;">Initializing AI Commander...</div>
            </div>

            <div class="cs-progress-track">
                <div class="cs-progress-bar"></div>
            </div>

            <div class="cs-modules">
                <div class="cs-module-dot"></div>
                <div class="cs-module-dot"></div>
                <div class="cs-module-dot"></div>
                <div class="cs-module-dot"></div>
                <div class="cs-module-dot"></div>
                <div class="cs-module-dot"></div>
            </div>

            <div class="cs-badge">Coming Soon</div>

            <div class="cs-features">
                <div class="cs-feature">
                    <div class="cs-feature-icon">📊</div>
                    <div class="cs-feature-label">Live Market</div>
                </div>
                <div class="cs-feature">
                    <div class="cs-feature-icon">🧮</div>
                    <div class="cs-feature-label">Smart Pricing</div>
                </div>
                <div class="cs-feature">
                    <div class="cs-feature-icon">🤖</div>
                    <div class="cs-feature-label">AI Signals</div>
                </div>
            </div>
        </div>

        <div class="cs-footer">
            <div class="cs-footer-text">PPS Anantams Corporation Pvt Ltd &bull; Vadodara, Gujarat</div>
            <div class="cs-footer-ver">v6.1 &bull; 2026</div>
        </div>
    </div>

    <script>
        const messages = {messages_js};
        let idx = 0;
        function cycleMsg() {{
            const el = document.getElementById('cs-status-msg');
            if (el) {{
                el.innerHTML = '<div class="cs-status-line" style="animation-delay:0s;">' + messages[idx] + '</div>';
                idx = (idx + 1) % messages.length;
            }}
        }}
        setInterval(cycleMsg, 3000);
    </script>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if not st.session_state.get("authenticated"):
    render_login()
else:
    render_coming_soon()
