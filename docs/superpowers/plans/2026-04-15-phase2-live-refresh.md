# Phase 2 — Live Refresh Standardization

**Date:** 2026-04-15
**Branch:** `feature/phase-2-live-refresh`
**Worktree:** `.worktrees/phase-2-live-refresh/`

## Problem

- `freshness_guard.py` exists and works but only covers 2 caches
  (market + news) and 3 pages (command_center, live_market, market_ticker).
- Other 11 of the Daily Core 14 pages have no visible freshness signal
  and no standard refresh button.
- User experience is inconsistent — some pages auto-stale-detect, most
  don't. No way to force refresh on-demand from any page.

## Goal

Single UI pattern across all 14 Daily Core pages:
`📊 Data X min old · [ 🔄 Refresh ]` at the top of each page.

Traffic-light dot: green `<10 min`, amber `10-30 min`, red `>30 min`.

Manual Refresh button:
1. Clears relevant file caches + `st.cache_data`
2. Triggers synchronous refresh of the caches that belong to this page
3. `st.rerun()` — user sees fresh data

## Non-goals

- No auto-polling / background threads on Streamlit Cloud free tier.
  Too expensive, not needed with the banner pattern.
- No per-widget refresh. Page-level only.

## Daily Core 14 pages + their caches

| Page key | Caches to watch |
|---|---|
| `command_center`    | hub_cache.json + tbl_news_feed.json |
| `live_market`       | hub_cache.json |
| `opportunities`     | opportunities.json |
| `pricing_calculator`| hub_cache.json (crude/FX for landed cost) |
| `price_prediction`  | hub_cache.json + ai_learned_weights.json |
| `crm_tasks`         | crm_tasks.json + crm_activity.json |
| `negotiation`       | customers from bitumen_dashboard.db (always fresh) |
| `daily_log`         | daily_log.json |
| `news`              | tbl_news_feed.json |
| `market_signals`    | tbl_market_signals.json |
| `telegram_analyzer` | tbl_telegram_intel.json |
| `documents`         | bitumen_dashboard.db (SQLite, always fresh) |
| `director_brief`    | hub_cache.json + tbl_news_feed.json |
| `settings`          | settings.json (always fresh — no bar) |

Pages with only DB-backed data get a simplified bar
(no age badge, just the Refresh button that clears `st.cache_data`).

## Tasks

### T0 — Safety baseline
`git tag phase-2-start` on current HEAD.

### T1 — Extend `freshness_guard.py`
- Add `PAGE_CACHES: dict[str, list[Path]]` registry.
- Add `get_page_age_minutes(page_key) -> dict` — returns `{max_age, per_cache_ages}`.
- Add `refresh_page(page_key, force=True)` — clears + re-fetches caches
  specific to that page, then clears `st.cache_data` globally.
- Keep existing `ensure_fresh()` + `get_cache_freshness()` for backward
  compat (command_center, live_market, market_ticker keep working).

### T2 — New component `components/refresh_bar.py`
- `render_refresh_bar(page_key: str, *, show_age: bool = True)`.
- Streamlit-native: 1 row, 3 cols (status dot + label, spacer, button).
- Dot colors: emerald / amber / red / muted (for DB-only pages).
- Button → `refresh_page(page_key)` → `st.rerun()`.

### T3 — Wire pilot (Command Center)
Add `render_refresh_bar("command_center")` at top of
`pages/home/command_center.py` render(). Smoke-test.

### T4 — Wire remaining 13 Daily Core pages
One-liner import + call per page. Keep existing `ensure_fresh` calls;
the bar is additive.

### T5 — Smoke test
- Every Daily Core page imports cleanly.
- Click Refresh on 3 random pages — verify age drops to <1 min,
  no crashes.

### T6 — Acceptance + tag
- `python -m pytest tests/` — 17/17 still pass.
- Grep gate: every Daily Core render() contains `render_refresh_bar`.
- `git tag phase-2-complete`.

## Time estimate

- T0-T2: 45 min (engine + component)
- T3: 10 min
- T4: 30 min (14 file edits, mostly mechanical)
- T5-T6: 15 min

Total: ~1.5 hrs.
