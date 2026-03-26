"use client";

import { useMemo } from "react";
import clsx from "clsx";
import {
  CheckCircle2, XCircle, Loader2, Circle,
  Database, GitCompare, Search, Brain, ShieldCheck,
  FileText, FileCheck, Building2, Globe, Flag,
} from "lucide-react";

// ─── Pipeline Steps ──────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { event: "INGESTING",            label: "Data Ingestion",      icon: Database,    agent: "Normaliser" },
  { event: "RECONCILING",          label: "Reconciliation",      icon: GitCompare,  agent: "GST + Bank + IC + Vendor" },
  { event: "DETECTING_ANOMALIES",  label: "Anomaly Detection",   icon: Search,      agent: "Benford + Duplicates + Patterns" },
  { event: "CRITIC_CHECK",         label: "RLAIF Quality Gate",  icon: Brain,       agent: "Critic Agent" },
  { event: "ENFORCING_GUARDRAILS", label: "Guardrail Engine",    icon: ShieldCheck, agent: "CGST + SEBI + IndAS + RBI" },
  { event: "GENERATING_REPORTS",   label: "Report Generation",   icon: FileText,    agent: "GSTR-3B + Variance + Audit + Tax" },
  { event: "FORM26AS_RECON",       label: "Form 26AS Recon",     icon: FileCheck,   agent: "TDS Reconciliation" },
  { event: "CONSOLIDATION",        label: "Multi-Entity",        icon: Building2,   agent: "IndAS 110 Consolidation" },
  { event: "REGULATORY_CHECK",     label: "Regulatory Check",    icon: Globe,       agent: "CBIC + SEBI + MCA Monitor" },
  { event: "COMPLETE",             label: "Complete",            icon: Flag,        agent: "Pipeline Finalized" },
] as const;

type StepStatus = "idle" | "running" | "done" | "error";

interface PipelineLog {
  event: string;
  agent?: string;
  status?: string;
  data?: Record<string, any>;
  timestamp?: string;
}

interface Props {
  logs: PipelineLog[];
  pipelineStatus: "IDLE" | "STARTED" | "RUNNING" | "COMPLETE" | "ERROR";
}

export function PipelineProgress({ logs, pipelineStatus }: Props) {
  // Derive step states from WebSocket logs
  const { stepStates, errorMessages, completedCount, progressPercent } = useMemo(() => {
    const states: Record<string, StepStatus> = {};
    const errors: Record<string, string> = {};

    for (const log of logs) {
      const ev = log.event;
      if (!ev) continue;

      // Map COMPLETE_WITH_ESCALATIONS to COMPLETE
      const mappedEvent = ev === "COMPLETE_WITH_ESCALATIONS" ? "COMPLETE" : ev;

      // Check if this event matches a pipeline step
      const step = PIPELINE_STEPS.find((s) => s.event === mappedEvent);
      if (!step) continue;

      if (log.status === "ERROR") {
        states[step.event] = "error";
        errors[step.event] = log.data?.error || log.data?.message || "Step failed";
      } else if (log.status === "DONE") {
        states[step.event] = "done";
      } else {
        // Only set to running if not already done/error
        if (states[step.event] !== "done" && states[step.event] !== "error") {
          states[step.event] = "running";
        }
      }
    }

    const done = Object.values(states).filter((s) => s === "done").length;
    const pct = Math.round((done / PIPELINE_STEPS.length) * 100);

    return { stepStates: states, errorMessages: errors, completedCount: done, progressPercent: pct };
  }, [logs]);

  if (pipelineStatus === "IDLE") return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-neutral-900/60 backdrop-blur-sm overflow-hidden">
      {/* Progress Header */}
      <div className="px-5 pt-4 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-white">Pipeline Progress</h3>
          <span className="text-xs text-neutral-500 font-mono">
            {completedCount}/{PIPELINE_STEPS.length} steps
          </span>
        </div>
        <span
          className={clsx(
            "text-xs font-bold px-2.5 py-0.5 rounded-full",
            progressPercent === 100
              ? "bg-emerald-500/15 text-emerald-400"
              : pipelineStatus === "ERROR"
              ? "bg-red-500/15 text-red-400"
              : "bg-indigo-500/15 text-indigo-400"
          )}
        >
          {progressPercent}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mx-5 h-1.5 rounded-full bg-neutral-800 overflow-hidden mb-4">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-700 ease-out",
            progressPercent === 100
              ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
              : pipelineStatus === "ERROR"
              ? "bg-gradient-to-r from-red-500 to-red-400"
              : "bg-gradient-to-r from-indigo-500 to-purple-500"
          )}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Steps Grid */}
      <div className="px-5 pb-5 grid grid-cols-2 md:grid-cols-5 gap-2">
        {PIPELINE_STEPS.map((step, i) => {
          const state: StepStatus = stepStates[step.event] || "idle";
          const StepIcon = step.icon;
          const error = errorMessages[step.event];

          return (
            <div
              key={step.event}
              className={clsx(
                "relative rounded-xl border p-3 transition-all duration-300 group",
                state === "done"    && "border-emerald-500/30 bg-emerald-500/5",
                state === "running" && "border-indigo-500/40 bg-indigo-500/10 shadow-lg shadow-indigo-500/5",
                state === "error"   && "border-red-500/30 bg-red-500/5",
                state === "idle"    && "border-white/5 bg-white/[0.02] opacity-50"
              )}
            >
              <div className="flex items-center gap-2 mb-1.5">
                {/* Status Indicator */}
                <div className="shrink-0">
                  {state === "done" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                  {state === "running" && <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />}
                  {state === "error" && <XCircle className="w-4 h-4 text-red-400" />}
                  {state === "idle" && <Circle className="w-4 h-4 text-neutral-600" />}
                </div>
                <StepIcon
                  className={clsx(
                    "w-3.5 h-3.5",
                    state === "done"    && "text-emerald-400/60",
                    state === "running" && "text-indigo-400/60",
                    state === "error"   && "text-red-400/60",
                    state === "idle"    && "text-neutral-700"
                  )}
                />
              </div>

              <p
                className={clsx(
                  "text-[11px] font-semibold leading-tight",
                  state === "done"    && "text-emerald-300",
                  state === "running" && "text-indigo-300",
                  state === "error"   && "text-red-300",
                  state === "idle"    && "text-neutral-600"
                )}
              >
                {step.label}
              </p>
              <p className="text-[9px] text-neutral-600 mt-0.5 truncate">{step.agent}</p>

              {/* Error tooltip */}
              {error && (
                <p className="text-[9px] text-red-400/80 mt-1 line-clamp-2">{error}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
