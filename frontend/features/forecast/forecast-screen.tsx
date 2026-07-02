import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";
import type { WorkspaceDiagnostics } from "@/shared/api";
import type { ForecastSimulation, ForecastSnapshot } from "@/features/forecast/types";
import { ForecastScenariosWidget } from "@/features/forecast/widgets/forecast-scenarios-widget";
import { ForecastSummaryWidget } from "@/features/forecast/widgets/forecast-summary-widget";

function formatMetric(value: number | null, suffix = "") {
  if (value === null || value === undefined) {
    return "Нет данных";
  }
  return `${Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)}${suffix}`;
}

function renderExpectedEffect(effect: ForecastSimulation["expectedEffect"]) {
  const rows = Object.entries(effect);
  if (rows.length === 0) {
    return <div className="text-sm leading-6 text-[var(--ink-soft)]">Эффект появится после расчета сценария.</div>;
  }

  return (
    <div className="grid gap-2 md:grid-cols-2">
      {rows.map(([key, value]) => (
        <div key={key} className="rounded-[14px] bg-[var(--panel-strong)] px-3 py-2 text-sm">
          <span className="font-semibold">{key}</span>
          <span className="ml-2 text-[var(--ink-soft)]">{value === null ? "Нет данных" : String(value)}</span>
        </div>
      ))}
    </div>
  );
}

