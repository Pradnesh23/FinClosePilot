"use client";
import { useState, useEffect } from "react";
import clsx from "clsx";
import { API_BASE } from "@/lib/api";
import { Cpu, Zap, TrendingDown, DollarSign, Activity } from "lucide-react";

type RoutingStats = {
  calls_by_model: Record<string, number>;
  python_only_calls: number;
  estimated_cost_usd: number;
  estimated_cost_if_all_pro: number;
  cost_savings_pct: number;
  routing_summary: string;
};

const MODEL_COLORS: Record<string, { bar: string; text: string; label: string }> = {
  "gemini-1.5-flash": { bar: "bg-emerald-500", text: "text-emerald-400", label: "Flash 1.5" },
  "gemini-2.0-flash":  { bar: "bg-blue-500",    text: "text-blue-400",    label: "Flash 2.0" },
  "gemini-1.5-pro":    { bar: "bg-purple-500",   text: "text-purple-400",  label: "Pro 1.5" },
  "PYTHON_ONLY":       { bar: "bg-amber-500",    text: "text-amber-400",   label: "Pure Python" },
};

function SavingsGauge({ pct }: { pct: number }) {
  const clamped = Math.max(0, Math.min(100, pct));
  const color = clamped >= 90 ? "text-emerald-400" : clamped >= 60 ? "text-blue-400" : "text-amber-400";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-neutral-800" />
          <circle
            cx="18" cy="18" r="15.5" fill="none" strokeWidth="2.5"
            strokeDasharray={`${clamped} ${100 - clamped}`}
            strokeLinecap="round"
            className={clsx(
              "transition-all duration-1000",
              clamped >= 90 ? "stroke-emerald-500" : clamped >= 60 ? "stroke-blue-500" : "stroke-amber-500"
            )}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={clsx("text-xl font-bold", color)}>{clamped}%</span>
        </div>
      </div>
      <span className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider">Cost Saved</span>
    </div>
  );
}

export function CostEfficiency({ runId }: { runId: string }) {
  const [stats, setStats] = useState<RoutingStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    fetch(`${API_BASE}/cost-efficiency/${runId}`)
      .then((r) => r.json())
      .then((d) => setStats(d.routing_stats ?? null))
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return (
      <div className="animate-pulse space-y-3 p-4">
        <div className="h-4 w-36 bg-neutral-800 rounded" />
        <div className="h-24 bg-neutral-800/50 rounded-xl" />
      </div>
    );
  }

  if (!stats) return null;

  const totalCalls = Object.values(stats.calls_by_model).reduce((s, v) => s + v, 0);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Cpu className="w-4 h-4 text-blue-400" />
        <span className="text-sm font-semibold text-white">Smart Model Routing</span>
      </div>

      {/* Savings + Cost */}
      <div className="flex items-center gap-6">
        <SavingsGauge pct={stats.cost_savings_pct} />
        <div className="flex-1 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-neutral-500">Actual Cost</span>
            <span className="text-emerald-400 font-semibold">${stats.estimated_cost_usd.toFixed(4)}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-neutral-500">If All Pro</span>
            <span className="text-neutral-400 line-through">${stats.estimated_cost_if_all_pro.toFixed(4)}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-neutral-500">Total Calls</span>
            <span className="text-white font-semibold">{totalCalls}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-neutral-500">Python Only</span>
            <span className="text-amber-400 font-semibold">{stats.python_only_calls} (free)</span>
          </div>
        </div>
      </div>

      {/* Model Distribution Bar */}
      {totalCalls > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] text-neutral-500 font-medium uppercase tracking-wider">Call Distribution</p>
          <div className="h-3 rounded-full overflow-hidden flex bg-neutral-800">
            {Object.entries(stats.calls_by_model).map(([model, count]) => {
              const pct = (count / totalCalls) * 100;
              const style = MODEL_COLORS[model] || { bar: "bg-gray-500", text: "text-gray-400", label: model };
              return (
                <div
                  key={model}
                  className={clsx("h-full transition-all duration-700", style.bar)}
                  style={{ width: `${pct}%` }}
                  title={`${style.label}: ${count} calls (${pct.toFixed(0)}%)`}
                />
              );
            })}
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.calls_by_model).map(([model, count]) => {
              const style = MODEL_COLORS[model] || { bar: "bg-gray-500", text: "text-gray-400", label: model };
              return (
                <div key={model} className="flex items-center gap-1.5 text-[11px]">
                  <div className={clsx("w-2 h-2 rounded-full", style.bar)} />
                  <span className="text-neutral-500">{style.label}</span>
                  <span className={clsx("font-semibold", style.text)}>{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Router Summary */}
      {stats.routing_summary && (
        <p className="text-[11px] text-neutral-500 italic border-t border-white/5 pt-2">
          {stats.routing_summary}
        </p>
      )}
    </div>
  );
}
