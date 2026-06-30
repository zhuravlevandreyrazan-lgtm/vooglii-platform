import type { CommandCenterKpis } from "@/features/command-center/kpi-types";
import type {
  ExecutiveBrief,
  ExecutiveConfidence,
  ExecutiveInsight,
  ExecutiveRecommendation,
  ExecutiveStatus
} from "@/features/command-center/executive-brief-types";

const FALLBACK_SUMMARY = "Недостаточно данных для формирования рекомендаций.";

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
    kpis.profit,
    kpis.margin,
    kpis.roas,
    kpis.acos
  ].filter(hasReadableMetric).length;

  if (readyCount >= 5) {
    return "high";
  }
  if (readyCount >= 3) {
    return "medium";
  }
  return "low";
}

function resolveGreeting(status: ExecutiveStatus) {
  if (status === "Business Stable") {
    return "Картина бизнеса выглядит устойчиво.";
  }
  if (status === "Attention Required") {
    return "Сегодня бизнесу требуется управленческое внимание.";
  }
  return "Сводка сформирована с ограниченным набором данных.";
}

function resolveSummary(kpis: CommandCenterKpis, status: ExecutiveStatus) {
  const signals: string[] = [];

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
    return `Ключевые сигналы указывают на давление на результат. ${signals.join(" ")}`;
  }

  if (status === "Business Stable") {
    return `Основные KPI выглядят стабильно. ${signals.join(" ")}`;
  }

  return `Доступные KPI позволяют сформировать частичную картину. ${signals.join(" ")}`;
}

function resolveRecommendation(kpis: CommandCenterKpis, status: ExecutiveStatus): ExecutiveRecommendation {
  if (kpis.topRisk) {
    return {
      title: "Сфокусируйтесь на главном риске.",
      detail: kpis.topRisk.summary || FALLBACK_SUMMARY,
      priority: "high"
    };
  }

  if (kpis.topOpportunity) {
    return {
      title: "Используйте выявленную возможность.",
      detail: kpis.topOpportunity.summary,
      priority: "medium"
    };
  }

  if (status === "Business Stable") {
    return {
      title: "Поддерживайте текущий темп.",
      detail: "Существенных негативных сигналов не обнаружено. Сохраняйте контроль над маржой и рекламной эффективностью.",
      priority: "low"
    };
  }

  return {
    title: "Соберите больше данных.",
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
