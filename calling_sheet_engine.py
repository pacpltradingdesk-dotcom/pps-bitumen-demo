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
