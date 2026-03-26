"""
SQLite database models for FinClosePilot.
Creates all tables on startup.
"""

import sqlite3
import os
import json
from datetime import datetime
from backend.config import SQLITE_DB_PATH


def get_db_connection():
    """Returns a SQLite connection with row_factory set."""
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'EMPLOYEE', -- 'MANAGER' or 'EMPLOYEE'
            manager_id INTEGER REFERENCES users(id), -- If EMPLOYEE, who is their manager?
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)

    # Pipeline runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            period TEXT,
            total_records INTEGER DEFAULT 0,
            matched_records INTEGER DEFAULT 0,
            breaks INTEGER DEFAULT 0,
            anomalies INTEGER DEFAULT 0,
            guardrail_fires INTEGER DEFAULT 0,
            hard_blocks INTEGER DEFAULT 0,
            soft_flags INTEGER DEFAULT 0,
            advisories INTEGER DEFAULT 0,
            total_blocked_inr REAL DEFAULT 0,
            total_flagged_inr REAL DEFAULT 0,
            time_taken_seconds REAL DEFAULT 0,
            entities TEXT DEFAULT '[]',
            source_files TEXT DEFAULT '[]',
            error TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Audit log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            agent TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            regulation TEXT,
            confidence REAL,
            status TEXT DEFAULT 'INFO',
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Transactions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            transaction_id TEXT,
            date TEXT,
            vendor_name TEXT,
            vendor_gstin TEXT,
            invoice_no TEXT,
            amount REAL,
            type TEXT,
            narration TEXT,
            gl_account TEXT,
            hsn_code TEXT,
            gst_rate REAL,
            igst REAL,
            cgst REAL,
            sgst REAL,
            source TEXT,
            cost_centre TEXT,
            vendor_type TEXT,
            raw_data TEXT,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Reconciliation breaks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recon_breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            recon_type TEXT NOT NULL,
            break_category TEXT,
            vendor_name TEXT,
            vendor_gstin TEXT,
            transaction_id TEXT,
            amount REAL,
            source_a_amount REAL,
            source_b_amount REAL,
            difference REAL,
            root_cause TEXT,
            auto_clearable INTEGER DEFAULT 0,
            confidence REAL,
            regulation TEXT,
            ai_reasoning TEXT,
            status TEXT DEFAULT 'OPEN',
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Anomalies
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            anomaly_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            vendor_name TEXT,
            vendor_gstin TEXT,
            transaction_ids TEXT,
            financial_exposure_inr REAL,
            p_value REAL,
            chi_square REAL,
            reasoning TEXT,
            status TEXT DEFAULT 'OPEN',
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Guardrail fires
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guardrail_fires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            rule_id TEXT NOT NULL,
            rule_level TEXT NOT NULL,
            regulation TEXT,
            section TEXT,
            vendor_name TEXT,
            vendor_gstin TEXT,
            transaction_id TEXT,
            amount_inr REAL,
            violation_detail TEXT,
            action_taken TEXT,
            cfo_override INTEGER DEFAULT 0,
            override_reason TEXT,
            override_by TEXT,
            override_at TEXT,
            telegram_sent INTEGER DEFAULT 0,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Reports
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            report_type TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            content TEXT NOT NULL,
            critic_score REAL,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # RLHF signals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rlhf_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            original_output TEXT,
            correction TEXT,
            correction_reason TEXT,
            corrected_by TEXT,
            guardrail_fire_id INTEGER,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Regulatory changes (System-wide)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regulatory_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detected_at TEXT NOT NULL,
            framework TEXT NOT NULL,
            notification_no TEXT,
            summary TEXT NOT NULL,
            what_changed TEXT,
            effective_date TEXT,
            affected_areas TEXT,
            action_required TEXT,
            urgency TEXT NOT NULL,
            source_url TEXT,
            applied INTEGER DEFAULT 0
        )
    """)

    # Letta fallback store
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS letta_fallback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            agent_id TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            label TEXT,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Escalations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            user_id INTEGER,
            agent_type TEXT NOT NULL,
            item_id TEXT,
            reason_code TEXT NOT NULL,
            confidence REAL,
            threshold REAL,
            item_json TEXT,
            escalation_level TEXT NOT NULL DEFAULT 'HUMAN_REVIEW',
            resolved INTEGER DEFAULT 0,
            resolved_by TEXT,
            resolved_at TEXT,
            resolution_note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Model usage tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            user_id INTEGER,
            task_type TEXT NOT NULL,
            model_used TEXT NOT NULL,
            tokens_estimated INTEGER,
            latency_ms INTEGER,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ─── Migration Logic (Add user_id to existing tables if missing) ───
    tables_to_migrate = [
        "pipeline_runs", "audit_log", "transactions", "recon_breaks",
        "anomalies", "guardrail_fires", "reports", "rlhf_signals",
        "letta_fallback", "escalations", "model_usage"
    ]
    for table in tables_to_migrate:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")
        except sqlite3.OperationalError:
            pass # Column already exists

    # Also migrate users table to add manager_id if missing
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN manager_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("[DB] All tables initialized with Multi-User support.")

