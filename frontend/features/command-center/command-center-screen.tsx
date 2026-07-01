import Link from "next/link";
import { ArrowRight, Clock3, Sparkles } from "lucide-react";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { KpiCard } from "@/shared/components/kpi-card";
import { StatusBadge } from "@/shared/components/status-badge";
import { WorkspaceHeader } from "@/shared/components/workspace-header";
import { WidgetCard } from "@/shared/widgets";
import { RiskOpportunityPanel } from "@/features/command-center/components/risk-opportunity-panel";
import type { ExecutiveBrief } from "@/features/command-center/executive-brief-types";
import type { ExecutiveTimelineEvent } from "@/features/command-center/executive-timeline-types";
import {
  formatDateTime,
  formatKpiValue,
  formatPeriodLabel,
  formatSeverityLabel
} from "@/features/command-center/formatters";
import type { CommandCenterKpis } from "@/features/command-center/kpi-types";
import type { PriorityAction } from "@/features/command-center/priority-actions-types";
import type { CommandCenterScreenData, StatusTone } from "@/types/platform";
import {
  localizeActionImpact,
  localizeActionStatus,
  localizeActionType,
  localizeConfidence,
  localizeKnownText,
  localizeRuntimeSource,
  localizeSeverity,
  localizeStatus,
  sanitizeUserText
} from "@/shared/ui/status-labels";

const FALLBACK_BRIEF_HELP = "Пока недостаточно данных, чтобы сделать уверенный вывод.";

type CommandCenterScreenProps = CommandCenterScreenData & {
  executiveBrief: ExecutiveBrief;
  executiveTimeline: ExecutiveTimelineEvent[];
  kpis: CommandCenterKpis;
  priorityActions: PriorityAction[];
  loading?: boolean;
  error?: string | null;
  reload?: () => void;
  lastUpdated?: string | null;
};

function mapExecutiveStatusTone(status: ExecutiveBrief["overallStatus"]): StatusTone {
  switch (status) {
    case "Business Stable":
      return "healthy";
    case "Attention Required":
      return "watch";
    default:
      return "neutral";
  }
}

function mapActionSeverityTone(severity: PriorityAction["severity"]): StatusTone {
  switch (severity) {
    case "critical":
      return "risk";
    case "high":
      return "watch";
    case "medium":
      return "accent";
    default:
      return "neutral";
  }
}

function mapTimelineSeverityTone(severity: ExecutiveTimelineEvent["severity"]): StatusTone {
  switch (severity) {
    case "critical":
      return "risk";
    case "high":
      return "watch";
    case "medium":
      return "accent";
    case "low":
      return "neutral";
    default:
      return "healthy";
  }
}

function resolveSourceLabel(source: CommandCenterScreenData["source"], runtimeSource?: CommandCenterScreenData["runtimeSource"]) {
  if (source === "demo") {
    return "Демо-режим";
  }
  if (source === "mock_fallback") {
    return "Показываем резервные данные";
  }
  return localizeRuntimeSource(runtimeSource ?? "live");
}

function dataRuntimeTone(
  source: CommandCenterScreenData["source"],
  snapshot: CommandCenterScreenData["snapshot"],
  runtimeSource?: CommandCenterScreenData["runtimeSource"]
): StatusTone {
  if (source === "demo") {
    return "accent";
  }
  if (source === "mock_fallback") {
    return "watch";
  }
  if (runtimeSource === "cache") {
    return "accent";
  }
  if (runtimeSource === "degraded" || runtimeSource === "stale_cache" || runtimeSource === "fallback") {
    return "watch";
  }
  return "healthy";
}

