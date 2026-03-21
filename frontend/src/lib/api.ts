// Centralised API URL using .env.local
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const WS_BASE  = process.env.NEXT_PUBLIC_WS_URL  ?? "ws://localhost:8000/ws";

export { API_BASE, WS_BASE };

// ─── API helpers ─────────────────────────────────────────────────────────────

export async function startDemo(): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/demo/load`);
  if (!res.ok) throw new Error("Demo load failed");
  return res.json();
}

export async function getRun(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

export async function getAllRuns(): Promise<any> {
  const res = await fetch(`${API_BASE}/runs`);
  return res.json();
}

export async function getReport(runId: string, type: string): Promise<any> {
  const res = await fetch(`${API_BASE}/runs/${runId}/report/${type}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getAuditPackage(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/runs/${runId}/audit-package`);
  return res.json();
}

export async function postAuditQuery(question: string, runId?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/audit/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, run_id: runId }),
  });
  return res.json();
}

export async function getRegulatoryUpdates(): Promise<any> {
  const res = await fetch(`${API_BASE}/regulatory/updates`);
  return res.json();
}

export async function triggerRegulatoryCheck(): Promise<any> {
  const res = await fetch(`${API_BASE}/regulatory/check`);
  return res.json();
}

export async function getTaxOpportunities(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/tax/opportunities/${runId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function postRLHFSignal(
  runId: string,
  guardrailFireId: number,
  reason: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/rlhf/signal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, guardrail_fire_id: guardrailFireId, override_reason: reason }),
  });
  return res.json();
}

export async function testTelegram(): Promise<any> {
  const res = await fetch(`${API_BASE}/telegram/test`, { method: "POST" });
  return res.json();
}

// ─── Phase 2: Escalation + Cost + Surprise APIs ────────────────────────────

export async function getEscalations(runId: string, unresolvedOnly = true): Promise<any> {
  const url = unresolvedOnly
    ? `${API_BASE}/escalations/${runId}?resolved=false`
    : `${API_BASE}/escalations/${runId}`;
  const res = await fetch(url);
  return res.json();
}

export async function resolveEscalation(
  escalationId: number,
  resolvedBy = "CFO",
  notes = ""
): Promise<any> {
  const res = await fetch(`${API_BASE}/escalations/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ escalation_id: escalationId, resolved_by: resolvedBy, resolution_notes: notes }),
  });
  return res.json();
}

export async function getCostEfficiency(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/cost-efficiency/${runId}`);
  return res.json();
}

export async function triggerSurprise(scenarioType: string): Promise<any> {
  const res = await fetch(`${API_BASE}/surprise/${scenarioType}`, { method: "POST" });
  return res.json();
}

