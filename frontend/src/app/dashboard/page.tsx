"use client";

import { useState, useEffect, useRef } from "react";
import clsx from "clsx";
import {
  Play, RefreshCw, Zap, BarChart2, Search, FileText,
  IndianRupee, Globe, ShieldCheck, AlertTriangle,
  Brain, Building2, Clock, TrendingUp, Upload, Database,
} from "lucide-react";
import { startDemo, getRun, WS_BASE } from "@/lib/api";
import { CloseDashboard }   from "@/app/components/CloseDashboard";
import { AgentFeed }        from "@/app/components/AgentFeed";
import { GuardrailLog }     from "@/app/components/GuardrailLog";
import { BenfordChart }     from "@/app/components/BenfordChart";
import { AnomalyHeatmap }   from "@/app/components/AnomalyHeatmap";
import { ReconResults }     from "@/app/components/ReconResults";
import { ReportViewer }     from "@/app/components/ReportViewer";
import { AuditQuery }       from "@/app/components/AuditQuery";
import { TaxOptimiser }     from "@/app/components/TaxOptimiser";
import { RegMonitor }       from "@/app/components/RegMonitor";
import { LearningChart }    from "@/app/components/LearningChart";
import { PredictiveClose }  from "@/app/components/PredictiveClose";
import { MultiEntityView }  from "@/app/components/MultiEntityView";
import { Form26AS }         from "@/app/components/Form26AS";
import { EscalationPanel }  from "@/app/components/EscalationPanel";
import { CostEfficiency }   from "@/app/components/CostEfficiency";
import { FileUploadModal }    from "@/app/components/FileUploadModal";
import { PipelineProgress }   from "@/app/components/PipelineProgress";
import { DatasetViewer }      from "@/app/components/DatasetViewer";
import type { WsEvent }       from "@/lib/types";

type Tab = {
  id: string;
  label: string;
  icon: any;
};

const TABS: Tab[] = [
  { id: "feed",       label: "Live Feed",    icon: Zap },
  { id: "recon",      label: "Recon",        icon: BarChart2 },
  { id: "anomalies",  label: "Anomalies",    icon: AlertTriangle },
  { id: "guardrails", label: "Guardrails",   icon: ShieldCheck },
  { id: "escalations",label: "Escalations",  icon: AlertTriangle },
  { id: "cost",       label: "Cost",         icon: TrendingUp },
  { id: "reports",    label: "Reports",      icon: FileText },
  { id: "tax",        label: "Tax",          icon: IndianRupee },
  { id: "audit",      label: "Audit Query",  icon: Search },
  { id: "regulatory", label: "Reg Monitor",  icon: Globe },
  { id: "learning",   label: "Learning",     icon: Brain },
  { id: "predict",    label: "Predictive",   icon: Clock },
  { id: "entities",   label: "Entities",     icon: Building2 },
  { id: "form26as",   label: "Form 26AS",    icon: FileText },
  { id: "datasets",   label: "Datasets",     icon: Database },
];

type PipelineStatus = "IDLE" | "STARTED" | "RUNNING" | "COMPLETE" | "ERROR";

