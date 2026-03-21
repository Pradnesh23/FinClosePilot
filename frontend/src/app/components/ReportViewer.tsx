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

export function ReportViewer({ reports, runId }: ReportViewerProps) {
  const [activeTab, setActiveTab] = useState(Object.keys(reports)[0] ?? "gstr3b");

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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
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
        <button
          onClick={downloadReport}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-xs text-neutral-400 hover:text-white transition-colors"
        >
          <Download className="w-3.5 h-3.5" /> Export JSON
        </button>
      </div>

      <div className="bg-black/40 rounded-xl p-4 font-mono text-xs overflow-auto max-h-96 border border-white/5">
        <JsonViewer data={reports[activeTab]} />
      </div>
    </div>
  );
}
