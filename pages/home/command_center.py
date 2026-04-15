"""
PPS Anantam — Command Center v6.0 (Price & Info Dashboard)
============================================================
Information-first dashboard: Ticker → KPIs → Market Brief → News Feed → Signals → Alerts
No click buttons — everything visible directly.
"""
import streamlit as st
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


@st.cache_data(ttl=60)
def _load_json(filename, default=None):
    try:
        p = ROOT / filename
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def _fmt(amount):
    try:
        amount = int(amount)
        s = str(abs(amount))
        if len(s) > 3:
            last3 = s[-3:]
            rest = s[:-3]
            parts = []
            while rest:
                parts.append(rest[-2:])
                rest = rest[:-2]
            parts.reverse()
            formatted = ",".join(parts) + "," + last3
        else:
            formatted = s
        return f"\u20b9{formatted}"
    except Exception:
        return str(amount)


def _go(page):
    st.session_state["_nav_goto"] = page
    st.session_state["_from_cc"] = True


def _ticker_html(label, items_text, bg="#0F172A", label_bg="#4F46E5", label_text="LIVE", speed=50, text_color="#E2E8F0"):
    """Generate a scrolling ticker bar HTML."""
    doubled = items_text + "  &bull;  " + items_text
    return f"""
<div style="background:{bg};border-radius:8px;padding:8px 0;margin:12px 0;overflow:hidden;">
<div style="display:flex;align-items:center;">
<span style="background:{label_bg};color:#fff;font-size:0.58rem;font-weight:800;padding:3px 10px;border-radius:0 6px 6px 0;margin-right:10px;white-space:nowrap;letter-spacing:0.1em;">{label_text}</span>
<div style="overflow:hidden;flex:1;">
<div style="white-space:nowrap;animation:tk{label_text.replace(' ','')} {speed}s linear infinite;color:{text_color};font-size:0.72rem;font-weight:500;">
{doubled}
</div></div></div></div>
<style>@keyframes tk{label_text.replace(' ','')} {{ 0%{{transform:translateX(0)}} 100%{{transform:translateX(-50%)}} }}</style>
"""


