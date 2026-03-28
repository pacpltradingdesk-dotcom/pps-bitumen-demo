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
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f172a;overflow:hidden}
.px{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;font-family:'Inter',sans-serif;position:relative;overflow:hidden;background:#0f172a}

/* Moving grid floor */
.px-floor{position:absolute;bottom:0;left:0;right:0;height:45%;background:linear-gradient(180deg,transparent,rgba(79,70,229,0.03));overflow:hidden}
.px-floor::before{content:'';position:absolute;top:0;left:-50%;width:200%;height:100%;
  background-image:linear-gradient(rgba(79,70,229,0.08) 1px,transparent 1px),linear-gradient(90deg,rgba(79,70,229,0.08) 1px,transparent 1px);
  background-size:80px 40px;transform:perspective(400px) rotateX(60deg);transform-origin:top center;
  animation:floor-scroll 1.5s linear infinite}
@keyframes floor-scroll{to{transform:perspective(400px) rotateX(60deg) translateY(40px)}}

/* Speed lines */
.speed-lines{position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;overflow:hidden}
.sp-line{position:absolute;height:2px;background:linear-gradient(90deg,transparent,rgba(79,70,229,0.4),transparent);animation:sp-fly 0.8s linear infinite;border-radius:2px}
.sp-line:nth-child(1){top:15%;width:120px;left:-120px;animation-delay:0s;animation-duration:0.7s}
.sp-line:nth-child(2){top:25%;width:80px;left:-80px;animation-delay:0.2s;animation-duration:0.5s}
.sp-line:nth-child(3){top:40%;width:150px;left:-150px;animation-delay:0.4s;animation-duration:0.6s}
.sp-line:nth-child(4){top:55%;width:100px;left:-100px;animation-delay:0.1s;animation-duration:0.8s}
.sp-line:nth-child(5){top:65%;width:60px;left:-60px;animation-delay:0.3s;animation-duration:0.55s}
.sp-line:nth-child(6){top:78%;width:130px;left:-130px;animation-delay:0.5s;animation-duration:0.65s}
.sp-line:nth-child(7){top:35%;width:90px;left:-90px;animation-delay:0.15s;animation-duration:0.45s;background:linear-gradient(90deg,transparent,rgba(124,58,237,0.3),transparent)}
.sp-line:nth-child(8){top:50%;width:110px;left:-110px;animation-delay:0.35s;animation-duration:0.75s;background:linear-gradient(90deg,transparent,rgba(99,102,241,0.3),transparent)}
@keyframes sp-fly{to{transform:translateX(calc(100vw + 200px))}}

.px-c{position:relative;z-index:10;text-align:center}

/* ══ RUNNING ROBOT ══ */
.runner-stage{width:200px;height:160px;margin:0 auto 20px;position:relative}

/* Whole robot bounces up/down while running */
.runner{position:absolute;left:50%;top:20px;transform:translateX(-50%);animation:runner-bounce 0.35s ease-in-out infinite}
@keyframes runner-bounce{0%,100%{transform:translateX(-50%) translateY(0)}50%{transform:translateX(-50%) translateY(-12px)}}

/* Lean forward for speed */
.runner-body-wrap{transform:rotate(12deg);transform-origin:center bottom}

/* Head */
.r-head{width:52px;height:42px;background:linear-gradient(135deg,#4F46E5,#7C3AED);border-radius:14px 14px 10px 10px;position:relative;margin:0 auto;box-shadow:0 0 24px rgba(79,70,229,0.5)}
.r-eye{width:10px;height:10px;background:#fff;border-radius:50%;position:absolute;top:14px}
.r-eye.l{left:10px}.r-eye.r{right:10px}
.r-eye::after{content:'';width:5px;height:5px;background:#0f172a;border-radius:50%;position:absolute;top:2px;left:4px}
.r-mouth{width:16px;height:2px;background:rgba(255,255,255,0.5);border-radius:2px;position:absolute;bottom:8px;left:18px}
.r-antenna{width:3px;height:14px;background:#7C3AED;position:absolute;top:-12px;left:24px;border-radius:2px}
.r-antenna::after{content:'';width:8px;height:8px;background:#4F46E5;border-radius:50%;position:absolute;top:-6px;left:-2.5px;box-shadow:0 0 14px rgba(79,70,229,1);animation:ant-glow 0.5s ease-in-out infinite alternate}
@keyframes ant-glow{to{box-shadow:0 0 24px rgba(79,70,229,1);transform:scale(1.3)}}

/* Body */
.r-torso{width:42px;height:34px;background:linear-gradient(180deg,#4338CA,#3730A3);border-radius:6px 6px 10px 10px;margin:2px auto 0;position:relative;box-shadow:0 0 16px rgba(67,56,202,0.3)}
.r-core{width:14px;height:14px;border:2px solid rgba(255,255,255,0.2);border-radius:4px;position:absolute;top:8px;left:12px}
.r-core::after{content:'';width:6px;height:6px;background:#34d399;border-radius:50%;position:absolute;top:2px;left:2px;box-shadow:0 0 8px #34d399;animation:core-p 0.4s ease-in-out infinite alternate}
@keyframes core-p{to{box-shadow:0 0 18px #34d399}}

/* Running arms — pump fast like sprinting */
.r-arm{width:8px;height:28px;background:#4338CA;border-radius:5px;position:absolute;top:46px;transform-origin:top center}
.r-arm.l{left:8px;animation:arm-pump-l 0.35s ease-in-out infinite}
.r-arm.r{right:8px;animation:arm-pump-r 0.35s ease-in-out infinite}
@keyframes arm-pump-l{0%{transform:rotate(45deg)}50%{transform:rotate(-45deg)}100%{transform:rotate(45deg)}}
@keyframes arm-pump-r{0%{transform:rotate(-45deg)}50%{transform:rotate(45deg)}100%{transform:rotate(-45deg)}}

/* Running legs — fast stride */
.r-leg{width:10px;height:24px;background:#3730A3;border-radius:4px 4px 6px 6px;position:absolute;top:78px;transform-origin:top center}
.r-leg.l{left:16px;animation:leg-run-l 0.35s ease-in-out infinite}
.r-leg.r{right:16px;animation:leg-run-r 0.35s ease-in-out infinite}
@keyframes leg-run-l{0%{transform:rotate(35deg)}50%{transform:rotate(-35deg)}100%{transform:rotate(35deg)}}
@keyframes leg-run-r{0%{transform:rotate(-35deg)}50%{transform:rotate(35deg)}100%{transform:rotate(-35deg)}}

/* Speed trail behind robot */
.r-trail{position:absolute;left:50%;top:40px;transform:translateX(-50%)}
.r-trail-line{position:absolute;height:3px;border-radius:2px;right:40px;animation:trail-fade 0.6s linear infinite}
.r-trail-line:nth-child(1){top:0;width:40px;background:rgba(79,70,229,0.5);animation-delay:0s}
.r-trail-line:nth-child(2){top:14px;width:55px;background:rgba(124,58,237,0.4);animation-delay:0.1s}
.r-trail-line:nth-child(3){top:28px;width:35px;background:rgba(99,102,241,0.3);animation-delay:0.2s}
.r-trail-line:nth-child(4){top:42px;width:50px;background:rgba(79,70,229,0.35);animation-delay:0.15s}
.r-trail-line:nth-child(5){top:56px;width:30px;background:rgba(124,58,237,0.25);animation-delay:0.25s}
@keyframes trail-fade{0%{opacity:1;transform:translateX(0) scaleX(1)}100%{opacity:0;transform:translateX(-60px) scaleX(0.3)}}

/* Dust puffs at feet */
.r-dust{position:absolute;bottom:10px;left:50%;transform:translateX(-50%)}
.r-puff{position:absolute;border-radius:50%;background:rgba(148,163,184,0.2);animation:puff-up 0.7s ease-out infinite}
.r-puff:nth-child(1){width:12px;height:12px;bottom:0;left:-20px;animation-delay:0s}
.r-puff:nth-child(2){width:8px;height:8px;bottom:4px;left:-10px;animation-delay:0.15s}
.r-puff:nth-child(3){width:10px;height:10px;bottom:0;left:-30px;animation-delay:0.3s}
@keyframes puff-up{0%{opacity:0.6;transform:scale(1) translateY(0)}100%{opacity:0;transform:scale(2.5) translateY(-20px)}}

/* Floating energy sparks */
.r-sparks{position:absolute;width:200px;height:160px;top:0;left:0;pointer-events:none}
.r-spark{position:absolute;width:3px;height:3px;background:#a5b4fc;border-radius:50%;animation:spark-fly 1s linear infinite}
.r-spark:nth-child(1){top:30px;left:20px;animation-delay:0s;animation-duration:0.8s}
.r-spark:nth-child(2){top:60px;left:10px;animation-delay:0.3s;animation-duration:0.6s}
.r-spark:nth-child(3){top:45px;left:30px;animation-delay:0.5s;animation-duration:0.9s}
.r-spark:nth-child(4){top:80px;left:15px;animation-delay:0.2s;animation-duration:0.7s}
@keyframes spark-fly{0%{opacity:1;transform:translate(0,0)}100%{opacity:0;transform:translate(-80px,-20px)}}

.px-title{color:#f8fafc;font-size:1.2rem;font-weight:800;letter-spacing:-0.02em;margin-bottom:4px}
.px-sub{color:#64748b;font-size:0.7rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:24px}
.px-msg{color:#94a3b8;font-size:0.82rem;font-weight:500;min-height:22px}
.px-msg-line{animation:px-fadein 0.5s ease forwards;opacity:0}
@keyframes px-fadein{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.px-track{width:240px;height:3px;background:rgba(79,70,229,0.1);border-radius:3px;margin:18px auto 0;overflow:hidden}
.px-bar{height:100%;width:30%;background:linear-gradient(90deg,#4F46E5,#7C3AED,#4F46E5);border-radius:3px;animation:px-slide 1.2s ease-in-out infinite}
@keyframes px-slide{0%{transform:translateX(-100%)}100%{transform:translateX(400%)}}
.px-dots{display:flex;gap:6px;justify-content:center;margin-top:20px}
.px-dt{width:6px;height:6px;border-radius:50%;animation:px-dp 3s ease-in-out infinite}
.px-dt:nth-child(1){background:#4F46E5;animation-delay:0s}.px-dt:nth-child(2){background:#7C3AED;animation-delay:0.3s}
.px-dt:nth-child(3){background:#06b6d4;animation-delay:0.6s}.px-dt:nth-child(4){background:#10b981;animation-delay:0.9s}
.px-dt:nth-child(5){background:#f59e0b;animation-delay:1.2s}.px-dt:nth-child(6){background:#ef4444;animation-delay:1.5s}
@keyframes px-dp{0%,100%{opacity:0.3;transform:scale(1)}50%{opacity:1;transform:scale(1.5)}}
</style>

<div class="px">
  <div class="px-floor"></div>
  <div class="speed-lines">
    <div class="sp-line"></div><div class="sp-line"></div><div class="sp-line"></div><div class="sp-line"></div>
    <div class="sp-line"></div><div class="sp-line"></div><div class="sp-line"></div><div class="sp-line"></div>
  </div>

  <div class="px-c">
    <div class="runner-stage">
      <!-- Speed trail -->
      <div class="r-trail">
        <div class="r-trail-line"></div><div class="r-trail-line"></div><div class="r-trail-line"></div>
        <div class="r-trail-line"></div><div class="r-trail-line"></div>
      </div>

      <!-- Robot -->
      <div class="runner">
        <div class="runner-body-wrap">
          <div class="r-antenna"></div>
          <div class="r-head">
            <div class="r-eye l"></div>
            <div class="r-eye r"></div>
            <div class="r-mouth"></div>
          </div>
          <div class="r-arm l"></div>
          <div class="r-torso"><div class="r-core"></div></div>
          <div class="r-arm r"></div>
          <div class="r-leg l"></div>
          <div class="r-leg r"></div>
        </div>
      </div>

      <!-- Dust puffs -->
      <div class="r-dust">
        <div class="r-puff"></div><div class="r-puff"></div><div class="r-puff"></div>
      </div>

      <!-- Energy sparks -->
      <div class="r-sparks">
        <div class="r-spark"></div><div class="r-spark"></div><div class="r-spark"></div><div class="r-spark"></div>
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
