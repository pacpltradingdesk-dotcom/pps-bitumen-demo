"""
Daily Flow shortcut row — 5 large buttons of the most-used daily actions.

Sits below the hero call card on Command Center.

  [ 📝 Quote ]  [ 📋 Brief ]  [ 📢 Broadcast ]  [ 🔮 Predict ]  [ 🤝 Negotiate ]

Each button sets st.session_state["selected_page"] and reruns — same
mechanism the sidebar uses, so navigation is consistent.
"""
from __future__ import annotations
import streamlit as st

# (icon+label, target page key — must match dashboard.PAGE_DISPATCH)
_FLOW = [
    ("📝 Quote",     "🧮 Pricing Calculator"),
    ("📋 Brief",     "📋 Director Briefing"),
    ("📢 Broadcast", "📤 Share Center"),
    ("🔮 Predict",   "🔮 Price Prediction"),
    ("🤝 Negotiate", "🤝 Negotiation Assistant"),
]


def render_daily_flow_row() -> None:
    st.markdown(
        "<div style='font-size:0.62rem;font-weight:800;letter-spacing:0.14em;"
        "color:#6B7280;text-transform:uppercase;margin:14px 0 6px 0;'>"
        "Daily Flow · jump to the 5 actions you do every day"
        "</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(_FLOW))
    for i, (label, page) in enumerate(_FLOW):
        with cols[i]:
            if st.button(
                label,
                key=f"_daily_flow_{i}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state["selected_page"] = page
                st.rerun()
