"""
LangGraph pipeline — orchestrates all FinClosePilot agents.
"""

import json
import logging
import uuid
import asyncio
from datetime import datetime
from typing import TypedDict, Any, Callable, Awaitable, Optional

from backend.agents.ingestion.normaliser import normalise_data
from backend.agents.reconciliation.gst_recon import run_gst_reconciliation
from backend.agents.reconciliation.bank_recon import run_bank_reconciliation
from backend.agents.reconciliation.intercompany_recon import run_intercompany_reconciliation
from backend.agents.reconciliation.vendor_recon import run_vendor_reconciliation
from backend.agents.anomaly.benford_analyser import analyse_benford
from backend.agents.anomaly.duplicate_detector import detect_duplicates
from backend.agents.anomaly.pattern_detector import detect_patterns
from backend.agents.guardrails.gst_guardrails import check_gst_guardrails
from backend.agents.guardrails.indas_guardrails import check_indas_guardrails
from backend.agents.guardrails.sebi_guardrails import check_sebi_guardrails
from backend.agents.guardrails.rbi_guardrails import check_rbi_guardrails
from backend.agents.reports.gstr3b_generator import generate_gstr3b
from backend.agents.reports.variance_report import generate_variance_report
from backend.agents.reports.audit_committee import generate_audit_committee_report
from backend.agents.reports.tax_optimiser import find_tax_opportunities
from backend.agents.reports.audit_packager import build_audit_package
from backend.agents.additions.form26as_recon import parse_form26as_pdf, reconcile_form26as
from backend.agents.additions.multi_entity import run_consolidation
from backend.agents.additions.predictive_close import predict_close_timeline, store_close_duration
from backend.agents.additions.regulatory_monitor import run_regulatory_monitor
from backend.agents.learning.rlaif_critic import critique_output
from backend.notifications.telegram_bot import (
    send_guardrail_alert, send_anomaly_alert, send_pipeline_complete
)
from backend.memory import letta_client as letta_mod
from backend.database import audit_logger as db
from backend.database.models import init_db
from backend.agents.model_router import get_routing_stats

logger = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    run_id: str
    period: str
    raw_data: dict
    normalised_data: list
    recon_results: dict
    anomalies: dict
    critic_scores: dict
    guardrail_results: dict
    reports: dict
    tax_opportunities: dict
    form26as_results: dict
    consolidation_results: dict
    prediction: dict
    regulatory_updates: dict
    escalations: list         # Phase 2: confidence escalations
    audit_log: list
    ws_callback: Any
    letta_client: Any
    agent_id: str
    entities: list
    telegram_sent: bool
    retry_count: int
    start_time: float
    form26as_path: str | None
    error: str | None


async def _ws(state: PipelineState, event: str, agent: str, data: dict = None, status: str = "RUNNING"):
    """Helper to broadcast WebSocket message."""
    cb = state.get("ws_callback")
    if cb:
        try:
            await cb(event, agent, data or {}, status)
        except Exception:
            pass


async def node_ingest(state: PipelineState) -> PipelineState:
    """INGESTING — normalise raw data."""
    run_id = state["run_id"]
    t0 = asyncio.get_event_loop().time()
    await _ws(state, "INGESTING", "Data Ingestion Agent", {"message": "Normalising uploaded data..."})
    db.log_event(run_id, "Normaliser", "START", {"source_count": len(state.get("raw_data", {}))})

    raw = state.get("raw_data", {})
    results = []
    for source_type, text in raw.items():
        result = await normalise_data(str(text), source_type)
        results.extend(result.get("records", []))
        db.log_event(run_id, "Normaliser", "NORMALISED",
                     {"source": source_type, "records": len(result.get("records", []))})

    state["normalised_data"] = results
    db.update_run(run_id, total_records=len(results), status="RECONCILING")

    # Save normalised transactions to DB
    for t in results:
        db.save_transaction(run_id, t)

    elapsed = asyncio.get_event_loop().time() - t0
    await store_close_duration(run_id, "INGESTING", int(elapsed), state["letta_client"], state["agent_id"])
    await _ws(state, "INGESTING", "Data Ingestion Agent",
              {"records": len(results), "message": f"Normalised {len(results)} records"},
              status="DONE")

    # Update prediction
    prediction = await predict_close_timeline(
        {"current_step": "RECONCILING", "elapsed_seconds": elapsed, "hard_blocks": 0},
        state["letta_client"], state["agent_id"],
    )
    state["prediction"] = prediction
    return state


