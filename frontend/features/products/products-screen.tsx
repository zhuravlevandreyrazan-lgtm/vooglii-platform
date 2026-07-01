import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { ProductAlertsWidget } from "@/features/products/widgets/product-alerts-widget";
import { ProductHealthWidget } from "@/features/products/widgets/product-health-widget";
import { ProductHistoryWidget } from "@/features/products/widgets/product-history-widget";
import { ProductInventoryPreviewWidget } from "@/features/products/widgets/product-inventory-preview-widget";
import { ProductRecommendationsWidget } from "@/features/products/widgets/product-recommendations-widget";
import { ProductsSummaryWidget } from "@/features/products/widgets/products-summary-widget";
import { ProductsTableWidget } from "@/features/products/widgets/products-table-widget";
import { ProductTimelineWidget } from "@/features/products/widgets/product-timeline-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { ProductSnapshot } from "@/features/products/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function ProductsScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated
}: {
  data: ProductSnapshot;
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
            <OpenAutomationLink format="JSON" workspace="products" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Обновить данные
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Платформа", "Товары"]}
        subtitle="SKU-аналитика, рекомендации, история и товарные сигналы по ассортименту."
        title="Товары"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Сейчас показываются резервные данные. Попробуйте обновить страницу позже."
          title="Товарные данные временно недоступны"
          tone="watch"
        />
      ) : null}

      <ProductsSummaryWidget
        error={error}
        loading={loading}
        summary={data.summary}
        updatedAt={lastUpdated ?? undefined}
      />

      <ProductsTableWidget error={error} loading={loading} products={data.products} />

      <ProductHealthWidget error={error} loading={loading} products={data.products} />

      <ProductRecommendationsWidget
        error={error}
        loading={loading}
        recommendations={data.recommendations}
      />

      <ProductHistoryWidget error={error} history={data.history} loading={loading} />

      <ProductInventoryPreviewWidget
        error={error}
        loading={loading}
        products={data.inventoryPreview}
      />

      <ProductAlertsWidget alerts={data.alerts} error={error} loading={loading} />

      <ProductTimelineWidget error={error} loading={loading} timeline={data.timeline} />
    </div>
  );
}
