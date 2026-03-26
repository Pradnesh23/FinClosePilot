import json
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from backend.database.models import get_db_connection


def log_event(
    run_id: str,
    agent: str,
    action: str,
    user_id: Optional[int] = None,
    details: Optional[dict] = None,
    regulation: Optional[str] = None,
    confidence: Optional[float] = None,
    status: str = "INFO",
):
    """Log a pipeline event to the audit trail."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO audit_log
                (run_id, user_id, timestamp, agent, action, details, regulation, confidence, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                datetime.utcnow().isoformat(),
                agent,
                action,
                json.dumps(details) if details else None,
                regulation,
                confidence,
                status,
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"[AuditLogger] Failed to log event: {e}")
    finally:
        conn.close()


def get_audit_trail(run_id: str, limit: int = 200) -> list:
    """Fetch audit events for a given run."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM audit_log
            WHERE run_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_run(run_id: str, user_id: Optional[int] = None, period: str = "Q3FY26", source_files: Optional[list] = None) -> None:
    """Create or upsert a pipeline run record."""
    conn = get_db_connection()
    now = datetime.utcnow().isoformat()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO pipeline_runs
                (run_id, user_id, created_at, updated_at, status, period, source_files)
            VALUES (?, ?, ?, ?, 'RUNNING', ?, ?)
            """,
            (
                run_id,
                user_id,
                now,
                now,
                period,
                json.dumps(source_files or []),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_run(run_id: str, **kwargs) -> None:
    """Update pipeline run fields."""
    if not kwargs:
        return
    conn = get_db_connection()
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [run_id]
    try:
        conn.execute(f"UPDATE pipeline_runs SET {fields} WHERE run_id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_run(run_id: str) -> dict | None:
    """Fetch a single run record."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_transaction(run_id: str, txn: dict, user_id: Optional[int] = None) -> None:
    """Save a normalised transaction."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO transactions
                (run_id, user_id, transaction_id, date, vendor_name, vendor_gstin,
                 invoice_no, amount, type, narration, gl_account, hsn_code,
                 gst_rate, igst, cgst, sgst, source, cost_centre, vendor_type, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                txn.get("id") or txn.get("transaction_id"),
                txn.get("date"),
                txn.get("vendor_canonical") or txn.get("vendor_name"),
                txn.get("vendor_gstin"),
                txn.get("invoice_no") or txn.get("reference_no"),
                txn.get("amount"),
                txn.get("type"),
                txn.get("narration"),
                txn.get("gl_account"),
                txn.get("hsn_code"),
                txn.get("gst_rate"),
                txn.get("igst"),
                txn.get("cgst"),
                txn.get("sgst"),
                txn.get("source"),
                txn.get("cost_centre"),
                txn.get("vendor_type"),
                json.dumps(txn.get("raw_data", {})),
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"[AuditLogger] Failed to save transaction: {e}")
    finally:
        conn.close()


def list_runs(user_id: int = None, is_manager: bool = False, limit: int = 50) -> list:
    """List pipeline runs, optionally filtered by user_id for Employees."""
    conn = get_db_connection()
    try:
        if is_manager and user_id is None:
            # Global view for managers (if no user_id specified)
            query = "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT ?"
            params = (limit,)
        elif user_id is not None:
            # Personal history (for both Employees and Managers)
            query = "SELECT * FROM pipeline_runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
            params = (user_id, limit)
        else:
            # Fallback (non-manager, no user_id) - return empty or generic recent
            query = "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT ?"
            params = (limit,)
            
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_team_runs(manager_id: int, limit: int = 50) -> list:
    """List all runs from employees managed by this manager."""
    conn = get_db_connection()
    try:
        query = """
            SELECT pr.*, u.username as employee_name
            FROM pipeline_runs pr
            JOIN users u ON pr.user_id = u.id
            WHERE u.manager_id = ?
            ORDER BY pr.created_at DESC
            LIMIT ?
        """
        rows = conn.execute(query, (manager_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_guardrail_fire(run_id: str, fire: dict, user_id: Optional[int] = None) -> int:
    """Save a guardrail fire and return its rowid."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO guardrail_fires
                (run_id, user_id, rule_id, rule_level, regulation, section,
                 vendor_name, vendor_gstin, transaction_id,
                 amount_inr, violation_detail, action_taken)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                fire.get("rule_id"),
                fire.get("rule_level"),
                fire.get("regulation"),
                fire.get("section"),
                fire.get("vendor_name"),
                fire.get("vendor_gstin"),
                fire.get("transaction_id"),
                fire.get("amount_inr"),
                fire.get("violation_detail"),
                fire.get("action_taken"),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def save_recon_break(run_id: str, brk: dict, user_id: Optional[int] = None) -> None:
    """Save a reconciliation break."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO recon_breaks
                (run_id, user_id, recon_type, break_category, vendor_name, vendor_gstin,
                 transaction_id, amount, source_a_amount, source_b_amount,
                 difference, root_cause, auto_clearable, confidence,
                 regulation, ai_reasoning, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """,
            (
                run_id,
                user_id,
                brk.get("recon_type") or "GST",
                brk.get("break_type") or brk.get("root_cause"),
                brk.get("vendor_name"),
                brk.get("vendor_gstin"),
                brk.get("invoice_no") or brk.get("reference_no") or brk.get("transaction_id"),
                brk.get("difference"),
                brk.get("books_amount") or brk.get("gl_amount"),
                brk.get("gstr2a_amount") or brk.get("bank_amount"),
                brk.get("difference"),
                brk.get("root_cause") or brk.get("break_type"),
                1 if brk.get("auto_clearable") else 0,
                brk.get("confidence"),
                brk.get("regulation"),
                brk.get("ai_reasoning") or brk.get("description"),
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"[AuditLogger] Failed to save recon break: {e}")
    finally:
        conn.close()


