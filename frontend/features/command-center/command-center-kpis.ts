import type {
  ActionItem,
  AlertItem,
  CommandCenterSnapshot,
  HealthMetric,
  StatusTone,
  TimelineEvent
} from "@/types/platform";
import type {
  CommandCenterKpis,
  KpiMetric,
  KpiMetricKey,
  KpiOpportunity,
  KpiRisk,
  KpiTrend,
  KpiTrendDirection
} from "@/features/command-center/kpi-types";

const UNKNOWN_VALUE = "Нет данных";
const UNKNOWN_TREND = "Нет динамики";

const KPI_MATCHERS: Record<Exclude<KpiMetricKey, "businessHealth">, string[]> = {
  revenue: ["revenue", "gmv", "sales", "turnover", "vyru", "vykup"],
  profit: ["profit", "net profit", "operating profit", "contribution"],
  margin: ["margin", "net margin", "contribution margin"],
  orders: ["orders", "order count"],
  advertisingSpend: ["ad spend", "advertising", "marketing spend", "promo spend", "spend"],
  roas: ["roas"],
  acos: ["acos"]
};

function normalizeText(value: string | undefined) {
  return (value ?? "").trim().toLowerCase().replace(/\s+/g, " ");
}

function isMeaningfulValue(value: string | undefined) {
  const normalized = normalizeText(value);
  return Boolean(normalized) && !["n/a", "na", "-", "unknown", "not available"].includes(normalized);
}

