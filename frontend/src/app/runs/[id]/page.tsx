"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";

import type { Job, EvalExample } from "@/lib/types";
import { StatusBadge } from "@/components/runs/StatusBadge";
import { ProgressBar } from "@/components/runs/ProgressBar";
import { EvalQuestionsPanel } from "@/components/runs/EvalQuestionsPanel";
import { HyperparameterForm } from "@/components/runs/HyperparameterForm";
import { TrainingCategories } from "@/components/runs/TrainingCategories";

// TODO: Fetch job, eval examples, and categories from the API

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function RunDetailPage() {
  const [selectedEvalIndex, setSelectedEvalIndex] = useState<
    number | undefined
  >(0);
  const [selectedCategory, setSelectedCategory] = useState<string>("");

  // TODO: Fetch job, eval examples, and categories from the API
  const [job] = useState<Job | null>(null);
  const [evalExamples] = useState<EvalExample[]>([]);
  const [categories] = useState<{ name: string; count: number }[]>([]);

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
          <p className="text-sm text-muted-foreground">Loading run...</p>
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
        </div>
        <div className="max-w-md">
          <ProgressBar progress={job.progress} />
        </div>
      </div>

      {/* Two-panel layout */}
      <div className="flex gap-6">
        {/* Left panel — 35% */}
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

        {/* Right panel — 65% */}
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
            {job.status === "completed" ? (
              <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-border p-12">
                <p className="text-sm text-muted-foreground">
                  Heatmap and charts will render here
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
