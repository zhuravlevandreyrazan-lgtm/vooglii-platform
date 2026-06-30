import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ReportTemplate } from "@/features/reports/types";

export function ReportTemplatesWidget({
  templates,
  loading = false,
  error = null
}: {
  templates: ReportTemplate[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={templates.length === 0}
      emptyMessage="Report templates will appear here when backend returns template metadata."
      error={error}
      loading={loading}
      subtitle="Report templates"
      title="Templates"
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {templates.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="text-base font-semibold">{item.name}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="neutral">{item.category}</StatusBadge>
              <StatusBadge tone="healthy">{item.status}</StatusBadge>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