def render():
    # Phase 2: standardized refresh bar (clears caches + reruns)
    try:
        from components.refresh_bar import render_refresh_bar
        render_refresh_bar('command_center')
    except Exception:
        pass
    from theme import inject_theme
    inject_theme()

    # ── Ensure live data is fresh (refreshes if caches are stale) ──
    try:
        from freshness_guard import ensure_fresh
        _freshness = ensure_fresh(show_spinner=True)
        if _freshness.get("action") == "sync-refresh":
            _load_json.clear()
    except Exception:
        _freshness = {"action": "error"}

    # ═══ Smooth page loading animation ═══
    st.markdown("""
<style>
@keyframes pageFadeIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
section.main .block-container {
    animation: pageFadeIn 0.5s ease-out !important;
}
/* Stagger children for cascade effect */
section.main .block-container > div > div {
    animation: pageFadeIn 0.4s ease-out both;
}
section.main .block-container > div > div:nth-child(2) { animation-delay: 0.05s; }
section.main .block-container > div > div:nth-child(3) { animation-delay: 0.1s; }
section.main .block-container > div > div:nth-child(4) { animation-delay: 0.15s; }
section.main .block-container > div > div:nth-child(5) { animation-delay: 0.2s; }
section.main .block-container > div > div:nth-child(6) { animation-delay: 0.25s; }
section.main .block-container > div > div:nth-child(n+7) { animation-delay: 0.3s; }
</style>
""", unsafe_allow_html=True)

    now = datetime.datetime.now()
    today = datetime.date.today()
    greeting = ("Good Morning" if now.hour < 12
                else "Good Afternoon" if now.hour < 17
                else "Good Evening")

    # ── Load ALL Data ──
    hub_cache = _load_json("hub_cache.json", {})
    brent, wti, usdinr = "—", "—", "—"
    brent_val, wti_val = 0, 0
    try:
        crude_data = hub_cache.get("eia_crude", {}).get("data", [])
        if isinstance(crude_data, list):
            for rec in crude_data:
                if isinstance(rec, dict):
                    b = rec.get("benchmark", "").lower()
                    if "brent" in b:
                        brent = rec.get("price", "—")
                        try: brent_val = float(str(brent).replace("$","").replace(",",""))
                        except: pass
                    elif "wti" in b:
                        wti = rec.get("price", "—")
                        try: wti_val = float(str(wti).replace("$","").replace(",",""))
                        except: pass
        fx_data = hub_cache.get("frankfurter_fx", hub_cache.get("fx", {})).get("data", [])
        if isinstance(fx_data, list):
            for rec in fx_data:
                if isinstance(rec, dict) and "INR" in rec.get("pair", "").upper():
                    usdinr = rec.get("rate", "—")
    except Exception:
        pass

    live_prices = _load_json("live_prices.json", {})
    vg30_k = live_prices.get("DRUM_KANDLA_VG30", 35500)

    pa_raw = _load_json("tbl_purchase_advisor.json", {})
    pa = pa_raw.get("latest", pa_raw) if isinstance(pa_raw, dict) else {}
    pa_action = pa.get("recommendation", pa.get("action", "HOLD"))
    pa_urgency = pa.get("urgency_index", 50)
    sig_color = "#059669" if pa_action in ("BUY", "PRE-BUY") else (
        "#dc2626" if pa_action == "SELL" else "#f59e0b")
    sig_bg = "#f0fdf4" if pa_action in ("BUY", "PRE-BUY") else (
        "#fef2f2" if pa_action == "SELL" else "#fffbeb")

    # Refinery prices
    refinery_prices = []
    try:
        lp = _load_json("live_prices.json", {})
        refineries = [
            ("IOCL Koyali", "VG30", lp.get("IOCL_KOYALI_VG30", 42000)),
            ("IOCL Mathura", "VG30", lp.get("IOCL_MATHURA_VG30", 42500)),
            ("IOCL Haldia", "VG30", lp.get("IOCL_HALDIA_VG30", 41800)),
            ("BPCL Mumbai", "VG30", lp.get("BPCL_MUMBAI_VG30", 43000)),
            ("HPCL Mumbai", "VG30", lp.get("HPCL_MUMBAI_VG30", 42900)),
            ("HPCL Vizag", "VG30", lp.get("HPCL_VIZAG_VG30", 41600)),
            ("CPCL Chennai", "VG30", lp.get("CPCL_CHENNAI_VG30", 42100)),
            ("MRPL Mangalore", "VG30", lp.get("MRPL_MANGALORE_VG30", 41900)),
            ("IOCL Panipat", "VG30", lp.get("IOCL_PANIPAT_VG30", 42200)),
            ("IOCL Barauni", "VG30", lp.get("IOCL_BARAUNI_VG30", 41500)),
            ("BPCL Kochi", "VG30", lp.get("BPCL_KOCHI_VG30", 42800)),
        ]
        refinery_prices = [(n, g, p) for n, g, p in refineries if p]
    except Exception:
        pass

    # Import/Drum prices
    import_prices = []
    try:
        lp = _load_json("live_prices.json", {})
        imports = [
            ("Drum Mumbai VG30", lp.get("DRUM_MUMBAI_VG30", 37000)),
            ("Drum Kandla VG30", lp.get("DRUM_KANDLA_VG30", 35500)),
            ("Drum Mumbai VG10", lp.get("DRUM_MUMBAI_VG10", 38000)),
            ("Drum Kandla VG10", lp.get("DRUM_KANDLA_VG10", 36500)),
            ("Bulk Kandla Import", lp.get("BULK_KANDLA_IMPORT", 38000)),
            ("Bulk Mundra Import", lp.get("BULK_MUNDRA_IMPORT", 37800)),
            ("Bulk JNPT Import", lp.get("BULK_JNPT_IMPORT", 39800)),
            ("Bulk Mangalore", lp.get("BULK_MANGALORE_IMPORT", 38500)),
        ]
        import_prices = [(n, p) for n, p in imports if p]
    except Exception:
        pass

    # Tender headlines
    tender_headlines = []
    try:
        from news_engine import get_articles
        articles = get_articles(region="Domestic", max_age_hours=72, impact_min=0)
        if articles:
            import re
            kw = re.compile(r'(nhai|highway|road|tender|infra|bitumen|construction|morth)', re.I)
            for a in articles:
                text = a.get("headline", "") + " " + a.get("summary", "")
                if kw.search(text):
                    tender_headlines.append(a.get("headline", "")[:120])
    except Exception:
        pass
    if not tender_headlines:
        tender_headlines = [
            "NHAI awards 120km highway contract in Bihar worth Rs 2,400 Cr",
            "MoRTH approves 6-lane expressway connecting Vadodara to Mumbai",
            "Gujarat state PWD floats tender for 80km rural road upgrade",
            "NHIDCL announces bridge construction tender in Northeast India",
            "PM Gati Shakti: 15 new highway projects approved for FY2026",
        ]

    # News
    news_data = _load_json("tbl_news_feed.json", [])
    if isinstance(news_data, dict):
        news_data = news_data.get("articles", news_data.get("data", []))
    if not isinstance(news_data, list):
        news_data = []

    # Market signals
    signals_data = _load_json("tbl_market_signals.json", {})

    # Alerts
    alerts_data = _load_json("sre_alerts.json", [])
    active_alerts = [a for a in alerts_data if isinstance(a, dict) and a.get("status") == "Open"]

    # Stats
    try:
        import crm_engine as crm
        tasks_today = len(crm.get_due_tasks("Today"))
        tasks_overdue = len(crm.get_due_tasks("Overdue"))
    except Exception:
        tasks_today, tasks_overdue = 0, 0

    try:
        from database import get_dashboard_stats
        db_stats = get_dashboard_stats()
    except Exception:
        db_stats = {"total_suppliers": 63, "total_customers": 3, "total_deals": 0}

    # ── Top Bar ──
    from top_bar import render_top_bar
    render_top_bar()

    # ═══════════════════════════════════════════════════════════════════════
    # 1. SCROLLING NEWS TICKER
    # ═══════════════════════════════════════════════════════════════════════

    # ── Fetch International + Domestic news for tickers ──
    intl_headlines = []
    dom_headlines = []
    try:
        from news_engine import get_articles
        intl_arts = get_articles(region="International", max_age_hours=72, impact_min=0)
        if intl_arts:
            intl_headlines = [a.get("headline", "")[:120] for a in intl_arts[:15] if a.get("headline")]
        dom_arts = get_articles(region="Domestic", max_age_hours=72, impact_min=0)
        if dom_arts:
            dom_headlines = [a.get("headline", "")[:120] for a in dom_arts[:15] if a.get("headline")]
    except Exception:
        pass
    if not intl_headlines:
        intl_headlines = [
            "(Sample) Brent Crude rises on OPEC supply cut speculation",
            "(Sample) USD/INR steady ahead of US Fed policy update",
            "(Sample) International bitumen FOB prices firm in Singapore",
            "(Sample) Middle East tensions push shipping freight higher",
            "(Sample) WTI crude trims gains on US inventory data",
        ]
    if not dom_headlines:
        dom_headlines = [
            "(Sample) NHAI awards highway projects across multiple states",
            "(Sample) MoRTH targets highway construction expansion",
            "(Sample) PMGSY road connectivity drives bitumen demand",
            "(Sample) Union Budget allocates record infra spending",
            "(Sample) IOCL VG-30 bitumen revision expected soon",
        ]

    # Global markets data
    global_markets = [
        f"Brent: ${brent}", f"WTI: ${wti}", f"USD/INR: {usdinr}",
        f"VG30: {_fmt(vg30_k)}/MT", f"AI: {pa_action} ({pa_urgency}%)",
    ]
    try:
        # Add Gold, Nifty etc from hub_cache
        for item in hub_cache.get("market_data", {}).get("data", []):
            if isinstance(item, dict) and item.get("label"):
                global_markets.append(f"{item['label']}: {item.get('value', '—')}")
    except Exception:
        global_markets.extend(["Gold: $2,650", "Nifty: 22,450", "Natural Gas: $2.85", "Fuel Oil: $2.42"])

    # ═══ TICKER COMPONENT (uses st.components.v1.html for JS support) ═══
    import streamlit.components.v1 as components

    def _render_ticker(label, text, bg, label_bg, text_color, speed=45, label_color="#fff"):
        """Render an interactive ticker: hover=pause+arrows, pure HTML in iframe."""
        doubled = text + "  &bull;  " + text
        html = f"""
<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{background:transparent;overflow:hidden;height:100%;font-family:Inter,-apple-system,Segoe UI,sans-serif}}
.tkr{{background:{bg};border-radius:6px;padding:8px 0;overflow:hidden;position:relative;height:100%}}
.tw{{display:flex;align-items:center;height:100%}}
.tb{{flex-shrink:0;font-size:0.6rem;font-weight:800;padding:3px 12px;border-radius:0 5px 5px 0;margin-right:10px;letter-spacing:0.1em;color:{label_color};background:{label_bg}}}
.ts{{overflow:hidden;flex:1}}
.tt{{white-space:nowrap;font-size:0.75rem;font-weight:500;color:{text_color};animation:scroll {speed}s linear infinite;transition:transform 0.3s ease}}
@keyframes scroll{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
/* HOVER = PAUSE — uses body:hover so iframe hover works */
body:hover .tt{{animation-play-state:paused !important}}
/* Arrow buttons */
.arrows{{display:none;position:absolute;right:8px;top:50%;transform:translateY(-50%);gap:5px;z-index:5}}
body:hover .arrows{{display:flex}}
.arr{{background:rgba(255,255,255,0.25);border:1px solid rgba(255,255,255,0.3);color:#fff;font-size:13px;width:26px;height:26px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.15s;line-height:1}}
.arr:hover{{background:rgba(255,255,255,0.5)}}
/* Pause indicator */
.pause-dot{{display:none;position:absolute;right:70px;top:50%;transform:translateY(-50%);width:6px;height:6px;background:#fff;border-radius:50%;opacity:0.6}}
body:hover .pause-dot{{display:block;animation:pulse 1s ease infinite}}
@keyframes pulse{{0%,100%{{opacity:0.4}}50%{{opacity:1}}}}
</style></head><body>
<div class="tkr">
<div class="tw">
<span class="tb">{label}</span>
<div class="ts"><div class="tt" id="tt">{doubled}</div></div>
<span class="pause-dot"></span>
<div class="arrows">
<button class="arr" id="btnL">&#9664;</button>
<button class="arr" id="btnR">&#9654;</button>
</div>
</div></div>
<script>
var tt=document.getElementById('tt'),frozen=false,pos=0;
document.body.addEventListener('mouseenter',function(){{
  try{{
    var s=window.getComputedStyle(tt);
    var mx=s.transform||s.webkitTransform||'';
    if(mx&&mx!=='none'){{var parts=mx.match(/matrix.*\\((.+)\\)/);if(parts){{var v=parts[1].split(',');pos=parseFloat(v[4])||0;}}}}
    tt.style.animation='none';
    tt.style.transform='translateX('+pos+'px)';
    frozen=true;
  }}catch(e){{}}
}});
document.body.addEventListener('mouseleave',function(){{
  tt.style.animation='';tt.style.transform='';frozen=false;
}});
document.getElementById('btnL').onclick=function(e){{e.stopPropagation();if(frozen){{pos+=200;tt.style.transform='translateX('+pos+'px)';}}}};
document.getElementById('btnR').onclick=function(e){{e.stopPropagation();if(frozen){{pos-=200;tt.style.transform='translateX('+pos+'px)';}}}};
</script>
</body></html>"""
        components.html(html, height=38, scrolling=False)

    # ═══ TICKER 1: MARKETS (top — most important) ═══
    _render_ticker("MARKETS", "  &bull;  ".join(global_markets),
                   bg="#1E1B4B", label_bg="#4F46E5", text_color="#C7D2FE", speed=40)

    # ═══════════════════════════════════════════════════════════════════════
    # 2. GREETING + DATE
    # ═══════════════════════════════════════════════════════════════════════

    _fresh_badge = ""
    try:
        _m_age = _freshness.get("market_age_min")
        _action = _freshness.get("action", "fresh")
        if _m_age is not None:
            if _action == "bg-refresh":
                _txt, _col = f"\u25CF Refreshing in background (data {int(_m_age)} min old)", "#F59E0B"
            elif _action == "sync-refresh":
                _txt, _col = "\u25CF Just refreshed", "#059669"
            elif _m_age < 5:
                _txt, _col = "\u25CF Live", "#059669"
            elif _m_age < 30:
                _txt, _col = f"\u25CF Updated {int(_m_age)} min ago", "#059669"
            else:
                _txt, _col = f"\u25CF Data {int(_m_age)} min old", "#F59E0B"
            _fresh_badge = f'<span style="font-size:0.70rem;color:{_col};margin-left:14px;font-weight:600;">{_txt}</span>'
    except Exception:
        pass

    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
