"""
PPS Anantam — Sync Engine v1.0
================================
Master synchronization engine for the entire dashboard ecosystem.
Runs daily at 6 AM IST + on-demand via UI.

Orchestrates:
  1. Market data refresh (crude, FX, weather)
  2. News feed refresh (RSS + API)
  3. Trade data refresh (UN Comtrade)
  4. Data validation (SRE sanity checks)
  5. Calculated table refresh (demand, correlations)
  6. Opportunity scanning
  7. CRM profile auto-updates
  8. Alert generation
  9. Sync logging
"""

import json
import time
import threading
import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None

SYNC_LOG_FILE = BASE / "sync_logs.json"

_scheduler_thread = None
_scheduler_running = False
_scheduler_lock = threading.Lock()


def _now() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _load_json(path, default=None):
    if default is None:
        default = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


class SyncEngine:
    """Master synchronization engine — runs daily + on-demand."""

    def __init__(self):
        self.results = {
            "started_at": "",
            "completed_at": "",
            "status": "pending",
            "steps": [],
            "apis_called": 0,
            "apis_succeeded": 0,
            "records_updated": 0,
            "errors": [],
        }

    def _run_batch(self, steps: list[tuple[str, callable]]) -> None:
        """Run a batch of steps in parallel using ConcurrentExecutor."""
        try:
            from resilience_manager import ConcurrentExecutor, DeadLetterQueue
            tasks = [
                {"name": name, "fn": fn, "args": (), "timeout": 120}
                for name, fn in steps
            ]
            results = ConcurrentExecutor.run_parallel(tasks, max_workers=4, timeout_per_task=120)
            for r in results:
                if not r.get("success"):
                    self.results["errors"].append(f"{r['name']}: {r.get('error', 'unknown')}")
                    DeadLetterQueue.push("sync_step", {"step_name": r["name"]}, r.get("error", ""))
        except ImportError:
            # Fallback to sequential if resilience_manager not available
            for name, fn in steps:
                try:
                    fn()
                except Exception as e:
                    self.results["errors"].append(f"{name}: {e}")

    def run_full_sync(self) -> dict:
        """Orchestrates complete data refresh across all systems (parallel batches)."""
        self.results["started_at"] = _now()
        self.results["status"] = "running"

        # Batch 1 (parallel): Data fetching
        self._run_batch([
            ("market_data", self._sync_market_data),
            ("news_feeds", self._sync_news_feeds),
            ("trade_data", self._sync_trade_data),
        ])

        # Batch 2 (parallel): Validation + processing
        self._run_batch([
            ("validate", self._validate_data),
            ("calculations", self._refresh_calculations),
            ("opportunities", self._scan_opportunities),
        ])

        # Batch 3 (parallel): CRM + communications + automation
        self._run_batch([
            ("crm_profiles", self._update_crm_profiles),
            ("alerts", self._generate_alerts),
            ("comms", self._process_communication_triggers),
            ("daily_rotation", self._run_daily_rotation),
            ("festival_broadcasts", self._check_festival_broadcasts),
            ("price_watch", self._run_price_watch),
            ("ai_replies", self._process_ai_replies),
            ("briefing", self._generate_director_briefing),
        ])

        # Batch 4 (parallel): AI + ML + Intelligence
        self._run_batch([
            ("ai_learning", self._run_ai_learning),
            ("smart_alerts", self._generate_smart_alerts),
            ("infra_demand", self._sync_infra_demand),
            ("source_health", self._sync_source_health),
            ("auto_insights", self._sync_auto_insights),
            ("rag_index", self._sync_rag_index),
            ("boost_models", self._sync_boost_models),
            ("market_signals", self._sync_market_signals),
        ])

        # Batch 5 (parallel): AI Trading Intelligence Refresh
        self._run_batch([
            ("intelligence_refresh", self._sync_intelligence_refresh),
            ("market_pulse", self._sync_market_pulse),
            ("recommendations", self._sync_recommendations),
        ])

        # Finalize
        self.results["completed_at"] = _now()
        self.results["status"] = (
            "success" if not self.results["errors"]
            else "partial" if self.results["apis_succeeded"] > 0
            else "failed"
        )

        # Save sync log
        self._save_log()

        return self.results

    def run_market_only(self) -> dict:
        """Quick sync — market data only."""
        self.results["started_at"] = _now()
        self._sync_market_data()
        self.results["completed_at"] = _now()
        self.results["status"] = "success" if not self.results["errors"] else "partial"
        self._save_log()
        return self.results

    # ─── Step 1: Market Data ─────────────────────────────────────────────────

    def _sync_market_data(self):
        """Refresh crude prices, FX rates, weather."""
        step = {"name": "Market Data", "status": "running", "started_at": _now(), "details": []}

        # Crude Prices (EIA / yfinance)
        try:
            from api_hub_engine import connect_eia
            result = connect_eia()
            self.results["apis_called"] += 1
            if result and result.get("ok"):
                self.results["apis_succeeded"] += 1
                self.results["records_updated"] += result.get("records", 0)
                step["details"].append(f"Crude: {result.get('records', 0)} records from {result.get('source', 'unknown')}")
            else:
                step["details"].append(f"Crude: Failed — {result.get('error', 'unknown')}")
                self.results["errors"].append("Crude price fetch failed")
        except Exception as e:
            step["details"].append(f"Crude: Error — {str(e)[:100]}")
            self.results["errors"].append(f"Crude: {str(e)[:100]}")

        # FX Rates
        try:
            from api_hub_engine import connect_fx
            result = connect_fx()
            self.results["apis_called"] += 1
            if result and result.get("ok"):
                self.results["apis_succeeded"] += 1
                self.results["records_updated"] += result.get("records", 0)
                step["details"].append(f"FX: {result.get('records', 0)} records")
            else:
                step["details"].append("FX: Failed")
        except Exception as e:
            step["details"].append(f"FX: Error — {str(e)[:100]}")

        # Weather
        try:
            from api_hub_engine import connect_weather
            result = connect_weather()
            self.results["apis_called"] += 1
            if result and result.get("ok"):
                self.results["apis_succeeded"] += 1
                self.results["records_updated"] += result.get("records", 0)
                step["details"].append(f"Weather: {result.get('records', 0)} records")
        except Exception as e:
            step["details"].append(f"Weather: Error — {str(e)[:100]}")

        # World Bank (Economic data)
        try:
            from api_hub_engine import connect_world_bank
            result = connect_world_bank()
            self.results["apis_called"] += 1
            if result and result.get("ok"):
                self.results["apis_succeeded"] += 1
                self.results["records_updated"] += result.get("records", 0)
                step["details"].append(f"World Bank: {result.get('records', 0)} indicators")
        except Exception as e:
            step["details"].append(f"World Bank: Error — {str(e)[:100]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 2: News Feeds ──────────────────────────────────────────────────

    def _sync_news_feeds(self):
        """Refresh news from RSS + API sources."""
        step = {"name": "News Feeds", "status": "running", "started_at": _now(), "details": []}

        try:
            from api_hub_engine import connect_news
            result = connect_news()
            self.results["apis_called"] += 1
            if result and result.get("ok"):
                self.results["apis_succeeded"] += 1
                self.results["records_updated"] += result.get("records", 0)
                step["details"].append(f"News: {result.get('records', 0)} articles")
            else:
                step["details"].append("News: No new articles")
        except Exception as e:
            step["details"].append(f"News: Error — {str(e)[:100]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 3: Trade Data ──────────────────────────────────────────────────

    def _sync_trade_data(self):
        """Refresh UN Comtrade import data."""
        step = {"name": "Trade Data", "status": "running", "started_at": _now(), "details": []}

        try:
            from api_hub_engine import connect_comtrade
            result = connect_comtrade()
            self.results["apis_called"] += 1
            if result and result.get("ok"):
                self.results["apis_succeeded"] += 1
                self.results["records_updated"] += result.get("records", 0)
                step["details"].append(f"Trade: {result.get('records', 0)} records")
        except Exception as e:
            step["details"].append(f"Trade: Error — {str(e)[:100]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 4: Validate Data ───────────────────────────────────────────────

    def _validate_data(self):
        """Run SRE validation on all data tables."""
        step = {"name": "Validation", "status": "running", "started_at": _now(), "details": []}

        try:
            from sre_engine import get_health_status
            health = get_health_status()
            issues = [h for h in health if h.get("status") in ("WARN", "FAIL")]
            step["details"].append(f"Health check: {len(health)} entities, {len(issues)} issues")
            if issues:
                for issue in issues[:5]:
                    step["details"].append(
                        f"  {issue.get('entity_type', '?')}/{issue.get('entity_name', '?')}: "
                        f"{issue.get('status', '?')} — {issue.get('details', '')[:80]}"
                    )
        except Exception as e:
            step["details"].append(f"Validation skipped: {str(e)[:100]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 5: Refresh Calculations ────────────────────────────────────────

    def _refresh_calculations(self):
        """Recalculate demand proxy, regression coefficients, etc."""
        step = {"name": "Calculations", "status": "running", "started_at": _now(), "details": []}

        try:
            from correlation_engine import run_full_analysis
            result = run_full_analysis()
            n_corr = len(result.get("correlations", [])) if isinstance(result, dict) else 0
            step["details"].append(f"Correlation: {n_corr} results")
        except Exception as e:
            step["details"].append(f"Correlation: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 6: Opportunities ───────────────────────────────────────────────

    def _scan_opportunities(self):
        """Run opportunity discovery engine."""
        step = {"name": "Opportunities", "status": "running", "started_at": _now(), "details": []}

        try:
            from opportunity_engine import OpportunityEngine
            engine = OpportunityEngine()
            opps = engine.scan_all_opportunities()
            step["details"].append(f"Found {len(opps)} new opportunities")
            for opp in opps[:3]:
                step["details"].append(f"  {opp.get('type', '?')}: {opp.get('title', '')[:60]}")
        except Exception as e:
            step["details"].append(f"Opportunity scan: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 7: CRM Updates ────────────────────────────────────────────────

    def _update_crm_profiles(self):
        """Auto-update customer/supplier relationship stages via database."""
        step = {"name": "CRM Updates", "status": "running", "started_at": _now(), "details": []}

        try:
            from crm_engine import IntelligentCRM
            crm = IntelligentCRM()
            updated = crm.auto_update_all_profiles()
            step["details"].append(f"CRM: {updated} profiles updated via database")
        except Exception as e:
            step["details"].append(f"CRM: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 8: Alerts ──────────────────────────────────────────────────────

    def _generate_alerts(self):
        """Generate daily summary alerts."""
        step = {"name": "Alerts", "status": "running", "started_at": _now(), "details": []}

        try:
            # Check for price volatility
            prices = _load_json(BASE / "tbl_crude_prices.json", [])
            brent_prices = [p["price"] for p in prices if p.get("benchmark") == "Brent"]
            if len(brent_prices) >= 2:
                latest = brent_prices[-1]
                prev = brent_prices[-2]
                change_pct = ((latest - prev) / prev) * 100 if prev else 0
                if abs(change_pct) > 3:
                    step["details"].append(
                        f"ALERT: Brent moved {change_pct:+.1f}% (${prev:.2f} -> ${latest:.2f})"
                    )

            # Check overdue CRM tasks
            tasks = _load_json(BASE / "crm_tasks.json", [])
            overdue = [t for t in tasks if t.get("status") == "Pending"]
            if overdue:
                step["details"].append(f"ALERT: {len(overdue)} pending CRM tasks")

        except Exception as e:
            step["details"].append(f"Alerts: error — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 9: Communication Triggers ──────────────────────────────────────

    def _process_communication_triggers(self):
        """Trigger email/WhatsApp engines based on sync results."""
        step = {"name": "Communication Triggers", "status": "running", "started_at": _now(), "details": []}

        # Gather opportunities and overdue deals
        opportunities = []
        overdue_deals = []
        try:
            from opportunity_engine import get_all_opportunities
            opportunities = get_all_opportunities(status="new") or []
        except Exception:
            pass
        try:
            from database import get_all_deals
            today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
            for d in get_all_deals():
                if d.get("status") != "active":
                    continue
                outstanding = (d.get("total_value_inr") or 0) - (d.get("payment_received_inr") or 0)
                payment_date = d.get("payment_date") or d.get("delivery_date")
                if outstanding > 0 and payment_date and payment_date < today:
                    overdue_deals.append(d)
        except Exception:
            pass

        # Email triggers
        try:
            from email_engine import EmailEngine
            email_eng = EmailEngine()
            queued = email_eng.on_opportunity_scan(opportunities)
            if queued > 0:
                step["details"].append(f"Email: {queued} messages queued from opportunities")
            overdue_queued = email_eng.on_payment_overdue(overdue_deals)
            if overdue_queued > 0:
                step["details"].append(f"Email: {overdue_queued} payment reminders queued")
        except Exception as e:
            step["details"].append(f"Email triggers: skipped — {str(e)[:80]}")

        # WhatsApp triggers
        try:
            from whatsapp_engine import WhatsAppEngine
            wa_eng = WhatsAppEngine()
            wa_queued = wa_eng.on_opportunity_scan(opportunities)
            if wa_queued > 0:
                step["details"].append(f"WhatsApp: {wa_queued} messages queued from opportunities")
            wa_overdue = wa_eng.on_payment_overdue(overdue_deals)
            if wa_overdue > 0:
                step["details"].append(f"WhatsApp: {wa_overdue} payment reminders queued")
        except Exception as e:
            step["details"].append(f"WhatsApp triggers: skipped — {str(e)[:80]}")

        if not step["details"]:
            step["details"].append("No communication triggers fired")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 10a: Daily Rotation ──────────────────────────────────────────────

    def _run_daily_rotation(self):
        """Trigger daily contact rotation if scheduled."""
        step = {"name": "Daily Rotation", "status": "running", "started_at": _now(), "details": []}
        try:
            from settings_engine import load_settings
            settings = load_settings()
            if not settings.get("daily_rotation_enabled", False):
                step["details"].append("Rotation: disabled in settings")
            else:
                from rotation_engine import ContactRotationEngine
                engine = ContactRotationEngine()
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                batch = engine.select_daily_batch(today)
                if batch:
                    result = engine.execute_rotation(batch, today)
                    step["details"].append(
                        f"Rotation: sent={result.get('sent',0)} "
                        f"failed={result.get('failed',0)} of {len(batch)}")
                    self.results["records_updated"] += result.get("sent", 0)
                else:
                    step["details"].append("Rotation: no contacts in batch")
        except Exception as e:
            step["details"].append(f"Rotation: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 10b: Festival Broadcasts ───────────────────────────────────────

    def _check_festival_broadcasts(self):
        """Check and execute festival broadcasts if any are due."""
        step = {"name": "Festival Broadcasts", "status": "running", "started_at": _now(), "details": []}
        try:
            from settings_engine import load_settings
            settings = load_settings()
            if not settings.get("festival_broadcast_enabled", False):
                step["details"].append("Festival broadcasts: disabled")
            else:
                from rotation_engine import FestivalBroadcastEngine
                engine = FestivalBroadcastEngine()
                days_ahead = settings.get("festival_broadcast_days_ahead", 1)
                upcoming = engine.get_upcoming_festivals(days_ahead=days_ahead)
                if upcoming:
                    for fest in upcoming:
                        fname = fest.get("name", fest.get("festival", ""))
                        fdate = fest.get("parsed_date", fest.get("date", ""))
                        if fname:
                            prepared = engine.prepare_festival_messages(fname, fdate)
                            if prepared.get("messages"):
                                result = engine.execute_festival_broadcast(prepared)
                                step["details"].append(
                                    f"Festival '{fname}': wa={result.get('sent_whatsapp',0)} "
                                    f"email={result.get('sent_email',0)}")
                else:
                    step["details"].append("No festivals due")
        except Exception as e:
            step["details"].append(f"Festival: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 10c: Price Watch ───────────────────────────────────────────────

    def _run_price_watch(self):
        """Detect price changes and broadcast if significant."""
        step = {"name": "Price Watch", "status": "running", "started_at": _now(), "details": []}
        try:
            from settings_engine import load_settings
            settings = load_settings()
            if not settings.get("price_broadcast_enabled", False):
                step["details"].append("Price broadcast: disabled")
            else:
                from price_watch_engine import PriceWatchEngine
                engine = PriceWatchEngine()
                result = engine.run_check()
                changes = result.get("changes_found", 0)
                if changes > 0:
                    br = result.get("broadcast_result", {})
                    step["details"].append(
                        f"Price changes: {changes} detected, "
                        f"wa={br.get('sent_whatsapp',0)} email={br.get('sent_email',0)}")
                else:
                    step["details"].append("No significant price changes")
        except Exception as e:
            step["details"].append(f"Price watch: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 10d: AI Auto-Replies ───────────────────────────────────────────

    def _process_ai_replies(self):
        """Process incoming WhatsApp messages with AI auto-reply."""
        step = {"name": "AI Auto-Replies", "status": "running", "started_at": _now(), "details": []}
        try:
            from settings_engine import load_settings
            settings = load_settings()
            if not settings.get("ai_auto_reply_enabled", False):
                step["details"].append("AI auto-reply: disabled")
            else:
                from ai_reply_engine import process_pending_replies
                result = process_pending_replies()
                step["details"].append(
                    f"AI replies: processed={result.get('processed',0)} "
                    f"auto={result.get('auto_replied',0)} "
                    f"escalated={result.get('escalated',0)}")
        except Exception as e:
            step["details"].append(f"AI replies: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 10e: Director Briefing ─────────────────────────────────────────

    def _generate_director_briefing(self):
        """Auto-generate and store daily briefing."""
        step = {"name": "Director Briefing", "status": "running", "started_at": _now(), "details": []}

        try:
            from director_briefing_engine import DirectorBriefingEngine
            engine = DirectorBriefingEngine()
            briefing = engine.generate_briefing()
            engine.save_briefing_to_db(briefing)
            step["details"].append(f"Briefing generated for {briefing.get('briefing_date', 'today')}")
        except Exception as e:
            step["details"].append(f"Briefing: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 11: AI Learning ─────────────────────────────────────────────────

    def _run_ai_learning(self):
        """Run daily AI learning cycle, weekly/monthly if due."""
        step = {"name": "AI Learning", "status": "running", "started_at": _now(), "details": []}

        try:
            from ai_learning_engine import AILearningEngine
            engine = AILearningEngine()

            # Daily learning (always)
            daily_result = engine.daily_learn()
            if daily_result.get("status") != "disabled":
                acc = daily_result.get("accuracy_scores", {}).get("price_7d", "N/A")
                step["details"].append(f"Daily learn: accuracy={acc}%")
            else:
                step["details"].append("Daily learning: disabled in settings")

            # Weekly learning (check if Monday)
            now = datetime.datetime.now(IST)
            if now.weekday() == 0:  # Monday
                weekly_result = engine.weekly_learn()
                if weekly_result.get("status") != "disabled":
                    step["details"].append(
                        f"Weekly learn: {weekly_result.get('customer_score_updates', 0)} CRM updates"
                    )

            # Monthly learning (check if 1st of month)
            if now.day == 1:
                monthly_result = engine.monthly_learn()
                if monthly_result.get("status") != "disabled":
                    step["details"].append(
                        f"Monthly learn: v{monthly_result.get('model_version', '?')}"
                    )

        except Exception as e:
            step["details"].append(f"AI Learning: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 12: Smart Alert Scan ────────────────────────────────────────────

    def _generate_smart_alerts(self):
        """Run the upgraded P0/P1/P2 alert engine."""
        step = {"name": "Smart Alerts", "status": "running", "started_at": _now(), "details": []}

        try:
            from command_intel.alert_center import run_alert_scan
            count = run_alert_scan()
            step["details"].append(f"Alert scan: {count} new alerts generated")
        except Exception as e:
            step["details"].append(f"Smart alerts: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 13: Infra Demand Intelligence ─────────────────────────────────

    def _sync_infra_demand(self):
        """Run GDELT live update + demand scoring."""
        step = {"name": "Infra Demand Intelligence", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from settings_engine import load_settings
            settings = load_settings()
            if not settings.get("infra_demand_enabled", True):
                step["details"].append("Infra demand: disabled in settings")
                step["status"] = "skipped"
                self.results["steps"].append(step)
                return

            from infra_demand_engine import run_live_update
            result = run_live_update()
            step["details"].append(
                f"GDELT: {result.get('articles_inserted', 0)} new articles, "
                f"{result.get('scores_computed', 0)} scores, "
                f"{result.get('alerts_generated', 0)} alerts"
            )
            if result.get("errors"):
                step["details"].extend(result["errors"][:3])
        except Exception as e:
            step["details"].append(f"Infra demand: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 14: Source Registry Health Update ──────────────────────────────

    def _sync_source_health(self):
        """Update source_registry table with latest sync health data."""
        step = {"name": "Source Registry Health", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from database import get_all_sources, update_source_registry
            sources = get_all_sources()
            updated = 0
            for src in sources:
                if src.get("status") == "active":
                    update_source_registry(src["id"], {"last_success": _now()})
                    updated += 1
            step["details"].append(f"Updated {updated} source health records")
        except Exception as e:
            step["details"].append(f"Source health: skipped — {str(e)[:80]}")

        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 15: Auto Insights ──────────────────────────────────────────────

    def _sync_auto_insights(self):
        """Generate daily AI insights after data refresh."""
        step = {"name": "Auto Daily Insights", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from auto_insight_engine import schedule_insights
            schedule_insights()
            step["details"].append("Daily insights generated")
        except Exception as e:
            step["details"].append(f"Auto insights: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 16: RAG Index Refresh ──────────────────────────────────────────

    def _sync_rag_index(self):
        """Rebuild RAG search index with latest data."""
        step = {"name": "RAG Index Refresh", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from rag_engine import refresh_index
            result = refresh_index()
            step["details"].append(f"RAG index: {result.get('indexed', 0)} docs ({result.get('engine', 'none')})")
        except Exception as e:
            step["details"].append(f"RAG index: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 17: ML Boost Model Training ────────────────────────────────────

    def _sync_boost_models(self):
        """Retrain LightGBM/XGBoost models on latest data."""
        step = {"name": "ML Boost Training", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from ml_boost_engine import train_boost_models
            result = train_boost_models()
            step["details"].append(f"Boost models trained: {result.get('models_trained', 0)}")
        except Exception as e:
            step["details"].append(f"Boost training: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 18: Market Intelligence Signals ───────────────────────────────

    def _sync_market_signals(self):
        """Compute all 10 market intelligence signals."""
        step = {"name": "Market Intelligence Signals", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from market_intelligence_engine import compute_all_signals
            result = compute_all_signals()
            master = result.get("master", {})
            step["details"].append(
                f"Master signal: {master.get('market_direction', 'N/A')} "
                f"(confidence {master.get('confidence', 0)}%)")
            ok_count = sum(1 for s in result.values() if s.get("status") == "OK")
            step["details"].append(f"10 signals computed, {ok_count} OK")
        except Exception as e:
            step["details"].append(f"Market signals: Error — {str(e)[:100]}")
            self.results["errors"].append(f"Market signals: {str(e)[:100]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Step 19: AI Trading Intelligence Refresh ────────────────────────────

    def _sync_intelligence_refresh(self):
        """Trigger unified intelligence refresh (Batch 5)."""
        step = {"name": "Intelligence Refresh", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from unified_intelligence_engine import refresh_intelligence
            result = refresh_intelligence()
            ok = sum(1 for v in result.values() if v and not str(v).startswith("Error"))
            step["details"].append(f"Intelligence refresh: {ok}/{len(result)} engines OK")
        except Exception as e:
            step["details"].append(f"Intelligence refresh: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    def _sync_market_pulse(self):
        """Generate contextual market alerts."""
        step = {"name": "Market Pulse", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from market_pulse_engine import monitor_all
            result = monitor_all()
            alert_count = len(result.get("alerts", []))
            step["details"].append(f"Market pulse: {alert_count} alerts generated")
        except Exception as e:
            step["details"].append(f"Market pulse: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    def _sync_recommendations(self):
        """Generate daily trading recommendations."""
        step = {"name": "Recommendations", "status": "running",
                "started_at": _now(), "details": []}
        try:
            from recommendation_engine import generate_daily_recommendations
            result = generate_daily_recommendations()
            action = "N/A"
            buy = result.get("buy_timing", {})
            if isinstance(buy, dict):
                action = buy.get("action", "N/A")
            step["details"].append(f"Recommendations generated: buy action={action}")
        except Exception as e:
            step["details"].append(f"Recommendations: skipped — {str(e)[:80]}")
        step["status"] = "done"
        step["completed_at"] = _now()
        self.results["steps"].append(step)

    # ─── Logging ─────────────────────────────────────────────────────────────

    def _save_log(self):
        """Save sync results to log file."""
        logs = _load_json(SYNC_LOG_FILE, [])
        logs.append(self.results)
        if len(logs) > 500:
            logs = logs[-500:]
        _save_json(SYNC_LOG_FILE, logs)

    def get_missing_data_gaps(self) -> list:
        """Returns list of data that needs human input."""
        try:
            from missing_inputs_engine import MissingInputsEngine
            engine = MissingInputsEngine()
            return engine.scan_all_gaps()
        except Exception:
            return []


# ─── Scheduler ───────────────────────────────────────────────────────────────

def run_sync_now() -> dict:
    """Run full sync immediately (on-demand)."""
    engine = SyncEngine()
    return engine.run_full_sync()


def run_market_sync() -> dict:
    """Quick market-only sync."""
    engine = SyncEngine()
    return engine.run_market_only()


def _get_schedule_times() -> dict:
    """Load daily automation schedule from settings, fallback to business_context."""
    defaults = {
        "price_gathering": "05:00",
        "daily_brief": "06:30",
        "festival_check": "07:00",
        "daily_broadcast": "09:00",
        "price_alerts": "18:00",
        "daily_report": "21:00",
    }
    try:
        from settings_engine import load_settings
        s = load_settings()
        return {
            "price_gathering": s.get("schedule_price_gathering_time", defaults["price_gathering"]),
            "daily_brief": s.get("schedule_daily_brief_time", defaults["daily_brief"]),
            "festival_check": s.get("schedule_festival_check_time", defaults["festival_check"]),
            "daily_broadcast": s.get("schedule_daily_broadcast_time", defaults["daily_broadcast"]),
            "price_alerts": s.get("schedule_price_alerts_time", defaults["price_alerts"]),
            "daily_report": s.get("schedule_daily_report_time", defaults["daily_report"]),
        }
    except Exception:
        pass
    try:
        from business_context import get_daily_schedule
        sched = get_daily_schedule()
        for item in sched:
            key = item.get("task", "").lower().replace(" ", "_")
            if key in defaults:
                defaults[key] = item.get("time", defaults[key])
    except Exception:
        pass
    return defaults


def _scheduler_loop(interval_minutes: int = 60):
    """Background scheduler loop with heartbeat."""
    global _scheduler_running
    while _scheduler_running:
        try:
            from resilience_manager import HeartbeatMonitor
            HeartbeatMonitor.beat("SyncScheduler")
        except Exception:
            pass
        try:
            engine = SyncEngine()
            engine.run_full_sync()
        except Exception:
            pass
        # Sleep in small chunks so we can stop gracefully
        for _ in range(interval_minutes * 60):
            if not _scheduler_running:
                break
            time.sleep(1)


def start_sync_scheduler(interval_minutes: int = 60):
    """Start background sync scheduler."""
    global _scheduler_thread, _scheduler_running
    with _scheduler_lock:
        if _scheduler_thread and _scheduler_thread.is_alive():
            return  # Already running
        _scheduler_running = True
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(interval_minutes,),
            daemon=True,
            name="SyncScheduler"
        )
        _scheduler_thread.start()

        # Register with heartbeat monitor
        try:
            from resilience_manager import HeartbeatMonitor
            HeartbeatMonitor.register(
                "SyncScheduler",
                restart_fn=lambda: start_sync_scheduler(interval_minutes),
                expected_interval_sec=interval_minutes * 60,
            )
        except Exception:
            pass


def stop_sync_scheduler():
    """Stop background sync scheduler."""
    global _scheduler_running
    _scheduler_running = False


def get_sync_history(limit: int = 20) -> list:
    """Get recent sync logs."""
    logs = _load_json(SYNC_LOG_FILE, [])
    return logs[-limit:]


def get_last_sync() -> dict:
    """Get the most recent sync result."""
    logs = _load_json(SYNC_LOG_FILE, [])
    return logs[-1] if logs else {"status": "never_synced", "started_at": "N/A"}
