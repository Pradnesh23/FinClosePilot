"use client";
import { useState, useEffect } from "react";
import clsx from "clsx";
import { API_BASE } from "@/lib/api";
import {
  AlertTriangle, ShieldAlert, Scale, CheckCircle2, Clock,
  ChevronDown, ChevronUp, ExternalLink, User, Gavel,
} from "lucide-react";

type Escalation = {
  id: number;
  run_id: string;
  agent_type: string;
  reason_code: string;
  escalation_level: string;
  confidence: number;
  threshold: number;
  item_json: string;
  resolved: boolean;
  resolved_by?: string;
  created_at: string;
};

const LEVEL_STYLES: Record<string, { color: string; bg: string; icon: any }> = {
  CFO:          { color: "text-red-400",    bg: "bg-red-500/10 border-red-500/20",    icon: ShieldAlert },
  LEGAL:        { color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20", icon: Gavel },
  HUMAN_REVIEW: { color: "text-amber-400",  bg: "bg-amber-500/10 border-amber-500/20", icon: User },
  AUTO_PROCEED: { color: "text-emerald-400",bg: "bg-emerald-500/10 border-emerald-500/20", icon: CheckCircle2 },
};

function ConfidenceBadge({ confidence, threshold }: { confidence: number; threshold: number }) {
  const pct = Math.round(confidence * 100);
  const gap = Math.round((threshold - confidence) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-500",
            pct >= 90 ? "bg-emerald-500" : pct >= 75 ? "bg-amber-500" : "bg-red-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-neutral-500">{pct}%</span>
      {gap > 0 && (
        <span className="text-[10px] text-red-400/80">−{gap}% below threshold</span>
      )}
    </div>
  );
}

export function EscalationPanel({ runId }: { runId: string }) {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [resolving, setResolving] = useState<number | null>(null);
  const [filter, setFilter] = useState<"all" | "unresolved">("unresolved");

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    const url = filter === "unresolved"
      ? `${API_BASE}/escalations/${runId}?resolved=false`
      : `${API_BASE}/escalations/${runId}`;
    fetch(url)
      .then((r) => r.json())
      .then((d) => setEscalations(d.escalations ?? []))
      .catch(() => setEscalations([]))
      .finally(() => setLoading(false));
  }, [runId, filter]);

  async function handleResolve(id: number) {
    setResolving(id);
    try {
      await fetch(`${API_BASE}/escalations/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ escalation_id: id, resolved_by: "CFO", resolution_notes: "Reviewed and approved" }),
      });
      setEscalations((prev) => prev.filter((e) => e.id !== id));
    } catch {
      // noop
    } finally {
      setResolving(null);
    }
  }

  const byLevel = escalations.reduce<Record<string, number>>((acc, e) => {
    acc[e.escalation_level] = (acc[e.escalation_level] || 0) + 1;
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="animate-pulse space-y-3 p-4">
        <div className="h-4 w-40 bg-neutral-800 rounded" />
        <div className="h-20 bg-neutral-800/50 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span className="text-sm font-semibold text-white">Escalation Queue</span>
          {escalations.length > 0 && (
            <span className="ml-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {escalations.length}
            </span>
          )}
        </div>
        <div className="flex gap-1 text-[11px]">
          {(["unresolved", "all"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                "px-2.5 py-1 rounded-md capitalize transition-colors",
                filter === f ? "bg-white/10 text-white" : "text-neutral-500 hover:text-neutral-300"
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Level Summary */}
      {Object.keys(byLevel).length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {Object.entries(byLevel).map(([level, count]) => {
            const style = LEVEL_STYLES[level] || LEVEL_STYLES.HUMAN_REVIEW;
            const Icon = style.icon;
            return (
              <div
                key={level}
                className={clsx("flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border", style.bg)}
              >
                <Icon className={clsx("w-3 h-3", style.color)} />
                <span className={clsx("font-semibold", style.color)}>{count}</span>
                <span className="text-neutral-500">{level.replace("_", " ")}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Escalation List */}
      {escalations.length === 0 ? (
        <div className="text-center py-8 text-neutral-600 text-sm">
          <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/30" />
          No pending escalations
        </div>
      ) : (
        <div className="space-y-2">
          {escalations.map((esc) => {
            const style = LEVEL_STYLES[esc.escalation_level] || LEVEL_STYLES.HUMAN_REVIEW;
            const Icon = style.icon;
            const expanded = expandedId === esc.id;
            let itemData: Record<string, any> = {};
            try { itemData = JSON.parse(esc.item_json); } catch {}

            return (
              <div
                key={esc.id}
                className={clsx(
                  "rounded-xl border transition-all",
                  expanded ? "bg-neutral-900/80 border-white/10" : "bg-black/20 border-white/5 hover:border-white/10"
                )}
              >
                <button
                  className="w-full flex items-center gap-3 px-4 py-3 text-left"
                  onClick={() => setExpandedId(expanded ? null : esc.id)}
                >
                  <Icon className={clsx("w-4 h-4 shrink-0", style.color)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-white truncate">
                        {esc.reason_code.replace(/_/g, " ")}
                      </span>
                      <span className={clsx("px-1.5 py-0.5 rounded text-[9px] font-bold", style.bg, style.color)}>
                        {esc.escalation_level.replace("_", " ")}
                      </span>
                    </div>
                    <ConfidenceBadge confidence={esc.confidence} threshold={esc.threshold} />
                  </div>
                  {expanded ? <ChevronUp className="w-4 h-4 text-neutral-500" /> : <ChevronDown className="w-4 h-4 text-neutral-500" />}
                </button>

                {expanded && (
                  <div className="px-4 pb-4 space-y-3 border-t border-white/5 pt-3">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div><span className="text-neutral-500">Agent: </span><span className="text-white">{esc.agent_type}</span></div>
                      <div><span className="text-neutral-500">Time: </span><span className="text-white">{new Date(esc.created_at).toLocaleTimeString()}</span></div>
                      {itemData.vendor_name && (
                        <div><span className="text-neutral-500">Vendor: </span><span className="text-white">{itemData.vendor_name}</span></div>
                      )}
                      {itemData.amount_inr && (
                        <div><span className="text-neutral-500">Amount: </span><span className="text-white">₹{Number(itemData.amount_inr).toLocaleString("en-IN")}</span></div>
                      )}
                    </div>
                    {itemData.reasoning && (
                      <p className="text-xs text-neutral-400 italic">&ldquo;{itemData.reasoning}&rdquo;</p>
                    )}
                    <button
                      onClick={() => handleResolve(esc.id)}
                      disabled={resolving === esc.id}
                      className={clsx(
                        "w-full py-2 rounded-lg text-xs font-bold transition-all",
                        resolving === esc.id
                          ? "bg-neutral-800 text-neutral-500 cursor-wait"
                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20"
                      )}
                    >
                      {resolving === esc.id ? "Resolving..." : "✓ Mark as Reviewed & Approved"}
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
