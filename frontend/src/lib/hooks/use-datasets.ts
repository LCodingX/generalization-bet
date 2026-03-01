"use client";

import { useCallback } from "react";
import { useLocalStorage } from "./use-local-storage";
import type { Dataset } from "@/lib/types";

const STORAGE_KEY = "gb-datasets";

export function useDatasets() {
  const [datasets, setDatasets] = useLocalStorage<Dataset[]>(STORAGE_KEY, []);

  const addDataset = useCallback(
    (name: string): Dataset => {
      const newDataset: Dataset = {
        id: `ds-${Date.now()}`,
        name,
        examples: [],
        created_at: new Date().toISOString(),
      };
      setDatasets((prev) => [...prev, newDataset]);
      return newDataset;
    },
    [setDatasets]
  );

  const updateDataset = useCallback(
    (id: string, updates: Partial<Dataset>) => {
      setDatasets((prev) =>
        prev.map((ds) => (ds.id === id ? { ...ds, ...updates } : ds))
      );
    },
    [setDatasets]
  );

  const deleteDataset = useCallback(
    (id: string) => {
      setDatasets((prev) => prev.filter((ds) => ds.id !== id));
    },
    [setDatasets]
  );

  return { datasets, addDataset, updateDataset, deleteDataset };
}
