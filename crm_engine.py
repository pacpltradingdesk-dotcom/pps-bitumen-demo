"""
PPS Anantam — Intelligent CRM Engine v3.0
==========================================
Market-intelligent CRM with auto-updating profiles,
relationship scoring, and AI-driven task management.

v3.0 changes:
  - Tasks stored in SQLite (crm_tasks table) instead of JSON
  - One-time auto-migration from crm_tasks.json → SQLite
  - Activities still in JSON (lightweight, append-only)
"""

import json
import datetime
import uuid
from datetime import timedelta
from pathlib import Path

import pytz

IST = pytz.timezone("Asia/Kolkata")
BASE = Path(__file__).parent

try:
    from log_engine import dashboard_log as _dlog
except ImportError:
    _dlog = None

# --- CONFIGURATION ---
TASKS_JSON_FILE = BASE / "crm_tasks.json"       # legacy (migrated to SQLite)
TASKS_JSON_BAK = BASE / "crm_tasks.json.bak"    # backup after migration
ACTIVITIES_FILE = BASE / "crm_activities.json"

# --- CONSTANTS ---
PIPELINE_STAGES = [
    "New Enquiry", "Quoted", "Negotiation", "PO Awaited",
    "Dispatch", "Delivered", "Payment Follow-up", "Closed Won", "Closed Lost"
]

TASK_TYPES = ["Call", "WhatsApp", "Email", "Meeting", "Internal"]
PRIORITIES = ["High", "Medium", "Low"]

# Relationship decay thresholds (days since last interaction)
RELATIONSHIP_THRESHOLDS = {"hot": 7, "warm": 30, "cold": 90}

# VIP scoring weights (total = 1.0)
VIP_WEIGHTS = {
    "deal_value": 0.35,
    "purchase_frequency": 0.25,
    "recency": 0.20,
    "response_rate": 0.10,
    "relationship_age": 0.10,
}
VIP_TIERS = {
    "platinum": 80,  # score >= 80
    "gold": 60,      # score >= 60
    "silver": 40,    # score >= 40
    "standard": 0,   # score < 40
}


# --- DATA HANDLING (Activities — still JSON) ---

def _load_json(filepath, default=None):
    if default is None:
        default = []
    fp = Path(filepath)
    if fp.exists():
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
    return default


def _save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def get_activities(): return _load_json(ACTIVITIES_FILE)
def save_activities(acts): _save_json(ACTIVITIES_FILE, acts)


# --- TASK STORAGE (SQLite) ---

def get_tasks() -> list[dict]:
    """Get all tasks from SQLite crm_tasks table."""
    try:
        from database import get_crm_tasks
        return get_crm_tasks()
    except Exception:
        # Fallback to JSON if DB not available
        return _load_json(TASKS_JSON_FILE)


def save_tasks(tasks: list[dict]):
    """Legacy compatibility — bulk-save tasks. Prefer add_task / complete_task."""
    _save_json(TASKS_JSON_FILE, tasks)


# --- ONE-TIME MIGRATION ---

_MIGRATION_DONE = False


def _migrate_json_to_sqlite():
    """Migrate tasks from crm_tasks.json → SQLite crm_tasks table (once)."""
    global _MIGRATION_DONE  # noqa: PLW0603
    if _MIGRATION_DONE:
        return
    _MIGRATION_DONE = True

    if not TASKS_JSON_FILE.exists():
        return

    try:
        from database import insert_crm_task, get_crm_tasks
        existing = get_crm_tasks()
        existing_ids = {t.get("task_id") for t in existing}

        json_tasks = _load_json(TASKS_JSON_FILE)
        if not json_tasks:
            return

        migrated = 0
        for t in json_tasks:
            tid = t.get("id", str(uuid.uuid4())[:8])
            if tid in existing_ids:
                continue
            try:
                insert_crm_task({
                    "task_id": tid,
                    "client": t.get("client", ""),
                    "type": t.get("type", "Call"),
                    "due_date": t.get("due_date", ""),
                    "status": t.get("status", "Pending"),
                    "priority": t.get("priority", "Medium"),
                    "note": t.get("note", ""),
                    "outcome": t.get("outcome", ""),
                    "automated": 1 if t.get("automated") else 0,
                    "created_at": t.get("created_at", ""),
                    "completed_at": t.get("completed_at", ""),
                })
                migrated += 1
            except Exception:
                pass

        if migrated > 0:
            # Backup JSON file and remove original
            import shutil
            try:
                shutil.copy2(TASKS_JSON_FILE, TASKS_JSON_BAK)
                TASKS_JSON_FILE.unlink()
            except Exception:
                pass
    except ImportError:
        pass
    except Exception:
        pass


