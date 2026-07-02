"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { SettingsNav } from "@/app/settings/settings-nav";
import {
  connectWbCabinetById,
  createWbCabinet,
  deleteWbCabinet,
  discoverWbCabinet,
  fetchWbCabinetApiHealth,
  fetchWbCabinetSyncStatus,
  fetchWbCabinets,
  selectWbCabinet,
  syncWbCabinet,
  testWbCabinet,
  updateWbCabinet,
  useAuth
} from "@/features/auth";
import type { WbCabinetProfile } from "@/features/auth";
import type { WbApiHealthItem, WbCabinetDiscovery, WbSyncJob } from "@/features/auth/services/wb-cabinet-data";
import { formatApiErrorMessage } from "@/shared/api";
import { Button } from "@/shared/components/button";
import { PageHeader } from "@/shared/layout";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";

type TokenForm = {
  seller: string;
  statistics: string;
  advertising: string;
  finance: string;
};

type SyncRange = {
  dateFrom: string;
  dateTo: string;
};

const DEFAULT_TOKENS: TokenForm = {
  seller: "",
  statistics: "",
  advertising: "",
  finance: ""
};

const DEFAULT_SYNC_RANGE: SyncRange = {
  dateFrom: "",
  dateTo: ""
};

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Еще не выполнялась";
  }

  return new Intl.DateTimeFormat("ru-RU", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function toneByStatus(status?: string | null): "healthy" | "watch" | "risk" | "neutral" | "accent" {
  const value = (status ?? "").toLowerCase();
  if (["ok", "success", "connected", "healthy", "high", "completed"].includes(value)) {
    return "healthy";
  }
  if (["partial", "pending", "medium", "watch", "queued", "running"].includes(value)) {
    return "watch";
  }
  if (["error", "failed", "critical", "missing_token", "blocked"].includes(value)) {
    return "risk";
  }
  if (["live", "active"].includes(value)) {
    return "accent";
  }
  return "neutral";
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function asStages(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null);
}

export default function SettingsWbCabinetPage() {
  const { cabinet, context, error, loading, reload } = useAuth();
  const [cabinets, setCabinets] = useState<WbCabinetProfile[]>([]);
  const [health, setHealth] = useState<WbApiHealthItem[]>([]);
  const [jobs, setJobs] = useState<WbSyncJob[]>([]);
  const [discovery, setDiscovery] = useState<WbCabinetDiscovery | null>(null);
  const [formName, setFormName] = useState("");
  const [sellerId, setSellerId] = useState("");
  const [scopes, setScopes] = useState("statistics, advertising, finance");
  const [tokens, setTokens] = useState<TokenForm>(DEFAULT_TOKENS);
  const [syncType, setSyncType] = useState("all");
  const [syncRange, setSyncRange] = useState<SyncRange>(DEFAULT_SYNC_RANGE);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const activeCabinetId = cabinet?.id ?? null;
  const managedCabinet = useMemo(
    () => cabinets.find((item) => item.id === activeCabinetId) ?? cabinet ?? null,
    [activeCabinetId, cabinet, cabinets]
  );
  const latestJob = jobs[0] ?? null;
  const latestJobMeta = asRecord(latestJob?.meta);
  const latestJobStages = asStages(latestJobMeta?.stages);
  const latestJobProgress = typeof latestJobMeta?.progress === "number" ? latestJobMeta.progress : 0;

  const buildCabinetPayload = useCallback(() => {
    const scopeList = scopes
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const tokenPayload = Object.fromEntries(
      Object.entries(tokens).filter((entry) => entry[1].trim().length > 0)
    );

    return {
      organizationId: context?.organizationId ?? null,
      name: formName.trim(),
      sellerId: sellerId.trim(),
      scopes: scopeList,
      tokens: tokenPayload
    };
  }, [context?.organizationId, formName, scopes, sellerId, tokens]);

  const loadCabinetState = useCallback(async () => {
    const list = await fetchWbCabinets();
    setCabinets(list);
    const targetCabinet = list.find((item) => item.id === activeCabinetId) ?? (activeCabinetId ? cabinet : null);
    if (targetCabinet?.id && targetCabinet.id !== "wb_cabinet_unconfigured") {
      const [healthPayload, syncPayload] = await Promise.all([
        fetchWbCabinetApiHealth(targetCabinet.id),
        fetchWbCabinetSyncStatus(targetCabinet.id)
      ]);
      setHealth(healthPayload);
      setJobs(Array.isArray(syncPayload.history) ? syncPayload.history : []);
    } else {
      setHealth([]);
      setJobs([]);
    }
  }, [activeCabinetId, cabinet]);

  useEffect(() => {
    if (!managedCabinet) {
      setFormName("");
      setSellerId("");
      setScopes("statistics, advertising, finance");
      setDiscovery(null);
      return;
    }
    setFormName(managedCabinet.name ?? "");
    setSellerId(managedCabinet.sellerId ?? "");
    setScopes((managedCabinet.scopes ?? ["statistics", "advertising", "finance"]).join(", "));
  }, [managedCabinet]);

  useEffect(() => {
    void loadCabinetState().catch((loadError) => {
      setMessage(formatApiErrorMessage(loadError));
    });
  }, [loadCabinetState]);

  useEffect(() => {
    if (!latestJob || !["queued", "running"].includes(latestJob.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadCabinetState().catch((loadError) => {
        setMessage(formatApiErrorMessage(loadError));
      });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [latestJob, loadCabinetState]);

  const refreshAll = async () => {
    await reload();
    await loadCabinetState();
  };

  const resetTokenInputs = () => setTokens(DEFAULT_TOKENS);

  const saveCabinet = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload = buildCabinetPayload();
      if (managedCabinet && managedCabinet.id !== "wb_cabinet_unconfigured") {
        await updateWbCabinet(managedCabinet.id, payload);
        setMessage("Кабинет обновлен. Токены сохранены только на backend.");
      } else {
        const created = await createWbCabinet(payload);
        await selectWbCabinet(created.id);
        setMessage("Кабинет создан и выбран как активный.");
      }
      resetTokenInputs();
      await refreshAll();
    } catch (saveError) {
      setMessage(formatApiErrorMessage(saveError));
    } finally {
      setSaving(false);
    }
  };

  const runDiscovery = async () => {
    if (!formName.trim()) {
      setMessage("Укажите название кабинета перед проверкой.");
      return;
    }
    setDiscovering(true);
    setMessage(null);
    try {
      const payload = await discoverWbCabinet(buildCabinetPayload());
      setDiscovery(payload);
      setMessage(payload.canConnect ? "Доступ подтвержден. Кабинет готов к подключению и первой синхронизации." : "Часть API недоступна. Проверьте токены и повторите проверку.");
    } catch (discoveryError) {
      setMessage(formatApiErrorMessage(discoveryError));
    } finally {
      setDiscovering(false);
    }
  };

  const runTest = async () => {
    if (!managedCabinet || managedCabinet.id === "wb_cabinet_unconfigured") {
      setMessage("Сначала сохраните кабинет.");
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      const result = await testWbCabinet(managedCabinet.id);
      setMessage(`Проверка завершена: ${result.status}.`);
      await refreshAll();
    } catch (testError) {
      setMessage(formatApiErrorMessage(testError));
    } finally {
      setSaving(false);
    }
  };

  const runConnect = async () => {
    if (!formName.trim()) {
      setMessage("Заполните параметры кабинета перед подключением.");
      return;
    }
    setConnecting(true);
    setMessage(null);
    try {
      let cabinetId = managedCabinet?.id;
      if (!cabinetId || cabinetId === "wb_cabinet_unconfigured") {
        const created = await createWbCabinet(buildCabinetPayload());
        cabinetId = created.id;
        await selectWbCabinet(created.id);
      } else {
        await updateWbCabinet(cabinetId, buildCabinetPayload());
      }
      const result = await connectWbCabinetById(cabinetId);
      setMessage(`Подключение завершено: ${result.status}. Первая синхронизация запущена автоматически.`);
      resetTokenInputs();
      await refreshAll();
    } catch (connectError) {
      setMessage(formatApiErrorMessage(connectError));
    } finally {
      setConnecting(false);
    }
  };

  const runSync = async () => {
    if (!managedCabinet || managedCabinet.id === "wb_cabinet_unconfigured") {
      setMessage("Сначала сохраните кабинет.");
      return;
    }
    setSyncing(true);
    setMessage(null);
    try {
      const result = await syncWbCabinet(managedCabinet.id, {
        type: syncType,
        dateFrom: syncRange.dateFrom || null,
        dateTo: syncRange.dateTo || null
      });
      setMessage(`Синхронизация поставлена в очередь: ${result.job?.status ?? "queued"}.`);
      await refreshAll();
    } catch (syncError) {
      setMessage(formatApiErrorMessage(syncError));
    } finally {
      setSyncing(false);
    }
  };

  const removeCabinet = async (cabinetId: string) => {
    setSaving(true);
    setMessage(null);
    try {
      await deleteWbCabinet(cabinetId);
      setMessage("Кабинет удален.");
      await refreshAll();
    } catch (deleteError) {
      setMessage(formatApiErrorMessage(deleteError));
    } finally {
      setSaving(false);
    }
  };

  const setActiveCabinet = async (cabinetId: string) => {
    setSaving(true);
    setMessage(null);
    try {
      await selectWbCabinet(cabinetId);
      setMessage("Активный кабинет переключен.");
      await refreshAll();
    } catch (selectError) {
      setMessage(formatApiErrorMessage(selectError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Платформа", "Настройки", "Кабинет WB"]}
        subtitle="Подключение живого кабинета Wildberries, проверка API и запуск первой синхронизации без вывода токенов в браузер."
        title="Кабинет Wildberries"
        actions={
          managedCabinet ? (
            <StatusBadge tone={toneByStatus(managedCabinet.status)}>
              {managedCabinet.connected ? "Подключен" : "Ожидает подключения"}
            </StatusBadge>
          ) : null
        }
      />

      <SettingsNav />

      <WidgetCard
        error={error}
        loading={loading}
        status={context ? { label: context.mode === "live" ? "live" : context.mode, tone: context.mode === "live" ? "healthy" : "accent" } : undefined}
        subtitle={managedCabinet?.name ?? "Подключите первый кабинет"}
        title="Параметры подключения"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Название кабинета</span>
            <input
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={formName}
              onChange={(event) => setFormName(event.target.value)}
              placeholder="Например, Основной кабинет VOOGLII"
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Seller ID</span>
            <input
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={sellerId}
              onChange={(event) => setSellerId(event.target.value)}
              placeholder="WB-123456"
            />
          </label>
          <label className="space-y-2 md:col-span-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Секции доступа</span>
            <input
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={scopes}
              onChange={(event) => setScopes(event.target.value)}
              placeholder="statistics, advertising, finance"
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Seller token</span>
            <input
              type="password"
              autoComplete="off"
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={tokens.seller}
              onChange={(event) => setTokens((current) => ({ ...current, seller: event.target.value }))}
              placeholder={managedCabinet?.tokens?.seller ?? "Оставьте пустым, чтобы не менять"}
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Statistics token</span>
            <input
              type="password"
              autoComplete="off"
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={tokens.statistics}
              onChange={(event) => setTokens((current) => ({ ...current, statistics: event.target.value }))}
              placeholder={managedCabinet?.tokens?.statistics ?? "Оставьте пустым, чтобы не менять"}
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Advertising token</span>
            <input
              type="password"
              autoComplete="off"
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={tokens.advertising}
              onChange={(event) => setTokens((current) => ({ ...current, advertising: event.target.value }))}
              placeholder={managedCabinet?.tokens?.advertising ?? "Оставьте пустым, чтобы не менять"}
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Finance token</span>
            <input
              type="password"
              autoComplete="off"
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={tokens.finance}
              onChange={(event) => setTokens((current) => ({ ...current, finance: event.target.value }))}
              placeholder={managedCabinet?.tokens?.finance ?? "Оставьте пустым, чтобы не менять"}
            />
          </label>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Button disabled={saving || !formName.trim()} onClick={() => void saveCabinet()}>
            {managedCabinet && managedCabinet.id !== "wb_cabinet_unconfigured" ? "Сохранить кабинет" : "Создать кабинет"}
          </Button>
          <Button disabled={discovering || !formName.trim()} variant="ghost" onClick={() => void runDiscovery()}>
            {discovering ? "Проверяем API" : "Проверить доступ"}
          </Button>
          <Button disabled={saving || !managedCabinet || managedCabinet.id === "wb_cabinet_unconfigured"} variant="ghost" onClick={() => void runTest()}>
            Проверить токены
          </Button>
          <Button disabled={connecting || !formName.trim()} variant="ghost" onClick={() => void runConnect()}>
            {connecting ? "Подключаем кабинет" : "Подключить и синхронизировать"}
          </Button>
          {message ? <StatusBadge tone="neutral">{message}</StatusBadge> : null}
        </div>

        <div className="mt-5 rounded-[22px] border border-[var(--line)] bg-[var(--panel-strong)] p-4 text-sm leading-7 text-[var(--ink)]">
          Токены отправляются только на backend и после сохранения возвращаются в UI только в маскированном виде.
        </div>

        {discovery ? (
          <div className="mt-5 rounded-[22px] border border-[var(--line)] bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-[var(--ink)]">Результат проверки подключения</p>
                <p className="mt-1 text-xs text-[var(--ink-soft)]">
                  {discovery.canConnect ? "Кабинет готов к первой синхронизации." : "Подключение возможно частично. Недостающие секции останутся в degraded-режиме."}
                </p>
              </div>
              <StatusBadge tone={discovery.canConnect ? "healthy" : "watch"}>
                {discovery.canConnect ? "Готов" : "Частично"}
              </StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {discovery.availableApis.map((item, index) => (
                <div key={`${item.name ?? "api"}-${index}`} className="rounded-[18px] border border-[var(--line)] bg-[var(--panel-strong)] px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--ink)]">{item.name ?? "API"}</p>
                    <StatusBadge tone={toneByStatus(item.status ?? "unknown")}>{item.status ?? "unknown"}</StatusBadge>
                  </div>
                  <p className="mt-1 text-xs text-[var(--ink-soft)]">{item.reason ?? "Статус получен во время live-проверки."}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </WidgetCard>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <WidgetCard subtitle="Состояние seller, statistics, advertising и finance API" title="Здоровье интеграции">
          <div className="space-y-3">
            {health.length > 0 ? (
              health.map((item) => (
                <div key={item.section} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--ink)]">{item.section}</p>
                      <p className="mt-1 text-xs text-[var(--ink-soft)]">{item.message ?? item.requiredAction ?? "Статус будет показан после первой проверки."}</p>
                    </div>
                    <StatusBadge tone={toneByStatus(item.status)}>{item.status}</StatusBadge>
                  </div>
                </div>
              ))
            ) : (
              <p className="rounded-[20px] border border-dashed border-[var(--line)] bg-white px-4 py-5 text-sm text-[var(--ink-soft)]">
                После первой проверки здесь появится состояние подключенных API и рекомендации по токенам.
              </p>
            )}
          </div>
        </WidgetCard>

        <WidgetCard subtitle="Текущий статус подключения и готовность аналитики" title="Активный кабинет">
          <div className="space-y-3 text-sm text-[var(--ink)]">
            <div className="rounded-[20px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)]">Статус</p>
              <div className="mt-2 flex items-center gap-3">
                <StatusBadge tone={toneByStatus(managedCabinet?.status)}>{managedCabinet?.status ?? "not_configured"}</StatusBadge>
                <span>{managedCabinet?.syncMessage ?? "Подключите кабинет и запустите первую синхронизацию."}</span>
              </div>
            </div>
            <div className="rounded-[20px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)]">Последняя синхронизация</p>
              <p className="mt-2 font-semibold">{formatDateTime(managedCabinet?.lastSyncAt)}</p>
            </div>
            <div className="rounded-[20px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)]">Качество данных</p>
              <p className="mt-2 font-semibold">{managedCabinet?.dataQuality ?? "pending"}</p>
            </div>
            <div className="rounded-[20px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)]">Готовность AI Director</p>
              <p className="mt-2 font-semibold">
                {managedCabinet?.connected && managedCabinet?.lastSyncAt ? "Данные загружены, live-аналитика активна" : "Ожидается первое успешное получение данных"}
              </p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <WidgetCard subtitle="Ручной запуск полной или частичной синхронизации" title="Синхронизация">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Тип синхронизации</span>
            <select
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={syncType}
              onChange={(event) => setSyncType(event.target.value)}
            >
              <option value="all">all</option>
              <option value="sales">sales</option>
              <option value="orders">orders</option>
              <option value="products">products</option>
              <option value="cards">cards</option>
              <option value="prices">prices</option>
              <option value="stocks">stocks</option>
              <option value="advertising">advertising</option>
              <option value="finance">finance</option>
              <option value="returns">returns</option>
              <option value="warehouses">warehouses</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Дата от</span>
            <input
              type="date"
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={syncRange.dateFrom}
              onChange={(event) => setSyncRange((current) => ({ ...current, dateFrom: event.target.value }))}
            />
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Дата до</span>
            <input
              type="date"
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={syncRange.dateTo}
              onChange={(event) => setSyncRange((current) => ({ ...current, dateTo: event.target.value }))}
            />
          </label>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Button disabled={syncing || !managedCabinet || managedCabinet.id === "wb_cabinet_unconfigured"} onClick={() => void runSync()}>
            {syncing ? "Ставим задачу в очередь" : "Запустить синхронизацию"}
          </Button>
          {latestJob ? <StatusBadge tone={toneByStatus(latestJob.status)}>{latestJob.status}</StatusBadge> : null}
        </div>

        {latestJob ? (
          <div className="mt-5 rounded-[22px] border border-[var(--line)] bg-[var(--panel-strong)] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-[var(--ink)]">Текущая задача</p>
                <p className="mt-1 text-xs text-[var(--ink-soft)]">
                  {latestJob.type} • старт {formatDateTime(latestJob.startedAt)} • загружено записей: {latestJob.recordsLoaded}
                </p>
              </div>
              <StatusBadge tone={toneByStatus(latestJob.status)}>{latestJob.status}</StatusBadge>
            </div>
            <div className="mt-4 h-3 overflow-hidden rounded-full bg-white">
              <div className="h-full rounded-full bg-[var(--accent)] transition-all" style={{ width: `${Math.max(6, latestJobProgress)}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-[var(--ink-soft)]">
              <span>{String(latestJobMeta?.currentStage ?? "Ожидание выполнения")}</span>
              <span>{latestJobProgress}%</span>
            </div>
            {latestJobStages.length > 0 ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {latestJobStages.map((stage, index) => (
                  <div key={`${String(stage.name ?? "stage")}-${index}`} className="rounded-[18px] border border-[var(--line)] bg-white px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-[var(--ink)]">{String(stage.name ?? "stage")}</p>
                      <StatusBadge tone={toneByStatus(String(stage.status ?? "pending"))}>{String(stage.status ?? "pending")}</StatusBadge>
                    </div>
                    <p className="mt-1 text-xs text-[var(--ink-soft)]">
                      {typeof stage.recordsLoaded === "number" ? `Загружено: ${stage.recordsLoaded}` : "Ожидаем результат этапа"}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
            {latestJob.errorMessage ? <p className="mt-3 text-xs text-[var(--danger)]">{latestJob.errorMessage}</p> : null}
          </div>
        ) : null}

        <div className="mt-5 space-y-3">
          {jobs.length > 0 ? (
            jobs.map((job) => (
              <div key={job.id} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[var(--ink)]">{job.type}</p>
                    <p className="mt-1 text-xs text-[var(--ink-soft)]">
                      {formatDateTime(job.startedAt)} • записей: {job.recordsLoaded}
                    </p>
                  </div>
                  <StatusBadge tone={toneByStatus(job.status)}>{job.status}</StatusBadge>
                </div>
                {job.errorMessage ? <p className="mt-2 text-xs text-[var(--danger)]">{job.errorMessage}</p> : null}
              </div>
            ))
          ) : (
            <p className="rounded-[20px] border border-dashed border-[var(--line)] bg-white px-4 py-5 text-sm text-[var(--ink-soft)]">
              История синхронизаций появится после первого запуска.
            </p>
          )}
        </div>
      </WidgetCard>

      <WidgetCard subtitle="В одном workspace можно хранить несколько кабинетов" title="Список кабинетов">
        <div className="space-y-3">
          {cabinets.length > 0 ? (
            cabinets.map((item) => (
              <div key={item.id} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[var(--ink)]">{item.name}</p>
                    <p className="mt-1 text-xs text-[var(--ink-soft)]">
                      Seller ID: {item.sellerId || "не указан"} • Last sync: {formatDateTime(item.lastSyncAt)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge tone={toneByStatus(item.status)}>{item.status}</StatusBadge>
                    {item.id === activeCabinetId ? (
                      <StatusBadge tone="accent">active</StatusBadge>
                    ) : (
                      <Button disabled={saving} variant="ghost" onClick={() => void setActiveCabinet(item.id)}>
                        Сделать активным
                      </Button>
                    )}
                    <Button disabled={saving} variant="ghost" onClick={() => void removeCabinet(item.id)}>
                      Удалить
                    </Button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="rounded-[20px] border border-dashed border-[var(--line)] bg-white px-4 py-5 text-sm text-[var(--ink-soft)]">
              Добавьте первый кабинет, чтобы подключить живые данные Wildberries к платформе.
            </p>
          )}
        </div>
      </WidgetCard>
    </div>
  );
}
