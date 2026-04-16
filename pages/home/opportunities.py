import streamlit as st
import pandas as pd
import datetime

from components.empty_state import render_empty_state


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
    # Phase 2: standardized refresh bar (clears caches + reruns)
    try:
        from components.refresh_bar import render_refresh_bar
        render_refresh_bar('opportunities')
    except Exception:
        pass
    # Phase 4: active customer banner — shows persistent customer context
    try:
        from navigation_engine import render_active_context_strip
        render_active_context_strip()
    except Exception:
        pass
    _today_str = datetime.date.today().strftime("%d %b %Y")
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            border-bottom:2px solid var(--sandal,#e8dcc8);
            padding-bottom:6px;
            margin-bottom:10px;">
  <div style="display:flex;align-items:baseline;gap:10px;">
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">🔍 Opportunities (Auto-Discovered)</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">Intelligence</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="background:#e8f5ee;color:#2d6a4f;font-size:0.68rem;font-weight:700;padding:2px 9px;border-radius:12px;border:1px solid #b7dfc9;">AI-Powered</span>
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.info("Auto-discovers profitable opportunities from market changes. Scan runs daily + on price changes.")
    try:
        from opportunity_engine import OpportunityEngine, get_all_opportunities, mark_opportunity_status
        import json as _opp_json

        _opp_eng = OpportunityEngine()

        # Auto-scan on first visit of the session
        if not st.session_state.get("_opp_scanned"):
            try:
                _opp_eng.scan_all_opportunities()
                st.session_state["_opp_scanned"] = True
            except Exception:
                pass

        _opp_tabs = st.tabs(["New Opportunities", "Today's Targets", "Scan Now", "All History"])

        with _opp_tabs[0]:
            _new_opps = get_all_opportunities(status="new")
            if _new_opps:
                st.markdown(f"**{len(_new_opps)} new opportunities found**")
                for _oi, _opp in enumerate(_new_opps[:20]):
                    _otype = _opp.get("type", "")
                    _otitle = _opp.get("title", "Opportunity")
                    _opri = _opp.get("priority", "P2")
                    _pri_colors = {"P0": "🔴", "P1": "🟡", "P2": "🔵"}
                    with st.expander(f"{_pri_colors.get(_opri, '🔵')} [{_opri}] {_otitle}"):
                        st.markdown(_opp.get("description", ""))
                        if _opp.get("recommended_action"):
                            st.success(f"**Action:** {_opp['recommended_action']}")
                        _oc1, _oc2, _oc3 = st.columns(3)
                        _oc1.metric("Savings/MT", _fmt_inr(_opp.get("savings_per_mt", 0)))
                        _oc2.metric("Est. Margin", _fmt_inr(_opp.get("estimated_margin_per_mt", 0)))
                        _oc3.metric("Est. Volume", f"{_opp.get('estimated_volume_mt', 0):.0f} MT")
                        if _opp.get("whatsapp_template"):
                            with st.expander("WhatsApp Template"):
                                st.code(_opp["whatsapp_template"], language=None)
                        if _opp.get("call_script"):
                            with st.expander("Call Script"):
                                st.code(_opp["call_script"], language=None)
                        if st.button(f"Mark Contacted", key=f"opp_contact_{_oi}"):
                            # Find real index in full opportunity list
                            _all_opps_list = get_all_opportunities()
                            for _real_idx, _real_opp in enumerate(_all_opps_list):
                                if (_real_opp.get("title") == _opp.get("title")
                                        and _real_opp.get("created_at") == _opp.get("created_at")):
                                    mark_opportunity_status(_real_idx, "contacted")
                                    break
                            st.rerun()
            else:
                render_empty_state(
                    key="opp_new",
                    icon="🔍",
                    title="Abhi koi nayi opportunity nahi",
                    hint="Fresh scan chalao ya market signals check karo.",
                    cta_label="🔄 Run Scan Now",
                    on_click=_opp_eng.scan_all_opportunities,
                )

        with _opp_tabs[1]:
            _recs = _opp_eng.get_todays_recommendations()
            st.subheader("Buyers to Call Today")
            _b2c = _recs.get("buyers_to_call", [])
            if _b2c:
                for _bc in _b2c[:10]:
                    st.markdown(f"- **{_bc.get('customer_name', 'Unknown')}** ({_bc.get('customer_city', '')}) — "
                                f"Save {_fmt_inr(_bc.get('savings_per_mt', 0))}/MT | {_bc.get('priority', 'P2')}")
            else:
                render_empty_state(
                    key="opp_buyers",
                    icon="📞",
                    title="Koi buyer flag nahi hua aaj",
                    hint="Pricing calculator se quote bhejo — naya lead yahan aajayega.",
                    cta_label="→ Open Pricing Calculator",
                    cta_target="🧮 Pricing Calculator",
                )

            st.subheader("Follow-ups Due")
            _fud = _recs.get("followups_due", [])
            if _fud:
                for _fu in _fud[:10]:
                    st.markdown(f"- {_fu.get('title', _fu.get('customer_name', 'Task'))} — {_fu.get('status', '')}")
            else:
                render_empty_state(
                    key="opp_followups",
                    icon="✅",
                    title="Koi follow-up due nahi",
                    hint="CRM mein jaake manual task add karo ya automation rules check karo.",
                    cta_label="→ Open CRM & Tasks",
                    cta_target="🎯 CRM & Tasks",
                    tone="success",
                )

            st.subheader("Reactivation Targets")
            _react = _recs.get("reactivation_targets", [])
            if _react:
                for _rt in _react[:5]:
                    st.markdown(f"- **{_rt.get('customer_name', _rt.get('title', 'Target'))}** — {_rt.get('type', '')}")
            else:
                render_empty_state(
                    key="opp_react",
                    icon="💤",
                    title="Koi dormant customer abhi flag nahi hua",
                    hint="Broadcast bhejke sleepy contacts ko jagao.",
                    cta_label="→ Open Share Center",
                    cta_target="📤 Share Center",
                )

        with _opp_tabs[2]:
            st.markdown("Run a fresh opportunity scan across all data sources.")
            if st.button("Run Full Opportunity Scan", type="primary", use_container_width=True):
                with st.spinner("Scanning for opportunities..."):
                    _scan_results = _opp_eng.scan_all_opportunities()
                st.success(f"Scan complete! Found {len(_scan_results)} opportunities.")
                st.rerun()

        with _opp_tabs[3]:
            _all_opps = get_all_opportunities()
            if _all_opps:
                _opp_df = pd.DataFrame(_all_opps)
                _cols_to_show = ["type", "title", "priority", "status", "savings_per_mt", "created_at"]
                _display_cols = [c for c in _cols_to_show if c in _opp_df.columns]
                st.dataframe(_opp_df[_display_cols], use_container_width=True, hide_index=True)
            else:
                render_empty_state(
                    key="opp_history",
                    icon="📜",
                    title="History abhi khaali hai",
                    hint="Pehla scan chalate hi yahan record banta jayega.",
                    cta_label="🔄 Run First Scan",
                    on_click=_opp_eng.scan_all_opportunities,
                )

    except Exception as _e:
        st.error(f"Opportunities failed to load: {_e}")
