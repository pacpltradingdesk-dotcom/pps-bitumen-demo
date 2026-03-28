# -*- coding: utf-8 -*-
"""
PPS Anantam — Infra Demand Intelligence Dashboard
===================================================
7-tab UI: Heatmap | Target Rankings | Live Feed | Alerts |
          Trend Analysis | Source Health | Backfill & Settings
"""

import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
import datetime
import streamlit as st

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(t): pass

try:
    import infra_demand_engine as ide
    _ENGINE_OK = True
except Exception as _e:
    _ENGINE_OK = False
    _ENGINE_ERR = str(_e)

# Vastu Design System colors
NAVY = "#1e3a5f"
GREEN = "#2d6a4f"
GOLD = "#c9a84c"
FIRE = "#b85c38"


def render():
    """Main entry point — called by dashboard.py."""
    display_badge("real-time")

    # Header banner
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{NAVY},{GREEN});color:white;
                padding:18px 24px;border-radius:12px;margin-bottom:16px;">
      <div style="font-size:1.3rem;font-weight:800;">
        🏗️ Infra Demand Intelligence (2-Year + Live)
      </div>
      <div style="font-size:0.82rem;opacity:0.88;margin-top:4px;">
        GDELT News + Budget Cross-Check + Tender Signals → Bitumen Demand Estimation by State/City
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not _ENGINE_OK:
        st.error(f"Engine import failed: {_ENGINE_ERR}")
        return

    # Initialize tables on first render
    if "infra_tables_init" not in st.session_state:
        ide.init_infra_tables()
        st.session_state["infra_tables_init"] = True

    # Quick stats header
    _render_stats_bar()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🗺️ India Heatmap",
        "🎯 Target Rankings",
        "📰 Live Feed",
        "🚨 Alerts",
        "📈 Trend Analysis",
        "💚 Source Health",
        "⚙️ Backfill & Settings",
    ])

    with tab1:
        _render_heatmap()
    with tab2:
        _render_rankings()
    with tab3:
        _render_live_feed()
    with tab4:
        _render_alerts()
    with tab5:
        _render_trends()
    with tab6:
        _render_source_health()
    with tab7:
        _render_settings()


def _render_stats_bar():
    """Quick stats row at top."""
    stats = ide.get_news_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Articles", f"{stats['total_articles']:,}")
    c2.metric("States Covered", stats["states_covered"])
    c3.metric("Tender Signals", f"{stats['tender_signals']:,}")
    c4.metric("Last Fetch", stats["last_fetch"][:16] if stats["last_fetch"] != "Never" else "Never")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: INDIA HEATMAP
# ═══════════════════════════════════════════════════════════════════════════════

