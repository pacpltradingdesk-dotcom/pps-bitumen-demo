"""
Tutorial Engine — In-Context Guided Tour
=========================================
Actual UI buttons pe pulse animation inject hoti hai (JavaScript via
components.html accessing parent document). Sidebar mein ek small tour
panel guidance + navigation provide karta hai.

Flow:
  sidebar "📖 Tutorial" click → _show_tutorial=True
  → render_tour() renders panel in sidebar
  → JS injects `.tour-target` class on the current step's target button
     in parent DOM, making it pulse with a halo effect
  → Next/Prev updates _tour_step, rerun triggers new highlight
  → Skip/Finish clears state + removes highlights

Entry points:
  render_tutorial_dialog() — legacy alias
  render_tour()            — sidebar panel + JS highlight
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as _components


# ── Tour Steps ──────────────────────────────────────────────────────────────
# target: button text to find & pulse in main DOM (empty = no highlight)
# title:  step heading
# body:   Hindi-English explanation
# where:  location hint chip
_STEPS = [
    {
        "target": "",
        "title": "🎉 Welcome to PPS Anantam",
        "body": "Aapka bitumen trading ka AI command center. Chalo 2 minute ka tour lete hain — har button ka kaam samjha dunga. Next dabao.",
        "where": "Tour shuru",
    },
    {
        "target": "Price & Info",
        "title": "📊 Price & Info",
        "body": "Yahan se sab prices aur market info milega — Command Center, Live Market, Market Signals, News, Price Prediction, Global Markets, Director Briefing. Roz subah sabse pehle yahan aao.",
        "where": "Top Bar — Button 1",
    },
    {
        "target": "Sales",
        "title": "🧾 Sales & CRM",
        "body": "Customer se related sab kaam — One-Click Quote, Pricing Calculator, CRM Tasks, Opportunities, Negotiation AI, Communication Hub. 24,000+ contacts managed.",
        "where": "Top Bar — Button 2",
    },
    {
        "target": "Logistics",
        "title": "🚚 Logistics",
        "body": "Supply chain visibility — port tracking, vessel maps, refinery supply, feasibility engine (kaunsa source best hai?), tanker tracking, NHAI highway projects.",
        "where": "Top Bar — Button 3",
    },
    {
        "target": "Purchasers",
        "title": "📋 Purchasers",
        "body": "Buyer management — customer directory, purchase orders, sales orders, payment tracking, credit aging (30/60/90/120 days), party master data.",
        "where": "Top Bar — Button 4",
    },
    {
        "target": "Sharing",
        "title": "📤 Sharing",
        "body": "Content broadcast — WhatsApp/Telegram/Email templates, scheduled shares, 25K+ contact broadcasts, festival campaigns, AI auto-reply.",
        "where": "Top Bar — Button 5",
    },
    {
        "target": "Settings",
        "title": "⚙️ Settings",
        "body": "System config — 200+ business rules (margins, GST, rate limits), API keys (OpenAI, NewsAPI, weather), health monitor, bug tracker, AI learning, user management.",
        "where": "Top Bar — Button 6",
    },
    {
        "target": "Logout",
        "title": "🚪 Logout (top right)",
        "body": "Session khatam karne ke liye yeh button. Default mein 24 ghante tak auto-login rahega (tab close karne pe bhi). Logout dabao to force-exit.",
        "where": "Top Bar — Right Side",
    },
    {
        "target": "📖 Tutorial",
        "title": "📖 Tutorial (yeh button)",
        "body": "Kabhi bhi confuse ho to sidebar ka yeh button dabao — yeh tour dobara chalega. Full written guide ke liye USER_GUIDE.md bhi hai project mein.",
        "where": "Sidebar — Top",
    },
    {
        "target": "",
        "title": "🎯 Bas! Ab Use Karo",
        "body": "Tour complete. Shuru karne ke liye koi bhi module dabao. Home > Command Center best start hai. Koi dikkat ho to Settings > Knowledge Base mein FAQ search karo.",
        "where": "Happy trading!",
    },
]


# ── JS injection: highlight real button in parent DOM ──────────────────────

def _inject_highlight(target_text: str):
    """
    Inject JS that:
      1. Removes any existing .tour-target highlights from parent document
      2. Finds the first button whose text includes target_text
      3. Adds .tour-target class → animated outline + pulse halo
      4. Scrolls it into view
    If target_text is empty, only the cleanup step runs.
    """
    # Escape for JS string literal
    js_target = (target_text or "").replace("\\", "\\\\").replace("'", "\\'")

    html = f"""
