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

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_JOB: Job = {
  id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  status: "completed",
  status_message: "Run finished successfully",
  progress: 1.0,
  model_name: "meta-llama/Llama-2-7b-hf",
  hyperparameters: {
    learning_rate: 2e-4,
    epochs: 3,
    batch_size: 4,
    lora_rank: 16,
    lora_alpha: 32,
    lora_dropout: 0.05,
    checkpoint_interval: 50,
    max_seq_length: 512,
    datainf_damping: 0.1,
  },
  created_at: "2026-02-25T11:00:00Z",
  started_at: "2026-02-25T11:05:00Z",
  completed_at: "2026-02-25T18:42:00Z",
};

const MOCK_EVAL_EXAMPLES: EvalExample[] = [
  {
    question: "What is the capital of France?",
    completion: "The capital of France is Paris.",
  },
  {
    question: "Explain the concept of gradient descent in machine learning.",
    completion:
      "Gradient descent is an optimization algorithm that iteratively adjusts parameters to minimize a loss function by moving in the direction of steepest descent.",
  },
  {
    question: "What are the main differences between Python and JavaScript?",
    completion:
      "Python is dynamically typed and interpreted, designed for readability. JavaScript was created for web browsers but now runs server-side with Node.js.",
  },
  {
    question: "How does photosynthesis work?",
    completion:
      "Photosynthesis converts light energy into chemical energy, using CO2 and water to produce glucose and oxygen in chloroplasts.",
  },
  {
    question:
      "Summarize the key points of the transformer architecture paper.",
    completion:
      "The transformer uses self-attention mechanisms instead of recurrence, enabling parallelization and achieving state-of-the-art results in NLP tasks.",
  },
];

const MOCK_CATEGORIES = [
  { name: "Geography", count: 120 },
  { name: "Science", count: 95 },
  { name: "Programming", count: 210 },
  { name: "History", count: 85 },
  { name: "Mathematics", count: 150 },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function RunDetailPage() {
  const [selectedEvalIndex, setSelectedEvalIndex] = useState<
    number | undefined
  >(0);
  const [selectedCategory, setSelectedCategory] = useState<string>("");

  const job = MOCK_JOB;

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
                examples={MOCK_EVAL_EXAMPLES}
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
              categories={MOCK_CATEGORIES}
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
