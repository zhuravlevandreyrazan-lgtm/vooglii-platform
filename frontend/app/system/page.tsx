import { WorkspacePlaceholder } from "@/widgets/workspace-placeholder";

export default function SystemPage() {
  return (
    <WorkspacePlaceholder
      description="Раздел покажет состояние системы, синхронизаций, диагностики и готовности данных."
      eyebrow="Система"
      title="Система"
    />
  );
}