<script>
(function() {{
  try {{
    var doc = window.parent.document;
    if (!doc) return;

    // 1. Cleanup previous highlights
    var old = doc.querySelectorAll('.tour-target');
    old.forEach(function(el) {{
      el.classList.remove('tour-target');
    }});

    // 2. Inject style tag once
    if (!doc.getElementById('pps-tour-style')) {{
      var style = doc.createElement('style');
      style.id = 'pps-tour-style';
      style.textContent = `
        @keyframes pps-tour-pulse {{
          0%, 100% {{
            box-shadow: 0 0 0 0 rgba(79,70,229,0.75),
                        0 0 0 0 rgba(201,168,76,0.5);
          }}
          50% {{
            box-shadow: 0 0 0 10px rgba(79,70,229,0.35),
                        0 0 0 22px rgba(201,168,76,0);
          }}
        }}
        @keyframes pps-tour-ring {{
          0%   {{ transform: scale(1);   opacity: 0.9; }}
          100% {{ transform: scale(2.4); opacity: 0;   }}
        }}
        .tour-target {{
          animation: pps-tour-pulse 1.6s ease-in-out infinite !important;
          outline: 3px solid #4F46E5 !important;
          outline-offset: 4px !important;
          border-radius: 10px !important;
          position: relative !important;
          z-index: 9999 !important;
          scroll-margin-top: 120px !important;
        }}
        .tour-target::before {{
          content: "";
          position: absolute;
          inset: -4px;
          border: 2px solid #c9a84c;
          border-radius: 12px;
          animation: pps-tour-ring 1.6s ease-out infinite;
          pointer-events: none;
        }}
      `;
      doc.head.appendChild(style);
    }}

    // 3. Find and highlight the target button by text match
    var targetText = '{js_target}';
    if (!targetText) return;

    var buttons = doc.querySelectorAll('button');
    var found = null;
    for (var i = 0; i < buttons.length; i++) {{
      var txt = (buttons[i].textContent || '').trim();
      if (txt && txt.indexOf(targetText) !== -1) {{
        // Skip hidden / zero-sized buttons
        var r = buttons[i].getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        found = buttons[i];
        break;
      }}
    }}

    if (found) {{
      found.classList.add('tour-target');
      found.scrollIntoView({{behavior: 'smooth', block: 'center'}});
    }}
  }} catch (err) {{
    console.warn('Tour highlight failed:', err);
  }}
}})();
</script>
<style>html, body {{ margin:0; padding:0; height:0; }}</style>
"""
    _components.html(html, height=0)


# ── Progress dots renderer ─────────────────────────────────────────────────

def _dots_html(current: int, total: int) -> str:
    pcs = []
    for i in range(total):
        if i < current:
            pcs.append('<span style="width:6px;height:6px;border-radius:50%;background:rgba(201,168,76,0.55);"></span>')
        elif i == current:
            pcs.append('<span style="width:18px;height:6px;border-radius:3px;background:#c9a84c;"></span>')
        else:
            pcs.append('<span style="width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,0.22);"></span>')
    return (
        '<div style="display:flex;gap:5px;justify-content:center;align-items:center;margin:10px 0 4px 0;">'
        + "".join(pcs)
        + "</div>"
    )


# ── Tour panel renderer ────────────────────────────────────────────────────

def render_tour():
    """Render the tour panel (call inside sidebar when _show_tutorial is True)."""
    total = len(_STEPS)
    idx = st.session_state.get("_tour_step", 0)
    idx = max(0, min(idx, total - 1))
    step = _STEPS[idx]

    # 1. Inject the highlight for the CURRENT step's target
    _inject_highlight(step.get("target", ""))

    # 2. Render the panel content
    panel_html = f"""
<div style="background:linear-gradient(135deg,#0f1729 0%,#1e293b 100%);
            border-radius:14px;padding:18px 16px 12px;margin:4px 0 12px 0;
            color:#fff;box-shadow:0 12px 30px rgba(0,0,0,0.25);
            border:1px solid rgba(99,102,241,0.25);">
  <div style="display:flex;align-items:center;justify-content:space-between;
              font-size:0.66rem;font-weight:700;color:#94a3b8;
              text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">
    <span>📖 Guided Tour</span>
    <span style="color:#c9a84c;">Step {idx + 1} / {total}</span>
  </div>
  <div style="font-size:1.02rem;font-weight:800;margin:0 0 8px 0;
              background:linear-gradient(90deg,#fff,#c9a84c);
              -webkit-background-clip:text;background-clip:text;
              -webkit-text-fill-color:transparent;">
    {step["title"]}
  </div>
  <div style="font-size:0.82rem;line-height:1.55;color:#cbd5e1;margin-bottom:10px;">
    {step["body"]}
  </div>
  <div style="display:inline-block;background:rgba(99,102,241,0.15);
              border:1px solid rgba(99,102,241,0.3);color:#a5b4fc;
              padding:3px 10px;border-radius:12px;font-size:0.7rem;
              font-weight:600;">📍 {step["where"]}</div>
  {_dots_html(idx, total)}
</div>
"""
    st.markdown(panel_html, unsafe_allow_html=True)

    # 3. Nav buttons (Prev / Skip / Next)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("←", key=f"_tour_prev_{idx}",
                     use_container_width=True, disabled=(idx == 0),
                     help="Previous step"):
            st.session_state["_tour_step"] = idx - 1
            st.rerun()
    with c2:
        if st.button("Skip", key=f"_tour_skip_{idx}",
                     use_container_width=True,
                     help="Close tour"):
            _end_tour()
            st.rerun()
    with c3:
        if idx < total - 1:
            if st.button("Next →", key=f"_tour_next_{idx}",
                         use_container_width=True, type="primary"):
                st.session_state["_tour_step"] = idx + 1
                st.rerun()
        else:
            if st.button("🎉 Finish", key=f"_tour_finish_{idx}",
                         use_container_width=True, type="primary"):
                _end_tour()
                st.rerun()


def _end_tour():
    """Clear tour state AND remove any DOM highlights."""
    st.session_state["_tour_step"] = 0
    st.session_state["_show_tutorial"] = False
    # Fire a final cleanup JS to strip .tour-target from DOM
    _inject_highlight("")


# ── Legacy alias (backward compat with previous subtab_bar import) ─────────

def render_tutorial_dialog():
    """Backward-compat shim — calls render_tour()."""
    render_tour()