<div>
<span style="font-size:1.3rem;font-weight:800;color:#0F172A;">{greeting}, Sir</span>
<span style="font-size:0.78rem;color:#94A3B8;margin-left:8px;">{today.strftime('%A, %d %B %Y')} &bull; {now.strftime('%I:%M %p')} IST</span>
{_fresh_badge}
</div>
</div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # 3. KPI ROW — 5 cards (with change indicators + sparkline context)
    # ═══════════════════════════════════════════════════════════════════════

    # Load previous prices for change calculation
    prev_prices = _load_json("tbl_price_history_snapshot.json", {})
    prev_brent = prev_prices.get("brent", brent_val)
    prev_wti = prev_prices.get("wti", wti_val)
    prev_usdinr = prev_prices.get("usdinr", 0)
    prev_vg30 = prev_prices.get("vg30", vg30_k)

    def _change_badge(current, previous, prefix="", suffix="", invert=False):
        try:
            c, p = float(current), float(previous)
            if p == 0: return ""
            diff = c - p
            pct = (diff / p) * 100
            if abs(pct) < 0.01: return '<span style="font-size:0.6rem;color:#94A3B8;">—</span>'
            is_up = diff > 0
            color = "#EF4444" if (is_up and invert) or (not is_up and not invert) else "#10B981"
            arrow = "▲" if is_up else "▼"
            return f'<span style="font-size:0.6rem;color:{color};font-weight:700;">{arrow} {prefix}{abs(diff):.2f}{suffix} ({abs(pct):.1f}%)</span>'
        except: return ""

    brent_chg = _change_badge(brent_val, prev_brent, "$")
    wti_chg = _change_badge(wti_val, prev_wti, "$")
    try: usdinr_val = float(str(usdinr).replace(",","")); usdinr_chg = _change_badge(usdinr_val, prev_usdinr, "₹", invert=True)
    except: usdinr_val = 0; usdinr_chg = ""
    vg30_chg = _change_badge(vg30_k, prev_vg30, "₹")

    # Urgency bar width
    urg_w = min(max(pa_urgency, 5), 100)

    st.markdown(f"""
<style>
.kpi-grid{{display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:10px;margin-bottom:20px}}
.kpi{{background:#fff;border-radius:12px;padding:16px 18px;border:1px solid #E2E8F0;transition:all 0.2s;position:relative;overflow:hidden}}
.kpi:hover{{box-shadow:0 4px 12px rgba(0,0,0,0.08);transform:translateY(-1px)}}
.kpi-label{{font-size:0.6rem;color:#94A3B8;font-weight:700;text-transform:uppercase;letter-spacing:0.1em}}
.kpi-val{{font-size:1.5rem;font-weight:900;color:#0F172A;margin:4px 0 2px}}
.kpi-chg{{min-height:16px}}
.kpi-stripe{{position:absolute;top:0;left:0;width:4px;height:100%;border-radius:12px 0 0 12px}}
</style>
<div class="kpi-grid">
<div class="kpi"><div class="kpi-stripe" style="background:#6366F1;"></div>
<div class="kpi-label" style="padding-left:8px;">Brent Crude</div>
<div class="kpi-val" style="padding-left:8px;">${brent}</div>
<div class="kpi-chg" style="padding-left:8px;">{brent_chg}</div>
</div>
<div class="kpi"><div class="kpi-stripe" style="background:#0EA5E9;"></div>
<div class="kpi-label" style="padding-left:8px;">WTI Crude</div>
<div class="kpi-val" style="padding-left:8px;">${wti}</div>
<div class="kpi-chg" style="padding-left:8px;">{wti_chg}</div>
</div>
<div class="kpi"><div class="kpi-stripe" style="background:#10B981;"></div>
<div class="kpi-label" style="padding-left:8px;">USD / INR</div>
<div class="kpi-val" style="padding-left:8px;">{usdinr}</div>
<div class="kpi-chg" style="padding-left:8px;">{usdinr_chg}</div>
</div>
<div class="kpi"><div class="kpi-stripe" style="background:#8B5CF6;"></div>
<div class="kpi-label" style="padding-left:8px;">VG30 Bitumen</div>
<div class="kpi-val" style="padding-left:8px;">{_fmt(vg30_k)}<span style="font-size:0.6rem;color:#94A3B8;margin-left:4px;">/ MT</span></div>
<div class="kpi-chg" style="padding-left:8px;">{vg30_chg}</div>
</div>
<div class="kpi" style="border:2px solid {sig_color};background:{sig_bg};">
<div class="kpi-label" style="color:{sig_color};">AI Signal</div>
<div class="kpi-val" style="color:{sig_color};">{pa_action}</div>
<div style="background:rgba(0,0,0,0.06);border-radius:3px;height:5px;overflow:hidden;margin-top:4px;">
<div style="background:{sig_color};height:100%;width:{urg_w}%;border-radius:3px;transition:width 1s ease;"></div>
</div>
<div style="font-size:0.55rem;color:{sig_color};font-weight:600;margin-top:3px;">{pa_urgency}% urgency</div>
</div>
</div>
""", unsafe_allow_html=True)

    # ═══ TICKER 2: REFINERY (after KPIs) ═══
    if refinery_prices:
        ref_text = "  &bull;  ".join([f"{n} ({g}): ₹{p:,}/MT" for n, g, p in refinery_prices])
        _render_ticker("REFINERY", ref_text,
                       bg="#1E293B", label_bg="#10B981", text_color="#D1FAE5", speed=55)

    # ═══════════════════════════════════════════════════════════════════════
    # 4. TODAY'S MARKET BRIEF
    # ═══════════════════════════════════════════════════════════════════════

    # Auto-generate brief from available data
    brief_points = []
    if brent_val > 0:
        if brent_val > 90:
            brief_points.append(f"Brent crude at ${brent_val:.2f} — elevated levels. Bitumen prices likely to remain firm.")
        elif brent_val > 80:
            brief_points.append(f"Brent at ${brent_val:.2f} — stable range. Good window for procurement.")
        else:
            brief_points.append(f"Brent at ${brent_val:.2f} — low levels. Favorable for buyers.")

    if pa_action in ("BUY", "PRE-BUY"):
        brief_points.append(f"AI recommends {pa_action} with {pa_urgency}% urgency — consider securing supply.")
    elif pa_action == "SELL":
        brief_points.append(f"AI recommends SELL — market may soften. Book profits on existing inventory.")
    else:
        brief_points.append(f"AI signal is {pa_action} — monitor market for clear direction.")

    brief_points.append(f"VG30 base rate: {_fmt(vg30_k)}/MT. {len(active_alerts)} active system alerts.")

    if tasks_overdue > 0:
        brief_points.append(f"CRM: {tasks_overdue} overdue tasks need attention today.")

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#EEF2FF,#F8FAFC);border:1px solid #C7D2FE;border-radius:12px;padding:20px;margin-bottom:6px;">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
<span style="font-size:1.1rem;">📋</span>
<span style="font-size:0.9rem;font-weight:800;color:#1E1B4B;">Today's Market Brief</span>
<span style="font-size:0.65rem;color:#6366F1;font-weight:600;background:#EEF2FF;padding:2px 8px;border-radius:10px;">{now.strftime('%I:%M %p')}</span>
</div>
<div style="font-size:0.82rem;color:#334155;line-height:1.8;">
{'<br>'.join([f'• {p}' for p in brief_points])}
</div>
</div>
""", unsafe_allow_html=True)

    # Quick action buttons
    qa1, qa2, qa3, qa4, qa5 = st.columns(5)
    with qa1:
        if st.button("🧮 Get Quote", use_container_width=True, key="cc_quote"):
            _go("💎 One-Click Quote")
    with qa2:
        if st.button("📡 View Signals", use_container_width=True, key="cc_signals"):
            _go("📡 Market Signals")
    with qa3:
        if st.button("🎯 CRM Tasks", use_container_width=True, key="cc_crm"):
            _go("🎯 CRM & Tasks")
    with qa4:
        if st.button("📝 Manual Price Entry", use_container_width=True, key="cc_manual"):
            _go("📝 Manual Price Entry")
    with qa5:
        if st.button("📤 Rate Broadcast", use_container_width=True, key="cc_broadcast"):
            _go("📡 Rate Broadcast")

    # Colorful strip below buttons
    st.markdown("""
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:-8px;margin-bottom:12px;">
  <div style="height:6px;border-radius:0 0 8px 8px;background:linear-gradient(90deg,#059669,#10B981);box-shadow:0 3px 10px rgba(5,150,105,0.5);"></div>
  <div style="height:6px;border-radius:0 0 8px 8px;background:linear-gradient(90deg,#4F46E5,#6366F1);box-shadow:0 3px 10px rgba(79,70,229,0.5);"></div>
  <div style="height:6px;border-radius:0 0 8px 8px;background:linear-gradient(90deg,#D97706,#F59E0B);box-shadow:0 3px 10px rgba(217,119,6,0.5);"></div>
  <div style="height:6px;border-radius:0 0 8px 8px;background:linear-gradient(90deg,#7C3AED,#8B5CF6);box-shadow:0 3px 10px rgba(124,58,237,0.5);"></div>
  <div style="height:6px;border-radius:0 0 8px 8px;background:linear-gradient(90deg,#E11D48,#F43F5E);box-shadow:0 3px 10px rgba(225,29,72,0.5);"></div>
