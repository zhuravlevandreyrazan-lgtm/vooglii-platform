import type { ExecutiveBrief } from "@/features/command-center/executive-brief-types";
import type { CommandCenterKpis } from "@/features/command-center/kpi-types";
import type { PriorityAction, PriorityActionSeverity, PriorityActionType } from "@/features/command-center/priority-actions-types";

const SEVERITY_ORDER: Record<PriorityActionSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3
};

function createAction(action: PriorityAction): PriorityAction {
  return { ...action };
}

function dedupeActions(actions: PriorityAction[]) {
  const unique: PriorityAction[] = [];
  const seen = new Set<string>();

  actions.forEach((action) => {
    const key = `${action.type}:${action.title.trim().toLowerCase()}`;

    if (seen.has(key)) {
      return;
    }

    seen.add(key);
    unique.push(action);
  });

  return unique;
}

function sortActions(actions: PriorityAction[]) {
  return [...actions].sort((left, right) => {
    const severityDiff = SEVERITY_ORDER[left.severity] - SEVERITY_ORDER[right.severity];

    if (severityDiff !== 0) {
      return severityDiff;
    }

    return left.title.localeCompare(right.title);
  });
}

function riskSeverityFromTone(tone: CommandCenterKpis["topRisk"] extends infer T ? T : never) {
  if (!tone || typeof tone !== "object" || !("tone" in tone)) {
    return "high" as PriorityActionSeverity;
  }

  if (tone.tone === "risk") {
    return "critical" as PriorityActionSeverity;
  }

  if (tone.tone === "watch") {
    return "high" as PriorityActionSeverity;
  }

  return "medium" as PriorityActionSeverity;
}

function hasKnownMetricValue(metric: CommandCenterKpis["advertisingSpend"]) {
  return metric.state === "ready";
}

function isWeakAdsEfficiency(kpis: CommandCenterKpis) {
  const roasUnknown = kpis.roas.state !== "ready";
  const acosUnknown = kpis.acos.state !== "ready";
  const roasWeak = kpis.roas.state === "ready" && kpis.roas.numericValue > 0 && kpis.roas.numericValue < 3;
  const acosWeak = kpis.acos.state === "ready" && kpis.acos.numericValue >= 30;

  return roasUnknown || acosUnknown || roasWeak || acosWeak;
}

export function buildPriorityActions(
  kpis: CommandCenterKpis,
  executiveBrief: ExecutiveBrief
): PriorityAction[] {
  const actions: PriorityAction[] = [];

  if (kpis.topRisk) {
    actions.push(
      createAction({
        id: "priority-risk",
        type: "risk",
        severity: riskSeverityFromTone(kpis.topRisk),
        title: kpis.topRisk.title,
        description: kpis.topRisk.summary,
        impact: "stability",
        recommendation:
          executiveBrief.recommendation.detail || "Проверить источник риска и подготовить план снижения давления на результат.",
        status: "ready",
        source: "executiveBrief"
      })
    );
  }

  if (kpis.topOpportunity) {
    actions.push(
      createAction({
        id: "priority-growth",
        type: "growth",
        severity: kpis.businessHealth.numericValue >= 75 ? "medium" : "low",
        title: kpis.topOpportunity.title,
        description: kpis.topOpportunity.summary,
        impact: "revenue",
        recommendation: "Проверить возможность и при подтверждении аккуратно масштабировать рабочий сценарий.",
        status: "review",
        source: "kpi"
      })
    );
  }

  if (kpis.businessHealth.state === "ready" && kpis.businessHealth.numericValue < 60) {
    actions.push(
      createAction({
        id: "priority-profit-recovery",
        type: "profit",
        severity: "high",
        title: "Снизить давление на прибыль",
        description: "Индикатор business health опустился ниже безопасного уровня.",
        impact: "profit",
        recommendation: "Проверить прибыль, рекламу и остатки по проблемным SKU.",
        status: "ready",
        source: "kpi"
      })
    );
  }

  if (kpis.businessHealth.state === "ready" && kpis.businessHealth.numericValue >= 75) {
    actions.push(
      createAction({
        id: "priority-growth-mode",
        type: "growth",
        severity: "low",
        title: "Удерживать стабильный режим роста",
        description: "Business health остаётся в устойчивой зоне.",
        impact: "revenue",
        recommendation: "Сохранить текущий режим и искать точки масштабирования.",
        status: "review",
        source: "kpi"
      })
    );
  }

  if (hasKnownMetricValue(kpis.advertisingSpend) && isWeakAdsEfficiency(kpis)) {
    actions.push(
      createAction({
        id: "priority-ads-efficiency",
        type: "ads",
        severity: "medium",
        title: "Проверить эффективность рекламы",
        description: "Расходы на рекламу есть, но эффективность кампаний недостаточно подтверждена KPI.",
        impact: "efficiency",
        recommendation: "Проверить эффективность рекламных кампаний.",
        status: "review",
        source: "kpi"
      })
    );
  }

  const uniqueActions = dedupeActions(actions);

  if (uniqueActions.length === 0) {
    uniqueActions.push(
      createAction({
        id: "priority-data-fallback",
        type: "data",
        severity: "medium",
        title: "Обновить управленческие данные",
        description: "Для уверенного списка действий пока недостаточно подтверждённых сигналов.",
        impact: "visibility",
        recommendation: "Обновить данные и проверить подключение источников.",
        status: "new",
        source: "fallback"
      })
    );
  }

  return sortActions(uniqueActions).slice(0, 4);
}
