"use client";

import { useEffect, useState } from "react";
import { SettingsNav } from "@/app/settings/settings-nav";
import { apiEndpoints, formatApiErrorMessage, requestJson, RuntimeBadge } from "@/shared/api";
import { useDemoMode } from "@/shared/demo/demo-provider";
import { PageHeader } from "@/shared/layout";
import { StatusBadge } from "@/shared/status";
import { useWorkspaceContext } from "@/shared/workspace-context";
import { WidgetCard } from "@/shared/widgets";

type StatusPayload = {
  status?: string;
  version?: string;
  build?: string;
  wbApi?: string;
  database?: string;
  analytics?: string;
  ads?: string;
  finance?: string;
  system?: string;
  runtime?: {
    duration_ms?: number;
    cached?: boolean;
    stale?: boolean;
    degraded?: boolean;
    source?: string;
  };
};

type VersionPayload = {
  version?: string;
  build?: string;
  git?: string;
  apiVersion?: string;
  environment?: string;
  buildType?: string;
  frontendVersion?: string;
};

type HealthPayload = {
  status?: string;
  uptimeSeconds?: number;
  memoryUsageMb?: number | null;
  pythonVersion?: string;
  platform?: string;
  applicationVersion?: string;
  frontendVersion?: string;
  environment?: string;
  runtimeMode?: string;
  startup?: {
    ok?: boolean;
    warnings?: string[];
  };
};

type MetricsPayload = {
  startupValidation?: {
    ok?: boolean;
    warnings?: string[];
  };
};

const WORKSPACE_READINESS = [
  "Главная",
  "Бизнес",
  "Финансы",
  "Реклама",
  "Товары",
  "Остатки",
  "ИИ-советник",
  "Отчеты",
  "Карточка товара"
];

const KNOWN_LIMITATIONS = [
  "Демо-режим управляется фронтендом и не сохраняет состояние на сервере.",
  "Выгрузки, расписания и уведомления в dev/RC еще используют безопасные заглушки доставки.",
  "Статус smoke-проверки по-прежнему фиксируется после ручного запуска скриптов."
];

