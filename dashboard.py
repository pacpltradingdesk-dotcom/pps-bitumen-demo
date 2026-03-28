"""
PPS Anantam — Bitumen Sales Dashboard v6.1
Login → Command Center (real) → Click anything → Processing animation
"""

import streamlit as st
import datetime
import json
import base64
import os

# Navigation
from nav_config import MODULE_NAV, TOPBAR_MODULES, OVERFLOW_MODULES, PAGE_REDIRECTS
from nav_config import get_tabs, get_module_for_page, get_feature_idx_for_page, resolve_page
from theme import inject_theme
from top_bar import render_top_bar
from subtab_bar import render_sidebar_features

try:
    from pdf_export_bar import render_export_bar, inject_print_css
    _PDF_BAR_OK = True
except Exception:
    _PDF_BAR_OK = False
    def render_export_bar(*a, **kw): pass
    def inject_print_css(): pass

_CONFIDENCE_OK = False
def render_confidence_bar(*a, **kw): pass
def render_data_health_card(*a, **kw): pass
try:
    from data_confidence_engine import render_confidence_bar, render_data_health_card
    _CONFIDENCE_OK = True
except Exception:
    pass

try:
    from role_engine import render_login_form, get_current_role, check_role, init_roles
    init_roles()
    _ROLE_OK = True
except Exception:
    _ROLE_OK = False
    def render_login_form(): return True
    def get_current_role(): return "admin"
    def check_role(r): return True


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE STARTUP
# ═══════════════════════════════════════════════════════════════════════════════
def _init_engines():
    if st.session_state.get("_engines_started"):
        return
    for mod, fn in [
        ("api_manager", lambda m: (m.init_system(), m.start_auto_health())),
        ("sre_engine", lambda m: (m.init_sre(), m.start_sre_background(interval_min=15))),
        ("api_hub_engine", lambda m: (m.init_hub(), m.start_hub_scheduler(interval_min=60))),
        ("sync_engine", lambda m: m.start_sync_scheduler(interval_minutes=60)),
        ("email_engine", lambda m: m.start_email_scheduler()),
        ("whatsapp_engine", lambda m: m.start_whatsapp_scheduler()),
        ("port_tracker_engine", lambda m: m.init_port_tracker()),
        ("directory_engine", lambda m: m.init_directory()),
    ]:
        try:
            fn(__import__(mod))
        except Exception:
            pass
    try:
        from resilience_manager import HeartbeatMonitor
        HeartbeatMonitor.start_checker()
    except Exception:
        pass
    st.session_state["_engines_started"] = True


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PPS Anantam — Bitumen Dashboard v6.1",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN GATE
# ═══════════════════════════════════════════════════════════════════════════════
from login_page import render_login
if not render_login():
    st.stop()

_init_engines()

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "🎯 Command Center"
if "_active_module" not in st.session_state:
    st.session_state["_active_module"] = st.session_state.get("selected_module", "📊 Price & Info")


# ═══════════════════════════════════════════════════════════════════════════════
# PROCESSING ANIMATION (shown for ALL pages except Command Center)
# ═══════════════════════════════════════════════════════════════════════════════
PROCESSING_HTML = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
.px{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:72vh;font-family:'Inter',sans-serif;position:relative;overflow:hidden}
.px-bg{position:absolute;top:0;left:0;right:0;bottom:0;background-image:linear-gradient(rgba(79,70,229,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(79,70,229,0.03) 1px,transparent 1px);background-size:50px 50px;animation:px-grid 20s linear infinite;pointer-events:none}
@keyframes px-grid{to{transform:translate(50px,50px)}}
.px-orb1{position:absolute;width:350px;height:350px;background:radial-gradient(circle,rgba(79,70,229,0.1),transparent 70%);top:-80px;left:-60px;border-radius:50%;animation:px-ob 10s ease-in-out infinite;pointer-events:none}
.px-orb2{position:absolute;width:300px;height:300px;background:radial-gradient(circle,rgba(124,58,237,0.08),transparent 70%);bottom:-80px;right:-60px;border-radius:50%;animation:px-ob 12s ease-in-out infinite reverse;pointer-events:none}
@keyframes px-ob{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(30px,20px) scale(1.1)}}
.px-c{position:relative;z-index:10;text-align:center}

