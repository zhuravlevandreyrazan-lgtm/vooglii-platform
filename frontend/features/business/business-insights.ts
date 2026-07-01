import type { BusinessInsight, BusinessKpis } from "@/features/business/types";

function readyMetrics(kpis: BusinessKpis) {
  return [
    kpis.revenue,
    kpis.profit,
    kpis.margin,
    kpis.orders,
    kpis.returns,
    kpis.averageOrderValue,
    kpis.unitsSold,
    kpis.healthScore
  ].filter((metric) => metric.state === "ready").length;
}

export function buildBusinessInsights(kpis: BusinessKpis): BusinessInsight {
  const readyCount = readyMetrics(kpis);
  if (readyCount === 0) {
    return {
      summary: "Данных по бизнесу за выбранный период пока нет. Подключите кабинет и загрузите продажи Wildberries.",
      strengths: ["Сильные стороны бизнеса появятся после загрузки выручки, заказов и прибыли."],
      weaknesses: ["По текущему периоду пока нет надежных бизнес-агрегатов."],
      risks: ["Не стоит принимать управленческие решения, опираясь на отсутствующие данные."],
      opportunities: ["Загрузите продажи WB Agent, чтобы открыть аналитику Бизнеса и Главной страницы."],
      confidence: "low",
      generatedAt: null
    };
  }

  const strengths: string[] = [];
  const weaknesses: string[] = [];
  const risks: string[] = [];
  const opportunities: string[] = [];

  if (kpis.revenueTrend.numericValue > 0) {
    strengths.push("Выручка растет по сравнению с предыдущим периодом.");
  } else {
    weaknesses.push("Рост выручки замедляется и требует внимания.");
  }

  if (kpis.margin.numericValue >= 25) {
    strengths.push("Маржинальность остается комфортной для стабильной работы.");
  } else {
    weaknesses.push("Маржинальность под давлением и может снижать итоговую прибыль.");
  }

  if (kpis.profit.numericValue > 0) {
    strengths.push("Бизнес остается прибыльным в текущем периоде.");
  } else {
    risks.push("Прибыль находится под риском или уже ниже комфортного уровня.");
  }

  if (kpis.returns.numericValue > 45 || kpis.returns.delta.startsWith("+")) {
    risks.push("Возвраты растут и могут ухудшить маржинальность и качество заказов.");
  }

  if (kpis.averageOrderValue.numericValue >= 240) {
    opportunities.push("Средний чек позволяет аккуратно масштабировать рост.");
  }

  if (kpis.healthScore.numericValue >= 75) {
    opportunities.push("Состояние бизнеса позволяет тестировать точки роста.");
  } else {
    risks.push("Состояние бизнеса требует внимания перед масштабированием.");
  }

  const confidenceLevel = readyCount;
  const confidence =
    confidenceLevel >= 8 ? "high" : confidenceLevel >= 5 ? "medium" : "low";

  const summary =
    strengths.length || weaknesses.length || risks.length || opportunities.length
      ? [
          strengths[0],
          weaknesses[0],
          risks[0],
          opportunities[0]
        ]
          .filter(Boolean)
          .join(" ")
      : "Пока недостаточно данных, чтобы собрать надежную бизнес-сводку.";

  return {
    summary,
    strengths: strengths.length ? strengths : ["Явных сильных сторон по текущим сигналам пока не подтверждено."],
    weaknesses: weaknesses.length ? weaknesses : ["Существенных слабых зон по текущим сигналам не подтверждено."],
    risks: risks.length ? risks : ["Существенных бизнес-рисков по текущим сигналам не подтверждено."],
    opportunities: opportunities.length
      ? opportunities
      : ["Подтвержденных точек роста по текущим сигналам пока нет."],
    confidence,
    generatedAt: null
  };
}
