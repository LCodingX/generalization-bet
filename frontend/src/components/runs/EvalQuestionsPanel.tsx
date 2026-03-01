"use client";

import type { EvalExample } from "@/lib/types";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface EvalQuestionsPanelProps {
  examples: EvalExample[];
  selectedIndex?: number;
  onSelect?: (index: number) => void;
}

export function EvalQuestionsPanel({
  examples,
  selectedIndex,
  onSelect,
}: EvalQuestionsPanelProps) {
  return (
    <ScrollArea className="h-full">
      <div className="space-y-1 p-1">
        {examples.map((example, index) => {
          const isSelected = selectedIndex === index;

          return (
            <button
              key={index}
              type="button"
              onClick={() => onSelect?.(index)}
              className={cn(
                "w-full text-left rounded-lg px-3 py-2.5 transition-colors",
                isSelected
                  ? "bg-indigo-50 border-l-2 border-indigo-500"
                  : "hover:bg-muted/50 border-l-2 border-transparent"
              )}
            >
              <div className="flex items-start gap-2.5">
                <span className="text-xs font-mono text-muted-foreground tabular-nums mt-0.5 shrink-0">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm leading-snug line-clamp-2">
                    {example.question}
                  </p>
                  {example.completion && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                      {example.completion}
                    </p>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </ScrollArea>
  );
}
