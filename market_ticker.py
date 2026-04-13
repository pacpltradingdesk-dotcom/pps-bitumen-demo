"""
market_ticker.py -- 4-Row Market Data Scrolling Ticker
======================================================
Renders four CSS-animated ticker rows below the news ticker:
  Row 1: Tenders   -- NHAI / Infrastructure / Highway tender headlines
  Row 2: Markets   -- Brent, WTI, USD/INR, Gold, Nifty, NG, FO, Bitumen CFR
  Row 3: Refinery  -- IOCL/BPCL/HPCL VG-30 bitumen prices (INR/MT)
  Row 4: Import    -- Drum & bulk import port prices (INR/MT)

Speed: 600s animation (matching news_ticker.py).
Pauses on hover. Price items color-coded green/red/yellow.

Usage:
    from market_ticker import render_market_ticker
    render_market_ticker()
"""

from __future__ import annotations

import re
import streamlit as st
import streamlit.components.v1 as components

# ── Tender keyword filter (word-boundary matching to avoid false positives) ─

_TENDER_KW_PATTERNS = [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) for kw in [
    "tender", "awarded", "highway", "road project", "nhai",
    "morth", "pmgsy", "expressway", "bitumen demand",
    "epc contract", "ham project", "work order", "infrastructure",
    "resurfacing", "road contract", "letter of award",
    "construction project", "road construction", "highway project",
    "bitumen", "asphalt", "road work",
]]

# ── Demo fallback data ─────────────────────────────────────────────────────

_DEMO_TENDERS = [
    ("NHAI awards Rs 14,200 Cr road projects across 6 states in Q4",
     "https://pib.gov.in"),
    ("MoRTH targets 12,000 km highway construction in FY 2025-26",
     "https://economictimes.com"),
    ("PMGSY Phase IV connects 18,000 villages -- bitumen demand at peak",
     "https://pib.gov.in"),
    ("Budget 2025-26: Rs 2.78 lakh Cr for road + infrastructure sector",
     "https://business-standard.com"),
    ("NHAI receives 23 bids for 2,400-km highway package in UP, Bihar",
     "https://economictimes.com"),
    ("Rajasthan PWD floats tender for 420 km state highway resurfacing",
     "https://pib.gov.in"),
    ("India bitumen demand forecast: 8.2 MMT in FY 2025-26 -- PPAC",
     "https://ppac.gov.in"),
    ("Gujarat roads dept opens Rs 1,800 Cr tender for 6-lane expressway",
     "https://pib.gov.in"),
    ("NHAI: 65,000 km National Highways awarded under Bharatmala Phase-I",
     "https://economictimes.com"),
]

_DEMO_GLOBAL_MARKETS = [
    {"label": "Brent Crude",  "value": "₹ 75.50",  "change": "+0.80%", "color": "#16a34a", "icon": "\U0001f6e2\ufe0f"},
    {"label": "WTI Crude",    "value": "₹ 71.50",  "change": "-0.40%", "color": "#dc2626", "icon": "\U0001f6e2\ufe0f"},
    {"label": "USD/INR",      "value": "\u20b986.80", "change": "+0.15%", "color": "#16a34a", "icon": "\U0001f4b5"},
    {"label": "Gold",         "value": "₹ 2,650",  "change": "+0.22%", "color": "#16a34a", "icon": "\U0001f947"},
    {"label": "Nifty 50",     "value": "22,450",  "change": "+0.35%", "color": "#16a34a", "icon": "\U0001f4c8"},
    {"label": "Natural Gas",  "value": "₹ 2.85",   "change": "-1.20%", "color": "#dc2626", "icon": "\U0001f525"},
    {"label": "Fuel Oil",     "value": "₹ 2.42",   "change": "+0.10%", "color": "#c9a84c", "icon": "\u26fd"},
    {"label": "Bitumen CFR",  "value": "₹ 310",    "change": "",       "color": "#c9a84c", "icon": "\U0001f3ed"},
]

