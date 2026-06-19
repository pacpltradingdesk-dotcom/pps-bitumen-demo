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
