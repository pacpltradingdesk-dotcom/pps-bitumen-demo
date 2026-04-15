"""
Contact Import Engine
=====================
Backend for the Contact Importer module.

Features:
  - Parse Excel/CSV (pandas), PDF (pdfplumber if installed), Images (pytesseract if installed)
  - Extract contacts using AI (ai_fallback_engine) or deterministic regex rules
  - Duplicate detection against tbl_contacts.json
  - Save to multiple CRM/Directory destinations
  - Batch history logging to tbl_import_history.json

PPS Anantams Logistics AI — v3.3.3
"""

from __future__ import annotations

import datetime
import io
import json
import re
import uuid
from pathlib import Path
from typing import Optional

from api_hub_engine import NormalizedTables

BASE_DIR = Path(__file__).parent

# ─── Category & Destination constants ────────────────────────────────────────

CATEGORY_TYPES = [
    "Importer", "Exporter", "Trader", "Dealer",
    "Decanter Unit", "Commission Agent",
    "Truck Transporter", "Tanker Transporter",
    "Contractor", "Govt Officer", "CHA",
]

DESTINATION_OPTIONS = [
    "CRM — Tasks (Follow-Up)",
    "CRM — Activity Log",
    "Directory — Companies",
    "Directory — Persons",
    "Port Contacts",
    "Govt Contacts",
    "Logistics Contacts",
    "Export Only (No Save)",
]

# ─── Contact schema ───────────────────────────────────────────────────────────

CONTACT_SCHEMA: dict = {
    "contact_id":       "",
    "import_batch":     "",
    "category_type":    "",
    "buyer_seller_tag": "unknown",  # buyer / seller / both / unknown
    "company_name":     "",
    "person_name":      "",
    "mobile1":          "",
    "mobile2":          "",
    "email1":           "",
    "address":          "",
    "city":             "",
    "state":            "",
    "pincode":          "",
    "gstin":            "",
    "pan":              "",
    "website":          "",
    "tags":             "",
    "notes":            "",
    "source_file":      "",
    "destination":      "",
    "confidence":       0,
    "duplicate_status": "new",   # new / possible_duplicate / confirmed_dup
    "extraction_mode":  "",      # ai / rules / manual
}

# ─── Column header fuzzy-match mapping (Excel/CSV) ───────────────────────────

_COL_MAP: list[tuple[str, list[str]]] = [
    ("person_name",  ["name", "contact", "person", "full name", "contact name"]),
    ("company_name", ["company", "firm", "organization", "org", "business", "company name"]),
    ("mobile1",      ["phone", "mobile", "cell", "contact no", "mob", "tel", "phone no", "mobile no"]),
    ("mobile2",      ["phone2", "mobile2", "alt phone", "alternate mobile", "other phone"]),
    ("email1",       ["email", "mail", "e-mail", "email address", "email id"]),
    ("address",      ["address", "addr", "location", "street", "add"]),
    ("city",         ["city", "town", "district"]),
    ("state",        ["state", "province", "region"]),
    ("pincode",      ["pin", "pincode", "zip", "postal", "post code", "pin code"]),
    ("gstin",        ["gstin", "gst", "gst no", "gst number", "gst_no"]),
    ("pan",          ["pan", "pan no", "pan number", "pan_no"]),
    ("website",      ["website", "web", "url", "site"]),
    ("notes",        ["notes", "remark", "remarks", "comment", "comments", "note"]),
]

# ─── AI extraction prompt ─────────────────────────────────────────────────────

_AI_PROMPT_TMPL = """\
You are a contact data extractor for an Indian bitumen trading company.
Extract ALL contacts from the text below. Category: {category_type}.
Return ONLY a valid JSON array. Each element must have these exact keys:
  company_name, person_name, mobile1, mobile2, email1, address, city, state,
  pincode, gstin, pan, website, notes
Use "" for unknown fields. No extra keys. No markdown. No explanation.
Text:
---
{text}
---"""

# ─── Regex patterns ──────────────────────────────────────────────────────────

