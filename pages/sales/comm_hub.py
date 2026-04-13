import streamlit as st
import pandas as pd
import datetime


def render():
    _today_str = datetime.date.today().strftime("%d %b %Y")
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            border-bottom:2px solid var(--sandal,#e8dcc8);
            padding-bottom:6px;
            margin-bottom:10px;">
  <div style="display:flex;align-items:baseline;gap:10px;">
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">💬 Communication Hub</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">Sales & CRM</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="background:#e8f5ee;color:#2d6a4f;font-size:0.68rem;font-weight:700;padding:2px 9px;border-radius:12px;border:1px solid #b7dfc9;">Templates</span>
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.info("Auto-generates WhatsApp, Email, and Call scripts for sales team.")

    # Pull context (customer name + city + grade) for pre-fill
    _ctx_cust = ""; _ctx_city_v = ""; _ctx_grade = "VG30"
    try:
        from navigation_engine import get_context
        _ctx_cust   = get_context("customer_name", "") or ""
        _ctx_city_v = get_context("customer_city", "") or ""
        _ctx_grade  = get_context("customer_grade", "VG30") or "VG30"
    except Exception:
        pass

    try:
        from communication_engine import CommunicationHub

        _comm = CommunicationHub()
        _comm_tabs = st.tabs(["Generate Message", "Follow-up Sequence", "Communication Log"])

        with _comm_tabs[0]:
            _msg_type = st.selectbox("Message Type", ["Offer", "Follow-up", "Reactivation", "Payment Reminder"])
            _cc1, _cc2 = st.columns(2)
            with _cc1:
                _comm_cust = st.text_input("Customer Name", value=_ctx_cust,
                                           placeholder="e.g. L&T Construction", key="comm_cust")
                _comm_city = st.text_input("City", value=_ctx_city_v,
                                           placeholder="e.g. Mumbai", key="comm_city")
            with _cc2:
                _grade_opts = ["VG30", "VG10", "VG40"]
                _grade_idx = _grade_opts.index(_ctx_grade) if _ctx_grade in _grade_opts else 0
                _comm_grade = st.selectbox("Grade", _grade_opts, index=_grade_idx, key="comm_grade")
                _comm_qty = st.number_input("Quantity (MT)", min_value=10, value=100, step=10, key="comm_qty")
            _comm_price = st.number_input("Price (INR/MT)", min_value=20000, max_value=80000, value=42000, step=500, key="comm_price")

            _channel = st.radio("Channel", ["WhatsApp", "Email", "Call Script"], horizontal=True)

            if st.button("Generate", type="primary", use_container_width=True, key="comm_gen"):
                if _comm_cust:
                    if _channel == "WhatsApp":
                        if _msg_type == "Offer":
                            _msg = _comm.whatsapp_offer(_comm_cust, _comm_city, _comm_grade, _comm_qty, _comm_price)
                        elif _msg_type == "Follow-up":
                            _msg = _comm.whatsapp_followup(_comm_cust)
                        elif _msg_type == "Reactivation":
                            _msg = _comm.whatsapp_reactivation(_comm_cust, _comm_city, _comm_price, _comm_price + 2000, 2000)
                        else:
                            _msg = _comm.whatsapp_payment_reminder(_comm_cust, 500000)
                        st.text_area("WhatsApp Message (copy & send):", _msg, height=300)
                    elif _channel == "Email":
                        if _msg_type == "Offer":
                            _email = _comm.email_offer(_comm_cust, _comm_city, _comm_grade, _comm_qty, _comm_price)
                        else:
                            _email = _comm.email_followup(_comm_cust, city=_comm_city, price=_comm_price)
                        st.text_input("Subject:", _email.get("subject", ""), key="email_subj_out")
                        st.text_area("Body:", _email.get("body", ""), height=350)
                    else:
                        _script = _comm.call_script_offer(_comm_cust, _comm_city, _comm_grade, _comm_price)
                        st.text_area("Call Script:", _script, height=400)

                    _comm.log_communication(_comm_cust, _channel, _msg_type)
                    st.success(f"{_channel} {_msg_type} generated and logged.")
                else:
                    st.warning("Please enter customer name.")

        with _comm_tabs[1]:
            st.subheader("5-Touch Follow-up Sequence")
            _fu_cust = st.text_input("Customer", key="fu_cust")
            _fu_city = st.text_input("City", key="fu_city")
            _fu_price = st.number_input("Offer Price", min_value=20000, value=42000, step=500, key="fu_price")
            if st.button("Generate Sequence", key="fu_gen"):
                if _fu_cust:
                    _seq = _comm.generate_followup_sequence(_fu_cust, _fu_city, _fu_price)
                    for _s in _seq:
                        _day_label = f"Day {_s['day']}" if _s['day'] > 0 else "Today"
                        st.markdown(f"**{_day_label}** — {_s['channel']}: {_s['action']}")

        with _comm_tabs[2]:
            st.subheader("Recent Communications")
            _hist = _comm.get_communication_history(limit=30)
            if _hist:
                _hist_df = pd.DataFrame(_hist)
                st.dataframe(_hist_df, use_container_width=True, hide_index=True)
            else:
                st.caption("No communications logged yet.")

    except Exception as _e:
        st.error(f"Communication Hub failed to load: {_e}")

    # ── Smart navigation: contextual next steps ──
    try:
        from navigation_engine import render_next_step_cards
        render_next_step_cards("💬 Communication Hub")
        st.session_state["_ns_rendered_inline"] = True
    except Exception:
        pass
