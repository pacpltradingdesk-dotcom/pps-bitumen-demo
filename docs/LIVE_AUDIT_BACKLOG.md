# PPS Bitumen Dashboard — Live Audit Backlog (19-Jun-2026)

Live walkthrough of `ppsanatams.cloud` from a **bitumen-price-platform** lens.
Severity: 🔴 wrong-data/broken · 🟠 UX/clarity · 🟢 betterment.

## #1 THEME (cross-cutting) — Price & Signal NOT single-source on screen
The single-source-of-truth holds in `price_master`/`get_unified_prices`, but the
RENDERED values diverge across pages because different surfaces read different
caches (Command Center → get_unified_prices; Live Market "Market Pulse" →
market_pulse_engine cache; ticker → another). For a price platform this is the
highest-impact problem: different screens show different Brent/VG30/USD-INR.

---

## 🏠 Command Center
- 🔴 Signal shown 3 ways at once: hero "HOLD — awaiting first market computation",
  stats-bar "BEARISH 69", ticker "WAIT 8 DAYS (37%)" / earlier "PRE-BUY 77%".
- 🔴 Hero empty-state on reload ("Run the market intelligence engine") — no real
  call for a trader landing on the page; signal not persisted/cached.
- 🟠 USD/INR change "▼ ₹6.93 (7.4%)" — implausible daily move; comparing stale
  March (93.89) vs today (86.17) as a "daily" delta. Change % must use adjacent period.
- 🟢 KPIs Brent/WTI/USD-INR/VG30 live & internally consistent on this page.
- 🟢 Quick Stats: Suppliers "—", Active Deals "—" not wired.

## 📊 Live Market
- 🔴 CROSS-PAGE PRICE MISMATCH: Live Market Pulse = Brent $75.19 / WTI $71.08 /
  INR 86.67 / VG30 ₹78,260, vs Command Center Brent $80.03 / WTI $76.19 /
  INR 86.17 / VG30 ₹76,870. Different prices on different screens.
- 🔴 Intra-page VG30 mismatch: top stats-bar ₹76,870 vs Market Pulse bar ₹78,260.
- 🔴 Signal inconsistency continues: "SIDEWAYS 50%" + "NEUTRAL 61" here vs CC's HOLD/BEARISH/PRE-BUY.
- 🟠 Stale-comparison alert: "[ESCALATED] INR strengthened 8.2% against USD".
- 🟠 Duplicate escalated alerts: "Brent moved -4.0%" + "-4.1%".
- 🟢 APIs 25/25 healthy; Opportunities 12; Predicted ₹82,596/MT.

## 🧾 Sales landing
- 🔴 Brent THIRD different value: alert "Brent … Live: $80.14" vs Live Market $75.19 vs CC $80.03.
- 🟠 "Top 5 Cheapest Sources" lists Taloja Terminal TWICE (₹84,330 and ₹87,157) — dedup bug.
- 🟠 Price Forecast (6-month) renders a FLAT line (~80k constant) — not a credible forecast.
- 🟢 Next revision 01-07-2026 dynamic (fix working).

## 🧮 Pricing Calculator (form + result)
- 🟢 Landed-cost MATH CORRECT and uses the right base ₹76,870 (= VG30_BASE):
  GST 18% +₹13,836.60, ex-refinery ₹90,706.60, transport 774km×₹6/km=₹4,644.
  CONFIRMS the inconsistency is in DISPLAY bars (market_pulse), not the calc engine.
- 🟠 Default-selected quote = the MOST EXPENSIVE option (Mumbai Drum ₹95,350.60)
  while cheapest is Ennore Port ₹86,201.26 (₹9,149 less). Should auto-select cheapest.
- 🟠 "Season: Unknown" for the destination — sales_calendar season not resolving.
- 🟠 Calculator offers only VG30/VG10 grades (no VG40/CRMB/PMB/Emulsion).
- 🟢 Multi-source ranking, full breakdown, T&C, bank, Official+Premium PDF, WhatsApp share.

---

## 🎯 PRIORITIZED IMPROVEMENT PLAN (Top 10)  —  STATUS
- ✅ DONE #1 price single-source (commit ea73b98), ✅ DONE #4 quote-cheapest (e8690e6).
- ⏳ NEXT: #2 %-change adjacent-period, #3 one AI signal, then #5-#10.

