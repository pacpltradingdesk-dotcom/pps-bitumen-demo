# Phase 1 — Demo Purge + Real Data Sync

**Spec date:** 14 April 2026
**Status:** Approved (awaiting implementation plan)
**Audience:** Prince P Shah (primary user), prospective clients (observers)
**Scope:** Phase 1 of 4 in the "Surgical Rewire" initiative.

## Context

`pps-demo-live` is PPS Anantam's bitumen trading dashboard. Prince uses it daily for pricing, sales, intelligence, and reporting. It is also shown to prospective clients as proof that PPS operates a data-driven business.

Today the dashboard mixes real data (25,667 contacts, 63 suppliers, 53K+ infra demand rows, 572 director briefings) with demo data (3 fake customers, 8 hardcoded contractor names, 15+ placeholder strings in form inputs, a `mock_data.py` generator). When Prince demos to a client, the fake names undermine the "real business" story.

Phase 1 removes the demo footprint and replaces it with the real data that already exists on disk, adds a reusable Excel/CSV import wizard so Prince can keep the dataset current himself, and leaves the codebase ready for the later phases (live refresh, nav simplification, per-page UX).

## Goals

1. Remove every fake/demo customer, contractor, and placeholder name from user-facing surfaces.
2. Sync the 25,667 real contacts from `tbl_contacts.json` into the SQLite `contacts` table and promote relevant rows into `customers`.
3. Import `Bitumen_Customer_Profile_WhatsApp.xlsx` into a new `customer_profiles` table.
4. Ship a reusable Excel/CSV import wizard at `/System/Import Wizard` so Prince can add future contacts or profiles without CLI.
5. Empty-states instead of fake data on pages where real data is not yet present.

## Non-goals

- Live refresh / auto-polling standardization — Phase 2.
- Navigation and information-architecture simplification — Phase 3.
- Per-page UX polish — Phase 4.
- Multi-user or role-based access.
- Any new business feature.

## Done criteria

- `grep -r "L&T Construction\|Rohan Kumar\|Shree Ganesh\|Highway Builders" --include='*.py'` in the 15 audited files returns zero matches (the standalone `generate_pdf_demos.py` dev script is excluded).
- 25,000+ rows visible and searchable in the Contacts Directory page.
- At least one real Excel/CSV file imported through the wizard in a smoke test.
- Prince confirms verbally that no fake names appear on any Daily Core page.
- All pre-existing `streamlit.testing.v1` AppTest journeys (morning-intel, sales-flow, deal-to-dispatch) still pass with zero errors.
- Rollback flow tested once: run a test import, then revert it through `import_history`.

## Data audit

| File / Table | State now | Action in Phase 1 |
|---|---|---|
| `sales_parties.json` | 3 fake customers | Delete file. |
| `customers` DB table | 3 demo rows | Truncate; re-populate via categorization from `contacts`. |
| `suppliers` DB table | 63 real rows (IOCL, BPCL, HPCL, MRPL, Agarwal, etc.) | Keep unchanged. |
| `contacts` DB table | 132 rows | Full sync from `tbl_contacts.json` (25,667). |
| `tbl_contacts.json` | 25,667 real entries | Source of truth for the sync. |
| `mock_data.py` | 133 lines of random generators | Delete file; replace callers with real queries. |
| `demand_analytics.py` | 8 hardcoded contractor names | Replace with live DB query filtered by category. |
| Placeholder `text_input` values in 15+ files | "L&T Construction", "Rohan Kumar", etc. | Replace with neutral strings ("Customer name", "Client name"). |
| `Bitumen_Customer_Profile_WhatsApp.xlsx` | Unstructured Excel in parent dir | Import into new `customer_profiles` table via wizard. |
| `director_briefings` (572 rows) | Real generated output | Keep. |
| `infra_*` tables (53K+) | Real govt data | Keep. |
| `price_history` (8 rows) | Real market prices | Keep. |

## Import wizard — `pages/system/import_wizard.py`

A five-step wizard that lets Prince drop an Excel or CSV and import it into any of four target tables.

**Steps:**

1. **Upload** — drag-and-drop area. After file lands, show rows and columns detected.
2. **Map columns** — for each target-table field, a dropdown of source columns, pre-filled by fuzzy alias match (e.g. "Party Name" → `name`, "Mobile" → `phone`, "GST No." → `gstin`).
3. **Classify** — radio to pick target: `customer` / `supplier` / `contact` / `customer_profile`. Category tag (Contractor, Trader, Refinery, etc.) selected here.
4. **Preview & clean** — first 20 rows rendered as a table with duplicate rows flagged (match on name+phone). User picks dedupe strategy: skip / overwrite / merge.
5. **Commit** — progress bar, then summary panel: "Imported N new, skipped M duplicates, E errors" plus a back-link to the Contacts Directory.

