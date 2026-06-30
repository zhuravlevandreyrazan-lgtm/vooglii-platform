import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

export default async function InventoryDetailsPage({
  params
}: {
  params: Promise<{ sku: string }>;
}) {
  const { sku } = await params;

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Platform", "Inventory", sku]}
        subtitle="Inventory drilldown architecture is ready. Detailed stock analytics, warehouse breakdowns, forecast panels, and restock history can connect here later without changing the surrounding UI."
        title={`Inventory ${sku}`}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard subtitle="Coming soon" title="SKU Stock Overview">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            Detailed stock overview widgets will connect here when direct inventory drilldown payloads are available from backend.
          </p>
        </WidgetCard>

        <WidgetCard subtitle="Coming soon" title="Supply Forecast">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            Forecast and replenishment drilldown panels will be added here in a later phase.
          </p>
        </WidgetCard>
      </div>
    </div>
  );
}
