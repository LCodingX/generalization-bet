"use client";

import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Trash2, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

import type { EvalExample, HeatmapData, CategoryAggregate } from "@/lib/types";
import { useJob } from "@/lib/hooks/use-job";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/runs/StatusBadge";
import { ProgressBar } from "@/components/runs/ProgressBar";
import { EvalQuestionsPanel } from "@/components/runs/EvalQuestionsPanel";
import { HyperparameterForm } from "@/components/runs/HyperparameterForm";
import { TrainingCategories } from "@/components/runs/TrainingCategories";
import { InfluenceHeatmap } from "@/components/viz/InfluenceHeatmap";
import { AggregatedBarChart } from "@/components/viz/AggregatedBarChart";
import { Leaderboard } from "@/components/viz/Leaderboard";

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function RunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { job, scores, loading, error } = useJob(id);

  const [selectedEvalIndex, setSelectedEvalIndex] = useState<
    number | undefined
  >(0);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [deleting, setDeleting] = useState(false);

  // Derive eval examples from scores (unique eval questions, preserving order)
  const evalExamples = useMemo<EvalExample[]>(() => {
    const seen = new Set<string>();
    const examples: EvalExample[] = [];
    for (const row of scores) {
      if (!seen.has(row.eval_question)) {
        seen.add(row.eval_question);
        examples.push({ question: row.eval_question, completion: "" });
      }
    }
    return examples;
  }, [scores]);

  // Derive training categories from scores (unique train_category with counts)
  const categories = useMemo<{ name: string; count: number }[]>(() => {
    const countMap = new Map<string, Set<string>>();
    for (const row of scores) {
      if (!countMap.has(row.train_category)) {
        countMap.set(row.train_category, new Set());
      }
      countMap.get(row.train_category)!.add(row.train_id);
    }
    return Array.from(countMap.entries()).map(([name, ids]) => ({
      name,
      count: ids.size,
    }));
  }, [scores]);

  // Derive heatmap data: group by (category, eval_question), average tracin scores
  const heatmapData = useMemo<HeatmapData | null>(() => {
    if (scores.length === 0) return null;

    const categoryNames = categories.map((c) => c.name);
    const evalQuestions = evalExamples.map((e) => e.question);

    if (categoryNames.length === 0 || evalQuestions.length === 0) return null;

    const categoryIdx = new Map(categoryNames.map((c, i) => [c, i]));
    const evalIdx = new Map(evalQuestions.map((q, i) => [q, i]));

    // Accumulate sums and counts for averaging
    const sums: number[][] = categoryNames.map(() =>
      new Array(evalQuestions.length).fill(0)
    );
    const counts: number[][] = categoryNames.map(() =>
      new Array(evalQuestions.length).fill(0)
    );

    for (const row of scores) {
      const ci = categoryIdx.get(row.train_category);
      const ei = evalIdx.get(row.eval_question);
      if (ci !== undefined && ei !== undefined) {
        sums[ci][ei] += row.tracin_score;
        counts[ci][ei] += 1;
      }
    }

    const matrix = sums.map((row, ri) =>
      row.map((sum, ci) => (counts[ri][ci] > 0 ? sum / counts[ri][ci] : 0))
    );

    return { categories: categoryNames, evalQuestions, matrix };
  }, [scores, categories, evalExamples]);

  // Derive DataInf heatmap data (same structure, but using datainf_score)
  const datainfHeatmapData = useMemo<HeatmapData | null>(() => {
    if (scores.length === 0) return null;

    const categoryNames = categories.map((c) => c.name);
    const evalQuestions = evalExamples.map((e) => e.question);

    if (categoryNames.length === 0 || evalQuestions.length === 0) return null;

    const categoryIdx = new Map(categoryNames.map((c, i) => [c, i]));
    const evalIdx = new Map(evalQuestions.map((q, i) => [q, i]));

    const sums: number[][] = categoryNames.map(() =>
      new Array(evalQuestions.length).fill(0)
    );
    const counts: number[][] = categoryNames.map(() =>
      new Array(evalQuestions.length).fill(0)
    );

    for (const row of scores) {
      const ci = categoryIdx.get(row.train_category);
      const ei = evalIdx.get(row.eval_question);
      if (ci !== undefined && ei !== undefined) {
        sums[ci][ei] += row.datainf_score;
        counts[ci][ei] += 1;
      }
    }

    const matrix = sums.map((row, ri) =>
      row.map((sum, ci) => (counts[ri][ci] > 0 ? sum / counts[ri][ci] : 0))
    );

    return { categories: categoryNames, evalQuestions, matrix };
  }, [scores, categories, evalExamples]);

  // Derive aggregated scores per category for bar chart + leaderboard
  const categoryAggregates = useMemo<CategoryAggregate[]>(() => {
    if (scores.length === 0) return [];

    const categoryNames = categories.map((c) => c.name);
    const evalQuestions = evalExamples.map((e) => e.question);

    const aggMap = new Map<
      string,
      {
        tracin_total: number;
        datainf_total: number;
        eval_contributions: Map<string, { tracin: number; datainf: number }>;
      }
    >();

    for (const cat of categoryNames) {
      const contribs = new Map<string, { tracin: number; datainf: number }>();
      for (const eq of evalQuestions) {
        contribs.set(eq, { tracin: 0, datainf: 0 });
      }
      aggMap.set(cat, { tracin_total: 0, datainf_total: 0, eval_contributions: contribs });
    }

    for (const row of scores) {
      const agg = aggMap.get(row.train_category);
      if (!agg) continue;
      agg.tracin_total += row.tracin_score;
      agg.datainf_total += row.datainf_score;
      const contrib = agg.eval_contributions.get(row.eval_question);
      if (contrib) {
        contrib.tracin += row.tracin_score;
        contrib.datainf += row.datainf_score;
      }
    }

    return categoryNames.map((cat) => {
      const agg = aggMap.get(cat)!;
      return {
        category: cat,
        tracin_total: agg.tracin_total,
        datainf_total: agg.datainf_total,
        eval_contributions: Array.from(agg.eval_contributions.entries()).map(
          ([eq, v]) => ({ eval_question: eq, tracin: v.tracin, datainf: v.datainf })
        ),
      };
    });
  }, [scores, categories, evalExamples]);

  // Delete handler
  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this run?")) return;
    setDeleting(true);
    try {
      await api.del(`/api/v1/jobs/${id}`);
      router.push("/runs");
    } catch {
      setDeleting(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-background px-8 py-8">
        <Link
          href="/runs"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Runs
        </Link>
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-background px-8 py-8">
        <Link
          href="/runs"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Runs
        </Link>
        <div className="flex items-center justify-center py-24">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  // Job not found
  if (!job) {
    return (
      <div className="min-h-screen bg-background px-8 py-8">
        <Link
          href="/runs"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Runs
        </Link>
        <div className="flex items-center justify-center py-24">
          <p className="text-sm text-muted-foreground">Job not found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background px-8 py-8">
      {/* Back link */}
      <Link
        href="/runs"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Runs
      </Link>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <h1 className="text-2xl font-semibold font-sans text-foreground">
            {job.model_name}
          </h1>
          <StatusBadge status={job.status} />
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
            title="Delete run"
          >
            {deleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
          </button>
        </div>
        <div className="max-w-md">
          <ProgressBar progress={job.progress} />
        </div>
      </div>

      {/* Two-panel layout */}
      <div className="flex gap-6">
        {/* Left panel -- 35% */}
        <motion.div
          className="w-[35%] shrink-0 space-y-6"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          {/* Eval Questions */}
          <div className="card-elevated rounded-xl border border-border bg-white p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">
              Eval Questions
            </h2>
            <div className="h-[320px]">
              <EvalQuestionsPanel
                examples={evalExamples}
                selectedIndex={selectedEvalIndex}
                onSelect={setSelectedEvalIndex}
              />
            </div>
          </div>

          {/* Experiment Setup */}
          <div className="card-elevated rounded-xl border border-border bg-white p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">
              Experiment Setup
            </h2>
            <HyperparameterForm values={job.hyperparameters} readOnly />
          </div>
        </motion.div>

        {/* Right panel -- 65% */}
        <motion.div
          className="flex-1 space-y-6"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35, ease: "easeOut", delay: 0.1 }}
        >
          {/* Training Categories */}
          <div className="card-elevated rounded-xl border border-border bg-white p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">
              Training Categories
            </h2>
            <TrainingCategories
              categories={categories}
              selectedCategory={selectedCategory}
              onSelect={setSelectedCategory}
            />
          </div>

          {/* Influence Scores */}
          <div className="card-elevated rounded-xl border border-border bg-white p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">
              Influence Scores
            </h2>
            {job.status === "completed" && heatmapData ? (
              <div className="space-y-6">
                {/* Heatmaps */}
                <InfluenceHeatmap
                  data={heatmapData}
                  title="TracIn Influence"
                />
                {datainfHeatmapData && (
                  <InfluenceHeatmap
                    data={datainfHeatmapData}
                    title="DataInf Influence"
                  />
                )}

                {/* Bar Chart */}
                {categoryAggregates.length > 0 && (
                  <AggregatedBarChart
                    data={categoryAggregates}
                    metric="tracin"
                  />
                )}

                {/* Leaderboard */}
                {categoryAggregates.length > 0 && (
                  <Leaderboard
                    data={categoryAggregates}
                    metric="tracin"
                    onSelectCategory={setSelectedCategory}
                  />
                )}
              </div>
            ) : job.status === "completed" ? (
              <div className="flex items-center justify-center py-12">
                <p className="text-sm text-muted-foreground">
                  No influence scores available yet.
                </p>
              </div>
            ) : (
              <div className="flex items-center justify-center py-12">
                <p className="text-sm text-muted-foreground">
                  Influence scores will be available once the run reaches the
                  completed status. Current status:{" "}
                  <span className="font-mono">{job.status}</span>
                </p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
