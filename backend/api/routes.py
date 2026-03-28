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

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.database import audit_logger
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
from backend.api.auth import (
    create_access_token, verify_password, get_password_hash,
    get_user, get_user_by_email, get_current_user, Token, User, check_manager_role
)
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
    corrected_by: Optional[str] = "CFO"


# ─── Authentication Routes ──────────────────────────────────────────────────
@router.post("/api/auth/register", response_model=User)
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("EMPLOYEE"),
):
    if get_user(username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = get_password_hash(password)
    now = datetime.utcnow().isoformat()
    
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (username, email, hashed_pwd, role, now)
        )
        row = cursor.fetchone()
        user_id = row['id'] if row else 0
        conn.commit()
        return User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            created_at=now
        )
    finally:
        conn.close()


@router.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"[AUTH] Login attempt for user: {form_data.username}")
    user_dict = get_user(form_data.username)
    if not user_dict:
        logger.warning(f"[AUTH] User not found: {form_data.username}")
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    if not verify_password(form_data.password, user_dict["password_hash"]):
        logger.warning(f"[AUTH] Password mismatch for user: {form_data.username}")
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    logger.info(f"[AUTH] Login successful: {form_data.username}")
    access_token = create_access_token(data={"sub": user_dict["username"]})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/api/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/api/manager/team-runs")
async def get_team_runs(current_user: User = Depends(check_manager_role)):
    """Allow managers to see runs from their team."""
    return audit_logger.list_team_runs(current_user.id)


@router.get("/api/manager/team-datasets")
async def get_team_datasets(current_user: User = Depends(check_manager_role)):
    """Allow managers to see datasets used by their team."""
    runs = audit_logger.list_team_runs(current_user.id)
    datasets = []
    seen = set()
    for r in runs:
        files = json.loads(r.get("source_files", "[]"))
        for f in files:
            if f not in seen:
                datasets.append({
                    "name": f,
                    "employee": r.get("employee_name"),
                    "run_id": r.get("run_id"),
                    "timestamp": r.get("created_at")
                })
                seen.add(f)
    return datasets


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
    current_user: User = Depends(get_current_user),
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
        user_id=current_user.id,
        tester_name=current_user.username,
        tester_role=current_user.role
    )

    return {"run_id": run_id, "status": "STARTED", "period": period}


