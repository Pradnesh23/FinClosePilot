"use client";
import { AlertTriangle, Zap, Copy, ExternalLink } from "lucide-react";
import clsx from "clsx";
import { formatCurrency } from "@/lib/utils";

type Anomaly = {
  anomaly_type?: string;
  category?: string;
  severity?: string;
  vendor_name?: string;
  amount_inr?: number;
  financial_exposure_inr?: number;
  reasoning?: string;
  description?: string;
};

const SEV_STYLE: Record<string, string> = {
  CRITICAL: "bg-red-500/15 border-red-500/40 text-red-400",
  HIGH:     "bg-orange-500/10 border-orange-500/30 text-orange-400",
  MEDIUM:   "bg-amber-500/10 border-amber-500/20 text-amber-400",
  LOW:      "bg-neutral-800/60 border-white/5 text-neutral-400",
};

export function AnomalyHeatmap({ anomalies }: { anomalies: Record<string, any> }) {
  const benfordList: Anomaly[] = anomalies?.benford?.violations ?? [];
  const duplicates: Anomaly[] = anomalies?.duplicates?.duplicates ?? [];
  const patterns: Anomaly[] = anomalies?.patterns?.anomalies ?? [];
  const all: (Anomaly & { source: string })[] = [
    ...benfordList.map((a) => ({ ...a, source: "Benford" })),
    ...duplicates.map((a) => ({ ...a, source: "Duplicate" })),
    ...patterns.map((a) => ({ ...a, source: "Pattern" })),
  ];

  if (!all.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-3">
        <AlertTriangle className="w-10 h-10 opacity-30" />
        <p className="text-sm">No anomalies detected yet</p>
      </div>
    );
  }

  // Sort: CRITICAL → HIGH → MEDIUM → LOW
  const ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
  const sorted = [...all].sort(
    (a, b) => ORDER.indexOf(a.severity ?? "LOW") - ORDER.indexOf(b.severity ?? "LOW")
  );

  return (
    <div className="space-y-2">
      {sorted.map((anomaly, i) => {
        const sev = anomaly.severity ?? "LOW";
        const style = SEV_STYLE[sev] ?? SEV_STYLE.LOW;
        const exposure = anomaly.financial_exposure_inr ?? anomaly.amount_inr ?? 0;
        return (
          <div key={i} className={clsx("rounded-xl border p-3 space-y-1.5 transition-all hover:brightness-110", style)}>
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 shrink-0" />
                <span className="text-xs font-bold uppercase tracking-wide">{sev}</span>
                <span className="text-xs text-neutral-500 px-1.5 py-0.5 rounded-md bg-black/30">
                  {anomaly.source}
                </span>
              </div>
              {exposure > 0 && (
                <span className="text-xs font-mono font-bold shrink-0">
                  {formatCurrency(exposure)}
                </span>
              )}
            </div>
            <p className="text-xs text-white/80 leading-snug">
              {anomaly.reasoning ?? anomaly.description ?? anomaly.category ?? "Anomaly detected"}
            </p>
            {anomaly.vendor_name && (
              <p className="text-xs text-neutral-500">🏢 {anomaly.vendor_name}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
