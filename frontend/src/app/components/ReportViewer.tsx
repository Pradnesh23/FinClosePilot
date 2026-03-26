"use client";
import { FileText, Download, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { formatCurrency } from "@/lib/utils";

function JsonViewer({ data, depth = 0 }: { data: any; depth?: number }) {
  const [open, setOpen] = useState(depth < 2);
  if (typeof data === "string") return <span className="text-emerald-400">&quot;{data}&quot;</span>;
  if (typeof data === "number") return <span className="text-amber-400">{formatCurrency(data)}</span>;
  if (typeof data === "boolean") return <span className="text-purple-400">{String(data)}</span>;
  if (data === null) return <span className="text-neutral-500">null</span>;
  if (Array.isArray(data)) {
    return (
      <span>
        <button onClick={() => setOpen(!open)} className="text-indigo-400 hover:text-indigo-300">
          [{data.length}] {open ? "▾" : "▸"}
        </button>
        {open && (
          <div className="pl-4 border-l border-white/5 mt-1 space-y-1">
            {data.slice(0, 10).map((v, i) => (
              <div key={i}><JsonViewer data={v} depth={depth + 1} /></div>
            ))}
            {data.length > 10 && <p className="text-neutral-600 text-xs">...{data.length - 10} more</p>}
          </div>
        )}
      </span>
    );
  }
  if (typeof data === "object") {
    const keys = Object.keys(data);
    return (
      <span>
        <button onClick={() => setOpen(!open)} className="text-blue-400 hover:text-blue-300">
          {"{"}⋯{"}"} {open ? "▾" : "▸"}
        </button>
        {open && (
          <div className="pl-4 border-l border-white/5 mt-1 space-y-1">
            {keys.slice(0, 20).map((k) => (
              <div key={k} className="flex gap-2 items-start">
                <span className="text-neutral-400 shrink-0 text-xs">{k}:</span>
                <JsonViewer data={data[k]} depth={depth + 1} />
              </div>
            ))}
          </div>
        )}
      </span>
    );
  }
  return <span className="text-neutral-300">{String(data)}</span>;
}

type ReportViewerProps = {
  reports: Record<string, any>;
  runId?: string;
};

const REPORT_LABELS: Record<string, string> = {
  gstr3b: "GSTR-3B Draft",
  variance: "Variance Analysis",
  audit_committee: "Audit Committee",
  tax_optimiser: "Tax Optimiser",
};

function Gstr3bTable({ data }: { data: any }) {
  if (!data || typeof data !== "object") return null;
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="bg-white/5 border-b border-white/10 uppercase tracking-tighter text-neutral-500 font-bold">
              <th className="px-3 py-2">Section / Description</th>
              <th className="px-3 py-2 text-right">Taxable Value</th>
              <th className="px-3 py-2 text-right">IGST</th>
              <th className="px-3 py-2 text-right">CGST</th>
              <th className="px-3 py-2 text-right">SGST</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {Object.entries(data).map(([key, val]: [string, any]) => (
              <tr key={key} className="hover:bg-white/5">
                <td className="px-3 py-2 font-medium text-neutral-300">{key.replace(/_/g, " ")}</td>
                <td className="px-3 py-2 text-right text-white font-mono">{formatCurrency(val.taxable_value ?? 0)}</td>
                <td className="px-3 py-2 text-right text-indigo-400 font-mono">{formatCurrency(val.igst ?? 0)}</td>
                <td className="px-3 py-2 text-right text-emerald-400 font-mono">{formatCurrency(val.cgst ?? 0)}</td>
                <td className="px-3 py-2 text-right text-emerald-400 font-mono">{formatCurrency(val.sgst ?? 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AuditCommitteeView({ data }: { data: any }) {
  if (!data || typeof data !== "object") return null;
  const sections = data.sections || data;
  return (
    <div className="space-y-6">
      <div className="text-center border-b border-white/10 pb-4 mb-4">
        <h3 className="text-lg font-bold text-white uppercase tracking-widest">Audit Committee Summary Report</h3>
        <p className="text-xs text-neutral-500 mt-1">Ref: {data.report_id || "FC-AC-2026"}</p>
      </div>
      {Object.entries(sections).map(([title, content]: [string, any]) => (
        <div key={title} className="space-y-2">
          <h4 className="text-xs font-black text-indigo-400 uppercase tracking-wider">{title.replace(/_/g, " ")}</h4>
          <div className="p-4 rounded-xl bg-black/40 border border-white/5 text-xs text-neutral-400 leading-relaxed whitespace-pre-wrap">
            {typeof content === "string" ? content : JSON.stringify(content, null, 2)}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ReportViewer({ reports, runId }: ReportViewerProps) {
  const [activeTab, setActiveTab] = useState(Object.keys(reports)[0] ?? "gstr3b");
  const [viewMode, setViewMode] = useState<"formatted" | "json">("formatted");

  const tabs = Object.keys(REPORT_LABELS).filter(
    (k) => reports[k] !== undefined && reports[k] !== null
  );

  if (!tabs.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-3">
        <FileText className="w-10 h-10 opacity-30" />
        <p className="text-sm">Reports will appear here after the pipeline completes</p>
      </div>
    );
  }

  const downloadReport = () => {
    const blob = new Blob([JSON.stringify(reports[activeTab], null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeTab}_${runId ?? "report"}.json`;
    a.click();
  };

  const printReport = async () => {
    if (!runId) return;
    try {
      // Direct link to the professional PDF generator endpoint
      const token = localStorage.getItem("token");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/runs/${runId}/audit-package/pdf`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error("PDF generation failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FinClosePilot_Audit_${runId.slice(0, 8)}.pdf`;
      a.click();
    } catch (err) {
      console.error(err);
      window.print(); // Fallback to browser print if backend fails
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex gap-1 bg-black/40 rounded-xl p-1">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                activeTab === t
                  ? "bg-indigo-600 text-white"
                  : "text-neutral-500 hover:text-white"
              }`}
            >
              {REPORT_LABELS[t] ?? t}
            </button>
          ))}
        </div>
        
        <div className="flex gap-2">
          <div className="flex bg-neutral-900 rounded-lg p-1 border border-white/5">
            <button
              onClick={() => setViewMode("formatted")}
              className={`px-2 py-1 rounded text-[10px] uppercase font-bold tracking-wider transition-all ${
                viewMode === "formatted" ? "bg-white/10 text-white" : "text-neutral-600"
              }`}
            >
              Formatted
            </button>
            <button
              onClick={() => setViewMode("json")}
              className={`px-2 py-1 rounded text-[10px] uppercase font-bold tracking-wider transition-all ${
                viewMode === "json" ? "bg-white/10 text-white" : "text-neutral-600"
              }`}
            >
              JSON
            </button>
          </div>
          <button
            onClick={downloadReport}
            title="Export JSON"
            className="p-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white transition-colors border border-white/5"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={printReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-bold shadow-lg shadow-indigo-500/20"
          >
            <FileText className="w-3.5 h-3.5" /> PDF
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-white/5 overflow-hidden min-h-[300px] print:border-none print:shadow-none">
        <div className="bg-black/40 p-6 print:bg-white print:text-black">
          {viewMode === "json" ? (
            <div className="font-mono text-xs overflow-auto max-h-[500px]">
              <JsonViewer data={reports[activeTab]} />
            </div>
          ) : (
            <div className="animate-in fade-in duration-500">
              {activeTab === "gstr3b" && <Gstr3bTable data={reports[activeTab]} />}
              {activeTab === "audit_committee" && <AuditCommitteeView data={reports[activeTab]} />}
              {activeTab !== "gstr3b" && activeTab !== "audit_committee" && (
                <div className="font-mono text-xs overflow-auto max-h-[500px]">
                  <JsonViewer data={reports[activeTab]} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

