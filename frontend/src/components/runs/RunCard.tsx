"use client";

import type { Job } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "./StatusBadge";
import { ProgressBar } from "./ProgressBar";

interface RunCardProps {
  job: Job;
  onClick: () => void;
}

function formatRelativeTime(dateString: string): string {
  const now = Date.now();
  const then = new Date(dateString).getTime();
  const diffMs = now - then;

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;

  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

export function RunCard({ job, onClick }: RunCardProps) {
  const percentage = Math.round(Math.min(Math.max(job.progress, 0), 1) * 100);

  return (
    <Card
      className="card-elevated cursor-pointer hover:border-primary/30 transition-all"
      onClick={onClick}
    >
      <CardContent>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold truncate mr-2">
            {job.model_name}
          </h3>
          <StatusBadge status={job.status} />
        </div>

        <ProgressBar progress={job.progress} />

        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(job.created_at)}
          </span>
          <span className="text-xs font-mono text-muted-foreground tabular-nums">
            {percentage}%
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
