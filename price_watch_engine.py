"""
Price Watch Engine — Auto-Detect Price Changes & Broadcast
============================================================
Monitors live_prices.json for significant changes and automatically
broadcasts updates to all buyer contacts via WhatsApp and Email.

PPS Anantam Capital Pvt Ltd — CRM Automation v1.0
"""

from __future__ import annotations

import datetime
import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("price_watch_engine")

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None


def _slog(action: str, details: str = "", level: str = "info"):
    """Structured log to both stdlib logger and dashboard_log."""
    getattr(logger, level)(f"{action}: {details}" if details else action)
    if _dlog:
        getattr(_dlog, level)("price_watch_engine", action, details)


BASE = Path(__file__).parent
LIVE_PRICES_FILE = BASE / "live_prices.json"
PRICE_CACHE_FILE = BASE / "price_watch_cache.json"


# ══════════════════════════════════════════════════════════════════════════════
# PRICE WATCH ENGINE
# ══════════════════════════════════════════════════════════════════════════════


class PriceWatchEngine:
    """Monitors bitumen prices and broadcasts significant changes."""

    def __init__(self):
        self._settings = self._load_settings()

    def _load_settings(self) -> dict:
        try:
            from settings_engine import load_settings
            return load_settings()
        except Exception:
            return {}

    @property
    def threshold_pct(self) -> float:
        return self._settings.get("price_change_threshold_pct", 2.0)

    @property
    def channels(self) -> list:
        return self._settings.get("price_broadcast_channels", ["whatsapp", "email"])

    def load_current_prices(self) -> dict:
        """Load current prices from live_prices.json."""
        if not LIVE_PRICES_FILE.exists():
            return {}
        try:
            with open(LIVE_PRICES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def load_cached_prices(self) -> dict:
        """Load previously cached prices for comparison."""
        if not PRICE_CACHE_FILE.exists():
            return {}
        try:
            with open(PRICE_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_cache(self, prices: dict) -> None:
        """Save current prices as cache for next comparison."""
        try:
            with open(PRICE_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(prices, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save price cache: {e}")

    def detect_changes(self) -> list[dict]:
        """
        Compare current prices vs cached. Return significant changes.

        Returns list of: {key, grade, city, old_value, new_value, change_pct, direction}
        """
        current = self.load_current_prices()
        cached = self.load_cached_prices()

        if not current:
            return []

        # If no cache, save current and return (first run)
        if not cached:
            self.save_cache(current)
            return []

        changes = []
        threshold = self.threshold_pct

        # Handle different price data structures
        price_items = self._extract_price_items(current)
        cached_items = self._extract_price_items(cached)

        for key, new_val in price_items.items():
            old_val = cached_items.get(key)
            if old_val is None or old_val == 0:
                continue

            try:
                new_f = float(new_val)
                old_f = float(old_val)
            except (ValueError, TypeError):
                continue

            if old_f == 0:
                continue

            change_pct = ((new_f - old_f) / old_f) * 100

            if abs(change_pct) >= threshold:
                # Parse key to extract grade and city
                parts = key.split("_", 1)
                grade = parts[0] if parts else key
                city = parts[1] if len(parts) > 1 else ""

                changes.append({
                    "key": key,
                    "grade": grade,
                    "city": city,
                    "old_value": old_f,
                    "new_value": new_f,
                    "change_pct": round(change_pct, 2),
                    "direction": "up" if change_pct > 0 else "down",
                })

        return changes

    def _extract_price_items(self, data: dict) -> dict:
        """
        Flatten price data into {key: value} pairs.
        Handles nested structures like {grade: {city: price}}.
        """
        items = {}

        for key, val in data.items():
            if isinstance(val, (int, float)):
                items[key] = val
            elif isinstance(val, dict):
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, (int, float)):
                        items[f"{key}_{sub_key}"] = sub_val
                    elif isinstance(sub_val, dict):
                        price = sub_val.get("price", sub_val.get("value"))
                        if price is not None:
                            items[f"{key}_{sub_key}"] = price
            elif isinstance(val, str):
                try:
                    items[key] = float(val.replace(",", ""))
                except ValueError:
                    pass

        return items

    def broadcast_price_update(self, changes: list[dict]) -> dict:
        """
        Broadcast price changes to all buyer contacts.

        Returns: {total_contacts, sent_whatsapp, sent_email, failed, changes_count}
        """
        if not changes:
            return {"total_contacts": 0, "sent_whatsapp": 0,
                    "sent_email": 0, "failed": 0, "changes_count": 0}

        try:
            from database import get_contacts_for_broadcast
        except ImportError:
            return {"error": "database module not available"}

        # Get buyer contacts (primarily interested in price updates)
        contacts = get_contacts_for_broadcast()
        buyer_contacts = [c for c in contacts
                          if c.get("buyer_seller_tag") in ("buyer", "both", "unknown")]

        stats = {"total_contacts": len(buyer_contacts), "sent_whatsapp": 0,
                 "sent_email": 0, "failed": 0, "changes_count": len(changes)}

        for contact in buyer_contacts:
            name = contact.get("name", "")
            channel = self._pick_channel(contact)

            try:
                if channel == "whatsapp":
                    self._send_wa_price_update(contact, changes)
                    stats["sent_whatsapp"] += 1
                elif channel == "email":
                    self._send_email_price_update(contact, changes)
                    stats["sent_email"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"Price broadcast to {name}: {e}")

        # Log changes to database
        self._log_price_changes(changes)

        return stats

    def _pick_channel(self, contact: dict) -> str:
        """Pick communication channel for price broadcast."""
        wa_opted = contact.get("whatsapp_opted_in", 0)
        mobile = (contact.get("mobile1") or "").strip()
        email = (contact.get("email") or "").strip()
        email_opted = contact.get("email_opted_in", 1)

        if "whatsapp" in self.channels and wa_opted and mobile:
            return "whatsapp"
        elif "email" in self.channels and email_opted and email:
            return "email"
        return "skip"

    def _send_wa_price_update(self, contact: dict, changes: list[dict]) -> None:
        """Send price update via WhatsApp."""
        from whatsapp_engine import WhatsAppEngine
        wa = WhatsAppEngine()

        name = contact.get("name", "")
        # Send update for the most significant change
        change = max(changes, key=lambda c: abs(c.get("change_pct", 0)))

        try:
            from communication_engine import generate_price_update_message
            msg = generate_price_update_message(
                name=name,
                grade=change["grade"],
                old_price=change["old_value"],
                new_price=change["new_value"],
                city=change.get("city", ""),
                channel="whatsapp",
            )
        except Exception:
            msg = (f"Price Update: {change['grade']} changed "
                   f"{change['change_pct']:+.1f}% to {change['new_value']}")

        wa.queue_message(
            to_number=contact.get("mobile1", ""),
            template_name="price_update_v1",
            session_text=msg,
            message_type="template",
            auto_send=True,
        )

    def _send_email_price_update(self, contact: dict, changes: list[dict]) -> None:
        """Send price update via email."""
        name = contact.get("name", "")
        email_addr = contact.get("email", "")

        try:
            from communication_engine import CommunicationHub
            hub = CommunicationHub()
            prices = [{"grade": c["grade"], "old": c["old_value"],
                       "new": c["new_value"], "city": c.get("city", "")}
                      for c in changes]
            result = hub.email_price_update(name, prices)
            subject = result["subject"]
            body = result["body"]
        except Exception:
            subject = "Bitumen Price Update"
            body = f"Dear {name},\n\nPrice changes detected:\n"
            for c in changes:
                body += (f"  {c['grade']}: {c['old_value']} -> {c['new_value']} "
                         f"({c['change_pct']:+.1f}%)\n")

        try:
            from email_engine import queue_email
            queue_email(to=email_addr, subject=subject, body=body,
                        email_type="price_update")
        except Exception as e:
            logger.error(f"Email price update to {email_addr}: {e}")
            raise

    def _log_price_changes(self, changes: list[dict]) -> None:
        """Log price changes to database."""
        try:
            from database import insert_price_update_log
            for c in changes:
                insert_price_update_log(
                    price_key=c["key"],
                    old_value=c["old_value"],
                    new_value=c["new_value"],
                    change_pct=c["change_pct"],
                    broadcast_sent=True,
                )
        except Exception as e:
            logger.error(f"Failed to log price changes: {e}")

    def run_check(self) -> dict:
        """
        Single cycle: detect changes -> log -> broadcast if significant.

        Returns: {changes_found, broadcast_result}
        """
        changes = self.detect_changes()

        if not changes:
            return {"changes_found": 0, "broadcast_result": None}

        logger.info(f"Detected {len(changes)} significant price changes")

        # Update cache with current prices
        current = self.load_current_prices()
        self.save_cache(current)

        # Broadcast if enabled
        broadcast_result = None
        if self._settings.get("price_broadcast_enabled", False):
            broadcast_result = self.broadcast_price_update(changes)
            logger.info(f"Price broadcast result: {broadcast_result}")

        return {
            "changes_found": len(changes),
            "changes": changes,
            "broadcast_result": broadcast_result,
        }

    def get_price_history(self, limit: int = 50) -> list[dict]:
        """Get recent price change history from database."""
        try:
            from database import get_price_update_history
            return get_price_update_history(limit=limit)
        except Exception:
            return []


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND WATCHER
# ══════════════════════════════════════════════════════════════════════════════

_watcher_running = False
_watcher_thread: Optional[threading.Thread] = None


def start_price_watcher():
    """Start background price watcher thread."""
    global _watcher_running, _watcher_thread
    if _watcher_running:
        return

    _watcher_running = True
    _watcher_thread = threading.Thread(target=_watcher_loop, daemon=True,
                                        name="price_watcher")
    _watcher_thread.start()
    logger.info("Price watcher started")


def stop_price_watcher():
    """Stop background price watcher."""
    global _watcher_running
    _watcher_running = False
    logger.info("Price watcher stopped")


def _watcher_loop():
    """Check prices every N minutes (from settings)."""
    global _watcher_running
    while _watcher_running:
        try:
            from settings_engine import load_settings
            settings = load_settings()
            interval = settings.get("price_watch_interval_minutes", 5) * 60

            if settings.get("price_broadcast_enabled", False):
                engine = PriceWatchEngine()
                result = engine.run_check()
                if result.get("changes_found", 0) > 0:
                    logger.info(f"Price check: {result['changes_found']} changes")
        except Exception as e:
            logger.error(f"Price watcher error: {e}")

        # Sleep in 1-second intervals for clean shutdown
        for _ in range(max(int(interval if 'interval' in dir() else 300), 60)):
            if not _watcher_running:
                break
            time.sleep(1)


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ══════════════════════════════════════════════════════════════════════════════


def get_price_watch_status() -> dict:
    """Get current price watch engine status."""
    engine = PriceWatchEngine()
    current = engine.load_current_prices()
    cached = engine.load_cached_prices()

    return {
        "watcher_running": _watcher_running,
        "current_prices_count": len(engine._extract_price_items(current)),
        "cached_prices_count": len(engine._extract_price_items(cached)),
        "threshold_pct": engine.threshold_pct,
        "broadcast_enabled": engine._settings.get("price_broadcast_enabled", False),
        "channels": engine.channels,
    }


def manual_price_check() -> dict:
    """Manually trigger a price check (for UI button)."""
    engine = PriceWatchEngine()
    return engine.run_check()
