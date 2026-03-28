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
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">🔄 Sync Status</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">System</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="background:#e8f5ee;color:#2d6a4f;font-size:0.68rem;font-weight:700;padding:2px 9px;border-radius:12px;border:1px solid #b7dfc9;">Auto-Sync</span>
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.info("Master data synchronization — runs automatically every 60 minutes + on-demand.")
    try:
        from sync_engine import SyncEngine
        import json as _sync_json

        _sync_eng = SyncEngine()
        _sync_tabs = st.tabs(["Run Sync", "Sync History", "Missing Inputs"])

        with _sync_tabs[0]:
            st.subheader("Manual Sync")
            _sc1, _sc2 = st.columns(2)
            with _sc1:
                if st.button("Full Sync (All Sources)", type="primary", use_container_width=True):
                    with st.spinner("Running full sync... this may take 2-3 minutes"):
                        _result = _sync_eng.run_full_sync()
                    st.session_state["_sync_full_result"] = _result
                    st.session_state["_sync_market_result"] = None
                    st.rerun()
            with _sc2:
                if st.button("Market Data Only (Quick)", use_container_width=True):
                    with st.spinner("Syncing market data..."):
                        _result = _sync_eng.run_market_only()
                    st.session_state["_sync_market_result"] = _result
                    st.session_state["_sync_full_result"] = None
                    st.rerun()

            if st.session_state.get("_sync_full_result"):
                _result = st.session_state["_sync_full_result"]
                st.success(f"Sync completed! {_result.get('apis_succeeded', 0)} APIs succeeded.")
                for _step in _result.get("steps", []):
                    _step_status = _step.get("status", "unknown")
                    _step_icon = "OK" if _step_status == "success" else "WARN" if _step_status == "partial" else "FAIL"
                    st.markdown(f"- [{_step_icon}] {_step.get('name', 'Step')} — {_step.get('details', '')}")

            if st.session_state.get("_sync_market_result"):
                st.success("Market sync completed!")

        with _sync_tabs[1]:
            st.subheader("Sync History")
            try:
                from database import get_sync_logs
                _logs = get_sync_logs(limit=20)
                if _logs:
                    _log_df = pd.DataFrame(_logs)
                    st.dataframe(_log_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("No sync history yet. Run a sync first.")
            except Exception:
                st.caption("Sync logs not available.")

        with _sync_tabs[2]:
            st.subheader("Missing Data Inputs")
            try:
                from missing_inputs_engine import MissingInputsEngine
                _mi_eng = MissingInputsEngine()
                _gaps = _mi_eng.scan_all_gaps()
                if _gaps:
                    st.markdown(f"**{len(_gaps)} data gaps detected:**")
                    for _g in _gaps:
                        _gpri = _g.get("priority", "Medium")
                        _gpri_clr = "#dc2626" if _gpri == "High" else "#d97706" if _gpri == "Medium" else "#3b82f6"
                        st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:6px 10px;border-bottom:1px solid #f1f5f9;font-size:0.82rem;">
  <div>
    <span style="color:#2d3142;font-weight:600;">{_g.get('label', _g.get('field', 'Unknown'))}</span>
    <span style="font-size:0.72rem;color:#64748b;margin-left:8px;">{_g.get('reason', '')}</span>
  </div>
  <span style="background:{_gpri_clr};color:#fff;font-size:0.65rem;font-weight:700;
               padding:2px 8px;border-radius:8px;">{_gpri}</span>
</div>""", unsafe_allow_html=True)

                    _daily_qs = _mi_eng._daily_questions()
                    if _daily_qs:
                        st.subheader("Daily Questions")
                        for _dq in _daily_qs:
                            st.text_input(_dq.get("label", ""), key=f"dq_{_dq.get('field', '')}", placeholder=_dq.get("placeholder", ""))
                else:
                    st.success("No data gaps detected! All inputs are up to date.")
            except Exception as _e:
                st.caption(f"Missing inputs scanner not available: {_e}")

    except Exception as _e:
        st.error(f"Sync Status failed to load: {_e}")
