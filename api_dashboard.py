"""
PPS Anantams Logistics AI
API Intelligence Dashboard v3.0
=================================
Enhanced API registry view: 25 APIs, data center info, ping latency,
reliability scores, tab-API mapping, rate limits, and auto-repair status.
"""

import streamlit as st
import pandas as pd

try:
    from ui_badges import display_badge
except ImportError:
    def display_badge(_x): pass

try:
    from api_manager import (
        load_config, load_stats, get_reliability_scores,
        test_api_health, run_all_health_checks, ts_str,
    )
    AM_AVAILABLE = True
except ImportError:
    AM_AVAILABLE = False
    def load_config(): return {"widgets": {}, "tab_api_map": {}, "health_check_config": {}}
    def load_stats(): return {}
    def get_reliability_scores(): return {}
    def test_api_health(_x): return None
    def run_all_health_checks(_force=True): return {}, {}
    def ts_str(): return "—"

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

DATA_CENTER_LABELS = {
    "CDN_GLOBAL":      "🌐 CDN Global",
    "ECB_EU":          "🇪🇺 ECB Europe",
    "GITHUB_CDN":      "🐙 GitHub CDN",
    "YAHOO_FINANCE":   "📈 Yahoo Finance",
    "OPEN_METEO_EU":   "☁️ Open-Meteo EU",
    "WORLD_BANK_DC":   "🏦 World Bank DC",
    "NAGER_EU":        "📅 Nager.at EU",
    "REST_COUNTRIES":  "🗺️ Rest Countries",
    "TIME_API":        "⏰ TimeAPI.io",
    "LOCAL":           "💻 Local System",
}

AUTH_LABELS = {
    "none":   "🔓 No Auth",
    "apikey": "🔑 API Key",
    "oauth":  "🔐 OAuth",
}

