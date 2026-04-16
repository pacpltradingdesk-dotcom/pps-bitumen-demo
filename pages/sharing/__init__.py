"""Shared helpers for sharing sub-pages (share_center, telegram_dashboard)."""
from __future__ import annotations
import json
from pathlib import Path


def save_json(filepath, data) -> bool:
    """Write data to a JSON file. Returns True on success."""
    try:
        Path(filepath).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False
