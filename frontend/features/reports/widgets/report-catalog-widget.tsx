import Link from "next/link";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ReportItem } from "@/features/reports/types";

export function ReportCatalogWidget({
  catalog,
  loading = false,
  error = null
}: {
  catalog: ReportItem[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={catalog.length === 0}
      emptyMessage="Report catalog will appear here when backend returns available report metadata."
      error={error}
      loading={loading}
      subtitle="Available reports"
      title="Report Catalog"
    >
      <div className="space-y-3">
        {catalog.map((item) => (
          <Link
            key={item.id}
            className="block rounded-[22px] border border-[var(--line)] bg-white/70 p-4 transition hover:bg-white"
            href={item.href}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.name}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.description}</div>
              </div>
              <StatusBadge tone={item.status.tone}>{item.status.label}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="neutral">{item.category}</StatusBadge>
              <StatusBadge tone="accent">{item.source}</StatusBadge>
              <StatusBadge tone="watch">{item.updatedAt ?? "n/a"}</StatusBadge>
            </div>
          </Link>
        ))}
      </div>
    </WidgetCard>
  );
}
