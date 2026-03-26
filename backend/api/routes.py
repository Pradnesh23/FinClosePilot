"""
All FastAPI API routes for FinClosePilot.
"""

import json
import os
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.database.audit_logger import (
    get_audit_trail, get_run, list_runs, get_report,
    get_guardrail_fires, get_regulatory_changes,
)
from backend.database.models import init_db, get_db_connection
from backend.agents.pipeline import run_pipeline
from backend.agents.reports.audit_packager import build_audit_package
from backend.agents.additions.regulatory_monitor import run_regulatory_monitor
from backend.agents.learning.rlhf_collector import collect_cfo_override
from backend.api.websocket import manager
from backend.memory.letta_client import (
    init_letta_client, create_or_get_agent, query_audit_trail,
    seed_past_period_data, get_archival_by_label, LettaClientWrapper,
)
from backend.notifications.telegram_bot import send_test_message

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level Letta state (initialized on startup)
_letta_client = None
_agent_id = ""


def get_letta():
    return _letta_client, _agent_id


async def init_letta_on_startup():
    global _letta_client, _agent_id
    _letta_client = init_letta_client()
    _agent_id = await create_or_get_agent(_letta_client, "FinClosePilot")
    logger.info(f"[API] Letta initialized: agent_id={_agent_id}")


# ─── Models ─────────────────────────────────────────────────────────────────
class AuditQueryRequest(BaseModel):
    question: str
    run_id: Optional[str] = None


class RLHFSignalRequest(BaseModel):
    run_id: str
    guardrail_fire_id: int
    override_reason: str
    corrected_by: str = "CFO"


class MultiEntityUpload(BaseModel):
    entities: list


# ─── File Upload & Pipeline ─────────────────────────────────────────────────
@router.post("/api/upload")
async def upload_and_run(
    background_tasks: BackgroundTasks,
    transactions: Optional[UploadFile] = File(None),
    bank_statement: Optional[UploadFile] = File(None),
    gst_portal: Optional[UploadFile] = File(None),
    form26as: Optional[UploadFile] = File(None),
    period: str = Form("Q3 FY26"),
):
    """Accept file uploads and start the pipeline."""
    run_id = str(uuid.uuid4())
    raw_data = {}

    for name, upload in [
        ("ERP", transactions), ("BANK", bank_statement), ("GST_PORTAL", gst_portal)
    ]:
        if upload:
            content = await upload.read()
            raw_data[name] = content.decode("utf-8", errors="replace")

    form26as_path = None
    if form26as:
        save_path = f"/tmp/form26as_{run_id}.pdf"
        with open(save_path, "wb") as f:
            f.write(await form26as.read())
        form26as_path = save_path

    ws_cb = manager.make_callback(run_id)
    lc, ag = get_letta()

    background_tasks.add_task(
        run_pipeline,
        raw_data=raw_data,
        run_id=run_id,
        period=period,
        ws_callback=ws_cb,
        form26as_path=form26as_path,
        letta_client_=lc,
        agent_id=ag,
    )

    return {"run_id": run_id, "status": "STARTED", "period": period}


@router.post("/api/upload/multi")
async def upload_multi_entity(
    background_tasks: BackgroundTasks,
    payload: dict,
):
    """Accept multi-entity data and start group close pipeline."""
    run_id = str(uuid.uuid4())
    entities = payload.get("entities", [])
    period = payload.get("period", "Q3 FY26")
    lc, ag = get_letta()
    ws_cb = manager.make_callback(run_id)

    background_tasks.add_task(
        run_pipeline,
        raw_data={},
        run_id=run_id,
        period=period,
        ws_callback=ws_cb,
        entities=entities,
        letta_client_=lc,
        agent_id=ag,
    )
    return {"run_id": run_id, "status": "STARTED", "entities": len(entities)}


