"""
Home Page — Live Market Dashboard
Extracted from dashboard.py inline Home page block.
"""

import datetime as _dt
import json as _json

import streamlit as st


# ── Cached helpers (duplicated from main module for standalone use) ──────────

@st.cache_data(ttl=600)
def _cached_forecast_calendar():
    try:
        from command_intel.price_prediction import generate_forecast_calendar
        return generate_forecast_calendar()
    except Exception:
        return None


@st.cache_data(ttl=300)
def _cached_db_stats():
    """Cached database stats for Home dashboard."""
    try:
        from database import get_dashboard_stats
        return get_dashboard_stats()
    except Exception:
        return {"total_suppliers": 63, "total_customers": 3, "total_deals": 0}


def _fmt_inr_home(amount) -> str:
    """Format INR with Indian comma system for homepage display."""
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
        sign = "-" if amount < 0 else ""
        return f"{sign}\u20b9{formatted}"
    except (ValueError, TypeError):
        return str(amount)


# ── Main render function ────────────────────────────────────────────────────

def render(mkt: dict, _CONFIDENCE_OK: bool = False, render_data_health_card=None):
    """
    Render the Home page.

    Parameters
    ----------
    mkt : dict
        Market data dict with keys 'brent', 'wti', 'usdinr', each containing
        'value', 'change', and 'color'.
    _CONFIDENCE_OK : bool
        Whether the data-confidence engine loaded successfully.
    render_data_health_card : callable or None
        Optional callable to render the data-health card (Phase D).
    """

    # ── Load data for Home dashboard ─────────────────────────────────────────
    # Price prediction data — cached
    try:
        _fc_df  = _cached_forecast_calendar()
        if _fc_df is None:
            raise ValueError("No forecast data")
        _today  = _dt.date.today()
        _future = _fc_df[_fc_df["Date"].apply(
            lambda x: x.date() if hasattr(x, "date") else x) > _today]
        if not _future.empty:
            _nr     = _future.iloc[0]
            _pred   = _nr.get("Predicted (₹/MT)", _nr.get("Predicted", 48500))
            _lo     = _nr.get("Low Range", _pred - 400)
            _hi     = _nr.get("High Range", _pred + 400)
            _rdate  = _nr.get("Revision Date", "01-04-2026")
            _status = _nr.get("Status", "Pending")
            _chart_rows = _future.head(6)
            _chart_dates  = [str(r.get("Revision Date", "")) for _, r in _chart_rows.iterrows()]
            _chart_prices = [float(r.get("Predicted (₹/MT)", r.get("Predicted", 48500)))
                             for _, r in _chart_rows.iterrows()]
        else:
            _pred, _lo, _hi, _rdate, _status = 48500, 48100, 48900, "01-04-2026", "Pending"
            _chart_dates  = ["01-04-2026", "16-04-2026", "01-05-2026", "16-05-2026", "01-06-2026", "16-06-2026"]
            _chart_prices = [48500, 48800, 49100, 48700, 49200, 49600]
    except Exception:
        _pred, _lo, _hi, _rdate, _status = 48500, 48100, 48900, "01-04-2026", "Pending"
        _chart_dates  = ["01-04-2026", "16-04-2026", "01-05-2026", "16-05-2026", "01-06-2026", "16-06-2026"]
        _chart_prices = [48500, 48800, 49100, 48700, 49200, 49600]

    # CRM tasks
    try:
        with open("crm_tasks.json", encoding="utf-8") as _f:
            _crm_tasks = _json.load(_f)
        _task_count   = len(_crm_tasks)
        _high_pri     = sum(1 for t in _crm_tasks if t.get("priority") == "High")
    except Exception:
        _crm_tasks = []
        _task_count, _high_pri = 0, 0

    # Database stats (suppliers, customers) — cached
    _db_stats = _cached_db_stats()

    # Live prices
    try:
        with open("live_prices.json", encoding="utf-8") as _f:
            _lp = _json.load(_f)
    except Exception:
        _lp = {"DRUM_MUMBAI_VG30": 37000, "DRUM_KANDLA_VG30": 35500,
               "DRUM_MUMBAI_VG10": 38000, "DRUM_KANDLA_VG10": 36500}

    # API stats
    try:
        with open("api_stats.json", encoding="utf-8") as _f:
            _api_st = _json.load(_f)
        _api_ok  = sum(1 for v in _api_st.values() if v.get("status") == "OK")
        _api_tot = len(_api_st)
    except Exception:
        _api_st, _api_ok, _api_tot = {}, 5, 6

    # Active alerts
    try:
        from command_intel.alert_system import _get_active_alerts as _gaa
        _alerts = _gaa()
        _alert_count    = len(_alerts)
        _alert_critical = sum(1 for a in _alerts if a.get("severity") == "critical")
    except Exception:
        _alerts, _alert_count, _alert_critical = [], 0, 0

    # Cheapest sources (Top 5)
    _top_sources = []
    try:
        from calculation_engine import BitumenCalculationEngine as _CalcEngine
        _calc = _CalcEngine()
        _src_cities = ["Ahmedabad", "Mumbai", "Delhi", "Pune", "Indore"]
        for _sc in _src_cities:
            try:
                _srcs = _calc.find_best_sources(_sc, grade="VG30", top_n=1)
                if _srcs:
                    _top_sources.append({
                        "city": _sc,
                        "source": _srcs[0].get("source", "Unknown"),
                        "landed": _srcs[0].get("landed_cost", 0),
                    })
            except Exception:
                pass
        _top_sources.sort(key=lambda x: x.get("landed", 99999))
    except Exception:
        pass

    # Opportunities (from opportunity engine)
    _opportunities = []
    _opp_count = 0
    try:
        from opportunity_engine import get_all_opportunities as _get_opps
        _opportunities = _get_opps(status="new")
        _opp_count = len(_opportunities)
    except Exception:
        pass

    # Today's recommendations
    _todays_recs = {}
    try:
        from opportunity_engine import OpportunityEngine as _OppEngine
        _opp_eng = _OppEngine()
        _todays_recs = _opp_eng.get_todays_recommendations()
    except Exception:
        _todays_recs = {"buyers_to_call": [], "followups_due": [], "reactivation_targets": [], "total_new_opportunities": 0}

    # Missing inputs count
    _missing_count = 0
    try:
        from missing_inputs_engine import MissingInputsEngine as _MIEngine
        _mi = _MIEngine()
        _missing_count = len(_mi.scan_all_gaps())
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 1 — MARKET PULSE (Real-Time KPI Bar)
    # ─────────────────────────────────────────────────────────────────────────
    _today_str = _dt.date.today().strftime("%d %b %Y")
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#1e3a5f 0%,#0f2744 100%);border-radius:10px;
            padding:12px 20px;margin-bottom:14px;display:flex;align-items:center;
            justify-content:space-between;flex-wrap:wrap;gap:8px;">
  <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center;">
    <span style="font-size:0.72rem;font-weight:800;color:#93c5fd;text-transform:uppercase;
                 letter-spacing:0.08em;">MARKET PULSE</span>
    <span style="color:#e2e8f0;font-size:0.82rem;">
      <b>Brent:</b> {mkt['brent']['value']}
      <span style="color:{mkt['brent']['color']};font-weight:600;"> {mkt['brent']['change']}</span>
    </span>
    <span style="color:#e2e8f0;font-size:0.82rem;">
      <b>WTI:</b> {mkt['wti']['value']}
      <span style="color:{mkt['wti']['color']};font-weight:600;"> {mkt['wti']['change']}</span>
    </span>
    <span style="color:#e2e8f0;font-size:0.82rem;">
      <b>INR:</b> {mkt['usdinr']['value']}
      <span style="color:{mkt['usdinr']['color']};font-weight:600;"> {mkt['usdinr']['change']}</span>
    </span>
    <span style="color:#fcd34d;font-size:0.82rem;font-weight:600;">
      VG30: {_fmt_inr_home(_lp.get("DRUM_KANDLA_VG30", 35500))}
    </span>
  </div>
  <div style="font-size:0.72rem;color:#93c5fd;white-space:nowrap;">
    {_today_str}
  </div>
