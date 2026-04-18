"""
database.py — SQLite Database Layer for Bitumen Sales Dashboard
===============================================================

PPS Anantam (Gujarat, India) — B2B Bitumen Trading Platform

Replaces 27+ fragile JSON files with a single, transactional SQLite database.
Uses Python's built-in sqlite3 module only (no external ORM).

Each public function opens its own connection and closes it before returning,
ensuring thread safety for Streamlit / multi-threaded callers.

DB file: bitumen_dashboard.db  (created in the project directory)
Timestamps: IST (Asia/Kolkata, UTC+05:30)

Usage:
    from database import init_db, insert_customer, get_all_deals, ...
    init_db()  # call once at app startup
"""

import sqlite3
import os
import json
import queue
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IST = timezone(timedelta(hours=5, minutes=30))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitumen_dashboard.db")


def _now_ist() -> str:
    """Return current IST timestamp as ISO-8601 string."""
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _get_conn() -> sqlite3.Connection:
    """Open a new connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _rows_to_list(rows) -> list:
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTION POOL — Thread-safe reusable connections
# ═══════════════════════════════════════════════════════════════════════════

_pool = queue.Queue(maxsize=5)


def _create_connection() -> sqlite3.Connection:
    """Create a fresh SQLite connection with standard pragmas."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_connection():
    """
    Context manager returning a pooled connection.
    Auto-returns to pool on exit; creates new if pool empty.
    """
    try:
        conn = _pool.get_nowait()
    except queue.Empty:
        conn = _create_connection()
    try:
        yield conn
    finally:
        try:
            _pool.put_nowait(conn)
        except queue.Full:
            conn.close()


@contextmanager
def db_transaction():
    """
    Context manager for multi-statement transactions.

    Usage::

        with db_transaction() as conn:
            conn.execute("INSERT INTO ...", (...))
            conn.execute("UPDATE ...", (...))

    Auto-commits on success, auto-rollbacks on exception.
    """
    conn = _create_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# MONETARY & TIMESTAMP HELPERS
# ═══════════════════════════════════════════════════════════════════════════

# Columns that store monetary values — rounded on write
MONETARY_DEAL_COLS = frozenset({
    "buy_price_per_mt", "sell_price_per_mt", "landed_cost_per_mt",
    "margin_per_mt", "freight_per_mt", "total_value_inr",
    "payment_received_inr", "gst_amount", "competitor_price",
    "credit_limit_inr", "outstanding_inr", "last_purchase_price",
    "last_deal_price", "cost_per_mt", "estimated_margin_per_mt",
    "estimated_value_inr", "old_landed_cost", "new_landed_cost",
    "savings_per_mt",
})


def _round_money(value, decimals: int = 2) -> float:
    """Round monetary values consistently to avoid float drift."""
    if value is None:
        return 0.0
    return round(float(value), decimals)


def _round_monetary_fields(data: dict) -> dict:
    """Round all monetary fields in a data dict."""
    for col in MONETARY_DEAL_COLS:
        if col in data and data[col] is not None:
            data[col] = _round_money(data[col])
    return data


def _parse_timestamp(ts: str):
    """Parse an IST timestamp string to a datetime object, or None."""
    if not ts:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(ts, fmt)
            return dt.replace(tzinfo=IST)
        except ValueError:
            continue
    return None


def _days_since(ts: str):
    """Return the number of days since a timestamp string, or None."""
    dt = _parse_timestamp(ts)
    if not dt:
        return None
    now = datetime.now(IST)
    return (now - dt).days


def _is_within_days(ts: str, days: int) -> bool:
    """Check if a timestamp is within the last N days."""
    d = _days_since(ts)
    return d is not None and d <= days


# Transaction-aware insert/update (caller manages commit/rollback)

def _insert_row_tx(conn: sqlite3.Connection, table: str, data: dict) -> int:
    """Insert within an existing transaction (caller manages commit)."""
    _validate_table(table)
    col_names = _validate_columns(data.keys())
    cols = ", ".join(col_names)
    placeholders = ", ".join(["?"] * len(data))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    cur = conn.cursor()
    cur.execute(sql, list(data.values()))
    return cur.lastrowid


def _update_row_tx(conn: sqlite3.Connection, table: str, row_id: int, data: dict):
    """Update within an existing transaction (caller manages commit)."""
    _validate_table(table)
    col_names = _validate_columns(data.keys())
    set_clause = ", ".join([f"{k} = ?" for k in col_names])
    sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"
    conn.execute(sql, list(data.values()) + [row_id])


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMA — Table Creation DDL
# ═══════════════════════════════════════════════════════════════════════════

