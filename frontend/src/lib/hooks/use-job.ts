"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase";
import { api } from "@/lib/api";
import type { Job, InfluenceScoreRow, ScoresResponse } from "@/lib/types";

export function useJob(jobId: string) {
  const [job, setJob] = useState<Job | null>(null);
  const [scores, setScores] = useState<InfluenceScoreRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScores = useCallback(async () => {
    try {
      const PAGE_SIZE = 1000;
      let offset = 0;
      let allScores: InfluenceScoreRow[] = [];

      // Paginate until we have all scores
      while (true) {
        const data = await api.get<ScoresResponse>(
          `/api/v1/jobs/${jobId}/scores?limit=${PAGE_SIZE}&offset=${offset}`
        );
        allScores = allScores.concat(data.scores);
        if (allScores.length >= data.total || data.scores.length < PAGE_SIZE) {
          break;
        }
        offset += PAGE_SIZE;
      }

      setScores(allScores);
    } catch {
      // Scores may not be available yet
    }
  }, [jobId]);

  const fetchJob = useCallback(async () => {
    try {
      setError(null);
      const data = await api.get<Job>(`/api/v1/jobs/${jobId}`);
      setJob(data);
      if (data.status === "completed") {
        await fetchScores();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch job");
    } finally {
      setLoading(false);
    }
  }, [jobId, fetchScores]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  // Supabase Realtime subscription filtered to this job
  useEffect(() => {
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
          const updated = payload.new as Job;
          setJob(updated);
          if (updated.status === "completed") {
            fetchScores();
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [jobId, fetchScores]);

  return { job, scores, loading, error };
}
