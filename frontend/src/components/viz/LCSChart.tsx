"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import { getCategoryColor } from "@/lib/colors";

interface LCSChartProps {
  data: { epoch: number; global: number; partitions: Record<string, number> }[];
  categories: string[];
  pendingOffset?: number;
}

export function LCSChart({ data, categories, pendingOffset }: LCSChartProps) {
  const chartData = data.map((d) => ({
    epoch: d.epoch,
    global: d.global,
    ...d.partitions,
  }));

  // Determine the shaded region for pending epochs
  const shadedStart =
    pendingOffset && data.length > pendingOffset
      ? data[data.length - pendingOffset].epoch
      : undefined;
  const shadedEnd =
    pendingOffset && data.length > 0
      ? data[data.length - 1].epoch
      : undefined;

  return (
    <div className="card-elevated rounded-xl bg-card p-6">
      <h3 className="text-sm font-semibold text-card-foreground mb-1 font-sans">
        Linear CKA Similarity (LCS)
      </h3>
      <p className="text-xs text-muted-foreground mb-4 font-sans">
        -1 = straight path, 0 = orthogonal turn, +1 = reversal
      </p>

      <ResponsiveContainer width="100%" height={360}>
        <LineChart
          data={chartData}
          margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />

          <XAxis
            dataKey="epoch"
            tick={{ fontSize: 12, fontFamily: "var(--font-sans)" }}
            stroke="#94a3b8"
            label={{
              value: "Epoch",
              position: "insideBottomRight",
              offset: -4,
              fontSize: 12,
              fontFamily: "var(--font-sans)",
              fill: "#64748b",
            }}
          />

          <YAxis
            domain={[-1, 1]}
            tick={{ fontSize: 12, fontFamily: "var(--font-mono)" }}
            stroke="#94a3b8"
            label={{
              value: "LCS",
              angle: -90,
              position: "insideLeft",
              offset: 8,
              fontSize: 12,
              fontFamily: "var(--font-sans)",
              fill: "#64748b",
            }}
          />

          {/* Zero reference line */}
          <ReferenceLine
            y={0}
            stroke="#cbd5e1"
            strokeDasharray="6 4"
            strokeWidth={1}
          />

          {/* Pending-offset shaded area */}
          {shadedStart !== undefined && shadedEnd !== undefined && (
            <ReferenceArea
              x1={shadedStart}
              x2={shadedEnd}
              y1={-1}
              y2={1}
              fill="#94a3b8"
              fillOpacity={0.08}
              strokeOpacity={0}
            />
          )}

          <Tooltip
            contentStyle={{
              backgroundColor: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              fontSize: 12,
              fontFamily: "var(--font-mono)",
            }}
            labelStyle={{
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              marginBottom: 4,
            }}
            labelFormatter={(label) => `Epoch ${label}`}
            formatter={(value, name) => [
              (value as number).toFixed(4),
              name as string,
            ]}
          />

          <Legend
            wrapperStyle={{ fontSize: 12, fontFamily: "var(--font-sans)" }}
          />

          {/* Global LCS — bold primary line */}
          <Line
            type="monotone"
            dataKey="global"
            name="Global"
            stroke="#6366f1"
            strokeWidth={3}
            dot={false}
            isAnimationActive
            animationDuration={800}
            animationEasing="ease-in-out"
          />

          {/* Per-partition lines */}
          {categories.map((cat, i) => (
            <Line
              key={cat}
              type="monotone"
              dataKey={cat}
              name={cat}
              stroke={getCategoryColor(i)}
              strokeWidth={1.5}
              strokeOpacity={0.6}
              dot={false}
              isAnimationActive
              animationDuration={800}
              animationEasing="ease-in-out"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