_TABLES = {

    "suppliers": """
        CREATE TABLE IF NOT EXISTS suppliers (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            name                    TEXT NOT NULL,
            category                TEXT,
            city                    TEXT,
            state                   TEXT,
            contact                 TEXT,
            gstin                   TEXT,
            pan                     TEXT,
            credit_terms            TEXT,
            credit_limit_inr        REAL DEFAULT 0,
            payment_reliability_pct REAL DEFAULT 0,
            preferred_grades        TEXT,   -- JSON array, e.g. '["VG30","VG40"]'
            avg_monthly_volume_mt   REAL DEFAULT 0,
            last_deal_price         REAL,
            last_deal_date          TEXT,
            last_deal_qty           REAL,
            seasonality_tags        TEXT,
            relationship_stage      TEXT DEFAULT 'cold',
            next_followup_date      TEXT,
            notes                   TEXT,
            is_active               INTEGER DEFAULT 1,
            marked_for_purchase     INTEGER DEFAULT 0,
            created_at              TEXT,
            updated_at              TEXT
        );
    """,

    "customers": """
        CREATE TABLE IF NOT EXISTS customers (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            name                    TEXT NOT NULL,
            category                TEXT,
            city                    TEXT,
            state                   TEXT,
            contact                 TEXT,
            gstin                   TEXT,
            address                 TEXT,
            credit_terms            TEXT,
            credit_limit_inr        REAL DEFAULT 0,
            outstanding_inr         REAL DEFAULT 0,
            preferred_grades        TEXT,   -- JSON array
            avg_monthly_demand_mt   REAL DEFAULT 0,
            last_purchase_price     REAL,
            last_purchase_date      TEXT,
            last_purchase_qty       REAL,
            expected_monthly_demand REAL DEFAULT 0,
            seasonality_tags        TEXT,
            peak_months             TEXT,
            relationship_stage      TEXT DEFAULT 'cold',
            next_followup_date      TEXT,
            notes                   TEXT,
            is_active               INTEGER DEFAULT 1,
            created_at              TEXT,
            updated_at              TEXT
        );
    """,

    "deals": """
        CREATE TABLE IF NOT EXISTS deals (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_number             TEXT UNIQUE,
            customer_id             INTEGER,
            supplier_id             INTEGER,
            grade                   TEXT,
            quantity_mt             REAL,
            packaging               TEXT,
            buy_price_per_mt        REAL,
            sell_price_per_mt       REAL,
            landed_cost_per_mt      REAL,
            margin_per_mt           REAL,
            margin_pct              REAL,
            source_location         TEXT,
            destination             TEXT,
            distance_km             REAL,
            freight_per_mt          REAL,
            stage                   TEXT DEFAULT 'enquiry',
            status                  TEXT DEFAULT 'active',
            enquiry_date            TEXT,
            quote_date              TEXT,
            po_date                 TEXT,
            dispatch_date           TEXT,
            delivery_date           TEXT,
            payment_date            TEXT,
            total_value_inr         REAL,
            payment_received_inr    REAL DEFAULT 0,
            gst_amount              REAL,
            win_probability_pct     REAL DEFAULT 50,
            loss_reason             TEXT,
            competitor_price        REAL,
            client_benefit_pct      REAL,
            created_at              TEXT,
            updated_at              TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
    """,

    "price_history": """
        CREATE TABLE IF NOT EXISTS price_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time   TEXT,
            benchmark   TEXT,
            price       REAL,
            currency    TEXT,
            source      TEXT,
            validated   INTEGER DEFAULT 1
        );
    """,

    "fx_history": """
        CREATE TABLE IF NOT EXISTS fx_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time       TEXT,
            from_currency   TEXT,
            to_currency     TEXT,
            rate            REAL,
            source          TEXT
        );
    """,

    "inventory": """
        CREATE TABLE IF NOT EXISTS inventory (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            location          TEXT,
            grade             TEXT,
            quantity_mt       REAL,
            cost_per_mt       REAL,
            status            TEXT,
            expected_arrival  TEXT,
            vessel_name       TEXT,
            updated_at        TEXT
        );
    """,

    "communications": """
        CREATE TABLE IF NOT EXISTS communications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id     INTEGER,
            supplier_id     INTEGER,
            channel         TEXT,
            direction       TEXT,
            subject         TEXT,
            content         TEXT,
            template_used   TEXT,
            sent_at         TEXT,
            status          TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
    """,

    "opportunities": """
        CREATE TABLE IF NOT EXISTS opportunities (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            type                    TEXT,
            title                   TEXT,
            description             TEXT,
            customer_id             INTEGER,
            supplier_id             INTEGER,
            estimated_margin_per_mt REAL,
            estimated_volume_mt     REAL,
            estimated_value_inr     REAL,
            trigger_reason          TEXT,
            old_landed_cost         REAL,
            new_landed_cost         REAL,
            savings_per_mt          REAL,
            recommended_action      TEXT,
            whatsapp_template       TEXT,
            email_template          TEXT,
            call_script             TEXT,
            priority                TEXT,
            status                  TEXT DEFAULT 'new',
            valid_until             TEXT,
            created_at              TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
    """,

    "sync_logs": """
        CREATE TABLE IF NOT EXISTS sync_logs (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type         TEXT,
            started_at        TEXT,
            completed_at      TEXT,
            status            TEXT,
            apis_called       INTEGER,
            apis_succeeded    INTEGER,
            records_updated   INTEGER,
            errors            TEXT,
            next_scheduled    TEXT
        );
    """,

    "missing_inputs": """
        CREATE TABLE IF NOT EXISTS missing_inputs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name      TEXT,
            entity_type     TEXT,
            entity_id       INTEGER,
            reason          TEXT,
            priority        TEXT,
            status          TEXT DEFAULT 'pending',
            collected_value TEXT,
            collected_at    TEXT,
            created_at      TEXT
        );
    """,

    "email_queue": """
        CREATE TABLE IF NOT EXISTS email_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            to_email        TEXT NOT NULL,
            cc              TEXT,
            bcc             TEXT,
            subject         TEXT NOT NULL,
            body_html       TEXT,
            body_text       TEXT,
            email_type      TEXT,
            customer_id     INTEGER,
            deal_id         INTEGER,
            attachments     TEXT,
            status          TEXT DEFAULT 'draft',
            error_message   TEXT,
            smtp_message_id TEXT,
            retry_count     INTEGER DEFAULT 0,
            max_retries     INTEGER DEFAULT 3,
            scheduled_at    TEXT,
            sent_at         TEXT,
            created_at      TEXT,
            updated_at      TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """,

    "whatsapp_queue": """
        CREATE TABLE IF NOT EXISTS whatsapp_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            to_number       TEXT NOT NULL,
            message_type    TEXT NOT NULL,
            template_name   TEXT,
            template_params TEXT,
            session_text    TEXT,
            customer_id     INTEGER,
            deal_id         INTEGER,
            broadcast_id    TEXT,
            status          TEXT DEFAULT 'draft',
            wa_message_id   TEXT,
            error_message   TEXT,
            error_code      TEXT,
            retry_count     INTEGER DEFAULT 0,
            max_retries     INTEGER DEFAULT 3,
            scheduled_at    TEXT,
            sent_at         TEXT,
            delivered_at    TEXT,
            read_at         TEXT,
            created_at      TEXT,
            updated_at      TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """,

    "whatsapp_sessions": """
        CREATE TABLE IF NOT EXISTS whatsapp_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number    TEXT NOT NULL UNIQUE,
            session_start   TEXT NOT NULL,
            session_expires TEXT NOT NULL,
            customer_id     INTEGER,
            last_message    TEXT,
            created_at      TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """,

    "whatsapp_incoming": """
        CREATE TABLE IF NOT EXISTS whatsapp_incoming (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            from_number     TEXT NOT NULL,
            message_type    TEXT,
            message_text    TEXT,
            media_url       TEXT,
            wa_message_id   TEXT,
            customer_id     INTEGER,
            processed       INTEGER DEFAULT 0,
            received_at     TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """,

    "director_briefings": """
        CREATE TABLE IF NOT EXISTS director_briefings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            briefing_date   TEXT,
            generated_at    TEXT,
            briefing_data   TEXT,
            sent_email      INTEGER DEFAULT 0,
            sent_whatsapp   INTEGER DEFAULT 0,
            created_at      TEXT
        );
    """,

    "daily_logs": """
        CREATE TABLE IF NOT EXISTS daily_logs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date            TEXT,
            author              TEXT,
            entry_type          TEXT,
            customer_name       TEXT,
            channel             TEXT,
            notes               TEXT,
            outcome             TEXT,
            followup_date       TEXT,
            intel_source        TEXT,
            intel_confidence    TEXT,
            metadata            TEXT,
            created_at          TEXT
        );
    """,

    "alerts": """
        CREATE TABLE IF NOT EXISTS alerts (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type          TEXT,
            priority            TEXT,
            title               TEXT,
            description         TEXT,
            data                TEXT,
            recommended_action  TEXT,
            action_template     TEXT,
            status              TEXT DEFAULT 'new',
            snoozed_until       TEXT,
            created_at          TEXT,
            acted_at            TEXT,
            acted_by            TEXT
        );
    """,

    # ── Phase C: Universal Action + RBAC tables ────────────────────────────

    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT NOT NULL UNIQUE,
            display_name    TEXT,
            role            TEXT NOT NULL DEFAULT 'viewer',
            pin_hash        TEXT NOT NULL,
            email           TEXT,
            whatsapp_number TEXT,
            is_active       INTEGER DEFAULT 1,
            last_login      TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );
    """,

    "audit_log": """
        CREATE TABLE IF NOT EXISTS audit_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            username        TEXT,
            action          TEXT NOT NULL,
            resource        TEXT,
            details         TEXT,
            ip_address      TEXT,
            created_at      TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """,

    "recipient_lists": """
        CREATE TABLE IF NOT EXISTS recipient_lists (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            list_name       TEXT NOT NULL,
            list_type       TEXT DEFAULT 'email',
            recipients      TEXT NOT NULL,
            created_by      TEXT,
            is_active       INTEGER DEFAULT 1,
            created_at      TEXT,
            updated_at      TEXT
        );
    """,

    "source_registry": """
        CREATE TABLE IF NOT EXISTS source_registry (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_key      TEXT NOT NULL UNIQUE,
            source_name     TEXT NOT NULL,
            category        TEXT,
            provider        TEXT,
            api_url         TEXT,
            auth_type       TEXT DEFAULT 'none',
            status          TEXT DEFAULT 'active',
            refresh_minutes INTEGER DEFAULT 60,
            keywords        TEXT,
            state_mapping   TEXT,
            last_success    TEXT,
            last_error      TEXT,
            error_count     INTEGER DEFAULT 0,
            output_tables   TEXT,
            notes           TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );
    """,

    # ── Phase D: Integrations & Communication tables ─────────────────────────

    "chat_messages": """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            sender_type     TEXT NOT NULL,
            sender_name     TEXT,
            sender_id       INTEGER,
            message_text    TEXT NOT NULL,
            attachment_path TEXT,
            is_read         INTEGER DEFAULT 0,
            created_at      TEXT
        );
    """,

    "share_links": """
        CREATE TABLE IF NOT EXISTS share_links (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            link_token      TEXT NOT NULL UNIQUE,
            page_name       TEXT NOT NULL,
            filters_json    TEXT,
            created_by      TEXT,
            permissions     TEXT DEFAULT 'view',
            password_hash   TEXT,
            expires_at      TEXT,
            max_views       INTEGER DEFAULT 0,
            view_count      INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            last_accessed   TEXT,
            created_at      TEXT
        );
    """,

    "share_schedules": """
        CREATE TABLE IF NOT EXISTS share_schedules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_name   TEXT NOT NULL,
            page_name       TEXT NOT NULL,
            content_type    TEXT,
            channel         TEXT NOT NULL,
            recipients_json TEXT NOT NULL,
            frequency       TEXT NOT NULL,
            day_of_week     TEXT,
            day_of_month    INTEGER,
            time_ist        TEXT DEFAULT '09:00',
            is_active       INTEGER DEFAULT 1,
            last_run        TEXT,
            next_run        TEXT,
            run_count       INTEGER DEFAULT 0,
            created_by      TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );
    """,

    # ── Document Management tables ─────────────────────────────────────

    "company_master": """
        CREATE TABLE IF NOT EXISTS company_master (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            legal_name      TEXT NOT NULL,
            short_name      TEXT,
            gstin           TEXT,
            pan             TEXT,
            cin             TEXT,
            address_line1   TEXT,
            address_line2   TEXT,
            city            TEXT,
            pincode         TEXT,
            state           TEXT,
            state_code      TEXT,
            full_address    TEXT,
            hsn_code        TEXT,
            phone           TEXT,
            email           TEXT,
            website         TEXT,
            logo_path       TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );
    """,

    "bank_master": """
        CREATE TABLE IF NOT EXISTS bank_master (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id      INTEGER DEFAULT 1,
            bank_name       TEXT NOT NULL,
            ac_no           TEXT NOT NULL,
            ifsc            TEXT,
            branch          TEXT,
            is_primary      INTEGER DEFAULT 0,
            created_at      TEXT,
            updated_at      TEXT,
            FOREIGN KEY (company_id) REFERENCES company_master(id)
        );
    """,

    "terms_master": """
        CREATE TABLE IF NOT EXISTS terms_master (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            term_key        TEXT UNIQUE NOT NULL,
            term_text       TEXT NOT NULL,
            category        TEXT DEFAULT 'general',
            sort_order      INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            created_at      TEXT,
            updated_at      TEXT
        );
    """,

    "purchase_orders": """
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number       TEXT UNIQUE NOT NULL,
            deal_id         INTEGER,
            supplier_id     INTEGER,
            supplier_name   TEXT,
            supplier_gstin  TEXT,
            supplier_address TEXT,
            items_json      TEXT,
            logistics_json  TEXT,
            totals_json     TEXT,
            notes           TEXT,
            status          TEXT DEFAULT 'draft',
            pdf_path        TEXT,
            created_by      TEXT DEFAULT 'Admin',
            created_at      TEXT,
            updated_at      TEXT,
            FOREIGN KEY (deal_id) REFERENCES deals(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
    """,

    "sales_orders": """
        CREATE TABLE IF NOT EXISTS sales_orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            so_number       TEXT UNIQUE NOT NULL,
            deal_id         INTEGER,
            customer_id     INTEGER,
            customer_name   TEXT,
            customer_gstin  TEXT,
            customer_address TEXT,
            items_json      TEXT,
            logistics_json  TEXT,
            totals_json     TEXT,
            notes           TEXT,
            status          TEXT DEFAULT 'draft',
            pdf_path        TEXT,
            created_by      TEXT DEFAULT 'Admin',
            created_at      TEXT,
            updated_at      TEXT,
            FOREIGN KEY (deal_id) REFERENCES deals(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """,

    "payment_orders": """
        CREATE TABLE IF NOT EXISTS payment_orders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pay_number      TEXT UNIQUE NOT NULL,
            deal_id         INTEGER,
            po_id           INTEGER,
            so_id           INTEGER,
            supplier_name   TEXT,
            customer_name   TEXT,
            purchase_payable REAL DEFAULT 0,
            sales_receivable REAL DEFAULT 0,
            transport_cost  REAL DEFAULT 0,
            profit_json     TEXT,
            notes           TEXT,
            status          TEXT DEFAULT 'draft',
            pdf_path        TEXT,
            created_by      TEXT DEFAULT 'Admin',
            created_at      TEXT,
            updated_at      TEXT,
            FOREIGN KEY (deal_id) REFERENCES deals(id),
            FOREIGN KEY (po_id) REFERENCES purchase_orders(id),
            FOREIGN KEY (so_id) REFERENCES sales_orders(id)
        );
    """,

    "_doc_counters": """
        CREATE TABLE IF NOT EXISTS _doc_counters (
            doc_type    TEXT PRIMARY KEY,
            last_date   TEXT,
            last_seq    INTEGER DEFAULT 0
        );
    """,

    "transporters": """
        CREATE TABLE IF NOT EXISTS transporters (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            contact         TEXT,
            gstin           TEXT,
            pan             TEXT,
            city            TEXT,
            state           TEXT,
            address         TEXT,
            vehicle_types   TEXT,
            rate_per_km     REAL,
            bank_name       TEXT,
            bank_ac_no      TEXT,
            bank_ifsc       TEXT,
            is_active       INTEGER DEFAULT 1,
            notes           TEXT,
            created_at      TEXT,
            updated_at      TEXT
        );
    """,

    "comm_tracking": """
        CREATE TABLE IF NOT EXISTS comm_tracking (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id     TEXT NOT NULL UNIQUE,
            channel         TEXT NOT NULL,
            action          TEXT NOT NULL,
            sender          TEXT,
            recipient_name  TEXT,
            recipient_addr  TEXT,
            page_name       TEXT,
            content_type    TEXT,
            content_summary TEXT,
            delivery_status TEXT DEFAULT 'pending',
            error_message   TEXT,
            created_at      TEXT,
            delivered_at    TEXT
        );
    """,

    # ── CRM Automation Tables (Phase 6) ────────────────────────────────────

    "contacts": """
        CREATE TABLE IF NOT EXISTS contacts (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL,
            company_name        TEXT,
            contact_type        TEXT NOT NULL DEFAULT 'prospect',
            category            TEXT,
            buyer_seller_tag    TEXT DEFAULT 'unknown',
            city                TEXT,
            state               TEXT,
            mobile1             TEXT,
            mobile2             TEXT,
            email               TEXT,
            gstin               TEXT,
            pan                 TEXT,
            address             TEXT,
            pincode             TEXT,
            products_dealt      TEXT,
            preferred_language  TEXT DEFAULT 'en',
            whatsapp_opted_in   INTEGER DEFAULT 0,
            email_opted_in      INTEGER DEFAULT 1,
            last_contact_date   TEXT,
            last_contact_channel TEXT,
            next_rotation_date  TEXT,
            rotation_priority   REAL DEFAULT 0.0,
            relationship_score  REAL DEFAULT 0.0,
            lifetime_value_inr  REAL DEFAULT 0.0,
            contact_frequency   INTEGER DEFAULT 0,
            source              TEXT,
            customer_id         INTEGER,
            supplier_id         INTEGER,
            is_active           INTEGER DEFAULT 1,
            notes               TEXT,
            created_at          TEXT,
            updated_at          TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
    """,

    "contact_rotation_log": """
        CREATE TABLE IF NOT EXISTS contact_rotation_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id      INTEGER NOT NULL,
            rotation_date   TEXT NOT NULL,
            channel         TEXT,
            status          TEXT DEFAULT 'pending',
            message_type    TEXT,
            error_message   TEXT,
            created_at      TEXT,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        );
    """,

    "festival_broadcasts": """
        CREATE TABLE IF NOT EXISTS festival_broadcasts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            festival_name   TEXT NOT NULL,
            festival_date   TEXT NOT NULL,
            broadcast_status TEXT DEFAULT 'scheduled',
            total_contacts  INTEGER DEFAULT 0,
            sent_whatsapp   INTEGER DEFAULT 0,
            sent_email      INTEGER DEFAULT 0,
            failed_count    INTEGER DEFAULT 0,
            started_at      TEXT,
            completed_at    TEXT,
            created_at      TEXT
        );
    """,

    "price_update_log": """
        CREATE TABLE IF NOT EXISTS price_update_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            price_key       TEXT NOT NULL,
            old_value       REAL,
            new_value       REAL,
            change_pct      REAL,
            changed_by      TEXT DEFAULT 'system',
            broadcast_sent  INTEGER DEFAULT 0,
            broadcast_id    TEXT,
            created_at      TEXT
        );
    """,
}

# Indexes for common query patterns
_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_deals_stage       ON deals(stage);",
    "CREATE INDEX IF NOT EXISTS idx_deals_status      ON deals(status);",
    "CREATE INDEX IF NOT EXISTS idx_deals_customer    ON deals(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_deals_supplier    ON deals(supplier_id);",
    "CREATE INDEX IF NOT EXISTS idx_price_benchmark   ON price_history(benchmark, date_time);",
    "CREATE INDEX IF NOT EXISTS idx_fx_pair           ON fx_history(from_currency, to_currency, date_time);",
    "CREATE INDEX IF NOT EXISTS idx_comms_customer    ON communications(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_comms_supplier    ON communications(supplier_id);",
    "CREATE INDEX IF NOT EXISTS idx_opps_status       ON opportunities(status);",
    "CREATE INDEX IF NOT EXISTS idx_missing_status    ON missing_inputs(status);",
    "CREATE INDEX IF NOT EXISTS idx_suppliers_active  ON suppliers(is_active);",
    "CREATE INDEX IF NOT EXISTS idx_customers_active  ON customers(is_active);",
    "CREATE INDEX IF NOT EXISTS idx_inventory_grade   ON inventory(grade);",
    # Email queue indexes
    "CREATE INDEX IF NOT EXISTS idx_email_queue_status    ON email_queue(status);",
    "CREATE INDEX IF NOT EXISTS idx_email_queue_type      ON email_queue(email_type);",
    "CREATE INDEX IF NOT EXISTS idx_email_queue_customer  ON email_queue(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled ON email_queue(scheduled_at);",
    # WhatsApp queue indexes
    "CREATE INDEX IF NOT EXISTS idx_wa_queue_status       ON whatsapp_queue(status);",
    "CREATE INDEX IF NOT EXISTS idx_wa_queue_customer     ON whatsapp_queue(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_wa_queue_type         ON whatsapp_queue(message_type);",
    "CREATE INDEX IF NOT EXISTS idx_wa_session_phone      ON whatsapp_sessions(phone_number);",
    "CREATE INDEX IF NOT EXISTS idx_wa_incoming_from      ON whatsapp_incoming(from_number);",
    # Director / Daily log / Alert indexes
    "CREATE INDEX IF NOT EXISTS idx_briefings_date        ON director_briefings(briefing_date);",
    "CREATE INDEX IF NOT EXISTS idx_daily_logs_date       ON daily_logs(log_date);",
    "CREATE INDEX IF NOT EXISTS idx_daily_logs_type       ON daily_logs(entry_type);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_status         ON alerts(status);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_priority       ON alerts(priority);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_type           ON alerts(alert_type);",
    # Phase C: RBAC + Action + Ops indexes
    "CREATE INDEX IF NOT EXISTS idx_users_username          ON users(username);",
    "CREATE INDEX IF NOT EXISTS idx_users_role              ON users(role);",
    "CREATE INDEX IF NOT EXISTS idx_audit_user              ON audit_log(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_action            ON audit_log(action);",
    "CREATE INDEX IF NOT EXISTS idx_audit_created           ON audit_log(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_recip_name              ON recipient_lists(list_name);",
    "CREATE INDEX IF NOT EXISTS idx_source_reg_key          ON source_registry(source_key);",
    "CREATE INDEX IF NOT EXISTS idx_source_reg_status       ON source_registry(status);",
    # Phase D: Integrations & Communication indexes
    "CREATE INDEX IF NOT EXISTS idx_chat_convo              ON chat_messages(conversation_id);",
    "CREATE INDEX IF NOT EXISTS idx_chat_created            ON chat_messages(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_share_links_token       ON share_links(link_token);",
    "CREATE INDEX IF NOT EXISTS idx_share_links_active      ON share_links(is_active);",
    "CREATE INDEX IF NOT EXISTS idx_share_sched_active      ON share_schedules(is_active);",
    "CREATE INDEX IF NOT EXISTS idx_share_sched_next        ON share_schedules(next_run);",
    "CREATE INDEX IF NOT EXISTS idx_comm_track_channel      ON comm_tracking(channel);",
    "CREATE INDEX IF NOT EXISTS idx_comm_track_status       ON comm_tracking(delivery_status);",
    "CREATE INDEX IF NOT EXISTS idx_comm_track_created      ON comm_tracking(created_at);",
    # Transporter indexes
    "CREATE INDEX IF NOT EXISTS idx_transporters_active     ON transporters(is_active);",
    "CREATE INDEX IF NOT EXISTS idx_transporters_city       ON transporters(city);",
    # CRM Automation indexes (contacts)
    "CREATE INDEX IF NOT EXISTS idx_contacts_type           ON contacts(contact_type);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_category       ON contacts(category);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_city           ON contacts(city);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_state          ON contacts(state);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_buyer_seller   ON contacts(buyer_seller_tag);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_rotation       ON contacts(next_rotation_date);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_mobile         ON contacts(mobile1);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_email          ON contacts(email);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_active         ON contacts(is_active);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_wa_optin       ON contacts(whatsapp_opted_in);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_last_contact   ON contacts(last_contact_date);",
    "CREATE INDEX IF NOT EXISTS idx_rotation_log_contact    ON contact_rotation_log(contact_id);",
    "CREATE INDEX IF NOT EXISTS idx_rotation_log_date       ON contact_rotation_log(rotation_date);",
    "CREATE INDEX IF NOT EXISTS idx_rotation_log_status     ON contact_rotation_log(status);",
    "CREATE INDEX IF NOT EXISTS idx_festival_bc_date        ON festival_broadcasts(festival_date);",
    "CREATE INDEX IF NOT EXISTS idx_festival_bc_status      ON festival_broadcasts(broadcast_status);",
    "CREATE INDEX IF NOT EXISTS idx_price_log_key           ON price_update_log(price_key);",
    "CREATE INDEX IF NOT EXISTS idx_price_log_created       ON price_update_log(created_at);",
    # Document Management indexes
    "CREATE INDEX IF NOT EXISTS idx_po_supplier             ON purchase_orders(supplier_id);",
    "CREATE INDEX IF NOT EXISTS idx_po_deal                 ON purchase_orders(deal_id);",
    "CREATE INDEX IF NOT EXISTS idx_po_status               ON purchase_orders(status);",
    "CREATE INDEX IF NOT EXISTS idx_po_created              ON purchase_orders(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_so_customer             ON sales_orders(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_so_deal                 ON sales_orders(deal_id);",
    "CREATE INDEX IF NOT EXISTS idx_so_status               ON sales_orders(status);",
    "CREATE INDEX IF NOT EXISTS idx_so_created              ON sales_orders(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_pay_deal                ON payment_orders(deal_id);",
    "CREATE INDEX IF NOT EXISTS idx_pay_status              ON payment_orders(status);",
    "CREATE INDEX IF NOT EXISTS idx_pay_created             ON payment_orders(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_terms_category          ON terms_master(category);",
    "CREATE INDEX IF NOT EXISTS idx_bank_company            ON bank_master(company_id);",
]


# ═══════════════════════════════════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════════════════════════════════

def init_db():
    """
    Create all tables and indexes if they do not already exist.
    Safe to call multiple times (uses IF NOT EXISTS).
    Also runs incremental schema migrations.
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        for table_name, ddl in _TABLES.items():
            cur.execute(ddl)
        for idx_sql in _INDEXES:
            cur.execute(idx_sql)
        # Migrations: add columns if missing
        for tbl in ("customers", "suppliers"):
            for col, col_type in [("email", "TEXT"), ("whatsapp_number", "TEXT")]:
                try:
                    cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass  # Column already exists
        conn.commit()
    finally:
        conn.close()

    # Run incremental schema migrations
    _run_schema_migrations()

    # Initialize infra demand intelligence tables
    try:
        from infra_demand_engine import init_infra_tables
        init_infra_tables()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMA MIGRATIONS — Incremental, versioned