/* Robot Character */
.robot-wrap{margin:0 auto 24px;width:120px;height:140px;position:relative}
.robot-head{width:70px;height:56px;background:linear-gradient(135deg,#4F46E5,#7C3AED);border-radius:16px 16px 12px 12px;position:absolute;top:10px;left:25px;box-shadow:0 4px 20px rgba(79,70,229,0.4)}
.robot-eye{width:12px;height:12px;background:#fff;border-radius:50%;position:absolute;top:20px;animation:px-blink 4s ease-in-out infinite}
.robot-eye.l{left:14px}.robot-eye.r{right:14px}
.robot-eye::after{content:'';width:6px;height:6px;background:#0f172a;border-radius:50%;position:absolute;top:3px;left:3px}
@keyframes px-blink{0%,45%,55%,100%{transform:scaleY(1)}50%{transform:scaleY(0.1)}}
.robot-antenna{width:4px;height:16px;background:#7C3AED;position:absolute;top:-4px;left:33px;border-radius:2px}
.robot-antenna::after{content:'';width:10px;height:10px;background:#4F46E5;border-radius:50%;position:absolute;top:-8px;left:-3px;animation:px-glow 2s ease-in-out infinite;box-shadow:0 0 12px rgba(79,70,229,0.8)}
@keyframes px-glow{0%,100%{box-shadow:0 0 8px rgba(79,70,229,0.6);transform:scale(1)}50%{box-shadow:0 0 20px rgba(79,70,229,1);transform:scale(1.2)}}
.robot-mouth{width:20px;height:3px;background:rgba(255,255,255,0.6);border-radius:2px;position:absolute;bottom:10px;left:25px;animation:px-talk 2s steps(3) infinite}
@keyframes px-talk{0%,100%{width:20px}33%{width:14px}66%{width:24px}}
.robot-body{width:56px;height:44px;background:linear-gradient(180deg,#4338CA,#3730A3);border-radius:8px 8px 12px 12px;position:absolute;top:70px;left:32px;box-shadow:0 4px 16px rgba(67,56,202,0.3)}
.robot-chest{width:24px;height:24px;border:2px solid rgba(255,255,255,0.2);border-radius:6px;position:absolute;top:8px;left:14px}
.robot-chest::after{content:'';width:8px;height:8px;background:#34d399;border-radius:50%;position:absolute;top:6px;left:6px;animation:px-pulse 1.5s ease-in-out infinite}
@keyframes px-pulse{0%,100%{opacity:1;box-shadow:0 0 6px #34d399}50%{opacity:0.5;box-shadow:0 0 16px #34d399}}
.robot-arm{width:10px;height:32px;background:#4338CA;border-radius:6px;position:absolute;top:74px;animation:px-wave 3s ease-in-out infinite}
.robot-arm.l{left:18px;transform-origin:top center;animation-name:px-wave-l}
.robot-arm.r{right:18px;transform-origin:top center;animation-name:px-wave-r}
@keyframes px-wave-l{0%,100%{transform:rotate(-5deg)}50%{transform:rotate(10deg)}}
@keyframes px-wave-r{0%,100%{transform:rotate(5deg)}50%{transform:rotate(-10deg)}}
.robot-leg{width:14px;height:18px;background:#3730A3;border-radius:4px 4px 8px 8px;position:absolute;top:116px}
.robot-leg.l{left:34px}.robot-leg.r{right:34px}

/* Scan beam */
.px-scan{width:100px;height:2px;background:linear-gradient(90deg,transparent,#4F46E5,transparent);position:absolute;top:10px;left:10px;animation:px-scanmove 2.5s ease-in-out infinite;opacity:0.7;border-radius:2px;box-shadow:0 0 10px rgba(79,70,229,0.5)}
@keyframes px-scanmove{0%{top:10px;opacity:0}10%{opacity:0.7}90%{opacity:0.7}100%{top:130px;opacity:0}}

/* Data particles */
.px-particles{position:absolute;width:120px;height:140px;top:0;left:0}
.px-p{position:absolute;width:3px;height:3px;background:#7C3AED;border-radius:50%;opacity:0;animation:px-float 3s ease-in-out infinite}
.px-p:nth-child(1){left:10px;top:30px;animation-delay:0s}.px-p:nth-child(2){right:10px;top:50px;animation-delay:0.5s}
.px-p:nth-child(3){left:5px;top:80px;animation-delay:1s}.px-p:nth-child(4){right:5px;top:20px;animation-delay:1.5s}
.px-p:nth-child(5){left:50px;top:5px;animation-delay:0.7s}.px-p:nth-child(6){right:15px;top:100px;animation-delay:2s}
@keyframes px-float{0%{opacity:0;transform:translateY(0) scale(0)}30%{opacity:1;transform:translateY(-10px) scale(1)}70%{opacity:0.8}100%{opacity:0;transform:translateY(-40px) scale(0)}}

.px-title{color:#f8fafc;font-size:1.1rem;font-weight:800;letter-spacing:-0.02em;margin-bottom:4px}
.px-sub{color:#64748b;font-size:0.7rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:28px}

.px-msg{color:#94a3b8;font-size:0.82rem;font-weight:500;min-height:22px}
.px-msg-line{animation:px-fadein 0.5s ease forwards;opacity:0}
@keyframes px-fadein{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}

.px-track{width:220px;height:3px;background:rgba(79,70,229,0.1);border-radius:3px;margin:20px auto 0;overflow:hidden}
.px-bar{height:100%;width:30%;background:linear-gradient(90deg,#4F46E5,#7C3AED,#4F46E5);border-radius:3px;animation:px-slide 2s ease-in-out infinite}
@keyframes px-slide{0%{transform:translateX(-100%)}100%{transform:translateX(400%)}}

.px-dots{display:flex;gap:6px;justify-content:center;margin-top:24px}
.px-dt{width:6px;height:6px;border-radius:50%;animation:px-dp 3s ease-in-out infinite}
.px-dt:nth-child(1){background:#4F46E5;animation-delay:0s}.px-dt:nth-child(2){background:#7C3AED;animation-delay:0.3s}
.px-dt:nth-child(3){background:#06b6d4;animation-delay:0.6s}.px-dt:nth-child(4){background:#10b981;animation-delay:0.9s}
.px-dt:nth-child(5){background:#f59e0b;animation-delay:1.2s}.px-dt:nth-child(6){background:#ef4444;animation-delay:1.5s}
@keyframes px-dp{0%,100%{opacity:0.3;transform:scale(1)}50%{opacity:1;transform:scale(1.5)}}
</style>

<div class="px">
  <div class="px-bg"></div>
  <div class="px-orb1"></div>
  <div class="px-orb2"></div>
  <div class="px-c">
    <div class="robot-wrap">
      <div class="robot-antenna"></div>
      <div class="robot-head">
        <div class="robot-eye l"></div>
        <div class="robot-eye r"></div>
        <div class="robot-mouth"></div>
      </div>
      <div class="robot-arm l"></div>
      <div class="robot-body"><div class="robot-chest"></div></div>
      <div class="robot-arm r"></div>
      <div class="robot-leg l"></div>
      <div class="robot-leg r"></div>
      <div class="px-scan"></div>
      <div class="px-particles">
        <div class="px-p"></div><div class="px-p"></div><div class="px-p"></div>
        <div class="px-p"></div><div class="px-p"></div><div class="px-p"></div>
      </div>
    </div>

    <div class="px-title">PPS Anantams</div>
    <div class="px-sub">AI Commander Processing</div>

    <div class="px-msg" id="px-msg">
      <div class="px-msg-line">Initializing AI Commander...</div>
    </div>

    <div class="px-track"><div class="px-bar"></div></div>

    <div class="px-dots">
      <div class="px-dt"></div><div class="px-dt"></div><div class="px-dt"></div>
      <div class="px-dt"></div><div class="px-dt"></div><div class="px-dt"></div>
    </div>
  </div>
</div>

<script>
var pxMsgs=["Initializing AI Commander...","Connecting to Market Data APIs...","Loading 25,000+ CRM Contacts...","Syncing Brent Crude & VG30 Prices...","Calibrating Price Prediction Engine...","Loading Refinery Supply Data...","Processing Market Intelligence Signals...","Connecting to News Aggregator...","Loading Logistics & Port Data...","Syncing NHAI Tender Pipeline...","Initializing Communication Hub...","Loading Financial Intelligence...","Warming up ML Forecast Models...","Connecting to Telegram Channels...","Loading Competitor Price Data...","Almost Ready — Final Checks..."];
var pxI=0;
setInterval(function(){var e=document.getElementById("px-msg");if(e){e.innerHTML='<div class="px-msg-line">'+pxMsgs[pxI]+'</div>';pxI=(pxI+1)%pxMsgs.length;}},3000);
</script>
"""

def render_processing():
    import streamlit.components.v1 as components
    components.html(PROCESSING_HTML, height=700, scrolling=False)


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER — real page, full render
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.get("selected_page") == "🎯 Command Center":
    render_sidebar_features("📊 Price & Info")
    try:
        from pages.home.command_center import render as render_cc
        render_cc()
    except Exception:
        try:
            from command_intel import command_center_home as cmd_cc
            cmd_cc.render()
        except Exception as e:
            st.error(f"Command Center failed: {e}")

    # Block news modals and hide any popups — clicks still work for navigation
    st.markdown("""
    <style>
        #pps-news-modal,
        [data-testid="stDialog"],
        [data-testid="stModal"],
        div[role="dialog"] {
            display: none !important;
        }
    </style>
    <script>
        // Override news modal: instantly remove it if it ever appears
        const _mo = new MutationObserver(function(mutations) {
            const m = document.getElementById('pps-news-modal');
            if (m) m.remove();
        });
        _mo.observe(document.body, {childList: true, subtree: true});
    </script>
    """, unsafe_allow_html=True)

    # Handle nav clicks from CC buttons → go to processing
    if st.session_state.get("_nav_goto"):
        _goto = st.session_state.pop("_nav_goto")
        st.session_state["selected_page"] = resolve_page(_goto)
        _owner = get_module_for_page(_goto)
        if _owner:
            st.session_state["_active_module"] = _owner
        st.rerun()
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# ALL OTHER PAGES → Top bar + Sidebar + Processing Animation
# ═══════════════════════════════════════════════════════════════════════════════
if not render_login_form():
    st.stop()

render_top_bar()

_active_module = st.session_state.get("_active_module", "📊 Price & Info")
_sidebar_page = render_sidebar_features(_active_module)
if _sidebar_page:
    st.session_state["selected_page"] = _sidebar_page

selected_page = resolve_page(st.session_state.get("selected_page", "🎯 Command Center"))
st.session_state["selected_page"] = selected_page

inject_print_css()

# If somehow back to CC, rerun
if selected_page == "🎯 Command Center":
    st.rerun()

# Everything else → Processing animation
render_processing()

# Footer
st.markdown("""
<div style="
  background: #FFFFFF;
  border-top: 1px solid #E5E7EB;
  padding: 20px 32px;
  margin-top: 64px;
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;
  font-family: inherit;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.02);
">
  <div style="display:flex; align-items:center; gap:12px;">
    <span style="font-size:1.0rem; font-weight:800; color:var(--text-main); letter-spacing:-0.02em;">
      🏛️ PPS Anantam
    </span>
    <span style="font-size:0.75rem; color:var(--text-muted); font-weight:500; border-left:1px solid #E5E7EB; padding-left:12px;">
      Bitumen Sales Dashboard — HQ: Vadodara, GJ
    </span>
  </div>
  <div style="font-size:0.75rem; color:var(--text-muted); display:flex; gap:16px; flex-wrap:wrap; font-weight:600; align-items:center;">
    <span style="background:#F3F4F6; padding:4px 8px; border-radius:6px; border:1px solid #E5E7EB;">v6.1</span>
    <span>Build: 28-03-2026</span>
    <span style="color:#059669;">● Production</span>
    <span style="color:var(--text-blue); background:#EEF2FF; padding:4px 8px; border-radius:6px; font-weight:800; border:1px solid rgba(79, 70, 229, 0.2);">GST: 24AAHCV1611L2ZD</span>
  </div>
</div>
""", unsafe_allow_html=True)