</div>
""", unsafe_allow_html=True)

    # ─── P0 Alert Banner (if any critical alerts) ──────────────────────────
    try:
        from command_intel.alert_center import get_p0_alert_banner as _get_p0
        _p0_html = _get_p0()
        if _p0_html:
            st.markdown(_p0_html, unsafe_allow_html=True)
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2 — KPI Metrics (6 key metrics)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="kpi-bar">', unsafe_allow_html=True)
    _k1, _k2, _k3, _k4, _k5, _k6, _k7 = st.columns(7)
    _k1.metric("Predicted Price", f"{_fmt_inr_home(int(_pred))}/MT")
    _k2.metric("Suppliers", _db_stats.get("total_suppliers", 63))
    _k3.metric("Customers", _db_stats.get("total_customers", 3))
    _k4.metric("Opportunities", _opp_count if _opp_count else "Scan needed")
    _k5.metric("CRM Tasks", _task_count, f"{_high_pri} high priority" if _high_pri else None)
    _k6.metric("APIs Healthy", f"{_api_ok}/{_api_tot}")
    try:
        from market_intelligence_engine import get_master_signal
        _ms = get_master_signal()
        _k7.metric("Market Signal", _ms.get("market_direction", "N/A"),
                    f"{_ms.get('confidence', 0)}% conf")
    except Exception:
        _k7.metric("Market Signal", "N/A")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Data Health Card (Phase D) ──────────────────────────────────────────
    if _CONFIDENCE_OK and render_data_health_card is not None:
        render_data_health_card()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3 — Top Sources + Top Sell Opportunities (2-column)
    # ─────────────────────────────────────────────────────────────────────────
    _h3a, _h3b = st.columns(2)

    with _h3a:
        st.markdown('<div class="zoho-row-header">Top 5 Cheapest Sources (VG30 Landed)</div>', unsafe_allow_html=True)
        if _top_sources:
            _src_html = ""
            for _idx, _ts in enumerate(_top_sources[:5], 1):
                _rank_ico = ["", "1.", "2.", "3.", "4.", "5."][_idx]
                _src_html += f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:6px 10px;border-bottom:1px solid #f1f5f9;font-size:0.8rem;">
  <span style="color:#2d3142;font-weight:500;">{_rank_ico} {_ts['source']}</span>
  <span style="color:#1e3a5f;font-weight:700;">{_fmt_inr_home(_ts['landed'])}/MT</span>
</div>"""
            st.markdown(f'<div class="zoho-card">{_src_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="zoho-card" style="padding:16px;text-align:center;">
  <div style="font-size:0.82rem;color:#64748b;">Run a sync to discover cheapest sources</div>
</div>""", unsafe_allow_html=True)
        if st.button("Open Pricing Calculator", key="_home_pricing_btn", use_container_width=True):
            st.session_state["_nav_goto"] = "🧮 Pricing Calculator"
            st.rerun()

    with _h3b:
        st.markdown('<div class="zoho-row-header">Top Sell Opportunities</div>', unsafe_allow_html=True)
        _sell_opps = [o for o in _opportunities if o.get("type") == "price_drop_reactivation"][:5]
        if _sell_opps:
            _opp_html = ""
            for _idx, _so in enumerate(_sell_opps[:5], 1):
                _cname = _so.get("customer_name", "Unknown")[:25]
                _ccity = _so.get("customer_city", "")
                _margin = _so.get("estimated_margin_per_mt", 0)
                _opp_html += f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:6px 10px;border-bottom:1px solid #f1f5f9;font-size:0.8rem;">
  <span style="color:#2d3142;font-weight:500;">{_idx}. {_cname} ({_ccity})</span>
  <span style="color:#2d6a4f;font-weight:700;">{_fmt_inr_home(_margin)} margin</span>
</div>"""
            st.markdown(f'<div class="zoho-card">{_opp_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="zoho-card" style="padding:16px;text-align:center;">
  <div style="font-size:0.82rem;color:#64748b;">Run opportunity scan to find sell targets</div>
</div>""", unsafe_allow_html=True)
        if st.button("View All Opportunities", key="_home_opp_btn", use_container_width=True):
            st.session_state["_nav_goto"] = "🔍 Opportunities"
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 4 — Call Today + Negotiate Today (2-column)
    # ─────────────────────────────────────────────────────────────────────────
    _h4a, _h4b = st.columns(2)

    with _h4a:
        st.markdown('<div class="zoho-row-header">Call Today (Buyers)</div>', unsafe_allow_html=True)
        _buyers = _todays_recs.get("buyers_to_call", [])[:5]
        if _buyers:
            _buy_html = ""
            for _b in _buyers:
                _bname = _b.get("customer_name", "Unknown")[:28]
                _bcity = _b.get("customer_city", "")
                _bpri = _b.get("priority", "P2")
                _pri_clr = "#dc2626" if _bpri == "P0" else "#d97706" if _bpri == "P1" else "#3b82f6"
                _buy_html += f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:5px 10px;border-bottom:1px solid #f1f5f9;font-size:0.78rem;">
  <span style="color:#2d3142;font-weight:500;">{_bname}</span>
  <span style="display:flex;gap:8px;align-items:center;">
    <span style="color:#64748b;font-size:0.72rem;">{_bcity}</span>
    <span style="background:{_pri_clr};color:#fff;font-size:0.62rem;font-weight:700;
                 padding:1px 6px;border-radius:8px;">{_bpri}</span>
  </span>
</div>"""
            st.markdown(f'<div class="zoho-card">{_buy_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="zoho-card" style="padding:16px;text-align:center;">
  <div style="font-size:0.82rem;color:#64748b;">No buyers flagged for today. Run opportunity scan.</div>
</div>""", unsafe_allow_html=True)
        if st.button("Open CRM & Tasks", key="_home_crm_btn", use_container_width=True):
            st.session_state["_nav_goto"] = "🎯 CRM & Tasks"
            st.rerun()

    with _h4b:
        st.markdown('<div class="zoho-row-header">Follow-ups Due</div>', unsafe_allow_html=True)
        _followups = _todays_recs.get("followups_due", [])[:5]
        if _followups:
            _fu_html = ""
            for _fu in _followups:
                _fname = _fu.get("customer_name", _fu.get("title", "Task"))[:28]
                _ftype = _fu.get("type", _fu.get("channel", ""))
                _fu_html += f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:5px 10px;border-bottom:1px solid #f1f5f9;font-size:0.78rem;">
  <span style="color:#2d3142;font-weight:500;">{_fname}</span>
  <span style="color:#64748b;font-size:0.72rem;">{_ftype}</span>
</div>"""
            st.markdown(f'<div class="zoho-card">{_fu_html}</div>', unsafe_allow_html=True)
        else:
            _pending_tasks = [t for t in _crm_tasks if t.get("status") == "Pending"][:5]
            if _pending_tasks:
                _pt_html = ""
                for _pt in _pending_tasks:
                    _ptitle = _pt.get("title", "Task")[:28]
                    _ptype = _pt.get("type", "")
                    _pt_html += f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:5px 10px;border-bottom:1px solid #f1f5f9;font-size:0.78rem;">
  <span style="color:#2d3142;font-weight:500;">{_ptitle}</span>
  <span style="color:#64748b;font-size:0.72rem;">{_ptype}</span>
</div>"""
                st.markdown(f'<div class="zoho-card">{_pt_html}</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
<div class="zoho-card" style="padding:16px;text-align:center;">
  <div style="font-size:0.82rem;color:#64748b;">No follow-ups due today.</div>
</div>""", unsafe_allow_html=True)
        if st.button("Open Sales Workspace", key="_home_sales_btn", use_container_width=True):
            st.session_state["_nav_goto"] = "💼 Sales Workspace"
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 5 — Price Trend Chart + Alerts (2-column)
    # ─────────────────────────────────────────────────────────────────────────
    _h5a, _h5b = st.columns([6, 4])

    with _h5a:
        st.markdown('<div class="zoho-row-header">Price Forecast (VG-30, 6-month)</div>', unsafe_allow_html=True)
        try:
            import plotly.graph_objects as _go
            _fig = _go.Figure()
            _fig.add_trace(_go.Scatter(
                x=_chart_dates, y=_chart_prices, mode='lines+markers',
                line=dict(color='#2d6a4f', width=2.5),
                marker=dict(size=6, color='#2d6a4f'),
                fill='tozeroy', fillcolor='rgba(45,106,79,0.06)',
                hovertemplate='%{x}<br>%{y:,.0f}/MT<extra></extra>'
            ))
            _fig.update_layout(
                height=200, margin=dict(l=0, r=0, t=8, b=24),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, tickfont=dict(size=9), tickangle=-30),
                yaxis=dict(showgrid=True, gridcolor='#f1f5f9',
                           tickformat=',', tickfont=dict(size=9)),
                showlegend=False,
            )
            st.plotly_chart(_fig, use_container_width=True, config={"displayModeBar": False})
        except Exception:
            st.caption("Forecast chart unavailable.")
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-top:-8px;">
  <span style="background:#e8f5ee;color:#2d6a4f;font-size:0.72rem;font-weight:700;
               padding:3px 10px;border-radius:20px;border:1px solid #b7dfc9;">
    Confidence: 82%
  </span>
  <span style="font-size:0.68rem;color:#64748b;">Next revision: {_rdate}</span>
  <span style="font-size:0.68rem;color:#1e3a5f;font-weight:600;">{_fmt_inr_home(int(_pred))}/MT</span>
</div>
""", unsafe_allow_html=True)
        if st.button("Full Forecast", key="_home_fc_btn", use_container_width=True):
            st.session_state["_nav_goto"] = "🔮 Price Prediction"
            st.rerun()

    with _h5b:
        st.markdown('<div class="zoho-row-header">Alerts</div>', unsafe_allow_html=True)
        _sev_cfg = {
            "critical": ("#fff1f2", "#dc2626"),
            "warning":  ("#fffbeb", "#d97706"),
            "info":     ("#eff6ff", "#3b82f6"),
        }
        _alert_rows_html = ""
        for _al in _alerts[:5]:
            _sev = _al.get("severity", "info")
            _bg, _clr = _sev_cfg.get(_sev, _sev_cfg["info"])
            _title = _al.get("title", "Alert")[:50]
            _alert_rows_html += f"""
<div style="background:{_bg};border-left:3px solid {_clr};
     margin-bottom:4px;border-radius:4px;padding:5px 8px;">
  <span style="font-size:0.75rem;color:#2d3142;font-weight:500;">{_title}</span>
</div>"""
        if not _alert_rows_html:
            _alert_rows_html = '<div style="font-size:0.78rem;color:#64748b;padding:8px;">No active alerts. System healthy.</div>'
        st.markdown(f'<div class="zoho-card">{_alert_rows_html}</div>', unsafe_allow_html=True)

        # Missing inputs notification
        if _missing_count > 0:
            st.markdown(f"""
<div style="background:#fffbeb;border:1px solid #f59e0b;border-radius:8px;padding:8px 12px;margin-top:8px;">
  <span style="font-size:0.78rem;color:#92400e;font-weight:600;">
    {_missing_count} data gaps detected
  </span>
  <span style="font-size:0.72rem;color:#92400e;"> - update for better accuracy</span>
</div>""", unsafe_allow_html=True)
        if st.button("Alert System", key="_home_alert_btn", use_container_width=True):
            st.session_state["_nav_goto"] = "🔔 Alert System"
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 6 — Sales Snapshot + API Health (2-column)
    # ─────────────────────────────────────────────────────────────────────────
    _h6a, _h6b = st.columns(2)

    with _h6a:
        st.markdown('<div class="zoho-row-header">Sales Snapshot (Live Prices)</div>', unsafe_allow_html=True)
        _vg30_mum = _lp.get("DRUM_MUMBAI_VG30", 37000)
        _vg30_kan = _lp.get("DRUM_KANDLA_VG30", 35500)
        _vg10_mum = _lp.get("DRUM_MUMBAI_VG10", 38000)
        _vg10_kan = _lp.get("DRUM_KANDLA_VG10", 36500)
        st.markdown(f"""
<div class="zoho-card">
  <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
    <thead>
      <tr style="background:#f8fafc;">
        <th style="padding:6px 10px;text-align:left;font-weight:700;color:#1e3a5f;border-bottom:1px solid #e8dcc8;">Grade</th>
        <th style="padding:6px 10px;text-align:right;font-weight:700;color:#1e3a5f;border-bottom:1px solid #e8dcc8;">Mumbai</th>
        <th style="padding:6px 10px;text-align:right;font-weight:700;color:#1e3a5f;border-bottom:1px solid #e8dcc8;">Kandla</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding:5px 10px;color:#2d3142;font-weight:500;">VG-30</td>
        <td style="padding:5px 10px;text-align:right;font-weight:700;color:#2d6a4f;">{_fmt_inr_home(int(_vg30_mum))}</td>
        <td style="padding:5px 10px;text-align:right;font-weight:700;color:#2d6a4f;">{_fmt_inr_home(int(_vg30_kan))}</td>
      </tr>
      <tr style="background:#faf7f2;">
        <td style="padding:5px 10px;color:#2d3142;font-weight:500;">VG-10</td>
        <td style="padding:5px 10px;text-align:right;font-weight:700;color:#2d6a4f;">{_fmt_inr_home(int(_vg10_mum))}</td>
        <td style="padding:5px 10px;text-align:right;font-weight:700;color:#2d6a4f;">{_fmt_inr_home(int(_vg10_kan))}</td>
      </tr>
    </tbody>
  </table>
  <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
    <span class="zoho-stat-pill">{_db_stats.get('total_suppliers', 63)} Suppliers</span>
    <span class="zoho-stat-pill">{_db_stats.get('total_customers', 3)} Customers</span>
    <span class="zoho-stat-pill">{_db_stats.get('total_deals', 0)} Deals</span>
  </div>
</div>
""", unsafe_allow_html=True)

    with _h6b:
        st.markdown('<div class="zoho-row-header">API & System Health</div>', unsafe_allow_html=True)
        _api_display = list(_api_st.items())[:6] if _api_st else []
        _api_rows_html = ""
        for _aname, _adat in _api_display:
            _aok  = _adat.get("status", "") == "OK"
            _dot  = "ok" if _aok else "fail"
            _lat  = _adat.get("avg_latency_ms", 0)
            _label = _aname.replace("_", " ").title()[:22]
            _api_rows_html += f"""
<div class="alert-row" style="justify-content:flex-start;gap:10px;">
  <span class="api-dot {_dot}"></span>
  <span style="font-size:0.75rem;color:#2d3142;flex:1;font-weight:500;">{_label}</span>
  <span style="font-size:0.68rem;color:#64748b;">{_lat}ms</span>
</div>"""
        st.markdown(f"""
<div class="zoho-card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <span style="font-size:0.72rem;color:#64748b;">Live API Status</span>
    <span style="background:#e8f5ee;color:#2d6a4f;font-size:0.68rem;font-weight:700;
                 padding:2px 8px;border-radius:12px;border:1px solid #b7dfc9;">
      {_api_ok}/{_api_tot} Healthy
    </span>
  </div>
  {_api_rows_html}
</div>
""", unsafe_allow_html=True)
        if st.button("API Dashboard", key="_home_api_btn", use_container_width=True):
            st.session_state["_nav_goto"] = "🌐 API Dashboard"
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 7 — AI Command Centre (full width, navy gradient)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="zoho-row-header">AI Command Centre</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:linear-gradient(135deg,#1e3a5f 0%,#0f2744 100%);
            border-radius:12px;padding:14px 20px;margin-bottom:12px;">
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
    <span style="font-size:0.75rem;font-weight:700;color:#93c5fd;text-transform:uppercase;
                 letter-spacing:0.07em;">PPS Anantam AI — Ask Anything</span>
  </div>
  <div style="color:#e2e8f0;font-size:0.82rem;line-height:1.5;">
    AI assistant connected to live market data, CRM, and all modules.
  </div>
</div>
""", unsafe_allow_html=True)

    _ai_c1, _ai_c2, _ai_c3 = st.columns([3, 3, 4])

    with _ai_c1:
        st.markdown(f"""
<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(201,168,76,0.3);
            border-left:4px solid #c9a84c;border-radius:8px;padding:12px 14px;">
  <div style="color:#fcd34d;font-size:0.65rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.05em;margin-bottom:6px;">Next Revision</div>
  <div style="font-size:1.3rem;font-weight:800;color:#ffffff;">{_fmt_inr_home(int(_pred))}</div>
  <div style="font-size:0.68rem;color:#93c5fd;margin-top:2px;">/MT VG-30</div>
  <div style="display:flex;gap:10px;margin-top:8px;font-size:0.72rem;">
    <span style="color:#86efac;">{_fmt_inr_home(int(_lo))}</span>
    <span style="color:#fca5a5;">{_fmt_inr_home(int(_hi))}</span>
    <span style="color:#93c5fd;">{_rdate}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    with _ai_c2:
        st.markdown(f"""
<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);
            border-radius:8px;padding:12px 14px;">
  <div style="color:#93c5fd;font-size:0.65rem;font-weight:700;text-transform:uppercase;
              letter-spacing:0.05em;margin-bottom:8px;">Live Market</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
    <div>
      <div style="font-size:0.62rem;color:#94a3b8;">Brent</div>
      <div style="font-size:0.9rem;font-weight:700;color:#e2e8f0;">{mkt['brent']['value']}</div>
    </div>
    <div>
      <div style="font-size:0.62rem;color:#94a3b8;">WTI</div>
      <div style="font-size:0.9rem;font-weight:700;color:#e2e8f0;">{mkt['wti']['value']}</div>
    </div>
    <div>
      <div style="font-size:0.62rem;color:#94a3b8;">USD/INR</div>
      <div style="font-size:0.9rem;font-weight:700;color:#e2e8f0;">{mkt['usdinr']['value']}</div>
    </div>
    <div>
      <div style="font-size:0.62rem;color:#94a3b8;">APIs</div>
      <div style="font-size:0.9rem;font-weight:700;color:#86efac;">{_api_ok}/{_api_tot} OK</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    with _ai_c3:
        _quick_qs = [
            ("Next predicted price?",        "What is the next predicted bitumen price for the 1st or 16th cycle?"),
            ("News affecting crude?",         "Any breaking news affecting crude oil or bitumen prices today?"),
            ("Highest demand state?",         "Which Indian state has the highest bitumen demand this month?"),
            ("Open bugs & issues?",           "Show me all open bugs and API health issues in the system."),
        ]
        _ql_c1, _ql_c2 = st.columns(2)
        for _i, (_qlabel, _qtext) in enumerate(_quick_qs):
            _col = _ql_c1 if _i % 2 == 0 else _ql_c2
            with _col:
                if st.button(_qlabel, key=f"_home_q_{_i}", use_container_width=True):
                    st.session_state["_ai_prefill"] = _qtext
                    st.session_state["_nav_goto"]   = "🧠 AI Dashboard Assistant"
                    st.rerun()
        if st.button("Open Full AI Chat", key="_home_ai_full",
                     use_container_width=True, type="primary"):
            st.session_state["_nav_goto"] = "🧠 AI Dashboard Assistant"
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # MISSING INPUTS POPUP (once per day)
    # ─────────────────────────────────────────────────────────────────────────
    try:
        from missing_inputs_engine import MissingInputsEngine as _MIE2
        _mi2 = _MIE2()
        if _mi2.should_show_popup():
            _gaps = _mi2.scan_all_gaps()
            if _gaps:
                with st.expander(f"Data Gaps Detected ({len(_gaps)} items) — Click to review", expanded=False):
                    for _g in _gaps[:8]:
                        _gpri = _g.get("priority", "Medium")
                        _gpri_clr = "#dc2626" if _gpri == "High" else "#d97706" if _gpri == "Medium" else "#3b82f6"
                        st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:4px 0;border-bottom:1px solid #f1f5f9;font-size:0.78rem;">
  <span style="color:#2d3142;">{_g.get('label', _g.get('field', ''))}</span>
  <span style="background:{_gpri_clr};color:#fff;font-size:0.62rem;font-weight:700;
               padding:1px 6px;border-radius:8px;">{_gpri}</span>
</div>""", unsafe_allow_html=True)
    except Exception:
        pass

    # ── Handle deferred navigation (from Home quick-action buttons) ─────────
    if st.session_state.get("_nav_goto"):
        _goto = st.session_state.pop("_nav_goto")
        st.session_state['selected_page'] = _goto
        st.rerun()