**Wizard state** lives in `st.session_state` so navigating between steps is mobile-friendly and does not depend on URL params.

**Auto-save** — if the user leaves mid-wizard and returns, they resume from the last completed step.

**Rollback** — every import writes a row to `import_history`. The import_history dashboard offers a one-click revert for the most recent N imports; revert removes the inserted rows and marks the history row `reverted=1`.

## Import engine — `contact_import_engine.py`

Pure Python, no Streamlit. Reusable by the wizard and by a CLI script.

**Public API:**

- `parse_spreadsheet(file) -> pandas.DataFrame` — accepts `.xlsx` or `.csv`.
- `suggest_column_mapping(df_cols, target_schema) -> dict[str, str]` — fuzzy-matches source columns to DB fields. Known aliases table lives in the engine.
- `validate_rows(df, target_table) -> tuple[pd.DataFrame, pd.DataFrame]` — returns (valid_rows, invalid_rows_with_reason). Rules: required fields present, GSTIN format if supplied, Indian phone format if supplied.
- `dedupe_against_db(rows, target_table, strategy) -> pd.DataFrame` — `strategy` ∈ `{'skip', 'overwrite', 'merge'}`. Dedupe key is `name + phone` (case-insensitive, whitespace-normalised).
- `commit_import(rows, target_table, source_file) -> dict` — writes rows, writes `import_history`, returns `{inserted, skipped, errors}`. Wrapped in a single transaction so a mid-batch failure leaves the DB untouched.
- `revert_import(import_history_id) -> int` — deletes rows that were inserted by that import, returns count reverted.

## Schema changes

```sql
CREATE TABLE customer_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  company TEXT,
  city TEXT,
  state TEXT,
  whatsapp TEXT,
  email TEXT,
  category TEXT,
  notes TEXT,
  source_file TEXT,
  imported_at TEXT NOT NULL
);

CREATE TABLE import_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_name TEXT NOT NULL,
  target_table TEXT NOT NULL,
  rows_inserted INTEGER NOT NULL,
  rows_skipped INTEGER NOT NULL,
  rows_errored INTEGER NOT NULL,
  imported_at TEXT NOT NULL,
  reverted INTEGER DEFAULT 0
);

ALTER TABLE customers ADD COLUMN imported_from TEXT;
```

Migrations are additive; `database.py` runs them inside a transaction on startup. If already applied (detected via `PRAGMA table_info`), they are skipped.

## Migration sequence

Each step is a discrete commit so any mid-run failure can be inspected.

1. **Safety** — back up `bitumen_dashboard.db` → `bitumen_dashboard.db.pre-phase1.bak`, back up `tbl_contacts.json` → `.pre-phase1.bak`, tag git `pre-phase1-baseline`.
2. **Schema migration** — run the three DDL statements above.
3. **Demo purge** — delete the three demo rows from `customers`, delete `sales_parties.json`, delete `mock_data.py`, run `scripts/phase1_purge_demo_strings.py` to neutralise hardcoded placeholder strings in the 15 audited files, replace the 8 hardcoded contractor names in `demand_analytics.py` with a live DB query.
4. **Import real contacts** — `python -m contact_import_engine --source tbl_contacts.json --target contacts`. Expected: ~25K inserted, ~500 duplicates skipped, ~50 validation errors (bad GST, malformed phone).
5. **Categorise** — rows in `contacts` whose category contains "contractor" are promoted into `customers` via an `INSERT INTO customers SELECT ... FROM contacts WHERE ...`.
6. **Prince runs the wizard** — opens `/System/Import Wizard`, drops `Bitumen_Customer_Profile_WhatsApp.xlsx`, confirms mapping, commits. `customer_profiles` populated.
7. **Wire downstream pages** — `demand_analytics`, `pricing_calculator`, `negotiation`, `comm_hub`, `crm_tasks`, `opportunities`, `command_center`, `contacts_directory_dashboard` updated to read the real tables and show neutral placeholders where no data is selected.
8. **Verification gate** — Prince confirms each Daily Core page is clean.
9. **Cleanup + commit** — move backups to `.bak.archive/`, commit `phase-1: demo purge + real data sync complete`.

## Code touchpoints

