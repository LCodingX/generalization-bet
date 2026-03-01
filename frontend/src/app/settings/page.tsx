"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { LogOut, User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  // Display Preferences
  const [animationSpeed, setAnimationSpeed] = useState<string>("normal");
  const [defaultSort, setDefaultSort] = useState<string>("tracin_desc");

  // Run Defaults
  const [defaultModel, setDefaultModel] = useState("meta-llama/Llama-3.1-8B");
  const [defaultLoraRank, setDefaultLoraRank] = useState(16);
  const [defaultCheckpointInterval, setDefaultCheckpointInterval] =
    useState(50);

  // Mock account
  const mockEmail = "researcher@university.edu";

  return (
    <div className="min-h-screen bg-background px-8 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Settings
        </h1>
      </div>

      <div className="mx-auto max-w-2xl space-y-6">
        {/* ----------------------------------------------------------------
            Display Preferences
        ---------------------------------------------------------------- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle className="text-base">Display Preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Chart animation speed */}
              <div className="space-y-2">
                <Label>Chart Animation Speed</Label>
                <Select
                  value={animationSpeed}
                  onValueChange={setAnimationSpeed}
                >
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fast">Fast</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="slow">Slow</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Controls the speed of chart transitions and animations.
                </p>
              </div>

              <Separator />

              {/* Default sort order */}
              <div className="space-y-2">
                <Label>Default Sort Order</Label>
                <Select value={defaultSort} onValueChange={setDefaultSort}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tracin_desc">
                      TracIn descending
                    </SelectItem>
                    <SelectItem value="tracin_asc">
                      TracIn ascending
                    </SelectItem>
                    <SelectItem value="datainf_desc">
                      DataInf descending
                    </SelectItem>
                    <SelectItem value="datainf_asc">
                      DataInf ascending
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Default column and direction for sorting influence score
                  tables.
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ----------------------------------------------------------------
            Run Defaults
        ---------------------------------------------------------------- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.08 }}
        >
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle className="text-base">Run Defaults</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Default model */}
              <div className="space-y-2">
                <Label htmlFor="default-model">Default Model</Label>
                <Input
                  id="default-model"
                  value={defaultModel}
                  onChange={(e) => setDefaultModel(e.target.value)}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  HuggingFace model identifier used when creating new runs.
                </p>
              </div>

              <Separator />

              {/* Default LoRA rank */}
              <div className="space-y-2">
                <Label htmlFor="default-lora-rank">Default LoRA Rank</Label>
                <Input
                  id="default-lora-rank"
                  type="number"
                  min={1}
                  max={256}
                  value={defaultLoraRank}
                  onChange={(e) =>
                    setDefaultLoraRank(parseInt(e.target.value, 10) || 0)
                  }
                  className="w-32 font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Rank of the low-rank adaptation matrices (higher = more
                  parameters).
                </p>
              </div>

              <Separator />

              {/* Default checkpoint interval */}
              <div className="space-y-2">
                <Label htmlFor="default-checkpoint-interval">
                  Default Checkpoint Interval
                </Label>
                <Input
                  id="default-checkpoint-interval"
                  type="number"
                  min={1}
                  value={defaultCheckpointInterval}
                  onChange={(e) =>
                    setDefaultCheckpointInterval(
                      parseInt(e.target.value, 10) || 0
                    )
                  }
                  className="w-32 font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Number of training steps between checkpoint saves.
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ----------------------------------------------------------------
            Account
        ---------------------------------------------------------------- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: 0.16 }}
        >
          <Card className="card-elevated">
            <CardHeader>
              <CardTitle className="text-base">Account</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-primary">
                  <User className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {mockEmail}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Signed in via SSO
                  </p>
                </div>
              </div>

              <Separator />

              <Button variant="outline" className="text-destructive">
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
