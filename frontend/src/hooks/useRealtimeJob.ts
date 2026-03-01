"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";
import type { Job, JobStatus } from "@/lib/types";

interface RealtimeJobUpdate {
  status: JobStatus;
  progress: number;
  status_message: string | null;
}

export function useRealtimeJob(jobId: string | null) {
  const [update, setUpdate] = useState<RealtimeJobUpdate | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const supabase = createClient();
    const channel = supabase
      .channel(`job-${jobId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "jobs",
          filter: `id=eq.${jobId}`,
        },
        (payload) => {
          const row = payload.new as Record<string, unknown>;
          setUpdate({
            status: row.status as JobStatus,
            progress: row.progress as number,
            status_message: row.status_message as string | null,
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [jobId]);

  return update;
}
