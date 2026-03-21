"use client";
import { CheckCircle2, XCircle, AlertTriangle, ChevronRight } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import clsx from "clsx";

type ReconBreak = {
  break_type?: string;
  amount_difference?: number;
  root_cause?: string;
  suggested_action?: string;
  vendor_name?: string;
};

type ReconSection = {
  matched_count?: number;
  break_count?: number;
  total_books?: number;
  total_gstr2a?: number;
  breaks?: ReconBreak[];
  summary?: string;
};

export function ReconResults({ recon }: { recon: Record<string, ReconSection> }) {
  const sections = [
    { key: "gst", label: "GST Reconciliation", color: "indigo" },
    { key: "bank", label: "Bank Reconciliation", color: "emerald" },
    { key: "vendor", label: "Vendor Reconciliation", color: "amber" },
    { key: "intercompany", label: "Intercompany (IndAS 110)", color: "purple" },
  ];

  return (
    <div className="space-y-4">
      {sections.map(({ key, label, color }) => {
        const data: ReconSection = recon?.[key] ?? {};
        const matched = data.matched_count ?? 0;
        const breaks = data.break_count ?? data.breaks?.length ?? 0;
        const hasData = matched > 0 || breaks > 0;

        return (
          <div key={key} className="rounded-xl border border-white/10 bg-black/30 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <h4 className="font-medium text-sm text-white">{label}</h4>
              <div className="flex items-center gap-3 text-xs">
                {hasData ? (
                  <>
                    <span className="flex items-center gap-1 text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" /> {matched} matched
                    </span>
                    <span className={clsx("flex items-center gap-1", breaks > 0 ? "text-red-400" : "text-neutral-500")}>
                      <XCircle className="w-3.5 h-3.5" /> {breaks} breaks
                    </span>
                  </>
                ) : (
                  <span className="text-neutral-600">No data yet</span>
                )}
              </div>
            </div>

            {data.breaks && data.breaks.length > 0 && (
              <div className="p-3 space-y-2 max-h-48 overflow-y-auto">
                {data.breaks.slice(0, 5).map((b, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs p-2 rounded-lg bg-red-500/5 border border-red-500/10">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      {b.root_cause && <p className="text-neutral-300 truncate">{b.root_cause}</p>}
                      {b.amount_difference !== undefined && b.amount_difference !== 0 && (
                        <p className="text-red-400 font-mono">{formatCurrency(Math.abs(b.amount_difference))} diff</p>
                      )}
                      {b.suggested_action && (
                        <p className="text-emerald-400 mt-1">{b.suggested_action}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {data.summary && (
              <div className="px-4 py-2.5 text-xs text-neutral-500 border-t border-white/5">
                {data.summary}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
