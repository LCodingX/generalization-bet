"use client";

import { useCallback } from "react";
import { useLocalStorage } from "./use-local-storage";
import type { EvalSet } from "@/lib/types";

const STORAGE_KEY = "gb-eval-sets";

export function useEvalSets() {
  const [evalSets, setEvalSets] = useLocalStorage<EvalSet[]>(STORAGE_KEY, []);

  const addEvalSet = useCallback(
    (name: string): EvalSet => {
      const newEvalSet: EvalSet = {
        id: `ev-${Date.now()}`,
        name,
        examples: [],
        created_at: new Date().toISOString(),
      };
      setEvalSets((prev) => [...prev, newEvalSet]);
      return newEvalSet;
    },
    [setEvalSets]
  );

  const updateEvalSet = useCallback(
    (id: string, updates: Partial<EvalSet>) => {
      setEvalSets((prev) =>
        prev.map((es) => (es.id === id ? { ...es, ...updates } : es))
      );
    },
    [setEvalSets]
  );

  const deleteEvalSet = useCallback(
    (id: string) => {
      setEvalSets((prev) => prev.filter((es) => es.id !== id));
    },
    [setEvalSets]
  );

  return { evalSets, addEvalSet, updateEvalSet, deleteEvalSet };
}
