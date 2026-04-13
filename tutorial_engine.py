"""
Tutorial Engine — Floating Tooltip Guided Tour
================================================
Asli nav button pe highlight + bilkul uske paas floating tooltip with
step explanation + Next/Prev/Skip buttons. Intro.js-style in-context tour.

How it works:
  - Python side: tour step state in session_state (_tour_step)
  - JS side: components.html injects script into parent document that:
      1. Finds target button by text, adds .tour-target halo animation
      2. Creates/updates a tooltip DIV near the target (absolutely
         positioned using getBoundingClientRect)
      3. Tooltip has Next/Prev/Skip buttons which JS-click hidden
         Streamlit buttons (by label), triggering a Streamlit rerun
         with updated session state.

Entry points:
  render_tour()  — call inside st.sidebar when _show_tutorial is True
"""
from __future__ import annotations

import json as _json
import streamlit as st
import streamlit.components.v1 as _components


# ── Tour Steps ──────────────────────────────────────────────────────────────

_STEPS = [
    {
        "target": "",
        "title": "🎉 Welcome to PPS Anantam",
        "body": "Aapka bitumen trading ka AI command center. 2-minute ka quick tour — har button ka kaam samjha dunga. Next dabao shuru karne ke liye.",
    },
    {
        "target": "Price & Info",
        "title": "📊 Price & Info",
        "body": "Sab prices aur market info yahan — Command Center, Live Market, Market Signals, News, Price Prediction, Global Markets, Director Briefing. Subah sabse pehle yahan aao.",
    },
    {
        "target": "Sales",
        "title": "🧾 Sales & CRM",
        "body": "Customer ke saare kaam — One-Click Quote, Pricing Calculator, CRM Tasks, Opportunities, Negotiation AI, Communication Hub. 24,000+ contacts managed.",
    },
    {
        "target": "Logistics",
        "title": "🚚 Logistics",
        "body": "Supply chain visibility — port tracking, vessel maps, refinery supply, feasibility engine (kaunsa source best?), tanker tracking, NHAI projects.",
    },
    {
        "target": "Purchasers",
        "title": "📋 Purchasers",
        "body": "Buyer management — customer directory, purchase orders, sales orders, payment tracking, credit aging (30/60/90/120 days), party master.",
    },
    {
        "target": "Sharing",
        "title": "📤 Sharing",
        "body": "Content broadcast — WhatsApp/Telegram/Email templates, scheduled shares, 25K+ contact broadcasts, festival campaigns, AI auto-reply.",
    },
    {
        "target": "Settings",
        "title": "⚙️ Settings",
        "body": "System config — 200+ business rules (margins, GST, rate limits), API keys (OpenAI, NewsAPI), health monitor, bug tracker, AI learning, user management.",
    },
    {
        "target": "Logout",
        "title": "🚪 Logout",
        "body": "Session khatam karne ke liye. Default 24hr auto-login rahega (tab close karne pe bhi). Urgent exit ke liye dabao.",
    },
    {
        "target": "📖 Tutorial",
        "title": "📖 Tutorial (yeh button)",
        "body": "Kabhi bhi confuse ho to sidebar ka yeh button dabao — tour dobara chalega. Full written guide ke liye USER_GUIDE.md bhi hai.",
    },
    {
        "target": "",
        "title": "🎯 Bas! Ab Use Karo",
        "body": "Tour complete. Home > Command Center best start hai. Koi dikkat ho to Settings > Knowledge Base mein FAQ search karo.",
    },
]


# Hidden Streamlit button labels — these get JS-clicked by the tooltip
_CTRL_PREV   = "__PPS_TOUR_PREV__"
_CTRL_NEXT   = "__PPS_TOUR_NEXT__"
_CTRL_SKIP   = "__PPS_TOUR_SKIP__"
_CTRL_FINISH = "__PPS_TOUR_FINISH__"


# ── JS injection ────────────────────────────────────────────────────────────

