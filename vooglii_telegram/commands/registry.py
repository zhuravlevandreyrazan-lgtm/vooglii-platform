from __future__ import annotations

from dataclasses import dataclass

from security.permissions import permission_for_command


@dataclass(frozen=True)
class CommandSpec:
    name: str
    title: str
    description: str
    category: str
    visible_in_menu: bool = False
    visible_in_help: bool = False
    permission: str = ""


def _spec(name: str, title: str, description: str, category: str, *, menu: bool = False, help_item: bool = False) -> CommandSpec:
    return CommandSpec(
        name=name,
        title=title,
        description=description,
        category=category,
        visible_in_menu=menu,
        visible_in_help=help_item,
        permission=permission_for_command(name),
    )


COMMAND_SPECS = [
    _spec("start", "Старт", "Запустить VOOGLII Terminal", "customer", help_item=True),
    _spec("help", "Помощь", "Показать доступные команды", "customer", help_item=True),
    _spec("menu", "Меню", "Открыть главное меню", "customer", menu=True, help_item=True),
    _spec("connect", "Подключить кабинет", "Подключить кабинет Wildberries", "customer", menu=True, help_item=True),
    _spec("disconnect", "Отключить кабинет", "Безопасно удалить WB-токен", "customer", help_item=True),
    _spec("update", "Обновить данные", "Запустить синхронизацию данных", "customer", menu=True, help_item=True),
    _spec("sync", "Синхронизация", "Статус и история автоматических повторов WB", "customer", help_item=True),
    _spec("dashboard", "Главная сводка", "Главный экран и бизнес-сводка", "customer", menu=True, help_item=True),
    _spec("report", "Отчёт", "Ключевой отчёт за выбранный период", "customer", menu=True, help_item=True),
    _spec("business", "Бизнес", "Состояние бизнеса и рекомендации", "customer", menu=True, help_item=True),
    _spec("finance", "Финансы", "Прибыль, выплаты и деньги", "customer", menu=True, help_item=True),
    _spec("advert", "Реклама", "Аналитика рекламы Wildberries", "customer", menu=True, help_item=True),
    _spec("products", "Товары", "SKU, ассортимент и прибыльность", "customer", menu=True, help_item=True),
    _spec("cost", "Себестоимость", "Диагностика и заполнение себестоимости SKU", "customer", help_item=True),
    _spec("stocks", "Остатки", "Остатки и риски out-of-stock", "customer", menu=True, help_item=True),
    _spec("forecast", "Прогноз", "План пополнения и будущие риски", "customer", menu=True, help_item=True),
    _spec("validate", "Валидация", "Сертификация VOOGLII по weekly report WB", "customer", help_item=True),
    _spec("advisor", "Советник", "AI-рекомендации по бизнесу", "customer", menu=True, help_item=True),
    _spec("system", "Система", "Состояние данных и синхронизаций", "customer", menu=True, help_item=True),
    _spec("profile", "Профиль", "Статус кабинета и подписки", "customer", menu=True, help_item=True),
    _spec("tariff", "Тариф", "Информация о тарифе VOOGLII", "customer", help_item=True),
    _spec("admin", "Администрирование", "Служебные действия для администраторов", "admin"),
    _spec("health", "Health", "Проверка состояния бота", "admin"),
    _spec("syncstatus", "Sync Status", "Технический статус синхронизации", "admin"),
    _spec("apistatus", "API Status", "Технический статус API", "admin"),
    _spec("control", "Control", "Внутренний контрольный центр", "admin"),
    _spec("migration", "Migration", "Статус миграции", "admin"),
    _spec("performance", "Performance", "Диагностика производительности", "admin"),
    _spec("structure", "Structure", "Проверка структуры проекта", "admin"),
    _spec("telegram", "Telegram", "Внутренняя диагностика Telegram", "developer"),
    _spec("ui", "UI", "Внутренние UI-спеки", "developer"),
    _spec("rc", "Release Candidate", "Диагностика RC", "developer"),
    _spec("data", "Data", "Внутренняя диагностика данных", "developer"),
    _spec("adsfullstatsprobe", "Ads Probe", "Низкоуровневая диагностика ads fullstats", "developer"),
]


COMMAND_SPEC_MAP = {spec.name: spec for spec in COMMAND_SPECS}


def get_command_spec(name: str | None) -> CommandSpec | None:
    return COMMAND_SPEC_MAP.get(str(name or "").strip().lower())


def get_commands_for_category(category: str) -> list[CommandSpec]:
    return [spec for spec in COMMAND_SPECS if spec.category == category]


def get_customer_menu_commands() -> list[CommandSpec]:
    return [spec for spec in COMMAND_SPECS if spec.category == "customer" and spec.visible_in_menu]


def get_customer_help_commands() -> list[CommandSpec]:
    return [spec for spec in COMMAND_SPECS if spec.category == "customer" and spec.visible_in_help]
