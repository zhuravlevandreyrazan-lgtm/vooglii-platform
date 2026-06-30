import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { FinanceAlertsWidget } from "@/features/finance/widgets/finance-alerts-widget";
import { FinanceDifferenceWidget } from "@/features/finance/widgets/finance-difference-widget";
import { FinanceMetricWidget } from "@/features/finance/widgets/finance-metric-widget";
import { FinanceQualityWidget } from "@/features/finance/widgets/finance-quality-widget";
import { FinanceSummaryWidget } from "@/features/finance/widgets/finance-summary-widget";
import { FinanceTimelineWidget } from "@/features/finance/widgets/finance-timeline-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { FinanceSnapshot } from "@/features/finance/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function FinanceScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated
}: {
  data: FinanceSnapshot;
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
            <OpenAutomationLink format="CSV" workspace="finance" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Refresh finance snapshot
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Platform", "Finance"]}
        subtitle="A finance workspace for safe operating profit visibility, official profit status, trust, coverage, residual usage, and backend-provided finance quality signals."
        title="Finance"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Using fallback data. Backend response is unavailable or invalid."
          title="Fallback snapshot active"
          tone="watch"
        />
      ) : null}

      <FinanceSummaryWidget error={error} loading={loading} summary={data.summary} updatedAt={lastUpdated ?? undefined} />

      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Profit Widgets</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Prepared finance indicators from backend-ready snapshot</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {data.metrics.map((metric) => (
            <FinanceMetricWidget key={metric.label} error={error} loading={loading} metric={metric} />
          ))}
        </div>
      </section>

      <FinanceDifferenceWidget difference={data.difference} error={error} loading={loading} />

      <FinanceQualityWidget error={error} loading={loading} quality={data.quality} />

      <FinanceAlertsWidget alerts={data.alerts} error={error} loading={loading} />

      <FinanceTimelineWidget error={error} loading={loading} timeline={data.timeline} />
    </div>
  );
}
