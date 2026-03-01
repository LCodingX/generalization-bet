// Partition color palette — 10 distinguishable colors for training categories
export const PARTITION_COLORS = [
  "#6366f1", // indigo
  "#ec4899", // pink
  "#14b8a6", // teal
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#e11d48", // rose
  "#0ea5e9", // sky
] as const;

export function getCategoryColor(index: number): string {
  return PARTITION_COLORS[index % PARTITION_COLORS.length];
}

// Diverging color scale for heatmaps
// Negative (crimson) → zero (white) → positive (indigo)
export function getHeatmapColor(value: number, maxAbsValue: number): string {
  if (maxAbsValue === 0) return "#ffffff";
  const normalized = value / maxAbsValue; // -1 to +1
  if (normalized > 0) {
    const intensity = Math.min(normalized, 1);
    const r = Math.round(255 - intensity * (255 - 99));
    const g = Math.round(255 - intensity * (255 - 102));
    const b = Math.round(255 - intensity * (255 - 241));
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    const intensity = Math.min(Math.abs(normalized), 1);
    const r = Math.round(255 - intensity * (255 - 220));
    const g = Math.round(255 - intensity * (255 - 38));
    const b = Math.round(255 - intensity * (255 - 38));
    return `rgb(${r}, ${g}, ${b})`;
  }
}

export function getHeatmapTextColor(value: number, maxAbsValue: number): string {
  if (maxAbsValue === 0) return "#1e293b";
  const intensity = Math.abs(value / maxAbsValue);
  return intensity > 0.6 ? "#ffffff" : "#1e293b";
}
