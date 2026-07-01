"use client";

import Link from "next/link";
import { useAuth } from "@/features/auth";
import { AutomationOverviewWidget } from "@/features/automation/widgets/automation-overview-widget";
import { AutomationTimelineWidget } from "@/features/automation/widgets/automation-timeline-widget";
import { ExportCenterWidget } from "@/features/automation/widgets/export-center-widget";
import { ExportHistoryWidget } from "@/features/automation/widgets/export-history-widget";
import { JobsWidget } from "@/features/automation/widgets/jobs-widget";
import { QuickActionsWidget } from "@/features/automation/widgets/quick-actions-widget";
import { ScheduledReportsWidget } from "@/features/automation/widgets/scheduled-reports-widget";
import type { AutomationSnapshot, ExportFormat } from "@/features/automation/types";
import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { PageHeader } from "@/shared/layout";
import { StatusBadge } from "@/shared/status";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function AutomationScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  actionMessage = null,
  pendingAction = false,
  lastUpdated,
  selectedWorkspace,
  selectedFormat,
  onGenerate,
  onToggleSchedule,
  workspaceContext
}: {
  data: AutomationSnapshot;
  diagnostics?: WorkspaceDiagnostics;
  loading?: boolean;
  error?: string | null;
  actionMessage?: string | null;
  pendingAction?: boolean;
  lastUpdated?: string | null;
  selectedWorkspace?: string | null;
  selectedFormat?: string | null;
  onGenerate: (payload: { workspace: string; format: ExportFormat; name?: string; sku?: string }) => Promise<void>;
  onToggleSchedule: (scheduleId: string, enabled: boolean) => Promise<void>;
  workspaceContext?: {
    organizationId?: string | null;
    organization?: string | null;
    cabinetId?: string | null;
    cabinet?: string | null;
    mode?: string | null;
  };
}) {
  const { cabinet, organization, user } = useAuth();

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Платформа", "Автоматизация"]}
        subtitle="Экспорт, расписания, фоновые задачи и подготовка автоматических отчетов."
        title="Автоматизация"
        updatedAt={lastUpdated ?? undefined}
      />

      <div className="flex flex-wrap items-center gap-2">
        {selectedWorkspace ? <StatusBadge tone="accent">Раздел: {selectedWorkspace}</StatusBadge> : null}
        {selectedFormat ? <StatusBadge tone="neutral">Формат: {selectedFormat}</StatusBadge> : null}
        {actionMessage ? <StatusBadge tone="neutral">{actionMessage}</StatusBadge> : null}
      </div>

      <RuntimeBadge context={workspaceContext} diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Сейчас показываются резервные данные. Основные сценарии останутся доступны."
          title="Часть данных по автоматизации временно недоступна"
          tone="watch"
        />
      ) : null}

      <AutomationOverviewWidget
        cabinet={cabinet?.name ?? "Кабинет не подключен"}
        error={error}
        loading={loading}
        organization={organization?.name ?? "Организация недоступна"}
        owner={user?.name ?? "Пользователь недоступен"}
        selectedWorkspace={selectedWorkspace}
        summary={data.summary}
      />

      <QuickActionsWidget
        actions={data.quickActions}
        error={error}
        loading={loading}
        onGenerate={onGenerate}
        pendingAction={pendingAction}
      />

      <ExportCenterWidget
        error={error}
        exports={data.exports}
        loading={loading}
        onGenerate={onGenerate}
        pendingAction={pendingAction}
        selectedFormat={selectedFormat}
        selectedWorkspace={selectedWorkspace}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <ScheduledReportsWidget
          error={error}
          loading={loading}
          onToggle={onToggleSchedule}
          pendingAction={pendingAction}
          schedules={data.schedules}
        />
        <JobsWidget error={error} jobs={data.jobs} loading={loading} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <ExportHistoryWidget error={error} history={data.history} loading={loading} />
        <AutomationTimelineWidget error={error} loading={loading} timeline={data.timeline} />
      </div>

      <div className="rounded-[28px] border border-[var(--line)] bg-[linear-gradient(135deg,#fff8ed_0%,#f5efe3_55%,#ffffff_100%)] p-6 shadow-[var(--shadow-soft)]">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">
          Доставка уведомлений
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
          Запланированные отчеты будут приходить через раздел уведомлений
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--ink-soft)]">
          Автоматизация управляет выгрузками и расписаниями, а уведомления готовят доставку в Telegram, почту и другие каналы.
        </p>
        <Link
          className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
          href="/notifications"
        >
          Открыть уведомления
        </Link>
      </div>
    </div>
  );
}