async def node_reconcile(state: PipelineState) -> PipelineState:
    """RECONCILING — run all reconciliation agents in parallel where possible."""
    run_id = state["run_id"]
    t0 = asyncio.get_event_loop().time()
    txns = state.get("normalised_data", [])

    await _ws(state, "RECONCILING", "Reconciliation Agents",
              {"message": "Running GST + Bank + Intercompany + Vendor reconciliation..."})

    # Separate transaction sources
    gst_txns = [t for t in txns if t.get("source") in ("GST_PORTAL", "ERP")]
    bank_txns = [t for t in txns if t.get("source") == "BANK"]

    # Run GST, Bank, Intercompany, Vendor recon in parallel
    gst_task = run_gst_reconciliation(gst_txns, [], gst_txns, txns, state["letta_client"], state["agent_id"], run_id)
    bank_task = run_bank_reconciliation(bank_txns, txns, state["letta_client"], state["agent_id"])
    ic_task = run_intercompany_reconciliation([], state["letta_client"], state["agent_id"])
    vendor_task = run_vendor_reconciliation(txns, [], state["letta_client"], state["agent_id"])

    gst_r, bank_r, ic_r, vendor_r = await asyncio.gather(gst_task, bank_task, ic_task, vendor_task)

    total_breaks = (
        len(gst_r.get("breaks", []))
        + len(bank_r.get("breaks", []))
        + len(ic_r.get("ic_pairs", [{}]))
        + len(vendor_r.get("breaks", []))
    )
    matched = gst_r.get("matched_count", 0) + bank_r.get("matched_count", 0)

    state["recon_results"] = {
        "gst": gst_r,
        "bank": bank_r,
        "intercompany": ic_r,
        "vendor": vendor_r,
    }

    # Collect escalations from GST recon
    recon_escs = gst_r.get("escalations", [])
    if recon_escs:
        state.setdefault("escalations", []).extend(recon_escs)
        await _ws(state, "ESCALATION_REVIEW", "Escalation Engine",
                  {"message": f"{len(recon_escs)} recon items escalated", "count": len(recon_escs)})

    db.update_run(run_id, matched_records=matched, breaks=total_breaks, status="DETECTING_ANOMALIES")

    # Save recon breaks to DB
    for brk in gst_r.get("breaks", []):
        brk["recon_type"] = "GST"
        db.save_recon_break(run_id, brk)
    for brk in bank_r.get("breaks", []):
        brk["recon_type"] = "BANK"
        db.save_recon_break(run_id, brk)
    for brk in vendor_r.get("breaks", []):
        brk["recon_type"] = "VENDOR"
        db.save_recon_break(run_id, brk)

    # Store structured recon summary for frontend
    await letta_mod.store_to_archival(state["letta_client"], state["agent_id"], state["recon_results"], label=f"recon_{run_id}")

    elapsed = asyncio.get_event_loop().time() - t0
    await store_close_duration(run_id, "RECONCILING", int(elapsed), state["letta_client"], state["agent_id"])
    await _ws(state, "RECONCILING", "Reconciliation Agents",
              {"matched": matched, "breaks": total_breaks, "message": f"{matched} matched | {total_breaks} breaks"},
              status="DONE")
    return state


async def node_detect_anomalies(state: PipelineState) -> PipelineState:
    """DETECTING_ANOMALIES — Benford + Duplicates + Patterns."""
    run_id = state["run_id"]
    t0 = asyncio.get_event_loop().time()
    txns = state.get("normalised_data", [])

    await _ws(state, "DETECTING_ANOMALIES", "Anomaly Detection Agents",
              {"message": "Running Benford Law + Duplicate + Pattern analysis..."})

    benford, duplicates, patterns = await asyncio.gather(
        analyse_benford(txns, state["letta_client"], state["agent_id"], run_id),
        detect_duplicates(txns, state["letta_client"], state["agent_id"]),
        detect_patterns(txns, state["letta_client"], state["agent_id"]),
    )

    state["anomalies"] = {"benford": benford, "duplicates": duplicates, "patterns": patterns}

    all_anomalies = (
        benford.get("violations", [])
        + duplicates.get("duplicates", [])
        + patterns.get("anomalies", [])
    )
    total_anomalies = len(all_anomalies)

    # Collect escalations from benford
    benford_escs = benford.get("escalations", [])
    if benford_escs:
        state.setdefault("escalations", []).extend(benford_escs)
        await _ws(state, "ESCALATION_REVIEW", "Escalation Engine",
                  {"message": f"{len(benford_escs)} anomaly items escalated", "count": len(benford_escs)})

    db.update_run(run_id, anomalies=total_anomalies, status="CRITIC_CHECK")

    # Save anomalies to DB
    for a in all_anomalies:
        db.save_anomaly(run_id, a)

    # Store structured anomaly summary for frontend heatmap/charts
    await letta_mod.store_to_archival(state["letta_client"], state["agent_id"], state["anomalies"], label=f"anomalies_{run_id}")

    elapsed = asyncio.get_event_loop().time() - t0
    await store_close_duration(run_id, "DETECTING_ANOMALIES", int(elapsed), state["letta_client"], state["agent_id"])
    await _ws(state, "DETECTING_ANOMALIES", "Anomaly Detection Agents",
              {"anomalies": total_anomalies, "message": f"Found {total_anomalies} anomalies"},
              status="DONE")
    return state


