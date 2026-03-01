"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Plus, Database, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { getCategoryColor } from "@/lib/colors";
import type { Dataset } from "@/lib/types";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_DATASETS: Dataset[] = [
  {
    id: "ds-1",
    name: "MMLU Math Subset",
    examples: [
      { prompt: "Solve for x: 2x + 3 = 7", completion: "x = 2", category: "algebra" },
      { prompt: "What is the derivative of x^2?", completion: "2x", category: "calculus" },
      { prompt: "Find the area of a circle with r=5", completion: "25pi", category: "geometry" },
      { prompt: "Simplify: (x+1)(x-1)", completion: "x^2 - 1", category: "algebra" },
    ],
    created_at: "2026-02-15T10:30:00Z",
  },
  {
    id: "ds-2",
    name: "Code Generation v2",
    examples: [
      { prompt: "Write a Python function to reverse a string", completion: "def reverse(s): return s[::-1]", category: "python" },
      { prompt: "Implement binary search in JavaScript", completion: "function binarySearch(arr, target) { ... }", category: "javascript" },
      { prompt: "Write a SQL query to find duplicates", completion: "SELECT col, COUNT(*) FROM t GROUP BY col HAVING COUNT(*) > 1", category: "sql" },
    ],
    created_at: "2026-02-20T14:00:00Z",
  },
  {
    id: "ds-3",
    name: "Clinical QA Pairs",
    examples: [
      { prompt: "What are the symptoms of type 2 diabetes?", completion: "Common symptoms include increased thirst, frequent urination, and fatigue.", category: "endocrine" },
      { prompt: "Describe the mechanism of action of metformin.", completion: "Metformin decreases hepatic glucose production and increases insulin sensitivity.", category: "pharmacology" },
    ],
    created_at: "2026-02-25T09:15:00Z",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getUniqueCategories(dataset: Dataset): string[] {
  return [...new Set(dataset.examples.map((e) => e.category))];
}

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

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>(MOCK_DATASETS);
  const [newName, setNewName] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  function handleCreate() {
    if (!newName.trim()) return;
    const ds: Dataset = {
      id: `ds-${Date.now()}`,
      name: newName.trim(),
      examples: [],
      created_at: new Date().toISOString(),
    };
    setDatasets((prev) => [ds, ...prev]);
    setNewName("");
    setDialogOpen(false);
  }

  return (
    <div className="min-h-screen bg-background px-8 py-10">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Datasets
        </h1>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4" />
              New Dataset
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Dataset</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="dataset-name">Name</Label>
                <Input
                  id="dataset-name"
                  placeholder="e.g. MMLU Science Subset"
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

      {/* Dataset cards */}
      {datasets.length === 0 ? (
        <Card className="card-elevated">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Database className="mb-4 h-10 w-10 text-muted-foreground" />
            <p className="text-lg font-medium text-foreground">
              No datasets yet.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Create your first dataset to get started.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((ds, i) => {
            const categories = getUniqueCategories(ds);
            return (
              <motion.div
                key={ds.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: i * 0.05 }}
              >
                <Link href={`/datasets/${ds.id}`}>
                  <Card className="card-elevated cursor-pointer transition-shadow hover:shadow-md">
                    <CardHeader>
                      <CardTitle className="text-base">{ds.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {/* Category chips */}
                      <div className="flex flex-wrap gap-1.5">
                        {categories.map((cat, ci) => (
                          <Badge
                            key={cat}
                            variant="secondary"
                            className="text-[11px]"
                            style={{
                              backgroundColor: `${getCategoryColor(ci)}18`,
                              color: getCategoryColor(ci),
                            }}
                          >
                            {cat}
                          </Badge>
                        ))}
                      </div>

                      {/* Meta row */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="font-mono">
                          {ds.examples.length} example{ds.examples.length !== 1 ? "s" : ""}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {formatDate(ds.created_at)}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
