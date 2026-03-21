"use client";
import { FileText, AlertTriangle, CheckCircle2, Upload } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import clsx from "clsx";

type TdsDiscrepancy = {
  head?: string;
  tds_as_per_26as?: number;
  tds_in_books?: number;
  difference?: number;
  risk?: string;
};

type Form26ASResult = {
  pan?: string;
  assessment_year?: string;
  total_tds_26as?: number;
  total_tds_books?: number;
  net_discrepancy?: number;
  risk_level?: "HIGH" | "MEDIUM" | "LOW";
  discrepancies?: TdsDiscrepancy[];
  ai_assessment?: string;
  recommended_actions?: string[];
};

const RISK_STYLE: Record<string, string> = {
  HIGH:   "bg-red-500/10 border-red-500/30 text-red-400",
  MEDIUM: "bg-amber-500/10 border-amber-500/30 text-amber-400",
  LOW:    "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
};

export function Form26AS({ result }: { result?: Form26ASResult }) {
  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-4">
        <FileText className="w-10 h-10 opacity-30" />
        <div className="text-center space-y-1">
          <p className="text-sm">Form 26AS / AIS Reconciliation</p>
          <p className="text-xs text-neutral-700">
            Upload a Form 26AS PDF via the file upload endpoint to see TDS reconciliation
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-neutral-900 border border-white/5 text-xs text-neutral-500">
          <Upload className="w-3.5 h-3.5" />
          POST /api/upload with form26as field
        </div>
      </div>
    );
  }

  const riskStyle = RISK_STYLE[result.risk_level ?? "LOW"];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-neutral-500">PAN: {result.pan ?? "—"}</p>
          <p className="text-xs text-neutral-500">AY: {result.assessment_year ?? "—"}</p>
        </div>
        <span className={clsx("px-3 py-1 rounded-full text-xs font-bold border", riskStyle)}>
          {result.risk_level} RISK
        </span>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "26AS TDS", value: formatCurrency(result.total_tds_26as ?? 0), color: "text-white" },
          { label: "Books TDS", value: formatCurrency(result.total_tds_books ?? 0), color: "text-white" },
          {
            label: "Discrepancy",
            value: formatCurrency(Math.abs(result.net_discrepancy ?? 0)),
            color: (result.net_discrepancy ?? 0) !== 0 ? "text-red-400" : "text-emerald-400",
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="p-3 rounded-xl bg-neutral-900 border border-white/5 text-center">
            <p className="text-xs text-neutral-500">{label}</p>
            <p className={clsx("text-sm font-bold mt-1", color)}>{value}</p>
          </div>
        ))}
      </div>

      {/* Discrepancies */}
      {result.discrepancies && result.discrepancies.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Discrepancies by Head</p>
          {result.discrepancies.map((d, i) => (
            <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-white/5 bg-black/30 text-sm">
              <div>
                <p className="text-white">{d.head}</p>
                <p className="text-xs text-neutral-500 mt-0.5">{d.risk ?? "Normal"}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-neutral-500">26AS: {formatCurrency(d.tds_as_per_26as ?? 0)}</p>
                <p className={clsx("text-xs font-bold", (d.difference ?? 0) !== 0 ? "text-red-400" : "text-emerald-400")}>
                  Δ {formatCurrency(Math.abs(d.difference ?? 0))}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* AI Assessment */}
      {result.ai_assessment && (
        <div className="p-3 rounded-xl bg-indigo-500/5 border border-indigo-500/10 text-xs text-neutral-400 leading-relaxed">
          🤖 {result.ai_assessment}
        </div>
      )}

      {/* Actions */}
      {result.recommended_actions && result.recommended_actions.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-neutral-400 uppercase tracking-wider">Recommended Actions</p>
          {result.recommended_actions.map((a, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-neutral-400">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
              {a}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