@router.post("/api/upload/multi")
async def upload_multi_entity(
    background_tasks: BackgroundTasks,
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Accept multi-entity data and start group close pipeline."""
    run_id = str(uuid.uuid4())
    entities = payload.get("entities", [])
    period = payload.get("period", "Q3 FY26")
    lc, ag = get_letta()
    ws_cb = manager.make_callback(run_id)
    
    # Init run in DB
    audit_logger.create_run(run_id, user_id=current_user.id, period=period)

    background_tasks.add_task(
        run_pipeline,
        raw_data={},
        run_id=run_id,
        period=period,
        ws_callback=ws_cb,
        entities=entities,
        letta_client_=lc,
        agent_id=ag,
        user_id=current_user.id,
        tester_name=current_user.username,
        tester_role=current_user.role
    )
    return {"run_id": run_id, "status": "STARTED", "entities": len(entities)}


# ─── Demo Mode ──────────────────────────────────────────────────────────────
@router.get("/api/demo/load")
async def load_demo(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
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
    
    # Init run in DB (Fixes 'Run not found' 404)
    audit_logger.create_run(run_id, user_id=current_user.id, period="Q3 FY26")

    ws_cb = manager.make_callback(run_id)

    background_tasks.add_task(
        run_pipeline,
        raw_data=raw_data,
        run_id=run_id,
        period="Q3 FY26",
        ws_callback=ws_cb,
        letta_client_=lc,
        agent_id=ag,
        user_id=current_user.id,
        tester_name=current_user.username,
        tester_role=current_user.role
    )

    return {"run_id": run_id, "status": "STARTED", "demo": True, "period": "Q3 FY26"}


# ─── Run Results ─────────────────────────────────────────────────────────────
@router.get("/api/runs")
async def get_runs(current_user: User = Depends(get_current_user)):
    """List pipeline runs based on role."""
    # "My History" should always be personal, even for Managers.
    # Managers have a separate "Team Oversight" tab.
    return {"runs": list_runs(user_id=current_user.id, is_manager=False)}


@router.get("/api/runs/{run_id}")
async def get_run_result(run_id: str, current_user: User = Depends(get_current_user)):
    """Full results for a run, protected by user scoping."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    # Permission Check
    if current_user.role != "MANAGER" and run.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this run history")

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
            "SELECT * FROM anomalies WHERE run_id = %s", (run_id,)
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
async def get_audit_package(run_id: str, current_user: User = Depends(get_current_user)):
    """Build and return complete audit package."""
    run = get_run(run_id)
    if not run or (current_user.role != "MANAGER" and run.get("user_id") != current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    try:
        package = await build_audit_package(run_id)
        return package
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/runs/{run_id}/audit-package/pdf")
async def download_audit_package_pdf(run_id: str, current_user: User = Depends(get_current_user)):
    """Generate and return audit package as PDF."""
    from fastapi.responses import FileResponse
    from backend.utils.pdf_generator import generate_audit_report_pdf
    
    run = get_run(run_id)
    if not run or (current_user.role != "MANAGER" and run.get("user_id") != current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    try:
        package = await build_audit_package(run_id)
        pdf_path = f"/tmp/audit_report_{run_id}.pdf"
        generate_audit_report_pdf(package, pdf_path)
        return FileResponse(
            path=pdf_path, 
            filename=f"FinClosePilot_Audit_{run_id[:8]}.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Audit Query ─────────────────────────────────────────────────────────────
@router.post("/api/audit/query")
async def audit_query(req: AuditQueryRequest, current_user: User = Depends(get_current_user)):
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
            if any(k in (str(e.get("action", "")) + str(e.get("agent", "")) + str(e.get("details", ""))).lower()
                   for k in keyword.split())
        ]
        results = relevant[:15] + results

    # Synthesize an answer if we have results
    answer = "No relevant audit records found to answer this specific question."
    if results:
        context = "\n".join([
            f"- [{r.get('agent', 'system')}] {r.get('action') or r.get('event')}: {str(r.get('details') or '')}"
            for r in results[:10]
        ])
        
        system_prompt = (
            "You are a senior auditor for FinClosePilot. Your task is to answer the user's question "
            "based onto the provided audit trail logs. Be specific and citation-heavy. "
            "If the answer involves transaction amounts, vendors, or specific agents, mention them. "
            "If the logs don't contain enough info to answer fully, state what is present and what is missing."
        )
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
async def rlhf_signal(req: RLHFSignalRequest, current_user: User = Depends(get_current_user)):
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
async def trigger_regulatory_check(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """Trigger on-demand regulatory rules check."""
    lc, ag = get_letta()
    background_tasks.add_task(run_regulatory_monitor, lc, ag)
    return {"status": "TRIGGERED", "message": "Regulatory check running in background"}


@router.get("/api/regulatory/updates")
async def get_regulatory_updates(current_user: User = Depends(get_current_user)):
    """List all known regulatory updates from database. Seeds mock data if empty."""
    changes = get_regulatory_changes(limit=50)
    
    if not changes:
        # Seed some helpful demo changes for the USER
        from backend.agents.additions.regulatory_monitor import save_regulatory_change
        mock_changes = [
            {
                "framework": "GST",
                "notification_no": "Notif 01/2024-Central Tax",
                "summary": "Mandatory e-invoice for small businesses.",
                "what_changed": "Threshold for e-invoicing reduced to Rs 5 Crore.",
                "effective_date": "2024-04-01",
                "affected_areas": ["Compliance", "IT Systems"],
                "action_required": "Ensure ERP is updated to generate e-invoices.",
                "urgency": "HIGH",
                "source_url": "https://cbic.gov.in"
            },
            {
                "framework": "IncomeTax",
                "notification_no": "Section 43B(h)",
                "summary": "New rule for MSME payments.",
                "what_changed": "Payments to MSMEs must be made within 45 days to claim deduction.",
                "effective_date": "2024-04-01",
                "affected_areas": ["Accounts Payable", "Tax Deduction"],
                "action_required": "Audit vendor list for MSME status.",
                "urgency": "HIGH",
                "source_url": "https://incometaxindia.gov.in"
            }
        ]
        for c in mock_changes:
            save_regulatory_change(c)
        changes = get_regulatory_changes(limit=50)

    return {"changes": changes, "count": len(changes)}


# ─── PHASE 2: Escalations ───────────────────────────────────────────────────
class EscalationResolveRequest(BaseModel):
    escalation_id: int
    resolved_by: str = "CFO"
    resolution_notes: str = ""


@router.get("/api/escalations/{run_id}")
async def get_escalations_api(run_id: str, resolved: Optional[bool] = None, current_user: User = Depends(get_current_user)):
    """Get all escalations for a run, optionally filtered by resolved status."""
    from backend.database.audit_logger import get_escalations, get_unresolved_escalations
    if resolved is False:
        escs = get_unresolved_escalations(run_id)
    else:
        escs = get_escalations(run_id)
    return {"run_id": run_id, "escalations": escs, "count": len(escs)}


@router.post("/api/escalations/resolve")
async def resolve_escalation_api(req: EscalationResolveRequest, current_user: User = Depends(get_current_user)):
    """Resolve an escalation (CFO/human decision)."""
    from backend.database.audit_logger import resolve_escalation
    success = resolve_escalation(req.escalation_id, req.resolved_by, req.resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return {"success": True, "escalation_id": req.escalation_id, "resolved_by": req.resolved_by}


# ─── PHASE 2: Cost Efficiency ───────────────────────────────────────────────
@router.get("/api/cost-efficiency/{run_id}")
async def get_cost_efficiency(run_id: str, current_user: User = Depends(get_current_user)):
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
async def trigger_surprise(scenario_type: str, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
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
async def get_tax_opportunities(run_id: str, current_user: User = Depends(get_current_user)):
    """Get tax optimisation findings for a run."""
    r = get_report(run_id, "tax_optimiser")
    if not r:
        raise HTTPException(status_code=404, detail="Tax report not found")
    return r["content"]


# ─── Multi-Entity Status ─────────────────────────────────────────────────────
@router.get("/api/entities/status")
async def entities_status(current_user: User = Depends(get_current_user)):
    """Get multi-entity close status from all runs."""
    runs = list_runs(limit=20)
    return {"entities": [], "runs": runs[:5]}


# ─── Predictive Timeline ─────────────────────────────────────────────────────
@router.get("/api/prediction/{run_id}")
async def get_prediction(run_id: str, current_user: User = Depends(get_current_user)):
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