_DEMO_REFINERY_PRICES = [
    {"name": "IOCL Koyali",          "grade": "VG-30", "price_inr": 42000, "formatted": "\u20b942,000/MT"},
    {"name": "IOCL Mathura",         "grade": "VG-30", "price_inr": 42500, "formatted": "\u20b942,500/MT"},
    {"name": "IOCL Haldia",          "grade": "VG-30", "price_inr": 41800, "formatted": "\u20b941,800/MT"},
    {"name": "IOCL Barauni",         "grade": "VG-30", "price_inr": 41500, "formatted": "\u20b941,500/MT"},
    {"name": "IOCL Panipat",         "grade": "VG-30", "price_inr": 42200, "formatted": "\u20b942,200/MT"},
    {"name": "BPCL Mumbai",          "grade": "VG-30", "price_inr": 43000, "formatted": "\u20b943,000/MT"},
    {"name": "BPCL Kochi",           "grade": "VG-30", "price_inr": 42800, "formatted": "\u20b942,800/MT"},
    {"name": "HPCL Mumbai",          "grade": "VG-30", "price_inr": 42900, "formatted": "\u20b942,900/MT"},
    {"name": "HPCL Visakhapatnam",   "grade": "VG-30", "price_inr": 41600, "formatted": "\u20b941,600/MT"},
    {"name": "CPCL Chennai",         "grade": "VG-30", "price_inr": 42100, "formatted": "\u20b942,100/MT"},
    {"name": "MRPL Mangalore",       "grade": "VG-30", "price_inr": 41900, "formatted": "\u20b941,900/MT"},
]

_DEMO_IMPORT_PRICES = [
    {"name": "Drum Mumbai VG30",   "price_inr": 37000, "formatted": "\u20b937,000/MT"},
    {"name": "Drum Kandla VG30",   "price_inr": 35500, "formatted": "\u20b935,500/MT"},
    {"name": "Drum Mumbai VG10",   "price_inr": 38000, "formatted": "\u20b938,000/MT"},
    {"name": "Drum Kandla VG10",   "price_inr": 36500, "formatted": "\u20b936,500/MT"},
    {"name": "Kandla Bulk Import", "price_inr": 38000, "formatted": "\u20b938,000/MT"},
    {"name": "Mundra Bulk Import", "price_inr": 37800, "formatted": "\u20b937,800/MT"},
    {"name": "JNPT Bulk Import",   "price_inr": 39800, "formatted": "\u20b939,800/MT"},
    {"name": "Mangalore Import",   "price_inr": 38500, "formatted": "\u20b938,500/MT"},
]


# ── Indian comma formatter ─────────────────────────────────────────────────

def _fmt_inr(val: int) -> str:
    """Format integer as INR with Indian comma grouping: 1,23,456."""
    s = str(abs(val))
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while rest:
        parts.append(rest[-2:])
        rest = rest[:-2]
    parts.reverse()
    return ",".join(parts) + "," + last3


# ── Data fetchers ──────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def _fetch_tender_news(max_count: int = 15) -> list[tuple[str, str]]:
    """Fetch tender/infrastructure headlines. Returns [(headline, url)]."""
    items: list[tuple[str, str]] = []

    # Source 1: news_engine domestic articles filtered for tender keywords
    try:
        from news_engine import get_articles
        articles = get_articles(region="Domestic", max_age_hours=72, impact_min=0)
        if articles:
            for a in articles:
                text = a.get("headline", "") + " " + a.get("summary", "")
                if any(pat.search(text) for pat in _TENDER_KW_PATTERNS):
                    items.append((
                        a.get("headline", "")[:120],
                        a.get("source_url", "#"),
                    ))
    except Exception:
        pass

    # Source 2: NHAI tender cache from api_hub_engine
    try:
        from api_hub_engine import HubCache
        nhai = HubCache.get("nhai_tenders")
        if nhai and isinstance(nhai, dict):
            summary_text = nhai.get("summary", "")
            if summary_text and len(items) < 5:
                items.append((summary_text[:120], "https://nhai.gov.in"))
    except Exception:
        pass

    if not items:
        return list(_DEMO_TENDERS)
    return items[:max_count]


