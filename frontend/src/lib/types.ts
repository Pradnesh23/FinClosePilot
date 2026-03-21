// Shared TypeScript types for FinClosePilot frontend

export type PipelineStatus = "IDLE" | "STARTED" | "RUNNING" | "COMPLETE" | "ERROR";

export type GuardrailLevel = "HARD_BLOCK" | "SOFT_FLAG" | "ADVISORY" | "AUTO_ACTION";

export type GuardrailFire = {
  id?: number;
  rule_id: string;
  rule_level: GuardrailLevel;
  regulation: string;
  section?: string;
  vendor_name?: string;
  vendor_gstin?: string;
  transaction_id?: string;
  amount_inr?: number;
  itc_blocked_inr?: number;
  violation_detail: string;
  action_taken: string;
  run_id?: string;
};

export type AnomalySeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type Anomaly = {
  anomaly_type?: string;
  category?: string;
  severity?: AnomalySeverity;
  vendor_name?: string;
  amount_inr?: number;
  financial_exposure_inr?: number;
  reasoning?: string;
  description?: string;
};

export type ReconBreak = {
  break_type?: string;
  amount_difference?: number;
  root_cause?: string;
  suggested_action?: string;
  vendor_name?: string;
};

export type ReconSection = {
  matched_count?: number;
  break_count?: number;
  breaks?: ReconBreak[];
  summary?: string;
};

export type TaxOpportunity = {
  category: string;
  opportunity: string;
  regulation: string;
  section: string;
  estimated_saving_inr: number;
  action_required: string;
  deadline?: string;
  confidence: number;
  priority: "HIGH" | "MEDIUM" | "LOW";
};

export type RunSummary = {
  run_id: string;
  status: string;
  period?: string;
  total_records?: number;
  matched_records?: number;
  breaks?: number;
  anomalies?: number;
  guardrail_fires?: number;
  hard_blocks?: number;
  total_blocked_inr?: number;
  time_taken_seconds?: number;
  created_at?: string;
};

export type WsEvent = {
  event: string;
  agent: string;
  status: "RUNNING" | "DONE" | "ERROR";
  data: Record<string, any>;
  timestamp: string;
  run_id: string;
};

export type RegulatoryChange = {
  id?: number;
  framework: string;
  notification_no?: string;
  summary?: string;
  what_changed?: string;
  effective_date?: string;
  urgency?: "HIGH" | "MEDIUM" | "LOW";
  source_url?: string;
  action_required?: string;
};

export type PredictionResult = {
  predicted_completion_minutes: number;
  predicted_completion_time: string;
  confidence: number;
  current_bottleneck: string;
  bottleneck_reason: string;
  steps_complete: number;
  steps_remaining: number;
  risk_factors: string[];
  on_track: boolean;
};

export type Entity = {
  entity_id: string;
  entity_name: string;
  role: "parent" | "subsidiary";
  ownership_pct: number;
  status?: string;
  pct_complete?: number;
};