# ─── Demo Mode ──────────────────────────────────────────────────────────────
@router.get("/api/demo/load")
async def load_demo(background_tasks: BackgroundTasks):
    """Load demo dataset and start the pipeline."""
    demo_path = Path("./data/demo")
    raw_data = {}

    # Load demo CSVs
    for name, filename in [
        ("ERP", "demo_transactions.csv"),
        ("BANK", "demo_bank_statement.csv"),
        ("GST_PORTAL", "demo_gst_portal.csv"),
    ]:
        fp = demo_path / filename
        if fp.exists():
            raw_data[name] = fp.read_text(encoding="utf-8")

    # Seed Letta with past period data
    past_data_path = demo_path / "past_period_data.json"
    if past_data_path.exists():
        past_data = json.loads(past_data_path.read_text())
        lc, ag = get_letta()
        background_tasks.add_task(seed_past_period_data, lc, ag, past_data)

    run_id = str(uuid.uuid4())
    lc, ag = get_letta()
    ws_cb = manager.make_callback(run_id)

    background_tasks.add_task(
        run_pipeline,
        raw_data=raw_data,
        run_id=run_id,
        period="Q3 FY26",
        ws_callback=ws_cb,
        letta_client_=lc,
        agent_id=ag,
    )

    return {"run_id": run_id, "status": "STARTED", "demo": True, "period": "Q3 FY26"}


# ─── Run Results ─────────────────────────────────────────────────────────────
@router.get("/api/runs")
async def get_runs():
    """List all pipeline runs."""
    return {"runs": list_runs()}


