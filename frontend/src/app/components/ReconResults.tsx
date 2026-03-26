"use client";
import { CheckCircle2, XCircle, AlertTriangle, ArrowRight, FileText } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import clsx from "clsx";

type ReconBreak = {
  break_id?: string;
  break_type?: string;
  amount_difference?: number;
  root_cause?: string;
  suggested_action?: string;
  vendor_name?: string;
  vendor_gstin?: string;
  reference_no?: string;
  transaction_id?: string;
  invoice_no?: string;
  // Bank recon
  description?: string;
  difference?: number;
  recommended_je?: string;
  bank_amount?: number;
  gl_amount?: number;
  days_difference?: number;
  auto_clearable?: boolean;
  recon_type?: string;
  // GST recon
  gstr1_amount?: number;
  gstr2a_amount?: number;
  books_amount?: number;
  // Vendor recon
  our_amount?: number;
  vendor_amount?: number;
};

type ReconSection = {
  matched_count?: number;
  break_count?: number;
  total_books?: number;
  total_gstr2a?: number;
  total_bank_debits?: number;
  total_bank_credits?: number;
  total_gl_debits?: number;
  total_gl_credits?: number;
  breaks?: ReconBreak[];
  summary?: string;
};

const SOURCE_MAP: Record<string, { from: string; to: string; icon: string }> = {
  gst:          { from: "Books / ERP", to: "GST Portal (GSTR-2A)", icon: "📊" },
  bank:         { from: "Bank Statement", to: "General Ledger", icon: "🏦" },
  vendor:       { from: "Our Records", to: "Vendor Statement", icon: "🏢" },
  intercompany: { from: "Parent Entity", to: "Subsidiary (IndAS 110)", icon: "🔗" },
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
      {sections.map(({ key, label }) => {
        const data: ReconSection = recon?.[key] ?? {};
        const matched = data.matched_count ?? 0;
        const breakCount = data.break_count ?? data.breaks?.length ?? 0;
        const hasData = matched > 0 || breakCount > 0;
        const source = SOURCE_MAP[key];

        return (
          <div key={key} className="rounded-xl border border-white/10 bg-black/30 overflow-hidden">
            {/* Section Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <div className="flex items-center gap-2">
                <span className="text-base">{source?.icon}</span>
                <h4 className="font-medium text-sm text-white">{label}</h4>
              </div>
              <div className="flex items-center gap-3 text-xs">
                {hasData ? (
                  <>
                    <span className="flex items-center gap-1 text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" /> {matched} matched
                    </span>
                    <span className={clsx("flex items-center gap-1", breakCount > 0 ? "text-red-400" : "text-neutral-500")}>
                      <XCircle className="w-3.5 h-3.5" /> {breakCount} breaks
                    </span>
                  </>
                ) : (
                  <span className="text-neutral-600">No data yet</span>
                )}
              </div>
            </div>

            {/* Source Indicator */}
            {hasData && source && (
              <div className="px-4 py-2 bg-black/20 border-b border-white/5 flex items-center gap-2 text-xs text-neutral-400">
                <FileText className="w-3 h-3" />
                <span className="text-indigo-400">{source.from}</span>
                <ArrowRight className="w-3 h-3 text-neutral-600" />
                <span className="text-purple-400">{source.to}</span>
              </div>
            )}

            {/* Break Details */}
            {data.breaks && data.breaks.length > 0 && (
              <div className="p-3 space-y-2 max-h-80 overflow-y-auto">
                {data.breaks.map((b, i) => {
                  const title = b.break_type || "BREAK";
                  const cause = b.root_cause || b.description;
                  const diff = b.amount_difference ?? b.difference;
                  const action = b.suggested_action || b.recommended_je;
                  const vendor = b.vendor_name;
                  const gstin = b.vendor_gstin;
                  const refNo = b.reference_no || b.transaction_id || b.invoice_no || b.break_id;

                  return (
                    <div key={i} className="text-xs p-3 rounded-lg bg-red-500/5 border border-red-500/10 space-y-1.5">
                      {/* Break Type + Reference */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                          <span className="text-red-400 font-semibold uppercase">{title}</span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {refNo && (
                            <span className="font-mono text-neutral-500 bg-black/30 px-1.5 py-0.5 rounded text-[10px]">
                              #{refNo}
                            </span>
                          )}
                          {diff !== undefined && diff !== 0 && (
                            <span className="text-red-400 font-mono font-bold">
                              {formatCurrency(Math.abs(diff))} diff
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Vendor Info */}
                      {(vendor || gstin) && (
                        <div className="flex items-center gap-2 text-neutral-400">
                          {vendor && <span>🏢 {vendor}</span>}
                          {gstin && <span className="font-mono text-neutral-500 text-[10px]">GSTIN: {gstin}</span>}
                        </div>
                      )}

                      {/* Amounts Side-by-Side (Bank recon) */}
                      {b.bank_amount !== undefined && b.gl_amount !== undefined && (
                        <div className="grid grid-cols-2 gap-2 bg-black/20 rounded-lg p-2">
                          <div>
                            <span className="text-neutral-500 text-[10px] uppercase">Bank</span>
                            <p className="text-white font-mono">{formatCurrency(b.bank_amount)}</p>
                          </div>
                          <div>
                            <span className="text-neutral-500 text-[10px] uppercase">GL</span>
                            <p className="text-white font-mono">{formatCurrency(b.gl_amount)}</p>
                          </div>
                        </div>
                      )}

                      {/* Root Cause */}
                      {cause && <p className="text-neutral-300 leading-snug">{cause}</p>}

                      {/* Days Difference (Bank) */}
                      {b.days_difference !== undefined && b.days_difference > 0 && (
                        <p className="text-amber-400 text-[10px]">
                          ⏱ {b.days_difference} day{b.days_difference > 1 ? "s" : ""} timing difference
                          {b.auto_clearable && " — Auto-clearable"}
                        </p>
                      )}

                      {/* Suggested Action */}
                      {action && (
                        <div className="text-emerald-400 bg-emerald-500/10 rounded px-2 py-1">
                          ✅ {action}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Summary */}
            {data.summary && (
              <div className="px-4 py-2.5 text-xs text-neutral-500 border-t border-white/5 leading-relaxed">
                {data.summary}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
