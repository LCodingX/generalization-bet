"use client";

import { Fragment, useMemo, useState } from "react";
import type { HeatmapData } from "@/lib/types";
import { getHeatmapColor, getHeatmapTextColor } from "@/lib/colors";

interface InfluenceHeatmapProps {
  data: HeatmapData;
  title?: string;
}

interface HoveredCell {
  category: string;
  question: string;
  value: number;
  x: number;
  y: number;
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "\u2026";
}

export function InfluenceHeatmap({ data, title }: InfluenceHeatmapProps) {
  const [hovered, setHovered] = useState<HoveredCell | null>(null);

  const maxAbsValue = useMemo(() => {
    let max = 0;
    for (const row of data.matrix) {
      for (const v of row) {
        const abs = Math.abs(v);
        if (abs > max) max = abs;
      }
    }
    return max;
  }, [data.matrix]);

  const colCount = data.evalQuestions.length;
  const rowHeaderWidth = 140;
  const cellSize = 64;
  const headerHeight = 120;

  return (
    <div className="card-elevated p-4 rounded-xl">
      {title && (
        <h3 className="text-sm font-semibold text-card-foreground mb-4 font-sans">
          {title}
        </h3>
      )}

      <div className="relative overflow-x-auto">
        <div
          className="relative"
          style={{
            display: "grid",
            gridTemplateColumns: `${rowHeaderWidth}px repeat(${colCount}, ${cellSize}px)`,
            gridTemplateRows: `${headerHeight}px repeat(${data.categories.length}, ${cellSize}px)`,
            width: rowHeaderWidth + colCount * cellSize,
          }}
        >
          {/* Top-left empty corner */}
          <div
            style={{
              gridColumn: 1,
              gridRow: 1,
              position: "sticky",
              left: 0,
              zIndex: 20,
              backgroundColor: "#ffffff",
            }}
          />

          {/* Column headers — eval questions rotated */}
          {data.evalQuestions.map((q, ci) => (
            <div
              key={`col-${ci}`}
              style={{
                gridColumn: ci + 2,
                gridRow: 1,
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "flex-start",
                paddingBottom: 6,
                overflow: "hidden",
              }}
            >
              <span
                className="text-xs text-muted-foreground font-sans whitespace-nowrap"
                style={{
                  transform: "rotate(-45deg)",
                  transformOrigin: "bottom left",
                  display: "inline-block",
                  maxWidth: 100,
                }}
                title={q}
              >
                {truncate(q, 18)}
              </span>
            </div>
          ))}

          {/* Row headers + cells */}
          {data.categories.map((cat, ri) => (
            <Fragment key={`row-group-${ri}`}>
              {/* Sticky row header */}
              <div
                style={{
                  gridColumn: 1,
                  gridRow: ri + 2,
                  position: "sticky",
                  left: 0,
                  zIndex: 10,
                  backgroundColor: "#ffffff",
                  display: "flex",
                  alignItems: "center",
                  paddingRight: 8,
                }}
              >
                <span
                  className="text-xs font-medium text-card-foreground font-sans truncate"
                  title={cat}
                >
                  {cat}
                </span>
              </div>

              {/* Data cells */}
              {data.evalQuestions.map((_q, ci) => {
                const value = data.matrix[ri][ci];
                const bg = getHeatmapColor(value, maxAbsValue);
                const fg = getHeatmapTextColor(value, maxAbsValue);

                return (
                  <div
                    key={`cell-${ri}-${ci}`}
                    className="flex items-center justify-center cursor-default transition-opacity hover:opacity-80"
                    style={{
                      gridColumn: ci + 2,
                      gridRow: ri + 2,
                      backgroundColor: bg,
                      color: fg,
                      border: "1px solid rgba(226,232,240,0.5)",
                    }}
                    onMouseEnter={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setHovered({
                        category: cat,
                        question: data.evalQuestions[ci],
                        value,
                        x: rect.left + rect.width / 2,
                        y: rect.top,
                      });
                    }}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <span
                      className="font-mono text-xs tabular-nums"
                      style={{
                        fontWeight:
                          Math.abs(value / (maxAbsValue || 1)) > 0.6
                            ? 700
                            : 400,
                      }}
                    >
                      {value.toFixed(2)}
                    </span>
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>

        {/* Floating tooltip */}
        {hovered && (
          <div
            className="pointer-events-none fixed z-50 rounded-lg border border-border bg-popover px-3 py-2 shadow-md"
            style={{
              left: hovered.x,
              top: hovered.y - 8,
              transform: "translate(-50%, -100%)",
              maxWidth: 280,
            }}
          >
            <p className="text-xs font-semibold text-popover-foreground font-sans mb-1">
              {hovered.category}
            </p>
            <p className="text-xs text-muted-foreground font-sans mb-1">
              {hovered.question}
            </p>
            <p className="text-xs font-mono tabular-nums text-popover-foreground">
              Score: {hovered.value.toFixed(4)}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