async def node_critic(state: PipelineState) -> PipelineState:
    """CRITIC_CHECK — RLAIF quality gate."""
    run_id = state["run_id"]
    await _ws(state, "CRITIC_CHECK", "RLAIF Critic Agent",
              {"message": "Scoring output quality..."})

    combined_output = {
        "recon_results": state.get("recon_results", {}),
        "anomalies": state.get("anomalies", {}),
    }
    critic_result = await critique_output(combined_output, "reconciliation+anomaly")
    state["critic_scores"] = critic_result

    decision = critic_result.get("decision", "PROCEED")
    retry_count = state.get("retry_count", 0)

    await _ws(state, "CRITIC_CHECK", "RLAIF Critic Agent",
              {"decision": decision, "score": critic_result.get("overall_score")},
              status="DONE")

    db.log_event(run_id, "RLAIF_Critic", "SCORED", {
        "decision": decision,
        "overall_score": critic_result.get("overall_score"),
        "retry_count": retry_count,
    })

    if decision == "RETRY" and retry_count < 2:
        state["retry_count"] = retry_count + 1
        db.log_event(run_id, "RLAIF_Critic", "RETRY", {"attempt": retry_count + 1})
        # Re-run — skip via flag (LangGraph conditional handles this)
    return state


async def node_guardrails(state: PipelineState) -> PipelineState:
    """ENFORCING_GUARDRAILS — GST + IndAS + SEBI + RBI."""
    run_id = state["run_id"]
    t0 = asyncio.get_event_loop().time()
    txns = state.get("normalised_data", [])
    context = {"quarter_end_date": "2025-12-31", "period": state.get("period", "Q3 FY26")}

    await _ws(state, "ENFORCING_GUARDRAILS", "Guardrail Engine",
              {"message": "Enforcing CGST Act, SEBI LODR, IndAS, RBI rules..."})

    gst_g, indas_g, sebi_g, rbi_g = await asyncio.gather(
        check_gst_guardrails(txns, state.get("recon_results", {}), state["letta_client"], state["agent_id"], run_id),
        check_indas_guardrails(txns, context, state["letta_client"], state["agent_id"], run_id),
        check_sebi_guardrails(txns, context, state["letta_client"], state["agent_id"], run_id),
        check_rbi_guardrails(txns, context, state["letta_client"], state["agent_id"], run_id),
    )

    total_hard = (
        gst_g.get("hard_blocks", 0) + indas_g.get("hard_blocks", 0)
        + sebi_g.get("hard_blocks", 0) + rbi_g.get("hard_blocks", 0)
    )
    all_fires = (
        gst_g.get("fires", []) + indas_g.get("fires", [])
        + sebi_g.get("fires", []) + rbi_g.get("fires", [])
    )
    total_blocked = gst_g.get("total_blocked_inr", 0)

    state["guardrail_results"] = {
        "gst": gst_g, "indas": indas_g, "sebi": sebi_g, "rbi": rbi_g,
        "total_fires": len(all_fires),
        "total_hard_blocks": total_hard,
        "total_blocked_inr": total_blocked,
        "all_fires": all_fires,
    }

    # Collect escalations from guardrails
    for grd in [gst_g, indas_g, sebi_g, rbi_g]:
        grd_escs = grd.get("escalations", [])
        if grd_escs:
            state.setdefault("escalations", []).extend(grd_escs)
            await _ws(state, "ESCALATION_REVIEW", "Escalation Engine",
                      {"message": f"{len(grd_escs)} guardrail items escalated", "count": len(grd_escs)})

    db.update_run(
        run_id,
        guardrail_fires=len(all_fires),
        hard_blocks=total_hard,
        total_blocked_inr=total_blocked,
        status="GENERATING_REPORTS",
    )

    # Send Telegram alerts for hard blocks and critical anomalies
    telegram_sent = False
    for fire in all_fires:
        if fire.get("rule_level") == "HARD_BLOCK":
            await send_guardrail_alert(
                rule_id=fire.get("rule_id"),
                regulation=fire.get("regulation", ""),
                section=fire.get("section", ""),
                vendor_name=fire.get("vendor_name", "Unknown"),
                amount_inr=fire.get("amount_inr", 0),
                violation_detail=fire.get("violation_detail", ""),
                action_taken=fire.get("action_taken", "Blocked"),
                run_id=run_id,
                rule_level="HARD_BLOCK",
            )
            telegram_sent = True

    # Telegram for CRITICAL anomalies
    for anomaly in state.get("anomalies", {}).get("benford", {}).get("violations", []):
        if anomaly.get("severity") == "CRITICAL":
            await send_anomaly_alert(
                category="BENFORD_VIOLATION",
                severity="CRITICAL",
                vendor_name=anomaly.get("vendor_name", "Unknown"),
                financial_exposure_inr=anomaly.get("financial_exposure_inr", 0),
                reasoning=anomaly.get("reasoning", ""),
                run_id=run_id,
            )
            telegram_sent = True

    state["telegram_sent"] = telegram_sent

    elapsed = asyncio.get_event_loop().time() - t0
    await store_close_duration(run_id, "ENFORCING_GUARDRAILS", int(elapsed), state["letta_client"], state["agent_id"])
    await _ws(state, "ENFORCING_GUARDRAILS", "Guardrail Engine",
              {"fires": len(all_fires), "hard_blocks": total_hard, "blocked_inr": total_blocked},
              status="DONE")
    return state


