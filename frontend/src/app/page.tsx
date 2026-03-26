"use client";

import { useState, useEffect, useRef } from "react";
import clsx from "clsx";
import {
  Play, CheckCircle2, AlertTriangle, XCircle, Clock, ShieldCheck,
  Zap, BarChart2, Search, FileText, IndianRupee, Globe, Upload,
  RefreshCw, ChevronRight, ChevronLeft, Database, Users, History,
} from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { startDemo, getRun, WS_BASE, getAllRuns, getTeamRuns, getTeamDatasets, getDatasets } from "@/lib/api";
import { useAuth } from "./components/AuthContext";
import { AuthPage } from "./components/AuthPage";
import { Loader2, LogOut, User as UserIcon } from "lucide-react";

import { PipelineProgress }   from "./components/PipelineProgress";
import { DatasetViewer }      from "./components/DatasetViewer";
import { LandingPage }        from "./components/LandingPage";
import { GuardrailLog }     from "./components/GuardrailLog";
import { BenfordChart }     from "./components/BenfordChart";
import { AnomalyHeatmap }   from "./components/AnomalyHeatmap";
import { ReconResults }     from "./components/ReconResults";
import { ReportViewer }     from "./components/ReportViewer";
import { AuditQuery }       from "./components/AuditQuery";
import { TaxOptimiser }       from "./components/TaxOptimiser";
import { RegMonitor }         from "./components/RegMonitor";
import { FileUploadModal }    from "./components/FileUploadModal";

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

type Tab = "live" | "recon" | "anomalies" | "guardrails" | "reports" | "tax" | "audit" | "regulatory" | "datasets" | "team" | "history";

const TABS: { id: Tab; label: string; icon: any }[] = [
  { id: "live",       label: "Live Feed",    icon: Zap },
  { id: "recon",      label: "Recon",        icon: CheckCircle2 },
  { id: "anomalies",  label: "Anomalies",    icon: AlertTriangle },
  { id: "guardrails", label: "Guardrails",   icon: ShieldCheck },
  { id: "reports",    label: "Reports",      icon: FileText },
  { id: "tax",        label: "Tax",          icon: IndianRupee },
  { id: "audit",      label: "Audit Query",  icon: Search },
  { id: "regulatory", label: "Reg Monitor",  icon: Globe },
  { id: "datasets",   label: "Datasets",     icon: Database },
];

const MANAGER_TABS = [
  { id: "team", label: "Team Oversight", icon: Users },
];

