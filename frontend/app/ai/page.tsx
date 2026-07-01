import { WorkspacePlaceholder } from "@/widgets/workspace-placeholder";

export default function AiPage() {
  return (
    <WorkspacePlaceholder
      breadcrumb={["Платформа", "ИИ-советник"]}
      description="Раздел для рекомендаций, объяснений и рабочих сценариев с ИИ."
      title="ИИ-советник"
      widgets={[
        {
          title: "Рекомендации по действиям",
          subtitle: "Здесь будут собраны советы по продажам, рекламе и финансам."
        },
        {
          title: "Объяснение решений",
          subtitle: "Пояснения к рекомендациям и ключевым сигналам кабинета."
        }
      ]}
    />
  );
}