# ═══════════════════════════════════════════════════════════════════════════

def _run_schema_migrations():
    """Apply incremental schema migrations. Uses _schema_version tracker."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _schema_version (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                version     INTEGER NOT NULL,
                description TEXT,
                applied_at  TEXT
            )
        """)
        conn.commit()

        row = cur.execute("SELECT MAX(version) as v FROM _schema_version").fetchone()
        current_version = row["v"] if row and row["v"] else 0

        migrations = [
            (1, "Add CHECK constraints + fix NULL data", _migration_001_fix_data),
            (2, "Add UNIQUE indexes on business keys", _migration_002_unique_indexes),
            (3, "Add crm_tasks table", _migration_003_crm_tasks),
            (4, "Seed company_master, bank_master, terms_master", _migration_004_seed_company_data),
            (5, "Add transporters + payment_orders columns + seed new clauses", _migration_005_transporters_and_payment_cols),
            (6, "Add CRM automation tables: contacts, rotation log, festival, price log", _migration_006_crm_automation),
            (7, "Add VIP scoring, DPDP consent columns, sms_queue table", _migration_007_vip_and_sms),
            (8, "Phase 1: customer_profiles + import_history tables",
             _migration_008_phase1_import_tables),
        ]

        for version, desc, migration_fn in migrations:
            if version > current_version:
                try:
                    migration_fn(cur)
                    cur.execute(
                        "INSERT INTO _schema_version (version, description, applied_at) "
                        "VALUES (?, ?, ?)",
                        (version, desc, _now_ist()),
                    )
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    # Log but don't crash — migrations are best-effort
                    import logging
                    logging.getLogger("database").warning(
                        "Migration %d failed: %s", version, e
                    )
    finally:
        conn.close()


def _migration_001_fix_data(cur):
    """Fix NULL customer names and negative quantities."""
    cur.execute("UPDATE customers SET name = 'UNKNOWN' WHERE name IS NULL OR name = ''")
    cur.execute("UPDATE deals SET quantity_mt = ABS(quantity_mt) WHERE quantity_mt IS NOT NULL AND quantity_mt < 0")


def _migration_002_unique_indexes(cur):
    """Add unique composite index on customers to prevent duplicates."""
    try:
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_name_contact "
            "ON customers(name, contact) WHERE contact IS NOT NULL AND contact != ''"
        )
    except Exception:
        pass  # Skip if duplicates exist


