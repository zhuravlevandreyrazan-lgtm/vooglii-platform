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
        breadcrumb={["Платформа", "Остатки", sku]}
        subtitle="Карточка товара подготовлена для детальной аналитики по остаткам, складам, прогнозу и пополнению."
        title={`Остатки по SKU ${sku}`}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard subtitle="Раздел в подготовке" title="Сводка по остаткам SKU">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            Детальная аналитика по остаткам появится здесь после подключения прямого drilldown по SKU.
          </p>
        </WidgetCard>

        <WidgetCard subtitle="Раздел в подготовке" title="Прогноз пополнения">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            Прогноз поставок и сценарии пополнения станут доступны на следующем этапе развития раздела.
          </p>
        </WidgetCard>
      </div>
    </div>
  );
}