// ─── Team View Component ────────────────────────────────────────────────────
function TeamOverview({ onSelectRun }: { onSelectRun: (runId: string) => void }) {
  const [runs, setRuns] = useState<any[]>([]);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getTeamRuns(), getTeamDatasets()]).then(([r, d]) => {
      setRuns(r);
      setDatasets(d);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="p-8 text-center text-neutral-500 animate-pulse">Loading team data...</div>;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-indigo-400" />
          Recent Team Runs
        </h3>
        <div className="overflow-hidden rounded-2xl border border-white/5 bg-black/20">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-neutral-400 font-medium">
              <tr>
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Run ID</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Period</th>
                <th className="px-4 py-3">Performance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {runs.map((r) => (
                <tr 
                  key={r.run_id} 
                  onClick={() => onSelectRun(r.run_id)}
                  className="hover:bg-indigo-500/10 transition-colors cursor-pointer group"
                >
                  <td className="px-4 py-3 font-medium text-indigo-300 group-hover:text-indigo-200">{r.employee_name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-neutral-500">{r.run_id?.slice(0,8)}...</td>
                  <td className="px-4 py-3">
                    <span className={clsx("px-2 py-0.5 rounded-full text-[10px] font-bold uppercase",
                      r.status === 'COMPLETE' ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400")}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-neutral-400">{r.period}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-4">
                      <span className="text-emerald-400">✓ {r.matched_records}</span>
                      <span className="text-red-400">✗ {r.breaks}</span>
                    </div>
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-neutral-500 italic">No recent runs from team members.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-purple-400" />
          Team Datasets Oversight
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {datasets.map((d, i) => (
            <div key={i} className="p-4 rounded-2xl border border-white/5 bg-black/20 group hover:border-purple-500/30 transition-all hover:shadow-lg hover:shadow-purple-500/5">
              <div className="flex justify-between items-start mb-2">
                <p className="text-sm font-semibold truncate flex-1">{d.name}</p>
                <div className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 text-[10px] font-bold">
                  {d.employee}
                </div>
              </div>
              <p className="text-[10px] text-neutral-500 mb-2">Used in run: {d.run_id?.slice(0,8) || 'N/A'}</p>
              <div className="flex items-center gap-1.5 text-[10px] text-neutral-600">
                <Clock className="w-3 h-3" />
                {new Date(d.timestamp).toLocaleDateString()}
              </div>
            </div>
          ))}
          {datasets.length === 0 && (
            <div className="col-span-full p-8 text-center text-neutral-500 border border-dashed border-white/10 rounded-2xl">
              No datasets indexed from team runs yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── User History Component ─────────────────────────────────────────────────
function UserHistory({ onSelectRun }: { onSelectRun: (runId: string) => void }) {
  const [runs, setRuns] = useState<any[]>([]);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAllRuns(), getDatasets()]).then(([r, d]) => {
      setRuns(Array.isArray(r.runs) ? r.runs : []);
      setDatasets(Array.isArray(d.datasets) ? d.datasets : []);
      setLoading(false);
    }).catch(() => {
      setRuns([]);
      setDatasets([]);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="p-8 text-center text-neutral-500 animate-pulse">Loading your history...</div>;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <History className="w-5 h-5 text-indigo-400" />
          My Recent Runs
        </h3>
        <div className="overflow-hidden rounded-2xl border border-white/5 bg-black/20">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-neutral-400 font-medium">
              <tr>
                <th className="px-4 py-3">Run ID</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Period</th>
                <th className="px-4 py-3">Performance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {runs.map((r) => (
                <tr 
                  key={r.run_id} 
                  onClick={() => onSelectRun(r.run_id)}
                  className="hover:bg-indigo-500/10 transition-colors cursor-pointer group"
                >
                  <td className="px-4 py-3 font-mono text-xs text-indigo-300 group-hover:text-indigo-200">{r.run_id?.slice(0,8)}...</td>
                  <td className="px-4 py-3">
                    <span className={clsx("px-2 py-0.5 rounded-full text-[10px] font-bold uppercase",
                      r.status === 'COMPLETE' ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400")}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-neutral-400">{r.period}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-4">
                      <span className="text-emerald-400">✓ {r.matched_records || 0}</span>
                      <span className="text-red-400">✗ {r.breaks || 0}</span>
                    </div>
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-neutral-500 italic">No previous runs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-purple-400" />
          My Uploaded Datasets
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {datasets.map((d, i) => (
            <div key={i} className="p-4 rounded-2xl border border-white/5 bg-black/20 group hover:border-purple-500/30 transition-all hover:shadow-lg hover:shadow-purple-500/5">
              <div className="flex justify-between items-start mb-2">
                <p className="text-sm font-semibold truncate flex-1">{d.name}</p>
                <div className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-[10px] font-bold">
                  {d.timestamp ? new Date(d.timestamp).toLocaleDateString() : 'N/A'}
                </div>
              </div>
              <p className="text-[10px] text-neutral-500 mb-2">Source Run: {d.run_id?.slice(0,8) || 'N/A'}</p>
              <div className="flex items-center gap-1.5 text-[10px] text-neutral-600">
                <FileText className="w-3 h-3" />
                {d.rows || 0} records
              </div>
            </div>
          ))}
          {datasets.length === 0 && (
            <div className="col-span-full p-8 text-center text-neutral-500 border border-dashed border-white/10 rounded-2xl">
              No previous datasets found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

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
  const { user, loading, logout } = useAuth();
  const [status, setStatus]     = useState<PipelineStatus>("IDLE");
  const [runId, setRunId]       = useState<string | null>(null);
  const [logs, setLogs]         = useState<any[]>([]);
  const [runData, setRunData]   = useState<Partial<RunData>>({});
  const [fullResult, setFullResult] = useState<any>({});
  const [activeTab, setActiveTab]   = useState<Tab>(user?.role === "MANAGER" ? "team" : "live");
  const [showUpload, setShowUpload] = useState(false);
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
      
      // Merge real-time metrics into runData
      if (msg.data) {
        setRunData((p) => ({
          ...p,
          matched_records:    msg.data.matched    ?? p.matched_records,
          breaks:             msg.data.breaks     ?? p.breaks,
          anomalies:          msg.data.anomalies  ?? p.anomalies,
          guardrail_fires:    msg.data.fires      ?? p.guardrail_fires,
          hard_blocks:        msg.data.hard_blocks ?? p.hard_blocks,
          total_blocked_inr:  msg.data.blocked_inr ?? p.total_blocked_inr,
        }));
      }

      if (msg.event.startsWith("COMPLETE")) {
        setStatus(msg.event);
      } else {
        setStatus("RUNNING");
      }
    };
    ws.onerror = () => setStatus("ERROR");
    return () => ws.close();
  }, [runId]);

  // Fetch full run result when pipeline completes
  useEffect(() => {
    if (status?.startsWith("COMPLETE") && runId) {
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

  const isComplete = status?.startsWith("COMPLETE");

  const handleUploadStart = (newRunId: string) => {
    setShowUpload(false);
    setStatus("STARTED");
    setLogs([]);
    setRunData({});
    setFullResult({});
    setActiveTab("live");
    setRunId(newRunId);
  };

  const handleBackToStart = () => {
    setStatus("IDLE");
    setRunId(null);
    setLogs([]);
    setFullResult({});
    setRunData({});
    setActiveTab('live'); // Always return to Home (Hero/Upload)
  };

  const handleSelectTeamRun = (newRunId: string) => {
    setRunId(newRunId);
    setStatus("COMPLETE"); // Force status to complete to show panels
    setActiveTab("recon");  // Jump to recon details
    setLogs([]);            // History logs not loaded via socket for old runs currently
  };

  const [view, setView] = useState<"landing" | "auth" | "dashboard">("landing");

  useEffect(() => {
    if (user) setView("dashboard");
    else if (view === "dashboard") setView("landing");
  }, [user, view]);

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (view === "landing" && !user) {
    return <LandingPage onGetStarted={() => setView("auth")} />;
  }

  if (view === "auth" && !user) {
    return (
      <div className="relative">
        <button 
          onClick={() => setView("landing")}
          className="absolute top-8 left-8 z-50 px-4 py-2 rounded-full border border-white/10 bg-white/5 text-xs text-neutral-400 hover:text-white transition-colors flex items-center gap-2"
        >
          ← Back to Home
        </button>
        <AuthPage />
      </div>
    );
  }

  // Dashboard view (only if user exists)
  if (!user) return <LandingPage onGetStarted={() => setView("auth")} />;

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
            {user.role === "MANAGER" && (
              <button 
                onClick={() => setActiveTab("team")}
                className={clsx(
                  "hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl border transition-all",
                  activeTab === "team"
                    ? "border-purple-500/30 bg-purple-500/10 text-purple-400"
                    : "border-white/5 bg-white/5 text-neutral-400 hover:text-white"
                )}
              >
                <Users className="w-3.5 h-3.5" />
                <span className="text-xs font-semibold">Team Oversight</span>
              </button>
            )}

            <button 
              onClick={() => setActiveTab("history")}
              className={clsx(
                "hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl border transition-all",
                activeTab === "history"
                  ? "border-indigo-500/30 bg-indigo-500/10 text-indigo-400"
                  : "border-white/5 bg-white/5 text-neutral-400 hover:text-white"
              )}
            >
              <History className="w-3.5 h-3.5" />
              <span className="text-xs font-semibold">My History</span>
            </button>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/5 bg-white/5">
              <div className={clsx("w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold", 
                user.role === "MANAGER" ? "bg-purple-500/20 text-purple-400" : "bg-blue-500/20 text-blue-400")}>
                {user.username[0].toUpperCase()}
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-semibold leading-none">{user.username}</p>
                <p className="text-[10px] text-neutral-500 leading-none mt-1">{user.role}</p>
              </div>
              <button 
                onClick={logout}
                className="ml-2 p-1 hover:bg-white/10 rounded-md text-neutral-500 hover:text-red-400 transition-colors"
                title="Logout"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
            <span
              className={clsx("w-2 h-2 rounded-full", {
                "bg-neutral-600": status === "IDLE",
                "bg-amber-400 animate-pulse": status === "RUNNING" || status === "STARTED",
                "bg-emerald-400": status === "COMPLETE",
                "bg-red-400": status === "ERROR",
              })}
            />
          </div>
        </div>
      </header>

      <main className="pt-20 pb-16 px-4 md:px-6 max-w-7xl mx-auto space-y-6">
        {/* Contextual Back Button */}
        {(activeTab !== 'live' || status !== 'IDLE') && (
          <button
            onClick={handleBackToStart}
            className="flex items-center gap-2 text-sm text-neutral-500 hover:text-indigo-400 transition-colors mb-2 group w-fit"
          >
            <ChevronLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            Back to Home
          </button>
        )}

        {/* ── Hero (Only in IDLE and not in Oversight/History/Datasets) ── */}
        {status === "IDLE" && activeTab !== 'team' && activeTab !== 'datasets' && activeTab !== 'history' && (
          <div className="relative rounded-3xl overflow-hidden border border-white/10 bg-gradient-to-b from-neutral-900 to-neutral-950 p-10 md:p-16 text-center mt-2">
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
                  onClick={() => setShowUpload(true)}
                  className="group inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-full font-semibold hover:brightness-110 transition-all shadow-xl shadow-indigo-500/20"
                >
                  <Upload className="w-5 h-5 group-hover:scale-110 transition-transform" />
                  Upload Files
                </button>
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

        {/* ── Active Pipeline Info (Only if status not IDLE and NOT in History/Team) ── */}
        {status !== "IDLE" && activeTab !== 'history' && activeTab !== 'team' && (
          <div className="space-y-6">
            <PipelineProgress logs={logs} pipelineStatus={status} />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Metric label="Matched"    value={runData.matched_records ?? "—"} icon={CheckCircle2} color="emerald" />
              <Metric label="Breaks"     value={runData.breaks ?? "—"}           icon={XCircle}      color="red" />
              <Metric label="Anomalies"  value={runData.anomalies ?? "—"}        icon={AlertTriangle} color="amber" />
              <Metric label="Time"       value={runData.time_taken_seconds ? `${Math.round(runData.time_taken_seconds)}s` : "—"} icon={Clock} color="indigo" />
            </div>
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
            <div className="flex gap-1 bg-black/40 rounded-2xl p-1.5 overflow-x-auto border border-white/5 scrollbar-none mt-4">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as Tab)}
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
          </div>
        )}

        {/* ── Tab Panels (Show if Run active OR if specific oversight/history/datasets active) ── */}
        {(status !== "IDLE" || activeTab === 'team' || activeTab === 'datasets' || activeTab === 'history') && (
          <>
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
                  <GuardrailLog fires={fullResult.guardrail_fires ?? []} runId={runId ?? undefined} />
                )}

                {/* Reports */}
                {activeTab === "reports" && (
                  <ReportViewer reports={fullResult.reports ?? {}} runId={runId ?? undefined} />
                )}

                {/* Tax */}
                {activeTab === "tax" && (
                  <TaxOptimiser data={fullResult.reports?.tax_optimiser ?? {}} />
                )}

                {/* Audit Query */}
                {activeTab === "audit" && (
                  <AuditQuery runId={runId ?? undefined} />
                )}

                {/* Regulatory */}
                {activeTab === "regulatory" && (
                  <RegMonitor initialChanges={fullResult.regulatory_updates ?? []} />
                )}


                {/* Datasets */}
                {activeTab === "datasets" && (
                  <DatasetViewer />
                )}

                {/* Personal History */}
                {activeTab === "history" && (
                  <UserHistory onSelectRun={handleSelectTeamRun} />
                )}

                {/* Team Oversight (Manager ONLY) */}
                {activeTab === "team" && user.role === "MANAGER" && (
                  <TeamOverview onSelectRun={handleSelectTeamRun} />
                )}
              </div>
            </div>

            {/* Reset button (Only show if run active) */}
            {status !== "IDLE" && (
              <div className="flex justify-end">
                <button
                  onClick={() => { setStatus("IDLE"); setRunId(null); setLogs([]); setFullResult({}); setRunData({}); }}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-sm text-neutral-400 hover:text-white transition-colors"
                >
                  <RefreshCw className="w-4 h-4" /> New Run
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* File Upload Modal */}
      <FileUploadModal
        open={showUpload}
        onClose={() => setShowUpload(false)}
        onStart={handleUploadStart}
      />
    </div>
  );
}
