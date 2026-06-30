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
  const strengths: string[] = [];
  const weaknesses: string[] = [];
  const risks: string[] = [];
  const opportunities: string[] = [];

  if (kpis.revenueTrend.numericValue > 0) {
    strengths.push("Revenue is still expanding versus the previous comparison window.");
  } else {
    weaknesses.push("Revenue growth is soft and needs closer commercial monitoring.");
  }

  if (kpis.margin.numericValue >= 25) {
    strengths.push("Margin remains healthy enough to support stable operating performance.");
  } else {
    weaknesses.push("Margin is under pressure and may dilute operating profit.");
  }

  if (kpis.profit.numericValue > 0) {
    strengths.push("Business is currently profitable on the active period view.");
  } else {
    risks.push("Profit is at risk or already below the safe operating threshold.");
  }

  if (kpis.returns.numericValue > 45 || kpis.returns.delta.startsWith("+")) {
    risks.push("Returns are increasing and can erode both margin and order quality.");
  }

  if (kpis.averageOrderValue.numericValue >= 240) {
    opportunities.push("Average order value is high enough to support selective scaling.");
  }

  if (kpis.healthScore.numericValue >= 75) {
    opportunities.push("Business health supports targeted growth experiments.");
  } else {
    risks.push("Health score signals that leadership attention is needed before scaling.");
  }

  const confidenceLevel = readyMetrics(kpis);
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
      : "Not enough business data is available to form a reliable insight summary.";

  return {
    summary,
    strengths: strengths.length ? strengths : ["No clear strength is confirmed by current business signals."],
    weaknesses: weaknesses.length ? weaknesses : ["No material weakness is confirmed by current business signals."],
    risks: risks.length ? risks : ["No material business risk is confirmed by current business signals."],
    opportunities: opportunities.length
      ? opportunities
      : ["No clear business opportunity is confirmed by current business signals."],
    confidence,
    generatedAt: null
  };
}
