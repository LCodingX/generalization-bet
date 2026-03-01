"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import type { Job } from "@/lib/types";
import { useJobs } from "@/lib/hooks/use-jobs";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { RunCard } from "@/components/runs/RunCard";

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
  const { jobs, loading, error } = useJobs();

  const filtered = filterJobs(jobs, tab);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="h-6 w-6 rounded-full border-2 border-muted-foreground border-t-transparent animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-8">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

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
                No {tab} runs
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