### 🔴 P0 — wrong/inconsistent data (fix first; trust-critical for a price platform)
1. ✅ DONE — **One price source on every surface.** Make Market Pulse bar, ticker, KPIs all
   read `get_unified_prices()`. Today CC shows Brent $80.03/VG30 ₹76,870 while Live
   Market shows $75.19/₹78,260 and Sales shows Brent $80.14 — three truths.
   Add a render-layer consistency test (extend test_price_consistency).
2. **One AI signal everywhere**, persisted. Today: HOLD / BEARISH 69 / PRE-BUY 77 /
   NEUTRAL 61 / SIDEWAYS 50% across pages. Compute once, cache, show last-known
   (kill "awaiting first market computation" empty-state).
3. **Fix all "% change"** to use adjacent periods — removes the bogus
   "USD/INR ▼7.4%" / "INR strengthened 8.2%" artifacts (stale March vs today).

### 🟠 P1 — business/UX correctness
4. **Quote auto-selects the CHEAPEST source**, not the most expensive.
5. **Dedup source lists** (Taloja appears twice in Top-5 cheapest).
6. **Real price forecast** (the 6-month line is flat/constant → looks fake).
7. **Resolve "Season: Unknown"** in the pricing calculator (sales_calendar lookup).
8. **All traded grades in the calculator** (add VG40/CRMB/PMB to match rate-image).
9. **Alert dedup + de-noise** ("Brent moved -4.0%" + "-4.1%"; system-health WARN/FAIL
   alerts shown to a sales user).

### 🟢 P2 — betterment
10. Empty stats ("Suppliers —", "Active Deals —") wire or hide; consistent number
    formatting (Indian grouping) everywhere.

## NOT yet live-walked (next session — browser audit is context-heavy)
Intelligence (Market Signals, Competitor Intel, Telegram), Logistics (Maritime,
Port Tracker, Feasibility, Ecosystem), Purchasers/Documents, Sharing (Share Center +
new Rate Image once deployed, Rate Broadcast, Showcase), Settings/System (SRE, API
Hub, AI, Knowledge Base, Sync).

## TOP FIX (so far)
1. 🔴 One price source on every surface — make Market Pulse / ticker / KPIs all
   read `get_unified_prices()`; add a render-time consistency test extension.
2. 🔴 One AI signal everywhere — single composite, persisted; kill the
   "awaiting computation" empty-state (show last-known).
3. 🟠 Fix all "% change" to use adjacent periods (kills the 7-8% USD/INR artifact).

---

## 🔎 LIVE BROWSER WALK — 19-Jun-2026 (full re-verification on ppsanatams.cloud)
Walked all 6 sections + 14 pages as admin. Results:

### ✅ VERIFIED FIXED (live)
- **P0 #1 price single-source** — Command Center, Live Market Pulse, ticker, refinery
  strip, Pricing Calculator base all show Brent $79.48 / WTI $75.74 / USD-INR 86.17 /
  VG30 ₹76,870. The earlier 3-way mismatch is GONE. Intra-page VG30 (top bar vs Market
  Pulse) also consistent.
- **P1 #4 quote auto-cheapest** — calculator auto-selects Ennore Port ₹86,201.26 (the
  cheapest of 6), not Mumbai Drum ₹95,350 (most expensive). Green "Selected" confirms.
- **Feasibility ↔ Calculator consistency** — both rank by landed cost, same numbers
  (CPCL Chennai ₹93,407.76, BORL Bina ₹94,303.60).
