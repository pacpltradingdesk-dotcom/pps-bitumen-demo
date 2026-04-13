"""
Tutorial Engine — Interactive Step-by-Step Tour
================================================
Animated walkthrough: har step mein ek UI element dikhta hai, usme
cursor move hota hai aur click animation play hoti hai. Next button
se next step pe jaate hain.

Entry point:
    from tutorial_engine import render_tutorial_dialog
    render_tutorial_dialog()
"""
from __future__ import annotations

import streamlit as st


# ── Tour Steps ──────────────────────────────────────────────────────────────
# Har step mein:
#   icon       — emoji for the fake button/element
#   label      — button/section text
#   title      — step heading
#   body       — hindi-english explanation
#   where      — navigation hint (module > page)

_STEPS = [
    {
        "icon": "🏛️",
        "label": "PPS Anantam Dashboard",
        "title": "Welcome to PPS Anantam",
        "body": "Yeh aapka bitumen trading command center hai. 9 modules, 80+ pages. Chalo ek quick tour lete hain — bas 2 minute mein sab samajh aa jayega.",
        "where": "Login ke baad yahan pahuchte ho",
        "kind": "hero",
    },
    {
        "icon": "🏠",
        "label": "Home",
        "title": "Step 1: Top Bar — 9 Modules",
        "body": "Upar navigation bar mein 9 modules hain: Home, Pricing, Sales, Intelligence, Documents, Logistics, Reports, + 'More' mein Compliance & System. Kisi bhi module pe click karne se us module ki pages sidebar mein aajayengi.",
        "where": "Top Navigation Bar",
        "kind": "click",
    },
    {
        "icon": "🎯",
        "label": "Command Center",
        "title": "Step 2: Command Center",
        "body": "Home ka main page — 5 KPI cards (Brent, WTI, USD/INR, VG30, AI Signal), alerts panel, aur quick actions. Roz subah 5 min ke liye yahan aao.",
        "where": "Home > Command Center",
        "kind": "click",
    },
    {
        "icon": "💰",
        "label": "Pricing Calculator",
        "title": "Step 3: Quote Banao",
        "body": "Customer ke liye price nikalna hai? Yahan aao — location chuno, grade select karo, load type batao → ranked prices dikhenge, PDF quote ready.",
        "where": "Pricing > Pricing Calculator",
        "kind": "click",
    },
    {
        "icon": "💼",
        "label": "CRM Tasks",
        "title": "Step 4: Daily Worklist",
        "body": "Subah 9 baje yahan aao — Due / Overdue / Upcoming tasks dikhenge. Hot leads, follow-ups, calendar view — sab ek jagah. 25K+ contacts managed.",
        "where": "Sales & CRM > CRM Tasks",
        "kind": "click",
    },
    {
        "icon": "🧠",
        "label": "Market Signals",
        "title": "Step 5: Market Intelligence",
        "body": "10-signal composite — crude, FX, news, govt infra, tenders sab ek score mein. BULLISH / NEUTRAL / BEARISH verdict turant. Bade decision se pehle yahan check karo.",
        "where": "Intelligence > Market Signals",
        "kind": "click",
    },
    {
        "icon": "📊",
        "label": "Director Brief",
        "title": "Step 6: Executive Reports",
        "body": "6-page executive PDF briefing — yesterday + today + 15-day outlook. Prince sir ko forward karne ke liye ready format.",
        "where": "Reports > Director Brief",
        "kind": "click",
    },
    {
        "icon": "📄",
        "label": "Quick Actions",
        "title": "Step 7: Sidebar Quick Actions",
        "body": "Left sidebar mein 6 shortcut buttons — PDF, Print, Excel, Share, WhatsApp, Telegram. Kisi bhi page se direct share / export ho sakta hai.",
        "where": "Sidebar — Quick Actions section",
        "kind": "click",
    },
    {
        "icon": "🔐",
        "label": "24hr Session",
        "title": "Step 8: Login Once, 24 Hours",
        "body": "Ek baar login karo — 24 ghante tak session zinda. Browser band kar do, tab close karo, kuch bhi — wapas aane pe auto-logged in. Logout button sidebar ke neeche.",
        "where": "Automatic — sab pages pe",
        "kind": "info",
    },
    {
        "icon": "📖",
        "label": "Tutorial",
        "title": "Step 9: Yeh Tutorial — Kabhi Bhi",
        "body": "Agar kuch bhool jao ya confuse ho, sidebar ka '📖 Tutorial' button dabao — yeh tour dobara chalega. Ya full guide ke liye 'USER_GUIDE.md' padho.",
        "where": "Sidebar — Tutorial button",
        "kind": "info",
    },
    {
        "icon": "🎉",
        "label": "All Set!",
        "title": "Bas! Ab Use Karo",
        "body": "Aap ready ho. Shuru karne ke liye Home > Command Center pe jao. Koi dikkat ho to Settings > Knowledge Base mein FAQ search karo.",
        "where": "Happy trading!",
        "kind": "hero",
    },
]


