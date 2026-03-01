"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Play,
  Database,
  ClipboardList,
  Settings,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const NAV_ITEMS = [
  { href: "/runs", icon: Play, label: "Runs" },
  { href: "/datasets", icon: Database, label: "Datasets" },
  { href: "/evals", icon: ClipboardList, label: "Evals" },
  { href: "/settings", icon: Settings, label: "Settings" },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <TooltipProvider delayDuration={0}>
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-[68px] flex-col items-center border-r border-border bg-white py-4">
        {/* Logo */}
        <Link
          href="/runs"
          className="mb-8 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground font-mono text-lg font-bold"
        >
          &nabla;
        </Link>

        {/* Nav items */}
        <nav className="flex flex-1 flex-col items-center gap-1">
          {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
            const isActive = pathname.startsWith(href);
            return (
              <Tooltip key={href}>
                <TooltipTrigger asChild>
                  <Link
                    href={href}
                    className={cn(
                      "flex h-11 w-11 items-center justify-center rounded-xl transition-colors",
                      isActive
                        ? "bg-accent text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>
                  {label}
                </TooltipContent>
              </Tooltip>
            );
          })}
        </nav>
      </aside>
    </TooltipProvider>
  );
}
