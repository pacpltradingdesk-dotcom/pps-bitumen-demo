"""
news_ticker.py — Dual-Stream News Scrolling Ticker
====================================================
Renders two smooth CSS-animated ticker rows at the top of the dashboard:
  Row 1: 🌍 International  — Crude / Forex / Logistics headlines
  Row 2: 🇮🇳 Domestic India — NHAI / MoRTH / PMGSY / Roads headlines

Speed: 600s animation (10% of news_dashboard.py's 60s baseline).
Each headline is a clickable anchor that opens the source in a new tab.
Corporate Vastu light theme: linen/mint rows, navy/green text.

Usage:
    from news_ticker import render_news_ticker
    render_news_ticker()
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

# ── Demo fallback headlines (used when news_engine has no data) ──────────────

_DEMO_INTERNATIONAL = [
    ("Brent Crude rises 0.8% on OPEC supply cut speculation",         "https://oilprice.com"),
    ("USD/INR steady at 86.9 ahead of US Fed minutes",                 "https://reuters.com"),
    ("International bitumen FOB prices up ₹ 4/MT in Singapore market",  "https://oilprice.com"),
    ("Middle East tensions push shipping freight rates higher",         "https://cnbc.com"),
    ("WTI crude trims gains as US inventory data beats estimates",      "https://marketwatch.com"),
    ("IMF revises India growth forecast to 6.8% for FY 2025-26",       "https://reuters.com"),
    ("OPEC+ extends voluntary cuts through Q2 2026",                   "https://oilprice.com"),
]

_DEMO_DOMESTIC = [
    ("NHAI awards ₹ 14,200 Cr road projects across 6 states in Q4",       "https://pib.gov.in"),
    ("MoRTH targets 12,000 km highway construction in FY 2025-26",        "https://economictimes.com"),
    ("PMGSY Phase IV connects 18,000 villages — bitumen demand at peak",   "https://pib.gov.in"),
    ("Budget 2025-26: ₹ 2.78 lakh Cr for road + infrastructure sector",   "https://business-standard.com"),
    ("IOCL VG-30 bitumen: next revision expected 1-April-2026",           "https://pib.gov.in"),
    ("NHAI receives 23 bids for 2,400-km highway package in UP, Bihar",   "https://economictimes.com"),
    ("India bitumen demand forecast: 8.2 MMT in FY 2025-26 — PPAC",       "https://ppac.gov.in"),
]


# ── Load live articles from news_engine ─────────────────────────────────────

def _fetch_headlines(region: str, max_count: int = 20) -> list[tuple[str, str]]:
    """Returns list of (headline, url) tuples for the given region."""
    try:
        from news_engine import get_articles
        articles = get_articles(
            region=region,
            max_age_hours=72,
            impact_min=0,
        )
        if articles:
            return [
                (a.get("headline", "")[:120], a.get("source_url", "#"))
                for a in articles[:max_count]
                if a.get("headline")
            ]
    except Exception:
        pass
    # Fallback
    if region == "International":
        return _DEMO_INTERNATIONAL
    return _DEMO_DOMESTIC


# ── HTML ticker builder ───────────────────────────────────────────────────────

def _build_ticker_html(intl_items: list[tuple], dom_items: list[tuple], speed: int = 600) -> str:
    """Build full HTML + CSS + JS ticker. Speed is animation duration in seconds."""

    def items_to_html(items: list[tuple], link_color: str) -> str:
        parts = []
        for headline, url in items:
            safe_h = headline.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            parts.append(
                f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="color:{link_color};text-decoration:none;transition:color 0.2s;" '
                f'onmouseover="this.style.color=\'#c9a84c\';this.style.textDecoration=\'underline\';" '
                f'onmouseout="this.style.color=\'{link_color}\';this.style.textDecoration=\'none\';">'
                f'{safe_h}</a>'
                f'<span style="color:#c9a84c;margin:0 18px;font-weight:700;">◆</span>'
            )
        return "".join(parts)

    intl_html = items_to_html(intl_items, "#1e3a5f")
    dom_html  = items_to_html(dom_items,  "#2d6a4f")

    # Duplicate content for seamless loop
    intl_html_loop = intl_html * 2
    dom_html_loop  = dom_html  * 2

    return f"""