# ── CSS + Animated Button ───────────────────────────────────────────────────

def _step_css() -> str:
    """One-shot CSS injected with the step card."""
    return """
<style>
.tour-wrap {
  background: linear-gradient(135deg, #0f1729 0%, #1e293b 100%);
  border-radius: 16px;
  padding: 32px 28px;
  margin: 12px 0;
  color: #fff;
  box-shadow: 0 20px 40px rgba(0,0,0,0.25);
  position: relative;
  overflow: hidden;
}
.tour-wrap::before {
  content: "";
  position: absolute; inset: 0;
  background: radial-gradient(circle at 20% 0%, rgba(99,102,241,0.25), transparent 60%);
  pointer-events: none;
}
.tour-stage {
  background: #f8fafc;
  border-radius: 12px;
  padding: 36px 20px;
  margin: 0 0 24px 0;
  min-height: 180px;
  display: flex; align-items: center; justify-content: center;
  position: relative;
  overflow: hidden;
}
/* Mock button (the element being demonstrated) */
.tour-btn {
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff;
  font-weight: 700;
  font-size: 1.05rem;
  padding: 14px 28px;
  border-radius: 10px;
  box-shadow: 0 6px 20px rgba(79,70,229,0.35);
  display: inline-flex; align-items: center; gap: 10px;
  position: relative;
  animation: btn-press 2.2s ease-in-out infinite;
  z-index: 2;
}
.tour-btn.hero {
  background: linear-gradient(135deg, #c9a84c, #e3c26b);
  color: #0f1729;
  font-size: 1.15rem;
  padding: 18px 34px;
  box-shadow: 0 8px 30px rgba(201,168,76,0.4);
  animation: btn-pulse 2.5s ease-in-out infinite;
}
@keyframes btn-press {
  0%, 100% { transform: scale(1); box-shadow: 0 6px 20px rgba(79,70,229,0.35); }
  45%      { transform: scale(1.05); box-shadow: 0 12px 30px rgba(79,70,229,0.55); }
  50%      { transform: scale(0.94); box-shadow: 0 3px 8px rgba(79,70,229,0.25); }
  55%      { transform: scale(1.05); }
}
@keyframes btn-pulse {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.04); }
}
/* Ripple emitted from the button on "click" */
.tour-ripple {
  position: absolute;
  border: 2px solid #4F46E5;
  border-radius: 50%;
  width: 80px; height: 80px;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  animation: ripple 2.2s ease-out infinite;
  z-index: 1;
}
.tour-ripple.r2 { animation-delay: 0.7s; }
.tour-ripple.r3 { animation-delay: 1.4s; }
@keyframes ripple {
  0%   { opacity: 0.9; width: 40px; height: 40px; }
  100% { opacity: 0;   width: 280px; height: 280px; border-width: 0.5px; }
}
/* Cursor moving to the button */
.tour-cursor {
  position: absolute;
  top: 20%; left: 30%;
  font-size: 1.6rem;
  animation: cursor-move 2.2s ease-in-out infinite;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
  z-index: 3;
  pointer-events: none;
}
@keyframes cursor-move {
  0%       { top: 18%; left: 26%; opacity: 1; }
  40%      { top: 48%; left: 48%; opacity: 1; }
  45%, 55% { top: 50%; left: 50%; transform: scale(0.85); }
  60%      { top: 50%; left: 50%; transform: scale(1); }
  100%     { top: 18%; left: 26%; opacity: 1; }
}
/* Step title + body */
.tour-title {
  font-size: 1.4rem; font-weight: 800; margin: 0 0 10px 0;
  background: linear-gradient(90deg, #fff, #c9a84c);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.tour-body {
  font-size: 0.95rem; line-height: 1.6; color: #cbd5e1; margin: 0 0 12px 0;
}
.tour-where {
  display: inline-block;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.35);
  color: #a5b4fc;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 4px;
}
/* Progress dots */
.tour-dots {
  display: flex; gap: 6px; justify-content: center; margin: 16px 0 4px 0;
}
.tour-dots span {
  width: 8px; height: 8px; border-radius: 50%;
  background: rgba(255,255,255,0.2);
  transition: all 0.3s;
}
.tour-dots span.active {
  background: #c9a84c;
  width: 24px; border-radius: 4px;
}
.tour-dots span.done {
  background: rgba(201,168,76,0.5);
}
.tour-counter {
  font-size: 0.72rem; color: #94a3b8; text-align: center;
  text-transform: uppercase; letter-spacing: 0.1em; margin-top: 6px;
}
</style>
"""