async def node_generate_reports(state: PipelineState) -> PipelineState:
    """GENERATING_REPORTS — GSTR-3B + Variance + Audit Committee + Tax Optimiser."""
    run_id = state["run_id"]
    t0 = asyncio.get_event_loop().time()
    txns = state.get("normalised_data", [])

    await _ws(state, "GENERATING_REPORTS", "Report Generation Agents",
              {"message": "Generating GSTR-3B, Variance, Audit Committee, Tax reports..."})

    actuals = {"Travel": 1847000, "Technology": 850000, "Operations": 420000}
    budget = {"Travel": 420000, "Technology": 800000, "Operations": 450000}
    prior = {"Travel": 380000, "Technology": 750000, "Operations": 410000}
    context = {"period": state.get("period", "Q3 FY26")}

    gstr3b_task = generate_gstr3b(state.get("recon_results", {}), state.get("guardrail_results", {}),
                                   txns, state["letta_client"], state["agent_id"])
    variance_task = generate_variance_report(actuals, budget, prior, context,
                                              state["letta_client"], state["agent_id"])
    tax_task = find_tax_opportunities(txns, [], context, state["letta_client"], state["agent_id"])
    audit_task = generate_audit_committee_report(state, state["letta_client"], state["agent_id"])

    gstr3b, variance, tax, audit = await asyncio.gather(gstr3b_task, variance_task, tax_task, audit_task)

    state["reports"] = {"gstr3b": gstr3b, "variance": variance, "audit_committee": audit}
    state["tax_opportunities"] = tax

    # Save reports to DB
    db.save_report(run_id, "gstr3b", gstr3b, state.get("critic_scores", {}).get("overall_score"))
    db.save_report(run_id, "variance", variance)
    db.save_report(run_id, "audit_committee", audit)
    db.save_report(run_id, "tax_optimiser", tax)

    elapsed = asyncio.get_event_loop().time() - t0
    await store_close_duration(run_id, "GENERATING_REPORTS", int(elapsed), state["letta_client"], state["agent_id"])
    await _ws(state, "GENERATING_REPORTS", "Report Generation Agents",
              {"reports_generated": 4, "tax_saving": tax.get("total_potential_saving_inr", 0)},
              status="DONE")
    return state


