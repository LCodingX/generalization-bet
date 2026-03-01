"use client";

import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
}

const STATUS_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; pulse?: boolean }
> = {
  queued: {
    label: "Queued",
    bg: "bg-slate-100",
    text: "text-slate-600",
  },
  provisioning: {
    label: "Provisioning",
    bg: "bg-slate-100",
    text: "text-slate-600",
  },
  training: {
    label: "Training",
    bg: "bg-blue-100",
    text: "text-blue-700",
    pulse: true,
  },
  computing_tracin: {
    label: "Computing TracIn",
    bg: "bg-amber-100",
    text: "text-amber-700",
    pulse: true,
  },
  computing_datainf: {
    label: "Computing DataInf",
    bg: "bg-amber-100",
    text: "text-amber-700",
    pulse: true,
  },
  completed: {
    label: "Completed",
    bg: "bg-green-100",
    text: "text-green-700",
  },
  failed: {
    label: "Failed",
    bg: "bg-red-100",
    text: "text-red-700",
  },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    bg: "bg-slate-100",
    text: "text-slate-600",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      {config.pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-pulse rounded-full opacity-75",
              status === "training" ? "bg-blue-500" : "bg-amber-500"
            )}
          />
          <span
            className={cn(
              "relative inline-flex h-2 w-2 rounded-full",
              status === "training" ? "bg-blue-500" : "bg-amber-500"
            )}
          />
        </span>
      )}
      {config.label}
    </span>
  );
}
