"use client";
import { AlertTriangle, Shield, XCircle, Info } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
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

export function GuardrailLog({ fires = [] }: { fires: Fire[] }) {
  if (!fires.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-3">
        <Shield className="w-10 h-10 text-emerald-700 opacity-50" />
        <p className="text-sm">No guardrail violations in this run</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {fires.map((fire, i) => {
        const cfg = LEVEL_CONFIG[fire.rule_level] ?? LEVEL_CONFIG.ADVISORY;
        const Icon = cfg.icon;
        return (
          <div
            key={i}
            className={clsx("rounded-xl border p-4 space-y-2 transition-all", cfg.bg, cfg.border)}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <Icon className="w-4 h-4 shrink-0 text-current opacity-70" />
                <span className="font-mono text-xs text-neutral-400 truncate">{fire.rule_id}</span>
              </div>
              <span className={clsx("px-2 py-0.5 rounded-full text-xs font-bold shrink-0", cfg.badge)}>
                {cfg.label}
              </span>
            </div>

            <p className="text-sm text-white font-medium leading-snug">{fire.violation_detail}</p>

            <div className="grid grid-cols-2 gap-2 text-xs text-neutral-500">
              {fire.vendor_name && <span>🏢 {fire.vendor_name}</span>}
              {fire.amount_inr && fire.amount_inr > 0 && (
                <span>💰 {formatCurrency(fire.amount_inr)}</span>
              )}
              <span className="col-span-2 truncate">📋 {fire.regulation}</span>
            </div>

            <div className="text-xs text-emerald-400 bg-emerald-500/10 rounded-lg px-3 py-1.5">
              ✅ {fire.action_taken}
            </div>
          </div>
        );
      })}
    </div>
  );
}
