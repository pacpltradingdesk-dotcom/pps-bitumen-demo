"""
Daily Log Entry Panel
Simple logging interface for sales team to record interactions,
market intelligence, deal updates, and observations for AI learning.
"""
import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(*a, **kw):
        pass

import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")


def render():
    """Render the Daily Log Entry panel."""
    display_badge("manual")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e3a5f,#2d6a4f);color:white;
                padding:15px 20px;border-radius:10px;margin-bottom:15px;">
      <div style="font-size:1.2rem;font-weight:700;">Daily Log Entry</div>
      <div style="font-size:0.8rem;opacity:0.8;">Record interactions, intel, and observations</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Customer Interaction", "Market Intel",
        "Deal Update", "AI Notes", "History"
    ])

    # ─── Tab 1: Customer Interaction ─────────────────────────────────
    with tab1:
        with st.form("customer_interaction_form", clear_on_submit=True):
            st.markdown("##### Log Customer Interaction")

            # Customer dropdown from database
            customers = _get_customer_list()
            customer_name = st.selectbox(
                "Customer", options=customers,
                index=0 if customers else None,
                key="ci_customer")

            channel = st.radio("Channel",
                               ["Call", "WhatsApp", "Email", "Meeting", "Site Visit"],
                               horizontal=True, key="ci_channel")

            notes = st.text_area("Notes / Discussion Summary",
                                 placeholder="What was discussed?",
                                 key="ci_notes")

            outcome = st.selectbox("Outcome", [
                "will_callback", "order_placed", "quote_requested",
                "price_objection", "needs_time", "rejected", "no_answer"
            ], key="ci_outcome")

            followup_date = st.date_input("Follow-up Date (optional)",
                                          value=None, key="ci_followup")

            if st.form_submit_button("Save Interaction", type="primary"):
                if customer_name and notes:
                    _save_log_entry(
                        entry_type="customer_interaction",
                        customer_name=customer_name,
                        channel=channel,
                        notes=notes,
                        outcome=outcome,
                        followup_date=followup_date.strftime("%Y-%m-%d") if followup_date else None)
                    st.success("Interaction logged!")
                    if followup_date:
                        _create_crm_task(customer_name, channel, followup_date, notes)
                        st.info(f"CRM task created for {followup_date}")
                else:
                    st.warning("Please select customer and add notes")

    # ─── Tab 2: Market Intel ─────────────────────────────────────────
    with tab2:
        with st.form("market_intel_form", clear_on_submit=True):
            st.markdown("##### Log Market Intelligence")

            intel_source = st.text_input("Source",
                                         placeholder="e.g. Competitor salesperson, Market rumor",
                                         key="mi_source")

            intel_notes = st.text_area("Intelligence",
                                       placeholder="e.g. Competitor X offering VG30 at Rs38,500 in Ahmedabad",
                                       key="mi_notes")

            confidence = st.radio("Confidence Level",
                                  ["High", "Medium", "Low"],
                                  horizontal=True, key="mi_confidence")

            if st.form_submit_button("Save Intel", type="primary"):
                if intel_notes:
                    _save_log_entry(
                        entry_type="market_intel",
                        intel_source=intel_source,
                        notes=intel_notes,
                        intel_confidence=confidence)
                    st.success("Market intelligence logged!")
                else:
                    st.warning("Please add intelligence details")

    # ─── Tab 3: Deal Update ──────────────────────────────────────────
    with tab3:
        with st.form("deal_update_form", clear_on_submit=True):
            st.markdown("##### Log Deal Update")

            deals = _get_deal_list()
            deal_ref = st.selectbox("Deal Reference",
                                     options=deals if deals else ["No active deals"],
                                     key="du_deal")

            status_change = st.selectbox("Status Change", [
                "enquiry_received", "quote_sent", "negotiation",
                "po_received", "dispatched", "delivered",
                "payment_received", "deal_lost", "no_change"
            ], key="du_status")

            price_discussed = st.number_input("Price Discussed (Rs/MT)",
                                               min_value=0, value=0,
                                               key="du_price")

            deal_notes = st.text_area("Notes",
                                       placeholder="Key discussion points",
                                       key="du_notes")

            if st.form_submit_button("Save Update", type="primary"):
                if deal_notes:
                    _save_log_entry(
                        entry_type="deal_update",
                        customer_name=deal_ref,
                        notes=deal_notes,
                        outcome=status_change,
                        metadata={"price_discussed": price_discussed})
                    st.success("Deal update logged!")
                else:
                    st.warning("Please add notes")

    # ─── Tab 4: AI Notes ─────────────────────────────────────────────
    with tab4:
        with st.form("ai_notes_form", clear_on_submit=True):
            st.markdown("##### Observations for AI Learning")
            st.caption("Share patterns, observations, or corrections to help improve AI predictions")

            pattern_type = st.selectbox("Category", [
                "pricing_pattern", "demand_observation", "competitor_behavior",
                "logistics_insight", "seasonal_trend", "customer_preference", "other"
            ], key="ai_type")

            observation = st.text_area("Observation",
                                        placeholder="e.g. VG30 demand increases 20% when NHAI releases new tenders",
                                        key="ai_notes")

            if st.form_submit_button("Save Observation", type="primary"):
                if observation:
                    _save_log_entry(
                        entry_type="ai_note",
                        notes=observation,
                        metadata={"pattern_type": pattern_type})
                    st.success("Observation logged for AI learning!")
                else:
                    st.warning("Please add your observation")

    # ─── Tab 5: History ──────────────────────────────────────────────
    with tab5:
        st.markdown("##### Recent Log Entries")
        hist_date = st.date_input("Filter by date", value=datetime.date.today(),
                                   key="hist_date")
        logs = _get_logs(hist_date.strftime("%Y-%m-%d"))

        if not logs:
            st.info("No entries for this date")
        else:
            for log in logs:
                entry_type = log.get("entry_type", "unknown")
                type_icons = {
                    "customer_interaction": "\ud83d\udcde",
                    "market_intel": "\ud83d\udcca",
                    "deal_update": "\ud83d\udcbc",
                    "ai_note": "\ud83e\udde0",
                }
                icon = type_icons.get(entry_type, "\ud83d\udcdd")
                with st.expander(
                    f"{icon} {entry_type.replace('_', ' ').title()} — "
                    f"{log.get('customer_name', log.get('intel_source', 'N/A'))} "
                    f"({log.get('created_at', '')[:16]})"
                ):
                    st.markdown(f"**Notes:** {log.get('notes', '')}")
                    if log.get("channel"):
                        st.markdown(f"**Channel:** {log['channel']}")
                    if log.get("outcome"):
                        st.markdown(f"**Outcome:** {log['outcome']}")
                    if log.get("followup_date"):
                        st.markdown(f"**Follow-up:** {log['followup_date']}")
                    if log.get("intel_confidence"):
                        st.markdown(f"**Confidence:** {log['intel_confidence']}")


