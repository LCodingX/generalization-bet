"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import { useDatasets } from "@/lib/hooks/use-datasets";
import type { Dataset } from "@/lib/types";


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
  const { datasets, addDataset } = useDatasets();
  const router = useRouter();
  const [newName, setNewName] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  function handleCreate() {
    if (!newName.trim()) return;
    const ds = addDataset(newName.trim());
    setNewName("");
    setDialogOpen(false);
    router.push(`/datasets/${ds.id}`);
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