def _inject_tour_js(step: dict, idx: int, total: int):
    """Inject the tour script into parent DOM."""
    payload = {
        "target":      step.get("target", "") or "",
        "title":       step.get("title", ""),
        "body":        step.get("body", ""),
        "idx":         idx,
        "total":       total,
        "is_first":    (idx == 0),
        "is_last":     (idx == total - 1),
        "ctrl_prev":   _CTRL_PREV,
        "ctrl_next":   _CTRL_NEXT,
        "ctrl_skip":   _CTRL_SKIP,
        "ctrl_finish": _CTRL_FINISH,
    }
    payload_json = _json.dumps(payload)

    html = """
<script>
(function() {
  try {
    var doc = window.parent.document;
    var win = window.parent;
    if (!doc) return;

    var DATA = __PAYLOAD__;

    // ─── Inject style tag once ──────────────────────────────────
    if (!doc.getElementById('pps-tour-style')) {
      var style = doc.createElement('style');
      style.id = 'pps-tour-style';
      style.textContent = `
        @keyframes pps-tour-pulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(79,70,229,0.75), 0 0 0 0 rgba(201,168,76,0.5); }
          50%     { box-shadow: 0 0 0 10px rgba(79,70,229,0.35), 0 0 0 22px rgba(201,168,76,0); }
        }
        @keyframes pps-tour-fade {
          from { opacity: 0; transform: translateY(-6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .pps-tour-target {
          animation: pps-tour-pulse 1.6s ease-in-out infinite !important;
          outline: 3px solid #4F46E5 !important;
          outline-offset: 4px !important;
          border-radius: 10px !important;
          position: relative !important;
          z-index: 9998 !important;
          scroll-margin-top: 160px !important;
          scroll-margin-bottom: 260px !important;
        }
        #pps-tour-tip {
          position: absolute;
          z-index: 10000;
          width: 340px;
          max-width: calc(100vw - 40px);
          background: linear-gradient(135deg, #0f1729 0%, #1e293b 100%);
          color: #fff;
          border-radius: 14px;
          padding: 16px 18px 12px;
          box-shadow: 0 20px 50px rgba(0,0,0,0.35), 0 0 0 1px rgba(99,102,241,0.3);
          font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
          animation: pps-tour-fade 0.25s ease-out;
        }
        #pps-tour-tip .ppt-header {
          display:flex; justify-content:space-between; align-items:center;
          font-size:0.62rem; font-weight:700; color:#94a3b8;
          text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;
        }
        #pps-tour-tip .ppt-step { color:#c9a84c; }
        #pps-tour-tip .ppt-title {
          font-size:1.05rem; font-weight:800; margin:0 0 8px 0;
          background: linear-gradient(90deg, #fff, #c9a84c);
          -webkit-background-clip: text; background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        #pps-tour-tip .ppt-body {
          font-size:0.82rem; line-height:1.55; color:#cbd5e1; margin:0 0 12px 0;
        }
        #pps-tour-tip .ppt-dots {
          display:flex; gap:4px; justify-content:center; margin:8px 0;
        }
        #pps-tour-tip .ppt-dots span {
          width:6px; height:6px; border-radius:50%;
          background: rgba(255,255,255,0.22);
        }
        #pps-tour-tip .ppt-dots span.done { background: rgba(201,168,76,0.5); }
        #pps-tour-tip .ppt-dots span.active {
          background: #c9a84c; width:18px; border-radius:3px;
        }
        #pps-tour-tip .ppt-btns {
          display:grid; grid-template-columns: 1fr 1fr 1.4fr; gap:6px; margin-top:10px;
        }
        #pps-tour-tip .ppt-btn {
          border: 1px solid rgba(255,255,255,0.15);
          background: rgba(255,255,255,0.05);
          color: #e2e8f0;
          padding: 7px 10px;
          border-radius: 7px;
          cursor: pointer;
          font-size: 0.78rem;
          font-weight: 600;
          transition: all 0.15s;
        }
        #pps-tour-tip .ppt-btn:hover:not(:disabled) {
          background: rgba(255,255,255,0.12);
          border-color: rgba(255,255,255,0.3);
        }
        #pps-tour-tip .ppt-btn:disabled {
          opacity: 0.4; cursor: not-allowed;
        }
        #pps-tour-tip .ppt-btn.primary {
          background: linear-gradient(135deg, #4F46E5, #7C3AED);
          border-color: #4F46E5;
          color: #fff;
        }
        #pps-tour-tip .ppt-btn.primary:hover {
          background: linear-gradient(135deg, #4338CA, #6D28D9);
        }
        #pps-tour-tip .ppt-arrow {
          position: absolute;
          width: 14px; height: 14px;
          background: inherit;
          transform: rotate(45deg);
        }
        #pps-tour-tip.pos-below .ppt-arrow { top:-7px; left:40px; }
        #pps-tour-tip.pos-above .ppt-arrow { bottom:-7px; left:40px; }
        #pps-tour-tip.pos-center .ppt-arrow { display:none; }
      `;
      doc.head.appendChild(style);
    }

    // ─── Clear previous highlights ──────────────────────────────
    doc.querySelectorAll('.pps-tour-target').forEach(function(el) {
      el.classList.remove('pps-tour-target');
    });

    // ─── Find & hide the Streamlit control buttons (PREV/NEXT/SKIP/FINISH) ──
    // IMPORTANT: do NOT use pointer-events:none, visibility:hidden, or
    // display:none — all of those block programmatic .click() calls.
    // Move off-screen with absolute positioning only.
    var ctrlLabels = [DATA.ctrl_prev, DATA.ctrl_next, DATA.ctrl_skip, DATA.ctrl_finish];
    var ctrlButtons = {};
    doc.querySelectorAll('button').forEach(function(btn) {
      var txt = (btn.textContent || '').trim();
      for (var j = 0; j < ctrlLabels.length; j++) {
        // Use includes() instead of === in case streamlit adds whitespace
        if (txt === ctrlLabels[j] || txt.indexOf(ctrlLabels[j]) !== -1) {
          ctrlButtons[ctrlLabels[j]] = btn;
          // Hide the Streamlit wrapper by moving far off-screen.
          var wrap = btn.closest('.stButton') || btn.closest('[data-testid="stButton"]') || btn.parentElement;
          if (wrap) {
            wrap.style.position = 'absolute';
            wrap.style.left = '-99999px';
            wrap.style.top = '-99999px';
            wrap.style.width = '1px';
            wrap.style.height = '1px';
            wrap.style.overflow = 'hidden';
          }
        }
      }
    });

    // ─── Find target button ─────────────────────────────────────
    var target = null;
    if (DATA.target) {
      var btns = doc.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        var txt = (btns[i].textContent || '').trim();
        if (!txt) continue;
        // Exact start-match preferred to avoid matching "Generate PDF" for "PDF"
        if (txt === DATA.target || txt.indexOf(DATA.target) !== -1) {
          var r = btns[i].getBoundingClientRect();
          if (r.width < 2 || r.height < 2) continue;
          // Skip our own control buttons
          if (ctrlLabels.indexOf(txt) !== -1) continue;
          target = btns[i];
          break;
        }
      }
      if (target) {
        target.classList.add('pps-tour-target');
      }
    }

    // ─── Build/update tooltip ───────────────────────────────────
    var tip = doc.getElementById('pps-tour-tip');
    if (!tip) {
      tip = doc.createElement('div');
      tip.id = 'pps-tour-tip';
      doc.body.appendChild(tip);
    }

    // Dots HTML
    var dotsHtml = '';
    for (var k = 0; k < DATA.total; k++) {
      var cls = '';
      if (k < DATA.idx)      cls = 'done';
      else if (k === DATA.idx) cls = 'active';
      dotsHtml += '<span class="' + cls + '"></span>';
    }

    tip.innerHTML =
      '<div class="ppt-arrow"></div>' +
      '<div class="ppt-header">' +
        '<span>📖 Guided Tour</span>' +
        '<span class="ppt-step">Step ' + (DATA.idx + 1) + ' / ' + DATA.total + '</span>' +
      '</div>' +
      '<div class="ppt-title">' + DATA.title + '</div>' +
      '<div class="ppt-body">' + DATA.body + '</div>' +
      '<div class="ppt-dots">' + dotsHtml + '</div>' +
      '<div class="ppt-btns">' +
        '<button class="ppt-btn" id="ppt-prev" ' + (DATA.is_first ? 'disabled' : '') + '>← Prev</button>' +
        '<button class="ppt-btn" id="ppt-skip">Skip</button>' +
        '<button class="ppt-btn primary" id="ppt-next">' + (DATA.is_last ? '🎉 Finish' : 'Next →') + '</button>' +
      '</div>';

    // ─── Position tooltip near target ───────────────────────────
    function positionTip() {
      if (!target) {
        // Center of viewport
        tip.className = 'pos-center';
        tip.style.position = 'fixed';
        tip.style.top  = '50%';
        tip.style.left = '50%';
        tip.style.transform = 'translate(-50%, -50%)';
        return;
      }
      tip.style.position = 'absolute';
      tip.style.transform = '';

      var r = target.getBoundingClientRect();
      var scrollY = win.scrollY || doc.documentElement.scrollTop || 0;
      var scrollX = win.scrollX || doc.documentElement.scrollLeft || 0;
      var tipRect = tip.getBoundingClientRect();
      var tipW = Math.max(tipRect.width, 340);
      var tipH = tipRect.height || 200;

      // Space check: prefer below, else above
      var spaceBelow = win.innerHeight - r.bottom;
      var spaceAbove = r.top;
      var placeBelow = spaceBelow >= tipH + 20 || spaceBelow >= spaceAbove;

      var top, left;
      if (placeBelow) {
        top = r.bottom + scrollY + 14;
        tip.className = 'pos-below';
      } else {
        top = r.top + scrollY - tipH - 14;
        tip.className = 'pos-above';
      }

      // Horizontal: try to align left with target, but keep in viewport
      left = r.left + scrollX;
      var maxLeft = scrollX + win.innerWidth - tipW - 16;
      var minLeft = scrollX + 16;
      if (left > maxLeft) left = maxLeft;
      if (left < minLeft) left = minLeft;

      tip.style.top  = top  + 'px';
      tip.style.left = left + 'px';
    }

    // Wait a tick for tooltip to be in DOM before measuring
    setTimeout(positionTip, 10);

    // Reposition on resize/scroll
    if (win._ppsTourResizeListener) {
      win.removeEventListener('resize', win._ppsTourResizeListener);
      win.removeEventListener('scroll', win._ppsTourResizeListener, true);
    }
    win._ppsTourResizeListener = positionTip;
    win.addEventListener('resize', positionTip);
    win.addEventListener('scroll', positionTip, true);

    // Scroll target into view (after tooltip placed)
    if (target) {
      setTimeout(function() {
        target.scrollIntoView({behavior: 'smooth', block: 'center'});
        setTimeout(positionTip, 420);
      }, 80);
    }

    // ─── Wire tooltip buttons to hidden Streamlit controls ──────
    function clickCtrl(label) {
      var btn = ctrlButtons[label];
      if (!btn) {
        // Fallback: re-scan parent doc for the button (may have re-rendered)
        var all = doc.querySelectorAll('button');
        for (var i = 0; i < all.length; i++) {
          var t = (all[i].textContent || '').trim();
          if (t === label || t.indexOf(label) !== -1) { btn = all[i]; break; }
        }
      }
      if (btn) {
        // Native click — most reliable when button isn't blocked by
        // pointer-events:none or display:none. Do NOT also dispatchEvent,
        // doing both fires the click twice → double state change.
        try {
          btn.click();
        } catch (e) {
          try {
            btn.dispatchEvent(new MouseEvent('click', {
              bubbles: true, cancelable: true, view: win
            }));
          } catch (e2) {
            console.warn('PPS tour: click failed', e2);
          }
        }
      } else {
        console.warn('PPS tour: control button not found:', label);
      }
    }

    var prevBtn = tip.querySelector('#ppt-prev');
    var skipBtn = tip.querySelector('#ppt-skip');
    var nextBtn = tip.querySelector('#ppt-next');

    if (prevBtn) prevBtn.onclick = function() { clickCtrl(DATA.ctrl_prev); };
    if (skipBtn) skipBtn.onclick = function() {
      removeTip();
      clickCtrl(DATA.ctrl_skip);
    };
    if (nextBtn) nextBtn.onclick = function() {
      if (DATA.is_last) {
        removeTip();
        clickCtrl(DATA.ctrl_finish);
      } else {
        clickCtrl(DATA.ctrl_next);
      }
    };

    function removeTip() {
      var t = doc.getElementById('pps-tour-tip');
      if (t) t.remove();
      doc.querySelectorAll('.pps-tour-target').forEach(function(el) {
        el.classList.remove('pps-tour-target');
      });
    }

  } catch (err) {
    console.warn('PPS tour error:', err);
  }
})();
</script>
<style>html, body { margin: 0; padding: 0; }</style>
""".replace("__PAYLOAD__", payload_json)

    _components.html(html, height=0)