</div>
""", unsafe_allow_html=True)

    # ═══ TICKER 3: IMPORT (after market brief) ═══
    if import_prices:
        imp_text = "  &bull;  ".join([f"{n}: ₹{p:,}/MT" for n, p in import_prices])
        _render_ticker("IMPORT", imp_text,
                       bg="#1A1A2E", label_bg="#F59E0B", text_color="#FDE68A", speed=45, label_color="#1A1A2E")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. NEWS FEED — All news displayed directly
    # ═══════════════════════════════════════════════════════════════════════

    # ═══ TICKER 4: INTERNATIONAL (before news) ═══
    _render_ticker("INTERNATIONAL", "  &bull;  ".join(intl_headlines),
                   bg="#0F172A", label_bg="#C9A84C", text_color="#FDE68A", speed=55)

    # ═══ NEWS FEED — Cards in iframe, Modal in PARENT page (centered on screen) ═══
    if news_data:
        news_to_show = [n for n in news_data[:20] if isinstance(n, dict) and n.get("title", n.get("headline", ""))]
    else:
        news_to_show = []

    if news_to_show:
        import html as html_mod
        import json as json_mod

        # Build articles JSON for JS
        articles_js = []
        for article in news_to_show:
            title = article.get("title", article.get("headline", ""))
            source = article.get("source", article.get("publisher", "")) or ""
            date = article.get("published", article.get("date", article.get("timestamp", article.get("date_time", ""))))
            if isinstance(date, str) and len(date) > 10: date = date[:10]
            summary = article.get("summary", article.get("description", article.get("content", ""))) or ""
            url = article.get("url", article.get("link", "")) or ""
            sentiment = article.get("sentiment", "neutral")
            if isinstance(sentiment, str):
                sc = "#10B981" if sentiment.lower() in ("positive", "bullish") else "#EF4444" if sentiment.lower() in ("negative", "bearish") else "#F59E0B"
                sl = sentiment.title()
            else:
                sc, sl = "#94A3B8", "Neutral"
            img = article.get("image_url", article.get("image", article.get("urlToImage", ""))) or ""
            articles_js.append({"t": title, "s": source, "d": str(date) if date else "", "sum": summary, "u": url, "sc": sc, "sl": sl, "img": img})

        articles_json_str = json_mod.dumps(articles_js, ensure_ascii=False).replace("'", "\\'")

        # Build card HTML
        cards_html = ""
        for idx, article in enumerate(news_to_show):
            title_short = html_mod.escape(articles_js[idx]["t"][:100])
            source = html_mod.escape(articles_js[idx]["s"])
            date = html_mod.escape(articles_js[idx]["d"])
            summary_short = articles_js[idx]["sum"]
            summary_short = html_mod.escape(summary_short[:150] + "..." if len(summary_short) > 150 else summary_short)
            sc, sl = articles_js[idx]["sc"], articles_js[idx]["sl"]

            cards_html += f"""
