"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Rocket } from "lucide-react";

import type { Hyperparameters } from "@/lib/types";
import { DEFAULT_HYPERPARAMETERS } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { HyperparameterForm } from "@/components/runs/HyperparameterForm";

// ---------------------------------------------------------------------------
// Placeholder formats
// ---------------------------------------------------------------------------

const DATASET_PLACEHOLDER = `[
  {
    "prompt": "What is the capital of France?",
    "completion": "The capital of France is Paris.",
    "category": "Geography"
  },
  {
    "prompt": "Explain gradient descent.",
    "completion": "Gradient descent is an optimization algorithm...",
    "category": "ML"
  }
]`;

const EVAL_PLACEHOLDER = `[
  {
    "question": "What is the capital of Germany?",
    "completion": "The capital of Germany is Berlin."
  },
  {
    "question": "How does backpropagation work?",
    "completion": "Backpropagation computes gradients..."
  }
]`;

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function NewRunPage() {
  const [modelName, setModelName] = useState("");
  const [datasetJson, setDatasetJson] = useState("");
  const [evalJson, setEvalJson] = useState("");
  const [hyperparameters, setHyperparameters] = useState<Hyperparameters>(
    DEFAULT_HYPERPARAMETERS
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    console.log("Launch Run submitted", {
      modelName,
      datasetJson,
      evalJson,
      hyperparameters,
    });
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
      <h1 className="text-2xl font-semibold font-sans text-foreground mb-8">
        New Run
      </h1>

      {/* Form */}
      <form onSubmit={handleSubmit} className="max-w-2xl space-y-8">
        {/* Model Name */}
        <div className="card-elevated rounded-xl border border-border bg-white p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Model</h2>
          <div className="space-y-2">
            <Label htmlFor="model-name">Model name</Label>
            <Input
              id="model-name"
              type="text"
              placeholder="meta-llama/Llama-2-7b-hf"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="font-mono"
            />
          </div>
        </div>

        {/* Dataset */}
        <div className="card-elevated rounded-xl border border-border bg-white p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Training Dataset
          </h2>
          <p className="text-sm text-muted-foreground">
            Select a saved dataset or paste inline data as JSON.
          </p>
          <div className="space-y-2">
            <Label htmlFor="dataset-json">Dataset JSON</Label>
            <Textarea
              id="dataset-json"
              placeholder={DATASET_PLACEHOLDER}
              value={datasetJson}
              onChange={(e) => setDatasetJson(e.target.value)}
              className="min-h-[180px] font-mono text-xs"
            />
          </div>
        </div>

        {/* Eval Examples */}
        <div className="card-elevated rounded-xl border border-border bg-white p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Eval Examples
          </h2>
          <p className="text-sm text-muted-foreground">
            Paste eval question/completion pairs as JSON.
          </p>
          <div className="space-y-2">
            <Label htmlFor="eval-json">Eval JSON</Label>
            <Textarea
              id="eval-json"
              placeholder={EVAL_PLACEHOLDER}
              value={evalJson}
              onChange={(e) => setEvalJson(e.target.value)}
              className="min-h-[140px] font-mono text-xs"
            />
          </div>
        </div>

        {/* Hyperparameters */}
        <div className="card-elevated rounded-xl border border-border bg-white p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Hyperparameters
          </h2>
          <Separator />
          <HyperparameterForm
            values={hyperparameters}
            onChange={setHyperparameters}
          />
        </div>

        {/* Submit */}
        <Button type="submit" size="lg" className="w-full">
          <Rocket className="h-4 w-4" />
          Launch Run
        </Button>
      </form>
    </div>
  );
}
