"""
PPS Anantam — Daily Calling Sheet Engine
=========================================
Pure logic for the calling-sheet worklist: CRUD, parsing, carry-over, summaries.
No Streamlit imports — fully unit-testable. All DB access goes through database.py
low-level helpers (which validate table names against _VALID_TABLES).
"""
import io
import json
import pandas as pd
from database import (
    _insert_row, _update_row, _select_all, _get_conn, _now_ist,
)

CALL_STATUSES = ["Pending", "Connected", "No answer", "Busy",
                 "Switched off", "Wrong number", "Callback"]
OUTCOMES = ["", "Interested", "Quote requested", "Not interested",
            "Follow-up", "Deal"]
CORE_FIELDS = ["lead_name", "phone", "company", "city"]


def _loads(val):
    if not val:
        return {}
    try:
        return json.loads(val)
    except Exception:
        return {}


def _row_out(r: dict) -> dict:
    r = dict(r)
    r["extra"] = _loads(r.get("extra"))
    return r


def create_sheet(owner_username, owner_name, sheet_date, title,
                 source_filename, rows):
    """Create a calling_sheets record + bulk-insert its rows. Returns sheet_id."""
    now = _now_ist()
    # Coerce to str: callers sometimes pass a richer object (e.g. a user dict) as
    # owner_name; SQLite cannot bind a dict, so guard the whole class here.
    owner_username = str(owner_username) if owner_username is not None else ""
    if not isinstance(owner_name, str):
        owner_name = owner_username
    sheet_id = _insert_row("calling_sheets", {
        "owner_username": owner_username,
        "owner_name": owner_name or owner_username,
        "sheet_date": sheet_date,
        "title": title or f"Calling Sheet {sheet_date}",
        "source_filename": source_filename or "",
        "total_rows": len(rows),
        "created_at": now,
        "updated_at": now,
    })
    _bulk_insert_rows(sheet_id, owner_username, rows)
    return sheet_id