@router.get("/api/runs/{run_id}")
async def get_run_result(run_id: str):
    """Full results for a run."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    audit_trail = get_audit_trail(run_id, limit=50)
    guardrail_fires = get_guardrail_fires(run_id)

    # Fetch reports from DB
    reports = {}
    for rtype in ("gstr3b", "variance", "audit_committee", "tax_optimiser"):
        r = get_report(run_id, rtype)
        if r:
            reports[rtype] = r["content"]

    # Fetch anomalies
    conn = get_db_connection()
    try:
        anomaly_rows = conn.execute(
            "SELECT * FROM anomalies WHERE run_id = ?", (run_id,)
        ).fetchall()
        anomalies = [dict(a) for a in anomaly_rows]
    finally:
        conn.close()

    # Fetch structured results from Letta for frontend components (Heatmaps, Charts)
    lc, ag = get_letta()
    recon_results = await get_archival_by_label(lc, ag, f"recon_{run_id}")
    anomalies_summary = await get_archival_by_label(lc, ag, f"anomalies_{run_id}")

    return {
        "run": run,
        "reports": reports,
        "guardrail_fires": guardrail_fires,
        "anomalies": anomalies_summary or {},
        "anomaly_records": anomalies,
        "recon_results": recon_results or {},
        "audit_trail": audit_trail,
    }


@router.get("/api/runs/{run_id}/report/{report_type}")
async def get_specific_report(run_id: str, report_type: str):
    """Get a specific report type for a run."""
    r = get_report(run_id, report_type)
    if not r:
        raise HTTPException(status_code=404, detail=f"Report '{report_type}' not found for run {run_id}")
    return r


@router.get("/api/runs/{run_id}/audit-package")
async def get_audit_package(run_id: str):
    """Build and return complete audit package."""
    try:
        package = await build_audit_package(run_id)
        return package
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Audit Query ─────────────────────────────────────────────────────────────
@router.post("/api/audit/query")
async def audit_query(req: AuditQueryRequest):
    """Natural language audit trail query with synthesized answer."""
    from backend.agents.model_router import route_call
    
    lc, ag = get_letta()
    try:
        results = await query_audit_trail(lc, ag, req.question)
    except Exception:
        results = []

    # Enrich with DB audit trail
    db_trail = []
    if req.run_id:
        db_trail = get_audit_trail(req.run_id)
        keyword = req.question.lower()
        relevant = [
            e for e in db_trail
            if any(k in (e.get("action", "") + e.get("agent", "") + str(e.get("details", ""))).lower()
                   for k in keyword.split())
        ]
        results = relevant[:15] + results[:5]

    # Synthesize an answer if we have results
    answer = "No relevant audit records found to answer this specific question."
    if results:
        context = "\n".join([
            f"- [{r.get('agent', 'system')}] {r.get('action') or r.get('event')}: {str(r.get('details') or '')}"
            for r in results[:10]
        ])
        
        system_prompt = "You are a senior auditor. Answer the user's question concisely based ONLY on the provided audit trail logs. If the answer isn't there, say you don't know."
        user_message = f"Audit Trail Context:\n{context}\n\nQuestion: {req.question}"
        
        try:
            resp = await route_call("audit_query_response", system_prompt, user_message, run_id=req.run_id or "query")
            answer = resp["response"]
        except Exception as e:
            answer = f"Error generating answer: {str(e)}"

    return {
        "question": req.question, 
        "answer": answer,
        "results": results, 
        "count": len(results)
    }



# ─── RLHF Signal ─────────────────────────────────────────────────────────────
@router.post("/api/rlhf/signal")
async def rlhf_signal(req: RLHFSignalRequest):
    """Human correction signal — CFO override of a SOFT_FLAG."""
    lc, ag = get_letta()

    # Fetch the guardrail fire
    fires = get_guardrail_fires(req.run_id)
    fire = next((f for f in fires if f["id"] == req.guardrail_fire_id), None)
    if not fire:
        raise HTTPException(status_code=404, detail="Guardrail fire not found")

    result = await collect_cfo_override(
        run_id=req.run_id,
        guardrail_fire_id=req.guardrail_fire_id,
        original_fire=fire,
        override_reason=req.override_reason,
        corrected_by=req.corrected_by,
        letta_client_=lc,
        agent_id=ag,
    )
    return result


# ─── Regulatory Monitor ──────────────────────────────────────────────────────
@router.get("/api/regulatory/check")
async def trigger_regulatory_check(background_tasks: BackgroundTasks):
    """Trigger on-demand regulatory rules check."""
    lc, ag = get_letta()
    background_tasks.add_task(run_regulatory_monitor, lc, ag)
    return {"status": "TRIGGERED", "message": "Regulatory check running in background"}


@router.get("/api/regulatory/updates")
async def get_regulatory_updates():
    """List all known regulatory updates from database."""
    changes = get_regulatory_changes(limit=50)
    return {"changes": changes, "count": len(changes)}


# ─── PHASE 2: Escalations ───────────────────────────────────────────────────
class EscalationResolveRequest(BaseModel):
    escalation_id: int
    resolved_by: str = "CFO"
    resolution_notes: str = ""


@router.get("/api/escalations/{run_id}")
async def get_escalations_api(run_id: str, resolved: Optional[bool] = None):
    """Get all escalations for a run, optionally filtered by resolved status."""
    from backend.database.audit_logger import get_escalations, get_unresolved_escalations
    if resolved is False:
        escs = get_unresolved_escalations(run_id)
    else:
        escs = get_escalations(run_id)
    return {"run_id": run_id, "escalations": escs, "count": len(escs)}


@router.post("/api/escalations/resolve")
async def resolve_escalation_api(req: EscalationResolveRequest):
    """Resolve an escalation (CFO/human decision)."""
    from backend.database.audit_logger import resolve_escalation
    success = resolve_escalation(req.escalation_id, req.resolved_by, req.resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return {"success": True, "escalation_id": req.escalation_id, "resolved_by": req.resolved_by}


# ─── PHASE 2: Cost Efficiency ───────────────────────────────────────────────
@router.get("/api/cost-efficiency/{run_id}")
async def get_cost_efficiency(run_id: str):
    """Get model routing cost efficiency stats for a run."""
    from backend.agents.model_router import get_routing_stats
    from backend.database.audit_logger import get_model_usage_stats
    routing = get_routing_stats(run_id)
    db_stats = get_model_usage_stats(run_id)
    return {
        "run_id": run_id,
        "routing_stats": routing,
        "db_stats": db_stats,
    }


# ─── PHASE 2: Surprise Scenarios ────────────────────────────────────────────
@router.post("/api/surprise/{scenario_type}")
async def trigger_surprise(scenario_type: str, background_tasks: BackgroundTasks):
    """Trigger a pre-built surprise scenario for live demo."""
    from backend.agents.surprise_handler import (
        detect_surprise_scenario, handle_out_of_scope, handle_rule_conflict,
    )
    demo_path = Path("./data/demo/surprise_scenarios.json")
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="Surprise scenarios file not found")

    scenarios = json.loads(demo_path.read_text())
    valid_types = list(scenarios.keys())

    if scenario_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario. Valid: {valid_types}",
        )

    scenario = scenarios[scenario_type]
    lc, ag = get_letta()

    if scenario_type == "out_of_scope":
        result = await handle_out_of_scope(scenario["query"])
        return {"scenario": scenario_type, "result": result}

    if scenario_type == "rule_conflict":
        result = await handle_rule_conflict(
            scenario["transaction"],
            scenario["conflicting_rules"],
            letta_client=lc,
            agent_id=ag,
        )
        return {"scenario": scenario_type, "result": result}

    # For ambiguous_fraud, unknown_regulation, auto_clear_trap
    txn = scenario.get("transaction", {})
    result = await detect_surprise_scenario(txn, letta_client=lc, agent_id=ag)
    return {
        "scenario": scenario_type,
        "detection_result": result,
        "expected_outcome": scenario.get("expected_outcome"),
        "demo_talking_point": scenario.get("demo_talking_point"),
    }



# ─── Tax Opportunities ───────────────────────────────────────────────────────
@router.get("/api/tax/opportunities/{run_id}")
async def get_tax_opportunities(run_id: str):
    """Get tax optimisation findings for a run."""
    r = get_report(run_id, "tax_optimiser")
    if not r:
        raise HTTPException(status_code=404, detail="Tax report not found")
    return r["content"]


# ─── Multi-Entity Status ─────────────────────────────────────────────────────
@router.get("/api/entities/status")
async def entities_status():
    """Get multi-entity close status from all runs."""
    runs = list_runs(limit=20)
    return {"entities": [], "runs": runs[:5]}


# ─── Predictive Timeline ─────────────────────────────────────────────────────
@router.get("/api/prediction/{run_id}")
async def get_prediction(run_id: str):
    """Get current predictive timeline for a run."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "status": run.get("status"), "prediction": {}}


