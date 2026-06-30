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
  const alerts: BusinessAlert[] = [];

  if (kpis.profit.numericValue < 80000) {
    alerts.push({
      id: "business-alert-profit",
      title: "Profit is below the desired operating buffer",
      description: "Profit is positive, but the current level leaves less room for volatility and marketing pressure.",
      severity: "high",
      source: "kpi"
    });
  }

  if (kpis.margin.numericValue < 20) {
    alerts.push({
      id: "business-alert-margin",
      title: "Margin is under pressure",
      description: "Low margin can quickly compress profitability if revenue growth slows.",
      severity: "high",
      source: "kpi"
    });
  }

  if (kpis.returns.numericValue > 45 || kpis.returns.delta.startsWith("+")) {
    alerts.push({
      id: "business-alert-returns",
      title: "Returns are rising",
      description: "Higher returns can erode net contribution and reduce confidence in product quality.",
      severity: "medium",
      source: "kpi"
    });
  }

  if (kpis.profitTrend.numericValue < 0 && kpis.revenueTrend.numericValue >= 0) {
    alerts.push({
      id: "business-alert-costs",
      title: "Operating costs may be growing faster than revenue",
      description: "Profit is weakening while revenue still grows, which usually points to rising cost pressure.",
      severity: "medium",
      source: "kpi"
    });
  }

  if (kpis.revenueTrend.numericValue < 0 || kpis.healthScore.numericValue < 60) {
    alerts.push({
      id: "business-alert-dynamics",
      title: "Business dynamics are weakening",
      description: insight.summary,
      severity: "high",
      source: "insight"
    });
  }

  if (alerts.length === 0) {
    alerts.push({
      id: "business-alert-fallback",
      title: "Business alerts are waiting for stronger signals",
      description: "No material business alert is triggered by the current deterministic rules.",
      severity: "info",
      source: "fallback"
    });
  }

  return sortAlerts(alerts).slice(0, 5);
}
