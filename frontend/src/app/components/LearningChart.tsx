"use client";
import { BarChart2, TrendingUp } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, Bar, BarChart,
} from "recharts";

type LearningDataPoint = {
  period: string;
  critic_score?: number;
  hard_blocks?: number;
  false_positives?: number;
  cfo_overrides?: number;
  time_minutes?: number;
};

const DEMO_DATA: LearningDataPoint[] = [
  { period: "Q1 FY25", critic_score: 0.71, hard_blocks: 12, false_positives: 8, cfo_overrides: 5, time_minutes: 42 },
  { period: "Q2 FY25", critic_score: 0.77, hard_blocks: 9,  false_positives: 5, cfo_overrides: 3, time_minutes: 36 },
  { period: "Q3 FY25", critic_score: 0.82, hard_blocks: 7,  false_positives: 3, cfo_overrides: 2, time_minutes: 29 },
  { period: "Q4 FY25", critic_score: 0.87, hard_blocks: 5,  false_positives: 2, cfo_overrides: 1, time_minutes: 23 },
  { period: "Q1 FY26", critic_score: 0.91, hard_blocks: 3,  false_positives: 1, cfo_overrides: 0, time_minutes: 18 },
];

export function LearningChart({ data = DEMO_DATA }: { data?: LearningDataPoint[] }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-indigo-400" />
        <p className="text-sm text-neutral-400">
          RLAIF critic score and CFO override count — improving each period as the system learns from feedback.
        </p>
      </div>

      {/* Critic Score over Time */}
      <div>
        <h4 className="text-xs text-neutral-500 mb-3 font-medium uppercase tracking-wider">
          RLAIF Critic Score Over Time
        </h4>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
              <XAxis dataKey="period" tick={{ fill: "#737373", fontSize: 11 }} />
              <YAxis domain={[0.6, 1]} tick={{ fill: "#737373", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#171717", border: "1px solid #333", borderRadius: 8 }}
                labelStyle={{ color: "#fff" }}
                formatter={(v: any) => [Number(v).toFixed(2), "Score"]}
              />
              <Line
                type="monotone"
                dataKey="critic_score"
                stroke="#6366f1"
                strokeWidth={2.5}
                dot={{ fill: "#6366f1", r: 4 }}
                activeDot={{ r: 6 }}
                name="Critic Score"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Hard Blocks + False Positives */}
      <div>
        <h4 className="text-xs text-neutral-500 mb-3 font-medium uppercase tracking-wider">
          Hard Blocks & False Positives (Decreasing)
        </h4>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
              <XAxis dataKey="period" tick={{ fill: "#737373", fontSize: 11 }} />
              <YAxis tick={{ fill: "#737373", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#171717", border: "1px solid #333", borderRadius: 8 }}
                labelStyle={{ color: "#fff" }}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: "#737373" }} />
              <Bar dataKey="hard_blocks"     name="Hard Blocks"     fill="#ef4444" opacity={0.8} radius={[3,3,0,0]} />
              <Bar dataKey="false_positives" name="False Positives" fill="#f59e0b" opacity={0.8} radius={[3,3,0,0]} />
              <Bar dataKey="cfo_overrides"   name="CFO Overrides"   fill="#6366f1" opacity={0.8} radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Summary Trend */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Critic Score", value: `${((data[data.length - 1]?.critic_score ?? 0) * 100).toFixed(0)}%`, color: "indigo" },
          { label: "Hard Blocks", value: String(data[data.length - 1]?.hard_blocks ?? 0), color: "red" },
          { label: "Close Time", value: `${data[data.length - 1]?.time_minutes ?? 0}m`, color: "emerald" },
        ].map(({ label, value, color }) => (
          <div key={label} className={`p-3 rounded-xl bg-neutral-900 border border-white/5 text-center`}>
            <p className="text-xs text-neutral-500">{label}</p>
            <p className={`text-xl font-bold text-${color}-400 mt-1`}>{value}</p>
            <p className="text-xs text-emerald-500">↑ improving</p>
          </div>
        ))}
      </div>
    </div>
  );
}
