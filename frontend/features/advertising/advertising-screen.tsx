import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { AdvertisingAlertsWidget } from "@/features/advertising/widgets/advertising-alerts-widget";
import { AdvertisingCampaignsWidget } from "@/features/advertising/widgets/advertising-campaigns-widget";
import { AdvertisingHealthWidget } from "@/features/advertising/widgets/advertising-health-widget";
import { AdvertisingMetricWidget } from "@/features/advertising/widgets/advertising-metric-widget";
import { AdvertisingRecommendationsWidget } from "@/features/advertising/widgets/advertising-recommendations-widget";
import { AdvertisingSummaryWidget } from "@/features/advertising/widgets/advertising-summary-widget";
import { AdvertisingTimelineWidget } from "@/features/advertising/widgets/advertising-timeline-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { AdvertisingSnapshot } from "@/features/advertising/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function AdvertisingScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated
}: {
  data: AdvertisingSnapshot;
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
            <OpenAutomationLink format="CSV" workspace="advertising" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Обновить данные
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Платформа", "Реклама"]}
        subtitle="Расходы, эффективность кампаний, атрибуция и рекомендации по рекламе."
        title="Реклама"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Сейчас показываются резервные данные. Попробуйте обновить страницу позже."
          title="Рекламные данные временно недоступны"
          tone="watch"
        />
      ) : null}

      <AdvertisingSummaryWidget
        error={error}
        loading={loading}
        summary={data.summary}
        updatedAt={lastUpdated ?? undefined}
      />

      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Показатели рекламы</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Главное по рекламным кампаниям</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {data.metrics.map((metric) => (
            <AdvertisingMetricWidget key={metric.label} error={error} loading={loading} metric={metric} />
          ))}
        </div>
      </section>

      <AdvertisingCampaignsWidget campaigns={data.campaigns} error={error} loading={loading} />

      <AdvertisingRecommendationsWidget
        error={error}
        loading={loading}
        recommendations={data.recommendations}
      />

      <AdvertisingHealthWidget error={error} health={data.health} loading={loading} />

      <AdvertisingAlertsWidget alerts={data.alerts} error={error} loading={loading} />

      <AdvertisingTimelineWidget error={error} loading={loading} timeline={data.timeline} />
    </div>
  );
}