<style>
  .pps-ticker-wrap {{
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    overflow: hidden;
    border-bottom: 1px solid #e8dcc8;
    user-select: none;
  }}
  .pps-ticker-row {{
    display: flex;
    align-items: center;
    height: 32px;
    overflow: hidden;
    border-bottom: 1px solid #f0ebe1;
  }}
  .pps-ticker-row:last-child {{
    border-bottom: none;
  }}
  .pps-ticker-badge {{
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
  }}
  .pps-ticker-intl-badge {{
    background: #c9a84c;
    color: #ffffff;
    border-right: 1px solid #b8964a;
    min-width: 110px;
  }}
  .pps-ticker-dom-badge {{
    background: #2d6a4f;
    color: #ffffff;
    border-right: 1px solid #255a42;
    min-width: 110px;
  }}
  .pps-ticker-scroll-wrap {{
    flex: 1;
    overflow: hidden;
    height: 100%;
    display: flex;
    align-items: center;
    position: relative;
  }}
  /* Fade edges */
  .pps-ticker-scroll-wrap::after {{
    content: '';
    position: absolute;
    right: 0;
    top: 0;
    width: 40px;
    height: 100%;
    z-index: 2;
    pointer-events: none;
  }}
  .pps-intl-scroll-wrap::after {{
    background: linear-gradient(to right, transparent, #faf0e0);
  }}
  .pps-dom-scroll-wrap::after {{
    background: linear-gradient(to right, transparent, #f0faf4);
  }}
  .pps-ticker-text {{
    display: inline-block;
    white-space: nowrap;
    font-size: 12.5px;
    line-height: 32px;
    padding-left: 100%;
  }}
  .pps-ticker-intl-text {{
    animation: pps-intl-scroll {speed}s linear infinite;
    color: #1e3a5f;
  }}
  .pps-ticker-dom-text {{
    animation: pps-dom-scroll {speed}s linear infinite;
    color: #2d6a4f;
  }}
  @keyframes pps-intl-scroll {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
  }}
  @keyframes pps-dom-scroll {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
  }}
  .pps-ticker-row:hover .pps-ticker-text {{
    animation-play-state: paused;
  }}
  /* Background colours per row */
  .pps-row-intl {{ background: #faf0e0; }}
  .pps-row-dom  {{ background: #f0faf4; }}

  @media (max-width: 768px) {{
    .pps-ticker-badge {{ min-width: 60px; padding: 0 6px; font-size: 9px; }}
    .pps-ticker-text  {{ font-size: 11px; }}
    .pps-ticker-row   {{ height: 28px; }}
  }}
</style>

<div class="pps-ticker-wrap">
  <!-- International Row -->
  <div class="pps-ticker-row pps-row-intl" title="Hover to pause — click headline to open article">
    <div class="pps-ticker-badge pps-ticker-intl-badge">🌍&nbsp; International</div>
    <div class="pps-ticker-scroll-wrap pps-intl-scroll-wrap">
      <span class="pps-ticker-text pps-ticker-intl-text">
        {intl_html_loop}
      </span>
    </div>
  </div>
  <!-- Domestic Row -->
  <div class="pps-ticker-row pps-row-dom" title="Hover to pause — click headline to open article">
    <div class="pps-ticker-badge pps-ticker-dom-badge">🇮🇳&nbsp; India</div>
    <div class="pps-ticker-scroll-wrap pps-dom-scroll-wrap">
      <span class="pps-ticker-text pps-ticker-dom-text">
        {dom_html_loop}
      </span>
    </div>
  </div>
</div>
"""


# ── Public API ────────────────────────────────────────────────────────────────

def render_news_ticker(max_intl: int = 20, max_dom: int = 20):
    """
    Render the dual-stream news ticker.
    International row: crude/forex/logistics
    Domestic row:      NHAI/MoRTH/PMGSY/roads

    Speed: 600s per full scroll (10% of normal 60s speed = slow, readable).
    Pauses on hover. Each headline clicks through to source.

    Call this once, near the top of the main content area, before the header.
    """
    intl_items = _fetch_headlines("International", max_intl)
    dom_items  = _fetch_headlines("Domestic",      max_dom)

    _speed = st.session_state.get("_ticker_speed", 600)
    html = _build_ticker_html(intl_items, dom_items, speed=_speed)

    # Height: 2 rows × 32px + 2px border = 66px
    components.html(html, height=66, scrolling=False)
