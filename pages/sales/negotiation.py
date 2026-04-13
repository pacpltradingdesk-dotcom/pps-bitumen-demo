import streamlit as st
import datetime


def _fmt_inr(amount) -> str:
    """Format INR with Indian comma system."""
    try:
        amount = int(float(amount))
        s = str(abs(amount))
        if len(s) <= 3:
            formatted = s
        else:
            last3 = s[-3:]
            remaining = s[:-3]
            groups = []
            while remaining:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            formatted = ",".join(groups) + "," + last3
        prefix = "-" if amount < 0 else ""
        return f"{prefix}\u20b9{formatted}"
    except Exception:
        return f"\u20b9{amount}"


def render():
    _today_str = datetime.date.today().strftime("%d %b %Y")
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            border-bottom:2px solid var(--sandal,#e8dcc8);
            padding-bottom:6px;
            margin-bottom:10px;">
  <div style="display:flex;align-items:baseline;gap:10px;">
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">🤝 Negotiation Assistant</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">Sales & CRM</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="background:#e8f5ee;color:#2d6a4f;font-size:0.68rem;font-weight:700;padding:2px 9px;border-radius:12px;border:1px solid #b7dfc9;">AI-Powered</span>
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.info("Prepares complete briefing packs for sales team before customer calls.")
    try:
        from negotiation_engine import NegotiationAssistant, get_full_objection_library

        _neg = NegotiationAssistant()
        _neg_tabs = st.tabs(["Prepare Brief", "Objection Library"])

        with _neg_tabs[0]:
            st.subheader("Customer Negotiation Brief")
            _nc1, _nc2 = st.columns(2)
            with _nc1:
                _neg_cust = st.text_input("Customer Name", placeholder="e.g. L&T Construction")
                _neg_city = st.text_input("City", placeholder="e.g. Ahmedabad")
            with _nc2:
                _neg_grade = st.selectbox("Grade", ["VG30", "VG10", "VG40", "CRMB-55", "CRMB-60", "PMB", "Emulsion"])
                _neg_qty = st.number_input("Quantity (MT)", min_value=10, max_value=10000, value=100, step=10)
            _neg_last_price = st.number_input("Customer's Last Purchase Price (INR/MT, optional)", min_value=0, value=0, step=500)

            if st.button("Generate Negotiation Brief", type="primary", use_container_width=True):
                if _neg_cust and _neg_city:
                    with st.spinner("Preparing negotiation brief..."):
                        _brief = _neg.prepare_negotiation_brief(
                            customer_name=_neg_cust,
                            city=_neg_city,
                            grade=_neg_grade,
                            quantity_mt=_neg_qty,
                            customer_last_price=_neg_last_price if _neg_last_price > 0 else None
                        )

                    # Display brief
                    st.subheader("Negotiation Brief")

                    # Customer Profile
                    _cp = _brief.get("customer_profile", {})
                    st.markdown(f"**Customer:** {_cp.get('name', _neg_cust)} | "
                                f"**City:** {_cp.get('city', _neg_city)} | "
                                f"**Stage:** {_cp.get('relationship', 'new')}")

                    # Cost & Offers
                    _cost = _brief.get("our_best_cost", {})
                    if _cost:
                        _bc1, _bc2 = st.columns(2)
                        _bc1.metric("Best Landed Cost", f"{_fmt_inr(_cost.get('landed_cost', 0))}/MT")
                        _bc1.caption(f"Source: {_cost.get('source', 'N/A')}")
                        if _brief.get("walk_away_price"):
                            _bc2.metric("Walk-Away Price", _brief["walk_away_price"]["label"])

                    # Offer Tiers
                    _tiers = _brief.get("offer_tiers")
                    if _tiers:
                        st.markdown("**3-Tier Offer Pricing:**")
                        _tc1, _tc2, _tc3 = st.columns(3)
                        for _col, _tier_key, _color in [(_tc1, "aggressive", "#2d6a4f"), (_tc2, "balanced", "#1e3a5f"), (_tc3, "premium", "#c9a84c")]:
                            _tier = _tiers.get(_tier_key, {})
                            _col.markdown(f"""
<div style="background:#faf7f2;border:2px solid {_color};border-radius:8px;padding:12px;text-align:center;">
  <div style="font-size:0.68rem;font-weight:700;color:{_color};text-transform:uppercase;">{_tier.get('label', _tier_key)}</div>
  <div style="font-size:1.2rem;font-weight:800;color:#1e3a5f;">{_fmt_inr(_tier.get('price', 0))}</div>
  <div style="font-size:0.72rem;color:#64748b;">Margin: {_fmt_inr(_tier.get('margin', 0))}/MT</div>
</div>""", unsafe_allow_html=True)

                    # Client Benefit
                    _cb = _brief.get("client_benefit")
                    if _cb:
                        st.info(_cb.get("narrative", ""))

                    # Market Context
                    _mc = _brief.get("market_context", {})
                    if _mc.get("narrative"):
                        st.markdown(f"**Market Context:** {_mc['narrative']}")

                    # Objection Handling
                    _objs = _brief.get("objection_handling", [])
                    if _objs:
                        st.markdown("**Top Objections & Responses:**")
                        for _obj in _objs:
                            with st.expander(f"{_obj['objection']}"):
                                st.markdown(f"**Quick Reply:** {_obj['short_reply']}")
                                st.markdown(f"**Detailed:** {_obj['detailed_reply']}")
                                st.caption(f"Confidence: {_obj['confidence_booster']}")

                    # Closing Strategy
                    _cs = _brief.get("closing_strategy", {})
                    if _cs.get("recommended"):
                        st.markdown(f"**Recommended Close:** {_cs['recommended']['technique']}")
                        st.success(f'"{_cs["recommended"]["script"]}"')
                else:
                    st.warning("Please enter customer name and city.")

        with _neg_tabs[1]:
            st.subheader("Complete Objection Library")
            _obj_lib = get_full_objection_library()
            for _ok, _ov in _obj_lib.items():
                with st.expander(f"{_ov['objection']}"):
                    st.markdown(f"**Quick Reply:** {_ov['short_reply']}")
                    st.markdown(f"**Detailed:** {_ov['detailed_reply']}")
                    st.caption(f"Confidence Booster: {_ov['confidence_booster']}")

    except Exception as _e:
        st.error(f"Negotiation Assistant failed to load: {_e}")

    # ── Smart navigation: contextual next steps ──
    try:
        from navigation_engine import render_next_step_cards
        render_next_step_cards("🤝 Negotiation Assistant")
        st.session_state["_ns_rendered_inline"] = True
    except Exception:
        pass
