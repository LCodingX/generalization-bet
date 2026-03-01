"use client";

import { useState } from "react";
import type { Hyperparameters } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight } from "lucide-react";

interface HyperparameterFormProps {
  values: Hyperparameters;
  onChange?: (hp: Hyperparameters) => void;
  readOnly?: boolean;
}

interface FieldDef {
  key: keyof Hyperparameters;
  label: string;
  step?: number;
  min?: number;
  max?: number;
}

const BASIC_FIELDS: FieldDef[] = [
  { key: "learning_rate", label: "Learning Rate", step: 0.0001, min: 0 },
  { key: "epochs", label: "Epochs", step: 1, min: 1 },
  { key: "batch_size", label: "Batch Size", step: 1, min: 1 },
  { key: "lora_rank", label: "LoRA Rank", step: 1, min: 1 },
  { key: "lora_alpha", label: "LoRA Alpha", step: 1, min: 1 },
  { key: "max_seq_length", label: "Max Seq Length", step: 1, min: 1 },
];

const ADVANCED_FIELDS: FieldDef[] = [
  { key: "checkpoint_interval", label: "Checkpoint Interval", step: 1, min: 1 },
  { key: "datainf_damping", label: "DataInf Damping", step: 0.01, min: 0 },
  { key: "lora_dropout", label: "LoRA Dropout", step: 0.01, min: 0, max: 1 },
];

function formatValue(value: number): string {
  if (value < 0.001 && value > 0) return value.toExponential(1);
  return String(value);
}

export function HyperparameterForm({
  values,
  onChange,
  readOnly = false,
}: HyperparameterFormProps) {
  const [advancedOpen, setAdvancedOpen] = useState(false);

  function handleChange(key: keyof Hyperparameters, raw: string) {
    if (!onChange) return;
    const parsed = parseFloat(raw);
    if (isNaN(parsed)) return;
    onChange({ ...values, [key]: parsed });
  }

  function renderReadOnlyField(field: FieldDef) {
    return (
      <div
        key={field.key}
        className="flex items-center justify-between py-2 border-b border-border/50 last:border-0"
      >
        <span className="text-sm text-muted-foreground">{field.label}</span>
        <span className="text-sm font-mono tabular-nums">
          {formatValue(values[field.key])}
        </span>
      </div>
    );
  }

  function renderEditableField(field: FieldDef) {
    return (
      <div key={field.key} className="grid grid-cols-2 items-center gap-4">
        <Label htmlFor={`hp-${field.key}`} className="text-sm">
          {field.label}
        </Label>
        <Input
          id={`hp-${field.key}`}
          type="number"
          value={values[field.key]}
          onChange={(e) => handleChange(field.key, e.target.value)}
          step={field.step}
          min={field.min}
          max={field.max}
          className="font-mono tabular-nums"
        />
      </div>
    );
  }

  if (readOnly) {
    return (
      <div className="space-y-0">
        {BASIC_FIELDS.map(renderReadOnlyField)}
        {ADVANCED_FIELDS.map(renderReadOnlyField)}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Basic fields */}
      <div>
        <h4 className="text-sm font-medium text-foreground mb-4">Basic</h4>
        <div className="space-y-3">
          {BASIC_FIELDS.map(renderEditableField)}
        </div>
      </div>

      {/* Advanced fields (collapsible) */}
      <div>
        <button
          type="button"
          onClick={() => setAdvancedOpen(!advancedOpen)}
          className="flex items-center gap-1.5 text-sm font-medium text-foreground hover:text-primary transition-colors mb-4"
        >
          {advancedOpen ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          Advanced
        </button>
        {advancedOpen && (
          <div className="space-y-3">
            {ADVANCED_FIELDS.map(renderEditableField)}
          </div>
        )}
      </div>
    </div>
  );
}