# ─── Telegram Test ──────────────────────────────────────────────────────────
@router.post("/api/telegram/test")
async def telegram_test():
    """Send a test connectivity message to the configured CFO chat."""
    success = await send_test_message()
    return {"success": success, "message": "Test message sent" if success else "Telegram not configured"}


# ─── Datasets ───────────────────────────────────────────────────────────────
@router.get("/api/datasets")
async def list_datasets():
    """List all demo dataset files with metadata."""
    import csv
    from io import StringIO

    demo_path = Path("./data/demo")
    if not demo_path.exists():
        return {"datasets": []}

    datasets = []
    for fp in sorted(demo_path.iterdir()):
        if fp.name.startswith("."):
            continue
        meta = {
            "name": fp.name,
            "type": fp.suffix.lstrip("."),
            "size_bytes": fp.stat().st_size,
        }
        # For CSV files, count rows and extract column names
        if fp.suffix.lower() == ".csv":
            try:
                text = fp.read_text(encoding="utf-8")
                reader = csv.reader(StringIO(text))
                headers = next(reader, [])
                row_count = sum(1 for _ in reader)
                meta["rows"] = row_count
                meta["columns"] = headers
            except Exception:
                pass
        datasets.append(meta)

    return {"datasets": datasets}


@router.get("/api/datasets/{name}")
async def get_dataset_content(name: str):
    """Return parsed CSV content as JSON rows (max 500)."""
    import csv
    from io import StringIO

    demo_path = Path("./data/demo") / name
    if not demo_path.exists() or not demo_path.is_file():
        raise HTTPException(status_code=404, detail="Dataset not found")

    if demo_path.suffix.lower() == ".csv":
        text = demo_path.read_text(encoding="utf-8")
        reader = csv.DictReader(StringIO(text))
        rows = []
        columns = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= 500:
                break
            rows.append(dict(row))
        return {
            "name": name,
            "rows": rows,
            "columns": list(columns),
            "total_rows": len(rows),
        }
    elif demo_path.suffix.lower() == ".json":
        content = json.loads(demo_path.read_text(encoding="utf-8"))
        if isinstance(content, list):
            columns = list(content[0].keys()) if content else []
            return {
                "name": name,
                "rows": content[:500],
                "columns": columns,
                "total_rows": len(content),
            }
        else:
            # Single object — wrap in array
            columns = list(content.keys())
            return {
                "name": name,
                "rows": [content],
                "columns": columns,
                "total_rows": 1,
            }
    else:
        raise HTTPException(status_code=400, detail="Only CSV and JSON datasets are viewable")


# ─── WebSocket ──────────────────────────────────────────────────────────────
@router.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """Live agent activity WebSocket for a specific run."""
    await manager.connect(run_id, websocket)
    try:
        # Send current run status on connect
        run = get_run(run_id)
        if run:
            await websocket.send_text(json.dumps({
                "event": "CONNECTED",
                "run_status": run.get("status", "UNKNOWN"),
                "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat(),
            }))
        while True:
            await asyncio.sleep(30)  # Keep-alive ping
            await websocket.send_text(json.dumps({"event": "PING", "run_id": run_id}))
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)
    except Exception as e:
        logger.warning(f"[WS] Error in run {run_id}: {e}")
        manager.disconnect(run_id, websocket)
