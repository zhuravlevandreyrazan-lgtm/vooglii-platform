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

const FALLBACK_BRIEF_HELP = "Not enough data is available to form a confident recommendation yet.";

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

export function CommandCenterScreen({
  snapshot,
  source,
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
  const sourceTone = source === "real" ? "healthy" : "accent";
  const sourceLabel =
    source === "real" ? "LIVE DATA" : source === "demo" ? "DEMO MODE" : "MOCK DATA FALLBACK";
  const alerts = snapshot?.alerts ?? [];
  const workspaces = snapshot?.workspaces ?? [];
  const sharedWidgetError =
    error ?? fallbackReason ?? (source === "mock_fallback" ? "Displaying fallback snapshot." : null);
  const updatedAtLabel = formatDateTime(lastUpdated);

  return (
    <div className="space-y-6">
      <WorkspaceHeader
        description="The first commercial web surface of VOOGLII. This skeleton already mirrors the target command flow: understand business condition, see why it changed, and move into the next workspace with intent."
        eyebrow="VOOGLII Command Center"
        status={
          source === "real"
            ? "Read-only API snapshot active"
            : source === "demo"
              ? "Demo snapshot active"
              : "Mock snapshot active"
        }
        title="Business Operating System for marketplace sellers"
      />

      <div className="flex justify-end">
        <div className="flex flex-wrap items-center gap-3">
          <OpenAutomationLink format="PDF" workspace="executive" />
          <StatusBadge tone={sourceTone}>{sourceLabel}</StatusBadge>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <WidgetCard
          className="overflow-hidden"
          error={sharedWidgetError}
          loading={loading}
          status={{
            label: snapshot.businessHealth?.status ?? "UNKNOWN",
            tone: kpis.businessHealth.tone
          }}
          subtitle={formatKpiValue(kpis.businessHealth)}
          title="Business Health"
          updatedAt={updatedAtLabel}
        >
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-semibold tracking-[-0.05em]">
              {kpis.businessHealth.state === "ready" ? kpis.businessHealth.numericValue : "-"}
            </span>
            <span className="text-lg text-[var(--ink-soft)]">/100</span>
          </div>
          <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
            {kpis.businessHealth.note || "Business health summary is not available yet."}
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                Daily focus
              </div>
              <div className="mt-2 text-sm font-semibold">
                {kpis.topOpportunity?.title ??
                  priorityActions[0]?.title ??
                  "Protect margin before scale masks efficiency drift."}
              </div>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                Readiness
              </div>
              <div className="mt-2 text-sm font-semibold">
                {kpis.topRisk?.title ??
                  (source === "real"
                    ? "Connected to the read-only Command Center API."
                    : "Frontend stays available through mock fallback.")}
              </div>
            </div>
          </div>
        </WidgetCard>

        <WidgetCard
          error={sharedWidgetError}
          loading={loading}
          status={{
            label: executiveBrief.overallStatus,
            tone: mapExecutiveStatusTone(executiveBrief.overallStatus)
          }}
          subtitle={executiveBrief.greeting}
          title="Executive Brief"
          updatedAt={updatedAtLabel}
        >
          <div className="space-y-4">
            <p className="text-sm leading-7 text-[var(--ink-soft)]">{executiveBrief.summary}</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Top risk
                </div>
                <div className="mt-2 text-sm font-semibold">
                  {executiveBrief.topRisk?.title ?? "No material risk was identified from current KPI signals."}
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                  {executiveBrief.topRisk?.summary ?? FALLBACK_BRIEF_HELP}
                </p>
              </div>
              <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Top opportunity
                </div>
                <div className="mt-2 text-sm font-semibold">
                  {executiveBrief.topOpportunity?.title ?? "No clear growth opportunity is available yet."}
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                  {executiveBrief.topOpportunity?.summary ?? FALLBACK_BRIEF_HELP}
                </p>
              </div>
            </div>
            <div className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Recommendation
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
                  Confidence {executiveBrief.confidence}
                </StatusBadge>
              </div>
              <div className="mt-2 text-sm font-semibold">{executiveBrief.recommendation.title}</div>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                {executiveBrief.recommendation.detail}
              </p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
              KPI Grid
            </p>
            <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">Signal at a glance</h2>
          </div>
          <Button icon={<Sparkles size={16} />} onClick={reload} variant="secondary">
            Refresh snapshot
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
          emptyMessage="Executive timeline will appear here when enough rule-based signals are available."
          error={sharedWidgetError}
          loading={loading}
          status={{ label: "Rule-based view", tone: "neutral" }}
          subtitle="What matters next"
          title="Executive Timeline"
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
                  <h3 className="text-base font-semibold">{event.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{event.description}</p>
                  <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                    Source {event.source}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </WidgetCard>

        <WidgetCard
          empty={priorityActions.length === 0}
          emptyMessage="Priority actions will appear here when enough executive signals are available."
          error={sharedWidgetError}
          loading={loading}
          subtitle="Move from signal to action"
          title="Today Actions"
        >
          <div className="space-y-4">
            {priorityActions.map((action) => (
              <div key={action.id} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-base font-semibold">{action.title}</h3>
                  <StatusBadge tone={mapActionSeverityTone(action.severity)}>
                    {formatSeverityLabel(action.severity)}
                  </StatusBadge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <StatusBadge tone="neutral">{action.type}</StatusBadge>
                  {action.impact ? <StatusBadge tone="accent">{action.impact}</StatusBadge> : null}
                  <StatusBadge tone="healthy">{action.status}</StatusBadge>
                </div>
                <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{action.description}</p>
                <p className="mt-3 text-sm font-semibold">{action.recommendation}</p>
                <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  Source {action.source}
                </div>
              </div>
            ))}
          </div>
        </WidgetCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <section className="space-y-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
              Critical Alerts
            </p>
            <h2 className="mt-1 text-2xl font-semibold tracking-[-0.04em]">What needs attention</h2>
          </div>
          {alerts.map((alert) => (
            <Alert key={alert.id} detail={alert.detail} title={alert.title} tone={alert.tone} />
          ))}
        </section>

        <WidgetCard
          empty={workspaces.length === 0}
          emptyMessage="Workspace routes will appear here when navigation entries are available."
          error={sharedWidgetError}
          loading={loading}
          status={{ label: "Routing ready", tone: "accent" }}
          subtitle="Go deeper by function"
          title="Workspace Navigation"
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
                      {workspace.summary}
                    </p>
                  </div>
                  <ArrowRight className="mt-1 transition group-hover:translate-x-1" size={18} />
                </div>
                <div className="mt-4 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
                  {workspace.status}
                </div>
              </Link>
            ))}
          </div>
        </WidgetCard>
      </div>
    </div>
  );
}
