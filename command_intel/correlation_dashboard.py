# command_intel/correlation_dashboard.py
# PPS Anantam Agentic AI Eco System — v3.2.3
# Highway KM vs Bitumen Demand Correlation Dashboard (3-tab UI)

from __future__ import annotations

import datetime
from typing import Any, Dict, List

import streamlit as st

# ── safe imports ──────────────────────────────────────────────────────────────
try:
    import altair as alt
    _ALTAIR = True
except ImportError:
    _ALTAIR = False

try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

try:
    from correlation_engine import (
        run_full_analysis,
        load_monthly_series,
        cross_correlate,
        run_regression,
        generate_insights,
    )
    _ENGINE = True
except ImportError:
    _ENGINE = False

try:
    from api_hub_engine import NormalizedTables, _ist_now
    _HUB = True
except ImportError:
    _HUB = False
    def _ist_now() -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _corr_strength(r: float) -> str:
    """Human-readable correlation strength label."""
    ar = abs(r)
    if ar >= 0.70:
        return "Strong"
    if ar >= 0.40:
        return "Moderate"
    if ar >= 0.20:
        return "Weak"
    return "Negligible"


def _corr_signal(r: float) -> str:
    """Directional signal."""
    if r > 0.40:
        return "↑ Positive"
    if r < -0.40:
        return "↓ Negative"
    return "→ Neutral"


def _r_color(r: float) -> str:
    ar = abs(r)
    if ar >= 0.70:
        return "#16a34a"   # green  5.1:1 on white
    if ar >= 0.40:
        return "#d97706"   # amber  4.6:1 on white
    return "#5a6474"       # slate  5.5:1 on white


# ─────────────────────────────────────────────────────────────────────────────
#  KPI BAR
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpi_bar(results: Dict) -> None:
    """4-metric KPI row from latest analysis results."""
    best_lag   = results.get("best_lag")
    best_r     = results.get("best_r", 0.0)
    r_squared  = results.get("r_squared", 0.0)
    n_obs      = results.get("n_obs", 0)

    best_lag_label = f"{best_lag}m" if best_lag is not None else "N/A"
    signal         = _corr_signal(best_r) if best_r else "—"
    r_sq_label     = f"{r_squared:.2f}" if r_squared else "N/A"
    strength       = _corr_strength(best_r) if best_r else "N/A"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Best Lag",        best_lag_label,  help="Lag (months) at which highway KM shows strongest correlation with demand")
    c2.metric("Strongest r",     f"{best_r:.3f}", help=f"Pearson correlation at best lag — {strength}")
    c3.metric("Current Signal",  signal,          help="Direction of correlation at best lag")
    c4.metric("Model R²",        r_sq_label,      help=f"OLS regression R² across {n_obs} observations")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB A — CORRELATION TABLE + LAG CHART
# ─────────────────────────────────────────────────────────────────────────────

