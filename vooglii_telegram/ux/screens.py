from .design import BRAND_NAME, PRODUCT_NAME, status_dot, title


def start_screen(command_lines: list[str]) -> str:
    lines = [
        title("🏢", PRODUCT_NAME),
        "",
        "Центр управления бизнесом на Wildberries.",
        "",
        "Я помогу контролировать:",
        "📊 продажи",
        "💰 прибыль и выплаты",
        "📦 товары и остатки",
        "📣 рекламу",
        "🤖 рекомендации",
        "",
        "Быстрый старт:",
        "1. Подключите кабинет WB - /connect",
        "2. Обновите данные - /update",
        "3. Откройте главную сводку - /home",
        "",
        "Главные разделы:",
    ]
    lines.extend(command_lines)
    return "\n".join(lines)


def menu_screen() -> str:
    from .navigation import customer_menu_sections

    lines = [title("🏢", BRAND_NAME), "", "Главное меню", ""]
    for header, items in customer_menu_sections():
        lines.append(header)
        lines.extend(items)
        lines.append("")
    return "\n".join(lines).strip()


def profile_screen(username: str, tariff: str, role: str, wb_status: str, subscription: str, tax_mode: str, actions: list[str]) -> str:
    lines = [
        title("👤", "Ваш кабинет VOOGLII"),
        "",
        f"Пользователь: {username}",
        f"Тариф: {tariff}",
        f"Роль: {role}",
        f"Статус WB: {wb_status}",
        f"Подписка: {subscription}",
        f"Налоговый режим: {tax_mode}",
    ]
    if actions:
        lines.extend(["", "Что можно сделать:"])
        lines.extend(actions)
    return "\n".join(lines)


def home_screen(
    period_label: str,
    cards: list[tuple[str, str, str]],
    actions: list[str],
    sections: list[str],
    mode_label: str | None = None,
    mode_hint: str | None = None,
    validation_summary: str | None = None,
) -> str:
    lines = [title("🏢", BRAND_NAME), "", "Главная сводка", "", f"Период: {period_label}"]
    if mode_label:
        lines.extend(["", "Режим:", mode_label])
    if mode_hint:
        lines.append(mode_hint)
    lines.append("")
    for header, status, message in cards:
        lines.extend([f"{status_dot(status)} {header}", message, ""])
    if validation_summary:
        lines.extend([validation_summary, ""])
    lines.append("Что сделать сейчас:")
    lines.extend(actions)
    lines.extend(["", "Разделы:"])
    lines.extend(sections)
    return "\n".join(lines)


def system_customer_screen(items: list[str], actions: list[str]) -> str:
    lines = [title("⚙", "Состояние VOOGLII"), ""]
    lines.extend(items)
    lines.extend(["", "Что можно сделать:"])
    lines.extend(actions)
    return "\n".join(lines)


def business_screen(
    period_label: str,
    status_text: str,
    highlights: list[str],
    actions: list[str],
    next_sections: list[str],
    mode_label: str | None = None,
    mode_hint: str | None = None,
    validation_summary: str | None = None,
) -> str:
    lines = [title("📊", "Бизнес"), "", f"Период: {period_label}"]
    if mode_label:
        lines.extend(["", "Режим:", mode_label])
    if mode_hint:
        lines.append(mode_hint)
    lines.extend(["", "Статус:", status_text, "", "Главное:"])
    lines.extend(highlights)
    if validation_summary:
        lines.extend(["", validation_summary])
    lines.extend(["", "Что сделать сегодня:"])
    lines.extend(actions)
    lines.extend(["", "Следующие разделы:"])
    lines.extend(next_sections)
    return "\n".join(lines)


def finance_screen(
    period_label: str,
    status_text: str,
    money_lines: list[str],
    important_note: str,
    actions: list[str],
    mode_label: str | None = None,
    mode_hint: str | None = None,
    validation_summary: str | None = None,
) -> str:
    lines = [title("💰", "Финансы"), "", f"Период: {period_label}"]
    if mode_label:
        lines.extend(["", "Режим:", mode_label])
    if mode_hint:
        lines.append(mode_hint)
    lines.extend(["", "Статус:", status_text, "", "Деньги:"])
    lines.extend(money_lines)
    if validation_summary:
        lines.extend(["", validation_summary])
    lines.extend(["", "Важно:", important_note, "", "Что сделать:"])
    lines.extend(actions)
    return "\n".join(lines)


def products_screen(status_text: str, sku_lines: list[str], stock_note: str, actions: list[str]) -> str:
    lines = [title("📦", "Товары"), "", "Статус:", status_text, "", "SKU:"]
    lines.extend(sku_lines)
    lines.extend(["", "Остатки:", stock_note, "", "Что сделать:"])
    lines.extend(actions)
    return "\n".join(lines)


def analytics_screen(period_label: str, summary_lines: list[str], actions: list[str]) -> str:
    lines = [title("📈", "Аналитика"), "", f"Период: {period_label}", "", "Главное:"]
    lines.extend(summary_lines)
    lines.extend(["", "Что открыть:"])
    lines.extend(actions)
    return "\n".join(lines)