# ─── Helper Functions ────────────────────────────────────────────────────────

def _get_customer_list() -> list:
    """Get list of customer names from database."""
    try:
        from database import get_all_customers
        customers = get_all_customers()
        return [c.get("name", "Unknown") for c in customers]
    except Exception:
        return ["No customers loaded"]


def _get_deal_list() -> list:
    """Get list of active deals."""
    try:
        from database import get_all_deals
        deals = get_all_deals()
        return [f"{d.get('deal_number', 'N/A')} - {d.get('destination', '')}"
                for d in deals[:20]]
    except Exception:
        return []


def _save_log_entry(entry_type: str, customer_name: str = "",
                    channel: str = "", notes: str = "",
                    outcome: str = "", followup_date: str = None,
                    intel_source: str = "", intel_confidence: str = "",
                    metadata: dict = None):
    """Save a daily log entry to database."""
    import json
    try:
        from database import insert_daily_log
        insert_daily_log({
            "log_date": datetime.datetime.now(IST).strftime("%Y-%m-%d"),
            "author": "Sales Team",
            "entry_type": entry_type,
            "customer_name": customer_name,
            "channel": channel,
            "notes": notes,
            "outcome": outcome,
            "followup_date": followup_date,
            "intel_source": intel_source,
            "intel_confidence": intel_confidence,
            "metadata": json.dumps(metadata) if metadata else None,
        })
    except Exception as e:
        st.error(f"Failed to save: {e}")


def _create_crm_task(customer_name: str, channel: str,
                     followup_date, notes: str):
    """Auto-create CRM follow-up task."""
    try:
        from crm_engine import add_task
        due_str = followup_date.strftime("%Y-%m-%d") + " 10:00"
        add_task(
            client_name=customer_name,
            task_type=channel,
            due_date_str=due_str,
            priority="High",
            note=f"Follow-up from daily log: {notes[:100]}",
            automated=True)
    except Exception:
        pass


def _get_logs(date_str: str) -> list:
    """Get daily logs for a specific date."""
    try:
        from database import get_daily_logs
        return get_daily_logs(log_date=date_str, limit=50)
    except Exception:
        return []
