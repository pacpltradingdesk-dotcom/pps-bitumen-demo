"""
News Dashboard — PPS Anantams Logistics AI
===========================================
Streamlit UI for the News Intelligence module.

Tabs:
  🌍 International  — Global crude oil, OPEC, refinery, logistics news
  🇮🇳 Domestic      — India highway, NHAI, MoRTH, bitumen, tender news
  📡 Source Health  — API/RSS source uptime, last fetch status
  📜 Fetch Log      — Audit log of all fetch cycles
  ⚙️ Settings       — API keys (NewsAPI, GNews), refresh interval

Features:
  • Scrolling headline ticker (CSS animation)
  • Breaking news flash alert bar (score ≥ 80)
  • Sound toggle (Web Audio API beep via components.html)
  • Filters: time range, tags, source, impact slider, search
  • News cards with Open Source link, Mark Read, Save
  • Deduplication cluster badge
  • IST timestamps in DD-MM-YYYY HH:MM format
  • Hindi news support
"""

from __future__ import annotations

import sys
import os

# ── path so we can import news_engine from parent dir ──────────────────────
_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

import streamlit as st
import streamlit.components.v1 as components
import news_engine as ne

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

SENTIMENT_ICON = {"positive": "🟢", "negative": "🔴", "neutral": "🔵"}
IMPACT_COLOR   = {
    range(80, 101): "#ff2d2d",   # Breaking — red
    range(60,  80): "#ff8c00",   # High — orange
    range(40,  60): "#f5c518",   # Medium — gold
    range(0,   40): "#555555",   # Low — grey
}

def _impact_color(score: int) -> str:
    for r, c in IMPACT_COLOR.items():
        if score in r:
            return c
    return "#555555"

def _impact_label(score: int) -> str:
    if score >= 80: return "🔴 Breaking"
    if score >= 60: return "🟠 High"
    if score >= 40: return "🟡 Medium"
    return "⚫ Low"

TAG_COLORS: dict[str, str] = {
    "crude_oil":      "#8B0000",
    "opec":           "#C0392B",
    "brent":          "#A93226",
    "wti":            "#B03A2E",
    "middle_east":    "#7D6608",
    "sanctions":      "#1A5276",
    "forex":          "#117A65",
    "logistics":      "#1F618D",
    "refinery":       "#784212",
    "supply_chain":   "#2E4053",
    "nhai":           "#1E8449",
    "morth":          "#196F3D",
    "pmgsy":          "#1D8348",
    "pwd":            "#239B56",
    "tender":         "#F39C12",
    "budget":         "#D35400",
    "bitumen":        "#6E2F1A",
    "highway":        "#1A5276",
    "funding":        "#117864",
    "policy":         "#6C3483",
}

def _tag_badge(tag: str) -> str:
    color = TAG_COLORS.get(tag, "#444444")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 7px;'
        f'border-radius:10px;font-size:0.72em;margin:1px 2px;'
        f'display:inline-block;">{tag}</span>'
    )

# ══════════════════════════════════════════════════════════════════════════════
# CSS — injected once per render
# ══════════════════════════════════════════════════════════════════════════════

