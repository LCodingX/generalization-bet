"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import type { CategoryAggregate } from "@/lib/types";
import { getCategoryColor } from "@/lib/colors";

interface AggregatedBarChartProps {
  data: CategoryAggregate[];
  metric: "tracin" | "datainf";
}

export function AggregatedBarChart({ data, metric }: AggregatedBarChartProps) {
  const sorted = useMemo(() => {
    const key = metric === "tracin" ? "tracin_total" : "datainf_total";
    return [...data].sort((a, b) => Math.abs(b[key]) - Math.abs(a[key]));
  }, [data, metric]);

  const chartData = sorted.map((d) => ({
    category: d.category,
    value: metric === "tracin" ? d.tracin_total : d.datainf_total,
  }));

  // Build a color map preserving original index order for consistent coloring
  const colorMap = useMemo(() => {
    const map: Record<string, string> = {};
    data.forEach((d, i) => {
      map[d.category] = getCategoryColor(i);
    });
    return map;
  }, [data]);

  const metricLabel = metric === "tracin" ? "TracIn" : "DataInf";

  return (
    <div className="card-elevated rounded-xl bg-card p-6">
      <h3 className="text-sm font-semibold text-card-foreground mb-4 font-sans">
        Aggregated Influence &mdash; {metricLabel}
      </h3>

      <ResponsiveContainer width="100%" height={Math.max(280, sorted.length * 40 + 60)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />

          <XAxis
            type="number"
            tick={{ fontSize: 12, fontFamily: "var(--font-mono)" }}
            stroke="#94a3b8"
            label={{
              value: metricLabel,
              position: "insideBottomRight",
              offset: -4,
              fontSize: 12,
              fontFamily: "var(--font-sans)",
              fill: "#64748b",
            }}
          />

          <YAxis
            type="category"
            dataKey="category"
            width={120}
            tick={{ fontSize: 12, fontFamily: "var(--font-sans)" }}
            stroke="#94a3b8"
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
            formatter={(value) => [(value as number).toFixed(4), metricLabel]}
          />

          <Bar
            dataKey="value"
            radius={[0, 4, 4, 0]}
            isAnimationActive
            animationDuration={800}
            animationEasing="ease-in-out"
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.category}
                fill={colorMap[entry.category] ?? "#6366f1"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
