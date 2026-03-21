"use client";
import { CheckCircle2, XCircle, Zap, ChevronRight } from "lucide-react";
import { useRef, useEffect } from "react";
import clsx from "clsx";
import type { WsEvent } from "@/lib/types";

export function AgentFeed({ logs = [] }: { logs: WsEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  if (!logs.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-3">
        <Zap className="w-8 h-8 opacity-30" />
        <p className="text-sm">Start a pipeline run to see live agent events here</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
      {logs.map((log, i) => (
        <div key={i} className="flex gap-3 p-3 rounded-xl bg-black/50 border border-white/5 font-mono text-sm">
          <span className="text-neutral-600 shrink-0 text-xs mt-0.5 tabular-nums">
            {new Date(log.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </span>
          <div className="flex-1 space-y-0.5 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-indigo-400 text-xs">{log.event}</span>
              <ChevronRight className="w-3 h-3 text-neutral-700 shrink-0" />
              <span className="text-neutral-300 text-xs">{log.agent}</span>
            </div>
            {log.data && Object.keys(log.data).length > 0 && (
              <p className="text-neutral-500 text-xs break-words leading-relaxed">
                {typeof log.data.message === "string"
                  ? log.data.message
                  : JSON.stringify(log.data)}
              </p>
            )}
          </div>
          <div className="shrink-0 mt-0.5">
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
      <div ref={endRef} />
    </div>
  );
}
