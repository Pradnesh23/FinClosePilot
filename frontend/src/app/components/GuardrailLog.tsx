"use client";
import { useState } from "react";
import { AlertTriangle, Shield, XCircle, Info, UserCheck, Loader2, CheckCircle2, MessageSquare } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { postRLHFSignal } from "@/lib/api";
import clsx from "clsx";

type Fire = {
  id?: number;
  rule_id: string;
  rule_level: string;
  regulation: string;
  section?: string;
  vendor_name?: string;
  amount_inr?: number;
  violation_detail: string;
  action_taken: string;
};

const LEVEL_CONFIG: Record<string, { icon: any; bg: string; border: string; badge: string; label: string }> = {
  HARD_BLOCK: {
    icon: XCircle,
    bg: "bg-red-500/5",
    border: "border-red-500/30",
    badge: "bg-red-500/20 text-red-400",
    label: "HARD BLOCK",
  },
  SOFT_FLAG: {
    icon: AlertTriangle,
    bg: "bg-amber-500/5",
    border: "border-amber-500/30",
    badge: "bg-amber-500/20 text-amber-400",
    label: "SOFT FLAG",
  },
  ADVISORY: {
    icon: Info,
    bg: "bg-blue-500/5",
    border: "border-blue-500/30",
    badge: "bg-blue-500/20 text-blue-400",
    label: "ADVISORY",
  },
  AUTO_ACTION: {
    icon: Shield,
    bg: "bg-purple-500/5",
    border: "border-purple-500/30",
    badge: "bg-purple-500/20 text-purple-400",
    label: "AUTO ACTION",
  },
};

function OverrideForm({
  fireId,
  runId,
  onDone,
}: {
  fireId: number;
  runId: string;
  onDone: (success: boolean) => void;
}) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!reason.trim()) return;
    setSubmitting(true);
    try {
      await postRLHFSignal(runId, fireId, reason.trim());
      onDone(true);
    } catch {
      onDone(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mt-2 p-3 rounded-lg bg-black/30 border border-white/10 space-y-2">
      <label className="text-[10px] text-neutral-500 uppercase tracking-wider font-bold flex items-center gap-1.5">
        <MessageSquare className="w-3 h-3" />
        CFO Override Reason
      </label>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Explain why this guardrail fire should be overridden..."
        rows={2}
        className="w-full bg-neutral-800/80 text-sm text-neutral-200 rounded-lg px-3 py-2 border border-white/10 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
      />
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={() => onDone(false)}
          className="text-xs text-neutral-500 hover:text-neutral-300 px-3 py-1 rounded-lg hover:bg-white/5 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!reason.trim() || submitting}
          className={clsx(
            "flex items-center gap-1.5 text-xs px-4 py-1.5 rounded-lg font-semibold transition-all",
            reason.trim() && !submitting
              ? "bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
              : "bg-neutral-800 text-neutral-600 cursor-not-allowed"
          )}
        >
          {submitting ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              Submitting…
            </>
          ) : (
            <>
              <UserCheck className="w-3 h-3" />
              Submit Override
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export function GuardrailLog({ fires = [], runId }: { fires: Fire[]; runId?: string }) {
  const [overrideOpen, setOverrideOpen] = useState<number | null>(null);
  const [overridden, setOverridden] = useState<Set<number>>(new Set());
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const handleOverrideDone = (fireId: number, success: boolean) => {
    setOverrideOpen(null);
    if (success) {
      setOverridden((prev) => new Set(prev).add(fireId));
      setToast({ message: "CFO override recorded — RLHF signal sent to learning loop", type: "success" });
    } else {
      setToast({ message: "Override submission failed", type: "error" });
    }
    setTimeout(() => setToast(null), 4000);
  };

  if (!fires.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-3">
        <Shield className="w-10 h-10 text-emerald-700 opacity-50" />
        <p className="text-sm">No guardrail violations in this run</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 relative">
      {/* Toast notification */}
      {toast && (
        <div
          className={clsx(
            "fixed top-20 right-6 z-50 px-4 py-3 rounded-xl border text-sm font-medium flex items-center gap-2 shadow-2xl animate-in slide-in-from-right duration-300",
            toast.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              : "bg-red-500/10 border-red-500/30 text-red-400"
          )}
        >
          {toast.type === "success" ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <XCircle className="w-4 h-4" />
          )}
          {toast.message}
        </div>
      )}

      {fires.map((fire, i) => {
        const cfg = LEVEL_CONFIG[fire.rule_level] ?? LEVEL_CONFIG.ADVISORY;
        const Icon = cfg.icon;
        const fireId = fire.id ?? i;
        const isOverridden = overridden.has(fireId);
        const canOverride = fire.rule_level === "SOFT_FLAG" && runId && fire.id != null && !isOverridden;

        return (
          <div
            key={i}
            className={clsx(
              "rounded-xl border p-4 space-y-2 transition-all",
              isOverridden ? "bg-emerald-500/5 border-emerald-500/20 opacity-75" : `${cfg.bg} ${cfg.border}`
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <Icon className="w-4 h-4 shrink-0 text-current opacity-70" />
                <span className="font-mono text-xs text-neutral-400 truncate">{fire.rule_id}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {isOverridden && (
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 flex items-center gap-1">
                    <UserCheck className="w-3 h-3" />
                    OVERRIDDEN
                  </span>
                )}
                <span className={clsx("px-2 py-0.5 rounded-full text-xs font-bold", cfg.badge)}>
                  {cfg.label}
                </span>
              </div>
            </div>

            <p className="text-sm text-white font-medium leading-snug">{fire.violation_detail}</p>

            <div className="grid grid-cols-2 gap-2 text-xs text-neutral-500">
              {fire.vendor_name && <span>🏢 {fire.vendor_name}</span>}
              {fire.amount_inr && fire.amount_inr > 0 && (
                <span>💰 {formatCurrency(fire.amount_inr)}</span>
              )}
              <span className="col-span-2 truncate">📋 {fire.regulation}</span>
            </div>

            <div className="flex items-center justify-between gap-2">
              <div className="text-xs text-emerald-400 bg-emerald-500/10 rounded-lg px-3 py-1.5 flex-1">
                ✅ {fire.action_taken}
              </div>

              {/* CFO Override Button */}
              {canOverride && (
                <button
                  onClick={() => setOverrideOpen(overrideOpen === fireId ? null : fireId)}
                  className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-all shrink-0"
                >
                  <UserCheck className="w-3 h-3" />
                  CFO Override
                </button>
              )}
            </div>

            {/* Override inline form */}
            {overrideOpen === fireId && runId && fire.id != null && (
              <OverrideForm
                fireId={fire.id}
                runId={runId}
                onDone={(success) => handleOverrideDone(fireId, success)}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
