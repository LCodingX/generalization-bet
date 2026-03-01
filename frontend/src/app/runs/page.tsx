"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import type { Job } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { RunCard } from "@/components/runs/RunCard";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_JOBS: Job[] = [
  {
    id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    status: "training",
    status_message: "Epoch 2/3 — loss 0.342",
    progress: 0.62,
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
    created_at: "2026-02-28T14:30:00Z",
    started_at: "2026-02-28T14:32:00Z",
    completed_at: null,
  },
  {
    id: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    status: "computing_tracin",
    status_message: "Computing TracIn scores — checkpoint 3/5",
    progress: 0.45,
    model_name: "mistralai/Mistral-7B-v0.1",
    hyperparameters: {
      learning_rate: 1e-4,
      epochs: 5,
      batch_size: 8,
      lora_rank: 32,
      lora_alpha: 64,
      lora_dropout: 0.1,
      checkpoint_interval: 100,
      max_seq_length: 1024,
      datainf_damping: 0.05,
    },
    created_at: "2026-02-27T09:15:00Z",
    started_at: "2026-02-27T09:20:00Z",
    completed_at: null,
  },
  {
    id: "c3d4e5f6-a7b8-9012-cdef-123456789012",
    status: "completed",
    status_message: "Run finished successfully",
    progress: 1.0,
    model_name: "meta-llama/Llama-2-13b-hf",
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
  },
  {
    id: "d4e5f6a7-b8c9-0123-defa-234567890123",
    status: "failed",
    status_message: "OOM error during training at step 412",
    progress: 0.33,
    model_name: "meta-llama/Llama-2-7b-hf",
    hyperparameters: {
      learning_rate: 5e-4,
      epochs: 5,
      batch_size: 16,
      lora_rank: 64,
      lora_alpha: 128,
      lora_dropout: 0.1,
      checkpoint_interval: 25,
      max_seq_length: 2048,
      datainf_damping: 0.1,
    },
    created_at: "2026-02-24T16:00:00Z",
    started_at: "2026-02-24T16:02:00Z",
    completed_at: "2026-02-24T17:15:00Z",
  },
  {
    id: "e5f6a7b8-c9d0-1234-efab-345678901234",
    status: "queued",
    status_message: null,
    progress: 0,
    model_name: "microsoft/phi-2",
    hyperparameters: {
      learning_rate: 3e-4,
      epochs: 2,
      batch_size: 4,
      lora_rank: 8,
      lora_alpha: 16,
      lora_dropout: 0.05,
      checkpoint_interval: 50,
      max_seq_length: 512,
      datainf_damping: 0.1,
    },
    created_at: "2026-03-01T08:00:00Z",
    started_at: null,
    completed_at: null,
  },
];

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

const ACTIVE_STATUSES = new Set([
  "training",
  "computing_tracin",
  "computing_datainf",
  "provisioning",
]);
const PAST_STATUSES = new Set(["completed", "failed"]);
const QUEUED_STATUSES = new Set(["queued"]);

function filterJobs(jobs: Job[], tab: string): Job[] {
  switch (tab) {
    case "active":
      return jobs.filter((j) => ACTIVE_STATUSES.has(j.status));
    case "past":
      return jobs.filter((j) => PAST_STATUSES.has(j.status));
    case "queued":
      return jobs.filter((j) => QUEUED_STATUSES.has(j.status));
    default:
      return jobs;
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function RunsPage() {
  const router = useRouter();
  const [tab, setTab] = useState("active");

  const filtered = filterJobs(MOCK_JOBS, tab);

  return (
    <div className="min-h-screen bg-background px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold font-sans text-foreground">
          Runs
        </h1>
        <Button asChild>
          <Link href="/runs/new">
            <Plus className="h-4 w-4" />
            New Run
          </Link>
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="past">Past</TabsTrigger>
          <TabsTrigger value="queued">Queued</TabsTrigger>
        </TabsList>

        <TabsContent value={tab} className="mt-6">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center py-24">
              <p className="text-sm text-muted-foreground">
                No runs yet. Create your first run.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <AnimatePresence mode="popLayout">
                {filtered.map((job, index) => (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{
                      duration: 0.25,
                      delay: index * 0.05,
                      ease: "easeOut",
                    }}
                  >
                    <RunCard
                      job={job}
                      onClick={() => router.push(`/runs/${job.id}`)}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
