import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { InventoryAlertsWidget } from "@/features/inventory/widgets/inventory-alerts-widget";
import { InventoryHealthWidget } from "@/features/inventory/widgets/inventory-health-widget";
import { InventoryHistoryWidget } from "@/features/inventory/widgets/inventory-history-widget";
import { InventoryRestockPlanWidget } from "@/features/inventory/widgets/inventory-restock-plan-widget";
import { InventorySummaryWidget } from "@/features/inventory/widgets/inventory-summary-widget";
import { InventorySupplyPriorityWidget } from "@/features/inventory/widgets/inventory-supply-priority-widget";
import { InventoryTableWidget } from "@/features/inventory/widgets/inventory-table-widget";
import { InventoryTimelineWidget } from "@/features/inventory/widgets/inventory-timeline-widget";
import { InventoryWarehouseWidget } from "@/features/inventory/widgets/inventory-warehouse-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { InventorySnapshot } from "@/features/inventory/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function InventoryScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated
}: {
  data: InventorySnapshot;
  diagnostics?: WorkspaceDiagnostics;
  loading?: boolean;
  error?: string | null;
  reload?: () => void;
  lastUpdated?: string | null;
}) {
  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <div className="flex flex-wrap gap-3">
            <OpenAutomationLink format="CSV" workspace="inventory" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Refresh inventory snapshot
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Platform", "Inventory"]}
        subtitle="A dedicated inventory intelligence workspace for stock coverage, restock plans, supply priority, warehouse visibility, and backend-ready forecast interpretation."
        title="Inventory"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Using fallback data. Backend response is unavailable or invalid."
          title="Fallback snapshot active"
          tone="watch"
        />
      ) : null}

      <InventorySummaryWidget
        error={error}
        loading={loading}
        summary={data.summary}
        updatedAt={lastUpdated ?? undefined}
      />

      <InventoryTableWidget error={error} items={data.items} loading={loading} />

      <InventoryHealthWidget error={error} health={data.health} loading={loading} />

      <InventoryRestockPlanWidget error={error} loading={loading} plan={data.restockPlan} />

      <InventorySupplyPriorityWidget
        error={error}
        loading={loading}
        priorities={data.supplyPriority}
      />

      <InventoryWarehouseWidget error={error} loading={loading} warehouses={data.warehouses} />

      <InventoryHistoryWidget error={error} history={data.history} loading={loading} />

      <InventoryAlertsWidget alerts={data.alerts} error={error} loading={loading} />

      <InventoryTimelineWidget error={error} loading={loading} timeline={data.timeline} />
    </div>
  );
}
