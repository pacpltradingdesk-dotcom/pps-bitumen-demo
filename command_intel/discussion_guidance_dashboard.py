"""
PPS Anantam -- Discussion Guidance Dashboard v1.0
====================================================
3-tab UI: Supplier Discussion, Importer Discussion, Local Trader Discussion.
Each tab provides party selection, cargo parameters, and a "Generate Brief"
button that calls DiscussionGuide.prepare_discussion() to produce
talking points, price targets, objection responses, and WhatsApp drafts.

Vastu Design: NAVY #1e3a5f, GOLD #c9a84c, GREEN #2d6a4f.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("discussion_guidance_dashboard")

# ── Vastu Design System ─────────────────────────────────────────────────────
_NAVY  = "#1e3a5f"
_GREEN = "#2d6a4f"
_GOLD  = "#c9a84c"
_FIRE  = "#b85c38"
_IVORY = "#faf7f2"
_SLATE = "#64748b"

IST = timezone(timedelta(hours=5, minutes=30))
BASE = Path(__file__).resolve().parent.parent

# ── Safe imports ─────────────────────────────────────────────────────────────
try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    from discussion_guidance_engine import prepare_discussion
    _ENGINE = True
except ImportError:
    _ENGINE = False

try:
    from database import get_all_suppliers, get_all_customers
    _DB = True
except ImportError:
    _DB = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")


def _get_party_list(mode: str) -> List[dict]:
    """Get relevant party list based on discussion mode."""
    if not _DB:
        return []
    try:
        if mode == "supplier":
            return get_all_suppliers() or []
        elif mode in ("importer", "trader"):
            return get_all_customers() or []
    except Exception as exc:
        LOG.warning("Failed to load party list for %s: %s", mode, exc)
    return []


def _party_display_name(party: dict) -> str:
    """Create a display name for the dropdown."""
    name = party.get("name", "Unknown")
    city = party.get("city", "")
    state = party.get("state", "")
    location = f" ({city}, {state})" if city or state else ""
    return f"{name}{location}"


def _render_whatsapp_draft(st, draft: str) -> None:
    """Render WhatsApp draft with copy helper."""
    if not draft:
        return
    st.markdown("##### WhatsApp Draft Message")
    st.text_area(
        "Copy and send via WhatsApp",
        value=draft,
        height=200,
        key=f"wa_draft_{hash(draft) % 100000}",
        help="Select all text (Ctrl+A) and copy (Ctrl+C) to send via WhatsApp",
    )
    st.caption("Tip: Select all text in the box above, copy, and paste into WhatsApp.")


def _render_discussion_brief(st, brief: dict) -> None:
    """Render the discussion brief output from the engine."""
    if not brief:
        st.warning("The engine returned an empty brief.")
        return

    # Summary banner
    summary = brief.get("summary", brief.get("headline", ""))
    if summary:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{_NAVY},{_GREEN});'
            f'color:white;padding:14px 20px;border-radius:10px;margin-bottom:14px;">'
            f'<div style="font-size:1.05rem;font-weight:600;">{summary}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Talking points
    points = brief.get("talking_points", brief.get("key_points", []))
    if points:
        st.markdown("##### Talking Points")
        for i, point in enumerate(points, 1):
            if isinstance(point, dict):
                text = point.get("point", point.get("text", str(point)))
                priority = point.get("priority", "")
                st.markdown(f"**{i}.** {text}" + (f" _({priority})_" if priority else ""))
            else:
                st.markdown(f"**{i}.** {point}")

    # Price targets
    price_targets = brief.get("price_targets", brief.get("pricing", {}))
    if price_targets:
        st.markdown("---")
        st.markdown("##### Price Targets")
        if isinstance(price_targets, dict):
            pc1, pc2, pc3 = st.columns(3)
            target = price_targets.get("target", price_targets.get("balanced", "N/A"))
            floor_price = price_targets.get("floor", price_targets.get("aggressive", "N/A"))
            ceiling = price_targets.get("ceiling", price_targets.get("premium", "N/A"))
            pc1.metric("Floor / Aggressive", f"Rs {floor_price}" if floor_price != "N/A" else "N/A")
            pc2.metric("Target / Balanced", f"Rs {target}" if target != "N/A" else "N/A")
            pc3.metric("Ceiling / Premium", f"Rs {ceiling}" if ceiling != "N/A" else "N/A")

            # Additional pricing details
            for key in ("landed_cost", "margin", "forex_component", "freight_component"):
                if key in price_targets:
                    st.caption(f"{key.replace('_', ' ').title()}: Rs {price_targets[key]}")
        elif isinstance(price_targets, list) and _PANDAS:
            df = pd.DataFrame(price_targets)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Objection responses
    objections = brief.get("objection_responses", brief.get("objections", []))
    if objections:
        st.markdown("---")
        st.markdown("##### Objection Handling")
        for obj in objections:
            if isinstance(obj, dict):
                objection_text = obj.get("objection", obj.get("question", ""))
                response_text = obj.get("response", obj.get("answer", ""))
                with st.expander(f"Objection: {objection_text}", expanded=False):
                    st.markdown(response_text)
            elif isinstance(obj, str):
                st.markdown(f"- {obj}")

    # Market context
    context = brief.get("market_context", brief.get("market_data", {}))
    if context:
        with st.expander("Market Context", expanded=False):
            if isinstance(context, dict):
                for key, val in context.items():
                    st.markdown(f"- **{key.replace('_', ' ').title()}**: {val}")
            elif isinstance(context, list):
                for item in context:
                    st.markdown(f"- {item}")

    # WhatsApp draft
    wa_draft = brief.get("whatsapp_draft", brief.get("whatsapp_message", ""))
    if wa_draft:
        st.markdown("---")
        _render_whatsapp_draft(st, wa_draft)

    # Email draft
    email_draft = brief.get("email_draft", "")
    if email_draft:
        with st.expander("Email Draft", expanded=False):
            st.text_area(
                "Email draft",
                value=email_draft,
                height=200,
                key=f"email_{hash(str(brief)) % 100000}",
            )

    # Timestamps
    ts = brief.get("generated_at", brief.get("timestamp", _ist_now()))
    st.caption(f"Brief generated: {ts}")


def _render_discussion_tab(st, mode: str, tab_label: str) -> None:
    """Generic discussion tab renderer for all 3 modes."""
    st.subheader(f"{tab_label} Discussion Guide")

    if not _ENGINE:
        st.warning(
            "discussion_guidance_engine is not available. "
            "Cannot generate discussion briefs."
        )
        return

    # Party selection
    parties = _get_party_list(mode)
    party_info: dict = {}

    if parties:
        party_names = ["-- Select --"] + [_party_display_name(p) for p in parties]
        selected_idx = st.selectbox(
            f"Select {tab_label}",
            range(len(party_names)),
            format_func=lambda x: party_names[x],
            key=f"disc_{mode}_party",
        )
        if selected_idx > 0:
            party_info = parties[selected_idx - 1]
    else:
        st.info(
            f"No {tab_label.lower()} records found in the database. "
            "You can enter details manually below."
        )

    # Manual input fields
    with st.expander("Override / Enter Details Manually", expanded=not bool(party_info)):
        mc1, mc2 = st.columns(2)
        with mc1:
            manual_name = st.text_input(
                "Party Name",
                value=party_info.get("name", ""),
                key=f"disc_{mode}_name",
            )
            manual_city = st.text_input(
                "City",
                value=party_info.get("city", ""),
                key=f"disc_{mode}_city",
            )
        with mc2:
            manual_state = st.text_input(
                "State",
                value=party_info.get("state", ""),
                key=f"disc_{mode}_state",
            )
            manual_country = st.text_input(
                "Country",
                value=party_info.get("country", "India"),
                key=f"disc_{mode}_country",
            )

        if manual_name:
            party_info["name"] = manual_name
        if manual_city:
            party_info["city"] = manual_city
        if manual_state:
            party_info["state"] = manual_state
        if manual_country:
            party_info["country"] = manual_country

    # Cargo parameters
    st.markdown("##### Cargo Parameters")
    param_c1, param_c2, param_c3 = st.columns(3)
    with param_c1:
        cargo_type = st.selectbox(
            "Cargo Type",
            ["VG-30", "VG-40", "VG-10", "60/70", "80/100", "Bulk", "Drummed"],
            key=f"disc_{mode}_cargo",
        )
    with param_c2:
        quantity = st.number_input(
            "Quantity (MT)",
            min_value=0, value=500, step=50,
            key=f"disc_{mode}_qty",
        )
    with param_c3:
        target_price = st.number_input(
            "Target Price (Rs/MT)",
            min_value=0, value=0, step=100,
            key=f"disc_{mode}_price",
            help="Leave 0 for engine to suggest optimal price",
        )

    # Additional context
    additional_c1, additional_c2 = st.columns(2)
    with additional_c1:
        delivery_mode = st.selectbox(
            "Delivery Mode",
            ["Bulk (Tanker)", "Drummed", "Ex-Refinery", "FOB", "CFR", "CIF"],
            key=f"disc_{mode}_delivery",
        )
    with additional_c2:
        urgency = st.selectbox(
            "Urgency",
            ["Normal", "Urgent", "Critical"],
            key=f"disc_{mode}_urgency",
        )

    # Build enriched party info
    enriched_info = {
        **party_info,
        "cargo_type": cargo_type,
        "quantity_mt": quantity,
        "target_price": target_price if target_price > 0 else None,
        "delivery_mode": delivery_mode,
        "urgency": urgency,
    }

    # Generate Brief button
    st.markdown("---")
    if st.button(
        "Generate Discussion Brief",
        type="primary",
        key=f"disc_{mode}_generate",
        disabled=not enriched_info.get("name"),
    ):
        if not enriched_info.get("name"):
            st.error("Please select or enter a party name.")
            return

        with st.spinner(f"Generating {tab_label.lower()} discussion brief..."):
            try:
                brief = prepare_discussion(mode=mode, party_info=enriched_info)
            except Exception as exc:
                LOG.error("Discussion brief generation failed: %s", exc)
                st.error(f"Brief generation failed: {exc}")
                return

        if brief:
            st.session_state[f"disc_{mode}_brief"] = brief
        else:
            st.warning("The engine returned no brief. Check the input parameters.")

    # Display cached brief
    cached_brief = st.session_state.get(f"disc_{mode}_brief")
    if cached_brief:
        st.markdown("---")
        _render_discussion_brief(st, cached_brief)


# ── Main Render ──────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function -- called from dashboard.py routing."""
    import streamlit as st

    st.title("Discussion Guidance")
    st.caption(
        "AI-powered discussion briefs with talking points, pricing, "
        "objection handling, and WhatsApp drafts"
    )

    tabs = st.tabs([
        "Supplier Discussion",
        "Importer Discussion",
        "Local Trader Discussion",
    ])

    with tabs[0]:
        _render_discussion_tab(st, mode="supplier", tab_label="Supplier")

    with tabs[1]:
        _render_discussion_tab(st, mode="importer", tab_label="Importer")

    with tabs[2]:
        _render_discussion_tab(st, mode="trader", tab_label="Local Trader")
