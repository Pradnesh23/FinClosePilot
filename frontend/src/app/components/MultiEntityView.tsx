"use client";
import { Building2, CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import clsx from "clsx";
import type { Entity } from "@/lib/types";

const DEMO_ENTITIES: Entity[] = [
  { entity_id: "PARENT", entity_name: "FinCorp India Ltd",     role: "parent",     ownership_pct: 100, status: "COMPLETE",    pct_complete: 100 },
  { entity_id: "SUB1",   entity_name: "FinCorp Tech Pvt Ltd",  role: "subsidiary", ownership_pct: 80,  status: "COMPLETE",    pct_complete: 100 },
  { entity_id: "SUB2",   entity_name: "FinCorp Services Ltd",  role: "subsidiary", ownership_pct: 65,  status: "IN_PROGRESS", pct_complete: 72  },
  { entity_id: "SUB3",   entity_name: "FinCorp Retail Ltd",    role: "subsidiary", ownership_pct: 51,  status: "PENDING",     pct_complete: 0   },
];

const STATUS_ICON: Record<string, any> = {
  COMPLETE:    CheckCircle2,
  IN_PROGRESS: Clock,
  PENDING:     AlertTriangle,
};
const STATUS_COLOR: Record<string, string> = {
  COMPLETE:    "text-emerald-400",
  IN_PROGRESS: "text-amber-400",
  PENDING:     "text-neutral-500",
};

export function MultiEntityView({
  entities = DEMO_ENTITIES,
  eliminationSummary,
}: {
  entities?: Entity[];
  eliminationSummary?: { total_eliminated: number; adjustments: any[] };
}) {
  const parent  = entities.find((e) => e.role === "parent");
  const subs    = entities.filter((e) => e.role === "subsidiary");
  const allDone = entities.every((e) => e.status === "COMPLETE");

  return (
    <div className="space-y-5">
      {/* Group Overview */}
      <div className="flex items-center justify-between p-4 rounded-xl bg-gradient-to-r from-indigo-500/10 to-purple-500/5 border border-indigo-500/20">
        <div className="flex items-center gap-3">
          <Building2 className="w-6 h-6 text-indigo-400" />
          <div>
            <p className="font-semibold text-white">{parent?.entity_name ?? "Group Close"}</p>
            <p className="text-xs text-neutral-500">IndAS 110 Consolidation</p>
          </div>
        </div>
        <span
          className={clsx(
            "px-3 py-1 rounded-full text-xs font-medium",
            allDone
              ? "bg-emerald-500/15 text-emerald-400"
              : "bg-amber-500/15 text-amber-400"
          )}
        >
          {allDone ? "✅ Consolidated" : "⏳ In Progress"}
        </span>
      </div>

      {/* Entity Cards */}
      <div className="space-y-2">
        {entities.map((entity) => {
          const Icon = STATUS_ICON[entity.status ?? "PENDING"] ?? Clock;
          const color = STATUS_COLOR[entity.status ?? "PENDING"];
          return (
            <div
              key={entity.entity_id}
              className="flex items-center gap-4 p-4 rounded-xl border border-white/5 bg-neutral-900/50"
            >
              <div className={clsx("shrink-0", color)}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-white truncate">{entity.entity_name}</p>
                  <span className="text-xs text-neutral-600 shrink-0">
                    {entity.ownership_pct}% held
                  </span>
                </div>
                {entity.status === "IN_PROGRESS" && (
                  <div className="mt-1.5 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-500 rounded-full transition-all"
                      style={{ width: `${entity.pct_complete ?? 0}%` }}
                    />
                  </div>
                )}
              </div>
              <span className={clsx("text-xs font-medium shrink-0", color)}>
                {entity.status?.replace("_", " ")}
              </span>
            </div>
          );
        })}
      </div>

      {/* Elimination Summary */}
      {eliminationSummary && (
        <div className="p-4 rounded-xl bg-purple-500/5 border border-purple-500/20 space-y-2">
          <p className="text-xs font-medium text-purple-400 uppercase tracking-wider">
            Intercompany Eliminations (IndAS 110)
          </p>
          <p className="text-2xl font-bold text-white">
            ₹{(eliminationSummary.total_eliminated / 1e7).toFixed(2)} Cr
          </p>
          <p className="text-xs text-neutral-500">unrealised profit eliminated</p>
        </div>
      )}
    </div>
  );
}
