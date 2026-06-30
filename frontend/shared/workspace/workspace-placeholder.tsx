import { ChartPlaceholder } from "@/shared/components/chart-placeholder";
import { TablePlaceholder } from "@/shared/components/table-placeholder";
import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

type PlaceholderWidget = {
  title: string;
  subtitle: string;
};

export function WorkspacePlaceholder({
  breadcrumb,
  description,
  widgets,
  title
}: {
  breadcrumb: string[];
  description: string;
  widgets: PlaceholderWidget[];
  title: string;
}) {
  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={breadcrumb}
        subtitle={description}
        title={title}
      />

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <ChartPlaceholder
          subtitle="This workspace is ready for backend-connected executive widgets and deterministic insight layers."
          title={`${title} Signal Map`}
        />
        <WidgetCard
          subtitle="Coming soon"
          title={`${title} Workspace`}
        >
          <div className="space-y-3">
            {widgets.map((widget) => (
              <div key={widget.title} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="text-sm font-semibold">{widget.title}</div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{widget.subtitle}</p>
              </div>
            ))}
          </div>
        </WidgetCard>
      </div>

      <TablePlaceholder
        columns={["Priority", "Signal", "Owner", "State"]}
        title={`${title} Action Queue`}
      />
    </div>
  );
}
