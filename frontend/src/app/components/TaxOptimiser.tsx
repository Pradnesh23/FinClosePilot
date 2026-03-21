"use client";
import { TrendingUp, IndianRupee, ExternalLink } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import clsx from "clsx";

type Opportunity = {
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

const PRIORITY_STYLE: Record<string, string> = {
  HIGH: "bg-red-500/20 text-red-400 border-red-500/30",
  MEDIUM: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  LOW: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

export function TaxOptimiser({ data }: { data: any }) {
  const opportunities: Opportunity[] = data?.opportunities ?? [];
  const total: number = data?.total_potential_saving_inr ?? 0;
  const summary: string = data?.executive_summary ?? "";

  if (!opportunities.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-3">
        <IndianRupee className="w-10 h-10 opacity-30" />
        <p className="text-sm">Tax opportunities appear after pipeline runs</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Total Savings Banner */}
      <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-r from-emerald-500/10 to-indigo-500/5 border border-emerald-500/20">
        <TrendingUp className="w-8 h-8 text-emerald-400 shrink-0" />
        <div>
          <p className="text-xs text-neutral-400">Total Potential Tax Saving</p>
          <p className="text-2xl font-bold text-emerald-400">{formatCurrency(total)}</p>
        </div>
      </div>

      {summary && <p className="text-xs text-neutral-500 leading-relaxed">{summary}</p>}

      {/* Opportunities List */}
      <div className="space-y-3">
        {opportunities.map((op, i) => (
          <div key={i} className="p-4 rounded-xl border border-white/10 bg-neutral-900/50 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-neutral-500 font-mono">{op.category}</span>
                <span
                  className={clsx(
                    "px-2 py-0.5 rounded-full text-xs font-bold border",
                    PRIORITY_STYLE[op.priority] ?? PRIORITY_STYLE.LOW
                  )}
                >
                  {op.priority}
                </span>
              </div>
              <span className="text-emerald-400 font-bold text-sm shrink-0">
                +{formatCurrency(op.estimated_saving_inr)}
              </span>
            </div>
            <p className="text-sm text-white">{op.opportunity}</p>
            <p className="text-xs text-neutral-500">{op.section} — {op.regulation}</p>
            <div className="text-xs text-indigo-400 bg-indigo-500/10 rounded-lg px-3 py-1.5">
              📋 {op.action_required}
            </div>
            {op.deadline && (
              <p className="text-xs text-amber-400">⚠️ Deadline: {op.deadline}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
