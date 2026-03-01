"use client";

import { useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Upload,
  Edit,
  Save,
  ChevronLeft,
  ChevronRight,
  CheckSquare,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getCategoryColor } from "@/lib/colors";
import type { TrainingPair } from "@/lib/types";

// TODO: Fetch dataset rows and metadata from the API
const ALL_CATEGORIES: string[] = [];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DatasetDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const datasetName = `Dataset ${params.id}`;

  const [rows, setRows] = useState<TrainingPair[]>([]);
  const [editing, setEditing] = useState(false);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [bulkCategory, setBulkCategory] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);

  // Pagination (display-only)
  const [page] = useState(1);
  const totalPages = 1;

  // ---- Row editing helpers ------------------------------------------------

  function updateRow(index: number, field: keyof TrainingPair, value: string) {
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: value } : r))
    );
  }

  function toggleRowSelection(index: number) {
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function applyBulkCategory() {
    if (!bulkCategory || selectedRows.size === 0) return;
    setRows((prev) =>
      prev.map((r, i) =>
        selectedRows.has(i) ? { ...r, category: bulkCategory } : r
      )
    );
    setSelectedRows(new Set());
    setBulkCategory("");
  }

  // ---- File drop ----------------------------------------------------------

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) console.log("Dropped file:", file.name);
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) console.log("Selected file:", file.name);
    },
    []
  );

  // ---- Category color map (stable ordering) -------------------------------

  const categoryIndex = new Map<string, number>();
  ALL_CATEGORIES.forEach((c, i) => categoryIndex.set(c, i));

  return (
    <div className="min-h-screen bg-background px-8 py-10">
      {/* Back link + header */}
      <div className="mb-6 flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.push("/datasets")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {datasetName}
        </h1>
        <div className="ml-auto">
          <Button
            variant={editing ? "default" : "outline"}
            onClick={() => setEditing((v) => !v)}
          >
            {editing ? (
              <>
                <Save className="h-4 w-4" /> Save
              </>
            ) : (
              <>
                <Edit className="h-4 w-4" /> Edit
              </>
            )}
          </Button>
        </div>
      </div>

      {/* File upload zone */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <Card
          className={`card-elevated mb-6 cursor-pointer transition-colors ${
            dragOver ? "border-primary bg-accent" : ""
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <CardContent className="flex flex-col items-center justify-center py-10 text-center">
            <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">
              Drop .jsonl file here or click to browse
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Each line should be a JSON object with prompt, completion, and category fields.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".jsonl,.json"
              className="hidden"
              onChange={handleFileChange}
            />
          </CardContent>
        </Card>
      </motion.div>

      {/* Bulk category selector */}
      {editing && selectedRows.size > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="mb-4 flex items-center gap-3"
        >
          <CheckSquare className="h-4 w-4 text-primary" />
          <span className="text-sm text-muted-foreground">
            {selectedRows.size} row{selectedRows.size !== 1 ? "s" : ""} selected
          </span>
          <Select value={bulkCategory} onValueChange={setBulkCategory}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Assign category" />
            </SelectTrigger>
            <SelectContent>
              {ALL_CATEGORIES.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button size="sm" onClick={applyBulkCategory} disabled={!bulkCategory}>
            Apply
          </Button>
        </motion.div>
      )}

      {/* Inline hint */}
      <p className="mb-4 text-xs text-muted-foreground italic">
        Categories define training partitions for influence analysis.
      </p>

      {/* Data table */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.1 }}
      >
        <Card className="card-elevated overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/40">
                  {editing && (
                    <th className="w-10 px-4 py-3 text-left font-medium text-muted-foreground">
                      <input
                        type="checkbox"
                        className="rounded"
                        checked={selectedRows.size === rows.length && rows.length > 0}
                        onChange={(e) => {
                          if (e.target.checked)
                            setSelectedRows(new Set(rows.map((_, i) => i)));
                          else setSelectedRows(new Set());
                        }}
                      />
                    </th>
                  )}
                  <th className="w-12 px-4 py-3 text-left font-mono text-xs font-medium text-muted-foreground">
                    #
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                    Prompt
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                    Completion
                  </th>
                  <th className="w-40 px-4 py-3 text-left font-medium text-muted-foreground">
                    Category
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => {
                  const cIdx = categoryIndex.get(row.category) ?? i;
                  return (
                    <tr
                      key={i}
                      className={`border-b last:border-b-0 transition-colors ${
                        selectedRows.has(i) ? "bg-accent/50" : "hover:bg-muted/30"
                      }`}
                    >
                      {editing && (
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            className="rounded"
                            checked={selectedRows.has(i)}
                            onChange={() => toggleRowSelection(i)}
                          />
                        </td>
                      )}
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                        {i + 1}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <Input
                            value={row.prompt}
                            onChange={(e) => updateRow(i, "prompt", e.target.value)}
                            className="text-sm"
                          />
                        ) : (
                          <span className="text-foreground">{row.prompt}</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <Input
                            value={row.completion}
                            onChange={(e) =>
                              updateRow(i, "completion", e.target.value)
                            }
                            className="text-sm"
                          />
                        ) : (
                          <span className="font-mono text-xs text-foreground">
                            {row.completion}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editing ? (
                          <Select
                            value={row.category}
                            onValueChange={(v) => updateRow(i, "category", v)}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {ALL_CATEGORIES.map((cat) => (
                                <SelectItem key={cat} value={cat}>
                                  {cat}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge
                            variant="secondary"
                            className="text-[11px]"
                            style={{
                              backgroundColor: `${getCategoryColor(cIdx)}18`,
                              color: getCategoryColor(cIdx),
                            }}
                          >
                            {row.category}
                          </Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Showing {rows.length} of {rows.length * totalPages} examples
        </p>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon-sm" disabled={page === 1}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {Array.from({ length: totalPages }, (_, i) => (
            <Button
              key={i}
              variant={page === i + 1 ? "default" : "outline"}
              size="sm"
              className="h-8 w-8 p-0 text-xs"
            >
              {i + 1}
            </Button>
          ))}
          <Button variant="outline" size="icon-sm" disabled={page === totalPages}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