# --- CORE CRM LOGIC ---

def add_task(client_name, task_type, due_date_str, priority="Medium", note="", automated=False):
    """
    Adds a new task to the CRM (SQLite).
    due_date_str format: 'DD-MM-YYYY HH:MM'
    """
    task_id = str(uuid.uuid4())[:8]
    created_at = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")

    try:
        from database import insert_crm_task
        insert_crm_task({
            "task_id": task_id,
            "client": client_name,
            "type": task_type,
            "due_date": due_date_str,
            "status": "Pending",
            "priority": priority,
            "note": note,
            "outcome": "",
            "automated": 1 if automated else 0,
            "created_at": created_at,
            "completed_at": "",
        })
    except Exception:
        # Fallback: append to JSON
        tasks = _load_json(TASKS_JSON_FILE)
        tasks.append({
            "id": task_id, "client": client_name, "type": task_type,
            "due_date": due_date_str, "status": "Pending", "priority": priority,
            "note": note, "created_at": created_at, "automated": automated,
        })
        _save_json(TASKS_JSON_FILE, tasks)

    return {
        "id": task_id, "client": client_name, "type": task_type,
        "due_date": due_date_str, "status": "Pending", "priority": priority,
        "note": note, "created_at": created_at, "automated": automated,
    }


def complete_task(task_id, outcome_note=""):
    """Mark a task as completed (SQLite)."""
    completed_at = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    matched = None

    try:
        from database import complete_crm_task, get_crm_tasks
        complete_crm_task(task_id, outcome_note)
        # Find the task for activity logging
        tasks = get_crm_tasks()
        for t in tasks:
            if t.get("task_id") == task_id:
                matched = t
                break
    except Exception:
        # Fallback: JSON
        tasks = _load_json(TASKS_JSON_FILE)
        for t in tasks:
            if t.get("id") == task_id:
                t["status"] = "Completed"
                t["outcome"] = outcome_note
                t["completed_at"] = completed_at
                matched = t
                break
        _save_json(TASKS_JSON_FILE, tasks)

    if matched:
        client = matched.get("client", "")
        ttype = matched.get("type", "")
        tnote = matched.get("note", "")
        log_activity(client, ttype,
                     f"Completed Task: {tnote} | Outcome: {outcome_note}")


def log_activity(client_name, act_type, details):
    acts = get_activities()
    new_act = {
        "id": str(uuid.uuid4())[:8],
        "client": client_name,
        "type": act_type,
        "details": details,
        "timestamp": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    }
    acts.append(new_act)
    # Keep max 5000 activities
    if len(acts) > 5000:
        acts = acts[-5000:]
    save_activities(acts)


# --- AUTOMATION ENGINE ( The "Brain" ) ---

def auto_generate_tasks(client_data, deal_stage):
    """
    Generates tasks based on rules.
    Extended with 6 automation rules.
    """
    now = datetime.datetime.now(IST)
    created_tasks = []

    # Rule 1: New Lead -> Call in 15 mins
    if deal_stage == "New Enquiry":
        due = (now + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "Call", due, "High",
                 "New Enquiry: Introduction & Qualify", automated=True)
        created_tasks.append("New Lead Call")

    # Rule 2: Quote Sent -> Follow up in 2 hours + next day
    elif deal_stage == "Quoted":
        due = (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "WhatsApp", due, "High",
                 "Check if Quote Received", automated=True)
        due_next = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "Call", due_next, "Medium",
                 "Quote Follow-up / Negotiation", automated=True)
        created_tasks.append("Quote Follow-ups")

    # Rule 3: Payment Pending -> Daily Reminder
    elif deal_stage == "Payment Follow-up":
        due = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "Call", due, "High",
                 "Payment Reminder", automated=True)
        created_tasks.append("Payment Reminder")

    # Rule 4: Negotiation -> WhatsApp offer + Call in 1 day
    elif deal_stage == "Negotiation":
        due = (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "WhatsApp", due, "High",
                 "Send revised offer with 3-tier pricing", automated=True)
        due_call = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "Call", due_call, "High",
                 "Negotiation follow-up call", automated=True)
        created_tasks.append("Negotiation Tasks")

    # Rule 5: Delivered -> Thank you + Payment follow-up
    elif deal_stage == "Delivered":
        due = (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "WhatsApp", due, "Medium",
                 "Send delivery confirmation & thank you", automated=True)
        due_pay = (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "Call", due_pay, "Medium",
                 "Payment schedule follow-up", automated=True)
        created_tasks.append("Post-Delivery Tasks")

    # Rule 6: Closed Lost -> Re-engage in 30 days
    elif deal_stage == "Closed Lost":
        due = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
        add_task(client_data['name'], "Call", due, "Low",
                 "Re-engagement: Check if new opportunity exists", automated=True)
        created_tasks.append("Lost Deal Re-engagement")

    return created_tasks