_CSS = """
<style>
/* ── Scrolling Ticker ─────────────────────────────────────────────────── */
.news-ticker-wrap {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    overflow: hidden;
    padding: 6px 0;
    margin-bottom: 12px;
    position: relative;
}
.news-ticker-label {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: #e63946;
    color: #fff;
    font-weight: 700;
    font-size: 0.78em;
    padding: 0 10px;
    display: flex;
    align-items: center;
    z-index: 2;
    border-radius: 6px 0 0 6px;
    white-space: nowrap;
}
.news-ticker-inner {
    display: flex;
    padding-left: 90px;
    overflow: hidden;
}
.news-ticker-text {
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 60s linear infinite;
    color: #c9d1d9;
    font-size: 0.82em;
}
@keyframes ticker-scroll {
    0%   { transform: translateX(100vw); }
    100% { transform: translateX(-200%); }
}
/* ── Breaking Alert Bar ───────────────────────────────────────────────── */
.breaking-bar {
    background: linear-gradient(90deg, #7f0000, #c0392b, #7f0000);
    background-size: 200% 100%;
    animation: pulse-bg 2s ease infinite;
    color: #fff;
    padding: 10px 16px;
    border-radius: 6px;
    margin-bottom: 10px;
    font-weight: 700;
    font-size: 0.88em;
    display: flex;
    align-items: center;
    gap: 10px;
}
@keyframes pulse-bg {
    0%  { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100%{ background-position: 0% 50%; }
}
.breaking-dot {
    width: 10px; height: 10px;
    background: #fff;
    border-radius: 50%;
    animation: blink 1s step-start infinite;
    flex-shrink: 0;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
}
/* ── News Card ────────────────────────────────────────────────────────── */
.news-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}
.news-card:hover {
    border-color: #58a6ff;
}
.news-card.breaking-card {
    border-left: 4px solid #ff2d2d;
    background: #1a0505;
}
.news-card.saved-card {
    border-left: 4px solid #2ea44f;
}
.news-card.read-card {
    opacity: 0.65;
}
.news-headline {
    font-size: 0.95em;
    font-weight: 600;
    color: #c9d1d9;
    line-height: 1.4;
    margin: 0 0 6px 0;
}
.news-headline a {
    color: #58a6ff;
    text-decoration: none;
}
.news-headline a:hover {
    text-decoration: underline;
}
.news-meta {
    font-size: 0.74em;
    color: #8b949e;
    margin-bottom: 6px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
}
.news-summary {
    font-size: 0.82em;
    color: #8b949e;
    margin: 6px 0 8px 0;
    line-height: 1.5;
}
.news-tags {
    margin: 4px 0 8px 0;
    line-height: 1.8;
}
.impact-badge {
    font-size: 0.75em;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    color: #fff;
}
/* ── Source Health Table ──────────────────────────────────────────────── */
.source-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 6px;
    margin-bottom: 4px;
    background: #161b22;
    border: 1px solid #30363d;
    font-size: 0.82em;
    color: #c9d1d9;
}
.source-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-ok      { background: #2ea44f; }
.dot-fail    { background: #e63946; }
.dot-nokey   { background: #f5c518; }
.dot-unknown { background: #555; }
/* ── Stat pill ────────────────────────────────────────────────────────── */
.stat-pill {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: center;
}
.stat-num { font-size: 1.8em; font-weight: 700; color: #58a6ff; }
.stat-lbl { font-size: 0.75em; color: #8b949e; margin-top: 2px; }
/* ── Hindi badge ──────────────────────────────────────────────────────── */
.lang-hi {
    background: #ff9933;
    color: #fff;
    font-size: 0.68em;
    padding: 1px 5px;
    border-radius: 4px;
    font-weight: 700;
}
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
# BEEP SOUND (Web Audio API — no file needed)
# ══════════════════════════════════════════════════════════════════════════════

_BEEP_JS = """
<script>
function playBreakingBeep() {
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.5);
    } catch(e) {}
}
playBreakingBeep();
</script>
"""

# ══════════════════════════════════════════════════════════════════════════════
# TICKER
# ══════════════════════════════════════════════════════════════════════════════

def _render_ticker(articles: list[dict]):
    if not articles:
        return
    headlines = "  ◆  ".join(
        f"[{a.get('impact_score',0)}] {a.get('headline','')[:100]}"
        for a in articles[:20]
    )
    html = f"""
    <div class="news-ticker-wrap">
        <div class="news-ticker-label">📡 LIVE</div>
        <div class="news-ticker-inner">
            <span class="news-ticker-text">{headlines}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# BREAKING ALERT BAR
# ══════════════════════════════════════════════════════════════════════════════