def _render_correlation_tab(results: Dict) -> None:
    """Bar chart of r by lag + data table."""
    corr_list = results.get("corr_results", [])

    # lag slider
    max_lag = st.slider("Max Lag (months)", min_value=2, max_value=12, value=6,
                        key="corr_lag_slider",
                        help="Show correlation for lags 0 → N months")

    # run analysis on demand
    col_run, col_info = st.columns([2, 8])
    with col_run:
        if st.button("▶ Run Analysis", key="run_corr_analysis", type="primary"):
            with st.spinner("Running correlation + OLS regression…"):
                try:
                    results_new = run_full_analysis(max_lag=max_lag) if _ENGINE else {}
                    st.session_state["corr_results_cache"] = results_new
                    st.success("Analysis complete.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")

    with col_info:
        st.caption(
            "Pearson cross-correlation between Monthly Highway KM Completed (lagged) "
            "and Monthly Bitumen Import Volume.  Lag 0 = same month."
        )

    # use cached or passed results
    cached = st.session_state.get("corr_results_cache", {})
    if cached:
        corr_list = cached.get("corr_results", corr_list)

    if not corr_list:
        # try loading from JSON table
        if _HUB:
            corr_list = NormalizedTables.corr_results(50)

    if not corr_list:
        st.info("No correlation data yet.  Click **▶ Run Analysis** above.")
        return

    if _PANDAS:
        df_corr = pd.DataFrame(corr_list)
        # filter by slider lag
        if "lag_months" in df_corr.columns:
            df_corr = df_corr[df_corr["lag_months"] <= max_lag]

        # bar chart
        if _ALTAIR and not df_corr.empty and "correlation" in df_corr.columns:
            # colour by strength
            df_corr["strength"] = df_corr["correlation"].apply(_corr_strength)
            df_corr["abs_r"]    = df_corr["correlation"].abs()

            # find best lag row
            best_idx  = df_corr["abs_r"].idxmax() if not df_corr.empty else None
            best_lag_val = int(df_corr.loc[best_idx, "lag_months"]) if best_idx is not None else -1

            df_corr["is_best"] = df_corr["lag_months"] == best_lag_val

            bar = (
                alt.Chart(df_corr)
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(
                    x=alt.X("lag_months:O", title="Lag (months)", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("correlation:Q", title="Pearson r",
                            scale=alt.Scale(domain=[-1.0, 1.0]),
                            axis=alt.Axis(format=".2f")),
                    color=alt.condition(
                        alt.datum.is_best,
                        alt.value("#16a34a"),
                        alt.value("#2196F3"),
                    ),
                    tooltip=[
                        alt.Tooltip("lag_months:O",  title="Lag (months)"),
                        alt.Tooltip("correlation:Q", title="r",      format=".3f"),
                        alt.Tooltip("p_value:Q",     title="p-value",format=".4f"),
                        alt.Tooltip("n_obs:Q",       title="N obs"),
                        alt.Tooltip("strength:N",    title="Strength"),
                    ],
                )
                .properties(height=300, title="Cross-Correlation: Highway KM [t-lag] vs Bitumen Demand [t]")
            )
            # zero reference line
            rule = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule(color="#aaa", strokeDash=[4,4]).encode(y="y:Q")
            st.altair_chart(bar + rule, use_container_width=True)

        # table
        st.markdown("##### Correlation Results Table")
        display_cols = [c for c in ["lag_months","correlation","p_value","n_obs","series_x","series_y","notes"] if c in df_corr.columns]
        rename_map = {
            "lag_months":"Lag (m)","correlation":"Pearson r","p_value":"p-value",
            "n_obs":"N obs","series_x":"Series X","series_y":"Series Y","notes":"Notes",
        }
        fmt = {"Pearson r":"{:.3f}", "p-value":"{:.4f}"}
        try:
            styled = df_corr[display_cols].rename(columns=rename_map).style.format(fmt, na_rep="—")
            st.dataframe(styled, use_container_width=True, hide_index=True)
        except Exception:
            st.dataframe(df_corr[display_cols].rename(columns=rename_map), use_container_width=True, hide_index=True)

    # interpretation
    if corr_list:
        try:
            import math
            best_row = max(corr_list, key=lambda x: abs(x.get("correlation", 0)))
            best_r   = best_row.get("correlation", 0)
            best_l   = best_row.get("lag_months", 0)
            pval     = best_row.get("p_value", 1)
            sig      = "significant (p < 0.05)" if pval < 0.05 else "not statistically significant"
            st.info(
                f"**Strongest correlation**: r = **{best_r:.3f}** at lag **{best_l} month(s)** "
                f"({_corr_strength(best_r)}, {sig}).  "
                f"Interpretation: highway completions {best_l} month(s) earlier {'positively' if best_r > 0 else 'negatively'} "
                f"correlate with bitumen import demand."
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  TAB B — REGRESSION MODEL
# ─────────────────────────────────────────────────────────────────────────────

def _render_regression_tab(results: Dict) -> None:
    """Coefficient table, R², direction/strength interpretation."""
    # use cached results
    cached = st.session_state.get("corr_results_cache", {})
    eff_results = cached if cached else results

    reg = eff_results.get("regression", {})

    if not reg:
        # try loading from JSON
        if _HUB:
            coeff_data = NormalizedTables.corr_results(10)  # fallback read
            # also check tbl_regression_coeff via direct load
            try:
                import json, pathlib
                BASE = pathlib.Path(__file__).resolve().parent.parent
                path = BASE / "tbl_regression_coeff.json"
                if path.exists():
                    with open(path, encoding="utf-8") as f:
                        raw = json.load(f)
                    if isinstance(raw, list) and raw:
                        if _PANDAS:
                            df_coeff = pd.DataFrame(raw)
                            st.markdown("##### OLS Regression Coefficients (last run)")
                            st.dataframe(df_coeff, use_container_width=True, hide_index=True)
                            return
            except Exception:
                pass

        st.info("No regression data yet.  Click **▶ Run Analysis** in the Correlation tab.")
        return

    # formula
    formula = eff_results.get("formula", "")
    if formula:
        st.markdown(f"**Model Formula:**  `{formula}`")

    # R²
    r_sq = reg.get("r_squared", eff_results.get("r_squared", None))
    lag  = eff_results.get("best_lag", "?")
    n    = eff_results.get("n_obs", "?")
    c1, c2, c3 = st.columns(3)
    c1.metric("R²",         f"{r_sq:.3f}" if r_sq is not None else "N/A",
              help="Proportion of variance in demand explained by the model")
    c2.metric("Best Lag",   f"{lag}m",    help="Highway KM lag used in regression")
    c3.metric("Observations", str(n),     help="Number of monthly data points")

    # coefficients table
    coefficients = reg.get("coefficients", {})
    interp       = reg.get("interpretation", {})
    if coefficients and _PANDAS:
        rows = []
        for feat, coef in coefficients.items():
            rows.append({
                "Feature":         feat,
                "Coefficient":     round(coef, 4),
                "Sign":            "+" if coef >= 0 else "−",
                "Interpretation":  interp.get(feat, "—"),
            })
        df_coeff = pd.DataFrame(rows)

        # colour sign
        if _ALTAIR:
            chart = (
                alt.Chart(df_coeff)
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(
                    x=alt.X("Feature:N", title="Feature"),
                    y=alt.Y("Coefficient:Q", title="OLS Coefficient",
                            axis=alt.Axis(format=".4f")),
                    color=alt.condition(
                        alt.datum.Coefficient > 0,
                        alt.value("#16a34a"),
                        alt.value("#F44336"),
                    ),
                    tooltip=["Feature:N", "Coefficient:Q", "Sign:N", "Interpretation:N"],
                )
                .properties(height=260, title="OLS Regression Coefficients")
            )
            rule = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule(color="#aaa", strokeDash=[4,4]).encode(y="y:Q")
            st.altair_chart(chart + rule, use_container_width=True)

        st.markdown("##### Coefficient Table")
        st.dataframe(df_coeff, use_container_width=True, hide_index=True)

    elif coefficients:
        for feat, coef in coefficients.items():
            st.write(f"**{feat}**: {coef:.4f}  |  {interp.get(feat,'')}")

    # model interpretation prose
    st.markdown("##### Model Interpretation")
    if r_sq is not None:
        if r_sq >= 0.60:
            label = "Good fit — model explains most variance."
        elif r_sq >= 0.30:
            label = "Moderate fit — partial explanatory power."
        else:
            label = "Weak fit — other factors dominate demand."
        st.markdown(
            f"R² = **{r_sq:.3f}** — {label}  \n"
            f"Model: `Demand[t] = α + β₁·HighwayKM[t-{lag}] + β₂·CrudeOil[t] + β₃·FX_USDINR[t] + ε`  \n"
            "Coefficients show the marginal change in monthly import demand (MT) "
            "for a unit increase in each predictor, holding others constant."
        )

    with st.expander("📐 Model Assumptions & Limitations", expanded=False):
        st.markdown(
            """
- **OLS assumptions**: linearity, no multicollinearity, homoscedastic residuals.
- **Sample size**: model accuracy improves with ≥ 24 monthly observations.
- **Proxy data**: demand proxy is estimated from UN Comtrade import data, not actual consumption.
- **Highway KM**: All-India aggregate — state-level variation not captured.
- **Currency FX**: Monthly average USD/INR as a general macro proxy.
- Use model for directional insight only; not for precise demand forecasting.
"""
        )


# ─────────────────────────────────────────────────────────────────────────────
#  TAB C — INSIGHTS FEED
# ─────────────────────────────────────────────────────────────────────────────

def _render_insights_tab(results: Dict) -> None:
    """Auto-generated insights timeline + alert logic."""
    cached   = st.session_state.get("corr_results_cache", {})
    eff      = cached if cached else results
    insights = eff.get("insights", [])

    # also read from tbl_insights.json
    if _HUB:
        stored = NormalizedTables.insights(50)
        # merge, deduplicate on insight_text
        seen_texts = {i.get("insight_text","") for i in insights}
        for s in stored:
            if s.get("insight_text","") not in seen_texts:
                insights.append(s)
                seen_texts.add(s.get("insight_text",""))

    # severity filter
    severity_filter = st.selectbox(
        "Filter by severity",
        ["All", "ALERT", "HIGH", "MEDIUM", "INFO"],
        key="insight_severity_filter",
    )

    if severity_filter != "All":
        insights = [i for i in insights if i.get("severity","").upper() == severity_filter]

    if not insights:
        st.info(
            "No insights generated yet.  "
            "Run analysis from the **Correlation** tab to generate insights."
        )
        return

    # sort newest first (by date_ist if available)
    try:
        insights = sorted(insights, key=lambda x: x.get("date_ist",""), reverse=True)
    except Exception:
        pass

    st.markdown(f"**{len(insights)} insight(s)** found.")

    _SEVERITY_ICONS = {
        "ALERT":  "🚨",
        "HIGH":   "🔴",
        "MEDIUM": "🟡",
        "INFO":   "🔵",
    }
    _SEVERITY_COLORS = {
        "ALERT":  "#dc2626",   # red   5.5:1
        "HIGH":   "#c2410c",   # orange-red 5.6:1
        "MEDIUM": "#d97706",   # amber 4.6:1
        "INFO":   "#1d6dd8",   # blue  4.6:1
    }

    for insight in insights:
        severity    = insight.get("severity", "INFO").upper()
        icon        = _SEVERITY_ICONS.get(severity, "ℹ️")
        color       = _SEVERITY_COLORS.get(severity, "#5a6474")
        text        = insight.get("insight_text", "")
        date        = insight.get("date_ist", "")
        trigger     = insight.get("trigger_metric", "")

        with st.container():
            st.markdown(
                f"""<div style="border-left:4px solid {color};padding:8px 12px;margin-bottom:8px;
                background:rgba(0,0,0,0.02);border-radius:0 4px 4px 0;">
                <span style="font-weight:600;color:{color};">{icon} {severity}</span>
                &nbsp;<span style="color:#888;font-size:0.82em;">{date}</span>
                <br><span style="font-size:0.95em;">{text}</span>
                {f'<br><span style="color:#888;font-size:0.78em;">Trigger: {trigger}</span>' if trigger else ''}
                </div>""",
                unsafe_allow_html=True,
            )

    # alert box: km rising but imports dropping
    _render_alert_logic(eff)


def _render_alert_logic(results: Dict) -> None:
    """Special alert: highway KM up but imports down."""
    if not _ENGINE or not _PANDAS:
        return

    try:
        df = load_monthly_series()
        if df is None or df.empty:
            return
        if "km_completed" not in df.columns or "demand_proxy_mt" not in df.columns:
            return
        if len(df) < 2:
            return

        df = df.sort_values("period_label") if "period_label" in df.columns else df
        last2 = df.tail(2)
        km_delta  = last2["km_completed"].iloc[-1] - last2["km_completed"].iloc[-2]
        dem_delta = last2["demand_proxy_mt"].iloc[-1] - last2["demand_proxy_mt"].iloc[-2]

        if km_delta > 0 and dem_delta < 0:
            st.warning(
                "⚠️ **Divergence Alert**: Highway KM completions are rising "
                f"(+{km_delta:,.0f} km) but bitumen import demand is falling "
                f"({dem_delta:,.0f} MT).  This may indicate inventory drawdown, "
                "refinery supply substitution, or data lag — investigate further."
            )
        elif km_delta > 0 and dem_delta > 0:
            st.success(
                f"✅ **Aligned Signal**: Both highway KM (+{km_delta:,.0f} km) and "
                f"demand (+{dem_delta:,.0f} MT) are rising — consistent with model prediction."
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN ENTRY
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Main render function — called from dashboard.py routing."""
    # initialise session cache
    if "corr_results_cache" not in st.session_state:
        st.session_state["corr_results_cache"] = {}

    # load any stored results for KPI display
    results: Dict = st.session_state.get("corr_results_cache", {})

    # if cache empty, try reading from stored tables
    if not results and _HUB:
        corr_stored = NormalizedTables.corr_results(20)
        if corr_stored:
            try:
                best = max(corr_stored, key=lambda x: abs(x.get("correlation", 0)))
                results = {
                    "best_lag":    best.get("lag_months"),
                    "best_r":      best.get("correlation", 0),
                    "n_obs":       best.get("n_obs", 0),
                    "corr_results": corr_stored,
                }
            except Exception:
                pass

    # KPI bar
    _render_kpi_bar(results)
    st.markdown("---")

    # Tabs
    tabs = st.tabs([
        "📊 Correlation",
        "📐 Regression Model",
        "💡 Insights",
    ])

    with tabs[0]:
        _render_correlation_tab(results)

    with tabs[1]:
        _render_regression_tab(results)

    with tabs[2]:
        _render_insights_tab(results)
