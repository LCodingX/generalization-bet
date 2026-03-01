"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { getCategoryColor } from "@/lib/colors";

interface GradientNormsChartProps {
  data: { epoch: number; global: number; partitions: Record<string, number> }[];
  categories: string[];
}

export function GradientNormsChart({
  data,
  categories,
}: GradientNormsChartProps) {
  // Flatten records into a shape Recharts can use: { epoch, global, [cat]: value }
  const chartData = data.map((d) => ({
    epoch: d.epoch,
    global: d.global,
    ...d.partitions,
  }));

  return (
    <div className="card-elevated rounded-xl bg-card p-6">
      <h3 className="text-sm font-semibold text-card-foreground mb-4 font-sans">
        Gradient Norms
      </h3>

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
            tick={{ fontSize: 12, fontFamily: "var(--font-mono)" }}
            stroke="#94a3b8"
            label={{
              value: "Gradient Norm",
              angle: -90,
              position: "insideLeft",
              offset: 8,
              fontSize: 12,
              fontFamily: "var(--font-sans)",
              fill: "#64748b",
            }}
          />

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
          />

          <Legend
            wrapperStyle={{ fontSize: 12, fontFamily: "var(--font-sans)" }}
          />

          {/* Global norm — bold primary line */}
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

          {/* Per-partition lines — thin and semi-transparent */}
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