def _render_breaking_bar(breaking: list[dict], sound_on: bool):
    if not breaking:
        return
    count = len(breaking)
    top   = breaking[0]
    bar_html = f"""
    <div class="breaking-bar">
        <div class="breaking-dot"></div>
        <span>🚨 BREAKING ({count} alert{"s" if count>1 else ""}):</span>
        <span style="font-weight:400">{top.get('headline','')[:120]}</span>
        <span style="margin-left:auto;opacity:0.8;font-size:0.85em">{top.get('source_name','')} | {top.get('published_at_ist','')}</span>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)
    if sound_on:
        components.html(_BEEP_JS, height=0)

# ══════════════════════════════════════════════════════════════════════════════
# FILTER BAR
# ══════════════════════════════════════════════════════════════════════════════

def _render_filters(region: str, key_prefix: str) -> dict:
    """Render filter bar and return filter dict."""
    with st.expander("🔍 Filters & Search", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            time_range = st.selectbox(
                "Time Range",
                ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
                key=f"{key_prefix}_time"
            )
        with c2:
            all_sources = ["All"] + ne.get_article_sources(region)
            source_sel  = st.selectbox("Source", all_sources, key=f"{key_prefix}_src")
        with c3:
            lang_opts = ["All", "English (en)", "Hindi (hi)"]
            lang_sel  = st.selectbox("Language", lang_opts, key=f"{key_prefix}_lang")

        c4, c5 = st.columns([2, 1])
        with c4:
            search_txt = st.text_input("Search headlines / summary", key=f"{key_prefix}_srch",
                                       placeholder="e.g. crude oil, NHAI tender...")
        with c5:
            impact_min = st.slider("Min Impact Score", 0, 100, 0, key=f"{key_prefix}_imp")

        all_tags  = ne.get_all_tags(region)
        tags_sel  = st.multiselect("Filter by Tags", all_tags, key=f"{key_prefix}_tags")

        status_sel = st.multiselect("Status", ["new", "read", "saved"],
                                    default=["new", "read", "saved"],
                                    key=f"{key_prefix}_status")

    age_map = {
        "Last 24 Hours": 24,
        "Last 7 Days": 168,
        "Last 30 Days": 720,
        "All Time": 99999,
    }
    lang_map = {"All": "All", "English (en)": "en", "Hindi (hi)": "hi"}

    return {
        "max_age_hours": age_map.get(time_range, 168),
        "source":        source_sel,
        "language":      lang_map.get(lang_sel, "All"),
        "search":        search_txt.strip(),
        "impact_min":    impact_min,
        "tags":          tags_sel or None,
        "status":        status_sel,
    }

# ══════════════════════════════════════════════════════════════════════════════
# SINGLE NEWS CARD
# ══════════════════════════════════════════════════════════════════════════════

def _render_card(a: dict, idx: int, region_key: str):
    """
    Render a single news card using native Streamlit components.
    Avoids st.markdown(HTML) which shows raw tags in some Streamlit versions.
    """
    score    = a.get("impact_score", 0)
    status   = a.get("status", "new")
    lang     = a.get("language", "en")
    tags     = a.get("tags", [])
    senti    = a.get("sentiment", "neutral")
    headline = a.get("headline", "—")
    url      = a.get("source_url", "#")
    src_name = a.get("source_name", "")
    pub_time = a.get("published_at_ist", "")
    summary  = a.get("summary", "")[:300]
    art_id   = a.get("article_id", "")
    dup      = a.get("duplicate_count", 1)

    # Border color based on status/score
    if score >= 80:
        border = "4px solid #ff2d2d"
        bg     = "#1a0505"
    elif status == "saved":
        border = "4px solid #2ea44f"
        bg     = "#0d1117"
    elif status == "read":
        border = "1px solid #30363d"
        bg     = "#0d1117"
    else:
        border = "1px solid #30363d"
        bg     = "#161b22"

    opacity = "0.65" if status == "read" else "1.0"

    with st.container():
        st.markdown(
            f'<div style="border-left:{border};background:{bg};border-radius:8px;'
            f'padding:14px 16px;margin-bottom:10px;opacity:{opacity};">',
            unsafe_allow_html=True,
        )

        # Row 1: Impact badge + sentiment + language + source + time
        il       = _impact_label(score)
        ic       = _impact_color(score)
        senti_ic = SENTIMENT_ICON.get(senti, "🔵")
        lang_tag = " `HI`" if lang == "hi" else ""
        dup_note = f"  _(+{dup-1} similar)_" if dup > 1 else ""

        meta_parts = [
            f'<span style="background:{ic};color:#fff;padding:2px 8px;border-radius:10px;'
            f'font-size:0.75em;font-weight:700">{il} {score}</span>',
            f'<span style="color:#8b949e;font-size:0.78em">{senti_ic} {src_name} &nbsp;|&nbsp; 🕐 {pub_time}{dup_note}</span>',
        ]
        if lang == "hi":
            meta_parts.insert(1, '<span style="background:#ff9933;color:#fff;font-size:0.68em;'
                               'padding:1px 5px;border-radius:4px;font-weight:700">HI</span>')

        st.markdown(" &nbsp; ".join(meta_parts), unsafe_allow_html=True)

        # Row 2: Headline as clickable link
        st.markdown(
            f'<p style="font-size:0.95em;font-weight:600;color:#c9d1d9;margin:6px 0 4px 0;">'
            f'<a href="{url}" target="_blank" style="color:#58a6ff;text-decoration:none;">'
            f'{headline}</a></p>',
            unsafe_allow_html=True,
        )

        # Row 3: Tags as inline colored badges
        if tags:
            badge_parts = []
            for t in tags:
                color = TAG_COLORS.get(t, "#444444")
                badge_parts.append(
                    f'<span style="background:{color};color:#fff;padding:2px 7px;'
                    f'border-radius:10px;font-size:0.72em;margin:1px 2px;'
                    f'display:inline-block">{t}</span>'
                )
            st.markdown('<div style="margin:4px 0 6px 0">' + "".join(badge_parts) + "</div>",
                        unsafe_allow_html=True)

        # Row 4: Summary
        if summary:
            st.markdown(
                f'<p style="font-size:0.82em;color:#8b949e;margin:4px 0 8px 0;line-height:1.5">'
                f'{summary}</p>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # Action buttons (outside the card div — native Streamlit)
    b1, b2, b3, b4, _ = st.columns([1, 1, 1, 1, 3])
    with b1:
        if st.button("✅ Read", key=f"read_{region_key}_{idx}_{art_id}", use_container_width=True):
            ne.mark_article(art_id, "read")
            st.rerun()
    with b2:
        if st.button("🔖 Save", key=f"save_{region_key}_{idx}_{art_id}", use_container_width=True):
            ne.mark_article(art_id, "saved")
            st.rerun()
    with b3:
        if st.button("🗑 Archive", key=f"arch_{region_key}_{idx}_{art_id}", use_container_width=True):
            ne.mark_article(art_id, "archived")
            st.rerun()
    with b4:
        st.link_button("🔗 Open Source", url, use_container_width=True)
    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# STATS ROW
# ══════════════════════════════════════════════════════════════════════════════

def _render_stats(articles: list[dict], region: str):
    total    = len(articles)
    breaking = sum(1 for a in articles if a.get("impact_score", 0) >= 80)
    unread   = sum(1 for a in articles if a.get("status") == "new")
    saved    = sum(1 for a in articles if a.get("status") == "saved")
    hi_count = sum(1 for a in articles if a.get("language") == "hi")
    last_t   = ne.get_last_fetch_time()

    pills = [
        (str(total),    "Total Articles"),
        (str(breaking), "Breaking"),
        (str(unread),   "Unread"),
        (str(saved),    "Saved"),
    ]
    if region == "Domestic":
        pills.append((str(hi_count), "Hindi"))

    cols = st.columns(len(pills) + 1)
    for i, (num, lbl) in enumerate(pills):
        with cols[i]:
            st.markdown(
                f'<div class="stat-pill"><div class="stat-num">{num}</div>'
                f'<div class="stat-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )
    with cols[-1]:
        st.markdown(
            f'<div class="stat-pill"><div class="stat-num" style="font-size:0.9em;color:#8b949e">'
            f'{last_t}</div><div class="stat-lbl">Last Fetch (IST)</div></div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# NEWS LIST (International or Domestic)
# ══════════════════════════════════════════════════════════════════════════════

def _render_news_list(region: str, sound_on: bool, key_prefix: str):
    # Breaking news
    breaking = ne.get_breaking_news(region)
    _render_breaking_bar(breaking, sound_on)

    # Stats
    all_arts = ne.get_articles(region=region, max_age_hours=168)
    _render_stats(all_arts, region)

    st.markdown("---")

    # Ticker
    _render_ticker(all_arts[:30])

    # Filters
    f = _render_filters(region, key_prefix)

    # Fetch filtered articles
    articles = ne.get_articles(
        region       = region,
        max_age_hours= f["max_age_hours"],
        tags         = f["tags"],
        source       = f["source"],
        impact_min   = f["impact_min"],
        search       = f["search"],
        language     = f["language"],
    )

    # Status filter (post-query)
    if f["status"]:
        articles = [a for a in articles if a.get("status", "new") in f["status"]]

    if not articles:
        st.info("No articles match the current filters. Try broadening the filters or trigger a manual fetch.")
        return

    st.caption(f"Showing {len(articles)} article{'s' if len(articles)!=1 else ''}")

    # Render cards
    for idx, a in enumerate(articles):
        _render_card(a, idx, key_prefix)

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE HEALTH TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_source_health():
    st.subheader("📡 News Source Health")
    health = ne.get_source_health()

    # Group by region
    for region_label in ["International", "Domestic"]:
        sources = [s for s in health if s.get("region") == region_label]
        st.markdown(f"**{region_label} Sources ({len(sources)})**")
        for s in sources:
            status  = s.get("status", "Unknown")
            dot_cls = {
                "OK": "dot-ok", "Fail": "dot-fail",
                "No Key": "dot-nokey",
            }.get(status, "dot-unknown")

            error_str = s.get("error", "")
            error_html = f' <span style="color:#e63946;font-size:0.8em">— {error_str[:80]}</span>' if error_str else ""

            count_str = f"  {s.get('count',0)} articles" if s.get("count", 0) > 0 else ""
            last_str  = s.get("last_fetch", "") or "Never"

            st.markdown(
                f'<div class="source-row">'
                f'<div class="source-dot {dot_cls}"></div>'
                f'<span style="min-width:180px;font-weight:600">{s["name"]}</span>'
                f'<span style="color:#8b949e;min-width:50px">[{s["type"]}]</span>'
                f'<span style="color:#8b949e;min-width:60px">{status}</span>'
                f'<span style="color:#8b949e;min-width:170px">🕐 {last_str}</span>'
                f'<span style="color:#2ea44f">{count_str}</span>'
                f'{error_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("")

    # Manual fetch button
    st.markdown("---")
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("🔄 Fetch Now", use_container_width=True, type="primary"):
            with st.spinner("Fetching all sources..."):
                result = ne.run_fetch_cycle()
            total_added = sum(result.values())
            st.success(f"Fetch complete — {total_added} new articles added")
            st.rerun()
    with c2:
        st.caption("Triggers an immediate fetch cycle across all enabled sources (normally auto every 10 min).")

# ══════════════════════════════════════════════════════════════════════════════
# FETCH LOG TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_fetch_log():
    st.subheader("📜 Fetch Log (Last 200 Events)")
    logs = ne.get_fetch_log(200)
    if not logs:
        st.info("No fetch log yet. Trigger a manual fetch or wait for the auto-fetch cycle.")
        return

    import pandas as pd
    df = pd.DataFrame(logs)[
        ["fetch_id","source_id","start_time_ist","end_time_ist",
         "records_fetched","status","error_message"]
    ].rename(columns={
        "fetch_id":        "ID",
        "source_id":       "Source",
        "start_time_ist":  "Start (IST)",
        "end_time_ist":    "End (IST)",
        "records_fetched": "Fetched",
        "status":          "Status",
        "error_message":   "Error",
    })
    st.dataframe(df, use_container_width=True, height=400)

    st.markdown("---")
    st.subheader("📋 Change History (Last 100 Events)")
    changes = ne.get_change_history(100)
    if changes:
        df2 = pd.DataFrame(changes)[
            ["timestamp_ist","change_type","article_id","old_value","new_value","reason","actor"]
        ]
        st.dataframe(df2, use_container_width=True, height=300)
    else:
        st.info("No change history yet.")

# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS TAB
# ══════════════════════════════════════════════════════════════════════════════

def _render_settings():
    st.subheader("⚙️ News Module Settings")

    st.markdown("#### Optional API Keys")
    st.caption(
        "RSS feeds work without any key. NewsAPI and GNews keys unlock additional sources "
        "(free tier: 100 requests/day each)."
    )

    with st.form("news_api_keys"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**NewsAPI** — [newsapi.org](https://newsapi.org) (free: 100/day)")
            newsapi_key = st.text_input(
                "NewsAPI Key",
                value=ne.get_news_api_key("newsapi_key"),
                type="password",
                placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                key="newsapi_input"
            )
        with c2:
            st.markdown("**GNews** — [gnews.io](https://gnews.io) (free: 100/day)")
            gnews_key = st.text_input(
                "GNews Key",
                value=ne.get_news_api_key("gnews_key"),
                type="password",
                placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                key="gnews_input"
            )

        submitted = st.form_submit_button("💾 Save API Keys", type="primary")
        if submitted:
            if newsapi_key.strip():
                ne.save_news_cfg("newsapi_key", newsapi_key.strip())
            if gnews_key.strip():
                ne.save_news_cfg("gnews_key", gnews_key.strip())
            st.success("API keys saved to news_config.json")

    st.markdown("---")
    st.markdown("#### Source Registry (14 Sources)")
    import pandas as pd
    df = pd.DataFrame(ne.NEWS_SOURCES)[
        ["source_id","name","type","region","language","reliability","free_limit","refresh_interval_min"]
    ].rename(columns={
        "source_id":              "ID",
        "name":                   "Source Name",
        "type":                   "Type",
        "region":                 "Region",
        "language":               "Lang",
        "reliability":            "Reliability %",
        "free_limit":             "Free Limit",
        "refresh_interval_min":   "Refresh (min)",
    })
    st.dataframe(df, use_container_width=True, height=350)

    st.markdown("---")
    st.markdown("#### Data Management")
    col1, col2, col3 = st.columns(3)
    with col1:
        articles = ne.load_articles()
        st.metric("Stored Articles", len(articles))
    with col2:
        st.metric("Max Articles", ne.MAX_ARTICLES)
    with col3:
        st.metric("Dedup Threshold", f"{int(ne.DEDUP_THRESHOLD*100)}%")

    if st.button("🗑 Clear ALL Articles (reset to demo data)", type="secondary"):
        import os
        if ne.ARTICLES_FILE.exists():
            os.remove(str(ne.ARTICLES_FILE))
        st.success("Articles cleared — demo data will reload on next fetch.")
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render():
    # Inject CSS
    st.markdown(_CSS, unsafe_allow_html=True)

    # Header
    st.markdown(
        '<h2 style="margin-bottom:4px">📰 News Intelligence</h2>'
        '<p style="color:#8b949e;margin:0">PPS Anantam — Global & Domestic Market News</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Start auto-fetch on first load
    ne.start_auto_fetch()

    # Sound toggle (sidebar-style inline)
    hdr1, hdr2, hdr3 = st.columns([6, 1, 1])
    with hdr2:
        sound_on = st.toggle("🔔 Sound", value=False, key="news_sound_toggle",
                             help="Play a beep when breaking alerts are shown")
    with hdr3:
        if st.button("🔄 Refresh", key="news_manual_refresh", help="Reload articles from memory"):
            st.rerun()

    # Main tabs
    tab_intl, tab_dom, tab_health, tab_log, tab_settings = st.tabs([
        "🌍 International",
        "🇮🇳 Domestic India",
        "📡 Source Health",
        "📜 Fetch Log",
        "⚙️ Settings",
    ])

    with tab_intl:
        _render_news_list("International", sound_on, "intl")

    with tab_dom:
        _render_news_list("Domestic", sound_on, "dom")

    with tab_health:
        _render_source_health()

    with tab_log:
        _render_fetch_log()

    with tab_settings:
        _render_settings()