export function ForecastScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated,
  simulation,
  simulationLoading = false,
  simulateAction
}: {
  data: ForecastSnapshot;
  diagnostics?: WorkspaceDiagnostics;
  loading?: boolean;
  error?: string | null;
  reload?: () => void;
  lastUpdated?: string | null;
  simulation: ForecastSimulation | null;
  simulationLoading?: boolean;
  simulateAction: (type: "increase_ads" | "reduce_ads" | "restock") => Promise<void>;
}) {
  const periodCards = [
    { key: "sevenDays", label: "7 дней", item: data.periods.sevenDays },
    { key: "fourteenDays", label: "14 дней", item: data.periods.fourteenDays },
    { key: "thirtyDays", label: "30 дней", item: data.periods.thirtyDays }
  ] as const;

  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          reload ? (
            <Button variant="secondary" onClick={reload}>
              Обновить данные
            </Button>
          ) : null
        }
        breadcrumb={["Платформа", "Прогноз"]}
        subtitle="Прогноз продаж, прибыли, рекламной нагрузки и рисков по текущим данным кабинета."
        title="Прогноз"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Сейчас показан безопасный режим без расчетов. Полные прогнозы появятся после восстановления данных."
          title="Прогноз временно ограничен"
          tone="watch"
        />
      ) : null}

      <ForecastSummaryWidget data={data} error={error} loading={loading} updatedAt={lastUpdated} />

      <section className="grid gap-4 xl:grid-cols-3">
        {periodCards.map(({ key, label, item }) => (
          <WidgetCard
            key={key}
            error={error}
            loading={loading}
            status={{ label: item.status, tone: item.status === "ready" ? "healthy" : "watch" }}
            subtitle={label}
            title="Окно прогноза"
          >
            <div className="space-y-3 text-sm leading-6 text-[var(--ink-soft)]">
              <div>{`Выручка: ${formatMetric(item.expectedRevenue, " ₽")}`}</div>
              <div>{`Заказы: ${formatMetric(item.expectedOrders)}`}</div>
              <div>{`Единицы: ${formatMetric(item.expectedUnits)}`}</div>
              <div>{`Тренд: ${item.trend}`}</div>
              <div>{item.explanation}</div>
            </div>
          </WidgetCard>
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <WidgetCard
          error={error}
          loading={loading}
          status={{ label: data.profitForecast.status, tone: data.profitForecast.status === "ready" ? "healthy" : "watch" }}
          subtitle="Прибыль и маржа"
          title="Финансовый прогноз"
        >
          <div className="space-y-3 text-sm leading-6 text-[var(--ink-soft)]">
            <div>{`Операционная прибыль: ${formatMetric(data.profitForecast.expectedOperatingProfit, " ₽")}`}</div>
            <div>{`Маржа: ${data.profitForecast.expectedMargin === null ? "Нет данных" : `${data.profitForecast.expectedMargin.toFixed(1)}%`}`}</div>
            <div>{`Изменение прибыли: ${formatMetric(data.profitForecast.expectedProfitChange, " ₽")}`}</div>
            <div>{data.profitForecast.explanation}</div>
          </div>
        </WidgetCard>

        <WidgetCard
          error={error}
          loading={loading}
          status={{ label: data.inventoryForecast.status, tone: data.inventoryForecast.status === "ready" ? "healthy" : "watch" }}
          subtitle="Остатки и реклама"
          title="Операционные риски"
        >
          <div className="space-y-3 text-sm leading-6 text-[var(--ink-soft)]">
            <div>{data.inventoryForecast.message}</div>
            <div>{`Затронутая выручка: ${formatMetric(data.inventoryForecast.affectedRevenue, " ₽")}`}</div>
            <div>{`Расход рекламы: ${formatMetric(data.advertisingForecast.expectedSpend, " ₽")}`}</div>
            <div>{`ROAS: ${formatMetric(data.advertisingForecast.expectedROAS)}`}</div>
            <div>{data.advertisingForecast.explanation}</div>
          </div>
        </WidgetCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <WidgetCard
          empty={data.risks.length === 0}
          emptyMessage="Риски появятся, когда прогноз зафиксирует отклонения."
          error={error}
          loading={loading}
          subtitle="На что обратить внимание"
          title="Риски"
        >
          <div className="space-y-3">
            {data.risks.map((risk) => (
              <div key={risk.id} className="rounded-[18px] border border-[var(--line)] bg-white/72 p-3.5">
                <div className="text-sm font-semibold">{risk.title}</div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{risk.description}</p>
                {risk.action ? <p className="mt-2 text-sm font-semibold">{risk.action}</p> : null}
              </div>
            ))}
          </div>
        </WidgetCard>

        <WidgetCard
          empty={data.opportunities.length === 0}
          emptyMessage="Возможности появятся, когда система увидит подтвержденный потенциал роста."
          error={error}
          loading={loading}
          subtitle="Где можно ускориться"
          title="Возможности"
        >
          <div className="space-y-3">
            {data.opportunities.map((item) => (
              <div key={item.id} className="rounded-[18px] border border-[var(--line)] bg-white/72 p-3.5">
                <div className="text-sm font-semibold">{item.title}</div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
                {item.action ? <p className="mt-2 text-sm font-semibold">{item.action}</p> : null}
              </div>
            ))}
          </div>
        </WidgetCard>
      </div>

      <ForecastScenariosWidget error={error} loading={loading} scenarios={data.scenarios} />

      <WidgetCard
        error={error}
        loading={loading || simulationLoading}
        status={{ label: simulation?.status ?? "ready", tone: simulation?.status === "ready" ? "healthy" : "watch" }}
        subtitle="Increase ads, reduce ads, restock"
        title="Моделирование"
      >
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => void simulateAction("increase_ads")}>
              Увеличить рекламу
            </Button>
            <Button variant="secondary" onClick={() => void simulateAction("reduce_ads")}>
              Снизить рекламу
            </Button>
            <Button variant="secondary" onClick={() => void simulateAction("restock")}>
              Пополнить остатки
            </Button>
          </div>
          <div className="rounded-[18px] border border-[var(--line)] bg-white/72 p-3.5">
            <div className="text-sm font-semibold">
              {simulation?.recommendation ?? "Выберите сценарий, чтобы получить расчет эффекта."}
            </div>
            <div className="mt-3">{renderExpectedEffect(simulation?.expectedEffect ?? {})}</div>
            {simulation?.risks.length ? (
              <div className="mt-3 space-y-2">
                {simulation.risks.map((risk) => (
                  <div key={risk} className="text-sm leading-6 text-[var(--ink-soft)]">
                    {risk}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </WidgetCard>
    </div>
  );
}