def get_due_tasks(filter_type="Today"):
    """
    Filter options: Today, Overdue, Upcoming
    """
    all_tasks = get_tasks()
    pending = [t for t in all_tasks if t.get('status') == "Pending"]
    now_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    today_date = datetime.datetime.now(IST).strftime("%Y-%m-%d")

    filtered = []
    for t in pending:
        due = t.get('due_date', '') or ''
        t_date = due.split(' ')[0] if due else ''

        if filter_type == "Overdue":
            if due < now_str:
                filtered.append(t)
        elif filter_type == "Today":
            if t_date == today_date and due >= now_str:
                filtered.append(t)
        elif filter_type == "Upcoming":
            if t_date > today_date:
                filtered.append(t)

    return sorted(filtered, key=lambda x: x.get('due_date', ''))


# ─── INTELLIGENT CRM ────────────────────────────────────────────────────────

class IntelligentCRM:
    """Market-intelligent CRM with auto-updating profiles."""

    def __init__(self):
        try:
            from settings_engine import load_settings
            self.settings = load_settings()
        except Exception:
            self.settings = {}
        self.hot_days = self.settings.get("crm_hot_threshold_days", 7)
        self.warm_days = self.settings.get("crm_warm_threshold_days", 30)
        self.cold_days = self.settings.get("crm_cold_threshold_days", 90)

    def get_customer_profile(self, customer_name: str) -> dict:
        """
        Complete customer profile with intelligence.

        Returns: {
            basic, purchase_history, intelligence, recommendations
        }
        """
        profile = {
            "basic": {"name": customer_name},
            "purchase_history": [],
            "intelligence": {},
            "recommendations": {},
        }

        # Try database first
        try:
            from database import get_all_customers
            customers = get_all_customers()
            for c in customers:
                if c.get("name", "").lower() == customer_name.lower():
                    profile["basic"] = {
                        "name": c.get("name"),
                        "city": c.get("city"),
                        "state": c.get("state"),
                        "contact": c.get("contact"),
                        "gstin": c.get("gstin"),
                        "category": c.get("category"),
                    }
                    profile["intelligence"] = {
                        "last_price": c.get("last_purchase_price"),
                        "last_date": c.get("last_purchase_date"),
                        "last_qty": c.get("last_purchase_qty"),
                        "preferred_grade": c.get("preferred_grades"),
                        "credit_terms": c.get("credit_terms"),
                        "expected_monthly_demand": c.get("expected_monthly_demand"),
                        "outstanding": c.get("outstanding_inr", 0),
                        "relationship_stage": c.get("relationship_stage", "cold"),
                        "next_followup": c.get("next_followup_date"),
                    }
                    break
        except Exception:
            pass

        # Fallback to customers DB (Phase 1 — was sales_parties.json)
        if not profile["basic"].get("city"):
            try:
                from customer_source import load_customers
                for p in load_customers():
                    if p.get("name", "").lower() == customer_name.lower():
                        profile["basic"].update({
                            "city": p.get("city"),
                            "state": p.get("state"),
                            "category": p.get("category"),
                        })
                        break
            except Exception:
                pass

        # Activity history
        activities = get_activities()
        customer_acts = [a for a in activities if a.get("client", "").lower() == customer_name.lower()]
        profile["purchase_history"] = customer_acts[-20:]

        # Days since last interaction
        if customer_acts:
            try:
                last_ts = customer_acts[-1].get("timestamp", "")
                last_dt = datetime.datetime.strptime(last_ts, "%Y-%m-%d %H:%M")
                days_since = (datetime.datetime.now() - last_dt).days
                profile["intelligence"]["days_since_last_contact"] = days_since
                profile["intelligence"]["auto_relationship_stage"] = (
                    "hot" if days_since <= self.hot_days else
                    "warm" if days_since <= self.warm_days else
                    "cold"
                )
            except Exception:
                pass

        # Recommendations
        city = profile["basic"].get("city", "")
        if city:
            try:
                from calculation_engine import BitumenCalculationEngine
                calc = BitumenCalculationEngine()
                sources = calc.find_best_sources(city, grade="VG30", top_n=1)
                if sources:
                    best = sources[0]
                    landed = best.get("landed_cost", 0)
                    profile["recommendations"] = {
                        "best_price_today": landed + 500,
                        "best_source": best.get("source", ""),
                        "margin_at_best_price": 500,
                        "suggested_action": self._suggest_action(profile),
                    }
            except Exception:
                pass

        return profile

    def _suggest_action(self, profile: dict) -> str:
        """Generate suggested action based on profile data."""
        stage = profile.get("intelligence", {}).get("auto_relationship_stage", "cold")
        days = profile.get("intelligence", {}).get("days_since_last_contact", 999)

        if stage == "hot":
            return "Active customer. Check for repeat order opportunity."
        elif stage == "warm":
            return f"Last contact {days} days ago. Send updated price offer."
        else:
            return f"Cold customer ({days} days). Reactivation call recommended."

    def auto_update_all_profiles(self):
        """
        Called daily by sync engine to update all customer profiles.
        Updates relationship_stage based on interaction frequency.
        """
        updated = 0
        try:
            from database import get_all_customers, get_connection
            customers = get_all_customers()
            activities = get_activities()

            with get_connection() as conn:
                for cust in customers:
                    name = cust.get("name", "")
                    if not name:
                        continue

                    # Find last activity for this customer
                    cust_acts = [a for a in activities if a.get("client", "").lower() == name.lower()]
                    if cust_acts:
                        try:
                            last_ts = cust_acts[-1].get("timestamp", "")
                            last_dt = datetime.datetime.strptime(last_ts, "%Y-%m-%d %H:%M")
                            days_since = (datetime.datetime.now() - last_dt).days
                            new_stage = (
                                "hot" if days_since <= self.hot_days else
                                "warm" if days_since <= self.warm_days else
                                "cold"
                            )

                            conn.execute(
                                "UPDATE customers SET relationship_stage = ?, updated_at = ? WHERE name = ?",
                                (new_stage, datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"), name)
                            )
                            updated += 1
                        except Exception:
                            pass
                conn.commit()
        except Exception:
            pass

        return updated

    # ── VIP Scoring ──────────────────────────────────────────────────────────

    def compute_vip_score(self, contact: dict) -> dict:
        """
        Compute VIP score for a contact using weighted composite algorithm.

        Weights: deal_value(35%) + purchase_frequency(25%) + recency(20%)
                + response_rate(10%) + relationship_age(10%)

        Returns: {vip_score (0-100), vip_tier, breakdown}
        """
        scores = {}

        # 1. Deal Value (lifetime_value_inr) — normalize to 0-100
        ltv = float(contact.get("lifetime_value_inr") or 0)
        # Scale: 0=0, 10L=50, 50L+=100
        scores["deal_value"] = min(100, (ltv / 5_00_000) * 100) if ltv > 0 else 0

        # 2. Purchase Frequency — based on contact_frequency field or deal count
        freq = float(contact.get("contact_frequency") or 0)
        # Scale: 0=0, 2/month=50, 5+/month=100
        scores["purchase_frequency"] = min(100, (freq / 5) * 100) if freq > 0 else 0

        # 3. Recency — days since last contact (lower = better)
        days_since = 999
        last_date_str = contact.get("last_contact_date") or ""
        if last_date_str:
            try:
                for fmt in ("%Y-%m-%d %H:%M IST", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        last_dt = datetime.datetime.strptime(last_date_str.strip(), fmt)
                        days_since = (datetime.datetime.now() - last_dt).days
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        # Scale: 0 days=100, 7=85, 30=50, 90=10, 180+=0
        if days_since <= 7:
            scores["recency"] = 100 - (days_since * 2)
        elif days_since <= 30:
            scores["recency"] = 85 - ((days_since - 7) * 1.5)
        elif days_since <= 90:
            scores["recency"] = 50 - ((days_since - 30) * 0.67)
        else:
            scores["recency"] = max(0, 10 - ((days_since - 90) * 0.11))

        # 4. Response Rate — whatsapp/email responsiveness
        resp = float(contact.get("response_rate") or contact.get("relationship_score") or 0)
        scores["response_rate"] = min(100, resp)

        # 5. Relationship Age — months since first contact
        created = contact.get("created_at") or ""
        months_since = 0
        if created:
            try:
                for fmt in ("%Y-%m-%d %H:%M IST", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                    try:
                        created_dt = datetime.datetime.strptime(created.strip(), fmt)
                        months_since = (datetime.datetime.now() - created_dt).days / 30
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        # Scale: 0 months=10, 6=40, 12=60, 24+=100
        scores["relationship_age"] = min(100, (months_since / 24) * 100) if months_since > 0 else 10

        # Weighted composite
        total = sum(scores[k] * VIP_WEIGHTS[k] for k in VIP_WEIGHTS)
        total = round(min(100, max(0, total)), 1)

        # Determine tier
        tier = "standard"
        for tier_name, threshold in sorted(VIP_TIERS.items(), key=lambda x: -x[1]):
            if total >= threshold:
                tier = tier_name
                break

        return {
            "vip_score": total,
            "vip_tier": tier,
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
        }

    def update_all_vip_scores(self) -> dict:
        """
        Batch-update VIP scores for all contacts in SQLite.
        Returns: {updated, errors, tier_counts}
        """
        updated = 0
        errors = 0
        tier_counts = {"platinum": 0, "gold": 0, "silver": 0, "standard": 0}

        try:
            from database import get_all_contacts, _get_conn
            contacts = get_all_contacts(active_only=True)
            conn = _get_conn()

            for contact in contacts:
                try:
                    result = self.compute_vip_score(contact)
                    conn.execute(
                        "UPDATE contacts SET vip_score = ?, vip_tier = ?, "
                        "updated_at = datetime('now') WHERE id = ?",
                        (result["vip_score"], result["vip_tier"],
                         contact.get("id"))
                    )
                    tier_counts[result["vip_tier"]] = tier_counts.get(result["vip_tier"], 0) + 1
                    updated += 1
                except Exception:
                    errors += 1

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"VIP score update failed: {e}")

        return {"updated": updated, "errors": errors, "tier_counts": tier_counts}

    def get_vip_summary(self) -> dict:
        """Get VIP tier distribution summary."""
        try:
            from database import _get_conn
            conn = _get_conn()
            rows = conn.execute(
                "SELECT vip_tier, COUNT(*) as cnt FROM contacts "
                "WHERE is_active = 1 GROUP BY vip_tier"
            ).fetchall()
            conn.close()
            return {row["vip_tier"]: row["cnt"] for row in rows}
        except Exception:
            return {}

    def get_crm_summary(self) -> dict:
        """Get CRM dashboard summary stats."""
        tasks = get_tasks()
        activities = get_activities()

        pending = [t for t in tasks if t.get("status") == "Pending"]
        completed = [t for t in tasks if t.get("status") == "Completed"]
        high_pri = [t for t in pending if t.get("priority") == "High"]

        # Count by type
        type_counts = {}
        for t in pending:
            tp = t.get("type", "Other")
            type_counts[tp] = type_counts.get(tp, 0) + 1

        # Customer stats
        try:
            from database import get_dashboard_stats
            db_stats = get_dashboard_stats()
        except Exception:
            db_stats = {}

        return {
            "total_tasks": len(tasks),
            "pending": len(pending),
            "completed": len(completed),
            "high_priority": len(high_pri),
            "tasks_by_type": type_counts,
            "total_activities": len(activities),
            "total_customers": db_stats.get("total_customers", 0),
            "total_suppliers": db_stats.get("total_suppliers", 0),
            "active_deals": db_stats.get("active_deals", 0),
        }

    def get_todays_targets(self) -> dict:
        """
        AI-selected target lists for today.

        Returns: {
            calls_due, whatsapp_due, emails_due,
            overdue_tasks, hot_customers, cold_reactivations
        }
        """
        today_tasks = get_due_tasks("Today")
        overdue = get_due_tasks("Overdue")

        calls = [t for t in today_tasks if t.get("type") == "Call"]
        whatsapp = [t for t in today_tasks if t.get("type") == "WhatsApp"]
        emails = [t for t in today_tasks if t.get("type") == "Email"]

        # Hot customers (from database)
        hot_customers = []
        cold_reactivations = []
        try:
            from database import get_all_customers
            customers = get_all_customers()
            for c in customers:
                stage = c.get("relationship_stage", "cold")
                if stage == "hot":
                    hot_customers.append(c.get("name", ""))
                elif stage == "cold" and c.get("last_purchase_price"):
                    cold_reactivations.append({
                        "name": c.get("name"),
                        "city": c.get("city"),
                        "last_price": c.get("last_purchase_price"),
                    })
        except Exception:
            pass

        return {
            "calls_due": calls,
            "whatsapp_due": whatsapp,
            "emails_due": emails,
            "overdue_tasks": overdue,
            "hot_customers": hot_customers,
            "cold_reactivations": cold_reactivations[:10],
        }


# --- INITIALIZATION ---

def _init_crm():
    """Initialize CRM: migrate JSON → SQLite if needed."""
    _migrate_json_to_sqlite()

try:
    _init_crm()
except Exception:
    pass
