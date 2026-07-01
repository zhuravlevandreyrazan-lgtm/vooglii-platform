import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { ProductAdvertisingWidget } from "@/features/product-details/widgets/product-advertising-widget";
import { ProductFinanceWidget } from "@/features/product-details/widgets/product-finance-widget";
import { ProductForecastWidget } from "@/features/product-details/widgets/product-forecast-widget";
import { ProductHistoryWidget } from "@/features/product-details/widgets/product-history-widget";
import { ProductInsightWidget } from "@/features/product-details/widgets/product-insight-widget";
import { ProductInventoryWidget } from "@/features/product-details/widgets/product-inventory-widget";
import { ProductOverviewWidget } from "@/features/product-details/widgets/product-overview-widget";
import { ProductQuickActionsWidget } from "@/features/product-details/widgets/product-quick-actions-widget";
import { ProductRecommendationsWidget } from "@/features/product-details/widgets/product-recommendations-widget";
import { ProductSalesWidget } from "@/features/product-details/widgets/product-sales-widget";
import { ProductDetailsTimelineWidget } from "@/features/product-details/widgets/product-timeline-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { ProductDetailsSnapshot } from "@/features/product-details/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

function formatMoney(value: number | null) {
  return value === null ? "Нет данных" : `в‚Ѕ${value.toLocaleString("en-US")}`;
}

function formatCount(value: number | null) {
  return value === null ? "Нет данных" : value.toLocaleString("en-US");
}

export function ProductDetailsScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated,
  workspaceContext
}: {
  data: ProductDetailsSnapshot;
  diagnostics?: WorkspaceDiagnostics;
  loading?: boolean;
  error?: string | null;
  reload?: () => void;
  lastUpdated?: string | null;
  workspaceContext?: {
    organizationId?: string | null;
    organization?: string | null;
    cabinetId?: string | null;
    cabinet?: string | null;
    mode?: string | null;
  };
}) {
  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <div className="flex flex-wrap gap-3">
            <OpenAutomationLink format="JSON" sku={data.overview.sku} workspace="products" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Обновить данные
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Платформа", "Товары", data.overview.sku]}
        subtitle="Карточка SKU с продажами, прибылью, рекламой, остатками, историей и рекомендациями в одном экране."
        title={data.overview.name}
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge context={workspaceContext} diagnostics={diagnostics} />

      {workspaceContext?.organization || workspaceContext?.cabinet ? (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Организация</p>
            <p className="mt-2 text-sm font-semibold">{workspaceContext.organization ?? "нет данных"}</p>
          </div>
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Текущий кабинет</p>
            <p className="mt-2 text-sm font-semibold">{workspaceContext.cabinet ?? "нет данных"}</p>
          </div>
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Режим работы</p>
            <p className="mt-2 text-sm font-semibold">{workspaceContext.mode ?? "нет данных"}</p>
          </div>
        </div>
      ) : null}

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Сейчас показываются резервные данные. Ответ по SKU временно недоступен или еще не готов."
          title="Данные по товару временно недоступны"
          tone="watch"
        />
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-[26px] border border-[var(--line)] bg-white/80 p-5 shadow-[var(--shadow-soft)]">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Выручка</p>
          <p className="mt-3 text-2xl font-semibold tracking-[-0.04em]">{formatMoney(data.sales.revenue)}</p>
        </div>
        <div className="rounded-[26px] border border-[var(--line)] bg-white/80 p-5 shadow-[var(--shadow-soft)]">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Прибыль</p>
          <p className="mt-3 text-2xl font-semibold tracking-[-0.04em]">{formatMoney(data.finance.profit)}</p>
        </div>
        <div className="rounded-[26px] border border-[var(--line)] bg-white/80 p-5 shadow-[var(--shadow-soft)]">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Остаток</p>
          <p className="mt-3 text-2xl font-semibold tracking-[-0.04em]">{formatCount(data.inventory.stock)}</p>
        </div>
        <div className="rounded-[26px] border border-[var(--line)] bg-white/80 p-5 shadow-[var(--shadow-soft)]">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Состояние рекламы</p>
          <p className="mt-3 text-2xl font-semibold tracking-[-0.04em]">{data.advertising.adsHealth}</p>
        </div>
      </div>

      <ProductOverviewWidget
        deepLinks={data.deepLinks}
        error={error}
        loading={loading}
        overview={data.overview}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <ProductSalesWidget error={error} loading={loading} sales={data.sales} />
        <ProductFinanceWidget error={error} finance={data.finance} loading={loading} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <ProductAdvertisingWidget advertising={data.advertising} error={error} loading={loading} />
        <ProductInventoryWidget error={error} inventory={data.inventory} loading={loading} />
      </div>

      <ProductForecastWidget error={error} forecast={data.forecast} loading={loading} />

      <ProductRecommendationsWidget
        error={error}
        loading={loading}
        recommendations={data.recommendations}
      />

      <ProductInsightWidget error={error} insight={data.insight} loading={loading} />

      <ProductHistoryWidget error={error} history={data.history} loading={loading} />

      <ProductDetailsTimelineWidget error={error} loading={loading} timeline={data.timeline} />

      <ProductQuickActionsWidget error={error} loading={loading} actions={data.quickActions} />
    </div>
  );
}