async def node_form26as(state: PipelineState) -> PipelineState:
    """FORM26AS_RECON — if Form 26AS PDF was provided."""
    run_id = state["run_id"]
    pdf_path = state.get("form26as_path")

    if not pdf_path:
        await _ws(state, "FORM26AS_RECON", "Form 26AS Agent",
                  {"message": "No Form 26AS file provided — skipping."},
                  status="DONE")
        state["form26as_results"] = {}
        return state

    await _ws(state, "FORM26AS_RECON", "Form 26AS Agent",
              {"message": "Parsing and reconciling Form 26AS..."})

    form26as_data = await parse_form26as_pdf(pdf_path)
    result = await reconcile_form26as(form26as_data, [], state["letta_client"], state["agent_id"])
    state["form26as_results"] = result

    await _ws(state, "FORM26AS_RECON", "Form 26AS Agent",
              {"mismatches": result.get("summary", {}).get("total_mismatches", 0)},
              status="DONE")
    return state


async def node_consolidation(state: PipelineState) -> PipelineState:
    """CONSOLIDATION — multi-entity consolidation if multiple entities."""
    run_id = state["run_id"]
    entities = state.get("entities", [])

    if not entities or len(entities) <= 1:
        state["consolidation_results"] = {}
        await _ws(state, "CONSOLIDATION", "Multi-Entity Agent",
                  {"message": "Single entity — skipping consolidation."},
                  status="DONE")
        return state

    await _ws(state, "CONSOLIDATION", "Multi-Entity Agent",
              {"message": f"Consolidating {len(entities)} entities with IndAS 110..."})

    result = await run_consolidation(entities, state["letta_client"], state["agent_id"])
    state["consolidation_results"] = result

    await _ws(state, "CONSOLIDATION", "Multi-Entity Agent",
              {"entities": len(entities), "eliminations": len(result.get("elimination_entries", []))},
              status="DONE")
    return state


async def node_regulatory_check(state: PipelineState) -> PipelineState:
    """REGULATORY_CHECK — check for rule updates."""
    run_id = state["run_id"]
    await _ws(state, "REGULATORY_CHECK", "Regulatory Monitor",
              {"message": "Checking CBIC and SEBI for new notifications..."})

    result = await run_regulatory_monitor(state["letta_client"], state["agent_id"])
    state["regulatory_updates"] = result

    await _ws(state, "REGULATORY_CHECK", "Regulatory Monitor",
              {"changes_found": result.get("changes_found", 0)},
              status="DONE")
    return state


async def node_complete(state: PipelineState) -> PipelineState:
    """COMPLETE — finalize run and send completion Telegram."""
    run_id = state["run_id"]
    t_start = state.get("start_time", 0)
    elapsed = asyncio.get_event_loop().time() - t_start if t_start else 0

    guardrail_results = state.get("guardrail_results", {})
    all_anomalies = (
        len(state.get("anomalies", {}).get("benford", {}).get("violations", []))
        + len(state.get("anomalies", {}).get("duplicates", {}).get("duplicates", []))
        + len(state.get("anomalies", {}).get("patterns", {}).get("anomalies", []))
    )

    # Determine final status based on escalations
    escalations = state.get("escalations", [])
    final_status = "COMPLETE_WITH_ESCALATIONS" if escalations else "COMPLETE"

    db.update_run(
        run_id,
        status=final_status,
        time_taken_seconds=elapsed,
    )

    await send_pipeline_complete(
        run_id=run_id,
        matched=state.get("recon_results", {}).get("gst", {}).get("matched_count", 0),
        breaks=state.get("recon_results", {}).get("gst", {}).get("break_count", 0),
        anomalies=all_anomalies,
        guardrail_fires=guardrail_results.get("total_fires", 0),
        time_taken_seconds=elapsed,
        total_blocked_inr=guardrail_results.get("total_blocked_inr", 0),
        period=state.get("period", "Q3 FY26"),
    )

    await _ws(state, final_status, "Pipeline", {
        "elapsed_seconds": elapsed,
        "escalations": len(escalations),
    }, status="DONE")
    return state


