"use client";
import { Clock, AlertCircle, CheckCircle2, TrendingUp } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import clsx from "clsx";
import type { PredictionResult } from "@/lib/types";

export function PredictiveClose({
  prediction,
  currentStep = "",
}: {
  prediction?: PredictionResult;
  currentStep?: string;
}) {
  if (!prediction) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-600 gap-3">
        <Clock className="w-8 h-8 opacity-30" />
        <p className="text-sm">Predictive timeline appears while a pipeline is running</p>
      </div>
    );
  }

  const pct = Math.round(
    (prediction.steps_complete / Math.max(prediction.steps_complete + prediction.steps_remaining, 1)) * 100
  );

  const completionTime = new Date(prediction.predicted_completion_time);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-neutral-500">Predicted completion</p>
          <p className="text-2xl font-bold text-white">
            {prediction.predicted_completion_minutes} min
          </p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {completionTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
        </div>
        <div className="text-right">
          <span
            className={clsx(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border",
              prediction.on_track
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-red-500/10 text-red-400 border-red-500/20"
            )}
          >
            {prediction.on_track ? (
              <><CheckCircle2 className="w-3.5 h-3.5" /> On Track</>
            ) : (
              <><AlertCircle className="w-3.5 h-3.5" /> Delayed</>
            )}
          </span>
          <p className="text-xs text-neutral-500 mt-1">
            Confidence: {Math.round(prediction.confidence * 100)}%
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-neutral-500">
          <span>{prediction.steps_complete} steps done</span>
          <span>{prediction.steps_remaining} remaining</span>
        </div>
        <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-xs text-neutral-600 text-center">{pct}% complete</p>
      </div>

      {/* Bottleneck */}
      {prediction.current_bottleneck && (
        <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20">
          <p className="text-xs text-amber-400 font-medium">Current Bottleneck</p>
          <p className="text-sm text-white mt-0.5">{prediction.current_bottleneck}</p>
          {prediction.bottleneck_reason && (
            <p className="text-xs text-neutral-500 mt-1">{prediction.bottleneck_reason}</p>
          )}
        </div>
      )}

      {/* Risk Factors */}
      {prediction.risk_factors && prediction.risk_factors.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-neutral-500 font-medium">Risk Factors</p>
          {prediction.risk_factors.map((r, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-neutral-400">
              <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              {r}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