export function CommandCenterScreen({
  snapshot,
  source,
  runtimeSource,
  fallbackReason,
  executiveBrief,
  executiveTimeline,
  kpis,
  priorityActions,
  loading = false,
  error = null,
  reload,
  lastUpdated
}: CommandCenterScreenProps) {
  const runtimeTone = dataRuntimeTone(source, snapshot, runtimeSource);
  const sourceLabel = sanitizeUserText(resolveSourceLabel(source, runtimeSource), "Данные обновляются");
  const alerts = snapshot?.alerts ?? [];
  const workspaces = snapshot?.workspaces ?? [];
  const sharedWidgetError =
    error ?? fallbackReason ?? (source === "mock_fallback" ? "Сейчас показываются резервные данные." : null);
  const updatedAtLabel = formatDateTime(lastUpdated);

  return (
    <div className="space-y-6">
      <WorkspaceHeader
        description="Ключевые показатели, риски и рекомендации по вашему кабинету Wildberries в одном экране."
        eyebrow="VOOGLII"
        status={
          source === "real"
            ? "Кабинет подключен"
            : source === "demo"
              ? "Включен демо-режим"
              : "Показываем резервные данные"
        }
        title="Центр управления бизнесом"
      />

      <div className="flex justify-end">
        <div className="flex flex-wrap items-center gap-3">
          <OpenAutomationLink format="PDF" workspace="executive" />
          <StatusBadge tone={runtimeTone}>{sourceLabel}</StatusBadge>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <WidgetCard
          className="overflow-hidden"
          error={sharedWidgetError}
          loading={loading}
          status={{
            label: kpis.businessHealth.state === "ready" ? localizeStatus(snapshot.businessHealth?.status ?? "UNKNOWN") : "Ожидаем данные",
            tone: kpis.businessHealth.tone
          }}
          subtitle={kpis.businessHealth.state === "ready" ? formatKpiValue(kpis.businessHealth) : "Недостаточно данных"}
          title="Здоровье бизнеса"
          updatedAt={updatedAtLabel}
        >
          {kpis.businessHealth.state === "ready" ? (
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-semibold tracking-[-0.05em]">
                {kpis.businessHealth.numericValue}
              </span>
              <span className="text-lg text-[var(--ink-soft)]">/100</span>
            </div>
          ) : (
            <div className="rounded-[24px] border border-[var(--line)] bg-[linear-gradient(180deg,#fffdfc_0%,#fbf6ef_100%)] p-4 text-sm leading-6 text-[var(--ink-soft)]">
              Показатель появится после загрузки кабинета и первой синхронизации данных.
            </div>
          )}
          <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
            {sanitizeUserText(kpis.businessHealth.note, "Сводка по состоянию бизнеса пока недоступна.")}
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                Фокус дня
              </div>
              <div className="mt-2 text-sm font-semibold">
                {sanitizeUserText(
                  kpis.topOpportunity?.title ??
                  priorityActions[0]?.title ??
                  "Сначала защитите маржинальность, затем масштабируйте рост."
                )}
              </div>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                Текущее состояние
              </div>
              <div className="mt-2 text-sm font-semibold">
                {sanitizeUserText(
                  kpis.topRisk?.title ??
                  (source === "real"
                    ? "Кабинет подключен, данные поступают из рабочей системы."
                    : "Интерфейс продолжает работать в резервном режиме.")
                )}
              </div>
            </div>
          </div>
        </WidgetCard>

        <WidgetCard
          error={sharedWidgetError}
          loading={loading}
          status={{
            label: executiveBrief.overallStatus === "Business Stable" ? "Норма" : executiveBrief.overallStatus === "Attention Required" ? "Требует внимания" : "Нет данных",
            tone: mapExecutiveStatusTone(executiveBrief.overallStatus)
          }}
          subtitle={executiveBrief.greeting}
          title="Краткий вывод"
          updatedAt={updatedAtLabel}
        >
          <div className="space-y-4">
            <p className="text-sm leading-7 text-[var(--ink-soft)]">
              {sanitizeUserText(executiveBrief.summary, FALLBACK_BRIEF_HELP)}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Главный риск
                </div>
                <div className="mt-2 text-sm font-semibold">
                  {sanitizeUserText(executiveBrief.topRisk?.title, "Сейчас нет подтвержденного критичного риска.")}
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                  {sanitizeUserText(executiveBrief.topRisk?.summary, FALLBACK_BRIEF_HELP)}
                </p>
              </div>
              <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Возможность роста
                </div>
                <div className="mt-2 text-sm font-semibold">
                  {sanitizeUserText(executiveBrief.topOpportunity?.title, "Сейчас нет подтвержденной точки роста.")}
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                  {sanitizeUserText(executiveBrief.topOpportunity?.summary, FALLBACK_BRIEF_HELP)}
                </p>
              </div>
            </div>
            <div className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Что сделать сегодня
                </div>
                <StatusBadge
                  tone={
                    executiveBrief.confidence === "high"
                      ? "healthy"
                      : executiveBrief.confidence === "medium"
                        ? "watch"
                        : "neutral"
                  }
                >
                  Уверенность: {localizeConfidence(executiveBrief.confidence)}
                </StatusBadge>
              </div>
              <div className="mt-2 text-sm font-semibold">
                {sanitizeUserText(executiveBrief.recommendation.title, "Соберите больше данных.")}
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                {sanitizeUserText(executiveBrief.recommendation.detail, FALLBACK_BRIEF_HELP)}
              </p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
              Ключевые показатели
            </p>
            <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Главное по бизнесу</h2>
          </div>
          <Button icon={<Sparkles size={16} />} onClick={reload} variant="secondary">
            Обновить данные
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {kpis.cards.map((metric) => (
            <KpiCard key={metric.label} metric={metric} />
          ))}
        </div>
      </section>

      <RiskOpportunityPanel
        error={sharedWidgetError}
        loading={loading}
        topOpportunity={kpis.topOpportunity}
        topRisk={kpis.topRisk}
      />

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <WidgetCard
          empty={executiveTimeline.length === 0}
          emptyMessage="События и сигналы появятся после загрузки достаточного объема данных."
          error={sharedWidgetError}
          loading={loading}
          status={{ label: "Текущая картина", tone: "neutral" }}
          subtitle="Что важно дальше"
          title="Ключевые события"
        >
          <div className="space-y-4">
        {executiveTimeline.map((event) => (
          <div
            key={event.id}
            className="grid gap-4 rounded-[22px] border border-[var(--line)] bg-white/70 p-4 md:grid-cols-[110px_1fr]"
          >
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--ink-soft)]">
                    <Clock3 size={14} />
                    {formatPeriodLabel(event.period)}
                  </div>
                  <StatusBadge tone={mapTimelineSeverityTone(event.severity)}>
                    {formatSeverityLabel(event.severity)}
                  </StatusBadge>
                </div>
                <div>
                  <h3 className="text-base font-semibold">
                    {sanitizeUserText(event.title, "Событие обновится после синхронизации.")}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                    {sanitizeUserText(event.description, "Подробности появятся после обновления данных.")}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </WidgetCard>

        <WidgetCard
          empty={priorityActions.length === 0}
          emptyMessage="Список действий появится, когда будет достаточно подтвержденных сигналов."
          error={sharedWidgetError}
          loading={loading}
          subtitle="Переход от сигнала к действию"
          title="План на сегодня"
        >
          <div className="space-y-4">
            {priorityActions.map((action) => (
              <div key={action.id} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-base font-semibold">
                    {sanitizeUserText(action.title, "Действие")}
                  </h3>
                  <StatusBadge tone={mapActionSeverityTone(action.severity)}>
                    {localizeSeverity(action.severity)}
                  </StatusBadge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <StatusBadge tone="neutral">{localizeActionType(action.type)}</StatusBadge>
                  {action.impact ? <StatusBadge tone="accent">{localizeActionImpact(action.impact)}</StatusBadge> : null}
                  <StatusBadge tone="healthy">{localizeActionStatus(action.status)}</StatusBadge>
                </div>
                <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">
                  {sanitizeUserText(action.description, "Подробности появятся после обновления данных.")}
                </p>
                <p className="mt-3 text-sm font-semibold">
                  {sanitizeUserText(action.recommendation, "Проверьте кабинет и повторите обновление данных.")}
                </p>
              </div>
            ))}
          </div>
        </WidgetCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <section className="space-y-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
              Важные сигналы
            </p>
            <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Что требует внимания</h2>
          </div>
          {alerts.map((alert) => (
            <Alert key={alert.id} detail={alert.detail} title={alert.title} tone={alert.tone} />
          ))}
        </section>

        <WidgetCard
          empty={workspaces.length === 0}
          emptyMessage="Разделы станут доступны после загрузки маршрутов и данных."
          error={sharedWidgetError}
          loading={loading}
          status={{ label: "Навигация готова", tone: "accent" }}
          subtitle="Перейдите в нужный раздел"
          title="Разделы платформы"
        >
          <div className="grid gap-4 md:grid-cols-2">
            {workspaces.map((workspace) => (
              <Link
                key={workspace.title}
                className="group rounded-[24px] border border-[var(--line)] bg-white/70 p-5 transition hover:bg-white"
                href={workspace.href}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold">{workspace.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                      {localizeKnownText(workspace.summary, "Раздел готов к работе с данными кабинета.")}
                    </p>
                  </div>
                  <ArrowRight className="mt-1 transition group-hover:translate-x-1" size={18} />
                </div>
                <div className="mt-4 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
                  {localizeStatus(workspace.status)}
                </div>
              </Link>
            ))}
          </div>
        </WidgetCard>
      </div>
    </div>
  );
}