def _render_stage(step: dict) -> str:
    """Build the animated stage HTML for one step."""
    kind = step.get("kind", "click")
    btn_cls = "tour-btn hero" if kind == "hero" else "tour-btn"
    ripples = ""
    cursor = ""
    if kind == "click":
        ripples = """
<div class="tour-ripple"></div>
<div class="tour-ripple r2"></div>
<div class="tour-ripple r3"></div>
"""
        cursor = '<div class="tour-cursor">👆</div>'

    return f"""
<div class="tour-stage">
  {ripples}
  <div class="{btn_cls}">
    <span style="font-size:1.3rem;">{step["icon"]}</span>
    <span>{step["label"]}</span>
  </div>
  {cursor}
</div>
"""


def _render_dots(current: int, total: int) -> str:
    dots = []
    for i in range(total):
        if i < current:
            dots.append('<span class="done"></span>')
        elif i == current:
            dots.append('<span class="active"></span>')
        else:
            dots.append('<span></span>')
    return f'<div class="tour-dots">{"".join(dots)}</div>'


def _render_tutorial_content():
    """Render the interactive tour with Next/Prev navigation."""
    total = len(_STEPS)
    idx = st.session_state.get("_tour_step", 0)
    idx = max(0, min(idx, total - 1))
    step = _STEPS[idx]

    # Inject CSS once
    st.markdown(_step_css(), unsafe_allow_html=True)

    # Main step card
    st.markdown(
        f"""
<div class="tour-wrap">
  {_render_stage(step)}
  <div class="tour-title">{step["title"]}</div>
  <div class="tour-body">{step["body"]}</div>
  <div class="tour-where">📍 {step["where"]}</div>
  {_render_dots(idx, total)}
  <div class="tour-counter">Step {idx + 1} of {total}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Navigation buttons
    col_prev, col_skip, col_next = st.columns([1, 1, 1])

    with col_prev:
        if st.button("← Previous", key=f"_tour_prev_{idx}",
                     use_container_width=True, disabled=(idx == 0)):
            st.session_state["_tour_step"] = idx - 1
            st.rerun()

    with col_skip:
        if st.button("Skip Tour", key=f"_tour_skip_{idx}",
                     use_container_width=True):
            st.session_state["_tour_step"] = 0
            st.session_state["_show_tutorial"] = False
            st.rerun()

    with col_next:
        if idx < total - 1:
            if st.button("Next →", key=f"_tour_next_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state["_tour_step"] = idx + 1
                st.rerun()
        else:
            if st.button("🎉 Finish", key=f"_tour_finish_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state["_tour_step"] = 0
                st.session_state["_show_tutorial"] = False
                st.rerun()


# ── Public API ──────────────────────────────────────────────────────────────

def render_tutorial_dialog():
    """Open the tutorial as a modal dialog (or inline fallback)."""
    try:
        @st.dialog("📖 PPS Anantam — Interactive Tour", width="large")
        def _dlg():
            _render_tutorial_content()
        _dlg()
        return
    except Exception:
        pass

    # Fallback for older Streamlit (< 1.35)
    with st.container(border=True):
        _render_tutorial_content()
