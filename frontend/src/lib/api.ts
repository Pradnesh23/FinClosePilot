// Centralised API URL using .env.local
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const WS_BASE  = process.env.NEXT_PUBLIC_WS_URL  ?? "ws://localhost:8000/ws";

export { API_BASE, WS_BASE };

// ─── Auth Helpers ────────────────────────────────────────────────────────────

function getAuthHeader() {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const headers = {
    ...getAuthHeader(),
    ...options.headers,
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/";
    }
  }
  return res;
}

export async function login(payload: any): Promise<any> {
  const formData = new URLSearchParams();
  formData.append("username", payload.username);
  formData.append("password", payload.password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData,
  });
  if (!res.ok) throw new Error("Login failed");
  return res.json();
}

export async function register(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Registration failed");
  return res.json();
}

export async function getMe(): Promise<any> {
  const res = await apiFetch("/auth/me");
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

// ─── API helpers ─────────────────────────────────────────────────────────────

export async function startDemo(): Promise<{ run_id: string }> {
  const res = await apiFetch("/demo/load");
  if (!res.ok) throw new Error("Demo load failed");
  return res.json();
}

export async function getRun(runId: string): Promise<any> {
  const res = await apiFetch(`/runs/${runId}`);
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

export async function getAllRuns(): Promise<any> {
  const res = await apiFetch("/runs");
  return res.json();
}

export async function getReport(runId: string, type: string): Promise<any> {
  const res = await apiFetch(`/runs/${runId}/report/${type}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getAuditPackage(runId: string): Promise<any> {
  const res = await apiFetch(`/runs/${runId}/audit-package`);
  return res.json();
}

export async function postAuditQuery(question: string, runId?: string): Promise<any> {
  const res = await apiFetch("/audit/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, run_id: runId }),
  });
  return res.json();
}

export async function getRegulatoryUpdates(): Promise<any> {
  const res = await apiFetch("/regulatory/updates");
  return res.json();
}

export async function triggerRegulatoryCheck(): Promise<any> {
  const res = await apiFetch("/regulatory/check");
  return res.json();
}

export async function getTaxOpportunities(runId: string): Promise<any> {
  const res = await apiFetch(`/tax/opportunities/${runId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function postRLHFSignal(
  runId: string,
  guardrailFireId: number,
  reason: string
): Promise<any> {
  const res = await apiFetch("/rlhf/signal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, guardrail_fire_id: guardrailFireId, override_reason: reason }),
  });
  return res.json();
}

export async function testTelegram(): Promise<any> {
  const res = await apiFetch("/telegram/test", { method: "POST" });
  return res.json();
}

// ─── File Upload ────────────────────────────────────────────────────────────

export async function uploadFiles(files: {
  transactions?: File;
  bankStatement?: File;
  gstPortal?: File;
  form26as?: File;
  period?: string;
}): Promise<{ run_id: string }> {
  const formData = new FormData();
  if (files.transactions) formData.append("transactions", files.transactions);
  if (files.bankStatement) formData.append("bank_statement", files.bankStatement);
  if (files.gstPortal) formData.append("gst_portal", files.gstPortal);
  if (files.form26as) formData.append("form26as", files.form26as);
  formData.append("period", files.period ?? "Q3 FY26");

  const res = await apiFetch("/upload", { method: "POST", body: formData });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

// ─── Phase 2: Escalation + Cost + Surprise APIs ────────────────────────────

export async function getEscalations(runId: string, unresolvedOnly = true): Promise<any> {
  const url = unresolvedOnly
    ? `/escalations/${runId}?resolved=false`
    : `/escalations/${runId}`;
  const res = await apiFetch(url);
  return res.json();
}

export async function resolveEscalation(
  escalationId: number,
  resolvedBy = "CFO",
  notes = ""
): Promise<any> {
  const res = await apiFetch("/escalations/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ escalation_id: escalationId, resolved_by: resolvedBy, resolution_notes: notes }),
  });
  return res.json();
}

export async function getCostEfficiency(runId: string): Promise<any> {
  const res = await apiFetch(`/cost-efficiency/${runId}`);
  return res.json();
}

export async function triggerSurprise(scenarioType: string): Promise<any> {
  const res = await apiFetch(`/surprise/${scenarioType}`, { method: "POST" });
  return res.json();
}

// ─── Datasets ───────────────────────────────────────────────────────────────

export async function getDatasets(): Promise<any> {
  const res = await apiFetch("/datasets");
  return res.json();
}

export async function getDatasetContent(name: string): Promise<any> {
  const res = await apiFetch(`/datasets/${encodeURIComponent(name)}`);
  return res.json();
}

// ─── Team Oversight ─────────────────────────────────────────────────────────

export async function getTeamRuns(): Promise<any> {
    const res = await apiFetch("/manager/team-runs");
    return res.json();
}

export async function getTeamDatasets(): Promise<any> {
    const res = await apiFetch("/manager/team-datasets");
    return res.json();
}

