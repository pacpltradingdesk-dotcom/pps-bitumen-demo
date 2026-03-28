"""
Director Daily Intelligence Center
Morning briefing for company director with yesterday summary,
today's priorities, and 15-day forward outlook.
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
import json
import pytz

IST = pytz.timezone("Asia/Kolkata")


def _fmt_inr(amount) -> str:
    if amount is None or amount == 0:
        return "\u20b90"
    try:
        amount = float(amount)
        if amount < 0:
            return f"-{_fmt_inr(-amount)}"
        if amount >= 10000000:
            return f"\u20b9{amount / 10000000:.1f} Cr"
        if amount >= 100000:
            return f"\u20b9{amount / 100000:.1f} L"
        s = str(int(amount))
        if len(s) <= 3:
            return f"\u20b9{s}"
        last3 = s[-3:]
        remaining = s[:-3]
        groups = []
        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        return f"\u20b9{','.join(groups)},{last3}"
    except (ValueError, TypeError):
        return str(amount)


def render():
    """Render the Director Daily Intelligence Center page."""
    display_badge("real-time")

    from director_briefing_engine import DirectorBriefingEngine
    engine = DirectorBriefingEngine()

    # Date selector for historical review
    col_title, col_date = st.columns([3, 1])
    with col_date:
        selected_date = st.date_input("Briefing Date",
                                       value=datetime.date.today(),
                                       key="director_date")

    briefing = engine.generate_briefing(
        target_date=selected_date.strftime("%Y-%m-%d"))

    # ─── Greeting Banner ─────────────────────────────────────────────
    with col_title:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#1e3a5f,#2d6a4f);color:white;
                    padding:20px 25px;border-radius:12px;margin-bottom:15px;">
          <div style="font-size:1.6rem;font-weight:700;">
            {briefing.get('greeting', 'Hello')}, Director
          </div>
          <div style="font-size:0.85rem;opacity:0.85;margin-top:4px;">
            PPS Anantam Agentic AI Eco System &nbsp;|&nbsp;
            {briefing.get('timestamp', '')}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ─── Two-Column: Yesterday + Today ───────────────────────────────
    col_yes, col_tod = st.columns(2)

    with col_yes:
        st.markdown("#### Yesterday Summary")
        yesterday = briefing.get("yesterday_summary", {})
        deals = yesterday.get("deals_closed", {})
        comms = yesterday.get("communications", {})
        market = yesterday.get("market_movement", {})

        m1, m2 = st.columns(2)
        with m1:
            st.metric("Deals Closed", deals.get("count", 0))
            st.metric("Brent Crude",
                      f"${market.get('brent_price', 'N/A')}",
                      f"{market.get('brent_pct', 0):+.1f}%")
        with m2:
            st.metric("Communications", comms.get("total", 0))
            st.metric("USD/INR",
                      f"{market.get('fx_rate', 'N/A')}",
                      f"{market.get('fx_pct', 0):+.1f}%")

        outstanding = yesterday.get("outstanding_collections", {})
        if outstanding.get("total", 0) > 0:
            st.info(f"Outstanding: {_fmt_inr(outstanding['total'])}")

    with col_tod:
        st.markdown("#### Today's Priority Actions")
        actions = briefing.get("today_actions", {})
        buyers = actions.get("buyers_to_call", [])
        suppliers = actions.get("suppliers_to_negotiate", [])
        followups = actions.get("followups_due", [])

        if buyers:
            st.markdown("**Buyers to Call:**")
            for i, b in enumerate(buyers[:5], 1):
                name = b.get("name", b.get("client_name", "Unknown"))
                reason = b.get("reason", b.get("task_type", ""))
                st.markdown(f"{i}. **{name}** — {reason}")
        else:
            st.caption("No priority calls today")

        if suppliers:
            st.markdown("**Suppliers to Negotiate:**")
            for s in suppliers[:3]:
                name = s.get("name", "Unknown")
                st.markdown(f"- {name}")

        if followups:
            st.caption(f"{len(followups)} follow-ups due today")

    # ─── 15-Day Outlook ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 15-Day Forward Outlook")

    outlook = briefing.get("fifteen_day_outlook", {})
    demand = outlook.get("demand_score", {})
    price = outlook.get("price_direction", {})
    strategy = outlook.get("stock_strategy", {})

    o1, o2, o3 = st.columns(3)
    with o1:
        score = demand.get("total_score", 0)
        label = demand.get("label", "N/A")
        st.markdown(f"""
        <div style="text-align:center;padding:15px;background:{demand.get('color', '#c9a84c')}20;
                    border-radius:10px;border-left:4px solid {demand.get('color', '#c9a84c')};">
          <div style="font-size:2rem;font-weight:700;color:{demand.get('color', '#c9a84c')};">{score}</div>
          <div style="font-size:0.8rem;color:#555;">DEMAND / 100</div>
          <div style="font-size:0.85rem;font-weight:600;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    with o2:
        direction = price.get("direction", "STABLE")
        confidence = price.get("confidence_pct", 0)
        arrow = price.get("arrow", "\u25c6")
        dir_color = "#b85c38" if direction == "UP" else "#2d6a4f" if direction == "DOWN" else "#c9a84c"
        st.markdown(f"""
        <div style="text-align:center;padding:15px;background:{dir_color}20;
                    border-radius:10px;border-left:4px solid {dir_color};">
          <div style="font-size:2rem;font-weight:700;color:{dir_color};">{arrow} {direction}</div>
          <div style="font-size:0.8rem;color:#555;">PRICE DIRECTION</div>
          <div style="font-size:0.85rem;font-weight:600;">{confidence}% confidence</div>
        </div>
        """, unsafe_allow_html=True)

    with o3:
        strat = strategy.get("strategy", "HOLD")
        strat_color = strategy.get("color", "#1e3a5f")
        st.markdown(f"""
        <div style="text-align:center;padding:15px;background:{strat_color}20;
                    border-radius:10px;border-left:4px solid {strat_color};">
          <div style="font-size:1.5rem;font-weight:700;color:{strat_color};">{strat}</div>
          <div style="font-size:0.8rem;color:#555;">STRATEGY</div>
          <div style="font-size:0.85rem;">{strategy.get('urgency', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    # Strategy rationale
    rationale = strategy.get("rationale", [])
    if rationale:
        with st.expander("Strategy Rationale", expanded=True):
            for r in rationale:
                st.markdown(f"- {r}")

    # Demand score breakdown
    components = demand.get("components", {})
    if components:
        with st.expander("Demand Score Breakdown"):
            for key, comp in components.items():
                st.markdown(f"- **{key.replace('_', ' ').title()}**: "
                            f"{comp.get('weighted', 0):.0f} pts — {comp.get('detail', '')}")

    # Price signal details
    signals = price.get("signals", {})
    if signals:
        with st.expander("Price Signal Details"):
            for key, sig in signals.items():
                st.markdown(f"- **{key.replace('_', ' ').title()}** "
                            f"({sig.get('weight', 0)*100:.0f}% weight): "
                            f"{sig.get('direction', '')} — {sig.get('detail', '')}")

    # ─── Sparkline Charts ────────────────────────────────────────────
    sparklines = briefing.get("sparklines", {})
    brent_data = sparklines.get("brent", [])
    fx_data = sparklines.get("fx", [])

    if brent_data or fx_data:
        st.markdown("---")
        st.markdown("#### 7-Day Trends")
        sc1, sc2 = st.columns(2)
        with sc1:
            if brent_data:
                st.line_chart(brent_data, use_container_width=True, height=150)
                st.caption("Brent Crude ($/bbl)")
        with sc2:
            if fx_data:
                st.line_chart(fx_data, use_container_width=True, height=150)
                st.caption("USD/INR Rate")

    # ─── Opportunities ───────────────────────────────────────────────
    opps = briefing.get("opportunities", [])
    if opps:
        st.markdown("---")
        st.markdown("#### Discovered Opportunities")
        for opp in opps[:5]:
            priority = opp.get("priority", "P2")
            p_color = "#b85c38" if priority == "P0" else "#c9a84c" if priority == "P1" else "#1e3a5f"
            st.markdown(f"""
            <div style="padding:8px 12px;margin:4px 0;border-left:3px solid {p_color};
                        background:{p_color}10;border-radius:0 6px 6px 0;">
              <span style="color:{p_color};font-weight:600;">[{priority}]</span>
              {opp.get('title', opp.get('description', '')[:80])}
            </div>
            """, unsafe_allow_html=True)

    # ─── Actions ─────────────────────────────────────────────────────
    st.markdown("---")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        if st.button("Refresh Briefing", use_container_width=True):
            st.rerun()
    with ac2:
        if st.button("Save to History", use_container_width=True):
            engine.save_briefing_to_db(briefing)
            st.success("Briefing saved")
    with ac3:
        if st.button("Copy WhatsApp Summary", use_container_width=True):
            wa_text = engine.format_whatsapp_summary(briefing)
            st.code(wa_text, language=None)