def _inject_cleanup_js():
    """Remove tooltip + highlights from parent DOM."""
    html = """
<script>
(function() {
  try {
    var doc = window.parent.document;
    var tip = doc.getElementById('pps-tour-tip');
    if (tip) tip.remove();
    doc.querySelectorAll('.pps-tour-target').forEach(function(el) {
      el.classList.remove('pps-tour-target');
    });
  } catch (err) {}
})();
</script>
"""
    _components.html(html, height=0)


# ── Control-button handlers (hidden Streamlit buttons) ──────────────────────

def _render_control_buttons(idx: int, total: int):
    """Render the hidden Streamlit control buttons that the tooltip clicks."""
    # These buttons need to exist in the DOM so JS can trigger reruns.
    # They are hidden by the tour JS (positioned offscreen).
    if st.button(_CTRL_PREV, key="_pps_tour_ctrl_prev"):
        if idx > 0:
            st.session_state["_tour_step"] = idx - 1
            st.rerun()
    if st.button(_CTRL_NEXT, key="_pps_tour_ctrl_next"):
        if idx < total - 1:
            st.session_state["_tour_step"] = idx + 1
            st.rerun()
    if st.button(_CTRL_SKIP, key="_pps_tour_ctrl_skip"):
        _end_tour()
        st.rerun()
    if st.button(_CTRL_FINISH, key="_pps_tour_ctrl_finish"):
        _end_tour()
        st.rerun()


def _end_tour():
    """Clear tour state + DOM."""
    st.session_state["_tour_step"] = 0
    st.session_state["_show_tutorial"] = False
    _inject_cleanup_js()


# ── Public entry ────────────────────────────────────────────────────────────

def render_tour():
    """
    Render the tour for the current step.
    Call inside the sidebar (or anywhere before page content) when
    _show_tutorial is True. This will:
      - inject JS to highlight the target + show tooltip
      - render hidden control buttons for tooltip to trigger reruns
    """
    total = len(_STEPS)
    idx = st.session_state.get("_tour_step", 0)
    idx = max(0, min(idx, total - 1))
    step = _STEPS[idx]

    # 1. Hidden control buttons (must exist in DOM for JS to click)
    _render_control_buttons(idx, total)

    # 2. Inject tour JS (highlight + tooltip + wire buttons)
    _inject_tour_js(step, idx, total)


# ── Backward-compat alias ────────────────────────────────────────────────────

def render_tutorial_dialog():
    """Legacy alias — just calls render_tour()."""
    render_tour()
