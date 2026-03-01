"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import type { EvalExample } from "@/lib/types";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_EXAMPLES: EvalExample[] = [
  {
    question: "Explain the chain rule in calculus and provide an example.",
    completion:
      "The chain rule states that the derivative of f(g(x)) is f'(g(x)) * g'(x). For example, if h(x) = sin(x^2), then h'(x) = cos(x^2) * 2x.",
  },
  {
    question: "What is the difference between supervised and unsupervised learning?",
    completion:
      "Supervised learning uses labeled data to learn a mapping from inputs to outputs. Unsupervised learning discovers patterns in unlabeled data, such as clustering or dimensionality reduction.",
  },
  {
    question: "Describe how attention mechanisms work in transformers.",
    completion:
      "Attention computes a weighted sum of value vectors, where weights are determined by the compatibility (dot product) between query and key vectors, scaled and passed through softmax.",
  },
  {
    question: "What is LoRA and why is it useful for fine-tuning?",
    completion:
      "LoRA (Low-Rank Adaptation) freezes the pretrained model weights and injects trainable low-rank decomposition matrices into each layer, dramatically reducing the number of trainable parameters while maintaining performance.",
  },
];

const EVAL_SET_META: Record<string, string> = {
  "ev-1": "Generalization Questions v1",
  "ev-2": "Safety Probes - Batch 3",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function EvalSetDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const evalSetName = EVAL_SET_META[params.id] ?? `Eval Set ${params.id}`;

  const [examples, setExamples] = useState<EvalExample[]>(MOCK_EXAMPLES);

  function updateExample(
    index: number,
    field: keyof EvalExample,
    value: string
  ) {
    setExamples((prev) =>
      prev.map((ex, i) => (i === index ? { ...ex, [field]: value } : ex))
    );
  }

  function deleteExample(index: number) {
    setExamples((prev) => prev.filter((_, i) => i !== index));
  }

  function addExample() {
    setExamples((prev) => [...prev, { question: "", completion: "" }]);
  }

  return (
    <div className="min-h-screen bg-background px-8 py-10">
      {/* Back link + header */}
      <div className="mb-6 flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/evals")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {evalSetName}
        </h1>
      </div>

      {/* Inline hint */}
      <p className="mb-6 text-xs text-muted-foreground italic">
        Completions are required -- the system computes gradients of the loss on
        these question-answer pairs.
      </p>

      {/* Examples list */}
      <div className="space-y-4">
        {examples.map((ex, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: i * 0.04 }}
          >
            <Card className="card-elevated">
              <CardContent className="space-y-4">
                <div className="flex items-start justify-between gap-4">
                  {/* Index number */}
                  <span className="mt-2 shrink-0 font-mono text-sm text-muted-foreground tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>

                  {/* Fields */}
                  <div className="flex-1 space-y-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">
                        Question
                      </label>
                      <Textarea
                        value={ex.question}
                        onChange={(e) =>
                          updateExample(i, "question", e.target.value)
                        }
                        placeholder="Enter eval question..."
                        className="min-h-[60px] text-sm"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-muted-foreground">
                        Completion
                      </label>
                      <Textarea
                        value={ex.completion}
                        onChange={(e) =>
                          updateExample(i, "completion", e.target.value)
                        }
                        placeholder="Enter expected completion..."
                        className="min-h-[60px] font-mono text-xs"
                      />
                    </div>
                  </div>

                  {/* Delete button */}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="mt-2 shrink-0 text-muted-foreground hover:text-destructive"
                    onClick={() => deleteExample(i)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Add question button */}
      <Separator className="my-6" />
      <Button variant="outline" onClick={addExample} className="w-full">
        <Plus className="h-4 w-4" />
        Add Question
      </Button>
    </div>
  );
}
