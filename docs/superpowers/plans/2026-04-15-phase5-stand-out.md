# Phase 5 — Stand-Out UX

**Date:** 2026-04-15
**Branch:** `feature/phase-5-stand-out`

## Goal

Make the strong features instantly recognisable. Log in → 5 seconds →
"oh yeh valuable hai". Right now the functionality is there but
nothing visually dominates.

## 5 Moves

### Move 1 — Hero "Today's Call" card
Big card at top of Command Center:
> **TODAY'S CALL: BUY 50MT Kandla VG30**
> Confidence 82% · Expected +₹4.2L · Window: 48 hrs

Sourced from `business_advisor_engine.get_buy_advisory()` +
`market_intelligence_engine.get_composite_signal()`. Fallback: if no
clear call, show "HOLD — market neutral at 54".

### Move 2 — Power Stats ribbon
Thin 1-row strip right under top bar, visible on EVERY page:
> 📊 25,667 contacts · 56K DB rows · VG30 ₹50,327 · 🟢 BULLISH 78 · ⚠️ 4 alerts

Data sources:
- contacts: `sqlite SELECT COUNT(*) FROM contacts`
- db rows: sum of contacts + customers + customer_profiles + suppliers
- VG30 forecast: `hub_cache.json.markets.bitumen.vg30_mumbai`
- signal: `market_intelligence_engine.get_latest_composite()`
- alerts: `alert_system.count_active()`

Component: `components/power_stats_ribbon.py`, mounted in `top_bar.py`
after the main nav row.

### Move 3 — Feature pills
Small colored pills next to starred sidebar items:
- Price Prediction → `⚡ AI`
- Market Signals → `🔴 LIVE`
- Telegram Analyzer → `24K REACH` (or rename to show power)
- Negotiation → `⚡ AI`
- Director Briefing → `08:30 AM`

Implement in `subtab_bar.py` via an optional `pill` key per tab in
`nav_config.py`.

### Move 4 — Empty-state CTAs
Replace "—" and "0" displays with motivating actions:
- "0 suppliers" → "0 suppliers — Import 63 from vendor list [ Import ]"
- "0 active deals" → "No deals yet — Create first quote [ Open Calculator ]"
- "0 opportunities" → "Scan market for fresh opportunities [ Scan Now ]"

Focus: Command Center KPI cards.

### Move 5 — Daily Flow shortcut row
Row of 5 large buttons on Command Center, just below the hero card:
> [ 📝 Quote ]  [ 📋 Brief ]  [ 📢 Broadcast ]  [ 🔮 Predict ]  [ 🤝 Negotiate ]

Each button navigates to the canonical Daily Core page via
`navigation_engine.navigate_to()`.

## Task plan

| # | Task | Risk | Est |
|---|---|---|---|
| T1 | Move 2 — Power Stats ribbon + mount | low | 45 min |
| T2 | Move 3 — Feature pills (nav_config + subtab_bar) | low | 30 min |
| T3 | Move 1 — Hero "Today's Call" card on Command Center | medium | 45 min |
| T4 | Move 5 — Daily Flow shortcut row | low | 20 min |
| T5 | Move 4 — Empty-state CTAs on Command Center KPIs | low | 20 min |
| T6 | Smoke + screenshots + tag phase-5-complete | low | 15 min |

Order rationale: Move 2 (ribbon) + Move 3 (pills) = instant brand-wide
visibility. Then Move 1/5/4 concentrate on Command Center.

Total est: ~3 hrs.

## Non-goals

- Don't touch underlying engines (ribbon reads live values, doesn't
  compute them).
- Don't change Daily Core count or nav structure — Phase 3 nav layout
  stays.
- Don't ship animations / emojis that rely on external assets.
