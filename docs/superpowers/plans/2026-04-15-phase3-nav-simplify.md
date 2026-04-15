# Phase 3 — Navigation Simplification

**Date:** 2026-04-15
**Branch:** `feature/phase-3-nav-simplify`

## Problem

79 pages across 6 modules. Sidebar shows ALL pages in whichever module
is active — a wall of buttons that hides the 14 pages Prince actually
uses daily. Current star flags exist but don't drive layout.

## Goal

In each module sidebar, show the **starred (Daily Core) pages first,
always visible**. Hide the rest behind a collapsible **`Show all (N more)`**
expander. No pages are deleted — everything stays reachable.

## Tasks

### T1 — Re-star nav_config to match Daily Core 14
The 14 pages that should carry `star: True` after this task:

| # | Module | Page |
|---|---|---|
| 1 | Price & Info | Command Center |
| 2 | Price & Info | Live Market |
| 3 | Price & Info | Market Signals |
| 4 | Price & Info | News |
| 5 | Price & Info | Telegram Analyzer |
| 6 | Price & Info | Price Prediction |
| 7 | Price & Info | Director Briefing |
| 8 | Sales | Pricing Calculator |
| 9 | Sales | CRM & Tasks |
| 10 | Sales | Opportunities |
| 11 | Sales | Negotiation |
| 12 | Sales | Daily Log |
| 13 | Purchasers | Purchase Orders |
| 14 | Settings | Settings |

Remove `star: True` from any other entry. Total stars must equal 14.

### T2 — Update subtab_bar.py render loop
- Render all starred tabs in normal flow (unchanged look).
- After the last starred tab of a module, close the primary section and
  render a single `st.expander("➕ Show all (N more) · Advanced")` that
  holds the rest. Currently-selected page not in the starred list opens
  the expander by default.

### T3 — Smoke test
- Every module's starred count matches Daily Core allocation.
- subtab_bar imports cleanly.
- pytest 17/17 pass.

### T4 — Acceptance + tag
- Tag `phase-3-complete`, merge to main, push.