@st.cache_data(ttl=300)
def _fetch_global_markets() -> list[dict]:
    """Fetch global market prices. Returns list of {label, value, change, color, icon}."""
    items: list[dict] = []

    try:
        from api_manager import fetch_api_data
    except ImportError:
        return list(_DEMO_GLOBAL_MARKETS)

    TICKERS = [
        ("brent",       "Brent Crude",  "$",       "\U0001f6e2\ufe0f"),
        ("wti",         "WTI Crude",    "$",       "\U0001f6e2\ufe0f"),
        ("usdinr",      "USD/INR",      "\u20b9",  "\U0001f4b5"),
        ("gold_xau",    "Gold",         "$",       "\U0001f947"),
        ("nifty50",     "Nifty 50",     "",        "\U0001f4c8"),
        ("natural_gas", "Natural Gas",  "$",       "\U0001f525"),
        ("fuel_oil",    "Fuel Oil",     "$",       "\u26fd"),
    ]

    brent_usd = None
    for widget_id, label, prefix, icon in TICKERS:
        try:
            data = fetch_api_data(widget_id)
            if data and "current" in data:
                curr = float(data["current"])
                hist = float(data.get("history_7d", curr))
                pct = ((curr - hist) / hist * 100) if hist else 0.0

                if widget_id == "brent":
                    brent_usd = curr

                # Color coding
                if pct > 0.05:
                    color = "#16a34a"   # green
                elif pct < -0.05:
                    color = "#dc2626"   # red
                else:
                    color = "#c9a84c"   # gold/yellow

                # Format value
                if widget_id == "nifty50":
                    val_str = f"{prefix}{curr:,.0f}"
                else:
                    val_str = f"{prefix}{curr:,.2f}"

                items.append({
                    "label": label,
                    "value": val_str,
                    "change": f"{pct:+.2f}%",
                    "color": color,
                    "icon": icon,
                })
            else:
                items.append({"label": label, "value": "N/A", "change": "0.00%",
                              "color": "#94a3b8", "icon": icon})
        except Exception:
            items.append({"label": label, "value": "N/A", "change": "0.00%",
                          "color": "#94a3b8", "icon": icon})

    # Derived: Bitumen CFR India (Brent * 6.29 bbl-to-MT * 0.65 discount)
    if brent_usd:
        bitumen_cfr = round(brent_usd * 6.29 * 0.65, 2)
        items.append({
            "label": "Bitumen CFR",
            "value": f"${bitumen_cfr:,.0f}/MT",
            "change": "",
            "color": "#c9a84c",
            "icon": "\U0001f3ed",
        })
    else:
        items.append({"label": "Bitumen CFR", "value": "~₹ 310/MT", "change": "",
                      "color": "#94a3b8", "icon": "\U0001f3ed"})

    if all(i["value"] == "N/A" for i in items):
        return list(_DEMO_GLOBAL_MARKETS)
    return items


@st.cache_data(ttl=21600)
def _fetch_refinery_prices() -> list[dict]:
    """Fetch PSU refinery VG-30 prices. Returns [{name, grade, price_inr, formatted}]."""
    try:
        from feasibility_engine import get_live_prices
        prices = get_live_prices()
        items: list[dict] = []
        PSU_KEYS = [
            "IOCL Koyali", "IOCL Mathura", "IOCL Haldia", "IOCL Barauni",
            "IOCL Panipat", "BPCL Mumbai", "BPCL Kochi", "HPCL Mumbai",
            "HPCL Visakhapatnam", "CPCL Chennai", "MRPL Mangalore",
        ]
        for key in PSU_KEYS:
            if key in prices:
                val = int(prices[key])
                items.append({
                    "name": key,
                    "grade": "VG-30",
                    "price_inr": val,
                    "formatted": f"\u20b9{_fmt_inr(val)}/MT",
                })
        return items if items else list(_DEMO_REFINERY_PRICES)
    except Exception:
        return list(_DEMO_REFINERY_PRICES)


@st.cache_data(ttl=10800)
def _fetch_import_prices() -> list[dict]:
    """Fetch drum & import terminal prices. Returns [{name, price_inr, formatted}]."""
    try:
        from feasibility_engine import get_live_prices
        prices = get_live_prices()
        items: list[dict] = []
        IMPORT_KEYS = [
            ("DRUM_MUMBAI_VG30",       "Drum Mumbai VG30"),
            ("DRUM_KANDLA_VG30",       "Drum Kandla VG30"),
            ("DRUM_MUMBAI_VG10",       "Drum Mumbai VG10"),
            ("DRUM_KANDLA_VG10",       "Drum Kandla VG10"),
            ("Kandla Port Import",     "Kandla Bulk Import"),
            ("Mundra Port Import",     "Mundra Bulk Import"),
            ("JNPT Import Terminal",   "JNPT Bulk Import"),
            ("Mangalore Port Import",  "Mangalore Import"),
        ]
        for key, label in IMPORT_KEYS:
            if key in prices:
                val = int(prices[key])
                items.append({
                    "name": label,
                    "price_inr": val,
                    "formatted": f"\u20b9{_fmt_inr(val)}/MT",
                })
        return items if items else list(_DEMO_IMPORT_PRICES)
    except Exception:
        return list(_DEMO_IMPORT_PRICES)


# ── HTML item builders ─────────────────────────────────────────────────────

def _tender_items_to_html(items: list[tuple[str, str]]) -> str:
    """Build scrolling HTML for tender headlines (clickable links)."""
    parts = []
    for headline, url in items:
        safe_h = headline.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        parts.append(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#1e3a5f;text-decoration:none;transition:color 0.2s;" '
            f'onmouseover="this.style.color=\'#c9a84c\';this.style.textDecoration=\'underline\';" '
            f'onmouseout="this.style.color=\'#1e3a5f\';this.style.textDecoration=\'none\';">'
            f'{safe_h}</a>'
            f'<span style="color:#c9a84c;margin:0 18px;font-weight:700;">\u25c6</span>'
        )
    return "".join(parts)


