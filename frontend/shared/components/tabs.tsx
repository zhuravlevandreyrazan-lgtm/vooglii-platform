"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { cn } from "@/shared/lib/cn";

export type TabDefinition = {
  id: string;
  label: string;
  content: ReactNode;
};

export function Tabs({ tabs }: { tabs: TabDefinition[] }) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.id ?? "");
  const current = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const isActive = tab.id === current?.id;
          return (
            <button
              key={tab.id}
              className={cn(
                "rounded-full px-4 py-2 text-sm font-semibold transition",
                isActive
                  ? "bg-[var(--ink)] text-white"
                  : "bg-white/70 text-[var(--ink-soft)] hover:bg-white"
              )}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div>{current?.content}</div>
    </div>
  );
}
