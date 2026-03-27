"""
Audit Trail Packager — bundles complete audit package for a run.
"""

import logging
import json
from datetime import datetime
from backend.database.audit_logger import get_audit_trail, get_guardrail_fires # type: ignore
from sqlalchemy import select # type: ignore

from backend.database.models import ( # type: ignore
    get_db_session,
    reports as reports_table,
    anomalies as anomalies_table,
    recon_breaks as recon_breaks_table,
    pipeline_runs as pipeline_runs_table,
)

logger = logging.getLogger(__name__)


async def build_audit_package(run_id: str) -> dict: # type: ignore
    """Build a complete audit package for external auditors."""
    db = get_db_session()
    try:
        reports_rows = db.execute(
            select(reports_table.c.report_type, reports_table.c.content, reports_table.c.generated_at, reports_table.c.critic_score)
            .where(reports_table.c.run_id == run_id)
        ).mappings().all()
        reports = {}
        for r in reports_rows:
            reports[r["report_type"]] = {
                "content": json.loads(r["content"]) if r.get("content") else {},
                "generated_at": r.get("generated_at"),
                "critic_score": r.get("critic_score"),
            }

        anomalies_rows = db.execute(
            select(anomalies_table).where(anomalies_table.c.run_id == run_id)
        ).mappings().all()
        breaks_rows = db.execute(
            select(recon_breaks_table).where(recon_breaks_table.c.run_id == run_id)
        ).mappings().all()

        audit_trail = get_audit_trail(run_id)
        guardrail_fires = get_guardrail_fires(run_id)

        run_info = db.execute(
            select(pipeline_runs_table).where(pipeline_runs_table.c.run_id == run_id)
        ).mappings().first()
        run_dict = dict(run_info) if run_info else {}

        return {
            "run_id": run_id,
            "generated_at": datetime.utcnow().isoformat(),
            "run_summary": run_dict,
            "reports": reports,
            "anomalies_count": len(anomalies_rows),
            "anomalies": [dict(a) for a in anomalies_rows],
            "recon_breaks_count": len(breaks_rows),
            "recon_breaks": [dict(b) for b in breaks_rows],
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
    finally:
        db.close()
