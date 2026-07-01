import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

export default async function ReportDetailsPage({
  params
}: {
  params: Promise<{ reportId: string }>;
}) {
  const { reportId } = await params;

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Платформа", "Отчеты", reportId]}
        subtitle="Карточка отчета подготовлена для просмотра содержимого, истории выгрузок и сценариев доставки."
        title={`Отчет ${reportId}`}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard subtitle="Раздел в подготовке" title="Сводка по отчету">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            Подробное содержимое отчета появится здесь после подключения прямых данных по выбранному документу.
          </p>
        </WidgetCard>

        <WidgetCard subtitle="Раздел в подготовке" title="История выгрузок">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            История экспорта, расписание и сведения о сформированных файлах будут доступны в следующей итерации.
          </p>
        </WidgetCard>
      </div>
    </div>
  );
}
