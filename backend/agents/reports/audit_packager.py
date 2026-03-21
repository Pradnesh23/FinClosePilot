"""
Audit Trail Packager — bundles complete audit package for a run.
"""

import logging
import json
from datetime import datetime
from backend.database.audit_logger import get_audit_trail, get_guardrail_fires
from backend.database.models import get_db_connection

logger = logging.getLogger(__name__)


async def build_audit_package(run_id: str) -> dict:
    """Build a complete audit package for external auditors."""
    conn = get_db_connection()
    try:
        # Fetch all reports
        reports_rows = conn.execute(
            "SELECT report_type, content, generated_at, critic_score FROM reports WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        reports = {}
        for r in reports_rows:
            reports[r["report_type"]] = {
                "content": json.loads(r["content"]),
                "generated_at": r["generated_at"],
                "critic_score": r["critic_score"],
            }

        # Fetch anomalies
        anomalies = conn.execute(
            "SELECT * FROM anomalies WHERE run_id = ?", (run_id,)
        ).fetchall()

        # Fetch recon breaks
        breaks = conn.execute(
            "SELECT * FROM recon_breaks WHERE run_id = ?", (run_id,)
        ).fetchall()

        audit_trail = get_audit_trail(run_id)
        guardrail_fires = get_guardrail_fires(run_id)

        # Fetch run info
        run_info = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        run_dict = dict(run_info) if run_info else {}

        package = {
            "run_id": run_id,
            "generated_at": datetime.utcnow().isoformat(),
            "run_summary": run_dict,
            "reports": reports,
            "anomalies_count": len(anomalies),
            "anomalies": [dict(a) for a in anomalies],
            "recon_breaks_count": len(breaks),
            "recon_breaks": [dict(b) for b in breaks],
            "guardrail_fires_count": len(guardrail_fires),
            "guardrail_fires": guardrail_fires,
            "audit_trail_events": len(audit_trail),
            "audit_trail": audit_trail,
            "certification": {
                "prepared_by": "FinClosePilot AI Agent",
                "model": "Gemini 2.0 Flash",
                "method": "AI-assisted with regulatory guardrails",
                "disclaimer": (
                    "This package is AI-generated and requires CFO/CA attestation "
                    "before submission to regulatory authorities."
                ),
            },
        }
        return package
    finally:
        conn.close()