STATUS_COLOR = {
    "OK":      "#22c55e",
    "Fail":    "#ef4444",
    "Unknown": "#94a3b8",
    "Not Run": "#94a3b8",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _status_icon(status: str) -> str:
    icons = {"OK": "🟢", "Fail": "🔴", "Unknown": "⚪", "Not Run": "⚪"}
    return icons.get(status, "⚪")


def _reliability_bar(pct: float) -> str:
    filled = int(pct / 10)
    bar    = "█" * filled + "░" * (10 - filled)
    color  = "#22c55e" if pct >= 90 else ("#f59e0b" if pct >= 70 else "#ef4444")
    return f'<span style="color:{color};font-family:monospace">{bar}</span> {pct:.0f}%'


def _section_header(icon: str, title: str, color: str = "#3b82f6"):
    st.markdown(
        f'<div style="border-left:4px solid {color};padding:6px 12px;margin:14px 0 8px 0;'
        f'background:linear-gradient(90deg,{color}18,transparent)">'
        f'<span style="font-size:1.05rem;font-weight:700">{icon} {title}</span></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpi_row(config: dict, stats: dict, rel_scores: dict):
    """Top-level KPI summary row."""
    widgets   = config.get("widgets", {})
    total     = len(widgets)
    ok        = sum(1 for w in widgets if stats.get(w, {}).get("status") == "OK")
    failed    = sum(1 for w in widgets if stats.get(w, {}).get("status") == "Fail")
    unknown   = total - ok - failed
    avg_rel   = round(sum(rel_scores.values()) / len(rel_scores), 1) if rel_scores else 0
    fallbacks = sum(stats.get(w, {}).get("fallback_activations", 0) for w in widgets)
    auto_rep  = sum(stats.get(w, {}).get("auto_repair_count", 0) for w in widgets)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    metrics = [
        (c1, "Total APIs",         total,    "Registered in registry", "#3b82f6"),
        (c2, "Healthy",            f"🟢 {ok}", "Status: OK",            "#22c55e"),
        (c3, "Failed",             f"🔴 {failed}", "Needs attention",   "#ef4444"),
        (c4, "Not Tested",         f"⚪ {unknown}", "Run health check", "#94a3b8"),
        (c5, "Avg Reliability",    f"{avg_rel}%", "Across all APIs",    "#8b5cf6"),
        (c6, "Auto-Repairs",       auto_rep,  f"Fallbacks: {fallbacks}", "#f59e0b"),
    ]
    for col, label, val, delta, color in metrics:
        col.markdown(
            f'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);border-left:4px solid {color};'
            f'border-radius:10px;padding:12px 14px;text-align:center;margin:2px">'
            f'<div style="color:#94a3b8;font-size:0.76rem">{label}</div>'
            f'<div style="color:#f8fafc;font-size:1.5rem;font-weight:800">{val}</div>'
            f'<div style="color:{color};font-size:0.72rem">{delta}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption(f"Last refreshed: {ts_str()}")


def _render_registry_table(config: dict, stats: dict, rel_scores: dict):
    """Full 25-API registry table."""
    _section_header("📡", "Full API Registry — All 25 Endpoints", color="#3b82f6")

    widgets = config.get("widgets", {})
    rows = []
    for wid, conf in widgets.items():
        s     = stats.get(wid, {})
        status= s.get("status", "Not Run")
        lat   = s.get("avg_latency_ms", 0)
        calls = s.get("calls", 0)
        fails = s.get("failures", 0)
        rel   = rel_scores.get(wid, 0.0)
        fb    = s.get("fallback_activations", 0)
        ar    = s.get("auto_repair_count", 0)
        dc    = DATA_CENTER_LABELS.get(conf.get("data_center", ""), conf.get("data_center", "—"))
        auth  = AUTH_LABELS.get(conf.get("auth_type", "none"), "🔓 No Auth")
        tabs  = ", ".join(conf.get("tabs_used", []))[:60]
        rate  = conf.get("rate_limit", "—")
        cor   = "✅" if conf.get("cors_support") else "❌"
        fb_id = conf.get("fallback", "—")

        rows.append({
            "St": _status_icon(status),
            "API ID":       wid,
            "Name":         conf.get("name", ""),
            "Provider":     conf.get("provider", ""),
            "Data Center":  dc,
            "Auth":         auth,
            "CORS":         cor,
            "Refresh":      f"{conf.get('refresh_interval_sec',60)}s",
            "Rate Limit":   rate,
            "Reliability":  f"{rel:.0f}%",
            "Avg Lat (ms)": lat,
            "Calls":        calls,
            "Fails":        fails,
            "Fallback":     fb_id,
            "FB Activs":    fb,
            "Auto-Repairs": ar,
            "Purpose":      conf.get("purpose", "")[:60],
            "Tabs Used":    tabs,
        })

    if not rows:
        st.warning("No APIs registered in api_config.json.")
        return

    df = pd.DataFrame(rows)

    def color_status(val):
        if val == "🟢": return "color:#22c55e"
        if val == "🔴": return "color:#ef4444"
        return "color:#94a3b8"

    def color_rel(val):
        try:
            pct = float(str(val).replace("%", ""))
            if pct >= 90: return "color:#22c55e;font-weight:bold"
            if pct >= 70: return "color:#f59e0b;font-weight:bold"
            return "color:#ef4444;font-weight:bold"
        except Exception:
            return ""

    styled = df.style.applymap(color_status, subset=["St"]).applymap(color_rel, subset=["Reliability"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_tab_api_map(config: dict):
    """Tab ↔ API mapping section."""
    _section_header("🗺️", "Tab → API Dependency Map", color="#8b5cf6")

    tab_map = config.get("tab_api_map", {})
    if not tab_map:
        st.info("No tab-API map found in api_config.json.")
        return

    rows = []
    for tab, apis in tab_map.items():
        rows.append({"Dashboard Tab": tab, "Required APIs": ", ".join(apis), "Count": len(apis)})

    df = pd.DataFrame(rows).sort_values("Count", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption("This map tells you which APIs each dashboard tab depends on. If an API goes down, affected tabs are listed here.")


def _render_data_centers(config: dict, stats: dict):
    """Data center grouping & status."""
    _section_header("🏢", "Data Center Grouping", color="#06b6d4")

    widgets = config.get("widgets", {})
    dc_groups = {}
    for wid, conf in widgets.items():
        dc = conf.get("data_center", "UNKNOWN")
        dc_groups.setdefault(dc, []).append(wid)

    for dc, api_list in sorted(dc_groups.items()):
        dc_label = DATA_CENTER_LABELS.get(dc, dc)
        ok_count = sum(1 for a in api_list if stats.get(a, {}).get("status") == "OK")
        fail_count = len(api_list) - ok_count
        with st.expander(f"{dc_label} — {len(api_list)} APIs | 🟢 {ok_count} healthy"):
            for a in api_list:
                s = stats.get(a, {})
                icon = _status_icon(s.get("status", "Not Run"))
                lat  = s.get("avg_latency_ms", 0)
                name = widgets[a].get("name", a)
                st.markdown(
                    f'<span style="color:#94a3b8">{icon} <b>{name}</b> '
                    f'<span style="font-size:0.8rem">({a})</span> — '
                    f'Latency: {lat} ms | Calls: {s.get("calls",0)} | Fails: {s.get("failures",0)}'
                    f'</span>',
                    unsafe_allow_html=True,
                )


def _render_rate_limits(config: dict):
    """Rate limit & quota overview."""
    _section_header("⏱️", "Rate Limits & Quota Overview", color="#f59e0b")

    widgets = config.get("widgets", {})
    rows = []
    for wid, conf in widgets.items():
        rows.append({
            "API ID":       wid,
            "Name":         conf.get("name", ""),
            "Rate Limit":   conf.get("rate_limit", "Unknown"),
            "Auth Required":AUTH_LABELS.get(conf.get("auth_type","none"), "🔓 No Auth"),
            "CORS":         "✅ Yes" if conf.get("cors_support") else "❌ No",
            "Refresh (sec)":conf.get("refresh_interval_sec", 60),
            "Fallback":     conf.get("fallback", "None"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("All APIs use free tiers. yfinance is used as fallback only to avoid rate exhaustion.")


def _render_health_diagnostics(config: dict):
    """Interactive health diagnostic — test individual API."""
    _section_header("🧪", "Health Diagnostics — Test Individual API", color="#10b981")

    widgets = config.get("widgets", {})
    if not widgets:
        st.warning("No APIs configured.")
        return

    col_sel, col_btn, col_res = st.columns([2, 1, 3])
    with col_sel:
        target = st.selectbox("Select API to test", list(widgets.keys()),
                              format_func=lambda x: f"{x} — {widgets[x].get('name','')}")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("🔌 Ping API", type="primary")

    with col_res:
        if run_btn:
            if AM_AVAILABLE:
                with st.spinner(f"Pinging {target}..."):
                    result = test_api_health(target)
                if result:
                    st.success(f"✅ {target} — OK")
                    # Show parsed values only — no raw backend JSON exposed in UI
                    cur = result.get("current")
                    h7d = result.get("history_7d")
                    if cur is not None:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Current Value", f"{cur:,.4g}")
                        with col_b:
                            if h7d is not None and h7d != cur:
                                delta = round(cur - h7d, 4)
                                st.metric("7-Day Change", f"{delta:+.4g}")
                    holidays = result.get("holidays")
                    if holidays:
                        st.caption(f"{len(holidays)} holidays returned")
                    forecast = result.get("forecast_7d")
                    if forecast:
                        st.caption(f"7-day forecast: {len(forecast)} data points received")
                else:
                    st.error(f"❌ {target} — All retries + fallback failed. Check error log.")
            else:
                st.warning("api_manager not available.")

    # Full system check
    st.markdown("---")
    c_btn, c_out = st.columns([1, 3])
    with c_btn:
        full_btn = st.button("🚀 Run Full System Health Check (all 25 APIs)")
    with c_out:
        if full_btn and AM_AVAILABLE:
            with st.spinner("Checking all APIs... may take 30–60 seconds."):
                summary, results = run_all_health_checks(force=True)
            st.success(
                f"✅ {summary['healthy']}/{summary['total']} APIs healthy "
                f"({summary['health_pct']}%) — {summary['timestamp']}"
            )
            if summary["failed"] > 0:
                failed = [w for w, r in results.items() if not r["ok"]]
                st.warning(f"⚠️ Failed: {', '.join(failed)}")


def _render_reliability(config: dict, rel_scores: dict):
    """Reliability leaderboard."""
    _section_header("🏆", "API Reliability Leaderboard", color="#22c55e")

    widgets = config.get("widgets", {})
    if not rel_scores:
        st.info("No reliability data yet. Run a health check or let the dashboard fetch data automatically.")
        return

    rows = []
    for wid, pct in sorted(rel_scores.items(), key=lambda x: -x[1]):
        rows.append({
            "Rank":        "",
            "API ID":      wid,
            "Name":        widgets.get(wid, {}).get("name", ""),
            "Reliability": f"{pct:.1f}%",
            "Grade":       "A+" if pct >= 99 else ("A" if pct >= 95 else ("B" if pct >= 85 else ("C" if pct >= 70 else "D"))),
        })

    for i, r in enumerate(rows, 1):
        r["Rank"] = f"#{i}"

    df = pd.DataFrame(rows)

    def grade_color(val):
        c = {"A+": "#22c55e", "A": "#16a34a", "B": "#f59e0b", "C": "#ea580c", "D": "#ef4444"}
        return f"color:{c.get(val,'#94a3b8')};font-weight:bold"

    def rel_color(val):
        try:
            pct = float(str(val).replace("%", ""))
            if pct >= 90: return "color:#22c55e"
            if pct >= 70: return "color:#f59e0b"
            return "color:#ef4444"
        except Exception:
            return ""

    styled = df.style.applymap(grade_color, subset=["Grade"]).applymap(rel_color, subset=["Reliability"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_about():
    """Architecture / About section."""
    _section_header("📖", "About the API Integration Layer", color="#64748b")

    st.markdown("""
**Architecture Overview:**

| Layer | Detail |
|-------|--------|
| Config | `api_config.json` — 25 APIs with full metadata (endpoint, auth, rate limit, parse rules, tabs_used) |
| Fetch Engine | `api_manager.py` — retry loop (3x), auto fallback to yfinance, stale cache fallback |
| Cache | `api_cache.json` — TTL-based, per-API refresh intervals (60 sec – 24 hr) |
| Stats | `api_stats.json` — live call counts, failure counts, latency rolling avg |
| Error Log | `api_error_log.json` — persistent bug tracker (max 1,000 records) |
| Change Log | `api_change_log.json` — full audit trail (max 2,000 records) |
| Dev Log | `api_dev_log.json` — deployments, model changes, alerts (max 500) |
| Health Log | `api_health_log.json` — continuous ping history (max 2,000) |

**Free API Sources:**
- **fawazahmed0** — USD/INR via GitHub CDN (no key, no rate limit)
- **Frankfurter.app** — ECB rates backup (free, no key)
- **omkarcloud** — Brent/WTI JSON via GitHub (no key)
- **yfinance** — Universal fallback (Nifty50, Sensex, DXY, VIX, Gold)
- **Open-Meteo** — Weather for 4 Indian port cities (free, no key, 10k/day)
- **World Bank API** — GDP, Infrastructure, CPI (free, no key, 500/day)
- **Nager.at** — India public holidays (free, no key)
- **timeapi.io** — IST time sync (free, no key)
- **REST Countries** — Country metadata (free, no key)
""")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render():
    display_badge("real-time")

    st.markdown("""
<div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
padding:20px 24px;border-radius:12px;margin-bottom:20px;
border-left:5px solid #3b82f6;">
<div style="font-size:1.5rem;font-weight:900;color:#f8fafc;">
🌐 API Intelligence Dashboard
</div>
<div style="color:#94a3b8;font-size:0.9rem;margin-top:4px">
Real-time monitoring of all 25 registered APIs • Health status • Reliability scores •
Data center grouping • Rate limits • Auto-repair tracker
</div>
</div>
""", unsafe_allow_html=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    config     = load_config()
    stats      = load_stats()
    rel_scores = get_reliability_scores()

    # ── KPI Row ───────────────────────────────────────────────────────────────
    _render_kpi_row(config, stats, rel_scores)

    st.markdown("---")

    # ── Main tabs ─────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📡 Registry",
        "🗺️ Tab→API Map",
        "🏢 Data Centers",
        "⏱️ Rate Limits",
        "🏆 Reliability",
        "🧪 Diagnostics",
        "📖 About",
    ])

    with t1:
        _render_registry_table(config, stats, rel_scores)

    with t2:
        _render_tab_api_map(config)

    with t3:
        _render_data_centers(config, stats)

    with t4:
        _render_rate_limits(config)

    with t5:
        _render_reliability(config, rel_scores)

    with t6:
        _render_health_diagnostics(config)

    with t7:
        _render_about()