_RE_MOBILE  = re.compile(r'\b[6-9]\d{9}\b')
_RE_EMAIL   = re.compile(r'[\w.+\-]+@[\w\-]+\.\w+')
_RE_GSTIN   = re.compile(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b')
_RE_PAN     = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')
_RE_PINCODE = re.compile(r'\b[1-9][0-9]{5}\b')


# ══════════════════════════════════════════════════════════════════════════════
# FILE PARSING
# ══════════════════════════════════════════════════════════════════════════════

def parse_file(uploaded_file, category_type: str) -> tuple[list[dict], str, str]:
    """
    Detect file type and route to the appropriate parser.

    Returns:
      (contacts, raw_text, parse_warning)
      - contacts: pre-extracted list if structured (Excel/CSV), else []
      - raw_text: text dump for AI/rules extraction (PDF/image/unstructured)
      - parse_warning: non-empty string if a parser package is missing
    """
    name = uploaded_file.name.lower()
    ext  = name.rsplit(".", 1)[-1] if "." in name else ""

    if ext in ("xlsx", "xls", "csv"):
        contacts, warning = _parse_excel_csv(uploaded_file, category_type)
        return contacts, "", warning

    elif ext == "pdf":
        raw_text, warning = _parse_pdf(uploaded_file)
        return [], raw_text, warning

    elif ext in ("jpg", "jpeg", "png"):
        raw_text, warning = _parse_image(uploaded_file)
        return [], raw_text, warning

    else:
        # Try as text
        try:
            raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
        except Exception:
            raw_text = ""
        return [], raw_text, f"Unknown file type '.{ext}'. Treated as plain text."


def _parse_excel_csv(uploaded_file, category_type: str) -> tuple[list[dict], str]:
    """Parse Excel or CSV using pandas with fuzzy column matching."""
    try:
        import pandas as pd
    except ImportError:
        return [], "pandas not installed. Run: pip install pandas"

    try:
        name = uploaded_file.name.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, dtype=str).fillna("")
        else:
            df = pd.read_excel(uploaded_file, dtype=str).fillna("")
    except Exception as e:
        return [], f"Could not read file: {e}"

    # Build column mapping: header → schema field
    col_to_field: dict[str, str] = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        for field, patterns in _COL_MAP:
            if any(p in col_lower for p in patterns):
                if field not in col_to_field.values():
                    col_to_field[col] = field
                    break

    batch_id = _batch_id()
    contacts: list[dict] = []

    for _, row in df.iterrows():
        c = dict(CONTACT_SCHEMA)
        c["contact_id"]      = _short_uuid()
        c["import_batch"]    = batch_id
        c["category_type"]   = category_type
        c["extraction_mode"] = "rules"
        c["confidence"]      = 70

        for col, field in col_to_field.items():
            val = str(row.get(col, "")).strip()
            if val and not c.get(field):
                c[field] = val

        # Only keep rows that have at least one contact identifier
        if c["company_name"] or c["person_name"] or c["mobile1"] or c["email1"]:
            contacts.append(c)

    return contacts, ""


def _parse_pdf(uploaded_file) -> tuple[str, str]:
    """Extract text from PDF using pdfplumber. Returns (text, warning)."""
    try:
        import pdfplumber
    except ImportError:
        return "", "pdfplumber not installed (PDF text extraction unavailable). Run: pip install pdfplumber"

    try:
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            pages_text = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return "\n".join(pages_text), ""
    except Exception as e:
        return "", f"PDF parsing error: {e}"


