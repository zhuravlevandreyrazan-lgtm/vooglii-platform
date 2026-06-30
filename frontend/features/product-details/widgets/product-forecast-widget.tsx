import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { WidgetCard } from "@/shared/widgets";
import type { ProductForecast } from "@/features/product-details/types";

export function ProductForecastWidget({
  forecast,
  loading = false,
  error = null
}: {
  forecast: ProductForecast;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Forecast" title="Demand outlook">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <ProductDetailMetric
            label="Summary"
            value={forecast.summary}
            hint="Forecast text is backend-supplied and chart-ready for future expansion."
          />
        </div>
        <ProductDetailMetric label="Confidence" value={forecast.confidence} />
        <ProductDetailMetric
          label="Next reorder date"
          value={forecast.nextReorderDate ?? "Pending backend value"}
        />
      </div>
    </WidgetCard>
  );
}