def _migration_003_crm_tasks(cur):
    """Add crm_tasks table for CRM consolidation."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crm_tasks (
            id              TEXT PRIMARY KEY,
            client          TEXT NOT NULL,
            task_type       TEXT NOT NULL,
            due_date        TEXT,
            status          TEXT DEFAULT 'Pending',
            priority        TEXT DEFAULT 'Medium',
            note            TEXT,
            outcome         TEXT,
            automated       INTEGER DEFAULT 0,
            created_at      TEXT,
            completed_at    TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crm_tasks_status ON crm_tasks(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crm_tasks_client ON crm_tasks(client)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crm_tasks_due    ON crm_tasks(due_date)")


def _migration_004_seed_company_data(cur):
    """Seed company_master, bank_master, terms_master from company_config.py."""
    try:
        from company_config import COMPANY_PROFILE as CP
    except ImportError:
        return

    now = _now_ist()

    # Seed company_master (only if empty)
    row = cur.execute("SELECT COUNT(*) as c FROM company_master").fetchone()
    if row["c"] == 0:
        cur.execute(
            "INSERT INTO company_master "
            "(legal_name, short_name, gstin, pan, cin, address_line1, address_line2, "
            " city, pincode, state, state_code, full_address, hsn_code, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                CP.get("legal_name", ""), CP.get("short_name", ""),
                CP.get("gst_no", ""), CP.get("pan_no", ""), CP.get("cin_no", ""),
                CP.get("address_line1", ""), CP.get("address_line2", ""),
                CP.get("city", ""), CP.get("pincode", ""),
                CP.get("state", ""), CP.get("state_code", ""),
                CP.get("full_address", ""), CP.get("hsn_code", ""),
                now, now,
            ),
        )

    # Seed bank_master (only if empty)
    row = cur.execute("SELECT COUNT(*) as c FROM bank_master").fetchone()
    if row["c"] == 0:
        bd = CP.get("bank_details", {})
        cur.execute(
            "INSERT INTO bank_master "
            "(company_id, bank_name, ac_no, ifsc, branch, is_primary, created_at, updated_at) "
            "VALUES (1,?,?,?,?,1,?,?)",
            (bd.get("bank_name", ""), bd.get("ac_no", ""),
             bd.get("ifsc", ""), bd.get("branch", ""), now, now),
        )

    # Seed terms_master (only if empty)
    row = cur.execute("SELECT COUNT(*) as c FROM terms_master").fetchone()
    if row["c"] == 0:
        terms = CP.get("terms", [])
        for i, term_text in enumerate(terms):
            key = f"term_{i+1}"
            cat = "delivery" if i == 0 else "payment" if i == 2 else "legal"
            cur.execute(
                "INSERT INTO terms_master (term_key, term_text, category, sort_order, is_active, created_at, updated_at) "
                "VALUES (?,?,?,?,1,?,?)",
                (key, term_text, cat, i + 1, now, now),
            )
        # Add special clauses
        for key, attr in [
            ("declaration", "declaration"),
            ("interest_clause", "interest_clause"),
            ("complaint_clause", "complaint_clause"),
            ("driver_clause", "driver_clause"),
        ]:
            text = CP.get(attr, "")
            if text:
                cur.execute(
                    "INSERT INTO terms_master (term_key, term_text, category, sort_order, is_active, created_at, updated_at) "
                    "VALUES (?,?,?,?,1,?,?)",
                    (key, text, "clause", 100, now, now),
                )


def _migration_005_transporters_and_payment_cols(cur):
    """Add transporters table columns, payment_orders enhancements, seed new clauses."""
    # Add new columns to payment_orders (idempotent via try/except)
    new_cols = [
        ("payment_mode", "TEXT DEFAULT 'NEFT'"),
        ("purchase_due_date", "TEXT"),
        ("sales_expected_date", "TEXT"),
        ("purchase_status", "TEXT DEFAULT 'Pending'"),
        ("sales_status", "TEXT DEFAULT 'Pending'"),
        ("transport_amount", "REAL DEFAULT 0"),
        ("transport_status", "TEXT DEFAULT 'N/A'"),
        ("prepared_by", "TEXT"),
        ("approved_by", "TEXT"),
        ("po_number", "TEXT"),
        ("so_number", "TEXT"),
        ("transporter_name", "TEXT"),
    ]
    for col_name, col_type in new_cols:
        try:
            cur.execute(f"ALTER TABLE payment_orders ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass  # Column already exists

    # Add new columns to purchase_orders
    po_new_cols = [
        ("po_date", "TEXT"),
        ("reference_no", "TEXT"),
        ("lr_no", "TEXT"),
        ("transporter_id", "INTEGER"),
    ]
    for col_name, col_type in po_new_cols:
        try:
            cur.execute(f"ALTER TABLE purchase_orders ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass

    # Add new columns to sales_orders
    so_new_cols = [
        ("so_date", "TEXT"),
        ("reference_no", "TEXT"),
        ("lr_no", "TEXT"),
        ("transporter_id", "INTEGER"),
    ]
    for col_name, col_type in so_new_cols:
        try:
            cur.execute(f"ALTER TABLE sales_orders ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass

    # Seed new clauses (invoice_correction_clause, lr_clause)
    try:
        from company_config import COMPANY_PROFILE as CP
    except ImportError:
        CP = {}

    now = _now_ist()
    for key, attr in [
        ("invoice_correction_clause", "invoice_correction_clause"),
        ("lr_clause", "lr_clause"),
    ]:
        text = CP.get(attr, "")
        if text:
            # Check if already exists
            existing = cur.execute(
                "SELECT id FROM terms_master WHERE term_key = ?", (key,)
            ).fetchone()
            if not existing:
                cur.execute(
                    "INSERT INTO terms_master (term_key, term_text, category, sort_order, is_active, created_at, updated_at) "
                    "VALUES (?,?,?,?,1,?,?)",
                    (key, text, "clause", 101, now, now),
                )


def _migration_006_crm_automation(cur):
    """Add CRM automation tables: contacts, rotation log, festival, price log.
    Tables are created by _TABLES dict in init_db(), so this migration just
    ensures any future ALTER TABLE needs are handled."""
    pass  # Tables auto-created via _TABLES dict; migration placeholder for tracking


def _migration_007_vip_and_sms(cur):
    """Add VIP scoring columns to contacts, DPDP consent fields, sms_queue table."""
    # --- VIP scoring columns on contacts ---
    _safe_add_column(cur, "contacts", "vip_score", "REAL DEFAULT 0")
    _safe_add_column(cur, "contacts", "vip_tier", "TEXT DEFAULT 'standard'")

    # --- DPDP compliance columns ---
    _safe_add_column(cur, "contacts", "consent_timestamp", "TEXT")
    _safe_add_column(cur, "contacts", "unsubscribe_token", "TEXT")
    _safe_add_column(cur, "contacts", "sms_opted_in", "INTEGER DEFAULT 0")

    # --- SMS Queue table ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sms_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            to_number       TEXT NOT NULL,
            message         TEXT NOT NULL,
            sms_type        TEXT DEFAULT 'transactional',
            status          TEXT DEFAULT 'pending',
            scheduled_time  TEXT,
            sent_at         TEXT,
            error_message   TEXT,
            retry_count     INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sms_queue_status ON sms_queue(status)")


def _migration_008_phase1_import_tables(cur):
    """Phase 1: customer_profiles + import_history tables, imported_from on customers."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            company      TEXT,
            city         TEXT,
            state        TEXT,
            whatsapp     TEXT,
            email        TEXT,
            category     TEXT,
            notes        TEXT,
            source_file  TEXT,
            imported_at  TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name     TEXT NOT NULL,
            target_table  TEXT NOT NULL,
            rows_inserted INTEGER NOT NULL,
            rows_skipped  INTEGER NOT NULL,
            rows_errored  INTEGER NOT NULL,
            imported_at   TEXT NOT NULL,
            reverted      INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_profiles_name
        ON customer_profiles(name)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_import_history_imported_at
        ON import_history(imported_at DESC)
    """)
    # Add imported_from column to tables where it is missing
    for tbl in ("customers", "suppliers", "contacts"):
        try:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN imported_from TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists


def _safe_add_column(cur, table: str, column: str, col_def: str):
    """Add column if it doesn't already exist (SQLite has no IF NOT EXISTS for ALTER)."""
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
    except Exception:
        pass  # Column already exists


# ═══════════════════════════════════════════════════════════════════════════
# GENERIC HELPERS (private)
# ═══════════════════════════════════════════════════════════════════════════

_VALID_TABLES = {
    "suppliers", "customers", "deals", "price_history", "fx_history",
    "inventory", "communications", "opportunities", "sync_logs",
    "missing_inputs", "email_queue", "whatsapp_queue", "whatsapp_sessions",
    "whatsapp_incoming", "director_briefings", "daily_logs", "alerts",
    "users", "audit_log", "recipient_lists", "source_registry",
    "chat_messages", "share_links", "share_schedules", "comm_tracking",
    "crm_tasks", "_schema_version",
    "company_master", "bank_master", "terms_master",
    "purchase_orders", "sales_orders", "payment_orders", "_doc_counters",
    "transporters",
    # CRM Automation tables (Phase 6)
    "contacts", "contact_rotation_log", "festival_broadcasts", "price_update_log",
    # SMS queue (Phase 7)
    "sms_queue",
}

import re
_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_table(table: str) -> str:
    """Ensure table name is a known table — prevents SQL injection."""
    if table not in _VALID_TABLES:
        raise ValueError(f"Unknown table: {table!r}")
    return table


def _validate_columns(keys, table: str = "") -> list:
    """Ensure all column names are safe identifiers."""
    safe = []
    for k in keys:
        if not _SAFE_IDENT.match(k):
            raise ValueError(f"Invalid column name: {k!r}")
        safe.append(k)
    return safe


def _insert_row(table: str, data: dict) -> int:
    """
    Insert a single row into *table* using the keys/values from *data*.
    Returns the new row's id.
    """
    _validate_table(table)
    col_names = _validate_columns(data.keys())
    cols = ", ".join(col_names)
    placeholders = ", ".join(["?"] * len(data))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, list(data.values()))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _update_row(table: str, row_id: int, data: dict):
    """
    Update fields in *table* for the row with the given *row_id*.
    """
    _validate_table(table)
    col_names = _validate_columns(data.keys())
    set_clause = ", ".join([f"{k} = ?" for k in col_names])
    sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, list(data.values()) + [row_id])
        conn.commit()
    finally:
        conn.close()


def _select_all(table: str, where: str = "", params: tuple = (), order: str = "") -> list:
    """
    Return all rows from *table*, optionally filtered and ordered.

    The *where* and *order* clauses are validated to contain only safe
    SQL tokens (column names, operators, ASC/DESC). Use *params* for values.
    """
    _validate_table(table)
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    if order:
        sql += f" ORDER BY {order}"
    conn = _get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def _select_one(table: str, row_id: int) -> dict | None:
    """
    Return a single row by id, or None if not found.
    """
    _validate_table(table)
    conn = _get_conn()
    try:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# SUPPLIERS
# ═══════════════════════════════════════════════════════════════════════════

def insert_supplier(data: dict) -> int:
    """
    Insert a new supplier row.

    Parameters
    ----------
    data : dict
        Keys should match supplier column names (excluding 'id').
        'preferred_grades' may be a Python list — it will be JSON-encoded.

    Returns
    -------
    int
        The new supplier's id.
    """
    data = dict(data)  # shallow copy to avoid mutating caller's dict
    if "preferred_grades" in data and isinstance(data["preferred_grades"], list):
        data["preferred_grades"] = json.dumps(data["preferred_grades"])
    if "seasonality_tags" in data and isinstance(data["seasonality_tags"], list):
        data["seasonality_tags"] = json.dumps(data["seasonality_tags"])
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("suppliers", data)


def get_all_suppliers() -> list:
    """
    Return all active suppliers, ordered by name.
    """
    return _select_all("suppliers", where="is_active = 1", order="name ASC")


def get_supplier_by_id(supplier_id: int) -> dict | None:
    """Return a single supplier by id."""
    return _select_one("suppliers", supplier_id)


def update_supplier(supplier_id: int, data: dict):
    """
    Update one or more fields on an existing supplier.

    Parameters
    ----------
    supplier_id : int
    data : dict
        Column-value pairs to update.
    """
    data = dict(data)
    if "preferred_grades" in data and isinstance(data["preferred_grades"], list):
        data["preferred_grades"] = json.dumps(data["preferred_grades"])
    if "seasonality_tags" in data and isinstance(data["seasonality_tags"], list):
        data["seasonality_tags"] = json.dumps(data["seasonality_tags"])
    data["updated_at"] = _now_ist()
    _update_row("suppliers", supplier_id, data)


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ═══════════════════════════════════════════════════════════════════════════

def insert_customer(data: dict) -> int:
    """
    Insert a new customer row.

    Parameters
    ----------
    data : dict
        Keys should match customer column names (excluding 'id').
        'preferred_grades', 'seasonality_tags', 'peak_months' may be Python lists.

    Returns
    -------
    int
        The new customer's id.
    """
    data = dict(data)
    for field in ("preferred_grades", "seasonality_tags", "peak_months"):
        if field in data and isinstance(data[field], list):
            data[field] = json.dumps(data[field])
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("customers", data)


def get_all_customers() -> list:
    """Return all active customers, ordered by name."""
    return _select_all("customers", where="is_active = 1", order="name ASC")


def get_customer_by_id(customer_id: int) -> dict | None:
    """Return a single customer by id, or None."""
    return _select_one("customers", customer_id)


