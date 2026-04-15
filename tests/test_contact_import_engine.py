"""Unit tests for contact_import_engine — Phase 1."""
from __future__ import annotations
import pandas as pd
import pytest
from pathlib import Path

from contact_import_engine import (
    parse_spreadsheet,
    suggest_column_mapping,
)


# ── parse_spreadsheet ──────────────────────────────────────────────

def test_parse_csv(tmp_path: Path):
    csv = tmp_path / "sample.csv"
    csv.write_text("name,city,phone\nAsha,Pune,9876543210\n",
                   encoding="utf-8")
    df = parse_spreadsheet(csv)
    assert list(df.columns) == ["name", "city", "phone"]
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Asha"


def test_parse_xlsx(tmp_path: Path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["name", "city", "phone"])
    ws.append(["Asha", "Pune", "9876543210"])
    xlsx = tmp_path / "sample.xlsx"
    wb.save(xlsx)

    df = parse_spreadsheet(xlsx)
    assert list(df.columns) == ["name", "city", "phone"]
    assert df.iloc[0]["phone"] == "9876543210" or df.iloc[0]["phone"] == 9876543210


def test_parse_rejects_unsupported(tmp_path: Path):
    txt = tmp_path / "not-a-sheet.txt"
    txt.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_spreadsheet(txt)


# ── suggest_column_mapping ─────────────────────────────────────────

def test_mapping_direct_match():
    m = suggest_column_mapping(
        ["name", "city", "phone"],
        target_schema=["name", "city", "phone", "email"],
    )
    assert m == {"name": "name", "city": "city", "phone": "phone"}


def test_mapping_alias_party_name():
    m = suggest_column_mapping(
        ["Party Name", "Mobile", "GST No."],
        target_schema=["name", "phone", "gstin"],
    )
    assert m == {"name": "Party Name", "phone": "Mobile", "gstin": "GST No."}


def test_mapping_case_insensitive():
    m = suggest_column_mapping(["NAME", "CITY"], target_schema=["name", "city"])
    assert m == {"name": "NAME", "city": "CITY"}


def test_mapping_missing_target_omitted():
    m = suggest_column_mapping(["name"], target_schema=["name", "phone"])
    assert "phone" not in m


# ── validate_rows ──────────────────────────────────────────────────

from contact_import_engine import validate_rows, dedupe_against_db


def test_validate_keeps_good_rows():
    df = pd.DataFrame([
        {"name": "Asha", "phone": "9876543210", "gstin": ""},
        {"name": "Bhavesh", "phone": "+919876543211", "gstin": "24AAHCV1611L2ZD"},
    ])
    valid, invalid = validate_rows(df, "customers")
    assert len(valid) == 2
    assert len(invalid) == 0


def test_validate_drops_missing_name():
    df = pd.DataFrame([
        {"name": "", "phone": "9876543210"},
        {"name": "Asha", "phone": "9876543210"},
    ])
    valid, invalid = validate_rows(df, "customers")
    assert len(valid) == 1
    assert len(invalid) == 1
    assert invalid.iloc[0]["_reason"] == "missing name"


def test_validate_flags_bad_gstin():
    df = pd.DataFrame([
        {"name": "Asha", "phone": "9876543210", "gstin": "NOT-A-GSTIN"},
    ])
    valid, invalid = validate_rows(df, "customers")
    assert len(valid) == 0
    assert "gstin" in invalid.iloc[0]["_reason"].lower()


def test_validate_normalises_phone():
    df = pd.DataFrame([{"name": "Asha", "phone": "+91 98765-43210"}])
    valid, _ = validate_rows(df, "customers")
    assert valid.iloc[0]["phone"] == "+919876543210"


# ── dedupe_against_db ──────────────────────────────────────────────

def test_dedupe_skip_exact_match(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "INSERT INTO customers(name, contact) VALUES(?, ?)",
        ("Asha", "+919876543210"))
    conn.commit()
    conn.close()

    df = pd.DataFrame([
        {"name": "Asha", "phone": "+919876543210"},
        {"name": "Bhavesh", "phone": "+919876543211"},
    ])
    fresh = dedupe_against_db(df, "customers", strategy="skip", db_path=tmp_db)
    assert len(fresh) == 1
    assert fresh.iloc[0]["name"] == "Bhavesh"


def test_dedupe_whitespace_insensitive(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.execute("INSERT INTO customers(name, contact) VALUES(?, ?)",
                 ("Asha  Gupta", "+919876543210"))
    conn.commit()
    conn.close()

    df = pd.DataFrame([{"name": "asha gupta", "phone": "+919876543210"}])
    fresh = dedupe_against_db(df, "customers", strategy="skip", db_path=tmp_db)
    assert len(fresh) == 0
