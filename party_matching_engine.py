"""
Party Matching Engine — PPS Anantams Document Management
========================================================

3-tier party matching: GSTIN (exact) → Name (exact, case-insensitive) → Fuzzy (>85%).
Missing master data detection for incomplete records.
Uses only stdlib difflib — no external dependencies.
"""

from __future__ import annotations

import difflib
from typing import Optional

from database import (
    get_connection,
    _rows_to_list,
)

# ── Required fields for complete master data ──────────────────────────────

_REQUIRED_FIELDS_SUPPLIER = {"name", "gstin", "pan", "city", "state", "contact"}
_REQUIRED_FIELDS_CUSTOMER = {"name", "gstin", "address", "city", "state", "contact"}
_REQUIRED_FIELDS_TRANSPORTER = {"name", "contact", "city"}

FUZZY_THRESHOLD = 0.85  # 85% similarity


# ═══════════════════════════════════════════════════════════════════════════
# PARTY MATCHER
# ═══════════════════════════════════════════════════════════════════════════

class PartyMatcher:
    """3-tier party matching engine for suppliers and customers."""

    def match_party(
        self,
        name: str | None = None,
        gstin: str | None = None,
        party_type: str = "supplier",
    ) -> dict:
        """
        Match a party using 3-tier strategy:
          1. GSTIN exact match (confidence: 100%)
          2. Name exact match, case-insensitive (confidence: 95%)
          3. Fuzzy name match >85% (confidence: 85-94%)

        Returns:
            {match_type: "gstin"|"name"|"fuzzy"|"none",
             confidence: 0-100,
             matched_record: dict|None,
             missing_fields: list[str]}
        """
        if party_type == "supplier":
            table = "suppliers"
        elif party_type == "transporter":
            table = "transporters"
        else:
            table = "customers"

        # Tier 1: GSTIN exact match
        if gstin and gstin.strip():
            gstin_clean = gstin.strip().upper()
            record = self._find_by_gstin(table, gstin_clean)
            if record:
                return {
                    "match_type": "gstin",
                    "confidence": 100,
                    "matched_record": record,
                    "missing_fields": self._check_missing(record, party_type),
                }

        # Tier 2: Name exact match (case-insensitive)
        if name and name.strip():
            name_clean = name.strip()
            record = self._find_by_name_exact(table, name_clean)
            if record:
                return {
                    "match_type": "name",
                    "confidence": 95,
                    "matched_record": record,
                    "missing_fields": self._check_missing(record, party_type),
                }

            # Tier 3: Fuzzy name match
            match = self._find_by_name_fuzzy(table, name_clean)
            if match:
                return {
                    "match_type": "fuzzy",
                    "confidence": match["confidence"],
                    "matched_record": match["record"],
                    "missing_fields": self._check_missing(match["record"], party_type),
                }

        return {
            "match_type": "none",
            "confidence": 0,
            "matched_record": None,
            "missing_fields": [],
        }

    def find_missing_master_data(self, party_type: str = "supplier") -> list[dict]:
        """
        Return all parties with incomplete master data.
        Checks for missing GSTIN, PAN, address, city, state, contact.
        """
        if party_type == "supplier":
            table = "suppliers"
        elif party_type == "transporter":
            table = "transporters"
        else:
            table = "customers"
        required = (
            _REQUIRED_FIELDS_SUPPLIER if party_type == "supplier"
            else _REQUIRED_FIELDS_TRANSPORTER if party_type == "transporter"
            else _REQUIRED_FIELDS_CUSTOMER
        )

        with get_connection() as conn:
            rows = conn.execute(f"SELECT * FROM {table} WHERE is_active = 1").fetchall()
            records = _rows_to_list(rows)

        incomplete = []
        for rec in records:
            missing = []
            for field in required:
                val = rec.get(field)
                if not val or (isinstance(val, str) and not val.strip()):
                    missing.append(field)
            if missing:
                incomplete.append({
                    "id": rec["id"],
                    "name": rec.get("name", "UNKNOWN"),
                    "party_type": party_type,
                    "missing_fields": missing,
                    "completeness_pct": round(
                        (len(required) - len(missing)) / len(required) * 100
                    ),
                })
        return sorted(incomplete, key=lambda x: x["completeness_pct"])

    def suggest_merge_duplicates(self, party_type: str = "supplier") -> list[dict]:
        """
        Find potential duplicate parties by fuzzy name match.
        Returns pairs of records that may be duplicates.
        """
        if party_type == "supplier":
            table = "suppliers"
        elif party_type == "transporter":
            table = "transporters"
        else:
            table = "customers"

        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT id, name, gstin FROM {table} WHERE is_active = 1"
            ).fetchall()
            records = _rows_to_list(rows)

        duplicates = []
        seen = set()
        for i, rec_a in enumerate(records):
            for rec_b in records[i + 1 :]:
                pair_key = (min(rec_a["id"], rec_b["id"]), max(rec_a["id"], rec_b["id"]))
                if pair_key in seen:
                    continue
                name_a = (rec_a.get("name") or "").upper()
                name_b = (rec_b.get("name") or "").upper()
                if not name_a or not name_b:
                    continue
                ratio = difflib.SequenceMatcher(None, name_a, name_b).ratio()
                if ratio >= FUZZY_THRESHOLD:
                    seen.add(pair_key)
                    duplicates.append({
                        "record_a": rec_a,
                        "record_b": rec_b,
                        "similarity_pct": round(ratio * 100),
                        "same_gstin": (
                            bool(rec_a.get("gstin"))
                            and rec_a.get("gstin") == rec_b.get("gstin")
                        ),
                    })
        return sorted(duplicates, key=lambda x: -x["similarity_pct"])

    # ── Private helpers ────────────────────────────────────────────────────

    def _find_by_gstin(self, table: str, gstin: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE UPPER(gstin) = ? AND is_active = 1",
                (gstin.upper(),),
            ).fetchone()
            return dict(row) if row else None

    def _find_by_name_exact(self, table: str, name: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE UPPER(name) = ? AND is_active = 1",
                (name.upper(),),
            ).fetchone()
            return dict(row) if row else None

    def _find_by_name_fuzzy(self, table: str, name: str) -> dict | None:
        """Find best fuzzy match above threshold."""
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE is_active = 1"
            ).fetchall()
            records = _rows_to_list(rows)

        best_ratio = 0.0
        best_record = None
        name_upper = name.upper()

        for rec in records:
            rec_name = (rec.get("name") or "").upper()
            if not rec_name:
                continue
            ratio = difflib.SequenceMatcher(None, name_upper, rec_name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_record = rec

        if best_ratio >= FUZZY_THRESHOLD and best_record:
            return {
                "record": best_record,
                "confidence": round(best_ratio * 100),
            }
        return None

    def _check_missing(self, record: dict, party_type: str) -> list[str]:
        """Check which required fields are missing from a record."""
        required = (
            _REQUIRED_FIELDS_SUPPLIER if party_type == "supplier"
            else _REQUIRED_FIELDS_TRANSPORTER if party_type == "transporter"
            else _REQUIRED_FIELDS_CUSTOMER
        )
        missing = []
        for field in required:
            val = record.get(field)
            if not val or (isinstance(val, str) and not val.strip()):
                missing.append(field)
        return missing