- **Maritime AIS / Port congestion** — live (Mumbai/Kandla/Mundra congestion + ETA).
- **Rate Card Image** (today's feature) — renders branded card in Share Center.

### ⏳ STILL PENDING (confirmed live)
- **P0 #2 one AI signal** — on ONE screen: hero SECURE / sidebar NEUTRAL 60 / ticker
  HOLD 44% / KPI HOLD 44% / CC "Market Signals Overview" widget NEUTRAL 50% (ALL 9
  sub-signals flat 50% = placeholder), while the real **Market Signals page computes
  SIDEWAYS 60%** with differentiated sub-signals (Crude SIDEWAYS, Currency LOW, Weather
  GOOD, News HIGH, Govt FALLING, Tender MEDIUM). ROOT: CC signal widgets are NOT reading
  the live signal engine — they show a frozen 50% placeholder. Live Market agrees with
  Market Signals page (SIDEWAYS), so divergence is concentrated in Command Center.
- **P0 #3 % change** — USD/INR KPI "▼ ₹6.93 (7.4%)" (stale Mar-vs-today) still on CC,
  Live Market, Price Prediction header. Market Pulse bar shows +0.00% (different calc).
- **P1 #5 dedup** — calculator list is clean (Taloja once); still must check the
  "Sales landing Top-5 Cheapest" surface specifically.
- **P1 #7 Season: Unknown** — pricing calculator (Adilabad) still "Season: Unknown".
- **P1 #8 grades** — calculator offers only VG30/VG10 (no VG40/CRMB/PMB/Emulsion).
- **P1 #9 alert dedup** — Live Market/Sales bar still "[ESCALATED] Brent moved -4.0% |
  Brent moved -4.1%" (dupe) + "INR strengthened 8.2%" (stale).
- **P2 #10 empty stats + formatting** — CC Quick Stats SUPPLIERS "—" / ACTIVE DEALS "—",
  but Ecosystem page HAS Suppliers=63 (just not wired to CC). News page shows
  GDP 6.49476552383821% / CPI 4.95303550973656% (unrounded, ~15 decimals).

### 🛠️ FIXED IN CODE — 19-Jun (post-walk, NOT yet deployed)
- **P0 #3 % change** — `command_center.py`: drop the price-history snapshot when it
  is >2 days old (it was an 11-Apr fossil: usd 93.1 → bogus -7.4%). Badges now fall
  back to the adjacent-period 7-day feed change.
- **P0 #2 composite (core)** — `command_center.py`: the "Market Signals Overview"
  now reads the live `MarketIntelligenceEngine` master (SIDEWAYS 73%) instead of
  averaging stale sub-scores (which gave the contradictory NEUTRAL 50%). Now matches
  the dedicated Market Signals page. RESOLVED (per decision: distinct labels) — the
  headline buy-action KPI + ticker are relabelled "Buy Call" (HOLD) so they read as a
  separate signal from the market-direction "Composite Signal" (SIDEWAYS). Hero
  "Today's Call" (SECURE) stays a third distinct label.
- **P1 #5 dedup** — `calculation_engine.py`: cheapest-sources list now dedups by
  source name (Taloja was both an import terminal AND the auto-decanter), keeping the
  cheapest occurrence.
- **P1 #7 Season Unknown** — `sales_calendar.py`: unmapped cities now fall back to a
  national bitumen construction-season pattern (peak Feb-May & Oct-Nov, monsoon-off
  Jun-Sep) instead of "Unknown".
- **P1 #9 alert dedup** — `alert_center.py`: P0 banner dedups by normalized title
  (drops [ESCALATED] tag + numbers) so "Brent moved -4.0%/-4.1%" collapse to one.
- **P2 #10** — `command_center.py` wires Suppliers/Customers to `party_master`
  counts when the relational tables are empty (CC now shows 63 like Ecosystem);
  `market_signals_dashboard.py` rounds GDP/CPI (6.49476552383821% → 6.5%).
- **P1 #8 grades** — DONE (estimate-grade): calculator radio now offers VG30/VG10/
  VG40/CRMB/PMB. VG40/CRMB/PMB apply the flat differential from
  `price_master.GRADE_DIFFERENTIALS` (same source as the rate card: VG40 +2680,
  CRMB +1594, PMB +1644) in BOTH the optimizer (quote) and feasibility (preview),
  with an on-screen "estimate — confirm with desk" caption. Swap in PPS's real
  modified-grade premiums in `GRADE_DIFFERENTIALS` when available.

### 🆕 NEW FINDINGS (not in original backlog) — all STALE-DATA
- **Price Prediction** page banner: "🔴 Data stale · 3153 min old" (~52h).
- **Port Import Tracker**: "LAST UPDATE 02-03-2026" (~3.5 months old).
- **Telegram Analyzer**: "🔴 Data missing — click Refresh"; last run 2026-03-25 (~3mo).
  → Suggests one or more cron/refresh jobs (prediction, port-allocation, telegram-fetch)
    are not running on the VPS. Worth a systemd/cron audit alongside the P0/P1 fixes.
