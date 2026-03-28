"""
PPS Anantam — Google Sheets Sync Engine v1.0
===============================================
Free gspread + service-account integration for reading/writing
Google Sheets data. Supports scheduled syncs and data linking.

Uses: gspread (free), google-auth (free with service account)

Setup:
  1. Create Google Cloud project (free)
  2. Enable Google Sheets API
  3. Create service account → download JSON key
  4. Share sheet with service account email
"""

import json
import os
import sys
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(__file__))

IST = timezone(timedelta(hours=5, minutes=30))
BASE_DIR = Path(__file__).parent
LINKED_SHEETS_FILE = BASE_DIR / "linked_sheets.json"


class GoogleSheetsEngine:
    """Sync data between Google Sheets and local SQLite."""

    def __init__(self):
        from settings_engine import load_settings
        self.settings = load_settings()
        self._client = None

    def connect(self, service_account_path: str = None) -> tuple:
        """Connect to Google Sheets API using service account.
        Returns (success: bool, message: str)."""
        sa_path = service_account_path or self.settings.get("google_sheets_service_account_path", "")
        if not sa_path or not os.path.exists(sa_path):
            return False, "Service account JSON file not found. Please upload it in Integrations settings."
        try:
            import gspread
            self._client = gspread.service_account(filename=sa_path)
            return True, "Connected to Google Sheets API successfully."
        except ImportError:
            return False, "gspread package not installed. Run: pip install gspread"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def test_connection(self) -> tuple:
        """Test the Google Sheets connection.
        Returns (success: bool, message: str)."""
        ok, msg = self.connect()
        if not ok:
            return ok, msg
        try:
            self._client.list_spreadsheet_files(page_size=1)
            return True, "Connection test passed — API access verified."
        except Exception as e:
            return False, f"Connection test failed: {e}"

    def read_sheet(self, url_or_id: str, worksheet: str = None) -> list:
        """Read a Google Sheet and return list of dicts (rows).
        Returns list[dict] or empty list on error."""
        if not self._client:
            ok, _ = self.connect()
            if not ok:
                return []
        try:
            if url_or_id.startswith("http"):
                spreadsheet = self._client.open_by_url(url_or_id)
            else:
                spreadsheet = self._client.open_by_key(url_or_id)

            ws = spreadsheet.worksheet(worksheet) if worksheet else spreadsheet.sheet1
            return ws.get_all_records()
        except Exception:
            return []

    def sync_sheet_to_json(self, url_or_id: str, output_file: str,
                           worksheet: str = None) -> dict:
        """Sync a Google Sheet to a local JSON file.
        Returns {"success": bool, "rows": int, "message": str}."""
        data = self.read_sheet(url_or_id, worksheet)
        if not data:
            return {"success": False, "rows": 0, "message": "No data read from sheet."}
        try:
            out_path = BASE_DIR / output_file
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return {"success": True, "rows": len(data), "message": f"Synced {len(data)} rows to {output_file}"}
        except Exception as e:
            return {"success": False, "rows": 0, "message": f"Write failed: {e}"}

    def export_to_sheet(self, url_or_id: str, data: list, worksheet: str = "Export") -> dict:
        """Export data (list of dicts) to a Google Sheet worksheet.
        Returns {"success": bool, "rows": int, "message": str}."""
        if not self._client:
            ok, msg = self.connect()
            if not ok:
                return {"success": False, "rows": 0, "message": msg}
        if not data:
            return {"success": False, "rows": 0, "message": "No data to export."}
        try:
            if url_or_id.startswith("http"):
                spreadsheet = self._client.open_by_url(url_or_id)
            else:
                spreadsheet = self._client.open_by_key(url_or_id)

            try:
                ws = spreadsheet.worksheet(worksheet)
            except Exception:
                ws = spreadsheet.add_worksheet(title=worksheet, rows=len(data) + 1, cols=len(data[0]))

            headers = list(data[0].keys())
            rows = [headers] + [[row.get(h, "") for h in headers] for row in data]
            ws.clear()
            ws.update(range_name="A1", values=rows)
            return {"success": True, "rows": len(data), "message": f"Exported {len(data)} rows to '{worksheet}'"}
        except Exception as e:
            return {"success": False, "rows": 0, "message": f"Export failed: {e}"}

    # ── Linked Sheets Management ─────────────────────────────────────────────

    def get_linked_sheets(self) -> list:
        """Get all linked sheet configurations."""
        if LINKED_SHEETS_FILE.exists():
            try:
                with open(LINKED_SHEETS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def add_sheet_link(self, name: str, url: str, output_file: str,
                       sync_mode: str = "manual", refresh_minutes: int = 60,
                       worksheet: str = None) -> int:
        """Add a new linked sheet. Returns the link index."""
        sheets = self.get_linked_sheets()
        link = {
            "id": len(sheets) + 1,
            "name": name,
            "url": url,
            "output_file": output_file,
            "worksheet": worksheet,
            "sync_mode": sync_mode,
            "refresh_minutes": refresh_minutes,
            "last_sync": None,
            "last_status": "never",
            "rows_synced": 0,
            "is_active": True,
            "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
        }
        sheets.append(link)
        self._save_linked_sheets(sheets)
        return link["id"]

    def remove_sheet_link(self, link_id: int):
        """Deactivate a linked sheet by ID."""
        sheets = self.get_linked_sheets()
        for s in sheets:
            if s.get("id") == link_id:
                s["is_active"] = False
                break
        self._save_linked_sheets(sheets)

    def run_scheduled_syncs(self) -> dict:
        """Run all active auto-sync sheets that are due. Returns summary."""
        sheets = self.get_linked_sheets()
        synced = 0
        failed = 0
        now = datetime.now(IST)

        for s in sheets:
            if not s.get("is_active") or s.get("sync_mode") != "auto":
                continue
            last = s.get("last_sync")
            if last:
                try:
                    last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
                    if (now - last_dt).total_seconds() < s.get("refresh_minutes", 60) * 60:
                        continue
                except Exception:
                    pass

            result = self.sync_sheet_to_json(s["url"], s["output_file"], s.get("worksheet"))
            s["last_sync"] = now.strftime("%Y-%m-%d %H:%M:%S")
            if result["success"]:
                s["last_status"] = "success"
                s["rows_synced"] = result["rows"]
                synced += 1
            else:
                s["last_status"] = f"failed: {result['message']}"
                failed += 1

        self._save_linked_sheets(sheets)
        return {"synced": synced, "failed": failed, "total_active": sum(1 for s in sheets if s.get("is_active"))}

    def _save_linked_sheets(self, sheets: list):
        with open(LINKED_SHEETS_FILE, "w", encoding="utf-8") as f:
            json.dump(sheets, f, indent=2, ensure_ascii=False)


# ── Background Scheduler ─────────────────────────────────────────────────────

_sheets_scheduler_thread = None
_sheets_scheduler_running = False


def start_sheets_scheduler():
    """Start background scheduler for auto-syncing linked sheets."""
    global _sheets_scheduler_thread, _sheets_scheduler_running
    if _sheets_scheduler_running:
        return

    import time

    def _loop():
        global _sheets_scheduler_running
        _sheets_scheduler_running = True
        while _sheets_scheduler_running:
            try:
                engine = GoogleSheetsEngine()
                engine.run_scheduled_syncs()
            except Exception:
                pass
            time.sleep(300)  # Check every 5 minutes

    _sheets_scheduler_thread = threading.Thread(target=_loop, daemon=True, name="SheetsScheduler")
    _sheets_scheduler_thread.start()


def stop_sheets_scheduler():
    global _sheets_scheduler_running
    _sheets_scheduler_running = False
