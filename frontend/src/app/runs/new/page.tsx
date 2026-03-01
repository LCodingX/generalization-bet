"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, Rocket } from "lucide-react";

import { api } from "@/lib/api";
import { useDatasets } from "@/lib/hooks/use-datasets";
import { useEvalSets } from "@/lib/hooks/use-eval-sets";
import type {
  CreateJobRequest,
  EvalExample,
  Hyperparameters,
  JobCreatedResponse,
  TrainingPair,
} from "@/lib/types";
import { DEFAULT_HYPERPARAMETERS } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

// Sentinel value for the "None" select option
const NONE_VALUE = "__none__";

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

function parseTrainingPairs(raw: string): TrainingPair[] {
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error("Training dataset must be a JSON array.");
  }
  for (let i = 0; i < parsed.length; i++) {
    const item = parsed[i];
    if (
      typeof item.prompt !== "string" ||
      typeof item.completion !== "string" ||
      typeof item.category !== "string"
    ) {
      throw new Error(
        `Training pair at index ${i} must have "prompt", "completion", and "category" (all strings).`
      );
    }
  }
  return parsed as TrainingPair[];
}

function parseEvalExamples(raw: string): EvalExample[] {
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error("Eval examples must be a JSON array.");
  }
  for (let i = 0; i < parsed.length; i++) {
    const item = parsed[i];
    if (
      typeof item.question !== "string" ||
      typeof item.completion !== "string"
    ) {
      throw new Error(
        `Eval example at index ${i} must have "question" and "completion" (both strings).`
      );
    }
  }
  return parsed as EvalExample[];
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function NewRunPage() {
  const router = useRouter();
  const { datasets } = useDatasets();
  const { evalSets } = useEvalSets();

  const [modelName, setModelName] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(NONE_VALUE);
  const [datasetJson, setDatasetJson] = useState("");
  const [selectedEvalSetId, setSelectedEvalSetId] = useState<string>(NONE_VALUE);
  const [evalJson, setEvalJson] = useState("");
  const [hyperparameters, setHyperparameters] = useState<Hyperparameters>(
    DEFAULT_HYPERPARAMETERS
  );

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---- Dataset picker handler ----
  function handleDatasetSelect(value: string) {
    setSelectedDatasetId(value);
    if (value === NONE_VALUE) return;

    const dataset = datasets.find((ds) => ds.id === value);
    if (dataset && dataset.examples.length > 0) {
      setDatasetJson(JSON.stringify(dataset.examples, null, 2));
    }
  }

  // ---- Eval set picker handler ----
  function handleEvalSetSelect(value: string) {
    setSelectedEvalSetId(value);
    if (value === NONE_VALUE) return;

    const evalSet = evalSets.find((es) => es.id === value);
    if (evalSet && evalSet.examples.length > 0) {
      setEvalJson(JSON.stringify(evalSet.examples, null, 2));
    }
  }

  // ---- Submit ----
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Validate model name
    if (!modelName.trim()) {
      setError("Model name is required.");
      return;
    }

    // Parse and validate training pairs
    let trainingPairs: TrainingPair[] | undefined;
    if (datasetJson.trim()) {
      try {
        trainingPairs = parseTrainingPairs(datasetJson);
      } catch (err) {
        setError(
          `Invalid training dataset JSON: ${err instanceof Error ? err.message : String(err)}`
        );
        return;
      }
    }

    // Parse and validate eval examples
    let evalExamples: EvalExample[];
    if (!evalJson.trim()) {
      setError("Eval examples are required.");
      return;
    }
    try {
      evalExamples = parseEvalExamples(evalJson);
    } catch (err) {
      setError(
        `Invalid eval examples JSON: ${err instanceof Error ? err.message : String(err)}`
      );
      return;
    }

    // Build request payload
    const payload: CreateJobRequest = {
      model_name: modelName.trim(),
      hyperparameters,
      eval_examples: evalExamples,
    };
    if (trainingPairs && trainingPairs.length > 0) {
      payload.training_pairs = trainingPairs;
    }

    // Call backend API
    setSubmitting(true);
    try {
      const result = await api.post<JobCreatedResponse>(
        "/api/v1/jobs",
        payload
      );
      router.push(`/runs/${result.job_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
      setSubmitting(false);
    }
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

      {/* Error banner */}
      {error && (
        <div className="max-w-2xl mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

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

          {/* Dataset picker */}
          <div className="space-y-2">
            <Label>Saved dataset</Label>
            <Select
              value={selectedDatasetId}
              onValueChange={handleDatasetSelect}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Choose a dataset..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE_VALUE}>None (paste JSON below)</SelectItem>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id}>
                    {ds.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Raw JSON textarea */}
          <div className="space-y-2">
            <Label htmlFor="dataset-json">Dataset JSON</Label>
            <Textarea
              id="dataset-json"
              placeholder={DATASET_PLACEHOLDER}
              value={datasetJson}
              onChange={(e) => {
                setDatasetJson(e.target.value);
                // Clear dataset selection when user manually edits
                setSelectedDatasetId(NONE_VALUE);
              }}
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
            Select a saved eval set or paste eval question/completion pairs as
            JSON.
          </p>

          {/* Eval set picker */}
          <div className="space-y-2">
            <Label>Saved eval set</Label>
            <Select
              value={selectedEvalSetId}
              onValueChange={handleEvalSetSelect}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Choose an eval set..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE_VALUE}>None (paste JSON below)</SelectItem>
                {evalSets.map((es) => (
                  <SelectItem key={es.id} value={es.id}>
                    {es.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Raw JSON textarea */}
          <div className="space-y-2">
            <Label htmlFor="eval-json">Eval JSON</Label>
            <Textarea
              id="eval-json"
              placeholder={EVAL_PLACEHOLDER}
              value={evalJson}
              onChange={(e) => {
                setEvalJson(e.target.value);
                // Clear eval set selection when user manually edits
                setSelectedEvalSetId(NONE_VALUE);
              }}
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
        <Button type="submit" size="lg" className="w-full" disabled={submitting}>
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Launching...
            </>
          ) : (
            <>
              <Rocket className="h-4 w-4" />
              Launch Run
            </>
          )}
        </Button>
      </form>
    </div>
  );
}