<div class="card" onclick="openNews({idx})">
  <div class="card-top"><span class="src">{source}</span><span class="sent" style="color:{sc};background:{sc}15">{sl}</span></div>
  <div class="card-title">{title_short}</div>
  <div class="card-sum">{summary_short}</div>
  <div class="card-bot"><span class="card-date">{date}</span><span class="card-read">Read More →</span></div>
</div>"""

        # Build JS separately (not inside f-string to avoid JSON brace conflicts)
        js_code = """
var articles=""" + articles_json_str + """;
function openNews(i){
  var card=document.querySelectorAll('.card')[i];
  if(card)card.classList.add('loading');
  setTimeout(function(){
    if(card)card.classList.remove('loading');
    var a=articles[i];if(!a)return;
    var pd=window.parent.document;
    var old=pd.getElementById('pps-news-modal');
    if(old)old.remove();
    var t=a.t.toLowerCase();
    var grad='linear-gradient(135deg,#0F172A 0%,#1E1B4B 50%,#312E81 100%)';
    if(t.indexOf('crude')>-1||t.indexOf('oil')>-1||t.indexOf('opec')>-1)grad='linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)';
    else if(t.indexOf('bitumen')>-1||t.indexOf('road')>-1||t.indexOf('highway')>-1)grad='linear-gradient(135deg,#14532d 0%,#166534 50%,#15803d 100%)';
    else if(t.indexOf('india')>-1||t.indexOf('nhai')>-1||t.indexOf('morth')>-1)grad='linear-gradient(135deg,#7c2d12 0%,#c2410c 50%,#ea580c 100%)';
    else if(t.indexOf('import')>-1||t.indexOf('export')>-1||t.indexOf('trade')>-1)grad='linear-gradient(135deg,#1e3a5f 0%,#2563eb 50%,#3b82f6 100%)';
    var linkHtml=a.u?'<a href="'+a.u+'" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:8px;background:#4F46E5;color:#fff;text-decoration:none;padding:12px 28px;border-radius:10px;font-size:0.88rem;font-weight:700;box-shadow:0 2px 12px rgba(79,70,229,0.3);">\\ud83d\\udd17 Open Original Article</a>':'<span style="color:#94A3B8;font-style:italic;">Source link not available</span>';
    var html='<div id="pps-news-modal" style="position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:999999;display:flex;align-items:flex-start;justify-content:center;padding-top:60px;">'
      +'<div onclick="document.getElementById(\\x27pps-news-modal\\x27).remove()" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(15,23,42,0.7);backdrop-filter:blur(6px);"></div>'
      +'<div style="position:relative;background:#fff;border-radius:20px;width:95%;max-width:720px;max-height:82vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 25px 80px rgba(0,0,0,0.35);animation:ppsZoomIn 0.3s cubic-bezier(0.34,1.56,0.64,1);">'
        +'<button onclick="document.getElementById(\\x27pps-news-modal\\x27).remove()" style="position:absolute;top:14px;right:16px;z-index:10;background:rgba(255,255,255,0.95);border:none;font-size:1.5rem;color:#64748B;cursor:pointer;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 10px rgba(0,0,0,0.2);">&times;</button>'
        +(a.img?'<div style="width:100%;height:240px;border-radius:20px 20px 0 0;overflow:hidden;background:#0F172A;"><img src="'+a.img+'" style="width:100%;height:100%;object-fit:cover;object-position:center 20%;display:block;" onerror="this.parentElement.style.background=\\x27'+grad+'\\x27;this.parentElement.innerHTML=\\x27<div style=display:flex;align-items:center;justify-content:center;height:100%;color:#fff><div style=text-align:center><div style=font-size:2.5rem;margin-bottom:8px>\\ud83d\\udcf0</div><div style=font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;opacity:0.8>'+a.s+'</div></div></div>\\x27"/></div>':'<div style="width:100%;height:160px;background:'+grad+';border-radius:20px 20px 0 0;display:flex;align-items:center;justify-content:center;"><div style="text-align:center;color:#fff;"><div style="font-size:2.5rem;margin-bottom:8px;">\\ud83d\\udcf0</div><div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;opacity:0.8;">'+a.s+'</div></div></div>')
        +'<div style="padding:28px 32px;overflow-y:auto;flex:1;">'
          +'<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;flex-wrap:wrap;"><span style="font-size:0.65rem;color:#6366F1;font-weight:700;background:#EEF2FF;padding:3px 10px;border-radius:6px;">'+a.s+'</span><span style="font-size:0.6rem;font-weight:700;padding:3px 8px;border-radius:4px;color:'+a.sc+';background:'+a.sc+'15;">'+a.sl+'</span><span style="font-size:0.65rem;color:#94A3B8;">'+a.d+'</span></div>'
          +'<h2 style="font-size:1.3rem;font-weight:800;color:#0F172A;line-height:1.45;margin-bottom:18px;">'+a.t+'</h2>'
          +'<div style="height:1px;background:linear-gradient(90deg,#E2E8F0,transparent);margin:16px 0;"></div>'
          +'<p style="font-size:0.95rem;color:#334155;line-height:1.9;">'+(a.sum||'Full article content not available in RSS feed preview. Click the button below to read the complete article on the original website.')+'</p>'
          +'<div style="height:1px;background:linear-gradient(90deg,#E2E8F0,transparent);margin:18px 0;"></div>'
          +'<div>'+linkHtml+'</div>'
        +'</div>'
      +'</div>'
    +'</div>';
    if(!pd.getElementById('pps-modal-style')){
      var st=pd.createElement('style');st.id='pps-modal-style';
      st.textContent='@keyframes ppsZoomIn{from{opacity:0;transform:scale(0.92)}to{opacity:1;transform:scale(1)}}';
      pd.head.appendChild(st);
    }
    var div=pd.createElement('div');
    div.innerHTML=html;
    pd.body.appendChild(div.firstChild);
    var escHandler=function(e){if(e.key==='Escape'){var m=pd.getElementById('pps-news-modal');if(m)m.remove();pd.removeEventListener('keydown',escHandler);}};
    pd.addEventListener('keydown',escHandler);
  },120);
}
"""

        news_html = f"""
