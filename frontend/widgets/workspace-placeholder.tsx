import { ChartPlaceholder } from "@/shared/components/chart-placeholder";
import { TablePlaceholder } from "@/shared/components/table-placeholder";
import { WorkspaceHeader } from "@/shared/components/workspace-header";

export function WorkspacePlaceholder({
  eyebrow,
  title,
  description
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-6">
      <WorkspaceHeader
        description={description}
        eyebrow={eyebrow}
        status="Раздел в подготовке"
        title={title}
      />
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <ChartPlaceholder
          subtitle="Раздел подготовлен для подключения реальных данных и сигналов."
          title={`${title}: обзор сигналов`}
        />
        <TablePlaceholder
          columns={["Приоритет", "Сигнал", "Ответственный", "Статус"]}
          title={`${title}: очередь действий`}
        />
      </div>
    </div>
  );
}