def update_customer(customer_id: int, data: dict):
    """
    Update one or more fields on an existing customer.

    Parameters
    ----------
    customer_id : int
    data : dict
        Column-value pairs to update.
    """
    data = dict(data)
    for field in ("preferred_grades", "seasonality_tags", "peak_months"):
        if field in data and isinstance(data[field], list):
            data[field] = json.dumps(data[field])
    data["updated_at"] = _now_ist()
    _update_row("customers", customer_id, data)


# ═══════════════════════════════════════════════════════════════════════════
# DEALS
# ═══════════════════════════════════════════════════════════════════════════

def insert_deal(data: dict) -> int:
    """
    Insert a new deal row.

    Parameters
    ----------
    data : dict
        Keys should match deals column names (excluding 'id').
        If 'deal_number' is not supplied, one is auto-generated
        as DEAL-YYYYMMDD-HHMMSS.

    Returns
    -------
    int
        The new deal's id.
    """
    data = dict(data)
    if not data.get("deal_number"):
        data["deal_number"] = "DEAL-" + datetime.now(IST).strftime("%Y%m%d-%H%M%S")
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    _round_monetary_fields(data)
    return _insert_row("deals", data)


def get_all_deals() -> list:
    """Return all deals, most recent first."""
    return _select_all("deals", order="created_at DESC")


def get_deals_by_stage(stage: str) -> list:
    """Return deals filtered by pipeline stage (enquiry, quoted, confirmed, etc.)."""
    return _select_all("deals", where="stage = ?", params=(stage,), order="created_at DESC")


def get_deal_by_id(deal_id: int) -> dict | None:
    """Return a single deal by id."""
    return _select_one("deals", deal_id)


def update_deal_stage(deal_id: int, new_stage: str):
    """
    Move a deal to a new pipeline stage and record the corresponding date.

    Automatically sets the matching date column:
        enquiry  -> enquiry_date
        quoted   -> quote_date
        confirmed / po -> po_date
        dispatched     -> dispatch_date
        delivered      -> delivery_date
        paid           -> payment_date

    Uses a transaction to ensure atomicity.

    Parameters
    ----------
    deal_id : int
    new_stage : str
    """
    now = _now_ist()
    data = {"stage": new_stage, "updated_at": now}

    stage_date_map = {
        "enquiry":    "enquiry_date",
        "quoted":     "quote_date",
        "confirmed":  "po_date",
        "po":         "po_date",
        "dispatched": "dispatch_date",
        "delivered":  "delivery_date",
        "paid":       "payment_date",
    }
    date_col = stage_date_map.get(new_stage)
    if date_col:
        data[date_col] = now

    with db_transaction() as conn:
        _update_row_tx(conn, "deals", deal_id, data)


def update_deal(deal_id: int, data: dict):
    """
    Update arbitrary fields on an existing deal.

    Parameters
    ----------
    deal_id : int
    data : dict
        Column-value pairs to update.
    """
    data = dict(data)
    data["updated_at"] = _now_ist()
    _round_monetary_fields(data)
    _update_row("deals", deal_id, data)


# ═══════════════════════════════════════════════════════════════════════════
# PRICE HISTORY
# ═══════════════════════════════════════════════════════════════════════════

def insert_price_history(records: list):
    """
    Bulk-insert price history records.

    Parameters
    ----------
    records : list of dict
        Each dict should have keys: date_time, benchmark, price, currency,
        source, and optionally validated.
    """
    if not records:
        return
    conn = _get_conn()
    try:
        cur = conn.cursor()
        for rec in records:
            rec = dict(rec)
            rec.setdefault("validated", 1)
            cols = ", ".join(rec.keys())
            placeholders = ", ".join(["?"] * len(rec))
            cur.execute(
                f"INSERT INTO price_history ({cols}) VALUES ({placeholders})",
                list(rec.values()),
            )
        conn.commit()
    finally:
        conn.close()


def get_price_history(benchmark: str, limit: int = 100) -> list:
    """
    Return the most recent price records for a given benchmark.

    Parameters
    ----------
    benchmark : str
        E.g. 'Brent', 'VG30_Mumbai', 'Iran_180CST_FOB'.
    limit : int
        Max records to return (default 100).

    Returns
    -------
    list of dict
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM price_history WHERE benchmark = ? ORDER BY date_time DESC LIMIT ?",
            (benchmark, limit),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# FX HISTORY
# ═══════════════════════════════════════════════════════════════════════════

def insert_fx_rate(data: dict) -> int:
    """Insert a single FX rate record. Returns new row id."""
    data = dict(data)
    data.setdefault("date_time", _now_ist())
    return _insert_row("fx_history", data)


def get_fx_latest() -> dict:
    """
    Return the latest FX rate for each currency pair as a dict.

    Returns
    -------
    dict
        Keyed by "FROM/TO" (e.g. "USD/INR"), value is the latest rate dict.
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT fh.*
            FROM fx_history fh
            INNER JOIN (
                SELECT from_currency, to_currency, MAX(date_time) AS max_dt
                FROM fx_history
                GROUP BY from_currency, to_currency
            ) latest
            ON  fh.from_currency = latest.from_currency
            AND fh.to_currency   = latest.to_currency
            AND fh.date_time     = latest.max_dt
            """
        ).fetchall()
        result = {}
        for row in rows:
            d = _row_to_dict(row)
            key = f"{d['from_currency']}/{d['to_currency']}"
            result[key] = d
        return result
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# INVENTORY
# ═══════════════════════════════════════════════════════════════════════════

def upsert_inventory(data: dict) -> int:
    """
    Insert or update an inventory record.
    If a record with the same location + grade exists, update it; else insert.

    Returns the row id.
    """
    data = dict(data)
    data["updated_at"] = _now_ist()
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM inventory WHERE location = ? AND grade = ?",
            (data.get("location"), data.get("grade")),
        ).fetchone()
        if existing:
            row_id = existing["id"]
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            conn.execute(
                f"UPDATE inventory SET {set_clause} WHERE id = ?",
                list(data.values()) + [row_id],
            )
            conn.commit()
            return row_id
        else:
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO inventory ({cols}) VALUES ({placeholders})",
                list(data.values()),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def get_inventory_summary() -> list:
    """
    Return inventory grouped by grade with total quantities.

    Returns
    -------
    list of dict
        Each dict has: grade, total_quantity_mt, total_value_inr, locations (count).
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                grade,
                SUM(quantity_mt) AS total_quantity_mt,
                SUM(quantity_mt * cost_per_mt) AS total_value_inr,
                COUNT(DISTINCT location) AS locations
            FROM inventory
            WHERE quantity_mt > 0
            GROUP BY grade
            ORDER BY total_quantity_mt DESC
            """
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# COMMUNICATIONS
# ═══════════════════════════════════════════════════════════════════════════

def log_communication(data: dict) -> int:
    """
    Insert a communication log entry.

    Parameters
    ----------
    data : dict
        Keys: customer_id, supplier_id, channel, direction, subject,
              content, template_used, sent_at, status.

    Returns
    -------
    int
        The new communication row's id.
    """
    data = dict(data)
    data.setdefault("sent_at", _now_ist())
    return _insert_row("communications", data)


def get_communications(entity_type: str, entity_id: int, limit: int = 50) -> list:
    """
    Retrieve communication history for a customer or supplier.

    Parameters
    ----------
    entity_type : str
        'customer' or 'supplier'.
    entity_id : int
    limit : int

    Returns
    -------
    list of dict
    """
    col = "customer_id" if entity_type == "customer" else "supplier_id"
    conn = _get_conn()
    try:
        rows = conn.execute(
            f"SELECT * FROM communications WHERE {col} = ? ORDER BY sent_at DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# OPPORTUNITIES
# ═══════════════════════════════════════════════════════════════════════════

def insert_opportunity(data: dict) -> int:
    """
    Insert a new sales opportunity / SOS alert.

    Parameters
    ----------
    data : dict
        Keys matching the opportunities table columns.

    Returns
    -------
    int
        The new opportunity's id.
    """
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    return _insert_row("opportunities", data)


def get_all_opportunities(status: str = None) -> list:
    """
    Retrieve opportunities, optionally filtered by status.

    Parameters
    ----------
    status : str or None
        If provided (e.g. 'new', 'acted', 'expired'), filter by that status.
        If None, return all opportunities.

    Returns
    -------
    list of dict
    """
    if status:
        return _select_all(
            "opportunities",
            where="status = ?",
            params=(status,),
            order="created_at DESC",
        )
    return _select_all("opportunities", order="created_at DESC")


def update_opportunity(opportunity_id: int, data: dict):
    """Update fields on an existing opportunity."""
    data = dict(data)
    _update_row("opportunities", opportunity_id, data)


# ═══════════════════════════════════════════════════════════════════════════
# SYNC LOGS
# ═══════════════════════════════════════════════════════════════════════════

def log_sync(data: dict) -> int:
    """
    Record an API sync event.

    Parameters
    ----------
    data : dict
        Keys: sync_type, started_at, completed_at, status, apis_called,
              apis_succeeded, records_updated, errors, next_scheduled.

    Returns
    -------
    int
        The new sync_log row's id.
    """
    data = dict(data)
    data.setdefault("started_at", _now_ist())
    return _insert_row("sync_logs", data)


def get_sync_logs(limit: int = 20) -> list:
    """Return the most recent sync log entries."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM sync_logs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# MISSING INPUTS
# ═══════════════════════════════════════════════════════════════════════════

def add_missing_input(data: dict) -> int:
    """
    Record a field that still needs to be collected from the user.

    Parameters
    ----------
    data : dict
        Keys: field_name, entity_type, entity_id, reason, priority, status.

    Returns
    -------
    int
        The new missing_input row's id.
    """
    data = dict(data)
    data.setdefault("status", "pending")
    data.setdefault("created_at", _now_ist())
    return _insert_row("missing_inputs", data)


def get_missing_inputs(status: str = "pending") -> list:
    """
    Return missing input items, filtered by status.

    Parameters
    ----------
    status : str
        Default 'pending'. Use 'all' to return every record.

    Returns
    -------
    list of dict
    """
    if status == "all":
        return _select_all("missing_inputs", order="created_at DESC")
    return _select_all(
        "missing_inputs",
        where="status = ?",
        params=(status,),
        order="priority ASC, created_at ASC",
    )


def resolve_missing_input(input_id: int, collected_value: str):
    """Mark a missing input as collected."""
    _update_row("missing_inputs", input_id, {
        "status": "collected",
        "collected_value": collected_value,
        "collected_at": _now_ist(),
    })


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════════

def get_dashboard_stats() -> dict:
    """
    Return a summary dict for the main dashboard view.

    Returns
    -------
    dict with keys:
        total_customers         — count of active customers
        total_suppliers         — count of active suppliers
        total_deals             — count of all deals
        deals_by_stage          — dict {stage: count}
        active_deals            — count where status = 'active'
        total_deal_value_inr    — sum of total_value_inr for active deals
        total_received_inr      — sum of payment_received_inr
        total_outstanding_inr   — total_deal_value - total_received
        avg_margin_pct          — average margin_pct across active deals
        open_opportunities      — count of opportunities with status = 'new'
        pending_missing_inputs  — count of missing inputs with status = 'pending'
        inventory_mt            — total inventory quantity in MT
        last_sync               — most recent sync_log entry
    """
    conn = _get_conn()
    try:
        stats = {}

        # Customers
        row = conn.execute("SELECT COUNT(*) AS cnt FROM customers WHERE is_active = 1").fetchone()
        stats["total_customers"] = row["cnt"]

        # Suppliers
        row = conn.execute("SELECT COUNT(*) AS cnt FROM suppliers WHERE is_active = 1").fetchone()
        stats["total_suppliers"] = row["cnt"]

        # Deals — total count
        row = conn.execute("SELECT COUNT(*) AS cnt FROM deals").fetchone()
        stats["total_deals"] = row["cnt"]

        # Deals by stage
        rows = conn.execute(
            "SELECT stage, COUNT(*) AS cnt FROM deals GROUP BY stage"
        ).fetchall()
        stats["deals_by_stage"] = {r["stage"]: r["cnt"] for r in rows}

        # Active deals count
        row = conn.execute("SELECT COUNT(*) AS cnt FROM deals WHERE status = 'active'").fetchone()
        stats["active_deals"] = row["cnt"]

        # Financial totals
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(total_value_inr), 0)       AS total_val,
                COALESCE(SUM(payment_received_inr), 0)  AS total_recv,
                COALESCE(AVG(margin_pct), 0)             AS avg_margin
            FROM deals
            WHERE status = 'active'
            """
        ).fetchone()
        stats["total_deal_value_inr"] = row["total_val"]
        stats["total_received_inr"] = row["total_recv"]
        stats["total_outstanding_inr"] = row["total_val"] - row["total_recv"]
        stats["avg_margin_pct"] = round(row["avg_margin"], 2)

        # Open opportunities
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM opportunities WHERE status = 'new'"
        ).fetchone()
        stats["open_opportunities"] = row["cnt"]

        # Pending missing inputs
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM missing_inputs WHERE status = 'pending'"
        ).fetchone()
        stats["pending_missing_inputs"] = row["cnt"]

        # Inventory total
        row = conn.execute(
            "SELECT COALESCE(SUM(quantity_mt), 0) AS total FROM inventory"
        ).fetchone()
        stats["inventory_mt"] = row["total"]

        # Last sync
        row = conn.execute(
            "SELECT * FROM sync_logs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        stats["last_sync"] = _row_to_dict(row) if row else None

        return stats
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# EMAIL QUEUE
# ═══════════════════════════════════════════════════════════════════════════

def insert_email_queue(data: dict) -> int:
    """Insert a new email into the queue. Returns queue_id."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("email_queue", data)


