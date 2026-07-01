import { WorkspacePlaceholder } from "@/widgets/workspace-placeholder";

export default function AnalyticsPage() {
  return (
    <WorkspacePlaceholder
      breadcrumb={["Платформа", "Аналитика"]}
      description="Раздел для детального анализа показателей, сравнений и динамики."
      title="Аналитика"
      widgets={[
        {
          title: "Сравнение периодов",
          subtitle: "Поможет быстро сравнить ключевые показатели по разным срезам."
        },
        {
          title: "Глубокая детализация",
          subtitle: "Здесь появятся расширенные отчеты и расшифровка изменений."
        }
      ]}
    />
  );
}
