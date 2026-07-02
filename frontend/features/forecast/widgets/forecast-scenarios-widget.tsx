import { WidgetCard } from "@/shared/widgets";
import type { ForecastScenario } from "@/features/forecast/types";

function formatMoney(value: number | null) {
  if (value === null || value === undefined) {
    return "Нет данных";
  }
  return `${Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)} ₽`;
}

export function ForecastScenariosWidget({
  scenarios,
  loading = false,
  error = null
}: {
  scenarios: ForecastScenario[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={scenarios.length === 0}
      emptyMessage="Сценарии появятся, когда прогноз получит достаточно данных."
      error={error}
      loading={loading}
      subtitle="Консервативный, базовый и агрессивный"
      title="Сценарии"
    >
      <div className="grid gap-3 xl:grid-cols-3">
        {scenarios.map((scenario) => (
          <div key={scenario.id} className="rounded-[18px] border border-[var(--line)] bg-white/72 p-3.5">
            <div className="text-sm font-semibold">{scenario.title}</div>
            <div className="mt-3 space-y-2 text-sm text-[var(--ink-soft)]">
              <div>{`Выручка: ${formatMoney(scenario.revenue)}`}</div>
              <div>{`Прибыль: ${formatMoney(scenario.profit)}`}</div>
              <div>{`Риск: ${scenario.riskLevel}`}</div>
            </div>
            <div className="mt-3 space-y-2">
              {scenario.actions.map((action) => (
                <div key={action} className="rounded-[14px] bg-[var(--panel-strong)] px-3 py-2 text-sm leading-6">
                  {action}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
