import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { AdvisorConversationCard } from "@/features/advisor/components/advisor-conversation";
import { AdvisorActionsWidget } from "@/features/advisor/widgets/advisor-actions-widget";
import { AdvisorEvidenceWidget } from "@/features/advisor/widgets/advisor-evidence-widget";
import { AdvisorOverviewWidget } from "@/features/advisor/widgets/advisor-overview-widget";
import { AdvisorRecommendationsWidget } from "@/features/advisor/widgets/advisor-recommendations-widget";
import { AdvisorSourcesWidget } from "@/features/advisor/widgets/advisor-sources-widget";
import { AdvisorTimelineWidget } from "@/features/advisor/widgets/advisor-timeline-widget";
import { OpenAutomationLink } from "@/features/automation/components/open-automation-link";
import type { AdvisorSnapshot } from "@/features/advisor/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function AdvisorScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  reload,
  lastUpdated,
  workspaceContext
}: {
  data: AdvisorSnapshot;
  diagnostics?: WorkspaceDiagnostics;
  loading?: boolean;
  error?: string | null;
  reload?: () => void;
  lastUpdated?: string | null;
  workspaceContext?: {
    organizationId?: string | null;
    organization?: string | null;
    cabinetId?: string | null;
    cabinet?: string | null;
    mode?: string | null;
  };
}) {
  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <div className="flex flex-wrap gap-3">
            <OpenAutomationLink format="PDF" workspace="advisor" />
            {reload ? (
              <Button variant="secondary" onClick={reload}>
                Refresh advisor snapshot
              </Button>
            ) : null}
          </div>
        }
        breadcrumb={["Platform", "AI Advisor"]}
        subtitle="A unified management-facing advisor workspace that routes leadership through cross-workspace recommendations, evidence, sources, and action paths."
        title="AI Advisor"
        updatedAt={lastUpdated ?? undefined}
      />

      <RuntimeBadge context={workspaceContext} diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Using fallback data. Advisor snapshot is unavailable or invalid, but the conversation contract remains usable."
          title="Fallback snapshot active"
          tone="watch"
        />
      ) : null}

      <AdvisorOverviewWidget
        error={error}
        loading={loading}
        summary={data.summary}
        updatedAt={lastUpdated ?? undefined}
      />

      <section className="space-y-4">
        <div className="rounded-[28px] border border-[var(--line)] bg-[linear-gradient(135deg,#fff8ed_0%,#f5efe3_55%,#ffffff_100%)] p-6 shadow-[var(--shadow-soft)]">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">
            AI Copilot MVP
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
            Ask the platform what deserves attention next
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--ink-soft)]">
            The Copilot routes a management question through backend-ready advisor outputs and returns
            recommendations, evidence, links, related items, and diagnostics in one place.
          </p>
        </div>

        <AdvisorConversationCard
          context={{
            workspace: "advisor",
            organizationId: workspaceContext?.organizationId ?? undefined,
            cabinetId: workspaceContext?.cabinetId ?? undefined
          }}
          error={error}
          loading={loading}
          prompt={data.conversation.prompt}
        />
      </section>

      <AdvisorRecommendationsWidget
        error={error}
        loading={loading}
        recommendations={data.recommendations}
      />

      <AdvisorEvidenceWidget error={error} evidence={data.evidence} loading={loading} />

      <AdvisorTimelineWidget error={error} loading={loading} timeline={data.timeline} />

      <AdvisorActionsWidget actions={data.actions} error={error} loading={loading} />

      <AdvisorSourcesWidget error={error} loading={loading} sources={data.sources} />
    </div>
  );
}
