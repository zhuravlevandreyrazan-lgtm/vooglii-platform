import type { BusinessAlert, BusinessInsight, BusinessKpis } from "@/features/business/types";

const SEVERITY_ORDER: Record<BusinessAlert["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4
};

function sortAlerts(alerts: BusinessAlert[]) {
  return [...alerts].sort((left, right) => {
    const severityDiff = SEVERITY_ORDER[left.severity] - SEVERITY_ORDER[right.severity];
    if (severityDiff !== 0) {
      return severityDiff;
    }
    return left.title.localeCompare(right.title);
  });
}

export function buildBusinessAlerts(
  kpis: BusinessKpis,
  insight: BusinessInsight
): BusinessAlert[] {
  if (kpis.revenue.state === "unknown" && kpis.profit.state === "unknown" && kpis.orders.state === "unknown") {
    return [
      {
        id: "business-alert-no-data",
        title: "Нет данных по бизнесу",
        description: "Раздел подключен, но по выбранному периоду пока нет пригодных бизнес-агрегатов.",
        severity: "info",
        source: "fallback"
      }
    ];
  }

  const alerts: BusinessAlert[] = [];

  if (kpis.profit.numericValue < 80000) {
    alerts.push({
      id: "business-alert-profit",
      title: "Прибыль ниже желаемого уровня",
      description: "Прибыль положительная, но текущего запаса мало для устойчивого роста и рекламы.",
      severity: "high",
      source: "kpi"
    });
  }

  if (kpis.margin.numericValue < 20) {
    alerts.push({
      id: "business-alert-margin",
      title: "Маржинальность под давлением",
      description: "Низкая маржинальность может быстро ухудшить прибыль при замедлении выручки.",
      severity: "high",
      source: "kpi"
    });
  }

  if (kpis.returns.numericValue > 45 || kpis.returns.delta.startsWith("+")) {
    alerts.push({
      id: "business-alert-returns",
      title: "Возвраты растут",
      description: "Рост возвратов снижает вклад в прибыль и может сигнализировать о проблемах с товарами.",
      severity: "medium",
      source: "kpi"
    });
  }

  if (kpis.profitTrend.numericValue < 0 && kpis.revenueTrend.numericValue >= 0) {
    alerts.push({
      id: "business-alert-costs",
      title: "Расходы могут расти быстрее выручки",
      description: "Прибыль снижается при растущей выручке, что часто указывает на давление со стороны расходов.",
      severity: "medium",
      source: "kpi"
    });
  }

  if (kpis.revenueTrend.numericValue < 0 || kpis.healthScore.numericValue < 60) {
    alerts.push({
      id: "business-alert-dynamics",
      title: "Динамика бизнеса ухудшается",
      description: insight.summary,
      severity: "high",
      source: "insight"
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      id: "business-alert-fallback",
      title: "Сильных негативных сигналов пока нет",
      description: "По текущим правилам существенные бизнес-риски не выявлены.",
      severity: "info",
      source: "fallback"
    });
  }

  return sortAlerts(alerts).slice(0, 5);
}
