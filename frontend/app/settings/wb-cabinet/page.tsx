"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { SettingsNav } from "@/app/settings/settings-nav";
import {
  createWbCabinet,
  deleteWbCabinet,
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
import type { WbApiHealthItem, WbSyncJob } from "@/features/auth/services/wb-cabinet-data";
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

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Еще не выполнялось";
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
  if (["ok", "success", "connected", "healthy", "high"].includes(value)) {
    return "healthy";
  }
  if (["partial", "pending", "medium", "watch"].includes(value)) {
    return "watch";
  }
  if (["error", "failed", "critical", "missing_token"].includes(value)) {
    return "risk";
  }
  return "neutral";
}

const DEFAULT_TOKENS: TokenForm = {
  seller: "",
  statistics: "",
  advertising: "",
  finance: ""
};

const DEFAULT_SYNC_RANGE = {
  dateFrom: "",
  dateTo: ""
};

export default function SettingsWbCabinetPage() {
  const { cabinet, context, error, loading, reload } = useAuth();
  const [cabinets, setCabinets] = useState<WbCabinetProfile[]>([]);
  const [health, setHealth] = useState<WbApiHealthItem[]>([]);
  const [jobs, setJobs] = useState<WbSyncJob[]>([]);
  const [formName, setFormName] = useState("");
  const [sellerId, setSellerId] = useState("");
  const [scopes, setScopes] = useState("statistics, advertising, finance");
  const [tokens, setTokens] = useState<TokenForm>(DEFAULT_TOKENS);
  const [syncType, setSyncType] = useState("all");
  const [syncRange, setSyncRange] = useState(DEFAULT_SYNC_RANGE);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const activeCabinetId = cabinet?.id ?? null;
  const managedCabinet = useMemo(
    () => cabinets.find((item) => item.id === activeCabinetId) ?? cabinet ?? null,
    [activeCabinetId, cabinet, cabinets]
  );

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

  const resetTokenInputs = () => setTokens(DEFAULT_TOKENS);

  const refreshAll = async () => {
    await reload();
    await loadCabinetState();
  };

  const saveCabinet = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const scopeList = scopes
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const tokenPayload = Object.fromEntries(
        Object.entries(tokens).filter((entry) => entry[1].trim().length > 0)
      );
      const payload = {
        organizationId: context?.organizationId ?? null,
        name: formName.trim(),
        sellerId: sellerId.trim(),
        scopes: scopeList,
        tokens: tokenPayload
      };

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
      setMessage(`Синхронизация завершена со статусом ${result.job?.status ?? "unknown"}.`);
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
        subtitle="Подключение реального кабинета Wildberries, проверка токенов и запуск первой синхронизации без вывода raw token в браузер."
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
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Scopes</span>
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
          <Button disabled={saving || !managedCabinet || managedCabinet.id === "wb_cabinet_unconfigured"} variant="ghost" onClick={() => void runTest()}>
            Проверить токены
          </Button>
          {message ? <StatusBadge tone="neutral">{message}</StatusBadge> : null}
        </div>

        <div className="mt-5 rounded-[22px] border border-[var(--line)] bg-[var(--panel-strong)] p-4 text-sm leading-7 text-[var(--ink)]">
          Токены отправляются только на backend и после сохранения возвращаются в UI только в маскированном виде.
        </div>
      </WidgetCard>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <WidgetCard subtitle="Тест доступности API" title="Состояние секций">
          <div className="space-y-3">
            {health.length > 0 ? (
              health.map((item) => (
                <div key={item.section} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--ink)]">{item.section}</p>
                      <p className="mt-1 text-xs text-[var(--ink-soft)]">{item.message ?? item.requiredAction ?? "Статус пока не получен"}</p>
                    </div>
                    <StatusBadge tone={toneByStatus(item.status)}>{item.status}</StatusBadge>
                  </div>
                </div>
              ))
            ) : (
              <p className="rounded-[20px] border border-dashed border-[var(--line)] bg-white px-4 py-5 text-sm text-[var(--ink-soft)]">
                После первой проверки здесь появится состояние seller, statistics, advertising и finance API.
              </p>
            )}
          </div>
        </WidgetCard>

        <WidgetCard subtitle="Последний sync и качество данных" title="Активный кабинет">
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
          </div>
        </WidgetCard>
      </div>

      <WidgetCard subtitle="Запуск первой или повторной синхронизации" title="Синхронизация">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Тип sync</span>
            <select
              className="w-full rounded-[18px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              value={syncType}
              onChange={(event) => setSyncType(event.target.value)}
            >
              <option value="all">all</option>
              <option value="sales">sales</option>
              <option value="orders">orders</option>
              <option value="stocks">stocks</option>
              <option value="advertising">advertising</option>
              <option value="finance">finance</option>
              <option value="products">products</option>
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
            Запустить sync
          </Button>
        </div>

        <div className="mt-5 space-y-3">
          {jobs.length > 0 ? (
            jobs.map((job) => (
              <div key={job.id} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[var(--ink)]">{job.type}</p>
                    <p className="mt-1 text-xs text-[var(--ink-soft)]">
                      {formatDateTime(job.startedAt)} · записей: {job.recordsLoaded}
                    </p>
                  </div>
                  <StatusBadge tone={toneByStatus(job.status)}>{job.status}</StatusBadge>
                </div>
                {job.errorMessage ? <p className="mt-2 text-xs text-[var(--danger)]">{job.errorMessage}</p> : null}
              </div>
            ))
          ) : (
            <p className="rounded-[20px] border border-dashed border-[var(--line)] bg-white px-4 py-5 text-sm text-[var(--ink-soft)]">
              История sync появится после первого запуска.
            </p>
          )}
        </div>
      </WidgetCard>

      <WidgetCard subtitle="Несколько кабинетов можно хранить в одном workspace" title="Список кабинетов">
        <div className="space-y-3">
          {cabinets.length > 0 ? (
            cabinets.map((item) => (
              <div key={item.id} className="rounded-[20px] border border-[var(--line)] bg-white px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[var(--ink)]">{item.name}</p>
                    <p className="mt-1 text-xs text-[var(--ink-soft)]">
                      Seller ID: {item.sellerId || "не указан"} · Last sync: {formatDateTime(item.lastSyncAt)}
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
              Добавьте первый кабинет, чтобы подключить реальные данные Wildberries к платформе.
            </p>
          )}
        </div>
      </WidgetCard>
    </div>
  );
}