def _parse_image(uploaded_file) -> tuple[str, str]:
    """Extract text from image using Pillow + pytesseract. Returns (text, warning)."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return "", "Pillow/pytesseract not installed (image OCR unavailable). Run: pip install Pillow pytesseract"

    try:
        img  = Image.open(io.BytesIO(uploaded_file.read()))
        text = pytesseract.image_to_string(img)
        return text, ""
    except Exception as e:
        return "", f"Image OCR error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# AI EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_contacts_ai(raw_text: str, category_type: str) -> tuple[list[dict], str]:
    """
    Send raw_text to AI fallback engine for structured JSON extraction.

    Returns:
      (contacts, extraction_mode)
      extraction_mode: "ai" on success, "rules" if AI failed/unavailable
    """
    if not raw_text.strip():
        return [], "rules"

    prompt = _AI_PROMPT_TMPL.format(
        category_type=category_type,
        text=raw_text[:6000],
    )

    try:
        from ai_fallback_engine import ask_with_fallback
        result = ask_with_fallback(prompt, context="")
        if result.get("error") == "all_failed":
            return [], "rules"
        answer = result.get("answer", "")
        contacts = _parse_ai_json(answer, category_type)
        if contacts:
            return contacts, "ai"
    except Exception:
        pass

    return [], "rules"


def _parse_ai_json(raw_answer: str, category_type: str) -> list[dict]:
    """Parse the JSON array from AI response. Returns list of contact dicts."""
    # Strip markdown code fences if present
    text = raw_answer.strip()
    if "```" in text:
        text = re.sub(r"```[a-z]*\n?", "", text).replace("```", "").strip()

    # Find the JSON array
    start = text.find("[")
    end   = text.rfind("]")
    if start == -1 or end == -1:
        return []

    try:
        arr = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []

    if not isinstance(arr, list):
        return []

    batch_id = _batch_id()
    contacts: list[dict] = []

    for item in arr:
        if not isinstance(item, dict):
            continue
        c = dict(CONTACT_SCHEMA)
        c["contact_id"]      = _short_uuid()
        c["import_batch"]    = batch_id
        c["category_type"]   = category_type
        c["extraction_mode"] = "ai"
        c["confidence"]      = 85

        for key in ("company_name", "person_name", "mobile1", "mobile2",
                    "email1", "address", "city", "state", "pincode",
                    "gstin", "pan", "website", "notes"):
            val = str(item.get(key, "")).strip()
            if val:
                c[key] = val

        if c["company_name"] or c["person_name"] or c["mobile1"] or c["email1"]:
            contacts.append(c)

    return contacts


# ══════════════════════════════════════════════════════════════════════════════
# RULES-BASED EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_contacts_rules(raw_text: str, category_type: str) -> list[dict]:
    """
    Deterministic regex-based extraction from raw text.
    Groups patterns per paragraph/block and assembles contact dicts.
    """
    if not raw_text.strip():
        return []

    batch_id = _batch_id()

    # Split into blocks (double-newline or section breaks)
    blocks = re.split(r'\n{2,}', raw_text.strip())

    contacts: list[dict] = []
    seen_mobiles: set[str] = set()

    for block in blocks:
        if len(block.strip()) < 5:
            continue

        mobiles  = _RE_MOBILE.findall(block)
        emails   = _RE_EMAIL.findall(block)
        gstins   = _RE_GSTIN.findall(block)
        pans     = _RE_PAN.findall(block)
        pincodes = _RE_PINCODE.findall(block)

        # Skip blocks with no identifiable contact data
        if not (mobiles or emails or gstins):
            continue

        # Avoid complete duplicates
        primary_mobile = mobiles[0] if mobiles else ""
        if primary_mobile and primary_mobile in seen_mobiles:
            continue
        if primary_mobile:
            seen_mobiles.add(primary_mobile)

        c = dict(CONTACT_SCHEMA)
        c["contact_id"]      = _short_uuid()
        c["import_batch"]    = batch_id
        c["category_type"]   = category_type
        c["extraction_mode"] = "rules"
        c["confidence"]      = 50
        c["notes"]           = block[:200].replace("\n", " ").strip()

        if mobiles:
            c["mobile1"] = mobiles[0]
            if len(mobiles) > 1:
                c["mobile2"] = mobiles[1]
        if emails:
            c["email1"] = emails[0]
        if gstins:
            c["gstin"] = gstins[0]
        if pans:
            c["pan"] = pans[0]
        if pincodes:
            c["pincode"] = pincodes[0]

        contacts.append(c)

    # If no blocks yielded contacts, try whole-text extraction as single record
    if not contacts:
        mobiles = _RE_MOBILE.findall(raw_text)
        emails  = _RE_EMAIL.findall(raw_text)
        if mobiles or emails:
            c = dict(CONTACT_SCHEMA)
            c["contact_id"]      = _short_uuid()
            c["import_batch"]    = batch_id
            c["category_type"]   = category_type
            c["extraction_mode"] = "rules"
            c["confidence"]      = 40
            c["notes"]           = raw_text[:200].replace("\n", " ").strip()
            if mobiles:
                c["mobile1"] = mobiles[0]
            if emails:
                c["email1"] = emails[0]
            contacts.append(c)

    return contacts


# ══════════════════════════════════════════════════════════════════════════════
# DUPLICATE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def check_duplicates(new_contacts: list[dict]) -> list[dict]:
    """
    Compare new contacts against SQLite contacts table (fallback: tbl_contacts.json).
    Sets duplicate_status: 'new' / 'possible_duplicate' / 'confirmed_dup'.
    """
    # Try SQLite first
    ex_mobiles: set[str] = set()
    ex_emails: set[str] = set()
    ex_gstins: set[str] = set()

    try:
        from database import get_all_contacts
        existing = get_all_contacts(active_only=False)
        for r in existing:
            m = (r.get("mobile1") or "").strip()
            if m:
                ex_mobiles.add(m)
            e = (r.get("email") or "").strip().lower()
            if e:
                ex_emails.add(e)
            g = (r.get("gstin") or "").strip()
            if g:
                ex_gstins.add(g)
    except Exception:
        # Fallback to JSON
        try:
            existing = NormalizedTables.get_contacts()
            for r in existing:
                m = (r.get("mobile1") or "").strip()
                if m:
                    ex_mobiles.add(m)
                e = (r.get("email1") or r.get("email") or "").strip().lower()
                if e:
                    ex_emails.add(e)
                g = (r.get("gstin") or "").strip()
                if g:
                    ex_gstins.add(g)
        except Exception:
            pass

    result: list[dict] = []
    for c in new_contacts:
        m  = c.get("mobile1", "").strip()
        e  = c.get("email1",  "").strip().lower()
        g  = c.get("gstin",   "").strip()

        match_count = sum([
            bool(m and m in ex_mobiles),
            bool(e and e in ex_emails),
            bool(g and g in ex_gstins),
        ])

        if match_count >= 2:
            c["duplicate_status"] = "confirmed_dup"
        elif match_count == 1:
            c["duplicate_status"] = "possible_duplicate"
        else:
            c["duplicate_status"] = "new"

        result.append(c)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# SAVE TO DESTINATION
# ══════════════════════════════════════════════════════════════════════════════

def save_contacts(contacts: list[dict], destination: str,
                  source_file: str = "") -> dict:
    """
    Route contacts to the correct destination.
    Logs batch to tbl_import_history.json.
    Returns {"saved": N, "errors": [...]}.
    """
    if not contacts:
        return {"saved": 0, "errors": ["No contacts to save."]}

    saved  = 0
    errors: list[str] = []

    # Tag destination + source_file on all contacts
    for c in contacts:
        c["destination"]  = destination
        c["source_file"]  = source_file

    if destination == "Export Only (No Save)":
        return {"saved": len(contacts), "errors": []}

    elif destination == "CRM — Tasks (Follow-Up)":
        saved, errors = _save_to_crm_tasks(contacts)

    elif destination == "CRM — Activity Log":
        saved, errors = _save_to_crm_activity(contacts)

    elif destination in ("Directory — Companies", "Directory — Persons"):
        saved, errors = _save_to_directory(contacts, destination)

    else:
        # Port Contacts / Govt Contacts / Logistics Contacts → SQLite contacts table
        saved, errors = _save_to_sqlite_contacts(contacts)

    # Log to import history
    _log_batch(contacts, destination, source_file, saved, errors)

    return {"saved": saved, "errors": errors}


def _save_to_crm_tasks(contacts: list[dict]) -> tuple[int, list]:
    try:
        from crm_engine import add_task
    except ImportError:
        return 0, ["crm_engine not available."]

    saved  = 0
    errors = []
    today  = datetime.date.today()
    due    = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    for c in contacts:
        client_name = c.get("company_name") or c.get("person_name") or "Unknown"
        note = f"Auto-imported | Category: {c.get('category_type','')} | Mobile: {c.get('mobile1','')} | Email: {c.get('email1','')}"
        try:
            add_task(
                client_name=client_name,
                task_type="Call",
                due_date_str=due,
                priority="Medium",
                note=note,
                automated=True,
            )
            saved += 1
        except Exception as e:
            errors.append(f"{client_name}: {e}")

    return saved, errors


def _save_to_crm_activity(contacts: list[dict]) -> tuple[int, list]:
    try:
        from crm_engine import add_activity
    except ImportError:
        return 0, ["crm_engine.add_activity not available."]

    saved  = 0
    errors = []
    for c in contacts:
        client_name = c.get("company_name") or c.get("person_name") or "Unknown"
        note = f"Contact imported via importer | {c.get('category_type','')} | {c.get('mobile1','')} | {c.get('email1','')}"
        try:
            add_activity(client_name=client_name, activity_type="Import", note=note, automated=True)
            saved += 1
        except Exception as e:
            errors.append(f"{client_name}: {e}")

    return saved, errors


def _save_to_directory(contacts: list[dict], destination: str) -> tuple[int, list]:
    """Append contact records to tbl_dir_orgs.json (Companies) or tbl_contacts.json (Persons)."""
    try:
        existing = NormalizedTables.get_contacts()
    except Exception:
        existing = []

    for c in contacts:
        existing.append(c)

    try:
        NormalizedTables.save_contacts(existing)
        return len(contacts), []
    except Exception as e:
        return 0, [str(e)]


def _save_to_sqlite_contacts(contacts: list[dict]) -> tuple[int, list]:
    """Save contacts to SQLite contacts table. Falls back to JSON on error."""
    try:
        from database import upsert_contact
        saved = 0
        errors = []
        for c in contacts:
            try:
                row = {
                    "name": c.get("person_name") or c.get("company_name") or "Unknown",
                    "company_name": c.get("company_name", ""),
                    "contact_type": "prospect",
                    "category": c.get("category_type", ""),
                    "buyer_seller_tag": c.get("buyer_seller_tag", "unknown"),
                    "city": c.get("city", ""),
                    "state": c.get("state", ""),
                    "address": c.get("address", ""),
                    "pincode": c.get("pincode", ""),
                    "mobile1": c.get("mobile1", ""),
                    "mobile2": c.get("mobile2", ""),
                    "email": c.get("email1", ""),
                    "gstin": c.get("gstin", ""),
                    "pan": c.get("pan", ""),
                    "source": c.get("source_file", "importer"),
                    "notes": c.get("notes", ""),
                    "is_active": 1,
                }
                upsert_contact(row)
                saved += 1
            except Exception as e:
                errors.append(f"{c.get('person_name', '?')}: {e}")
        return saved, errors
    except ImportError:
        return _save_to_tbl_contacts_json(contacts)


def _save_to_tbl_contacts_json(contacts: list[dict]) -> tuple[int, list]:
    """Fallback: save to tbl_contacts.json."""
    try:
        existing = NormalizedTables.get_contacts()
    except Exception:
        existing = []

    for c in contacts:
        existing.append(c)

    try:
        NormalizedTables.save_contacts(existing)
        return len(contacts), []
    except Exception as e:
        return 0, [str(e)]


def _log_batch(contacts: list[dict], destination: str,
               source_file: str, saved: int, errors: list) -> None:
    """Append a batch summary record to tbl_import_history.json."""
    try:
        history = NormalizedTables.get_import_history()
    except Exception:
        history = []

    batch_ids = list({c.get("import_batch", "") for c in contacts if c.get("import_batch")})
    batch_id  = batch_ids[0] if batch_ids else _batch_id()

    record = {
        "batch_id":      batch_id,
        "timestamp":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST"),
        "source_file":   source_file,
        "category_type": contacts[0].get("category_type", "") if contacts else "",
        "extraction_mode": contacts[0].get("extraction_mode", "") if contacts else "",
        "total":         len(contacts),
        "saved":         saved,
        "errors":        len(errors),
        "destination":   destination,
    }

    history.append(record)
    try:
        NormalizedTables.save_import_history(history)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# IMPORT HISTORY
# ══════════════════════════════════════════════════════════════════════════════

def get_import_history() -> list[dict]:
    """Return all batch history records, newest first."""
    try:
        data = NormalizedTables.get_import_history()
        return list(reversed(data))
    except Exception:
        return []


def clear_import_history() -> None:
    """Delete all import history records."""
    try:
        NormalizedTables.save_import_history([])
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _short_uuid() -> str:
    return uuid.uuid4().hex[:8].upper()


def _batch_id() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Wizard-based import API (v6.0)
# ═══════════════════════════════════════════════════════════════════════════════
# New pure-function API for the Import Wizard. Operates on DataFrames and the
# live SQLite DB directly. Independent of the legacy `parse_file` /
# `save_contacts` flow above — kept side-by-side during migration.

import re as _re
from pathlib import Path as _Path
from typing import Iterable as _Iterable
import pandas as _pd


_ALIASES: dict[str, tuple[str, ...]] = {
    "name":    ("name", "party name", "customer name", "supplier name",
                "client name", "contact name", "full name"),
    "company": ("company", "company name", "organisation", "organization",
                "firm"),
    "phone":   ("phone", "mobile", "mobile no", "mobile number",
                "contact", "contact no", "contact number", "whatsapp"),
    "email":   ("email", "email id", "e-mail", "mail id"),
    "gstin":   ("gstin", "gst", "gst no", "gst no.", "gst number",
                "gst_number", "gstin no"),
    "city":    ("city", "town", "location"),
    "state":   ("state", "region"),
    "address": ("address", "addr", "full address"),
    "category": ("category", "type", "party type", "segment"),
    "notes":   ("notes", "remark", "remarks", "comments"),
}


def _norm(s: str) -> str:
    """Lowercase, strip, collapse whitespace and punctuation."""
    return _re.sub(r"[^a-z0-9]+", "", (s or "").strip().lower())


def parse_spreadsheet(path) -> "_pd.DataFrame":
    """Read .xlsx or .csv into a DataFrame. Raises ValueError on anything else."""
    p = _Path(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return _pd.read_csv(p, dtype=str).fillna("")
    if suffix in (".xlsx", ".xls"):
        return _pd.read_excel(p, dtype=str).fillna("")
    raise ValueError(f"Unsupported file type: {suffix} (expected .csv or .xlsx)")


def suggest_column_mapping(source_cols: _Iterable[str],
                           target_schema: _Iterable[str]) -> dict[str, str]:
    """Map target field names to the best source column name.

    Matching order:
      1. Exact match (case-insensitive, punctuation-normalised).
      2. Alias match from _ALIASES.
      3. Substring match (target name appears in source name).

    Returns a dict {target_field: source_col} for fields that matched.
    Target fields with no match are omitted.
    """
    source_list = list(source_cols)
    source_norm = {_norm(c): c for c in source_list}
    result: dict[str, str] = {}

    for target in target_schema:
        target_key = _norm(target)
        if target_key in source_norm:
            result[target] = source_norm[target_key]
            continue
        for alias in _ALIASES.get(target, ()):
            if _norm(alias) in source_norm:
                result[target] = source_norm[_norm(alias)]
                break
        if target in result:
            continue
        for norm_src, orig_src in source_norm.items():
            if target_key and target_key in norm_src:
                result[target] = orig_src
                break
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════════

_GSTIN_RE = _re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}Z[0-9A-Z]{1}$")


def _normalise_phone(raw) -> str:
    """Strip spaces/dashes, keep leading + and digits only."""
    if not raw:
        return ""
    s = str(raw).strip()
    out = "+" if s.startswith("+") else ""
    out += _re.sub(r"\D", "", s)
    return out


def validate_rows(df, target_table: str):
    """Split df into (valid, invalid). Invalid rows carry a `_reason` column."""
    valid_rows: list[dict] = []
    invalid_rows: list[dict] = []

    for _, row in df.iterrows():
        record = {k: ("" if _pd.isna(v) else str(v).strip())
                  for k, v in row.items()}

        reason = None
        if not record.get("name"):
            reason = "missing name"

        if "phone" in record:
            record["phone"] = _normalise_phone(record["phone"])

        gst = record.get("gstin", "").upper()
        if gst and not _GSTIN_RE.match(gst):
            reason = reason or "invalid gstin format"
        if gst:
            record["gstin"] = gst

        if reason:
            record["_reason"] = reason
            invalid_rows.append(record)
        else:
            valid_rows.append(record)

    return (_pd.DataFrame(valid_rows) if valid_rows else _pd.DataFrame(),
            _pd.DataFrame(invalid_rows) if invalid_rows else _pd.DataFrame())


# ═══════════════════════════════════════════════════════════════════════════════
# Dedupe
# ═══════════════════════════════════════════════════════════════════════════════

_PHONE_COL = {
    "customers": "contact",
    "suppliers": "contact",
    "contacts":  "phone",
    "customer_profiles": "whatsapp",
}


def _dedupe_key(name: str, phone: str) -> str:
    return f"{_norm(name)}|{_normalise_phone(phone)}"


def dedupe_against_db(df, target_table: str,
                      strategy: str = "skip",
                      db_path="bitumen_dashboard.db"):
    """Return rows that should be inserted, according to strategy.

    strategy:
      - 'skip'      → drop rows whose (name, phone) already exists.
      - 'overwrite' → keep all rows; caller must issue INSERT OR REPLACE.
      - 'merge'     → same as overwrite for now; merge happens during commit.
    """
    import sqlite3 as _sql
    if df.empty:
        return df

    phone_col = _PHONE_COL.get(target_table, "phone")
    conn = _sql.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT name, {phone_col} FROM {target_table}"
        ).fetchall()
    finally:
        conn.close()
    existing = {_dedupe_key(n or "", p or "") for n, p in rows}

    if strategy in ("overwrite", "merge"):
        return df.copy()

    mask = []
    for _, r in df.iterrows():
        key = _dedupe_key(r.get("name", ""), r.get("phone", ""))
        mask.append(key not in existing)
    return df[_pd.Series(mask, index=df.index)].copy()


# ═══════════════════════════════════════════════════════════════════════════════
# Commit + Revert
# ═══════════════════════════════════════════════════════════════════════════════

_INSERT_MAP: dict[str, dict[str, str]] = {
    "customers":         {"name": "name", "phone": "contact",
                          "city": "city", "state": "state",
                          "gstin": "gstin", "address": "address",
                          "category": "category"},
    "suppliers":         {"name": "name", "phone": "contact",
                          "city": "city", "state": "state",
                          "gstin": "gstin", "category": "category"},
    "contacts":          {"name": "name", "phone": "phone",
                          "city": "city", "state": "state",
                          "email": "email", "category": "category"},
    "customer_profiles": {"name": "name", "company": "company",
                          "phone": "whatsapp", "email": "email",
                          "city": "city", "state": "state",
                          "category": "category", "notes": "notes"},
}


def _now_iso() -> str:
    import datetime as _dt2
    return _dt2.datetime.now(_dt2.timezone(_dt2.timedelta(hours=5, minutes=30)))\
        .strftime("%Y-%m-%dT%H:%M:%S%z")


def commit_import(df, target_table: str,
                  source_file: str,
                  db_path="bitumen_dashboard.db") -> dict:
    """Insert rows and write an import_history row. Single transaction.

    Raises sqlite3.IntegrityError (or other sqlite3 errors) on failure —
    the DB is rolled back and no history row is written.

    Returns {inserted, skipped, errors, import_history_id}.
    """
    import sqlite3 as _sql
    if target_table not in _INSERT_MAP:
        raise ValueError(f"Unknown target table: {target_table}")

    mapping = _INSERT_MAP[target_table]
    # Special case: customer_profiles requires imported_at (NOT NULL), not imported_from
    needs_imported_at = (target_table == "customer_profiles")

    conn = _sql.connect(db_path)
    try:
        conn.execute("BEGIN")
        inserted = 0
        now_iso = _now_iso()
        for _, row in df.iterrows():
            if needs_imported_at:
                cols = ["source_file", "imported_at"]
                vals = [source_file, now_iso]
            else:
                cols = ["imported_from"]
                vals = [source_file]
            for src_key, db_col in mapping.items():
                if src_key in row and row[src_key] not in ("", None):
                    cols.append(db_col)
                    vals.append(row[src_key])
            placeholders = ", ".join(["?"] * len(vals))
            conn.execute(
                f"INSERT INTO {target_table} ({', '.join(cols)}) "
                f"VALUES ({placeholders})",
                vals,
            )
            inserted += 1

        cur = conn.execute(
            "INSERT INTO import_history "
            "(file_name, target_table, rows_inserted, rows_skipped, "
            " rows_errored, imported_at) VALUES (?, ?, ?, ?, ?, ?)",
            (source_file, target_table, inserted, 0, 0, now_iso),
        )
        import_id = cur.lastrowid
        conn.commit()
        return {
            "inserted": inserted,
            "skipped": 0,
            "errors": 0,
            "import_history_id": import_id,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def revert_import(import_history_id: int,
                  db_path="bitumen_dashboard.db") -> int:
    """Delete rows inserted by the given import; mark history reverted.

    Returns the number of rows removed.
    """
    import sqlite3 as _sql
    conn = _sql.connect(db_path)
    try:
        conn.execute("BEGIN")
        row = conn.execute(
            "SELECT file_name, target_table, reverted "
            "FROM import_history WHERE id = ?",
            (import_history_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"import_history id {import_history_id} not found")
        file_name, target_table, already = row
        if already:
            conn.rollback()
            return 0
        # customer_profiles uses source_file instead of imported_from
        col = "source_file" if target_table == "customer_profiles" else "imported_from"
        cur = conn.execute(
            f"DELETE FROM {target_table} WHERE {col} = ?",
            (file_name,),
        )
        removed = cur.rowcount
        conn.execute(
            "UPDATE import_history SET reverted = 1 WHERE id = ?",
            (import_history_id,),
        )
        conn.commit()
        return removed
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