export default function DashboardPage() {
  const [status, setStatus]       = useState<PipelineStatus>("IDLE");
  const [runId, setRunId]         = useState<string | null>(null);
  const [logs, setLogs]           = useState<WsEvent[]>([]);
  const [runData, setRunData]     = useState<any>({});
  const [fullResult, setFullResult] = useState<any>({});
  const [activeTab, setActiveTab]   = useState("feed");
  const [showUpload, setShowUpload] = useState(false);

  // WebSocket connection
  useEffect(() => {
    if (!runId) return;
    const ws = new WebSocket(`${WS_BASE}/${runId}`);
    ws.onmessage = ({ data }) => {
      try {
        const msg: WsEvent = JSON.parse(data);
        if (msg.event === "CONNECTED" || msg.event === "PING") return;
        setLogs((p) => [...p, msg]);
        setStatus(
          msg.event === "COMPLETE" || msg.event === "COMPLETE_WITH_ESCALATIONS"
            ? "COMPLETE"
            : "RUNNING"
        );
      } catch {}
    };
    ws.onerror = () => setStatus("ERROR");
    return () => ws.close();
  }, [runId]);

  // Fetch full result on complete
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
    setActiveTab("feed");
    try {
      const res = await startDemo();
      setRunId(res.run_id);
    } catch {
      setStatus("ERROR");
    }
  };

  const handleReset = () => {
    setStatus("IDLE");
    setRunId(null);
    setLogs([]);
    setRunData({});
    setFullResult({});
  };

  const handleUploadStart = (newRunId: string) => {
    setShowUpload(false);
    setStatus("STARTED");
    setLogs([]);
    setRunData({});
    setFullResult({});
    setActiveTab("feed");
    setRunId(newRunId);
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans flex flex-col">
      {/* Header */}
      <header className="shrink-0 border-b border-white/10 bg-black/60 backdrop-blur-xl">
        <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold text-white">FinClosePilot</span>
            <span className="text-neutral-600">/</span>
            <span className="text-neutral-400 text-sm">Dashboard</span>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={clsx("w-2 h-2 rounded-full", {
                "bg-neutral-700":               status === "IDLE",
                "bg-amber-400 animate-pulse":   status === "RUNNING" || status === "STARTED",
                "bg-emerald-400":               status === "COMPLETE",
                "bg-red-400":                   status === "ERROR",
              })}
            />
            {status === "IDLE" ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowUpload(true)}
                  className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg text-sm font-semibold hover:brightness-110 transition-all shadow-lg shadow-indigo-500/20"
                >
                  <Upload className="w-4 h-4" /> Upload Files
                </button>
                <button
                  onClick={handleDemo}
                  className="flex items-center gap-2 px-4 py-1.5 bg-white text-black rounded-lg text-sm font-semibold hover:bg-neutral-200 transition-colors"
                >
                  <Play className="w-4 h-4 fill-black" /> Run Demo
                </button>
              </div>
            ) : (
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-4 py-1.5 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-sm text-neutral-300 transition-colors"
              >
                <RefreshCw className="w-4 h-4" /> New Run
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden max-w-[1600px] mx-auto w-full">
        {/* Left Sidebar — CloseDashboard */}
        <aside className="w-72 shrink-0 border-r border-white/5 bg-neutral-900/30 overflow-y-auto p-4 space-y-6">
          <CloseDashboard
            run={{
              ...runData,
              status: status === "IDLE" ? undefined : status,
              period: runData.period ?? "Q3 FY26",
            }}
            guardrailBreakdown={fullResult.guardrail_results?.breakdown}
          />
          {/* Phase 2: Sidebar cost + escalation summaries */}
          {runId && status === "COMPLETE" && (
            <>
              <div className="border-t border-white/5 pt-4">
                <CostEfficiency runId={runId} />
              </div>
              <div className="border-t border-white/5 pt-4">
                <EscalationPanel runId={runId} />
              </div>
            </>
          )}
          {/* Pipeline Progress — always visible during run */}
          {status !== "IDLE" && (
            <div className="border-t border-white/5 pt-4">
              <PipelineProgress logs={logs} pipelineStatus={status} />
            </div>
          )}
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Tab Bar */}
          <div className="shrink-0 border-b border-white/5 bg-black/20 px-4">
            <div className="flex gap-0.5 overflow-x-auto scrollbar-none py-2">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={clsx(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap shrink-0",
                    activeTab === id
                      ? "bg-indigo-600 text-white"
                      : "text-neutral-500 hover:text-neutral-300 hover:bg-white/5"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Panel */}
          <div className="flex-1 overflow-y-auto p-5">
            {activeTab === "feed" && (
              <AgentFeed logs={logs} />
            )}
            {activeTab === "recon" && (
              <ReconResults recon={fullResult.recon_results ?? {}} />
            )}
            {activeTab === "anomalies" && (
              <div className="space-y-6">
                <AnomalyHeatmap anomalies={fullResult.anomalies ?? {}} />
                <div className="rounded-xl border border-white/10 bg-neutral-900/50 p-5">
                  <h4 className="text-sm font-medium text-neutral-400 mb-4">
                    Benford&apos;s Law Digit Distribution
                  </h4>
                  <BenfordChart observed={fullResult.anomalies?.benford?.digit_distribution ?? {}} />
                </div>
              </div>
            )}
            {activeTab === "guardrails" && (
              <GuardrailLog fires={fullResult.guardrail_results?.all_fires ?? []} runId={runId ?? undefined} />
            )}
            {activeTab === "reports" && (
              <ReportViewer reports={fullResult.reports ?? {}} runId={runId ?? undefined} />
            )}
            {activeTab === "tax" && (
              <TaxOptimiser data={fullResult.tax_opportunities ?? {}} />
            )}
            {activeTab === "audit" && (
              <AuditQuery runId={runId ?? undefined} />
            )}
            {activeTab === "regulatory" && (
              <RegMonitor />
            )}
            {activeTab === "learning" && (
              <LearningChart />
            )}
            {activeTab === "predict" && (
              <PredictiveClose prediction={fullResult.prediction} />
            )}
            {activeTab === "entities" && (
              <MultiEntityView
                eliminationSummary={fullResult.intercompany_eliminations}
              />
            )}
            {activeTab === "form26as" && (
              <Form26AS result={fullResult.form26as} />
            )}
            {activeTab === "escalations" && runId && (
              <div className="rounded-xl border border-white/10 bg-neutral-900/50 p-5">
                <EscalationPanel runId={runId} />
              </div>
            )}
            {activeTab === "cost" && runId && (
              <div className="rounded-xl border border-white/10 bg-neutral-900/50 p-5">
                <CostEfficiency runId={runId} />
              </div>
            )}
            {activeTab === "datasets" && (
              <DatasetViewer />
            )}
          </div>
        </main>
      </div>

      {/* File Upload Modal */}
      <FileUploadModal
        open={showUpload}
        onClose={() => setShowUpload(false)}
        onStart={handleUploadStart}
      />
    </div>
  );
}
