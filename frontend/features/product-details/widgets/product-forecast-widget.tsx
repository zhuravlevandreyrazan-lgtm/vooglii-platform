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
    <WidgetCard error={error} loading={loading} subtitle="Прогноз" title="Ожидания по спросу">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <ProductDetailMetric
            label="Сводка"
            value={forecast.summary}
            hint="Текст прогноза приходит с backend и готов к будущему расширению графиками."
          />
        </div>
        <ProductDetailMetric label="Уверенность" value={forecast.confidence} />
        <ProductDetailMetric
          label="Следующая дата пополнения"
          value={forecast.nextReorderDate ?? "Ждем данные"}
        />
      </div>
    </WidgetCard>
  );
}
