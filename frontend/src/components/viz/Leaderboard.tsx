"use client";

import { useMemo, useState } from "react";
import type { CategoryAggregate } from "@/lib/types";
import { getCategoryColor } from "@/lib/colors";

interface LeaderboardProps {
  data: CategoryAggregate[];
  metric: "tracin" | "datainf";
  onSelectCategory?: (category: string) => void;
}

export function Leaderboard({
  data,
  metric: initialMetric,
  onSelectCategory,
}: LeaderboardProps) {
  const [metric, setMetric] = useState<"tracin" | "datainf">(initialMetric);

  const sorted = useMemo(() => {
    const key = metric === "tracin" ? "tracin_total" : "datainf_total";
    return [...data].sort((a, b) => Math.abs(b[key]) - Math.abs(a[key]));
  }, [data, metric]);

  // Build color map using original data order for consistent coloring
  const colorMap = useMemo(() => {
    const map: Record<string, string> = {};
    data.forEach((d, i) => {
      map[d.category] = getCategoryColor(i);
    });
    return map;
  }, [data]);

  return (
    <div className="card-elevated rounded-xl bg-card p-6">
      <h3 className="text-sm font-semibold text-card-foreground mb-4 font-sans">
        Most Influential Categories
      </h3>

      {/* Metric toggle */}
      <div className="flex gap-1 mb-4 rounded-lg bg-muted p-1 w-fit">
        <button
          type="button"
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors font-sans ${
            metric === "tracin"
              ? "bg-card text-card-foreground shadow-sm"
              : "text-muted-foreground hover:text-card-foreground"
          }`}
          onClick={() => setMetric("tracin")}
        >
          by TracIn
        </button>
        <button
          type="button"
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors font-sans ${
            metric === "datainf"
              ? "bg-card text-card-foreground shadow-sm"
              : "text-muted-foreground hover:text-card-foreground"
          }`}
          onClick={() => setMetric("datainf")}
        >
          by DataInf
        </button>
      </div>

      {/* Table header */}
      <div className="grid grid-cols-[32px_16px_1fr_80px_80px] gap-x-3 items-center px-3 pb-2 border-b border-border">
        <span className="text-xs text-muted-foreground font-sans">#</span>
        <span />
        <span className="text-xs text-muted-foreground font-sans">
          Category
        </span>
        <span className="text-xs text-muted-foreground font-sans text-right">
          TracIn
        </span>
        <span className="text-xs text-muted-foreground font-sans text-right">
          DataInf
        </span>
      </div>

      {/* Rows */}
      <div className="divide-y divide-border/50">
        {sorted.map((entry, i) => {
          const rank = i + 1;
          const isTop3 = rank <= 3;

          return (
            <button
              key={entry.category}
              type="button"
              className={`grid grid-cols-[32px_16px_1fr_80px_80px] gap-x-3 items-center w-full px-3 py-2.5 text-left transition-colors hover:bg-accent/50 ${
                isTop3 ? "bg-accent/30" : ""
              } ${onSelectCategory ? "cursor-pointer" : "cursor-default"}`}
              onClick={() => onSelectCategory?.(entry.category)}
            >
              {/* Rank */}
              <span
                className={`text-xs tabular-nums font-mono ${
                  isTop3
                    ? "font-bold text-primary"
                    : "text-muted-foreground"
                }`}
              >
                {rank}
              </span>

              {/* Color chip */}
              <span
                className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
                style={{
                  backgroundColor: colorMap[entry.category] ?? "#6366f1",
                }}
              />

              {/* Category name */}
              <span className="text-sm font-medium text-card-foreground font-sans truncate">
                {entry.category}
              </span>

              {/* TracIn value */}
              <span
                className={`text-xs tabular-nums text-right font-mono ${
                  metric === "tracin"
                    ? "font-semibold text-card-foreground"
                    : "text-muted-foreground"
                }`}
              >
                {entry.tracin_total.toFixed(3)}
              </span>

              {/* DataInf value */}
              <span
                className={`text-xs tabular-nums text-right font-mono ${
                  metric === "datainf"
                    ? "font-semibold text-card-foreground"
                    : "text-muted-foreground"
                }`}
              >
                {entry.datainf_total.toFixed(3)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
