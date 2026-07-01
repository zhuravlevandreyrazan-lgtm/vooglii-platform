import Link from "next/link";
import { SettingsNav } from "@/app/settings/settings-nav";
import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Платформа", "Настройки"]}
        subtitle="Параметры платформы, готовность к показу, профиль и диагностика кабинета."
        title="Настройки"
      />

      <SettingsNav />

      <div className="grid gap-6 xl:grid-cols-4">
        <WidgetCard subtitle="Готовность к запуску" title="Контроль запуска">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Проверьте доступность сервиса, режим работы, версию и известные ограничения перед показом платформы.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/settings/readiness"
          >
            Открыть раздел готовности
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="Пользователь, организация и кабинет" title="Профиль">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Просматривайте текущую сессию, параметры организации, кабинет продавца и качество синхронизации в одном месте.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/settings/profile"
          >
            Открыть профиль
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="Подключение и диагностика" title="Кабинет WB">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Управляйте подключением кабинета и проверяйте его состояние без показа чувствительных данных на фронтенде.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/settings/wb-cabinet"
          >
            Открыть кабинет
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="Каналы, правила и тестовая отправка" title="Уведомления">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Управляйте маршрутизацией уведомлений и тестовой отправкой без раскрытия секретов Telegram, почты или webhook.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/notifications"
          >
            Открыть уведомления
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="Роли, права и журнал действий" title="Команда">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Проверяйте роли и права доступа, а также безопасно управляйте пользователями через backend-контракт.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/team"
          >
            Открыть команду
          </Link>
        </WidgetCard>
      </div>
    </div>
  );
}