def _market_items_to_html(items: list[dict]) -> str:
    """Build scrolling HTML for market prices with color-coded changes."""
    parts = []
    for item in items:
        change_html = ""
        if item.get("change"):
            change_html = (
                f'<span style="color:{item["color"]};font-weight:600;margin-left:4px;">'
                f'{item["change"]}</span>'
            )
        parts.append(
            f'<span style="color:#1e3a5f;white-space:nowrap;">'
            f'{item.get("icon","")} <b>{item["label"]}:</b> {item["value"]}'
            f'{change_html}</span>'
            f'<span style="color:#c9a84c;margin:0 14px;font-weight:700;">\u25c6</span>'
        )
    return "".join(parts)


def _price_items_to_html(items: list[dict], text_color: str) -> str:
    """Build scrolling HTML for price rows (refinery / import)."""
    parts = []
    for item in items:
        name = item.get("name", "")
        grade = item.get("grade", "")
        formatted = item.get("formatted", "")
        label = f"{name} {grade}".strip() if grade else name
        parts.append(
            f'<span style="color:{text_color};white-space:nowrap;">'
            f'{label} \u2014 <b>{formatted}</b></span>'
            f'<span style="color:#c9a84c;margin:0 14px;font-weight:700;">\u25c6</span>'
        )
    return "".join(parts)


# ── Main HTML + CSS builder ────────────────────────────────────────────────

