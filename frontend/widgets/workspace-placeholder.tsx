import { ChartPlaceholder } from "@/shared/components/chart-placeholder";
import { TablePlaceholder } from "@/shared/components/table-placeholder";
import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

type PlaceholderWidget = {
  title: string;
  subtitle: string;
};

const DEFAULT_WIDGETS: PlaceholderWidget[] = [
  {
    title: "Ключевые сигналы",
    subtitle: "Здесь появятся основные показатели и сигналы раздела."
  },
  {
    title: "План действий",
    subtitle: "После подключения данных здесь будут рекомендации для работы."
  }
];

export function WorkspacePlaceholder({
  breadcrumb,
  description,
  widgets,
  title,
  eyebrow
}: {
  breadcrumb?: string[];
  description: string;
  widgets?: PlaceholderWidget[];
  title: string;
  eyebrow?: string;
}) {
  const resolvedBreadcrumb = breadcrumb ?? ["Платформа", eyebrow ?? title];
  const resolvedWidgets = widgets?.length ? widgets : DEFAULT_WIDGETS;

  return (
    <div className="space-y-6">
      <PageHeader breadcrumb={resolvedBreadcrumb} subtitle={description} title={title} />

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <ChartPlaceholder
          subtitle="После подключения раздела здесь появится визуальная сводка по ключевым показателям."
          title={`${title}: обзор`}
        />
        <WidgetCard subtitle="Что появится в разделе" title={`${title}: возможности`}>
          <div className="space-y-3">
            {resolvedWidgets.map((widget) => (
              <div key={widget.title} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="text-sm font-semibold">{widget.title}</div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{widget.subtitle}</p>
              </div>
            ))}
          </div>
        </WidgetCard>
      </div>

      <TablePlaceholder
        columns={["Приоритет", "Сигнал", "Ответственный", "Статус"]}
        title={`${title}: план действий`}
      />
    </div>
  );
}
