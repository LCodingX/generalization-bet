"use client";

interface ProgressBarProps {
  progress: number;
}

export function ProgressBar({ progress }: ProgressBarProps) {
  const clampedProgress = Math.min(Math.max(progress, 0), 1);
  const percentage = Math.round(clampedProgress * 100);

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div
          className="h-full rounded-full bg-indigo-500"
          style={{
            width: `${percentage}%`,
            transition: "width 0.6s ease",
          }}
        />
      </div>
      <span className="text-xs font-mono text-muted-foreground w-10 text-right tabular-nums">
        {percentage}%
      </span>
    </div>
  );
}