def get_guardrail_fires(run_id: str) -> list:
    """Fetch all guardrail fires for a specific run."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM guardrail_fires WHERE run_id = ? ORDER BY id ASC",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_anomaly(run_id: str, anomaly: dict, user_id: Optional[int] = None) -> None:
    """Save an anomaly finding."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO anomalies
                (run_id, user_id, anomaly_type, severity, vendor_name, vendor_gstin,
                 transaction_ids, financial_exposure_inr, p_value, chi_square, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                anomaly.get("anomaly_type"),
                anomaly.get("severity"),
                anomaly.get("vendor_name"),
                anomaly.get("vendor_gstin"),
                json.dumps(anomaly.get("transaction_ids", [])),
                anomaly.get("financial_exposure_inr"),
                anomaly.get("p_value"),
                anomaly.get("chi_square"),
                anomaly.get("reasoning"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_rlhf_signal(run_id: str, signal: dict, user_id: Optional[int] = None) -> None:
    """Save a human correction signal."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO rlhf_signals
                (run_id, user_id, timestamp, signal_type, original_output,
                 correction, correction_reason, corrected_by, guardrail_fire_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                datetime.utcnow().isoformat(),
                signal.get("signal_type"),
                json.dumps(signal.get("original_output")),
                signal.get("correction"),
                signal.get("correction_reason"),
                signal.get("corrected_by", "CFO"),
                signal.get("guardrail_fire_id"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_report(run_id: str, report_type: str, content: dict, user_id: Optional[int] = None, critic_score: Optional[float] = None) -> None:
    """Save a generated report."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO reports
                (run_id, user_id, report_type, generated_at, content, critic_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                report_type,
                datetime.utcnow().isoformat(),
                json.dumps(content),
                critic_score,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_report(run_id: str, report_type: str) -> dict | None:
    """Fetch a specific report for a run."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM reports WHERE run_id = ? AND report_type = ? ORDER BY id DESC LIMIT 1",
            (run_id, report_type),
        ).fetchone()
        if row:
            r = dict(row)
            r["content"] = json.loads(r["content"])
            return r
        return None
    finally:
        conn.close()


def save_regulatory_change(change: dict) -> None:
    """Save a detected regulatory change."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO regulatory_changes
                (detected_at, framework, notification_no, summary,
                 what_changed, effective_date, affected_areas,
                 action_required, urgency, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                change.get("framework"),
                change.get("notification_no"),
                change.get("summary"),
                change.get("what_changed"),
                change.get("effective_date"),
                json.dumps(change.get("affected_areas", [])),
                change.get("action_required"),
                change.get("urgency"),
                change.get("source_url"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_regulatory_changes(limit: int = 50) -> list:
    """Get recent regulatory changes."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM regulatory_changes ORDER BY detected_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Escalation CRUD ──────────────────────────────────────────────────────────

def log_escalation(record: dict, user_id: Optional[int] = None) -> int:
    """Save an escalation record, return its rowid."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO escalations
                (run_id, user_id, agent_type, item_id, reason_code, confidence,
                 threshold, item_json, escalation_level, resolved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                record.get("run_id"),
                user_id,
                record.get("agent_type"),
                record.get("escalation_id") or record.get("item_id"),
                record.get("reason_code"),
                record.get("confidence"),
                record.get("threshold"),
                json.dumps(record.get("item", {})),
                record.get("escalation_level", "HUMAN_REVIEW"),
                record.get("created_at", datetime.utcnow().isoformat()),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"[AuditLogger] Failed to log escalation: {e}")
        return -1
    finally:
        conn.close()


def get_escalations(run_id: str, user_id: int = None) -> list:
    """Get all escalations for a run, optionally filtered by user_id."""
    conn = get_db_connection()
    try:
        query = "SELECT * FROM escalations WHERE run_id = ?"
        params = [run_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY id ASC"
        
        rows = conn.execute(query, tuple(params)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["item_json"] = json.loads(d["item_json"]) if d.get("item_json") else {}
            except (json.JSONDecodeError, TypeError):
                pass
            result.append(d)
        return result
    finally:
        conn.close()


def get_unresolved_escalations(user_id: Optional[int] = None) -> list:
    """Get unresolved escalations, optionally filtered by user_id."""
    conn = get_db_connection()
    try:
        where = "WHERE resolved = 0"
        params = []
        if user_id:
            where += " AND user_id = ?"
            params.append(user_id)
            
        rows = conn.execute(
            f"SELECT * FROM escalations {where} ORDER BY created_at DESC",
            tuple(params)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["item_json"] = json.loads(d["item_json"]) if d.get("item_json") else {}
            except (json.JSONDecodeError, TypeError):
                pass
            result.append(d)
        return result
    finally:
        conn.close()


def resolve_escalation(escalation_id: int, resolved_by: str, resolution_note: str) -> bool:
    """Resolve an escalation by setting resolved=1 and storing who+when+note."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            UPDATE escalations
            SET resolved = 1, resolved_by = ?, resolved_at = ?, resolution_note = ?
            WHERE id = ?
            """,
            (resolved_by, datetime.utcnow().isoformat(), resolution_note, escalation_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[AuditLogger] Failed to resolve escalation: {e}")
        return False
    finally:
        conn.close()


# ─── Model Usage Tracking ─────────────────────────────────────────────────────

def log_model_usage(
    run_id: str, task_type: str, model_used: str, user_id: Optional[int] = None,
    tokens_estimated: Optional[int] = None, latency_ms: Optional[int] = None
) -> None:
    """Log a model call for cost tracking."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO model_usage
                (run_id, user_id, task_type, model_used, tokens_estimated, latency_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, user_id, task_type, model_used, tokens_estimated, latency_ms,
             datetime.utcnow().isoformat()),
        )
        conn.commit()
    except Exception as e:
        print(f"[AuditLogger] Failed to log model usage: {e}")
    finally:
        conn.close()


def get_model_usage_stats(run_id: str = None) -> dict:
    """Get model usage stats, optionally scoped to a specific run."""
    conn = get_db_connection()
    try:
        where = "WHERE run_id = ?" if run_id else ""
        params = (run_id,) if run_id else ()

        rows = conn.execute(
            f"SELECT model_used, COUNT(*) as cnt, SUM(tokens_estimated) as total_tokens "
            f"FROM model_usage {where} GROUP BY model_used",
            params,
        ).fetchall()

        calls_by_model = {}
        total_tokens_by_model = {}
        for r in rows:
            calls_by_model[r["model_used"]] = r["cnt"]
            total_tokens_by_model[r["model_used"]] = r["total_tokens"] or 0

        python_rows = conn.execute(
            f"SELECT COUNT(*) as cnt FROM model_usage {where} AND model_used = 'PYTHON_ONLY'"
            if where else
            "SELECT COUNT(*) as cnt FROM model_usage WHERE model_used = 'PYTHON_ONLY'",
            params,
        ).fetchone()
        python_only = python_rows["cnt"] if python_rows else 0

        return {
            "calls_by_model": calls_by_model,
            "total_tokens_by_model": total_tokens_by_model,
            "python_only_calls": python_only,
        }
    finally:
        conn.close()
