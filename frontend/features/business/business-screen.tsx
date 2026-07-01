import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { StatusBadge } from "@/shared/status";
import { BusinessAlertsWidget } from "@/features/business/widgets/business-alerts-widget";
import { BusinessInsightWidget } from "@/features/business/widgets/business-insight-widget";
import { BusinessMetricWidget } from "@/features/business/widgets/business-metric-widget";
import { BusinessTopProductsWidget } from "@/features/business/widgets/business-top-products-widget";
import { BusinessTrendWidget } from "@/features/business/widgets/business-trend-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { BusinessAlert, BusinessInsight, BusinessKpis, BusinessSnapshot } from "@/features/business/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function BusinessScreen({
  data,
  kpis,
  insight,
  alerts,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated
}: {
  data: BusinessSnapshot;
  kpis: BusinessKpis;
  insight: BusinessInsight;
  alerts: BusinessAlert[];
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
            <OpenAutomationLink format="JSON" workspace="business" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Обновить данные
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Платформа", "Бизнес"]}
        subtitle="Выручка, прибыль, заказы и основные бизнес-показатели по вашему кабинету Wildberries."
        title="Бизнес"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Сейчас показываются резервные данные. Попробуйте обновить страницу позже."
          title="Основные данные временно недоступны"
          tone="watch"
        />
      ) : null}

      <BusinessInsightWidget error={error} insight={insight} loading={loading} updatedAt={lastUpdated ?? undefined} />

      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Ключевые показатели</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Ключевые показатели бизнеса</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {kpis.cards.map((metric) => (
            <BusinessMetricWidget key={metric.label} error={error} loading={loading} metric={metric} />
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Сравнение периодов</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Сравнение периодов</h2>
          </div>
          <StatusBadge tone={kpis.healthScore.tone}>{kpis.healthScore.value}</StatusBadge>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <BusinessTrendWidget error={error} loading={loading} trend={data.periods.today} />
          <BusinessTrendWidget error={error} loading={loading} trend={data.periods.yesterday} />
          <BusinessTrendWidget error={error} loading={loading} trend={data.periods.sevenDays} />
          <BusinessTrendWidget error={error} loading={loading} trend={data.periods.thirtyDays} />
        </div>
      </section>

      <BusinessTopProductsWidget error={error} loading={loading} products={data.topProducts} />

      <BusinessAlertsWidget alerts={alerts} error={error} loading={loading} />

      <div className="text-sm text-[var(--ink-soft)]">
        Обновлено: {lastUpdated ?? "нет данных"}
      </div>
    </div>
  );
}