export default function SettingsReadinessPage() {
  const { enabled: demoModeEnabled } = useDemoMode();
  const workspace = useWorkspaceContext();
  const [statusData, setStatusData] = useState<StatusPayload | null>(null);
  const [versionData, setVersionData] = useState<VersionPayload | null>(null);
  const [healthData, setHealthData] = useState<HealthPayload | null>(null);
  const [metricsData, setMetricsData] = useState<MetricsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const [statusPayload, versionPayload, healthPayload, metricsPayload] = await Promise.all([
          requestJson<StatusPayload>(apiEndpoints.status),
          requestJson<VersionPayload>(apiEndpoints.version),
          requestJson<HealthPayload>("/api/health"),
          requestJson<MetricsPayload>("/api/metrics")
        ]);
        setStatusData(statusPayload);
        setVersionData(versionPayload);
        setHealthData(healthPayload);
        setMetricsData(metricsPayload);
      } catch (loadError) {
        setError(formatApiErrorMessage(loadError));
      }
    };
    void run();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Платформа", "Настройки", "Готовность"]}
        subtitle="Краткий чек-лист по доступности платформы, проверкам и текущему режиму работы."
        title="Готовность к запуску"
      />

      <SettingsNav />

      {statusData?.runtime ? (
        <RuntimeBadge
          context={{
            organization: workspace.organization?.name,
            cabinet: workspace.cabinet?.name,
            mode: workspace.mode
          }}
          diagnostics={{
            source: demoModeEnabled ? "demo" : ((statusData.runtime.source as "live" | "cache" | "stale_cache" | "degraded" | "fallback" | "demo") ?? "fallback"),
            degraded: Boolean(statusData.runtime.degraded),
            cached: Boolean(statusData.runtime.cached),
            stale: Boolean(statusData.runtime.stale),
            durationMs: statusData.runtime.duration_ms,
            validationStatus: "ok"
          }}
        />
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard error={error} subtitle="Режим платформы" title="Окружение">
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={demoModeEnabled ? "accent" : "healthy"}>
              {demoModeEnabled ? "Демо-режим" : "Рабочий режим"}
            </StatusBadge>
            <StatusBadge tone="neutral">API: {statusData?.status ?? "Нет данных"}</StatusBadge>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Версия</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.version ?? statusData?.version ?? "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Сборка</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.build ?? statusData?.build ?? "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Коммит</p>
              <p className="mt-2 font-mono text-[var(--ink-soft)]">{versionData?.git ?? "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">API</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.apiVersion ?? "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Окружение</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.environment ?? healthData?.environment ?? "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Тип сборки</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.buildType ?? "нет данных"}</p>
            </div>
          </div>
        </WidgetCard>

        <WidgetCard subtitle="Последние проверки" title="Операционные проверки">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Smoke-проверка</p>
              <p className="mt-2 text-[var(--ink-soft)]">
                Перед показом запускайте `python scripts/smoke_api.py`, `npm.cmd run type-check` и `npm.cmd run build`.
              </p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Известные ограничения</p>
              <p className="mt-2 text-[var(--ink-soft)]">Актуальный список ограничений хранится в `KNOWN_LIMITATIONS.md`.</p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <WidgetCard subtitle="Готовность разделов" title="Покрытие витрины">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {WORKSPACE_READINESS.map((workspace) => (
            <div key={workspace} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold">{workspace}</p>
                <StatusBadge tone="healthy">Готово</StatusBadge>
              </div>
            </div>
          ))}
        </div>
      </WidgetCard>

      <WidgetCard subtitle="Контекст рабочего пространства" title="Выбранные организации и кабинеты">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Количество организаций</p>
            <p className="mt-2 text-sm font-semibold">{workspace.context.organizationCount}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Количество кабинетов</p>
            <p className="mt-2 text-sm font-semibold">{workspace.context.cabinetCount}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Текущая организация</p>
            <p className="mt-2 text-sm font-semibold">{workspace.organization?.name ?? "нет данных"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Текущий кабинет</p>
            <p className="mt-2 text-sm font-semibold">{workspace.cabinet?.name ?? "нет данных"}</p>
          </div>
        </div>
      </WidgetCard>

      <WidgetCard subtitle="Статус подключенных сервисов" title="Сервисы">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[
            ["WB API", statusData?.wbApi],
            ["База данных", statusData?.database],
            ["Аналитика", statusData?.analytics],
            ["Реклама", statusData?.ads],
            ["Финансы", statusData?.finance],
            ["Система", statusData?.system]
          ].map(([label, value]) => (
            <div key={label} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">{label}</p>
              <p className="mt-2 text-sm font-semibold">{value ?? "Нет данных"}</p>
            </div>
          ))}
        </div>
      </WidgetCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard subtitle="Проверки состояния и запуска" title="Состояние">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Время работы</p>
              <p className="mt-2 text-[var(--ink-soft)]">{typeof healthData?.uptimeSeconds === "number" ? `${healthData.uptimeSeconds} c` : "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Память</p>
              <p className="mt-2 text-[var(--ink-soft)]">{typeof healthData?.memoryUsageMb === "number" ? `${healthData.memoryUsageMb} МБ` : "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Python</p>
              <p className="mt-2 text-[var(--ink-soft)]">{healthData?.pythonVersion ?? "нет данных"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Frontend</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.frontendVersion ?? healthData?.frontendVersion ?? "нет данных"}</p>
            </div>
          </div>
        </WidgetCard>

        <WidgetCard subtitle="Развертывание" title="Docker и запуск">
          <div className="grid gap-3">
            <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm">
              <p className="font-semibold">Docker</p>
              <p className="mt-2 text-[var(--ink-soft)]">В репозитории уже есть multi-stage Dockerfile для backend и frontend, а также compose-конфигурации.</p>
            </div>
            <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm">
              <p className="font-semibold">Проверка запуска</p>
              <p className="mt-2 text-[var(--ink-soft)]">
                {metricsData?.startupValidation?.ok ? "Проверка запуска проходит успешно." : "Проверка запуска вернула предупреждения."}
              </p>
            </div>
            <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm">
              <p className="font-semibold">Статус развертывания</p>
              <p className="mt-2 text-[var(--ink-soft)]">Платформа готова к VPS или cloud-развертыванию с отдельными примерами env и CI-проверками сборки.</p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <WidgetCard subtitle="Сервисы платформы" title="Автоматизация">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Выгрузки, расписания и фоновые задачи уже подготовлены для production-среды.
          </p>
        </WidgetCard>
        <WidgetCard subtitle="Сервисы платформы" title="Уведомления">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Раздел уведомлений отслеживается, а безопасные заглушки доставки остаются отделены от production-секретов.
          </p>
        </WidgetCard>
        <WidgetCard subtitle="Сервисы платформы" title="Доступ">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Контекст пользователя, организации и кабинета доступен в проверках запуска, состоянии и разделе готовности.
          </p>
        </WidgetCard>
      </div>

      <WidgetCard subtitle="Заметки по релизу" title="Известные ограничения">
        <div className="grid gap-3">
          {KNOWN_LIMITATIONS.map((item) => (
            <div key={item} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm text-[var(--ink-soft)]">
              {item}
            </div>
          ))}
        </div>
      </WidgetCard>
    </div>
  );
}
