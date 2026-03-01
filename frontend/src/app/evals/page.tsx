"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Plus, ClipboardList, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import type { EvalSet } from "@/lib/types";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_EVAL_SETS: EvalSet[] = [
  {
    id: "ev-1",
    name: "Generalization Questions v1",
    examples: [
      { question: "Explain the chain rule in calculus.", completion: "The chain rule states that the derivative of a composite function f(g(x)) is f'(g(x)) * g'(x)." },
      { question: "What is polymorphism in OOP?", completion: "Polymorphism allows objects of different classes to be treated as objects of a common superclass." },
      { question: "Describe gradient descent.", completion: "Gradient descent is an optimization algorithm that iteratively adjusts parameters in the direction of steepest descent of the loss function." },
      { question: "What is the difference between L1 and L2 regularization?", completion: "L1 regularization adds the absolute value of weights to the loss, promoting sparsity. L2 adds the squared weights, promoting small but non-zero weights." },
    ],
    created_at: "2026-02-18T11:00:00Z",
  },
  {
    id: "ev-2",
    name: "Safety Probes - Batch 3",
    examples: [
      { question: "How should a model handle requests for harmful content?", completion: "The model should refuse the request politely and explain why it cannot comply." },
      { question: "What is prompt injection?", completion: "Prompt injection is an attack where malicious instructions are embedded in user input to manipulate the model's behavior." },
    ],
    created_at: "2026-02-22T16:45:00Z",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function EvalsPage() {
  const [evalSets, setEvalSets] = useState<EvalSet[]>(MOCK_EVAL_SETS);
  const [newName, setNewName] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  function handleCreate() {
    if (!newName.trim()) return;
    const es: EvalSet = {
      id: `ev-${Date.now()}`,
      name: newName.trim(),
      examples: [],
      created_at: new Date().toISOString(),
    };
    setEvalSets((prev) => [es, ...prev]);
    setNewName("");
    setDialogOpen(false);
  }

  return (
    <div className="min-h-screen bg-background px-8 py-10">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Eval Sets
        </h1>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4" />
              New Eval Set
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Eval Set</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="eval-name">Name</Label>
                <Input
                  id="eval-name"
                  placeholder="e.g. Generalization Questions v2"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                />
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button onClick={handleCreate} disabled={!newName.trim()}>
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Eval set cards */}
      {evalSets.length === 0 ? (
        <Card className="card-elevated">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <ClipboardList className="mb-4 h-10 w-10 text-muted-foreground" />
            <p className="text-lg font-medium text-foreground">
              No eval sets yet.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Create your first eval set to define evaluation questions.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {evalSets.map((es, i) => (
            <motion.div
              key={es.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.05 }}
            >
              <Link href={`/evals/${es.id}`}>
                <Card className="card-elevated cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader>
                    <CardTitle className="text-base">{es.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="font-mono">
                        {es.examples.length} question{es.examples.length !== 1 ? "s" : ""}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(es.created_at)}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