def get_email_queue(status: str = None, limit: int = 50) -> list:
    """Return email queue items, optionally filtered by status."""
    if status:
        return _select_all("email_queue", where="status = ?",
                           params=(status,), order="created_at DESC")[:limit]
    return _select_all("email_queue", order="created_at DESC")[:limit]


def update_email_status(queue_id: int, status: str, **kwargs):
    """Update email queue item status and optional fields."""
    data = {"status": status, "updated_at": _now_ist()}
    data.update(kwargs)
    _update_row("email_queue", queue_id, data)


# ═══════════════════════════════════════════════════════════════════════════
# WHATSAPP QUEUE
# ═══════════════════════════════════════════════════════════════════════════

def insert_wa_queue(data: dict) -> int:
    """Insert a new WhatsApp message into the queue. Returns queue_id."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("whatsapp_queue", data)


def get_wa_queue(status: str = None, limit: int = 50) -> list:
    """Return WhatsApp queue items, optionally filtered by status."""
    if status:
        return _select_all("whatsapp_queue", where="status = ?",
                           params=(status,), order="created_at DESC")[:limit]
    return _select_all("whatsapp_queue", order="created_at DESC")[:limit]


def update_wa_status(queue_id: int, status: str, **kwargs):
    """Update WhatsApp queue item status and optional fields."""
    data = {"status": status, "updated_at": _now_ist()}
    data.update(kwargs)
    _update_row("whatsapp_queue", queue_id, data)


def get_active_wa_session(phone_number: str) -> dict | None:
    """Return active session for a phone number, or None."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM whatsapp_sessions WHERE phone_number = ? "
            "AND session_expires > ? LIMIT 1",
            (phone_number, _now_ist()),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def upsert_wa_session(phone_number: str, customer_id: int = None,
                      last_message: str = "") -> int:
    """Create or update a WhatsApp session (24h window)."""
    now = _now_ist()
    expires = (datetime.now(IST) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM whatsapp_sessions WHERE phone_number = ?",
            (phone_number,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE whatsapp_sessions SET session_start = ?, session_expires = ?, "
                "last_message = ?, customer_id = ? WHERE id = ?",
                (now, expires, last_message, customer_id, existing["id"]),
            )
            conn.commit()
            return existing["id"]
        else:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO whatsapp_sessions (phone_number, session_start, "
                "session_expires, customer_id, last_message, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (phone_number, now, expires, customer_id, last_message, now),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def insert_wa_incoming(data: dict) -> int:
    """Insert an incoming WhatsApp message. Returns row id."""
    data = dict(data)
    data.setdefault("received_at", _now_ist())
    return _insert_row("whatsapp_incoming", data)


def get_wa_incoming(processed: int = None, limit: int = 50) -> list:
    """Return incoming WhatsApp messages."""
    if processed is not None:
        return _select_all("whatsapp_incoming", where="processed = ?",
                           params=(processed,), order="received_at DESC")[:limit]
    return _select_all("whatsapp_incoming", order="received_at DESC")[:limit]


# ═══════════════════════════════════════════════════════════════════════════
# DIRECTOR BRIEFINGS
# ═══════════════════════════════════════════════════════════════════════════

def insert_director_briefing(data: dict) -> int:
    """Insert a generated director briefing."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    return _insert_row("director_briefings", data)


def get_director_briefings(limit: int = 30) -> list:
    """Return recent director briefings."""
    return _select_all("director_briefings",
                       order="briefing_date DESC")[:limit]


# ═══════════════════════════════════════════════════════════════════════════
# DAILY LOGS
# ═══════════════════════════════════════════════════════════════════════════

def insert_daily_log(data: dict) -> int:
    """Insert a daily log entry."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    return _insert_row("daily_logs", data)


def get_daily_logs(log_date: str = None, limit: int = 50) -> list:
    """Return daily logs, optionally filtered by date."""
    if log_date:
        return _select_all("daily_logs", where="log_date = ?",
                           params=(log_date,),
                           order="created_at DESC")[:limit]
    return _select_all("daily_logs", order="created_at DESC")[:limit]


# ═══════════════════════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════════════════════

def insert_alert(data: dict) -> int:
    """Insert a new alert. Returns alert id."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    data.setdefault("status", "new")
    return _insert_row("alerts", data)


def get_alerts(status: str = None, priority: str = None, limit: int = 100) -> list:
    """Return alerts, optionally filtered by status and/or priority."""
    where_parts = []
    params = []
    if status:
        where_parts.append("status = ?")
        params.append(status)
    if priority:
        where_parts.append("priority = ?")
        params.append(priority)
    where = " AND ".join(where_parts) if where_parts else ""
    return _select_all("alerts", where=where, params=tuple(params),
                       order="created_at DESC")[:limit]


def update_alert_status(alert_id: int, status: str, **kwargs):
    """Update alert status and optional fields (acted_at, acted_by, snoozed_until)."""
    data = {"status": status}
    data.update(kwargs)
    _update_row("alerts", alert_id, data)


# ═══════════════════════════════════════════════════════════════════════════
# PHASE C: USERS / AUDIT / RECIPIENTS / SOURCE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

def insert_user(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("users", data)

def get_user_by_username(username: str):
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()

def get_all_users() -> list:
    return _select_all("users", order="username")

def update_user(user_id: int, data: dict):
    data["updated_at"] = _now_ist()
    _update_row("users", user_id, data)

def delete_user(user_id: int) -> bool:
    """Hard-delete a user. Returns True on success. Refuses if this would
    leave zero active director accounts. Null-outs user_id on audit_log
    entries before deletion so history is preserved (username column stays)
    without tripping the FK constraint."""
    conn = _get_conn()
    try:
        target = conn.execute("SELECT role, is_active FROM users WHERE id = ?",
                              (user_id,)).fetchone()
        if not target:
            return False
        if target[0] == "director" and target[1]:
            other_directors = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'director' "
                "AND is_active = 1 AND id != ?", (user_id,)
            ).fetchone()[0]
            if other_directors == 0:
                raise ValueError("Cannot delete last active director account")
        # Preserve audit trail — disconnect FK, keep username string.
        conn.execute("UPDATE audit_log SET user_id = NULL WHERE user_id = ?",
                     (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def insert_audit_log(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    return _insert_row("audit_log", data)

def get_audit_logs(limit: int = 200, action_filter: str = None, user_filter: str = None) -> list:
    conn = _get_conn()
    try:
        sql = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if action_filter:
            sql += " AND action = ?"
            params.append(action_filter)
        if user_filter:
            sql += " AND username = ?"
            params.append(user_filter)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()

def insert_recipient_list(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("recipient_lists", data)

def get_recipient_lists(list_type: str = None) -> list:
    conn = _get_conn()
    try:
        if list_type:
            rows = conn.execute(
                "SELECT * FROM recipient_lists WHERE is_active = 1 AND list_type = ? ORDER BY list_name",
                (list_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM recipient_lists WHERE is_active = 1 ORDER BY list_name"
            ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()

def update_recipient_list(list_id: int, data: dict):
    data["updated_at"] = _now_ist()
    _update_row("recipient_lists", list_id, data)

def delete_recipient_list(list_id: int):
    _update_row("recipient_lists", list_id, {"is_active": 0, "updated_at": _now_ist()})

def insert_source_registry(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("source_registry", data)

def get_all_sources() -> list:
    return _select_all("source_registry", order="source_name")

def get_source_by_key(key: str):
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM source_registry WHERE source_key = ?", (key,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()

def update_source_registry(source_id: int, data: dict):
    data["updated_at"] = _now_ist()
    _update_row("source_registry", source_id, data)

def delete_source_registry(source_id: int):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM source_registry WHERE id = ?", (source_id,))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# CHAT MESSAGES
# ═══════════════════════════════════════════════════════════════════════════

def insert_chat_message(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    return _insert_row("chat_messages", data)

def get_chat_messages(conversation_id: str, limit: int = 100) -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()

def get_chat_conversations() -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT conversation_id,
                      MAX(sender_name) as last_sender,
                      MAX(created_at) as last_message_at,
                      SUM(CASE WHEN is_read = 0 AND sender_type = 'client' THEN 1 ELSE 0 END) as unread
               FROM chat_messages
               GROUP BY conversation_id
               ORDER BY last_message_at DESC"""
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()

def mark_chat_read(conversation_id: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE chat_messages SET is_read = 1 WHERE conversation_id = ? AND is_read = 0",
            (conversation_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# SHARE LINKS
# ═══════════════════════════════════════════════════════════════════════════

def insert_share_link(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    return _insert_row("share_links", data)

def get_share_link(token: str):
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM share_links WHERE link_token = ?", (token,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()

def get_all_share_links(active_only: bool = True) -> list:
    where = "is_active = 1" if active_only else ""
    return _select_all("share_links", where=where, order="created_at DESC")

def increment_share_view(token: str):
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE share_links SET view_count = view_count + 1, last_accessed = ? WHERE link_token = ?",
            (_now_ist(), token),
        )
        conn.commit()
    finally:
        conn.close()

def deactivate_share_link(link_id: int):
    _update_row("share_links", link_id, {"is_active": 0})


# ═══════════════════════════════════════════════════════════════════════════
# SHARE SCHEDULES
# ═══════════════════════════════════════════════════════════════════════════

def insert_share_schedule(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("share_schedules", data)

def get_share_schedules(active_only: bool = True) -> list:
    where = "is_active = 1" if active_only else ""
    return _select_all("share_schedules", where=where, order="schedule_name")

def update_share_schedule(schedule_id: int, data: dict):
    data["updated_at"] = _now_ist()
    _update_row("share_schedules", schedule_id, data)

def delete_share_schedule(schedule_id: int):
    _update_row("share_schedules", schedule_id, {"is_active": 0, "updated_at": _now_ist()})


# ═══════════════════════════════════════════════════════════════════════════
# COMMUNICATION TRACKING
# ═══════════════════════════════════════════════════════════════════════════

def insert_comm_tracking(data: dict) -> int:
    data.setdefault("created_at", _now_ist())
    return _insert_row("comm_tracking", data)

def get_comm_tracking(channel: str = None, limit: int = 200) -> list:
    conn = _get_conn()
    try:
        if channel:
            rows = conn.execute(
                "SELECT * FROM comm_tracking WHERE channel = ? ORDER BY created_at DESC LIMIT ?",
                (channel, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM comm_tracking ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()

def update_comm_tracking_status(tracking_id: str, status: str, error_message: str = None):
    conn = _get_conn()
    try:
        if error_message:
            conn.execute(
                "UPDATE comm_tracking SET delivery_status = ?, error_message = ?, delivered_at = ? WHERE tracking_id = ?",
                (status, error_message, _now_ist(), tracking_id),
            )
        else:
            conn.execute(
                "UPDATE comm_tracking SET delivery_status = ?, delivered_at = ? WHERE tracking_id = ?",
                (status, _now_ist(), tracking_id),
            )
        conn.commit()
    finally:
        conn.close()

def get_comm_stats(days: int = 30) -> dict:
    conn = _get_conn()
    try:
        from datetime import datetime, timedelta
        cutoff = (datetime.now(IST) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM comm_tracking WHERE created_at >= ?", (cutoff,)
        ).fetchone()["cnt"]
        by_channel = conn.execute(
            "SELECT channel, COUNT(*) as cnt FROM comm_tracking WHERE created_at >= ? GROUP BY channel",
            (cutoff,),
        ).fetchall()
        by_status = conn.execute(
            "SELECT delivery_status, COUNT(*) as cnt FROM comm_tracking WHERE created_at >= ? GROUP BY delivery_status",
            (cutoff,),
        ).fetchall()
        return {
            "total": total,
            "by_channel": {r["channel"]: r["cnt"] for r in by_channel},
            "by_status": {r["delivery_status"]: r["cnt"] for r in by_status},
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# CRM TASKS (SQLite-backed)
# ═══════════════════════════════════════════════════════════════════════════

def insert_crm_task(data: dict) -> str:
    """Insert or replace a CRM task. Returns task id."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    task_id = data.get("id", "")
    if not task_id:
        import uuid
        task_id = str(uuid.uuid4())[:8]
        data["id"] = task_id
    # Map 'type' to 'task_type' for DB column
    if "type" in data and "task_type" not in data:
        data["task_type"] = data.pop("type")
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO crm_tasks
               (id, client, task_type, due_date, status, priority, note,
                outcome, automated, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("id"), data.get("client", ""),
                data.get("task_type", "Call"), data.get("due_date"),
                data.get("status", "Pending"), data.get("priority", "Medium"),
                data.get("note", ""), data.get("outcome", ""),
                1 if data.get("automated") else 0,
                data.get("created_at", _now_ist()), data.get("completed_at"),
            ),
        )
        conn.commit()
        return task_id
    finally:
        conn.close()


def get_crm_tasks(status: str = None, client: str = None) -> list:
    """Return CRM tasks, optionally filtered."""
    conn = _get_conn()
    try:
        sql = "SELECT * FROM crm_tasks WHERE 1=1"
        params = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if client:
            sql += " AND client = ?"
            params.append(client)
        sql += " ORDER BY due_date ASC"
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def complete_crm_task(task_id: str, outcome: str = ""):
    """Mark a CRM task as completed."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE crm_tasks SET status = 'Completed', outcome = ?, "
            "completed_at = ? WHERE id = ?",
            (outcome, _now_ist(), task_id),
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# DATA RETENTION / CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

def cleanup_old_records() -> dict:
    """
    Trim oversized tables based on configured limits.
    Called from sync_engine Batch 4.
    Returns dict of {table: rows_deleted}.
    """
    try:
        from settings_engine import load_settings
        settings = load_settings()
    except ImportError:
        settings = {}

    limits = {
        "sync_logs":      settings.get("max_sync_logs", 1000),
        "audit_log":      10000,
        "comm_tracking":  settings.get("max_communication_records", 10000),
        "price_history":  settings.get("max_price_history_records", 5000),
    }

    results = {}
    conn = _get_conn()
    try:
        for table, max_rows in limits.items():
            try:
                row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
                count = row["c"] if row else 0
                if count > max_rows:
                    conn.execute(
                        f"DELETE FROM {table} WHERE id NOT IN "
                        f"(SELECT id FROM {table} ORDER BY id DESC LIMIT ?)",
                        (max_rows,),
                    )
                    results[table] = count - max_rows
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()
    return results


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT MANAGEMENT — Doc numbering + CRUD
# ═══════════════════════════════════════════════════════════════════════════

def _get_current_fy() -> str:
    """
    Return Indian Financial Year string. FY runs Apr 1 – Mar 31.
    E.g., March 2026 → "2526", April 2026 → "2627".
    """
    now = datetime.now(IST)
    year = now.year
    month = now.month
    if month >= 4:
        # Apr-Dec: FY starts this year
        start_year = year % 100
        end_year = (year + 1) % 100
    else:
        # Jan-Mar: FY started previous year
        start_year = (year - 1) % 100
        end_year = year % 100
    return f"{start_year:02d}{end_year:02d}"


def get_next_doc_number(doc_type: str) -> str:
    """
    Atomic FY-based auto-numbering: FY2526/PO/0001, FY2526/SO/0001, FY2526/PAY/0001.
    Counter resets each financial year (April 1).
    Thread-safe via BEGIN IMMEDIATE transaction.
    """
    fy = _get_current_fy()
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT last_date, last_seq FROM _doc_counters WHERE doc_type = ?",
            (doc_type,),
        ).fetchone()
        if row and row["last_date"] == fy:
            seq = row["last_seq"] + 1
            conn.execute(
                "UPDATE _doc_counters SET last_seq = ? WHERE doc_type = ?",
                (seq, doc_type),
            )
        else:
            seq = 1
            conn.execute(
                "INSERT OR REPLACE INTO _doc_counters (doc_type, last_date, last_seq) "
                "VALUES (?, ?, ?)",
                (doc_type, fy, seq),
            )
        conn.commit()
        return f"FY{fy}/{doc_type}/{seq:04d}"
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Company Master ────────────────────────────────────────────────────────

def get_company_master() -> dict | None:
    """Return the company master row (single row expected)."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM company_master LIMIT 1").fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def upsert_company_master(data: dict) -> int:
    """Insert or update company master (single row, id=1)."""
    data["updated_at"] = _now_ist()
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT id FROM company_master LIMIT 1").fetchone()
        if existing:
            row_id = existing["id"]
            col_names = _validate_columns(data.keys())
            set_clause = ", ".join([f"{k} = ?" for k in col_names])
            conn.execute(
                f"UPDATE company_master SET {set_clause} WHERE id = ?",
                list(data.values()) + [row_id],
            )
        else:
            data["created_at"] = _now_ist()
            col_names = _validate_columns(data.keys())
            cols = ", ".join(col_names)
            placeholders = ", ".join(["?"] * len(data))
            conn.execute(
                f"INSERT INTO company_master ({cols}) VALUES ({placeholders})",
                list(data.values()),
            )
            row_id = 1
        conn.commit()
        return row_id
    finally:
        conn.close()


# ── Bank Master ───────────────────────────────────────────────────────────

def get_bank_accounts(company_id: int = 1) -> list:
    """Return all bank accounts for a company."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM bank_master WHERE company_id = ? ORDER BY is_primary DESC",
            (company_id,),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def get_primary_bank(company_id: int = 1) -> dict | None:
    """Return the primary bank account."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM bank_master WHERE company_id = ? AND is_primary = 1 LIMIT 1",
            (company_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def upsert_bank_account(data: dict) -> int:
    """Insert or update a bank account."""
    data["updated_at"] = _now_ist()
    conn = _get_conn()
    try:
        bank_id = data.pop("id", None)
        if bank_id:
            col_names = _validate_columns(data.keys())
            set_clause = ", ".join([f"{k} = ?" for k in col_names])
            conn.execute(
                f"UPDATE bank_master SET {set_clause} WHERE id = ?",
                list(data.values()) + [bank_id],
            )
        else:
            data["created_at"] = _now_ist()
            col_names = _validate_columns(data.keys())
            cols = ", ".join(col_names)
            placeholders = ", ".join(["?"] * len(data))
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO bank_master ({cols}) VALUES ({placeholders})",
                list(data.values()),
            )
            bank_id = cur.lastrowid
        conn.commit()
        return bank_id
    finally:
        conn.close()


# ── Terms Master ──────────────────────────────────────────────────────────

def get_terms(category: str | None = None) -> list:
    """Return terms, optionally filtered by category. Sorted by sort_order."""
    conn = _get_conn()
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM terms_master WHERE category = ? AND is_active = 1 "
                "ORDER BY sort_order",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM terms_master WHERE is_active = 1 ORDER BY sort_order"
            ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def get_term_by_key(term_key: str) -> dict | None:
    """Return a single term by its unique key."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM terms_master WHERE term_key = ?", (term_key,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def upsert_term(data: dict) -> int:
    """Insert or update a term by term_key."""
    data["updated_at"] = _now_ist()
    conn = _get_conn()
    try:
        term_key = data.get("term_key", "")
        existing = conn.execute(
            "SELECT id FROM terms_master WHERE term_key = ?", (term_key,)
        ).fetchone()
        if existing:
            row_id = existing["id"]
            col_names = _validate_columns(data.keys())
            set_clause = ", ".join([f"{k} = ?" for k in col_names])
            conn.execute(
                f"UPDATE terms_master SET {set_clause} WHERE id = ?",
                list(data.values()) + [row_id],
            )
        else:
            data["created_at"] = _now_ist()
            col_names = _validate_columns(data.keys())
            cols = ", ".join(col_names)
            placeholders = ", ".join(["?"] * len(data))
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO terms_master ({cols}) VALUES ({placeholders})",
                list(data.values()),
            )
            row_id = cur.lastrowid
        conn.commit()
        return row_id
    finally:
        conn.close()


# ── Purchase Orders ───────────────────────────────────────────────────────

def insert_purchase_order(data: dict) -> int:
    """Create a new purchase order. Auto-generates po_number if not provided."""
    if "po_number" not in data or not data["po_number"]:
        data["po_number"] = get_next_doc_number("PO")
    data["created_at"] = _now_ist()
    data["updated_at"] = _now_ist()
    # Serialize nested dicts to JSON
    for key in ("items_json", "logistics_json", "totals_json"):
        if key in data and isinstance(data[key], (dict, list)):
            data[key] = json.dumps(data[key])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        cols = ", ".join(col_names)
        placeholders = ", ".join(["?"] * len(data))
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO purchase_orders ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_purchase_order(po_id: int) -> dict | None:
    """Get a single PO by id."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE id = ?", (po_id,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        for key in ("items_json", "logistics_json", "totals_json"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
    finally:
        conn.close()


def get_purchase_order_by_number(po_number: str) -> dict | None:
    """Get a single PO by po_number."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM purchase_orders WHERE po_number = ?", (po_number,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        for key in ("items_json", "logistics_json", "totals_json"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
    finally:
        conn.close()


def get_all_purchase_orders(status: str | None = None, supplier_id: int | None = None,
                            limit: int = 100) -> list:
    """Return purchase orders with optional filters."""
    conn = _get_conn()
    try:
        sql = "SELECT * FROM purchase_orders WHERE 1=1"
        params = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if supplier_id:
            sql += " AND supplier_id = ?"
            params.append(supplier_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            d = _row_to_dict(row)
            for key in ("items_json", "logistics_json", "totals_json"):
                if d.get(key):
                    try:
                        d[key] = json.loads(d[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            results.append(d)
        return results
    finally:
        conn.close()


def update_purchase_order(po_id: int, data: dict):
    """Update a purchase order."""
    data["updated_at"] = _now_ist()
    for key in ("items_json", "logistics_json", "totals_json"):
        if key in data and isinstance(data[key], (dict, list)):
            data[key] = json.dumps(data[key])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        set_clause = ", ".join([f"{k} = ?" for k in col_names])
        conn.execute(
            f"UPDATE purchase_orders SET {set_clause} WHERE id = ?",
            list(data.values()) + [po_id],
        )
        conn.commit()
    finally:
        conn.close()


# ── Sales Orders ──────────────────────────────────────────────────────────

def insert_sales_order(data: dict) -> int:
    """Create a new sales order. Auto-generates so_number if not provided."""
    if "so_number" not in data or not data["so_number"]:
        data["so_number"] = get_next_doc_number("SO")
    data["created_at"] = _now_ist()
    data["updated_at"] = _now_ist()
    for key in ("items_json", "logistics_json", "totals_json"):
        if key in data and isinstance(data[key], (dict, list)):
            data[key] = json.dumps(data[key])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        cols = ", ".join(col_names)
        placeholders = ", ".join(["?"] * len(data))
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO sales_orders ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_sales_order(so_id: int) -> dict | None:
    """Get a single SO by id."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sales_orders WHERE id = ?", (so_id,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        for key in ("items_json", "logistics_json", "totals_json"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
    finally:
        conn.close()


def get_sales_order_by_number(so_number: str) -> dict | None:
    """Get a single SO by so_number."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sales_orders WHERE so_number = ?", (so_number,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        for key in ("items_json", "logistics_json", "totals_json"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
    finally:
        conn.close()


def get_all_sales_orders(status: str | None = None, customer_id: int | None = None,
                         limit: int = 100) -> list:
    """Return sales orders with optional filters."""
    conn = _get_conn()
    try:
        sql = "SELECT * FROM sales_orders WHERE 1=1"
        params = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if customer_id:
            sql += " AND customer_id = ?"
            params.append(customer_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            d = _row_to_dict(row)
            for key in ("items_json", "logistics_json", "totals_json"):
                if d.get(key):
                    try:
                        d[key] = json.loads(d[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            results.append(d)
        return results
    finally:
        conn.close()


def update_sales_order(so_id: int, data: dict):
    """Update a sales order."""
    data["updated_at"] = _now_ist()
    for key in ("items_json", "logistics_json", "totals_json"):
        if key in data and isinstance(data[key], (dict, list)):
            data[key] = json.dumps(data[key])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        set_clause = ", ".join([f"{k} = ?" for k in col_names])
        conn.execute(
            f"UPDATE sales_orders SET {set_clause} WHERE id = ?",
            list(data.values()) + [so_id],
        )
        conn.commit()
    finally:
        conn.close()


# ── Payment Orders ────────────────────────────────────────────────────────

def insert_payment_order(data: dict) -> int:
    """Create a new payment order. Auto-generates pay_number if not provided."""
    if "pay_number" not in data or not data["pay_number"]:
        data["pay_number"] = get_next_doc_number("PAY")
    data["created_at"] = _now_ist()
    data["updated_at"] = _now_ist()
    if "profit_json" in data and isinstance(data["profit_json"], (dict, list)):
        data["profit_json"] = json.dumps(data["profit_json"])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        cols = ", ".join(col_names)
        placeholders = ", ".join(["?"] * len(data))
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO payment_orders ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_payment_order(pay_id: int) -> dict | None:
    """Get a single payment order by id."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM payment_orders WHERE id = ?", (pay_id,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        if d.get("profit_json"):
            try:
                d["profit_json"] = json.loads(d["profit_json"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d
    finally:
        conn.close()


def get_all_payment_orders(status: str | None = None, limit: int = 100) -> list:
    """Return payment orders with optional filters."""
    conn = _get_conn()
    try:
        sql = "SELECT * FROM payment_orders WHERE 1=1"
        params = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            d = _row_to_dict(row)
            if d.get("profit_json"):
                try:
                    d["profit_json"] = json.loads(d["profit_json"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(d)
        return results
    finally:
        conn.close()


def update_payment_order(pay_id: int, data: dict):
    """Update a payment order."""
    data["updated_at"] = _now_ist()
    if "profit_json" in data and isinstance(data["profit_json"], (dict, list)):
        data["profit_json"] = json.dumps(data["profit_json"])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        set_clause = ", ".join([f"{k} = ?" for k in col_names])
        conn.execute(
            f"UPDATE payment_orders SET {set_clause} WHERE id = ?",
            list(data.values()) + [pay_id],
        )
        conn.commit()
    finally:
        conn.close()


# ── Transporters ─────────────────────────────────────────────────────────

def insert_transporter(data: dict) -> int:
    """Create a new transporter. Returns new ID."""
    data["created_at"] = _now_ist()
    data["updated_at"] = _now_ist()
    if "vehicle_types" in data and isinstance(data["vehicle_types"], (list, tuple)):
        data["vehicle_types"] = json.dumps(data["vehicle_types"])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        cols = ", ".join(col_names)
        placeholders = ", ".join(["?"] * len(data))
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO transporters ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_all_transporters(active_only: bool = True) -> list:
    """Return all transporters."""
    conn = _get_conn()
    try:
        sql = "SELECT * FROM transporters"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY name"
        rows = conn.execute(sql).fetchall()
        results = _rows_to_list(rows)
        for r in results:
            if r.get("vehicle_types"):
                try:
                    r["vehicle_types"] = json.loads(r["vehicle_types"])
                except (json.JSONDecodeError, TypeError):
                    pass
        return results
    finally:
        conn.close()


def get_transporter(transporter_id: int) -> dict | None:
    """Get a single transporter by ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM transporters WHERE id = ?", (transporter_id,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        if d.get("vehicle_types"):
            try:
                d["vehicle_types"] = json.loads(d["vehicle_types"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d
    finally:
        conn.close()


def update_transporter(transporter_id: int, data: dict):
    """Update a transporter."""
    data["updated_at"] = _now_ist()
    if "vehicle_types" in data and isinstance(data["vehicle_types"], (list, tuple)):
        data["vehicle_types"] = json.dumps(data["vehicle_types"])
    conn = _get_conn()
    try:
        col_names = _validate_columns(data.keys())
        set_clause = ", ".join([f"{k} = ?" for k in col_names])
        conn.execute(
            f"UPDATE transporters SET {set_clause} WHERE id = ?",
            list(data.values()) + [transporter_id],
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE: Run init when executed directly
# ═══════════════════════════════════════════════════════════════════════════
# CONTACTS — Unified 24K Contact Database
# ═══════════════════════════════════════════════════════════════════════════

def insert_contact(data: dict) -> int:
    """Insert a new contact. Returns contact id."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    data.setdefault("updated_at", _now_ist())
    return _insert_row("contacts", data)


def upsert_contact(data: dict) -> int:
    """Insert or update contact by mobile1. Returns contact id."""
    mobile = data.get("mobile1", "").strip()
    if not mobile:
        return insert_contact(data)
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM contacts WHERE mobile1 = ?", (mobile,)
        ).fetchone()
        if row:
            rid = row["id"]
            data["updated_at"] = _now_ist()
            _update_row("contacts", rid, data)
            return rid
        else:
            return insert_contact(data)
    finally:
        conn.close()


def get_all_contacts(contact_type: str = None, category: str = None,
                     buyer_seller: str = None, state: str = None,
                     active_only: bool = True, limit: int = 5000,
                     offset: int = 0) -> list:
    """Return contacts, optionally filtered."""
    conn = _get_conn()
    try:
        clauses = []
        params = []
        if active_only:
            clauses.append("is_active = 1")
        if contact_type:
            clauses.append("contact_type = ?")
            params.append(contact_type)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if buyer_seller:
            clauses.append("buyer_seller_tag = ?")
            params.append(buyer_seller)
        if state:
            clauses.append("state = ?")
            params.append(state)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM contacts{where} ORDER BY rotation_priority DESC, name ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def get_contacts_for_rotation(limit: int = 2400, min_gap_days: int = 7) -> list:
    """Get contacts due for rotation — not contacted in min_gap_days, sorted by priority."""
    conn = _get_conn()
    try:
        cutoff = (datetime.now(IST) - timedelta(days=min_gap_days)).strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            """SELECT * FROM contacts
               WHERE is_active = 1
                 AND (last_contact_date IS NULL OR last_contact_date < ?)
               ORDER BY rotation_priority DESC, last_contact_date ASC NULLS FIRST
               LIMIT ?""",
            (cutoff, limit),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def get_contacts_for_broadcast(wa_only: bool = False, email_only: bool = False) -> list:
    """Get all active contacts for broadcast (festival/price)."""
    conn = _get_conn()
    try:
        clauses = ["is_active = 1"]
        if wa_only:
            clauses.append("whatsapp_opted_in = 1 AND mobile1 IS NOT NULL AND mobile1 != ''")
        if email_only:
            clauses.append("email_opted_in = 1 AND email IS NOT NULL AND email != ''")
        where = " WHERE " + " AND ".join(clauses)
        rows = conn.execute(f"SELECT * FROM contacts{where} ORDER BY name").fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def update_contact_last_contacted(contact_id: int, channel: str = "whatsapp"):
    """Update last_contact_date and increment contact_frequency."""
    now = _now_ist()
    conn = _get_conn()
    try:
        conn.execute(
            """UPDATE contacts
               SET last_contact_date = ?, last_contact_channel = ?,
                   contact_frequency = contact_frequency + 1, updated_at = ?
               WHERE id = ?""",
            (now, channel, now, contact_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_contacts_count() -> dict:
    """Return counts: total, by type, by category, opted_in stats."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM contacts WHERE is_active = 1").fetchone()["c"]
        by_type = {}
        for row in conn.execute(
            "SELECT contact_type, COUNT(*) AS c FROM contacts WHERE is_active = 1 GROUP BY contact_type"
        ).fetchall():
            by_type[row["contact_type"]] = row["c"]
        by_category = {}
        for row in conn.execute(
            "SELECT category, COUNT(*) AS c FROM contacts WHERE is_active = 1 GROUP BY category"
        ).fetchall():
            by_category[row["category"] or "Uncategorized"] = row["c"]
        wa_opted = conn.execute(
            "SELECT COUNT(*) AS c FROM contacts WHERE is_active = 1 AND whatsapp_opted_in = 1"
        ).fetchone()["c"]
        email_opted = conn.execute(
            "SELECT COUNT(*) AS c FROM contacts WHERE is_active = 1 AND email_opted_in = 1"
        ).fetchone()["c"]
        return {
            "total": total,
            "by_type": by_type,
            "by_category": by_category,
            "whatsapp_opted_in": wa_opted,
            "email_opted_in": email_opted,
        }
    finally:
        conn.close()


def search_contacts(query: str, limit: int = 50) -> list:
    """Search contacts on name, company_name, city, mobile1, email."""
    conn = _get_conn()
    try:
        q = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM contacts
               WHERE is_active = 1 AND (
                   name LIKE ? OR company_name LIKE ? OR city LIKE ?
                   OR mobile1 LIKE ? OR email LIKE ? OR state LIKE ?
               ) ORDER BY name LIMIT ?""",
            (q, q, q, q, q, q, limit),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ── Contact Rotation Log ─────────────────────────────────────────────────

def insert_rotation_log(data: dict) -> int:
    """Log a rotation outreach attempt."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    return _insert_row("contact_rotation_log", data)


def get_rotation_stats(date: str) -> dict:
    """Return stats for a rotation day: sent, pending, failed."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM contact_rotation_log WHERE rotation_date = ? GROUP BY status",
            (date,),
        ).fetchall()
        stats = {"sent": 0, "pending": 0, "failed": 0, "skipped": 0, "total": 0}
        for r in rows:
            stats[r["status"]] = r["c"]
            stats["total"] += r["c"]
        return stats
    finally:
        conn.close()


# ── Festival Broadcasts ──────────────────────────────────────────────────

def insert_festival_broadcast(data: dict) -> int:
    """Create a festival broadcast record."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    return _insert_row("festival_broadcasts", data)


def update_festival_broadcast(broadcast_id: int, data: dict):
    """Update festival broadcast progress."""
    _update_row("festival_broadcasts", broadcast_id, data)


def get_festival_broadcasts(limit: int = 20) -> list:
    """Get recent festival broadcasts."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM festival_broadcasts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ── Price Update Log ─────────────────────────────────────────────────────

def insert_price_update_log(data: dict) -> int:
    """Log a price change."""
    data = dict(data)
    data.setdefault("created_at", _now_ist())
    return _insert_row("price_update_log", data)


def get_price_update_history(limit: int = 50) -> list:
    """Get recent price updates."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM price_update_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")
    print("Tables created:")
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for r in rows:
            count = conn.execute(f"SELECT COUNT(*) AS cnt FROM {r['name']}").fetchone()
            print(f"  - {r['name']:20s}  ({count['cnt']} rows)")
    finally:
        conn.close()
