import { Sparkles } from "lucide-react";
import { Card } from "@/shared/components/card";
import { StatusBadge } from "@/shared/components/status-badge";
import { localizeKnownText, localizeSourceName } from "@/shared/ui/status-labels";
import type { InsightItem } from "@/types/platform";

export function AiInsightCard({ insight }: { insight: InsightItem }) {
  return (
    <Card surface="accent" className="relative overflow-hidden">
      <div className="absolute -right-8 -top-8 h-36 w-36 rounded-full bg-white/8 blur-2xl" />
      <div className="relative">
        <div className="flex items-center justify-between gap-3">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white/80">
            <Sparkles size={14} />
            {insight.eyebrow}
          </div>
          <StatusBadge className="bg-white/12 text-white" tone={insight.tone}>
            {insight.confidence}
          </StatusBadge>
        </div>
        <h2 className="mt-5 max-w-2xl text-3xl font-semibold tracking-[-0.04em]">
          {insight.title}
        </h2>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-white/78">{insight.summary}</p>
        <div className="mt-6 flex flex-wrap gap-2">
          {insight.sources.map((source) => (
            <span
              key={source}
              className="rounded-full border border-white/10 bg-white/6 px-3 py-1 text-xs font-medium text-white/74"
            >
              {localizeKnownText(localizeSourceName(source), "данные кабинета")}
            </span>
          ))}
        </div>
      </div>
    </Card>
  );
}
