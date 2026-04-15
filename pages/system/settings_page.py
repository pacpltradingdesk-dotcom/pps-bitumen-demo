import streamlit as st
import datetime
from pathlib import Path


def render():
    # Phase 2: standardized refresh bar (clears caches + reruns)
    try:
        from components.refresh_bar import render_refresh_bar
        render_refresh_bar('settings')
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
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">⚙️ Settings</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">Technology</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.header("⚙️ System Settings & Integrations")

    st.subheader("🔗 External Integrations & API Keys")
    st.caption("Manage connections to third-party services for automation.")

    with st.expander("🔑 API Configuration", expanded=True):
        # Cloud persistence reminder
        try:
            from cloud_secrets import render_cloud_secrets_hint
            render_cloud_secrets_hint("ai", ["openai_api_key", "google_maps_api_key"],
                title="⚠️ Why API keys disappear on Cloud (and how to fix permanently — ai)")
        except Exception:
            pass
        api_c1, api_c2 = st.columns(2)
        with api_c1:
            try:
                from ai_fallback_engine import get_api_key as _get_ai_key
                _existing_openai_key = _get_ai_key("openai")
            except Exception:
                _existing_openai_key = ""
            openai_key_input = st.text_input("OpenAI / AI Key", value=_existing_openai_key, type="password", help="Required for AI Script generation (Optional).")
            st.text_input("Google Maps API Key", type="password", help="Required for accurate distance calculations.")
        with api_c2:
            st.caption("Email & WhatsApp configuration has moved to dedicated pages:")
            st.markdown("📧 **Email Engine** → SMTP Config tab")
            st.markdown("📱 **WhatsApp Engine** → API Config tab")

        if st.button("💾 Save API Settings"):
            if openai_key_input.strip():
                try:
                    from ai_fallback_engine import save_api_key as _save_ai_key
                    _save_ai_key("openai", openai_key_input.strip())
                    st.toast("OpenAI API key saved to ai_fallback_config.json")
                except Exception as _ke:
                    st.toast(f"Could not save key: {_ke}")
            else:
                st.toast("Settings Saved")

    with st.expander("🌐 Market Data API Keys", expanded=False):
        st.caption("Configure API keys for live market data feeds. All keys are stored locally in settings.json.")
        # Cloud persistence — settings.json is ephemeral on Cloud
        try:
            from cloud_secrets import secret_source_label, render_cloud_secrets_hint
            st.caption(secret_source_label("api_keys", file_present=True))
            render_cloud_secrets_hint("api_keys",
                ["api_key_eia", "api_key_fred", "api_key_data_gov_in",
                 "api_key_openweather", "api_key_newsapi"])
        except Exception:
            pass
        try:
            from settings_engine import load_settings as _ld_s, save_settings as _sv_s
            _api_sett = _ld_s()
            _api_configs = [
                ("EIA (US Energy)", "api_key_eia", "api_key_eia_enabled", "Crude oil & energy data from US EIA"),
                ("FRED (Federal Reserve)", "api_key_fred", "api_key_fred_enabled", "Economic indicators & interest rates"),
                ("data.gov.in", "api_key_data_gov_in", "api_key_data_gov_in_enabled", "Indian government open data"),
                ("OpenWeather", "api_key_openweather", "api_key_openweather_enabled", "Weather data for construction forecasting"),
                ("NewsAPI", "api_key_newsapi", "api_key_newsapi_enabled", "News headlines for sentiment analysis"),
            ]
            for _label, _key_field, _enable_field, _desc in _api_configs:
                _ac1, _ac2, _ac3 = st.columns([1.5, 2, 0.5])
                with _ac1:
                    _api_sett[_enable_field] = st.toggle(
                        f"Enable {_label}", value=_api_sett.get(_enable_field, False),
                        key=f"mkt_{_enable_field}")
                with _ac2:
                    _api_sett[_key_field] = st.text_input(
                        f"{_label} API Key", value=_api_sett.get(_key_field, ""),
                        type="password", key=f"mkt_{_key_field}", help=_desc)
                with _ac3:
                    if _api_sett.get(_key_field):
                        st.markdown("🟢")
                    else:
                        st.markdown("⚪")

            if st.button("💾 Save Market Data API Keys", key="save_mkt_api_keys"):
                _sv_s(_api_sett)
                # Also update hub_catalog.json if it exists
                try:
                    import json as _jj
                    _hc_path = Path("hub_catalog.json")
                    if _hc_path.exists():
                        with open(_hc_path, "r", encoding="utf-8") as _hf:
                            _hc = _jj.load(_hf)
                        _key_map = {
                            "api_key_eia": "eia", "api_key_fred": "fred",
                            "api_key_data_gov_in": "data_gov_in",
                            "api_key_openweather": "openweather",
                            "api_key_newsapi": "newsapi",
                        }
                        for _sf, _hid in _key_map.items():
                            for _entry in _hc:
                                if isinstance(_entry, dict) and _entry.get("id") == _hid:
                                    _entry["api_key"] = _api_sett.get(_sf, "")
                        with open(_hc_path, "w", encoding="utf-8") as _hf:
                            _jj.dump(_hc, _hf, indent=2, ensure_ascii=False)
                except Exception:
                    pass
                st.toast("Market Data API keys saved!")
        except Exception as _mke:
            st.caption(f"Settings engine unavailable: {_mke}")

    with st.expander("📧 Email & WhatsApp Automation", expanded=False):
        try:
            from settings_engine import load_settings as _load_s, save_settings as _save_s
            _sett = _load_s()
            _set_c1, _set_c2 = st.columns(2)
            with _set_c1:
                st.markdown("**Email Engine**")
                _sett["email_enabled"] = st.toggle("Enable Email Engine", value=_sett.get("email_enabled", False), key="set_email_en")
                _sett["email_auto_send_offer"] = st.toggle("Auto-send Offer Emails", value=_sett.get("email_auto_send_offer", False), key="set_email_offer")
                _sett["email_auto_send_followup"] = st.toggle("Auto-send Followup Emails", value=_sett.get("email_auto_send_followup", False), key="set_email_fu")
                _sett["email_auto_send_payment_reminder"] = st.toggle("Auto-send Payment Reminders", value=_sett.get("email_auto_send_payment_reminder", False), key="set_email_pay")
                _sett["email_director_report_enabled"] = st.toggle("Director Daily Report", value=_sett.get("email_director_report_enabled", False), key="set_email_dir")
                _sett["email_director_report_to"] = st.text_input("Director Report To", value=_sett.get("email_director_report_to", ""), key="set_email_dir_to")
            with _set_c2:
                st.markdown("**WhatsApp Engine**")
                _sett["whatsapp_enabled"] = st.toggle("Enable WhatsApp Engine", value=_sett.get("whatsapp_enabled", False), key="set_wa_en")
                _sett["whatsapp_auto_send_offer"] = st.toggle("Auto-send Offer Messages", value=_sett.get("whatsapp_auto_send_offer", False), key="set_wa_offer")
                _sett["whatsapp_auto_send_followup"] = st.toggle("Auto-send Followup Messages", value=_sett.get("whatsapp_auto_send_followup", False), key="set_wa_fu")
                _sett["whatsapp_auto_send_payment_reminder"] = st.toggle("Auto-send Payment Reminders (WA)", value=_sett.get("whatsapp_auto_send_payment_reminder", False), key="set_wa_pay")
                _sett["whatsapp_rate_limit_per_minute"] = st.number_input("Rate Limit (msgs/min)", value=_sett.get("whatsapp_rate_limit_per_minute", 20), key="set_wa_rate")
            if st.button("💾 Save Automation Settings", key="save_auto_settings"):
                _save_s(_sett)
                st.toast("Automation settings saved!")
        except Exception as _se:
            st.caption(f"Settings engine unavailable: {_se}")

    with st.expander("📊 Display & Tickers", expanded=False):
        st.caption("Control the scroll speed of the 6 news and market ticker rows on the homepage.")
        try:
            from settings_engine import load_settings as _ld_ts, save_settings as _sv_ts
            _ts_sett = _ld_ts()
        except Exception:
            _ts_sett = {}
        _current_speed = _ts_sett.get("ticker_speed", 600)
        _tc1, _tc2 = st.columns([3, 1])
        with _tc1:
            _new_speed = st.slider(
                "Ticker Scroll Speed (seconds per full cycle)",
                min_value=60, max_value=1200, value=int(_current_speed), step=30,
                help="Lower = faster scroll. 60s = fast, 600s = default, 1200s = very slow",
                key="set_ticker_speed",
            )
        with _tc2:
            if _new_speed <= 120:
                st.metric("Speed", "Fast")
            elif _new_speed <= 600:
                st.metric("Speed", "Normal")
            else:
                st.metric("Speed", "Slow")
        if _new_speed != _current_speed:
            st.session_state["_ticker_speed"] = _new_speed
            _ts_sett["ticker_speed"] = _new_speed
            try:
                _sv_ts(_ts_sett)
            except Exception:
                pass
        else:
            st.session_state["_ticker_speed"] = _current_speed

    st.divider()

    st.subheader("🧠 Smart Logic Rules")
    st.write("Configure how the system reacts to market changes.")

    col_rule1, col_rule2 = st.columns(2)
    with col_rule1:
        st.checkbox("Auto-Switch if Stock Unavailable", value=True)
        st.checkbox("Alert if Transport Cost > 10% hike", value=True)
    with col_rule2:
        st.checkbox("Enable SOS Trigger (> ₹200 drop)", value=True)
        st.checkbox("Auto-Create CRM Tasks for New Leads", value=True)

    st.divider()
    st.subheader("🚫 Unavailability Overrides")
    st.multiselect("Mark these Ports as CURRENTLY OFFLINE:", ["Haldia", "Mumbai", "Chennai", "Kochi"])