def _render_heatmap():
    st.subheader("State-wise Demand Heatmap (Next 30 Days)")

    scores = ide.get_heatmap_data()
    if not scores:
        st.info("No data yet. Run a backfill or live update first.")
        return

    # Grid layout: 4 columns
    cols_per_row = 4
    for i in range(0, len(scores), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(scores):
                break
            s = scores[idx]
            score = s.get("composite_score", 0)
            likelihood = s.get("demand_likelihood", "Low")
            mt_min = s.get("mt_min", 0)
            mt_max = s.get("mt_max", 0)

            if score >= 65:
                bg_color = GREEN
                badge = "🟢 HIGH"
            elif score >= 35:
                bg_color = GOLD
                badge = "🟡 MEDIUM"
            else:
                bg_color = FIRE
                badge = "🔴 LOW"

            col.markdown(f"""
            <div style="background:{bg_color};color:white;padding:12px;border-radius:10px;
                        margin-bottom:8px;min-height:120px;">
              <div style="font-size:0.9rem;font-weight:700;">{s['state']}</div>
              <div style="font-size:1.4rem;font-weight:800;margin:4px 0;">{score:.0f}</div>
              <div style="font-size:0.72rem;opacity:0.9;">{badge}</div>
              <div style="font-size:0.7rem;margin-top:4px;">
                {mt_min:,} – {mt_max:,} MT
              </div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: TARGET RANKINGS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_rankings():
    st.subheader("Top Target States by Demand Score")

    col7, col15, col30 = st.columns(3)

    for col, days, label in [(col7, 7, "Next 7 Days"), (col15, 15, "Next 15 Days"), (col30, 30, "Next 30 Days")]:
        with col:
            st.markdown(f"**{label}**")
            rankings = ide.get_target_rankings(days, 10)
            if not rankings:
                st.info("No data")
                continue

            for rank, r in enumerate(rankings, 1):
                score = r.get("composite_score", 0)
                if score >= 65:
                    color = GREEN
                elif score >= 35:
                    color = GOLD
                else:
                    color = FIRE

                reasons = r.get("reason_codes", [])
                reason_text = reasons[0] if reasons else "—"

                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;
                            border-left:4px solid {color};margin-bottom:4px;
                            background:#f8f9fa;border-radius:0 6px 6px 0;">
                  <span style="font-size:0.9rem;font-weight:700;color:{color};width:24px;">#{rank}</span>
                  <div style="flex:1;">
                    <div style="font-size:0.82rem;font-weight:600;">{r['state']}</div>
                    <div style="font-size:0.68rem;color:#666;">
                      {r.get('mt_min',0):,}–{r.get('mt_max',0):,} MT &nbsp;|&nbsp; {reason_text}
                    </div>
                  </div>
                  <span style="font-size:1rem;font-weight:800;color:{color};">{score:.0f}</span>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: LIVE FEED
# ═══════════════════════════════════════════════════════════════════════════════

def _render_live_feed():
    st.subheader("Live Infrastructure News Feed")

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        state_filter = st.selectbox("State", ["All"] + sorted(ide.INDIAN_STATES.keys()), key="feed_state")
    with fc2:
        cat_filter = st.selectbox("Category", ["All", "infrastructure", "tender", "budget", "disruption", "general"], key="feed_cat")
    with fc3:
        limit = st.selectbox("Show", [25, 50, 100, 200], key="feed_limit")

    state_val = state_filter if state_filter != "All" else None
    cat_val = cat_filter if cat_filter != "All" else None
    articles = ide.get_live_feed(limit=limit, state=state_val, category=cat_val)

    if not articles:
        st.info("No articles found. Run a backfill or live update to fetch data.")
        return

    st.caption(f"Showing {len(articles)} articles")

    for art in articles:
        sent = art.get("sentiment_label", "neutral")
        if sent == "positive":
            sent_badge = "🟢"
        elif sent == "negative":
            sent_badge = "🔴"
        else:
            sent_badge = "⚪"

        cat = art.get("category", "general")
        cat_colors = {"tender": GOLD, "infrastructure": GREEN, "disruption": FIRE, "budget": NAVY, "general": "#666"}
        cat_color = cat_colors.get(cat, "#666")

        st.markdown(f"""
        <div style="padding:8px 12px;border-bottom:1px solid #eee;display:flex;gap:10px;align-items:flex-start;">
          <div style="min-width:80px;font-size:0.7rem;color:#888;">{(art.get('published_at',''))[:10]}</div>
          <div style="flex:1;">
            <div style="font-size:0.82rem;font-weight:500;">
              <a href="{art.get('source_url','#')}" target="_blank" style="color:{NAVY};text-decoration:none;">
                {art.get('title','')[:120]}
              </a>
            </div>
            <div style="font-size:0.68rem;color:#888;margin-top:2px;">
              {art.get('state','—') or '—'} &nbsp;·&nbsp;
              {art.get('department','') or ''} &nbsp;·&nbsp;
              <span style="color:{cat_color};font-weight:600;">{cat.upper()}</span>
              &nbsp;{sent_badge}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_alerts():
    st.subheader("Demand Intelligence Alerts")

    alerts = ide.get_infra_alerts(status="new", limit=50)
    if not alerts:
        st.success("No active alerts.")
        return

    for a in alerts:
        prio = a.get("priority", "P2")
        if prio == "P0":
            border_color, bg = "#dc3545", "#fef2f2"
        elif prio == "P1":
            border_color, bg = "#fd7e14", "#fff7ed"
        else:
            border_color, bg = "#0d6efd", "#eff6ff"

        st.markdown(f"""
        <div style="border-left:4px solid {border_color};background:{bg};
                    padding:12px 16px;border-radius:0 8px 8px 0;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <span style="font-size:0.7rem;font-weight:700;color:{border_color};
                           background:white;padding:2px 8px;border-radius:4px;
                           border:1px solid {border_color};">{prio}</span>
              &nbsp;
              <span style="font-size:0.7rem;color:#888;">{a.get('alert_type','')}</span>
            </div>
            <span style="font-size:0.68rem;color:#888;">{(a.get('created_at',''))[:16]}</span>
          </div>
          <div style="font-size:0.88rem;font-weight:600;margin:6px 0 4px 0;">{a.get('title','')}</div>
          <div style="font-size:0.76rem;color:#555;">{a.get('description','')}</div>
          <div style="font-size:0.68rem;color:#888;margin-top:4px;">
            State: {a.get('state','—') or '—'}
          </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: TREND ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_trends():
    st.subheader("2-Year Trend Analysis")

    trend = ide.get_trend_data(months=24)
    months_data = trend.get("months", [])

    if not months_data:
        st.info("No trend data available. Run a backfill first.")
        return

    import pandas as pd
    df = pd.DataFrame(months_data)

    # Article volume chart
    st.markdown(f"**Monthly Article Volume**")
    if "month" in df.columns and "total" in df.columns:
        chart_df = df[["month", "total"]].set_index("month")
        st.bar_chart(chart_df, color=NAVY)

    # Tender signals chart
    if "tenders" in df.columns:
        st.markdown(f"**Monthly Tender Signals**")
        chart_df2 = df[["month", "tenders"]].set_index("month")
        st.bar_chart(chart_df2, color=GOLD)

    # Sentiment chart
    if "avg_sentiment" in df.columns:
        st.markdown(f"**Average Sentiment Score**")
        chart_df3 = df[["month", "avg_sentiment"]].set_index("month")
        st.line_chart(chart_df3, color=GREEN)

    # Disruption signals
    if "disruptions" in df.columns:
        st.markdown(f"**Disruption Signals**")
        chart_df4 = df[["month", "disruptions"]].set_index("month")
        st.bar_chart(chart_df4, color=FIRE)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: SOURCE HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

def _render_source_health():
    st.subheader("Data Source Health Monitor")

    sources = ide.get_source_health()
    if not sources:
        st.info("No source data yet. Sources will appear after first sync.")
        return

    for src in sources:
        health = src.get("health_score", 0)
        status = src.get("status", "unknown")

        if status == "live":
            status_color = GREEN
            status_icon = "🟢"
        elif status == "failing":
            status_color = FIRE
            status_icon = "🔴"
        else:
            status_color = GOLD
            status_icon = "🟡"

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;
                    border:1px solid #e5e7eb;border-radius:8px;margin-bottom:6px;">
          <span style="font-size:1.2rem;">{status_icon}</span>
          <div style="flex:1;">
            <div style="font-size:0.88rem;font-weight:600;">{src.get('source_name','')}</div>
            <div style="font-size:0.7rem;color:#888;">
              Type: {src.get('source_type','')} &nbsp;|&nbsp;
              Records: {src.get('total_records',0):,} &nbsp;|&nbsp;
              Last success: {(src.get('last_success','') or 'Never')[:16]}
            </div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:1.1rem;font-weight:800;color:{status_color};">{health:.0f}%</div>
            <div style="font-size:0.65rem;color:{status_color};text-transform:uppercase;">{status}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7: BACKFILL & SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def _render_settings():
    st.subheader("Backfill & Settings")

    # Backfill section
    st.markdown("---")
    st.markdown("**📥 GDELT Backfill**")
    st.caption("Fetch historical infrastructure news from GDELT. Each month makes one API call.")

    bc1, bc2 = st.columns([1, 2])
    with bc1:
        months = st.number_input("Months to backfill", min_value=1, max_value=24, value=6, key="bf_months")
    with bc2:
        st.markdown("")
        st.markdown("")
        if st.button("🚀 Start Backfill", key="btn_backfill", type="primary"):
            progress = st.progress(0, text="Starting backfill...")
            status_text = st.empty()

            def update_progress(pct, msg):
                progress.progress(pct / 100, text=msg)
                status_text.caption(msg)

            result = ide.run_backfill(months=months, progress_callback=update_progress)
            progress.progress(100, text="Complete!")
            st.success(
                f"Backfill complete: {result['articles_inserted']} articles inserted, "
                f"{result['budget_seeded']} budget records, "
                f"{result['scores_computed']} demand scores computed."
            )
            if result["errors"]:
                with st.expander(f"⚠️ {len(result['errors'])} warnings"):
                    for e in result["errors"]:
                        st.text(e)

    # Live update button
    st.markdown("---")
    st.markdown("**🔄 Live Update**")
    st.caption("Fetch latest GDELT articles and recompute demand scores.")
    if st.button("🔄 Run Live Update Now", key="btn_live"):
        with st.spinner("Running live update..."):
            result = ide.run_live_update()
        st.success(
            f"Live update: {result['articles_inserted']} new articles, "
            f"{result['scores_computed']} scores, {result['alerts_generated']} alerts."
        )
        if result["errors"]:
            for e in result["errors"]:
                st.warning(e)

    # Settings
    st.markdown("---")
    st.markdown("**⚙️ API Configuration**")

    try:
        from settings_engine import load_settings, save_settings
        settings = load_settings()

        sc1, sc2 = st.columns(2)
        with sc1:
            enabled = st.toggle("Infra Demand Intelligence Enabled",
                                value=settings.get("infra_demand_enabled", True),
                                key="infra_enabled_toggle")
        with sc2:
            interval = st.number_input("GDELT Sync Interval (minutes)",
                                       min_value=30, max_value=720, step=30,
                                       value=settings.get("gdelt_sync_interval_min", 120),
                                       key="gdelt_interval")

        if st.button("💾 Save Settings", key="btn_save_infra"):
            settings["infra_demand_enabled"] = enabled
            settings["gdelt_sync_interval_min"] = interval
            save_settings(settings)
            st.success("Settings saved!")

    except Exception as e:
        st.warning(f"Settings engine not available: {e}")

    # data.gov.in key
    st.markdown("---")
    st.markdown("**🔑 data.gov.in API Key**")
    st.caption("Free key from https://data.gov.in/user/register — enables budget data fetch.")
    try:
        from api_hub_engine import HubCatalog
        current_key = HubCatalog.get_key("data_gov_in_highways")
        new_key = st.text_input("API Key", value=current_key or "", type="password", key="datagov_key")
        if st.button("Save Key", key="btn_save_key"):
            HubCatalog.update_field("data_gov_in_highways", "key_value", new_key)
            HubCatalog.update_field("data_gov_in_highways", "status", "Live" if new_key else "Disabled")
            st.success("API key saved!")
    except Exception:
        st.info("Configure data.gov.in key in API Hub settings.")