async def run_pipeline(
    raw_data: dict,
    run_id: str = None,
    period: str = "Q3 FY26",
    ws_callback: Callable = None,
    entities: list = None,
    form26as_path: str = None,
    letta_client_=None,
    agent_id: str = "",
) -> dict:
    """
    Main pipeline entry point.
    Runs all nodes sequentially with parallel sub-steps where possible.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    init_db()
    db.create_run(run_id, period)
    db.log_event(run_id, "Pipeline", "START", {"period": period})

    if letta_client_ is None:
        from backend.memory.letta_client import init_letta_client, create_or_get_agent
        letta_client_ = init_letta_client()
        agent_id = await create_or_get_agent(letta_client_, "FinClosePilot")

    state: PipelineState = {
        "run_id": run_id,
        "period": period,
        "raw_data": raw_data,
        "normalised_data": [],
        "recon_results": {},
        "anomalies": {},
        "critic_scores": {},
        "guardrail_results": {},
        "reports": {},
        "tax_opportunities": {},
        "form26as_results": {},
        "consolidation_results": {},
        "prediction": {},
        "regulatory_updates": {},
        "escalations": [],
        "audit_log": [],
        "ws_callback": ws_callback,
        "letta_client": letta_client_,
        "agent_id": agent_id,
        "entities": entities or [],
        "telegram_sent": False,
        "retry_count": 0,
        "start_time": asyncio.get_event_loop().time(),
        "form26as_path": form26as_path,
        "error": None,
    }

    # Execute pipeline nodes in order
    nodes = [
        ("INGESTING", node_ingest),
        ("RECONCILING", node_reconcile),
        ("DETECTING_ANOMALIES", node_detect_anomalies),
        ("CRITIC_CHECK", node_critic),
        ("ENFORCING_GUARDRAILS", node_guardrails),
        ("GENERATING_REPORTS", node_generate_reports),
        ("FORM26AS_RECON", node_form26as),
        ("CONSOLIDATION", node_consolidation),
        ("REGULATORY_CHECK", node_regulatory_check),
        ("COMPLETE", node_complete),
    ]

    for step_name, node_fn in nodes:
        try:
            # Handle RETRY logic for critic check
            if step_name == "RECONCILING" and state.get("retry_count", 0) > 0:
                db.log_event(run_id, "Pipeline", "RETRY", {"step": step_name})

            state = await node_fn(state)

            # If critic says RETRY and we haven't exceeded limits, re-run recon
            if step_name == "CRITIC_CHECK":
                critic = state.get("critic_scores", {})
                if critic.get("decision") == "RETRY" and state.get("retry_count", 0) <= 2:
                    state = await node_reconcile(state)
                    state = await node_detect_anomalies(state)
                    state = await node_critic(state)

        except Exception as e:
            logger.error(f"[Pipeline] Step {step_name} failed: {e}", exc_info=True)
            db.log_event(run_id, "Pipeline", "ERROR", {"step": step_name, "error": str(e)}, status="ERROR")
            state["error"] = str(e)
            if ws_callback:
                await ws_callback(step_name, "Pipeline", {"error": str(e)}, "ERROR")

    # Build escalation summary
    escalations = state.get("escalations", [])
    esc_by_agent: dict[str, int] = {}
    esc_by_level: dict[str, int] = {}
    for esc in escalations:
        at = esc.get("agent_type", "unknown")
        lv = esc.get("escalation_level", "HUMAN_REVIEW")
        esc_by_agent[at] = esc_by_agent.get(at, 0) + 1
        esc_by_level[lv] = esc_by_level.get(lv, 0) + 1

    total_items_processed = len(state.get("normalised_data", [])) or 1
    escalation_summary = {
        "total_escalations": len(escalations),
        "by_agent": esc_by_agent,
        "by_level": esc_by_level,
        "auto_proceeded": total_items_processed - len(escalations),
        "escalated": len(escalations),
        "escalation_rate_pct": round(len(escalations) / max(total_items_processed, 1) * 100, 1),
    }

    has_escalations = len(escalations) > 0
    if state.get("error"):
        final_status = "ERROR"
    elif has_escalations:
        final_status = "COMPLETE_WITH_ESCALATIONS"
    else:
        final_status = "COMPLETE"

    # Return final state summary
    return {
        "run_id": run_id,
        "status": final_status,
        "period": period,
        "recon_results": state.get("recon_results", {}),
        "anomalies": state.get("anomalies", {}),
        "critic_scores": state.get("critic_scores", {}),
        "guardrail_results": state.get("guardrail_results", {}),
        "reports": {"keys": list(state.get("reports", {}).keys())},
        "tax_opportunities": state.get("tax_opportunities", {}),
        "form26as_results": state.get("form26as_results", {}),
        "consolidation_results": state.get("consolidation_results", {}),
        "prediction": state.get("prediction", {}),
        "regulatory_updates": state.get("regulatory_updates", {}),
        "escalation_summary": escalation_summary,
        "model_routing_stats": get_routing_stats(run_id),
        "telegram_sent": state.get("telegram_sent", False),
        "error": state.get("error"),
    }
