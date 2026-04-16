"""
Empty-state card with optional next-action CTA.

Turns dead-end "nothing here" messages into a friendly card with a clear
next step. Matches Phase 5 contract: CTA buttons use st.session_state
["_nav_goto"] + st.rerun() so the sidebar's active module updates too.

Usage:

    from components.empty_state import render_empty_state

    render_empty_state(
        key="opp_new",
        title="Abhi koi nayi opportunity nahi",
        hint="Scan chalayein ya market signals check karein.",
        cta_label="🔍 Scan Now",
        on_click=lambda: _opp_eng.scan_all_opportunities(),
    )

    # Or navigate to another page:
    render_empty_state(
        key="crm_empty",
        title="Sab tasks complete!",
        hint="Opportunities se naya deal uthao.",
        cta_label="→ Open Opportunities",
        cta_target="🔍 Opportunities",
    )
"""
from __future__ import annotations
from typing import Callable, Optional
import streamlit as st


def render_empty_state(
    *,
    key: str,
    title: str,
    hint: str = "",
    cta_label: Optional[str] = None,
    cta_target: Optional[str] = None,
    on_click: Optional[Callable[[], None]] = None,
    icon: str = "📭",
    tone: str = "muted",
) -> None:
    """Render a compact empty-state card. No-op if only title given."""
    tones = {
        "muted":   ("#f8fafc", "#e5e7eb", "#475569"),
        "success": ("#f0fdf4", "#bbf7d0", "#166534"),
        "info":    ("#eff6ff", "#bfdbfe", "#1e40af"),
    }
    bg, border, text = tones.get(tone, tones["muted"])
    st.markdown(
        f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;
            padding:18px 20px;margin:10px 0;text-align:center;">
  <div style="font-size:1.6rem;line-height:1;margin-bottom:8px;">{icon}</div>
  <div style="font-size:0.95rem;font-weight:700;color:{text};
              margin-bottom:4px;">{title}</div>
  {f'<div style="font-size:0.82rem;color:#64748b;">{hint}</div>' if hint else ''}
</div>
""",
        unsafe_allow_html=True,
    )
    if not cta_label:
        return

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.button(cta_label, key=f"_empty_cta_{key}", use_container_width=True):
            if cta_target:
                st.session_state["_nav_goto"] = cta_target
                st.rerun()
            elif on_click:
                try:
                    on_click()
                except Exception as _e:
                    st.error(f"Action failed: {_e}")
                st.rerun()
