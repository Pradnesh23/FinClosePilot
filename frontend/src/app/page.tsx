"use client";

import { useState, useEffect, useRef } from "react";
import clsx from "clsx";
import {
  Play, CheckCircle2, AlertTriangle, XCircle, Clock, ShieldCheck,
  Zap, BarChart2, Search, FileText, IndianRupee, Globe, Upload,
  RefreshCw, ChevronRight,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { startDemo, getRun, WS_BASE } from "@/lib/api";

import { GuardrailLog }   from "./components/GuardrailLog";
import { BenfordChart }   from "./components/BenfordChart";
import { AnomalyHeatmap } from "./components/AnomalyHeatmap";
import { ReconResults }   from "./components/ReconResults";
import { ReportViewer }   from "./components/ReportViewer";
import { AuditQuery }     from "./components/AuditQuery";
import { TaxOptimiser }   from "./components/TaxOptimiser";
import { RegMonitor }     from "./components/RegMonitor";

// ─── Types ────────────────────────────────────────────────────────────────────
type PipelineStatus = "IDLE" | "STARTED" | "RUNNING" | "COMPLETE" | "ERROR";
type RunData = {
  run_id: string;
  status: string;
  matched_records: number;
  breaks: number;
  anomalies: number;
  guardrail_fires: number;
  hard_blocks: number;
  total_blocked_inr: number;
  time_taken_seconds: number;
};

type Tab = "live" | "recon" | "anomalies" | "guardrails" | "reports" | "tax" | "audit" | "regulatory";

const TABS: { id: Tab; label: string; icon: any }[] = [
  { id: "live",       label: "Live Feed",    icon: Zap },
  { id: "recon",      label: "Recon",        icon: CheckCircle2 },
  { id: "anomalies",  label: "Anomalies",    icon: AlertTriangle },
  { id: "guardrails", label: "Guardrails",   icon: ShieldCheck },
  { id: "reports",    label: "Reports",      icon: FileText },
  { id: "tax",        label: "Tax",          icon: IndianRupee },
  { id: "audit",      label: "Audit Query",  icon: Search },
  { id: "regulatory", label: "Reg Monitor",  icon: Globe },
];

// ─── Metric Card ─────────────────────────────────────────────────────────────
function Metric({ label, value, icon: Icon, color }: any) {
  const c: Record<string, string> = {
    emerald: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
    red:     "text-red-400 bg-red-400/10 border-red-400/20",
    amber:   "text-amber-400 bg-amber-400/10 border-amber-400/20",
    indigo:  "text-indigo-400 bg-indigo-400/10 border-indigo-400/20",
  };
  return (
    <div className={clsx("p-4 rounded-xl border flex flex-col justify-between min-h-[88px]", c[color])}>
      <div className="flex justify-between items-start">
        <span className="text-xs uppercase tracking-wider opacity-70 font-medium">{label}</span>
        <Icon className="w-4 h-4 opacity-70" />
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const [status, setStatus]     = useState<PipelineStatus>("IDLE");
  const [runId, setRunId]       = useState<string | null>(null);
  const [logs, setLogs]         = useState<any[]>([]);
  const [runData, setRunData]   = useState<Partial<RunData>>({});
  const [fullResult, setFullResult] = useState<any>({});
  const [activeTab, setActiveTab]   = useState<Tab>("live");
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll log terminal
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Connect WebSocket once run_id is known
  useEffect(() => {
    if (!runId) return;
    const ws = new WebSocket(`${WS_BASE}/${runId}`);
    ws.onmessage = ({ data }) => {
      const msg = JSON.parse(data);
      if (msg.event === "CONNECTED" || msg.event === "PING") return;
      setLogs((p) => [...p, msg]);
      if (msg.event === "COMPLETE") {
        setStatus("COMPLETE");
      } else {
        setStatus("RUNNING");
      }
    };
    ws.onerror = () => setStatus("ERROR");
    return () => ws.close();
  }, [runId]);

  // Fetch full run result when pipeline completes
  useEffect(() => {
    if (status === "COMPLETE" && runId) {
      getRun(runId).then((d) => {
        setRunData(d.run ?? {});
        setFullResult(d);
      });
    }
  }, [status, runId]);

  const handleDemo = async () => {
    setStatus("STARTED");
    setLogs([]);
    setRunData({});
    setFullResult({});
    setActiveTab("live");
    try {
      const res = await startDemo();
      setRunId(res.run_id);
    } catch {
      setStatus("ERROR");
    }
  };

  const isComplete = status === "COMPLETE";

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans">
      {/* ── Header ── */}
      <header className="fixed top-0 w-full border-b border-white/10 bg-black/60 backdrop-blur-xl z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">FinClosePilot</h1>
            <span className="ml-1 px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-medium border border-indigo-500/20">
              India Edition
            </span>
          </div>
          <div className="flex items-center gap-4">
            {runId && (
              <span className="font-mono text-xs text-neutral-600 hidden md:block">
                {runId.split("-")[0]}
              </span>
            )}
            <span
              className={clsx("w-2 h-2 rounded-full", {
                "bg-neutral-600": status === "IDLE",
                "bg-amber-400 animate-pulse": status === "RUNNING" || status === "STARTED",
                "bg-emerald-400": status === "COMPLETE",
                "bg-red-400": status === "ERROR",
              })}
            />
            <span className="text-sm text-neutral-500 font-medium">Period: Q3 FY26</span>
          </div>
        </div>
      </header>

      <main className="pt-20 pb-16 px-4 md:px-6 max-w-7xl mx-auto space-y-6">
        {/* ── Hero ── */}
        {status === "IDLE" && (
          <div className="relative rounded-3xl overflow-hidden border border-white/10 bg-gradient-to-b from-neutral-900 to-neutral-950 p-10 md:p-16 text-center mt-8">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />
            <div className="relative z-10 space-y-5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
                🚀 AI-Native Financial Close Automation
              </div>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white via-neutral-200 to-neutral-500">
                AI-Native Financial Close
              </h2>
              <p className="text-neutral-400 max-w-2xl mx-auto text-lg leading-relaxed">
                500 transactions · GST/Bank/Vendor/IC recon · Benford fraud detection · CGST guardrails · GSTR-3B + Audit reports — all in one pipeline.
              </p>
              <div className="pt-6 flex flex-wrap items-center justify-center gap-4">
                <button
                  onClick={handleDemo}
                  className="group inline-flex items-center gap-2 px-8 py-4 bg-white text-black rounded-full font-semibold hover:bg-neutral-200 transition-all shadow-xl shadow-white/5"
                >
                  <Play className="w-5 h-5 fill-black group-hover:scale-110 transition-transform" />
                  Run Demo
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Pipeline UI ── */}
        {status !== "IDLE" && (
          <div className="space-y-6">
            {/* Metrics Bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Metric label="Matched"    value={runData.matched_records ?? "—"} icon={CheckCircle2} color="emerald" />
              <Metric label="Breaks"     value={runData.breaks ?? "—"}           icon={XCircle}      color="red" />
              <Metric label="Anomalies"  value={runData.anomalies ?? "—"}        icon={AlertTriangle} color="amber" />
              <Metric label="Time"       value={runData.time_taken_seconds ? `${Math.round(runData.time_taken_seconds)}s` : "—"} icon={Clock} color="indigo" />
            </div>

            {/* Hard-block banner */}
            {(runData.hard_blocks ?? 0) > 0 && (
              <div className="flex items-center justify-between p-4 rounded-2xl border border-red-500/30 bg-red-500/5">
                <div>
                  <p className="text-red-400 font-semibold text-sm">🚫 {runData.hard_blocks} HARD BLOCK{(runData.hard_blocks ?? 0) > 1 ? "S" : ""} — CGST Act 17(5)</p>
                  <p className="text-xs text-neutral-500 mt-0.5">ITC auto-reversed by guardrails</p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-white">{formatCurrency(runData.total_blocked_inr ?? 0)}</p>
                  <p className="text-xs text-neutral-500">blocked</p>
                </div>
              </div>
            )}

            {/* Tab Navigation */}
            <div className="flex gap-1 bg-black/40 rounded-2xl p-1.5 overflow-x-auto border border-white/5 scrollbar-none">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={clsx(
                    "flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium transition-all whitespace-nowrap shrink-0",
                    activeTab === id
                      ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                      : "text-neutral-500 hover:text-neutral-300 hover:bg-white/5"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </div>

            {/* Tab Panels */}
            <div className="rounded-2xl border border-white/10 bg-neutral-900/50 backdrop-blur-sm overflow-hidden min-h-[400px]">
              <div className="p-5">
                {/* Live Feed */}
                {activeTab === "live" && (
                  <div className="space-y-2 max-h-[500px] overflow-y-auto font-mono text-sm">
                    {logs.length === 0 && (
                      <div className="flex items-center gap-3 text-neutral-500 py-8 justify-center">
                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                        Waiting for pipeline events...
                      </div>
                    )}
                    {logs.map((log, i) => (
                      <div key={i} className="flex gap-3 p-3 rounded-xl bg-black/50 border border-white/5">
                        <span className="text-neutral-600 shrink-0 text-xs mt-0.5">
                          {new Date(log.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                        </span>
                        <div className="flex-1 space-y-0.5 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-indigo-400">{log.event}</span>
                            <ChevronRight className="w-3.5 h-3.5 text-neutral-700" />
                            <span className="text-neutral-300">{log.agent}</span>
                          </div>
                          {log.data && Object.keys(log.data).length > 0 && (
                            <p className="text-neutral-400 text-xs break-words">
                              {typeof log.data.message === "string" ? log.data.message : JSON.stringify(log.data)}
                            </p>
                          )}
                        </div>
                        <div className="shrink-0">
                          {log.status === "DONE" ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                          ) : log.status === "ERROR" ? (
                            <XCircle className="w-4 h-4 text-red-500" />
                          ) : (
                            <div className="w-4 h-4 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
                          )}
                        </div>
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                )}

                {/* Recon */}
                {activeTab === "recon" && (
                  <ReconResults recon={fullResult.recon_results ?? {}} />
                )}

                {/* Anomalies */}
                {activeTab === "anomalies" && (
                  <div className="space-y-6">
                    <AnomalyHeatmap anomalies={fullResult.anomalies ?? {}} />
                    <div>
                      <h4 className="text-sm font-medium text-neutral-400 mb-3">
                        Benford&apos;s Law Digit Distribution
                      </h4>
                      <BenfordChart
                        observed={fullResult.anomalies?.benford?.digit_distribution ?? {}}
                      />
                    </div>
                  </div>
                )}

                {/* Guardrails */}
                {activeTab === "guardrails" && (
                  <GuardrailLog fires={fullResult.guardrail_results?.all_fires ?? []} />
                )}

                {/* Reports */}
                {activeTab === "reports" && (
                  <ReportViewer reports={fullResult.reports ?? {}} runId={runId ?? undefined} />
                )}

                {/* Tax */}
                {activeTab === "tax" && (
                  <TaxOptimiser data={fullResult.tax_opportunities ?? {}} />
                )}

                {/* Audit Query */}
                {activeTab === "audit" && (
                  <AuditQuery runId={runId ?? undefined} />
                )}

                {/* Regulatory */}
                {activeTab === "regulatory" && (
                  <RegMonitor />
                )}
              </div>
            </div>

            {/* Reset button */}
            <div className="flex justify-end">
              <button
                onClick={() => { setStatus("IDLE"); setRunId(null); setLogs([]); setFullResult({}); setRunData({}); }}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-sm text-neutral-400 hover:text-white transition-colors"
              >
                <RefreshCw className="w-4 h-4" /> New Run
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
