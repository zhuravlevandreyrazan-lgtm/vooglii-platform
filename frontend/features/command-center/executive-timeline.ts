import type { ExecutiveBrief } from "@/features/command-center/executive-brief-types";
import type { CommandCenterKpis } from "@/features/command-center/kpi-types";
import type {
  ExecutiveTimelineEvent,
  ExecutiveTimelinePeriod,
  ExecutiveTimelineSeverity
} from "@/features/command-center/executive-timeline-types";
import type { PriorityAction } from "@/features/command-center/priority-actions-types";

const PERIOD_ORDER: Record<ExecutiveTimelinePeriod, number> = {
  yesterday: 0,
  today: 1,
  tomorrow: 2,
  week: 3
};

const SEVERITY_ORDER: Record<ExecutiveTimelineSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4
};

function createEvent(event: ExecutiveTimelineEvent): ExecutiveTimelineEvent {
  return { ...event };
}

function dedupeEvents(events: ExecutiveTimelineEvent[]) {
  const unique: ExecutiveTimelineEvent[] = [];
  const seen = new Set<string>();

  events.forEach((event) => {
    const key = `${event.period}:${event.title.trim().toLowerCase()}`;

    if (seen.has(key)) {
      return;
    }

    seen.add(key);
    unique.push(event);
  });

  return unique;
}

function sortEvents(events: ExecutiveTimelineEvent[]) {
  return [...events].sort((left, right) => {
    const periodDiff = PERIOD_ORDER[left.period] - PERIOD_ORDER[right.period];

    if (periodDiff !== 0) {
      return periodDiff;
    }

    const severityDiff = SEVERITY_ORDER[left.severity] - SEVERITY_ORDER[right.severity];

    if (severityDiff !== 0) {
      return severityDiff;
    }

    return left.title.localeCompare(right.title);
  });
}

function actionSeverityToTimelineSeverity(
  severity: PriorityAction["severity"]
): ExecutiveTimelineSeverity {
  switch (severity) {
    case "critical":
      return "critical";
    case "high":
      return "high";
    case "medium":
      return "medium";
    default:
      return "low";
  }
}

function riskToneToSeverity(tone: CommandCenterKpis["topRisk"] extends infer T ? T : never) {
  if (!tone || typeof tone !== "object" || !("tone" in tone)) {
    return "medium" as ExecutiveTimelineSeverity;
  }

  if (tone.tone === "risk") {
    return "high" as ExecutiveTimelineSeverity;
  }

  if (tone.tone === "watch") {
    return "medium" as ExecutiveTimelineSeverity;
  }

  return "low" as ExecutiveTimelineSeverity;
}

export function buildExecutiveTimeline(
  kpis: CommandCenterKpis,
  executiveBrief: ExecutiveBrief,
  priorityActions: PriorityAction[]
): ExecutiveTimelineEvent[] {
  const events: ExecutiveTimelineEvent[] = [];

  priorityActions
    .filter((action) => action.severity === "critical" || action.severity === "high")
    .forEach((action, index) => {
      events.push(
        createEvent({
          id: `timeline-action-${index + 1}`,
          period: "today",
          title: action.title,
          description: action.recommendation || action.description,
          severity: actionSeverityToTimelineSeverity(action.severity),
          source: "priorityActions"
        })
      );
    });

  if (kpis.topRisk) {
    events.push(
      createEvent({
        id: "timeline-top-risk",
        period:
          kpis.businessHealth.state === "ready" && kpis.businessHealth.numericValue < 60
            ? "tomorrow"
            : "week",
        title: kpis.topRisk.title,
        description: kpis.topRisk.summary,
        severity: riskToneToSeverity(kpis.topRisk),
        source: "kpi"
      })
    );
  }

  if (kpis.topOpportunity) {
    events.push(
      createEvent({
        id: "timeline-top-opportunity",
        period: "week",
        title: kpis.topOpportunity.title,
        description: kpis.topOpportunity.summary,
        severity: "low",
        source: "kpi"
      })
    );
  }

  if (kpis.businessHealth.state === "ready" && kpis.businessHealth.numericValue >= 75) {
    events.push(
      createEvent({
        id: "timeline-stable-business",
        period: "today",
        title: "Бизнес работает стабильно",
        description: executiveBrief.summary,
        severity: "info",
        source: "executiveBrief"
      })
    );
  }

  if (kpis.businessHealth.state === "ready" && kpis.businessHealth.numericValue < 60) {
    events.push(
      createEvent({
        id: "timeline-attention-required",
        period: "today",
        title: "Требуется управленческое внимание",
        description: executiveBrief.recommendation.detail,
        severity: "high",
        source: "executiveBrief"
      })
    );
  }

  const uniqueEvents = dedupeEvents(events);

  if (uniqueEvents.length === 0) {
    uniqueEvents.push(
      createEvent({
        id: "timeline-fallback",
        period: "today",
        title: "Ожидается обновление данных",
        description: "Пока недостаточно подтвержденных сигналов, чтобы собрать полноценную ленту действий.",
        severity: "info",
        source: "fallback"
      })
    );
  }

  return sortEvents(uniqueEvents).slice(0, 6);
}