def _build_market_ticker_html(
    tender_html: str,
    market_html: str,
    refinery_html: str,
    import_html: str,
    speed: int = 600,
) -> str:
    """Build the full 4-row ticker HTML with CSS animations. Speed in seconds."""

    # Duplicate content for seamless infinite loop
    tender_loop   = tender_html * 2
    market_loop   = market_html * 2
    refinery_loop = refinery_html * 2
    import_loop   = import_html * 2

    return f"""
<style>
  .pps-mkt-wrap {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    overflow: hidden;
    border-bottom: 1px solid #e8dcc8;
    user-select: none;
  }}
  .pps-mkt-row {{
    display: flex;
    align-items: center;
    height: 32px;
    overflow: hidden;
    border-bottom: 1px solid #f0ebe1;
  }}
  .pps-mkt-row:last-child {{
    border-bottom: none;
  }}
  .pps-mkt-badge {{
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 0 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    white-space: nowrap;
    z-index: 1;
    color: #ffffff;
    min-width: 110px;
  }}
  .pps-mkt-badge-tender   {{ background: #1e3a5f; border-right: 1px solid #163050; }}
  .pps-mkt-badge-market   {{ background: #c9a84c; border-right: 1px solid #b8964a; }}
  .pps-mkt-badge-refinery {{ background: #2d6a4f; border-right: 1px solid #255a42; }}
  .pps-mkt-badge-import   {{ background: #ea580c; border-right: 1px solid #c9480a; }}

  .pps-mkt-scroll-wrap {{
    flex: 1;
    overflow: hidden;
    height: 100%;
    display: flex;
    align-items: center;
    position: relative;
  }}
  /* Fade edge gradient */
  .pps-mkt-scroll-wrap::after {{
    content: '';
    position: absolute;
    right: 0; top: 0;
    width: 40px; height: 100%;
    z-index: 2;
    pointer-events: none;
  }}
  .pps-mkt-sw-tender::after   {{ background: linear-gradient(to right, transparent, #f0f4f8); }}
  .pps-mkt-sw-market::after   {{ background: linear-gradient(to right, transparent, #faf0e0); }}
  .pps-mkt-sw-refinery::after {{ background: linear-gradient(to right, transparent, #f0faf4); }}
  .pps-mkt-sw-import::after   {{ background: linear-gradient(to right, transparent, #fdf6f0); }}

  .pps-mkt-text {{
    display: inline-block;
    white-space: nowrap;
    font-size: 12.5px;
    line-height: 32px;
    padding-left: 100%;
  }}
  .pps-mkt-text-tender   {{ animation: pps-mkt-tender-scroll   {speed}s linear infinite; color: #1e3a5f; }}
  .pps-mkt-text-market   {{ animation: pps-mkt-market-scroll   {speed}s linear infinite; color: #1e3a5f; }}
  .pps-mkt-text-refinery {{ animation: pps-mkt-refinery-scroll {speed}s linear infinite; color: #2d6a4f; }}
  .pps-mkt-text-import   {{ animation: pps-mkt-import-scroll   {speed}s linear infinite; color: #9a3412; }}

  @keyframes pps-mkt-tender-scroll   {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
  @keyframes pps-mkt-market-scroll   {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
  @keyframes pps-mkt-refinery-scroll {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
  @keyframes pps-mkt-import-scroll   {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}

  /* Hover pauses per row */
  .pps-mkt-row:hover .pps-mkt-text {{
    animation-play-state: paused;
  }}

  /* Row backgrounds */
  .pps-mkt-row-tender   {{ background: #f0f4f8; }}
  .pps-mkt-row-market   {{ background: #faf0e0; }}
  .pps-mkt-row-refinery {{ background: #f0faf4; }}
  .pps-mkt-row-import   {{ background: #fdf6f0; }}

  /* Responsive */
  @media (max-width: 768px) {{
    .pps-mkt-badge {{ min-width: 60px; padding: 0 6px; font-size: 9px; }}
    .pps-mkt-text  {{ font-size: 11px; }}
    .pps-mkt-row   {{ height: 28px; }}
  }}
</style>

<div class="pps-mkt-wrap">
  <!-- Row 1: Tenders -->
  <div class="pps-mkt-row pps-mkt-row-tender" title="Hover to pause -- click headline to open source">
    <div class="pps-mkt-badge pps-mkt-badge-tender">\U0001f3d7\ufe0f&nbsp; Tenders</div>
    <div class="pps-mkt-scroll-wrap pps-mkt-sw-tender">
      <span class="pps-mkt-text pps-mkt-text-tender">
        {tender_loop}
      </span>
    </div>
  </div>
  <!-- Row 2: Global Markets -->
  <div class="pps-mkt-row pps-mkt-row-market" title="Hover to pause -- live global commodity & index prices">
    <div class="pps-mkt-badge pps-mkt-badge-market">\U0001f4c8&nbsp; Markets</div>
    <div class="pps-mkt-scroll-wrap pps-mkt-sw-market">
      <span class="pps-mkt-text pps-mkt-text-market">
        {market_loop}
      </span>
    </div>
  </div>
  <!-- Row 3: Refinery Prices -->
  <div class="pps-mkt-row pps-mkt-row-refinery" title="Hover to pause -- PSU refinery bitumen VG-30 prices">
    <div class="pps-mkt-badge pps-mkt-badge-refinery">\U0001f3ed&nbsp; Refinery</div>
    <div class="pps-mkt-scroll-wrap pps-mkt-sw-refinery">
      <span class="pps-mkt-text pps-mkt-text-refinery">
        {refinery_loop}
      </span>
    </div>
  </div>
  <!-- Row 4: Import / Drum Prices -->
  <div class="pps-mkt-row pps-mkt-row-import" title="Hover to pause -- drum & bulk import bitumen prices">
    <div class="pps-mkt-badge pps-mkt-badge-import">\U0001f6a2&nbsp; Import</div>
    <div class="pps-mkt-scroll-wrap pps-mkt-sw-import">
      <span class="pps-mkt-text pps-mkt-text-import">
        {import_loop}
      </span>
    </div>
  </div>
</div>
"""


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def render_market_ticker():
    """
    Render the 4-row market data ticker.
    Call once, near the top of the main dashboard content area.

    Rows:
      1. Tenders   (TTL 30 min)  -- NHAI / infrastructure headlines
      2. Markets   (TTL 5 min)   -- Brent, WTI, USD/INR, Gold, Nifty, NG, FO, Bitumen CFR
      3. Refinery  (TTL 6 hr)    -- IOCL/BPCL/HPCL VG-30 prices
      4. Import    (TTL 3 hr)    -- Drum & bulk import prices
    """
    # Auto-refresh stale caches (safety net for dead background schedulers)
    try:
        from freshness_guard import ensure_fresh
        ensure_fresh(show_spinner=False)
    except Exception:
        pass

    tenders  = _fetch_tender_news()
    markets  = _fetch_global_markets()
    refinery = _fetch_refinery_prices()
    imports  = _fetch_import_prices()

    _speed = st.session_state.get("_ticker_speed", 600)
    html = _build_market_ticker_html(
        _tender_items_to_html(tenders),
        _market_items_to_html(markets),
        _price_items_to_html(refinery, "#2d6a4f"),
        _price_items_to_html(imports, "#9a3412"),
        speed=_speed,
    )

    # 4 rows x 32px + 2px border = 130px
    components.html(html, height=130, scrolling=False)
