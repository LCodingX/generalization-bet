"use client";

import { getCategoryColor } from "@/lib/colors";
import { cn } from "@/lib/utils";

interface TrainingCategoriesProps {
  categories: { name: string; count: number }[];
  selectedCategory?: string;
  onSelect?: (category: string) => void;
}

export function TrainingCategories({
  categories,
  selectedCategory,
  onSelect,
}: TrainingCategoriesProps) {
  function handleClick(name: string) {
    if (!onSelect) return;
    // Toggle: if already selected, deselect
    if (selectedCategory === name) {
      onSelect("");
    } else {
      onSelect(name);
    }
  }

  return (
    <div className="space-y-1">
      {categories.map((category, index) => {
        const isSelected = selectedCategory === category.name;
        const color = getCategoryColor(index);

        return (
          <button
            key={category.name}
            type="button"
            onClick={() => handleClick(category.name)}
            className={cn(
              "w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors text-left",
              isSelected
                ? "bg-indigo-50 text-foreground"
                : "hover:bg-muted/50 text-foreground"
            )}
          >
            <span
              className="h-3 w-3 rounded-full shrink-0"
              style={{ backgroundColor: color }}
            />
            <span className="flex-1 truncate">{category.name}</span>
            <span className="text-xs text-muted-foreground font-mono tabular-nums">
              {category.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
