import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { HealthBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductAdvertising } from "@/features/product-details/types";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `в‚Ѕ${value.toLocaleString("en-US")}` : "Нет данных";
}

function formatPercent(value: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)}%` : "Нет данных";
}

function formatRatio(value: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)}x` : "Нет данных";
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
      subtitle="Реклама"
      title="Привлечение спроса"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Расходы" value={formatMoney(advertising.spend)} />
        <ProductDetailMetric label="ROAS" value={formatRatio(advertising.roas)} />
        <ProductDetailMetric label="ACOS" value={formatPercent(advertising.acos)} />
        <ProductDetailMetric
          label="Количество кампаний"
          value={typeof advertising.campaignCount === "number" ? String(advertising.campaignCount) : "Нет данных"}
        />
      </div>
    </WidgetCard>
  );
}
