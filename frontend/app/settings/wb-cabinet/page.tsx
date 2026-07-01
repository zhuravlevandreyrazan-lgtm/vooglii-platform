"use client";

import { useState } from "react";
import { SettingsNav } from "@/app/settings/settings-nav";
import { connectWbCabinet, disconnectWbCabinet, useAuth } from "@/features/auth";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";

function formatDate(value?: string | null) {
  if (!value) {
    return "Еще не синхронизировано";
  }

  return new Intl.DateTimeFormat("ru-RU", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function qualityScore(label?: string) {
  switch ((label ?? "").toLowerCase()) {
    case "high":
    case "showcase":
      return 90;
    case "medium":
      return 70;
    case "pending":
      return 50;
    default:
      return 60;
  }
}

export default function SettingsWbCabinetPage() {
  const { cabinet, context, error, loading, reload } = useAuth();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);

  const runAction = async (action: "connect" | "disconnect") => {
    setActionPending(true);
    setActionMessage(null);
    try {
      if (action === "connect") {
        const nextCabinet = await connectWbCabinet();
        setActionMessage(`Кабинет ${nextCabinet.name} ответил со статусом ${nextCabinet.status}.`);
      } else {
        const nextCabinet = await disconnectWbCabinet();
        setActionMessage(`Кабинет ${nextCabinet.name} ответил со статусом ${nextCabinet.status}.`);
      }
      await reload();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Не удалось выполнить действие с кабинетом.";
      setActionMessage(message);
    } finally {
      setActionPending(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Платформа", "Настройки", "Кабинет WB"]}
        subtitle="Диагностика кабинета и безопасные действия подключения или отключения без раскрытия реальных токенов."
        title="Кабинет WB"
        actions={
          cabinet ? (
            <StatusBadge tone={cabinet.connected ? "healthy" : "watch"}>
              {cabinet.connected ? "Подключен" : "Не подключен"}
            </StatusBadge>
          ) : null
        }
      />

      <SettingsNav />

      <WidgetCard
        error={error}
        loading={loading}
        status={context ? { label: context.mode, tone: context.mode === "demo" ? "accent" : "neutral" } : undefined}
        subtitle={cabinet?.name ?? "Профиль кабинета"}
        title="Состояние подключения"
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ID продавца</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.sellerId ?? "нет данных"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Статус токена</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.tokenStatus ?? "нет данных"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Последняя синхронизация</p>
            <p className="mt-2 text-sm font-semibold">{formatDate(cabinet?.lastSyncAt)}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Статус кабинета</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.status ?? "нет данных"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Качество данных</p>
            <div className="mt-2">
              <HealthBadge label={cabinet?.dataQuality ?? "Нет данных"} score={qualityScore(cabinet?.dataQuality)} />
            </div>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Контекст рабочего пространства</p>
            <p className="mt-2 text-sm font-semibold">{context?.cabinetId ?? "нет данных"}</p>
          </div>
        </div>

        <div className="mt-5 rounded-[22px] border border-[color:rgba(176,122,24,0.24)] bg-[color:rgba(176,122,24,0.08)] p-4 text-sm leading-7 text-[var(--ink)]">
          Не вставляйте реальные токены Wildberries в демо- или тестовом режиме. Работа с боевыми токенами должна оставаться только на backend по HTTPS.
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Button disabled={actionPending} onClick={() => void runAction("connect")}>
            Подключить кабинет
          </Button>
          <Button disabled={actionPending} variant="ghost" onClick={() => void runAction("disconnect")}>
            Отключить кабинет
          </Button>
          {actionMessage ? <StatusBadge tone="neutral">{actionMessage}</StatusBadge> : null}
        </div>
      </WidgetCard>
    </div>
  );
}
