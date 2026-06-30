import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { HealthBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductAdvertising } from "@/features/product-details/types";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `₽${value.toLocaleString("en-US")}` : "n/a";
}

function formatPercent(value: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)}%` : "n/a";
}

function formatRatio(value: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)}x` : "n/a";
}

export function ProductAdvertisingWidget({
  advertising,
  loading = false,
  error = null
}: {
  advertising: ProductAdvertising;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={<HealthBadge label={advertising.adsHealth} />}
      subtitle="Advertising"
      title="Demand capture"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Spend" value={formatMoney(advertising.spend)} />
        <ProductDetailMetric label="ROAS" value={formatRatio(advertising.roas)} />
        <ProductDetailMetric label="ACOS" value={formatPercent(advertising.acos)} />
        <ProductDetailMetric
          label="Campaign count"
          value={typeof advertising.campaignCount === "number" ? String(advertising.campaignCount) : "n/a"}
        />
      </div>
    </WidgetCard>
  );
}
