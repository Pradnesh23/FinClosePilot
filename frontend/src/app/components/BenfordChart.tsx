"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from "recharts";

type BenfordChartProps = {
  observed?: Record<string, number>;
};

// Expected Benford frequencies (%)
const BENFORD_EXPECTED: Record<string, number> = {
  "1": 30.1, "2": 17.6, "3": 12.5, "4": 9.7, "5": 7.9,
  "6": 6.7, "7": 5.8, "8": 5.1, "9": 4.6,
};

export function BenfordChart({ observed = {} }: BenfordChartProps) {
  const data = Object.keys(BENFORD_EXPECTED).map((digit) => ({
    digit,
    expected: BENFORD_EXPECTED[digit],
    observed: observed[digit] ?? 0,
    deviation: Math.abs((observed[digit] ?? 0) - BENFORD_EXPECTED[digit]),
  }));

  const hasData = data.some((d) => d.observed > 0);

  return (
    <div className="space-y-3">
      <p className="text-xs text-neutral-500">
        Compares actual first-digit distribution against Benford&apos;s Law prediction.
        Red bars indicate suspicious deviations.
      </p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <XAxis dataKey="digit" tick={{ fill: "#737373", fontSize: 12 }} />
            <YAxis tick={{ fill: "#737373", fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "#171717", border: "1px solid #333", borderRadius: 8 }}
              labelStyle={{ color: "#fff" }}
              formatter={(val: any, name: any) => [`${Number(val).toFixed(1)}%`, name]}
            />
            <Bar dataKey="expected" name="Expected %" fill="#4f46e5" opacity={0.5} radius={[3, 3, 0, 0]} />
            <Bar dataKey="observed" name="Observed %" radius={[3, 3, 0, 0]}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.deviation > 5 ? "#ef4444" : "#10b981"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {!hasData && (
        <p className="text-center text-xs text-neutral-600 pb-2">
          Run the demo pipeline to see Benford analysis results.
        </p>
      )}
    </div>
  );
}
