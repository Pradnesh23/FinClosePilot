"use client";
import { useState } from "react";
import { RefreshCw, Loader2, Globe, AlertCircle } from "lucide-react";
import { getRegulatoryUpdates, triggerRegulatoryCheck } from "@/lib/api";
import clsx from "clsx";

type RegulatoryChange = {
  id?: number;
  framework: string;
  notification_no?: string;
  summary?: string;
  what_changed?: string;
  effective_date?: string;
  urgency?: string;
  source_url?: string;
  action_required?: string;
};

const URGENCY_STYLE: Record<string, string> = {
  HIGH:   "bg-red-500/15 text-red-400 border-red-500/30",
  MEDIUM: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  LOW:    "bg-blue-500/10 text-blue-400 border-blue-500/30",
};

const FW_COLORS: Record<string, string> = {
  GST: "text-emerald-400", SEBI: "text-blue-400",
  RBI: "text-purple-400", IndAS: "text-amber-400", IncomeTax: "text-red-400",
};

export function RegMonitor({ initialChanges = [] }: { initialChanges?: RegulatoryChange[] }) {
  const [changes, setChanges] = useState<RegulatoryChange[]>(initialChanges);
  const [loading, setLoading] = useState(false);
  const [triggered, setTriggered] = useState(false);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const data = await getRegulatoryUpdates();
      setChanges(data.changes ?? []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleTrigger = async () => {
    setLoading(true);
    setTriggered(false);
    try {
      await triggerRegulatoryCheck();
      setTriggered(true);
      setTimeout(handleRefresh, 3000);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-neutral-500 flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5" /> Monitor runs every 6 hours (CBIC + SEBI)
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-xs text-neutral-400 hover:text-white transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Refresh
          </button>
          <button
            onClick={handleTrigger}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-xs font-medium disabled:opacity-50 transition-colors"
          >
            Force Check
          </button>
        </div>
      </div>

      {triggered && (
        <p className="text-xs text-emerald-400 bg-emerald-500/10 rounded-lg px-3 py-2">
          ✅ Regulatory monitor triggered. Results update in a few seconds...
        </p>
      )}

      {changes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-neutral-600 gap-3">
          <Globe className="w-8 h-8 opacity-30" />
          <p className="text-sm">No regulatory changes found yet. Trigger a check to fetch latest.</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {changes.map((c, i) => (
            <div
              key={i}
              className={clsx(
                "p-4 rounded-xl border space-y-2",
                URGENCY_STYLE[c.urgency ?? "LOW"] ?? URGENCY_STYLE.LOW
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className={clsx("text-xs font-bold", FW_COLORS[c.framework] ?? "text-neutral-400")}>
                  {c.framework}
                </span>
                {c.urgency === "HIGH" && (
                  <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">
                    <AlertCircle className="w-3 h-3" /> High Urgency
                  </span>
                )}
              </div>
              {c.notification_no && (
                <p className="text-xs font-mono text-neutral-400">{c.notification_no}</p>
              )}
              <p className="text-sm text-white/90">{c.summary ?? c.what_changed}</p>
              {c.action_required && (
                <p className="text-xs text-indigo-300 bg-indigo-500/10 rounded px-2 py-1">
                  📌 {c.action_required}
                </p>
              )}
              {c.effective_date && (
                <p className="text-xs text-neutral-500">Effective: {c.effective_date}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
