# Daily Calling Sheet — Design Spec

> _Date: 2026-06-26 · Owner: Rahul · App: pps-demo-live (PPS Anantam V6) · Status: APPROVED (design)_

## 1. Problem / Goal

Sales team ko ek jagah chahiye jahan har sales rep apni **daily calling sheet**
(Excel/CSV of leads/numbers to call) **upload** kare, us par din-bhar **kaam** kare
(har call ka status, remark, outcome, next follow-up set kare), har din ki **alag
sheet** bane, aur **har user ke poore records permanently** rahein. Manager/director
ko sabki sheets ka **oversight + team summary** chahiye.

This is a NEW section — distinct from the existing "📓 Daily Log" page
(`daily_log_panel.py`, a manual journal over `daily_logs`). The calling sheet is a
structured, uploadable **worklist**, not a free-form journal.

## 2. Decisions (locked)

| Topic | Decision |
|-------|----------|
| Visibility | Rep sees/edits **own** sheets only. **director** (oversight) sees **all** + Team tab. |
| Upload format | **Flexible auto-detect** — any Excel/CSV; system detects columns, user maps name/phone/company; rest preserved. |
| Per-call fields | **Call status, Remark/notes, Outcome, Next follow-up date** (all four). |
| Daily handling | **Daily separate sheet + carry-over** — un-called (Pending) rows can be pulled into a new day's sheet. Re-upload appends to today. |
| Approach | **DB-backed worklist** (2 tables + engine + new page) — fits codebase conventions. |

Rejected: file-based storage (reporting/carry-over/rollup painful); reusing
`daily_logs` (journal schema, would muddy both). Optional future cross-link: a
completed call may also drop a `daily_logs`/CRM entry — out of scope for v1.

## 3. Architecture

Follows the app's "engine-per-concern + SQLite + `command_intel/` page renderer"
pattern.

- **`calling_sheet_engine.py`** (root) — pure logic: parse upload, column auto-detect,
  CRUD, carry-over, per-sheet/per-user/team summaries. No Streamlit imports (testable).
- **`command_intel/calling_sheet_dashboard.py`** — page renderer with sub-tabs.
- **`database.py`** — 2 new `CREATE TABLE` statements in schema init + thin
  `insert_/get_/update_` helpers reusing existing `_insert_row` / `_update_row` /
  `_select_all`.
- **`nav_config.py`** — new page in the Sales (📋/🧾) module.
- **`dashboard.py`** — `_safe_render` routing entry → `calling_sheet_dashboard.render()`.

### Module boundaries
- Engine knows DB + parsing, nothing about UI.
- Dashboard knows UI + calls engine, never raw SQL.
- DB helpers are the only place that names tables/columns (single source — avoids the
  silent-failure schema-mismatch class fixed earlier this codebase).

## 4. Data model

**`calling_sheets`** — one row per (user, day) sheet:

| col | type | notes |
|-----|------|-------|
| id | INTEGER PK | |
| owner_username | TEXT | from `_auth_username` |
| owner_name | TEXT | display |
| sheet_date | TEXT (YYYY-MM-DD) | the day; default today, editable on upload |
| title | TEXT | e.g. original filename or "Calling Sheet 26-Jun" |
| source_filename | TEXT | uploaded file name |
| total_rows | INTEGER | denormalized count |
| created_at / updated_at | TEXT | IST timestamps |

**`calling_sheet_rows`** — one row per call/lead:

| col | type | notes |
|-----|------|-------|
| id | INTEGER PK | |
| sheet_id | INTEGER (FK→calling_sheets.id) | |
| owner_username | TEXT | denormalized for fast per-user / carry-over queries |
| lead_name | TEXT | mapped |
| phone | TEXT | mapped |
| company | TEXT | mapped (nullable) |
| city | TEXT | mapped (nullable) |
| extra | TEXT (JSON) | all other original columns, preserved verbatim |
| call_status | TEXT | default `'Pending'`; Connected/No answer/Busy/Switched off/Wrong number/Callback |
| outcome | TEXT | `''`/Interested/Quote requested/Not interested/Follow-up/Deal |
| remark | TEXT | free text |
| followup_date | TEXT (YYYY-MM-DD) | nullable |
| called_at | TEXT | set when status last changed from Pending |
| carried_from_row_id | INTEGER | null, or source row id if carried over |
| created_at / updated_at | TEXT | |

