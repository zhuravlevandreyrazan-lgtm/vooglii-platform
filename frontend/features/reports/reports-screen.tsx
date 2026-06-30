import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { ReportCatalogWidget } from "@/features/reports/widgets/report-catalog-widget";
import { ReportExportCenterWidget } from "@/features/reports/widgets/report-export-center-widget";
import { ReportSourcesWidget } from "@/features/reports/widgets/report-sources-widget";
import { ReportTemplatesWidget } from "@/features/reports/widgets/report-templates-widget";
import { ReportTimelineWidget } from "@/features/reports/widgets/report-timeline-widget";
import { RecentReportsWidget } from "@/features/reports/widgets/recent-reports-widget";
import { ReportsOverviewWidget } from "@/features/reports/widgets/reports-overview-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { WorkspaceDiagnostics } from "@/shared/api";
import type { ReportsSnapshot } from "@/features/reports/types";

export function ReportsScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated
}: {
  data: ReportsSnapshot;
  diagnostics?: WorkspaceDiagnostics;
  loading?: boolean;
  error?: string | null;
  reload?: () => void;
  lastUpdated?: string | null;
}) {
  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <div className="flex flex-wrap gap-3">
            <OpenAutomationLink format="PDF" workspace="reports" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Refresh reports snapshot
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Platform", "Reports"]}
        subtitle="A single entry point to backend-ready reports, report history, templates, sources, and future export capabilities."
        title="Reports Center"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Using fallback data. Reports response is unavailable or invalid."
          title="Fallback snapshot active"
          tone="watch"
        />
      ) : null}

      <ReportsOverviewWidget
        error={error}
        loading={loading}
        summary={data.summary}
        updatedAt={lastUpdated ?? undefined}
      />

      <ReportCatalogWidget catalog={data.catalog} error={error} loading={loading} />

      <RecentReportsWidget error={error} loading={loading} recent={data.recent} />

      <ReportTemplatesWidget error={error} loading={loading} templates={data.templates} />

      <ReportExportCenterWidget error={error} exports={data.exports} loading={loading} />

      <ReportSourcesWidget error={error} loading={loading} sources={data.sources} />

      <ReportTimelineWidget error={error} loading={loading} timeline={data.timeline} />
    </div>
  );
}