def _bulk_insert_rows(sheet_id, owner_username, rows):
    """Insert many rows efficiently in one connection."""
    if not rows:
        return
    now = _now_ist()
    payload = []
    for r in rows:
        payload.append((
            sheet_id, owner_username,
            (r.get("lead_name") or "").strip(),
            (r.get("phone") or "").strip(),
            (r.get("company") or "").strip(),
            (r.get("city") or "").strip(),
            json.dumps(r.get("extra") or {}, ensure_ascii=False),
            r.get("call_status") or "Pending",
            r.get("outcome") or "",
            r.get("remark") or "",
            r.get("followup_date"),
            r.get("called_at"),
            r.get("carried_from_row_id"),
            now, now,
        ))
    conn = _get_conn()
    try:
        conn.executemany(
            """INSERT INTO calling_sheet_rows
               (sheet_id, owner_username, lead_name, phone, company, city, extra,
                call_status, outcome, remark, followup_date, called_at,
                carried_from_row_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            payload,
        )
        conn.commit()
    finally:
        conn.close()


def get_sheet(sheet_id):
    rows = _select_all("calling_sheets", where="id = ?", params=(sheet_id,))
    return rows[0] if rows else None


def list_sheets(owner_username=None, limit=200):
    if owner_username:
        rows = _select_all("calling_sheets", where="owner_username = ?",
                           params=(owner_username,),
                           order="sheet_date DESC, id DESC")
    else:
        rows = _select_all("calling_sheets",
                           order="sheet_date DESC, id DESC")
    return rows[:limit]


def get_rows(sheet_id):
    rows = _select_all("calling_sheet_rows", where="sheet_id = ?",
                       params=(sheet_id,), order="id ASC")
    return [_row_out(r) for r in rows]


def delete_sheet(sheet_id, owner_username=None):
    """Delete a sheet and all its rows. If owner_username is given, only delete
    when it matches the sheet's owner (so a rep can't remove someone else's).
    Returns True if deleted, False if not found / owner mismatch."""
    conn = _get_conn()
    try:
        if owner_username is not None:
            row = conn.execute(
                "SELECT owner_username FROM calling_sheets WHERE id = ?",
                (sheet_id,)).fetchone()
            if not row or row[0] != owner_username:
                return False
        conn.execute("DELETE FROM calling_sheet_rows WHERE sheet_id = ?", (sheet_id,))
        cur = conn.execute("DELETE FROM calling_sheets WHERE id = ?", (sheet_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Upload parsing + column auto-detect ──────────────────────────────────────

_SYNONYMS = {
    "lead_name": ["name", "customer name", "customer", "client", "lead",
                  "party", "firm name", "contact name", "contact"],
    "phone": ["phone", "mobile", "mobile no", "mobile number", "contact no",
              "number", "phone no", "cell", "whatsapp", "ph"],
    "company": ["company", "firm", "organisation", "organization", "business",
                "company name", "firm name"],
    "city": ["city", "town", "location", "place", "district"],
}


def _norm(s):
    return "".join(str(s).lower().split())


def detect_columns(columns):
    avail = {c: _norm(c) for c in columns}
    mapping = {f: None for f in CORE_FIELDS}
    used = set()
    for field in CORE_FIELDS:
        for syn in _SYNONYMS[field]:
            target = _norm(syn)
            for col, ncol in avail.items():
                if col in used:
                    continue
                if ncol == target or target in ncol or ncol in target:
                    mapping[field] = col
                    used.add(col)
                    break
            if mapping[field]:
                break
    return mapping


def excel_sheet_names(file_bytes, filename):
    """Worksheet names for an Excel file; [] for CSV/other. Used to let the user
    pick the right tab when a workbook has a cover/README + data sheets."""
    if (filename or "").lower().endswith(".csv"):
        return []
    try:
        return list(pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names)
    except Exception:
        return []


def parse_file(file_bytes, filename, sheet_name=None):
    name = (filename or "").lower()
    bio = io.BytesIO(file_bytes)
    if name.endswith(".csv"):
        df = pd.read_csv(bio, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(bio, dtype=str,
                           sheet_name=(sheet_name if sheet_name else 0))
    df = df.fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_rows(df, mapping):
    out = []
    core_cols = {v for v in mapping.values() if v}
    for _, row in df.iterrows():
        rec = {f: (str(row[mapping[f]]).strip() if mapping[f] else "")
               for f in CORE_FIELDS}
        if not rec["lead_name"] and not rec["phone"]:
            continue
        extra = {c: str(row[c]).strip() for c in df.columns
                 if c not in core_cols and str(row[c]).strip()}
        rec["extra"] = extra
        out.append(rec)
    return out


# ── Row update + per-sheet summary ───────────────────────────────────────────

_EDITABLE = {"call_status", "outcome", "remark", "followup_date"}
_CONVERSION_OUTCOMES = {"Interested", "Quote requested", "Deal", "Follow-up"}


def update_row(row_id, data):
    clean = {k: v for k, v in data.items() if k in _EDITABLE}
    if not clean:
        return
    now = _now_ist()
    if clean.get("call_status") and clean["call_status"] != "Pending":
        clean["called_at"] = now
    clean["updated_at"] = now
    _update_row("calling_sheet_rows", row_id, clean)


def sheet_summary(sheet_id):
    rows = get_rows(sheet_id)
    total = len(rows)
    pending = sum(1 for r in rows if (r.get("call_status") or "Pending") == "Pending")
    called = total - pending
    connected = sum(1 for r in rows if r.get("call_status") == "Connected")
    conversions = sum(1 for r in rows if r.get("outcome") in _CONVERSION_OUTCOMES)
    return {
        "total": total, "called": called, "pending": pending,
        "connected": connected, "conversions": conversions,
        "pct_called": round(called / total * 100, 1) if total else 0.0,
    }


# ── Carry-over of un-called (pending) rows ───────────────────────────────────

def get_or_create_today_sheet(owner_username, owner_name, sheet_date):
    existing = _select_all(
        "calling_sheets", where="owner_username = ? AND sheet_date = ?",
        params=(owner_username, sheet_date), order="id DESC")
    if existing:
        return existing[0]["id"]
    return create_sheet(owner_username, owner_name, sheet_date,
                        f"Calling Sheet {sheet_date}", "", [])


def carry_over_pending(owner_username, owner_name, target_date):
    # already-carried source ids in the target date (dedupe)
    target_rows = _select_all(
        "calling_sheet_rows",
        where="owner_username = ? AND sheet_id IN "
              "(SELECT id FROM calling_sheets WHERE owner_username = ? AND sheet_date = ?)",
        params=(owner_username, owner_username, target_date))
    already = {r.get("carried_from_row_id") for r in target_rows
              if r.get("carried_from_row_id")}
    # pending rows from earlier dates
    pend = _select_all(
        "calling_sheet_rows",
        where="owner_username = ? AND call_status = 'Pending' AND sheet_id IN "
              "(SELECT id FROM calling_sheets WHERE owner_username = ? AND sheet_date < ?)",
        params=(owner_username, owner_username, target_date), order="id ASC")
    fresh = [r for r in pend if r["id"] not in already]
    if not fresh:
        return 0
    target_sid = get_or_create_today_sheet(owner_username, owner_name, target_date)
    new_rows = []
    for r in fresh:
        new_rows.append({
            "lead_name": r.get("lead_name"), "phone": r.get("phone"),
            "company": r.get("company"), "city": r.get("city"),
            "extra": _loads(r.get("extra")),
            "carried_from_row_id": r["id"],
        })
    _bulk_insert_rows(target_sid, owner_username, new_rows)
    # keep total_rows accurate
    cur = get_rows(target_sid)
    _update_row("calling_sheets", target_sid,
                {"total_rows": len(cur), "updated_at": _now_ist()})
    return len(new_rows)


# ── Team summary (director oversight) ────────────────────────────────────────

def team_summary(owner_username=None):
    sheets = list_sheets(owner_username=owner_username)
    out = []
    for s in sheets:
        summ = sheet_summary(s["id"])
        out.append({
            "sheet_id": s["id"], "owner_username": s["owner_username"],
            "owner_name": s.get("owner_name"), "sheet_date": s["sheet_date"],
            "title": s.get("title"), **summ,
        })
    return out