Status/outcome value lists live as constants in the engine (single source).

## 5. Flows

### 5.1 Upload
1. `st.file_uploader` (xlsx/xls/csv) → engine parses with pandas.
2. Auto-detect columns (case/space-insensitive match for name/phone/company/city;
   heuristics e.g. a column of 10-digit values → phone).
3. Mapping UI: user confirms/adjusts name·phone·company·city mapping; everything else
   goes to `extra` JSON. `sheet_date` defaults to today (editable).
4. Preview first N rows → Confirm → create `calling_sheets` + bulk-insert rows
   (`call_status='Pending'`). Empty/duplicate-phone rows flagged (not auto-dropped).

### 5.2 Today's Calls (worklist)
- Show today's sheet rows in `st.data_editor` (editable): call_status, outcome,
  remark, followup_date inline-editable; name/phone/company read-only.
- **Save** → diff against loaded state → `update_calling_row` per changed row; set
  `called_at` when leaving Pending.
- Progress header: X/Y called, connected %, conversions.
- (Optional, plan as stretch) "Focus mode": one lead card at a time with quick buttons.

### 5.3 Carry-over
- Button "Pull pending from previous days" → engine finds this user's rows with
  `call_status='Pending'` in sheets older than today AND not already carried into
  today (dedupe via `carried_from_row_id`) → inserts copies into today's sheet.
- If no today sheet exists, create an empty one first.

### 5.4 History
- List the user's past `calling_sheets` (date, total, called, completion %, conversions).
- Click a sheet → view/edit its rows (read-only for very old? — editable, no lock in v1).

### 5.5 Team view (director only)
- Rep selector (or "All") + date range → list sheets across reps + summary table:
  per rep per day = calls made, connected %, outcomes breakdown. Read-only.

## 6. RBAC / visibility

- Identity from `st.session_state["_auth_username"]` / `_auth_user`.
- Every read/write filters `owner_username = <current>` for role `sales`.
- Role `director` → may select any user / "All"; sees Team tab. (`operations`/`viewer`
  → no access or read-only own — page gated like other Sales pages via existing
  `_allowed()`/`resolve_page` RBAC.)
- Oversight role = **director** for v1. A dedicated "sales-manager" role can be added
  later if needed (noted, not built now).

## 7. Records / reporting

- Per-sheet progress + conversion computed from rows on the fly.
- Per-user lifetime history (all their sheets).
- Team rollup for director.
- Nothing is hard-deleted; sheets/rows persist as the permanent record.

## 8. UI placement

Sales module → new page **"📞 Daily Calling Sheet"**. Sub-tabs:
**Upload · Today's Calls · History · Team** (Team rendered only for director).

## 9. Testing

- pytest (`tests/test_calling_sheet.py`): column auto-detect, parse→rows, status/remark
  update sets called_at, carry-over inserts pending only + no duplicates, RBAC filter
  (rep sees only own; director sees all).
- DB helpers validated against real created schema (PRAGMA) to avoid column drift.
- Headless `test_apptest_*` sweep: new page renders for all 4 roles without ERROR.

## 10. Out of scope (v1)

- Auto-dialer / click-to-call integration (may add a `tel:`/WhatsApp link per row as a
  cheap stretch).
- Auto cross-posting completed calls into `daily_logs`/CRM.
- Scheduled reminders for `followup_date` (could reuse existing alert system later).
- Dedicated sales-manager role.

## 11. Incremental build order (slices — "dheere dheere")

1. **Slice 1 — Data layer:** 2 tables + DB helpers + engine CRUD + pytest. No UI.
2. **Slice 2 — Upload + parse:** engine parse/auto-detect + Upload tab + mapping UI.
3. **Slice 3 — Today's Calls:** editable worklist grid + save + progress.
4. **Slice 4 — History:** per-user past sheets list + view.
5. **Slice 5 — Carry-over:** pull-pending button + dedupe.
6. **Slice 6 — Team view + RBAC polish:** director rollup + gating.
7. **Slice 7 — Nav wiring + headless sweep + deploy.**

Each slice: implement → test/verify → commit. Deploy after a coherent set (likely
after Slice 3, then after Slice 7).
