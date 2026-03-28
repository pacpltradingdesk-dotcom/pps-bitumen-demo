# directory_fetcher.py
# PPS Anantam Agentic AI Eco System — v3.3.0
# India Bitumen & Roads Procurement Directory — Live Fetch & Verify
#
# SOURCE_REGISTRY: one entry per org_id with URL, schedule, type
# Fetches source pages (no network calls at import time)
# Logs fetch results to tbl_dir_fetch_logs.json
# Logs failures to tbl_dir_bugs.json

from __future__ import annotations

import datetime
import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

_BASE = Path(__file__).parent
TBL_DIR_FETCHES = _BASE / "tbl_dir_fetch_logs.json"
TBL_DIR_BUGS    = _BASE / "tbl_dir_bugs.json"

_lock = threading.RLock()

# ── Utilities ──────────────────────────────────────────────────────────────────
def _ist_now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")


def _load(path: Path, default: Any = None) -> Any:
    if default is None:
        default = []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE REGISTRY — one entry per org_id (56 Phase 1 entries)
# ══════════════════════════════════════════════════════════════════════════════
SOURCE_REGISTRY: Dict[str, dict] = {
    # ── Group A: Central ──────────────────────────────────────────────────────
    "CENT-001": {"url": "https://morth.nic.in/contact-us",           "schedule": "weekly",  "type": "HTML"},
    "CENT-002": {"url": "https://nhai.gov.in/ContactUs2",             "schedule": "weekly",  "type": "HTML"},
    "CENT-003": {"url": "https://nhidcl.com/contact",                 "schedule": "weekly",  "type": "HTML"},
    "CENT-004": {"url": "https://pmgsy.nic.in/contactus.asp",         "schedule": "monthly", "type": "HTML"},
    "CENT-005": {"url": "https://cpwd.gov.in/contact.aspx",           "schedule": "monthly", "type": "HTML"},
    "CENT-006": {"url": "https://bro.gov.in/contact.htm",             "schedule": "monthly", "type": "HTML"},

    # ── Group B: NHAI Regional Offices ────────────────────────────────────────
    "NHAI-RO-N":  {"url": "https://nhai.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},
    "NHAI-RO-S":  {"url": "https://nhai.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},
    "NHAI-RO-E":  {"url": "https://nhai.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},
    "NHAI-RO-W":  {"url": "https://nhai.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},
    "NHAI-RO-NW": {"url": "https://nhai.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},
    "NHAI-RO-C":  {"url": "https://nhai.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},

    # ── Group C: State PWDs ───────────────────────────────────────────────────
    "ST-AP": {"url": "https://aprd.ap.gov.in/contact",                "schedule": "monthly", "type": "HTML"},
    "ST-AR": {"url": "https://pwd.arunachal.gov.in/contact",           "schedule": "monthly", "type": "HTML"},
    "ST-AS": {"url": "https://pwd.assam.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},
    "ST-BR": {"url": "https://rcd.bih.nic.in/ContactUs.aspx",         "schedule": "monthly", "type": "HTML"},
    "ST-CG": {"url": "https://pwdcg.gov.in/contact",                  "schedule": "monthly", "type": "HTML"},
    "ST-GA": {"url": "https://pwd.goa.gov.in/contact-us",             "schedule": "monthly", "type": "HTML"},
    "ST-GJ": {"url": "https://roads.gujarat.gov.in/contactus.htm",    "schedule": "monthly", "type": "HTML"},
    "ST-HR": {"url": "https://pwdharyana.gov.in/contact-us",           "schedule": "monthly", "type": "HTML"},
    "ST-HP": {"url": "https://hppwd.hp.gov.in/contact",               "schedule": "monthly", "type": "HTML"},
    "ST-JH": {"url": "https://rcd.jharkhand.gov.in/contact-us",       "schedule": "monthly", "type": "HTML"},
    "ST-KA": {"url": "https://pwd.karnataka.gov.in/english/contact-us","schedule": "monthly", "type": "HTML"},
    "ST-KL": {"url": "https://pwd.kerala.gov.in/contact",             "schedule": "monthly", "type": "HTML"},
    "ST-MP": {"url": "https://mpmpwd.nic.in/contact-us",              "schedule": "monthly", "type": "HTML"},
    "ST-MH": {"url": "https://pwd.maharashtra.gov.in/1076/Contact-Us","schedule": "monthly", "type": "HTML"},
    "ST-MN": {"url": "https://pwd.manipur.gov.in/contact",            "schedule": "monthly", "type": "HTML"},
    "ST-ML": {"url": "https://megpwd.gov.in/contact",                 "schedule": "monthly", "type": "HTML"},
    "ST-MZ": {"url": "https://pwd.mizoram.gov.in/contact",            "schedule": "monthly", "type": "HTML"},
    "ST-NL": {"url": "https://pwdnagaland.gov.in/contact-us",         "schedule": "monthly", "type": "HTML"},
    "ST-OD": {"url": "https://works.odisha.gov.in/contact.htm",       "schedule": "monthly", "type": "HTML"},
    "ST-PB": {"url": "https://punjabpwdbr.gov.in/contact",            "schedule": "monthly", "type": "HTML"},
    "ST-RJ": {"url": "https://pwd.rajasthan.gov.in/content/raj/pwd/en/home.html", "schedule": "monthly", "type": "HTML"},
    "ST-SK": {"url": "https://spwd.sikkim.gov.in/contact",            "schedule": "monthly", "type": "HTML"},
    "ST-TN": {"url": "https://tnhighways.gov.in/contact",             "schedule": "monthly", "type": "HTML"},
    "ST-TG": {"url": "https://tgrb.telangana.gov.in/Contact",         "schedule": "monthly", "type": "HTML"},
    "ST-TR": {"url": "https://pwd.tripura.gov.in/contact",            "schedule": "monthly", "type": "HTML"},
    "ST-UP": {"url": "https://uppwd.gov.in/en/contact",               "schedule": "monthly", "type": "HTML"},
    "ST-UK": {"url": "https://pwduk.uk.gov.in/contact.html",          "schedule": "monthly", "type": "HTML"},
    "ST-WB": {"url": "https://wbpwd.gov.in/contact",                  "schedule": "monthly", "type": "HTML"},

    # ── UTs ───────────────────────────────────────────────────────────────────
    "UT-AN": {"url": "https://pwd.andaman.gov.in/contact.htm",        "schedule": "monthly", "type": "HTML"},
    "UT-CH": {"url": "https://chandigarh.gov.in/contact_us.htm",      "schedule": "monthly", "type": "HTML"},
    "UT-DD": {"url": "https://dnh.nic.in/contact.aspx",               "schedule": "monthly", "type": "HTML"},
    "UT-DL": {"url": "https://pwd.delhi.gov.in/wps/portal/PWD/HomePage/Department/contactUs", "schedule": "monthly", "type": "HTML"},
    "UT-JK": {"url": "https://jkpwd.nic.in/contactUs",                "schedule": "monthly", "type": "HTML"},
    "UT-LA": {"url": "https://lahdc.nic.in/contact",                  "schedule": "monthly", "type": "HTML"},
    "UT-LD": {"url": "https://lakgov.gov.in/contact",                 "schedule": "monthly", "type": "HTML"},
    "UT-PY": {"url": "https://pwd.py.gov.in/contact-us",              "schedule": "monthly", "type": "HTML"},

    # ── Group D: State Road Corporations ─────────────────────────────────────
    "CORP-MH": {"url": "https://msrdc.org/contact.html",              "schedule": "monthly", "type": "HTML"},
    "CORP-GJ": {"url": "https://gsrdc.gujarat.gov.in/contact",        "schedule": "monthly", "type": "HTML"},
    "CORP-KA": {"url": "https://krdcl.in/contactus",                  "schedule": "monthly", "type": "HTML"},
    "CORP-AP": {"url": "https://aproadways.ap.gov.in/contact",        "schedule": "monthly", "type": "HTML"},
    "CORP-TN": {"url": "https://tnrdc.in/contact.html",               "schedule": "monthly", "type": "HTML"},
    "CORP-RJ": {"url": "https://rsrdc.rajasthan.gov.in/contact",      "schedule": "monthly", "type": "HTML"},
    "CORP-HR": {"url": "https://hridc.org/contact",                   "schedule": "monthly", "type": "HTML"},
    "CORP-UP": {"url": "https://upeida.in/contact-us",                "schedule": "monthly", "type": "HTML"},
}

# ── Schedule intervals in days ─────────────────────────────────────────────────
_SCHEDULE_DAYS = {
    "daily":   1,
    "weekly":  7,
    "monthly": 30,
}


def _is_due(org_id: str) -> bool:
    """Return True if the org is overdue for a refresh based on its schedule."""
    reg = SOURCE_REGISTRY.get(org_id, {})
    interval = _SCHEDULE_DAYS.get(reg.get("schedule", "monthly"), 30)
    # Read last fetch timestamp from fetch logs
    logs = _load(TBL_DIR_FETCHES, [])
    org_logs = [l for l in logs if l.get("org_id") == org_id]
    if not org_logs:
        return True
    last_log = max(org_logs, key=lambda l: l.get("fetched_ist", ""))
    last_str = last_log.get("fetched_ist", "")
    try:
        last_dt = datetime.datetime.strptime(last_str, "%Y-%m-%d %H:%M IST")
        due_dt  = last_dt + datetime.timedelta(days=interval)
        return datetime.datetime.now() >= due_dt
    except Exception:
        return True


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def log_fetch(
    org_id: str, status: str, rows: int = 0, error: str = "", url: str = ""
) -> None:
    """Append a fetch result to tbl_dir_fetch_logs.json (max 2000 records)."""
    with _lock:
        logs = _load(TBL_DIR_FETCHES, [])
        logs.append({
            "log_id":      f"FL-{uuid.uuid4().hex[:8].upper()}",
            "org_id":      org_id,
            "url":         url or SOURCE_REGISTRY.get(org_id, {}).get("url", ""),
            "status":      status,       # ok | error | skip
            "rows":        rows,
            "error":       error,
            "fetched_ist": _ist_now(),
        })
        if len(logs) > 2000:
            logs = logs[-2000:]
        _save(TBL_DIR_FETCHES, logs)


def log_bug(
    org_id: str, source_url: str = "", error: str = "", http_code: int = 0
) -> None:
    """Append or update a bug record in tbl_dir_bugs.json."""
    with _lock:
        bugs = _load(TBL_DIR_BUGS, [])
        # Check if open bug exists for this org
        for bug in bugs:
            if bug.get("org_id") == org_id and bug.get("status") == "open":
                bug["retry_count"] = bug.get("retry_count", 0) + 1
                bug["last_seen_ist"] = _ist_now()
                bug["http_code"] = http_code or bug.get("http_code", 0)
                bug["error"] = error or bug.get("error", "")
                _save(TBL_DIR_BUGS, bugs)
                return
        # New bug
        bugs.append({
            "bug_id":       f"BUG-{uuid.uuid4().hex[:8].upper()}",
            "org_id":       org_id,
            "source_url":   source_url or SOURCE_REGISTRY.get(org_id, {}).get("url", ""),
            "error":        error,
            "http_code":    http_code,
            "first_seen_ist": _ist_now(),
            "last_seen_ist":  _ist_now(),
            "retry_count":  0,
            "status":       "open",
        })
        _save(TBL_DIR_BUGS, bugs)


def close_bug(org_id: str) -> None:
    """Mark any open bug for this org as resolved."""
    with _lock:
        bugs = _load(TBL_DIR_BUGS, [])
        for bug in bugs:
            if bug.get("org_id") == org_id and bug.get("status") == "open":
                bug["status"] = "resolved"
                bug["resolved_ist"] = _ist_now()
        _save(TBL_DIR_BUGS, bugs)


# ══════════════════════════════════════════════════════════════════════════════
# FETCH & VERIFY
# ══════════════════════════════════════════════════════════════════════════════

def _http_get(url: str, timeout: int = 15) -> tuple:
    """
    Attempt to GET a URL. Returns (ok: bool, text: str, http_code: int).
    Uses urllib (stdlib) — no extra deps required.
    """
    import urllib.request
    import ssl
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PPSDirectory/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return True, resp.read().decode("utf-8", errors="replace"), resp.status
    except Exception as exc:
        code = 0
        if hasattr(exc, "code"):
            code = exc.code
        return False, str(exc), code


def _extract_contact_signals(html: str) -> dict:
    """
    Parse raw HTML for email / phone patterns.
    Returns {emails: list, phones: list}.
    """
    import re
    emails = list(set(re.findall(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html
    )))
    phones = list(set(re.findall(
        r"(?:\+91[\-\s]?)?(?:\(?0?\d{2,4}\)?[\-\s]?)?\d{6,10}", html
    )))
    return {"emails": emails[:10], "phones": phones[:10]}


def fetch_and_verify_org(org_id: str) -> dict:
    """
    GET source_url; check if key fields still match stored record.
    Returns {ok, changed_fields, new_confidence, http_code, error}.

    Does NOT auto-update the record — caller decides.
    """
    try:
        from directory_engine import _get_org, update_org
    except ImportError:
        return {"ok": False, "error": "directory_engine import failed", "changed_fields": {}}

    reg = SOURCE_REGISTRY.get(org_id)
    if not reg:
        return {"ok": False, "error": f"org_id {org_id!r} not in SOURCE_REGISTRY", "changed_fields": {}}

    url = reg["url"]
    org = _get_org(org_id)
    if not org:
        return {"ok": False, "error": f"{org_id} not in tbl_dir_orgs.json", "changed_fields": {}}

    ok, html, http_code = _http_get(url)
    if not ok:
        log_fetch(org_id, "error", error=str(html), url=url)
        log_bug(org_id, source_url=url, error=str(html), http_code=http_code)
        return {"ok": False, "error": str(html), "http_code": http_code, "changed_fields": {}}

    signals = _extract_contact_signals(html)
    changed_fields: dict = {}

    # Check if stored email is still mentioned on page
    stored_email = org.get("official_email", "")
    if stored_email and "@" in stored_email:
        if stored_email.lower() not in html.lower():
            changed_fields["official_email_status"] = "not_found_on_page"

    # Determine new confidence
    new_confidence = "High" if ok and not changed_fields else "Medium"

    log_fetch(org_id, "ok", rows=1, url=url)
    close_bug(org_id)

    # Update last_verified_ist
    update_org(org_id, {
        "last_verified_ist": _ist_now(),
        "confidence": new_confidence,
    })

    return {
        "ok":             True,
        "http_code":      http_code,
        "changed_fields": changed_fields,
        "new_confidence": new_confidence,
        "signals":        signals,
        "error":          "",
    }


# ══════════════════════════════════════════════════════════════════════════════
# BATCH REFRESH
# ══════════════════════════════════════════════════════════════════════════════

def run_phase1_refresh(force: bool = False) -> dict:
    """
    Attempt to refresh all 56 Phase 1 orgs.
    force=True ignores schedule and refreshes all.
    Returns {ok, total, updated, failed, skipped}.
    """
    total = updated = failed = skipped = 0
    org_ids = list(SOURCE_REGISTRY.keys())

    for org_id in org_ids:
        total += 1
        if not force and not _is_due(org_id):
            skipped += 1
            continue
        try:
            result = fetch_and_verify_org(org_id)
            if result.get("ok"):
                updated += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            log_bug(org_id, error=str(exc))

    return {
        "ok":      True,
        "total":   total,
        "updated": updated,
        "failed":  failed,
        "skipped": skipped,
        "run_ist": _ist_now(),
    }


def schedule_refresh_check() -> None:
    """
    Called from dashboard startup.
    Identifies any Phase 1 orgs overdue for refresh and queues them
    as a background thread (non-blocking).
    """
    due_ids = [oid for oid in SOURCE_REGISTRY if _is_due(oid)]
    if not due_ids:
        return

    def _bg():
        for org_id in due_ids:
            try:
                fetch_and_verify_org(org_id)
            except Exception:
                pass

    t = threading.Thread(target=_bg, daemon=True, name="dir_refresh")
    t.start()


def get_fetch_stats() -> dict:
    """Return summary stats from fetch logs (for dashboard display)."""
    logs = _load(TBL_DIR_FETCHES, [])
    bugs = _load(TBL_DIR_BUGS, [])
    open_bugs = [b for b in bugs if b.get("status") == "open"]
    ok_count  = sum(1 for l in logs if l.get("status") == "ok")
    err_count = sum(1 for l in logs if l.get("status") == "error")
    last_run  = max((l.get("fetched_ist", "") for l in logs), default="Never")
    return {
        "total_fetches": len(logs),
        "ok":            ok_count,
        "errors":        err_count,
        "open_bugs":     len(open_bugs),
        "last_run_ist":  last_run,
    }
