"use client";
import { formatCurrency } from "@/lib/utils";
import clsx from "clsx";
import {
  CheckCircle2, XCircle, AlertTriangle, ShieldCheck, Clock,
  TrendingDown, TrendingUp, Activity, IndianRupee, Zap,
} from "lucide-react";
import type { RunSummary, GuardrailLevel } from "@/lib/types";

type CloseDashboardProps = {
  run?: Partial<RunSummary>;
  guardrailBreakdown?: Record<GuardrailLevel, number>;
};

function RiskGauge({ score }: { score: number }) {
  // score 0–100; 0=safe, 100=critical
  const clampedScore = Math.max(0, Math.min(100, score));
  const color =
    clampedScore >= 70 ? "text-red-400" :
    clampedScore >= 40 ? "text-amber-400" :
    "text-emerald-400";
  const label =
    clampedScore >= 70 ? "HIGH RISK" :
    clampedScore >= 40 ? "MEDIUM" :
    "LOW RISK";
  const degrees = (clampedScore / 100) * 180; // 0–180 degrees for semicircle

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-32 h-16 overflow-hidden">
        {/* Background arc */}
        <div className="absolute inset-0 rounded-t-full border-8 border-neutral-800" />
        {/* Colored arc */}
        <div
          className={clsx(
            "absolute inset-0 rounded-t-full border-8 origin-bottom transition-all duration-700",
            clampedScore >= 70 ? "border-red-500" :
            clampedScore >= 40 ? "border-amber-500" : "border-emerald-500"
          )}
          style={{ clipPath: `inset(0 ${100 - clampedScore}% 0 0)` }}
        />
        {/* Score in center */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
          <span className={clsx("text-xl font-bold", color)}>{clampedScore}</span>
        </div>
      </div>
      <span className={clsx("text-xs font-bold tracking-widest", color)}>{label}</span>
    </div>
  );
}

function StatRow({ icon: Icon, label, value, sub, color = "text-white" }: any) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
      <Icon className={clsx("w-4 h-4 shrink-0", color)} />
      <span className="text-sm text-neutral-400 flex-1">{label}</span>
      <div className="text-right">
        <span className={clsx("text-sm font-semibold", color)}>{value}</span>
        {sub && <p className="text-xs text-neutral-600">{sub}</p>}
      </div>
    </div>
  );
}

export function CloseDashboard({ run, guardrailBreakdown }: CloseDashboardProps) {
  const matched      = run?.matched_records ?? 0;
  const total        = run?.total_records ?? matched + (run?.breaks ?? 0);
  const breaks       = run?.breaks ?? 0;
  const anomalies    = run?.anomalies ?? 0;
  const hardBlocks   = run?.hard_blocks ?? 0;
  const blockedInr   = run?.total_blocked_inr ?? 0;
  const timeTaken    = run?.time_taken_seconds ?? 0;
  const matchRate    = total > 0 ? Math.round((matched / total) * 100) : 0;
  const riskScore    = Math.min(100, hardBlocks * 25 + anomalies * 5 + breaks * 2);
  const isComplete   = run?.status === "COMPLETE";

  return (
    <div className="space-y-5">
      {/* Close Status Badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          <span className="text-sm font-medium text-white">Close Status</span>
        </div>
        <span
          className={clsx(
            "px-3 py-1 rounded-full text-xs font-bold border",
            isComplete
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : run?.status
              ? "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse"
              : "bg-neutral-800 text-neutral-500 border-white/5"
          )}
        >
          {run?.status ?? "IDLE"}
        </span>
      </div>

      {/* Period + Match Rate */}
      {run?.period && (
        <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/15">
          <p className="text-xs text-neutral-500">Period</p>
          <p className="text-lg font-bold text-white">{run.period}</p>
          {matchRate > 0 && (
            <div className="mt-2">
              <div className="flex justify-between text-xs text-neutral-500 mb-1">
                <span>Match Rate</span>
                <span>{matchRate}%</span>
              </div>
              <div className="h-1.5 bg-neutral-800 rounded-full">
                <div
                  className={clsx("h-full rounded-full transition-all duration-700",
                    matchRate >= 95 ? "bg-emerald-500" : matchRate >= 80 ? "bg-amber-500" : "bg-red-500"
                  )}
                  style={{ width: `${matchRate}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Risk Gauge */}
      {isComplete && (
        <div className="flex flex-col items-center gap-2 py-2">
          <p className="text-xs text-neutral-500 font-medium uppercase tracking-wider">Risk Score</p>
          <RiskGauge score={riskScore} />
        </div>
      )}

      {/* Key Metrics */}
      <div className="rounded-xl border border-white/5 bg-black/20 px-4 py-2 divide-y divide-white/5">
        <StatRow icon={CheckCircle2} label="Matched Records"   value={matched.toLocaleString("en-IN")} color="text-emerald-400" />
        <StatRow icon={XCircle}      label="Recon Breaks"      value={breaks}                           color={breaks > 0 ? "text-red-400" : "text-neutral-400"} />
        <StatRow icon={AlertTriangle} label="Anomalies"        value={anomalies}                        color={anomalies > 0 ? "text-amber-400" : "text-neutral-400"} />
        <StatRow icon={ShieldCheck}  label="Guardrail Fires"   value={run?.guardrail_fires ?? 0}        color="text-indigo-400" />
        <StatRow icon={Clock}        label="Pipeline Time"     value={timeTaken ? `${Math.round(timeTaken)}s` : "—"} color="text-neutral-400" />
      </div>

      {/* Hard Block ITC Summary */}
      {hardBlocks > 0 && (
        <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 space-y-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-red-400" />
            <span className="text-xs font-bold text-red-400 uppercase tracking-wider">
              {hardBlocks} Hard Block{hardBlocks > 1 ? "s" : ""} — CGST 17(5)
            </span>
          </div>
          <p className="text-2xl font-bold text-white">{formatCurrency(blockedInr)}</p>
          <p className="text-xs text-neutral-500">ITC auto-reversed · no manual action needed</p>
        </div>
      )}

      {/* Guardrail Breakdown */}
      {guardrailBreakdown && Object.values(guardrailBreakdown).some(v => v > 0) && (
        <div className="space-y-2">
          <p className="text-xs text-neutral-500 font-medium uppercase tracking-wider">Guardrail Breakdown</p>
          {(Object.entries(guardrailBreakdown) as [GuardrailLevel, number][]).map(([level, count]) => {
            if (!count) return null;
            const colors: Record<GuardrailLevel, string> = {
              HARD_BLOCK:  "text-red-400 bg-red-500/10",
              SOFT_FLAG:   "text-amber-400 bg-amber-500/10",
              ADVISORY:    "text-blue-400 bg-blue-500/10",
              AUTO_ACTION: "text-purple-400 bg-purple-500/10",
            };
            return (
              <div key={level} className="flex justify-between items-center px-3 py-2 rounded-lg text-xs">
                <span className={clsx("px-2 py-0.5 rounded-full font-bold", colors[level])}>{level}</span>
                <span className="text-white font-semibold">{count}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
