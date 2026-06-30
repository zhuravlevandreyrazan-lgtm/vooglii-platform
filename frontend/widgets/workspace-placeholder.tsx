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
        status="Mock workspace"
        title={title}
      />
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <ChartPlaceholder
          subtitle="This placeholder is connected to the mock layer and ready for backend contracts."
          title={`${title} Signal Map`}
        />
        <TablePlaceholder
          columns={["Priority", "Signal", "Owner", "State"]}
          title={`${title} Action Queue`}
        />
      </div>
    </div>
  );
}
