import type { CommandCenterKpis } from "@/features/command-center/kpi-types";
import type {
  ExecutiveBrief,
  ExecutiveConfidence,
  ExecutiveInsight,
  ExecutiveRecommendation,
  ExecutiveStatus
} from "@/features/command-center/executive-brief-types";

const FALLBACK_SUMMARY = "Not enough live metrics are available yet to form a confident recommendation.";

function hasReadableMetric(value: CommandCenterKpis[keyof Omit<CommandCenterKpis, "topRisk" | "topOpportunity" | "cards">]) {
  return value.state === "ready";
}

function toExecutiveInsight(
  item: CommandCenterKpis["topRisk"] | CommandCenterKpis["topOpportunity"]
): ExecutiveInsight | null {
  if (!item) {
    return null;
  }

  return {
    title: item.title,
    summary: item.summary,
    tone: item.tone,
    source: item.source
  };
}

function resolveOverallStatus(kpis: CommandCenterKpis): ExecutiveStatus {
  if (kpis.businessHealth.state !== "ready") {
    return "Data Pending";
  }

  if (kpis.businessHealth.numericValue >= 75) {
    return "Business Stable";
  }

  return "Attention Required";
}

function resolveConfidence(kpis: CommandCenterKpis): ExecutiveConfidence {
  const readyCount = [
    kpis.businessHealth,
    kpis.revenue,
    kpis.profit,
    kpis.margin,
    kpis.roas,
    kpis.acos
  ].filter(hasReadableMetric).length;

  if (readyCount >= 6) {
    return "high";
  }
  if (readyCount >= 4) {
    return "medium";
  }
  return "low";
}

function resolveGreeting(status: ExecutiveStatus) {
  if (status === "Business Stable") {
    return "Business performance looks stable.";
  }
  if (status === "Attention Required") {
    return "Business performance needs management attention today.";
  }
  return "This brief was assembled from a limited set of live metrics.";
}

function resolveSummary(kpis: CommandCenterKpis, status: ExecutiveStatus) {
  const signals: string[] = [];

  if (hasReadableMetric(kpis.revenue)) {
    signals.push(`Revenue: ${kpis.revenue.value}.`);
  }
  if (hasReadableMetric(kpis.profit)) {
    signals.push(`Profit: ${kpis.profit.value}.`);
  }
  if (hasReadableMetric(kpis.margin)) {
    signals.push(`Margin: ${kpis.margin.value}.`);
  }
  if (hasReadableMetric(kpis.roas)) {
    signals.push(`ROAS: ${kpis.roas.value}.`);
  }
  if (hasReadableMetric(kpis.acos)) {
    signals.push(`ACOS: ${kpis.acos.value}.`);
  }
  if (kpis.topRisk?.title) {
    signals.push(`Top risk: ${kpis.topRisk.title}.`);
  }
  if (kpis.topOpportunity?.title) {
    signals.push(`Top opportunity: ${kpis.topOpportunity.title}.`);
  }

  if (signals.length === 0) {
    return FALLBACK_SUMMARY;
  }

  if (status === "Attention Required") {
    return `Key live metrics point to pressure on results. ${signals.join(" ")}`;
  }

  if (status === "Business Stable") {
    return `Core KPIs look stable. ${signals.join(" ")}`;
  }

  return `Available live KPIs provide a partial operating picture. ${signals.join(" ")}`;
}

function resolveRecommendation(kpis: CommandCenterKpis, status: ExecutiveStatus): ExecutiveRecommendation {
  if (kpis.topRisk) {
    return {
      title: "Focus on the primary risk.",
      detail: kpis.topRisk.summary || FALLBACK_SUMMARY,
      priority: "high"
    };
  }

  if (kpis.topOpportunity) {
    return {
      title: "Use the strongest opportunity.",
      detail: kpis.topOpportunity.summary,
      priority: "medium"
    };
  }

  if (status === "Business Stable") {
    return {
      title: "Maintain the current operating pace.",
      detail: "No major negative signals were detected. Keep monitoring margin and advertising efficiency.",
      priority: "low"
    };
  }

  return {
    title: "Collect more live data.",
    detail: FALLBACK_SUMMARY,
    priority: "high"
  };
}

export function buildExecutiveBrief(kpis: CommandCenterKpis): ExecutiveBrief {
  const overallStatus = resolveOverallStatus(kpis);

  return {
    greeting: resolveGreeting(overallStatus),
    overallStatus,
    summary: resolveSummary(kpis, overallStatus),
    topRisk: toExecutiveInsight(kpis.topRisk),
    topOpportunity: toExecutiveInsight(kpis.topOpportunity),
    recommendation: resolveRecommendation(kpis, overallStatus),
    confidence: resolveConfidence(kpis),
    generatedAt: null
  };
}