**New files:**
- `pages/system/import_wizard.py` (~400 lines)
- `contact_import_engine.py` (~300 lines)
- `scripts/phase1_migrate.py` (~150 lines, idempotent migration runner)
- `scripts/phase1_purge_demo_strings.py` (~100 lines, scripted find-and-replace; skips `generate_pdf_demos.py`, `docs/`, `tests/`, and `__pycache__/`)
- `tests/test_contact_import_engine.py` (~200 lines)

**Modified files (line counts are estimates):**
- `database.py` — +40 lines to add the two tables and the ALTER.
- `seed_data.py` — remove `seed_contacts()` demo branch and stop writing dummy sales parties.
- `command_intel/demand_analytics.py` — replace hardcoded list with live query (~60 lines).
- `command_intel/contacts_directory_dashboard.py` — pagination and refresh after import (~30 lines).
- `pages/pricing/pricing_calculator.py`, `pages/sales/negotiation.py`, `pages/sales/comm_hub.py`, `pages/sales/crm_tasks.py`, `pages/home/command_center.py`, `pages/home/opportunities.py`, `command_intel/crm_automation_dashboard.py`, `command_intel/ai_dashboard_assistant.py`, `command_intel/news_dashboard.py` — neutral placeholder strings and DB-backed dropdowns (~10–20 lines each).

**Deleted:**
- `mock_data.py`
- `sales_parties.json`
- `command_intel/contact_importer.py` (superseded by the new wizard)

**Config changes:**
- `.gitignore` — add `*.pre-phase1.bak` and `.bak.archive/`.

No new third-party dependencies. `openpyxl` and `pandas` are already in use.

## Error handling

- Invalid GSTIN in a row — row shown inline with the reason, user can fix in place, other rows still commit.
- Missing required field (`name`) — row skipped, reason logged in the errors tab of the wizard summary.
- Mid-import crash — the whole transaction rolls back; `import_history` is not written, so no partial state to clean up.
- Column auto-map guesses wrong — user can override any mapping in step 2 before commit.
- Duplicate detection false positive (two real people with same name+phone) — dedupe strategy `merge` updates the newer fields onto the existing row rather than skipping.
- Wizard navigated away mid-flow — `st.session_state` retains progress; next visit resumes from the last completed step.

## Testing

**Automated (must pass in CI):**
- `tests/test_contact_import_engine.py`
  - Parse a valid `.xlsx` and a valid `.csv` yield identical schemas.
  - Column mapping returns the expected field for ten known alias patterns.
  - Dedupe: exact match skipped, fuzzy match (case, whitespace) skipped, unique rows pass through.
  - Commit rolls back cleanly on a deliberately malformed row mid-batch.
  - `import_history` row written for every commit.
  - Revert removes exactly the inserted rows and no others.
- Existing `streamlit.testing.v1` AppTest journeys continue to pass.
- The 77-page import smoke test (all modules import without exception) continues to pass.

**Manual smoke tests (Prince):**
1. Command Center shows no fake KPI numbers — either real or empty state.
2. Negotiation: typing "L" in Customer autocompletes against real contacts; no "L&T Construction" placeholder.
3. Contacts Directory shows 25K+ rows and search by "Gujarat" filters correctly.
4. Import Wizard: dropping a 5-row test CSV results in 5 new rows within 10 seconds.
5. `import_history` shows the test import; its revert button removes the rows and marks the entry reverted.

**Codebase grep check:**
`grep -r "L&T Construction\|Rohan Kumar\|Shree Ganesh\|Highway Builders" --include='*.py'` returns zero matches across the 15 audited files. `generate_pdf_demos.py` is excluded (it is a developer-only tool that never renders in the app).

## Rollback strategy

- Schema migration or demo purge fails → restore `*.pre-phase1.bak` files, `git reset --hard pre-phase1-baseline`.
- Contact import partial failure → `import_history` revert button removes the inserted rows.
- Wizard import regrets → same revert path.
- Downstream wiring breaks a page → forward-fix; backups are still in place in case of a full rollback.

## Out-of-scope follow-ups

These live in Phase 2, 3, 4 specs (not yet written):

- Phase 2 — live refresh standardisation: `refresh_bar.py` component, `streamlit-autorefresh` dependency, `st.rerun()` audit across 220+ call sites.
- Phase 3 — nav simplification: top bar down to 6 modules, Daily Core surfaced, 66 advanced pages moved to a drawer.
- Phase 4 — per-page UX pass: active-customer banner, last-updated strip, consistent action buttons, empty states, premium PDF sharing buttons everywhere.