<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Inter,-apple-system,Segoe UI,sans-serif;background:transparent}}
.heading{{font-size:0.9rem;font-weight:800;color:#0F172A;margin-bottom:14px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.card{{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:16px;cursor:pointer;transition:all 0.2s;position:relative}}
.card:hover{{box-shadow:0 4px 16px rgba(0,0,0,0.1);border-color:#6366F1;transform:translateY(-2px)}}
.card:active{{transform:scale(0.97)}}
.card-top{{display:flex;justify-content:space-between;margin-bottom:8px}}
.src{{font-size:0.65rem;color:#6366F1;font-weight:700;background:#EEF2FF;padding:2px 8px;border-radius:6px}}
.sent{{font-size:0.6rem;font-weight:700;padding:2px 6px;border-radius:4px}}
.card-title{{font-size:0.82rem;font-weight:700;color:#0F172A;line-height:1.4;margin-bottom:6px}}
.card-sum{{font-size:0.72rem;color:#64748B;line-height:1.5}}
.card-bot{{display:flex;justify-content:space-between;align-items:center;margin-top:10px}}
.card-date{{font-size:0.6rem;color:#94A3B8}}
.card-read{{font-size:0.6rem;color:#6366F1;font-weight:600}}
.card.loading::after{{content:'';position:absolute;top:50%;left:50%;width:24px;height:24px;border:3px solid #6366F1;border-top-color:transparent;border-radius:50%;animation:spin 0.4s linear infinite;transform:translate(-50%,-50%);z-index:2}}
@keyframes spin{{to{{transform:translate(-50%,-50%) rotate(360deg)}}}}
</style></head><body>
<div class="heading">📰 Latest News & Updates</div>
<div class="grid">{cards_html}</div>
<script>{js_code}</script>
</body></html>"""
        n_rows = (len(news_to_show) + 1) // 2
        feed_height = 50 + n_rows * 120
        components.html(news_html, height=feed_height, scrolling=True)
    else:
        st.info("No news data available. News will appear here after data sync.")

    # ═══ TICKER 5: INDIA (after news) ═══
    _render_ticker("INDIA", "  &bull;  ".join(dom_headlines),
                   bg="#14532D", label_bg="#059669", text_color="#BBF7D0", speed=50)

    # ═══════════════════════════════════════════════════════════════════════
    # 6. MARKET SIGNALS SUMMARY
    # ═══════════════════════════════════════════════════════════════════════

    st.markdown("")
    st.markdown('<div style="font-size:0.9rem;font-weight:800;color:#0F172A;margin-bottom:12px;">📡 Market Signals Overview</div>', unsafe_allow_html=True)

    if isinstance(signals_data, dict) and signals_data:
        signal_items = []
        for key, val in signals_data.items():
            if isinstance(val, dict):
                score = val.get("score", val.get("value", 50))
                label = val.get("label", val.get("direction", key))
                signal_items.append({"name": key.replace("_", " ").title(), "score": score, "label": label})
            elif isinstance(val, (int, float)):
                signal_items.append({"name": key.replace("_", " ").title(), "score": val, "label": ""})

        if signal_items:
            # Composite score
            all_scores = []
            for sig in signal_items:
                try: all_scores.append(float(sig.get("score", 50)))
                except: pass
            composite = sum(all_scores) / len(all_scores) if all_scores else 50
            comp_color = "#10B981" if composite > 60 else "#EF4444" if composite < 40 else "#F59E0B"
            comp_label = "BULLISH" if composite > 60 else "BEARISH" if composite < 40 else "NEUTRAL"
            comp_bg = "#F0FDF4" if composite > 60 else "#FEF2F2" if composite < 40 else "#FFFBEB"

            # Master signal banner
            st.markdown(f"""
<div style="background:{comp_bg};border:2px solid {comp_color};border-radius:12px;padding:14px 20px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
<div>
<span style="font-size:0.65rem;color:{comp_color};font-weight:700;text-transform:uppercase;letter-spacing:0.1em;">Composite Signal</span>
<div style="font-size:1.3rem;font-weight:900;color:{comp_color};">{comp_label} &nbsp;{composite:.0f}%</div>
</div>
<div style="width:120px;">
<div style="background:rgba(0,0,0,0.06);border-radius:4px;height:8px;overflow:hidden;">
<div style="background:{comp_color};height:100%;width:{min(max(composite,5),100):.0f}%;border-radius:4px;"></div>
</div>
<div style="display:flex;justify-content:space-between;margin-top:2px;">
<span style="font-size:0.5rem;color:#94A3B8;">0</span>
<span style="font-size:0.5rem;color:#94A3B8;">100</span>
</div>
</div>
</div>""", unsafe_allow_html=True)

            # Individual signals grid
            signals_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;">'
            for sig in signal_items[:12]:
                score = sig.get("score", 50)
                try: score = float(score)
                except: score = 50
                color = "#10B981" if score > 60 else "#EF4444" if score < 40 else "#F59E0B"
                bar_width = min(max(score, 5), 100)
                direction = "Bullish ▲" if score > 60 else "Bearish ▼" if score < 40 else "Neutral ●"
                card_bg = "#F0FDF4" if score > 60 else "#FEF2F2" if score < 40 else "#FFFBEB"
                signals_html += f"""
<div style="background:{card_bg};border:1px solid {color}30;border-radius:10px;padding:12px 14px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
<span style="font-size:0.7rem;font-weight:700;color:#334155;">{sig['name']}</span>
<span style="font-size:0.6rem;font-weight:800;color:{color};background:#fff;padding:1px 6px;border-radius:4px;">{direction}</span>
</div>
<div style="display:flex;align-items:center;gap:8px;">
<div style="flex:1;background:rgba(0,0,0,0.06);border-radius:3px;height:5px;overflow:hidden;">
<div style="background:{color};height:100%;width:{bar_width}%;border-radius:3px;"></div>
</div>
<span style="font-size:0.75rem;font-weight:900;color:{color};min-width:32px;text-align:right;">{score:.0f}%</span>
</div>
</div>"""
            signals_html += '</div>'
            st.markdown(signals_html, unsafe_allow_html=True)
        else:
            st.caption("Signal data format not recognized.")
    else:
        st.caption("Market signals data not available. Run sync to fetch.")

    # ═══ TICKER 6: TENDERS (before alerts) ═══
    if tender_headlines:
        tnd_text = "  &bull;  ".join(tender_headlines)
        _render_ticker("TENDERS", tnd_text,
                       bg="#7F1D1D", label_bg="#EF4444", text_color="#FECACA", speed=60)

    # ═══════════════════════════════════════════════════════════════════════
    # 7. ALERTS + STATS ROW
    # ═══════════════════════════════════════════════════════════════════════

    st.markdown("")
    col_alerts, col_stats = st.columns([3, 2])

    with col_alerts:
        st.markdown('<div style="font-size:0.9rem;font-weight:800;color:#0F172A;margin-bottom:8px;">🔔 Active Alerts</div>', unsafe_allow_html=True)
        display_alerts = active_alerts[:8]
        if display_alerts:
            for al in display_alerts:
                sev = al.get("severity", al.get("priority", "info"))
                title = al.get("title", al.get("message", "Alert"))[:70]
                ts = al.get("created_at", al.get("timestamp", ""))
                if isinstance(ts, str) and len(ts) > 10:
                    ts = ts[:10]
                if sev in ("critical", "P0"):
                    dot, bg, border = "🔴", "#FEF2F2", "#FCA5A5"
                elif sev in ("warning", "P1"):
                    dot, bg, border = "🟡", "#FFFBEB", "#FDE68A"
                else:
                    dot, bg, border = "🟢", "#F0FDF4", "#BBF7D0"

                st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:8px;padding:10px 14px;margin-bottom:5px;display:flex;align-items:center;gap:8px;">
<span style="font-size:0.7rem;">{dot}</span>
<span style="font-size:0.75rem;color:#334155;font-weight:600;flex:1;">{title}</span>
<span style="font-size:0.58rem;color:#94A3B8;white-space:nowrap;">{ts}</span>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;padding:16px;text-align:center;font-size:0.82rem;color:#059669;font-weight:600;">✅ All Clear — No active alerts</div>', unsafe_allow_html=True)

        # Quick action row under alerts
        st.markdown("")
        a1, a2 = st.columns(2)
        with a1:
            if st.button("🚨 View All Alerts", use_container_width=True, key="cc_alerts"):
                _go("🚨 Alert Center")
        with a2:
            if st.button("🔄 Run Data Sync", use_container_width=True, key="cc_sync"):
                _go("🎛️ System Control Center")

    with col_stats:
        st.markdown('<div style="font-size:0.9rem;font-weight:800;color:#0F172A;margin-bottom:8px;">📊 Quick Stats</div>', unsafe_allow_html=True)

        stats = [
            # Empty-state aware: "—" for data we don't yet have (not a misleading zero)
            ("🏭", "Suppliers",
                db_stats.get('total_suppliers') or "—",
                "#6366F1"),
            ("👥", "Customers",
                db_stats.get('total_customers') or "—",
                "#8B5CF6"),
            ("📋", "Tasks Today", tasks_today, "#F59E0B" if tasks_overdue > 0 else "#10B981"),
            ("⚠️", "Overdue", tasks_overdue, "#EF4444" if tasks_overdue > 0 else "#10B981"),
            ("💼", "Active Deals",
                db_stats.get('total_deals') or "—",
                "#0EA5E9"),
            ("🔔", "Open Alerts", len(active_alerts), "#EF4444" if len(active_alerts) > 5 else "#10B981"),
        ]

        # 2x3 grid for stats
        stats_html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">'
        for icon, label, value, color in stats:
            stats_html += f"""
<div style="background:#fff;border:1px solid #E2E8F0;border-radius:10px;padding:10px 12px;display:flex;align-items:center;gap:10px;">
<span style="font-size:1.1rem;">{icon}</span>
<div>
<div style="font-size:1.1rem;font-weight:900;color:{color};">{value}</div>
<div style="font-size:0.58rem;color:#94A3B8;font-weight:600;text-transform:uppercase;">{label}</div>
</div>
</div>"""
        stats_html += '</div>'
        st.markdown(stats_html, unsafe_allow_html=True)

    # ── Footer with quick nav + sync status ──
    # Get last sync time
    sync_logs = _load_json("sync_logs.json", [])
    last_sync = "Never"
    if isinstance(sync_logs, list) and sync_logs:
        try: last_sync = sync_logs[-1].get("timestamp", sync_logs[-1].get("date", "Unknown"))[:16]
        except: pass
    elif isinstance(sync_logs, dict):
        last_sync = sync_logs.get("last_sync", sync_logs.get("timestamp", "Unknown"))
        if isinstance(last_sync, str) and len(last_sync) > 16: last_sync = last_sync[:16]

    st.markdown(f"""
<div style="margin-top:24px;padding:16px 0 8px;border-top:1px solid #E2E8F0;">
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
<span style="font-size:0.6rem;color:#94A3B8;">PPS Anantams Corporation Pvt Ltd &bull; Vadodara, Gujarat &bull; Command Center v6.0</span>
<span style="font-size:0.58rem;color:#94A3B8;">Last Sync: {last_sync} &bull; Page loaded: {now.strftime('%H:%M:%S IST')}</span>
</div>
</div>""", unsafe_allow_html=True)

    # ── Smart navigation: Continue + Next Steps ──
    try:
        from navigation_engine import render_continue_widget, render_next_step_cards
        render_continue_widget()
        render_next_step_cards("🎯 Command Center")
        st.session_state["_ns_rendered_inline"] = True
    except Exception:
        pass
