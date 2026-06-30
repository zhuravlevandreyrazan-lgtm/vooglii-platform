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
        breadcrumb={["Platform", "Reports", reportId]}
        subtitle="Report details architecture is ready. Detailed report content, export history, and scheduled delivery controls can connect here later without changing the surrounding UI."
        title={`Report ${reportId}`}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard subtitle="Coming soon" title="Report Overview">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            Detailed report overview widgets will connect here when direct report payloads are available from backend.
          </p>
        </WidgetCard>

        <WidgetCard subtitle="Coming soon" title="Export History">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            Export history, scheduling, and generated file metadata will be added here in a later phase.
          </p>
        </WidgetCard>
      </div>
    </div>
  );
}
