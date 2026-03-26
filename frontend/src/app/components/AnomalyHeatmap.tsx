"use client";
import { AlertTriangle, Zap, Copy, ExternalLink, ShieldAlert, Fingerprint } from "lucide-react";
import clsx from "clsx";
import { formatCurrency } from "@/lib/utils";

type Anomaly = {
  id?: number;
  anomaly_type?: string;
  category?: string;
  severity?: string;
  vendor_name?: string;
  vendor_gstin?: string;
  transaction_ids?: string | string[];
  amount_inr?: number;
  financial_exposure_inr?: number;
  reasoning?: string;
  description?: string;
  status?: string;
  p_value?: number;
  chi_square?: number;
};

const SEV_STYLE: Record<string, { bg: string; border: string; text: string; iconColor: string }> = {
  CRITICAL: {
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    text: "text-red-400",
    iconColor: "text-red-500",
  },
  HIGH: {
    bg: "bg-orange-500/10",
    border: "border-orange-500/20",
    text: "text-orange-400",
    iconColor: "text-orange-500",
  },
  MEDIUM: {
    bg: "bg-amber-500/5",
    border: "border-amber-500/20",
    text: "text-amber-400",
    iconColor: "text-amber-500",
  },
  LOW: {
    bg: "bg-neutral-900/40",
    border: "border-white/5",
    text: "text-neutral-400",
    iconColor: "text-neutral-600",
  },
};

export function AnomalyHeatmap({ anomalies }: { anomalies: Record<string, any> }) {
  const benfordList: Anomaly[] = anomalies?.benford?.violations ?? [];
  const duplicates: Anomaly[] = anomalies?.duplicates?.duplicates ?? [];
  const patterns: Anomaly[] = anomalies?.patterns?.anomalies ?? [];
  
  const all: (Anomaly & { source: string })[] = [
    ...benfordList.map((a) => ({ ...a, source: "Benford Analysis" })),
    ...duplicates.map((a) => ({ ...a, source: "Duplicate Detection" })),
    ...patterns.map((a) => ({ ...a, source: "Pattern Analysis" })),
  ];

  if (!all.length) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-neutral-600 gap-4 border border-dashed border-white/5 rounded-2xl">
        <div className="p-4 rounded-full bg-neutral-900/50">
          <ShieldAlert className="w-10 h-10 opacity-20" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-neutral-500">No anomalies detected</p>
          <p className="text-xs text-neutral-600 mt-1">Pipeline completed with clean results</p>
        </div>
      </div>
    );
  }

  // Sort: CRITICAL → HIGH → MEDIUM → LOW
  const ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
  const sorted = [...all].sort(
    (a, b) => ORDER.indexOf(a.severity ?? "LOW") - ORDER.indexOf(b.severity ?? "LOW")
  );

  return (
    <div className="space-y-3">
      {sorted.map((anomaly, i) => {
        const sev = anomaly.severity ?? "LOW";
        const cfg = SEV_STYLE[sev] ?? SEV_STYLE.LOW;
        const exposure = anomaly.financial_exposure_inr ?? anomaly.amount_inr ?? 0;
        const txIds = typeof anomaly.transaction_ids === 'string' 
          ? (anomaly.transaction_ids.startsWith('[') ? JSON.parse(anomaly.transaction_ids) : [anomaly.transaction_ids])
          : (anomaly.transaction_ids ?? []);
        
        const typeLabel = anomaly.anomaly_type?.replace(/_/g, " ") || anomaly.source;

        return (
          <div key={i} className={clsx(
            "rounded-xl border p-4 space-y-3 transition-all hover:ring-1 hover:ring-white/10 group",
            cfg.bg, cfg.border
          )}>
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <div className={clsx("p-1 rounded bg-black/40", cfg.iconColor)}>
                    <Zap className="w-3.5 h-3.5" />
                  </div>
                  <span className={clsx("text-[10px] font-black uppercase tracking-widest", cfg.text)}>
                    {sev}
                  </span>
                  <span className="text-[10px] text-neutral-500 bg-black/40 px-2 py-0.5 rounded-full border border-white/5">
                    {anomaly.source}
                  </span>
                </div>
                <h5 className="text-sm font-bold text-white capitalize">{typeLabel}</h5>
              </div>
              
              {exposure > 0 && (
                <div className="text-right">
                  <span className="text-[10px] text-neutral-500 uppercase font-bold tracking-tighter">Exposure</span>
                  <p className={clsx("text-lg font-mono font-bold leading-none", cfg.text)}>
                    {formatCurrency(exposure)}
                  </p>
                </div>
              )}
            </div>

            {/* Vendor & Proof Section */}
            <div className="flex flex-wrap gap-2">
              {anomaly.vendor_name && (
                <div className="px-2 py-1 rounded bg-black/30 border border-white/5 flex items-center gap-1.5 ">
                  <span className="text-neutral-500 text-[10px]">🏢</span>
                  <span className="text-xs text-neutral-300 font-medium">
                    {anomaly.vendor_name === "Unknown" ? "Unidentified Vendor" : anomaly.vendor_name}
                  </span>
                  {anomaly.vendor_gstin && (
                    <span className="text-[10px] text-neutral-600 font-mono border-l border-white/10 pl-1.5 ml-0.5">
                      {anomaly.vendor_gstin}
                    </span>
                  )}
                </div>
              )}
              
              {anomaly.p_value != null && (
                <div className="px-2 py-1 rounded bg-indigo-500/5 border border-indigo-500/10 flex items-center gap-1.5 text-indigo-400">
                  <Fingerprint className="w-3 h-3" />
                  <span className="text-[10px] font-bold">P-Value: {anomaly.p_value.toFixed(4)}</span>
                </div>
              )}

              {txIds.length > 0 && (
                <div className="px-2 py-1 rounded bg-black/30 border border-white/5 flex items-center gap-1.5 text-neutral-400">
                  <span className="text-neutral-500 text-[10px]">🔖</span>
                  <span className="text-[10px] font-mono">{txIds.length} Linked Trans.</span>
                </div>
              )}
            </div>

            {/* Reasoning */}
            <div className="relative">
              <p className="text-xs text-neutral-400 leading-relaxed pl-3 border-l-2 border-white/5 bg-gradient-to-r from-white/5 to-transparent py-2 rounded-r-lg">
                {anomaly.reasoning ?? anomaly.description ?? "Heuristic analysis indicates a high probability of processing error or policy bypass."}
              </p>
            </div>

            {/* Evidence Footer */}
            {txIds.length > 0 && (
              <div className="pt-1 flex gap-1.5 overflow-x-auto no-scrollbar pb-1">
                {txIds.slice(0, 4).map((id: string) => (
                  <span key={id} className="text-[9px] font-mono text-neutral-600 bg-neutral-900 px-1.5 py-0.5 rounded border border-white/5 shrink-0">
                    ID: {id}
                  </span>
                ))}
                {txIds.length > 4 && (
                  <span className="text-[9px] text-neutral-700 self-center">+{txIds.length - 4} more</span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
