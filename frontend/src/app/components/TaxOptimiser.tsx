"use client";
import { TrendingUp, IndianRupee, ExternalLink, ShieldAlert, AlertTriangle } from "lucide-react";
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

      {summary && (
        <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10 text-xs text-indigo-300 leading-relaxed italic">
          💡 {summary}
        </div>
      )}

      {/* Opportunities List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {opportunities.map((op, i) => (
          <div key={i} className="p-4 rounded-xl border border-white/10 bg-neutral-900/50 space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-black bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded uppercase tracking-tighter">
                    {op.category}
                  </span>
                  <span
                    className={clsx(
                      "px-2 py-0.5 rounded-full text-[10px] font-bold border",
                      PRIORITY_STYLE[op.priority] ?? PRIORITY_STYLE.LOW
                    )}
                  >
                    {op.priority}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-emerald-400 font-black text-base block leading-none">
                    +{formatCurrency(op.estimated_saving_inr)}
                  </span>
                  <span className="text-[9px] text-neutral-600 uppercase font-bold">Est. Saving</span>
                </div>
              </div>

              <h5 className="text-sm font-bold text-white leading-snug">{op.opportunity}</h5>
              
              <div className="flex items-center gap-1.5 text-[10px] text-neutral-500 font-mono">
                <ShieldAlert className="w-3 h-3 text-indigo-500" />
                <span className="text-indigo-400/80 font-bold">{op.section}</span>
                <span className="opacity-40">|</span>
                <span className="truncate">{op.regulation}</span>
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-white/5">
              <div className="text-xs text-neutral-300 bg-black/40 rounded-lg px-3 py-2 border border-white/5">
                <span className="text-indigo-500 font-bold block mb-1 uppercase text-[9px] tracking-widest">Recommended Action</span>
                {op.action_required}
              </div>
              
              <div className="flex items-center justify-between text-[10px]">
                {op.deadline && (
                  <span className="text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Due {op.deadline}
                  </span>
                )}
                <span className="ml-auto text-neutral-600 bg-neutral-800/50 px-2 py-0.5 rounded font-bold uppercase tracking-tighter">
                  Confidence: {(op.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
