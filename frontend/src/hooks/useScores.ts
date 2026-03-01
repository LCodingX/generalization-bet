"use client";

import { useCallback, useEffect, useState } from "react";
import { getScores } from "@/lib/api";
import type {
  CategoryAggregate,
  HeatmapData,
  InfluenceScoreRow,
  ScoresResponse,
} from "@/lib/types";

export function useScores(token: string | null, jobId: string | null) {
  const [scores, setScores] = useState<InfluenceScoreRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScores = useCallback(
    async (params?: { category?: string; sort_by?: string; order?: string; limit?: number }) => {
      if (!token || !jobId) return;
      setLoading(true);
      setError(null);
      try {
        const res = await getScores(token, jobId, { limit: 1000, ...params });
        setScores(res.scores);
        setTotal(res.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch scores");
      } finally {
        setLoading(false);
      }
    },
    [token, jobId]
  );

  useEffect(() => {
    fetchScores();
  }, [fetchScores]);

  return { scores, total, loading, error, refetch: fetchScores };
}

// Transform flat scores into heatmap matrix
export function scoresToHeatmap(
  scores: InfluenceScoreRow[],
  metric: "tracin_score" | "datainf_score"
): HeatmapData {
  const categorySet = new Set<string>();
  const evalSet = new Set<string>();
  scores.forEach((s) => {
    categorySet.add(s.train_category);
    evalSet.add(s.eval_question);
  });

  const categories = Array.from(categorySet).sort();
  const evalQuestions = Array.from(evalSet);

  const catIdx = new Map(categories.map((c, i) => [c, i]));
  const evalIdx = new Map(evalQuestions.map((q, i) => [q, i]));

  const matrix: number[][] = categories.map(() => evalQuestions.map(() => 0));

  scores.forEach((s) => {
    const ci = catIdx.get(s.train_category);
    const ei = evalIdx.get(s.eval_question);
    if (ci !== undefined && ei !== undefined) {
      matrix[ci][ei] += s[metric];
    }
  });

  return { categories, evalQuestions, matrix };
}

// Aggregate scores per category
export function scoresToAggregates(
  scores: InfluenceScoreRow[]
): CategoryAggregate[] {
  const map = new Map<string, CategoryAggregate>();

  scores.forEach((s) => {
    if (!map.has(s.train_category)) {
      map.set(s.train_category, {
        category: s.train_category,
        tracin_total: 0,
        datainf_total: 0,
        eval_contributions: [],
      });
    }
    const agg = map.get(s.train_category)!;
    agg.tracin_total += s.tracin_score;
    agg.datainf_total += s.datainf_score;
    agg.eval_contributions.push({
      eval_question: s.eval_question,
      tracin: s.tracin_score,
      datainf: s.datainf_score,
    });
  });

  return Array.from(map.values()).sort(
    (a, b) => Math.abs(b.tracin_total) - Math.abs(a.tracin_total)
  );
}