function parseNumericValue(value: string | undefined) {
  if (!value) {
    return 0;
  }

  const compact = value.replace(/\u00A0/g, " ").replace(/\s+/g, "");
  const match = compact.match(/-?\d+(?:[.,]\d+)?/);

  if (!match) {
    return 0;
  }

  const parsed = Number(match[0].replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function parseTrend(delta: string | undefined): KpiTrend {
  if (!isMeaningfulValue(delta)) {
    return {
      value: UNKNOWN_TREND,
      direction: "unknown",
      summary: "Динамика пока недоступна."
    };
  }

  const normalized = (delta ?? "").trim();
  const numeric = parseNumericValue(normalized);
  let direction: KpiTrendDirection = "flat";

  if (normalized.startsWith("+") || numeric > 0) {
    direction = "up";
  } else if (normalized.startsWith("-") || numeric < 0) {
    direction = "down";
  }

  return {
    value: normalized,
    direction,
    summary: normalized
  };
}

function healthToneFromScore(score: number): StatusTone {
  if (score >= 80) {
    return "healthy";
  }
  if (score >= 60) {
    return "watch";
  }
  return "risk";
}

function createUnknownMetric(
  key: KpiMetricKey,
  label: string,
  unit: KpiMetric["unit"],
  note: string
): KpiMetric {
  return {
    key,
    label,
    value: UNKNOWN_VALUE,
    numericValue: 0,
    unit,
    state: "unknown",
    tone: "neutral",
    note,
    trend: parseTrend(undefined),
    source: "derived-fallback"
  };
}

function toCardMetric(metric: KpiMetric): HealthMetric {
  return {
    label: metric.label,
    value: metric.state === "ready" ? metric.value : UNKNOWN_VALUE,
    delta: metric.trend.value,
    tone: metric.tone,
    note: metric.note
  };
}

function findSnapshotMetric(snapshot: CommandCenterSnapshot, matchers: string[]) {
  return snapshot.kpis.find((metric) => {
    const haystack = `${normalizeText(metric.label)} ${normalizeText(metric.note)}`;
    return matchers.some((matcher) => haystack.includes(normalizeText(matcher)));
  });
}

function buildDerivedMetric(
  snapshot: CommandCenterSnapshot,
  key: Exclude<KpiMetricKey, "businessHealth">,
  label: string,
  unit: KpiMetric["unit"],
  fallbackNote: string
) {
  const sourceMetric = findSnapshotMetric(snapshot, KPI_MATCHERS[key]);

  if (!sourceMetric) {
    return createUnknownMetric(key, label, unit, fallbackNote);
  }

  const state = isMeaningfulValue(sourceMetric.value) ? "ready" : "unknown";

  return {
    key,
    label,
    value: state === "ready" ? sourceMetric.value : UNKNOWN_VALUE,
    numericValue: parseNumericValue(sourceMetric.value),
    unit,
      state,
      tone: sourceMetric.tone,
      note: sourceMetric.note || fallbackNote,
      trend: parseTrend(sourceMetric.delta),
      source: sourceMetric.note || "api.kpis"
  } satisfies KpiMetric;
}

function buildBusinessHealthMetric(snapshot: CommandCenterSnapshot): KpiMetric {
  const score = Number.isFinite(snapshot.businessHealth.score) ? snapshot.businessHealth.score : 0;

  return {
    key: "businessHealth",
    label: "Здоровье бизнеса",
    value: `${score}/100`,
    numericValue: score,
    unit: "score",
    state: "ready",
    tone: healthToneFromScore(score),
    note: snapshot.businessHealth.summary,
    trend: {
      value: snapshot.businessHealth.status || UNKNOWN_TREND,
      direction: "flat",
      summary: snapshot.businessHealth.status || "Статус бизнеса пока недоступен."
    },
    source: "api.businessHealth"
  };
}

function pickTopRisk(
  alerts: AlertItem[],
  timeline: TimelineEvent[],
  actions: ActionItem[]
): KpiRisk | null {
  const riskAlert = alerts.find((item) => item.tone === "risk") ?? alerts.find((item) => item.tone === "watch");

  if (riskAlert) {
    return {
      title: riskAlert.title,
      summary: riskAlert.detail,
      tone: riskAlert.tone,
      source: "api.alerts"
    };
  }

  const riskEvent =
    timeline.find((item) => item.tone === "risk") ?? timeline.find((item) => item.tone === "watch");

  if (riskEvent) {
    return {
      title: riskEvent.title,
      summary: riskEvent.detail,
      tone: riskEvent.tone,
      source: "api.timeline"
    };
  }

  const riskAction =
    actions.find((item) => item.tone === "risk") ?? actions.find((item) => item.tone === "watch");

  if (riskAction) {
    return {
      title: riskAction.title,
      summary: `Ответственный: ${riskAction.owner}. Срок: ${riskAction.eta}.`,
      tone: riskAction.tone,
      source: "api.actions"
    };
  }

  return null;
}

function pickTopOpportunity(commandCenter: CommandCenterSnapshot): KpiOpportunity | null {
  const opportunityAction =
    commandCenter.actions.find((item) => item.tone === "accent") ??
    commandCenter.actions.find((item) => item.tone === "healthy");

  if (opportunityAction) {
    return {
      title: opportunityAction.title,
      summary: `Ответственный: ${opportunityAction.owner}. Срок: ${opportunityAction.eta}.`,
      tone: opportunityAction.tone,
      source: "api.actions"
    };
  }

  if (commandCenter.executiveBrief?.title) {
    return {
      title: commandCenter.executiveBrief.title,
      summary: commandCenter.executiveBrief.summary,
      tone: commandCenter.executiveBrief.tone,
      source: "api.executiveBrief"
    };
  }

  return null;
}

function buildCards(snapshot: CommandCenterSnapshot, metrics: KpiMetric[]) {
  const cards: HealthMetric[] = [];
  const seenLabels = new Set<string>();
  const targetCount = Math.max(snapshot.kpis.length, 4);

  const addCard = (metric: HealthMetric) => {
    if (seenLabels.has(metric.label) || cards.length >= targetCount) {
      return;
    }
    cards.push(metric);
    seenLabels.add(metric.label);
  };

  metrics.filter((metric) => metric.state === "ready").forEach((metric) => addCard(toCardMetric(metric)));
  snapshot.kpis.forEach((metric) => addCard(metric));
  metrics.forEach((metric) => addCard(toCardMetric(metric)));

  return cards;
}

export function buildCommandCenterKpis(commandCenter: CommandCenterSnapshot): CommandCenterKpis {
  const revenue = buildDerivedMetric(
    commandCenter,
    "revenue",
    "Выручка",
    "currency",
    "Данные по выручке пока недоступны."
  );
  const profit = buildDerivedMetric(
    commandCenter,
    "profit",
    "Прибыль",
    "currency",
    "Данные по прибыли пока недоступны."
  );
  const margin = buildDerivedMetric(
    commandCenter,
    "margin",
    "Маржинальность",
    "percent",
    "Данные по маржинальности пока недоступны."
  );
  const orders = buildDerivedMetric(
    commandCenter,
    "orders",
    "Заказы",
    "count",
    "Данные по заказам пока недоступны."
  );
  const advertisingSpend = buildDerivedMetric(
    commandCenter,
    "advertisingSpend",
    "Расходы на рекламу",
    "currency",
    "Данные по расходам на рекламу пока недоступны."
  );
  const roas = buildDerivedMetric(
    commandCenter,
    "roas",
    "Окупаемость рекламы",
    "ratio",
    "Данные по окупаемости рекламы пока недоступны."
  );
  const acos = buildDerivedMetric(
    commandCenter,
    "acos",
    "Доля рекламных расходов",
    "percent",
    "Данные по доле рекламных расходов пока недоступны."
  );
  const businessHealth = buildBusinessHealthMetric(commandCenter);

  const cards = buildCards(commandCenter, [
    businessHealth,
    revenue,
    profit,
    margin,
    orders,
    advertisingSpend,
    roas,
    acos
  ]);

  return {
    revenue,
    profit,
    margin,
    orders,
    advertisingSpend,
    roas,
    acos,
    businessHealth,
    topRisk: pickTopRisk(commandCenter.alerts, commandCenter.timeline, commandCenter.actions),
    topOpportunity: pickTopOpportunity(commandCenter),
    cards
  };
}
