from __future__ import annotations

from load_sales import load_sales_for_user


def _bot():
    import telegram_bot

    return telegram_bot


def normalize_sync_error(error_code):
    status = str(error_code or "")
    bot = _bot()
    if status.startswith("ADS_PARTIAL_MISSING_IDS"):
        return (
            "⚠ Рекламные данные обновлены частично.\n"
            "Часть кампаний пока не удалось связать с товарами WB."
        )
    if status.startswith("RATE_LIMIT"):
        return f"⏳ Лимит WB API. Повтор через {bot.rate_text(status)}."
    return f"⚠ Ошибка обновления: {status}"


def run_user_sync(user_id, token, days=30):
    saved, status = load_sales_for_user(user_id, token, days, False, True)
    return {"saved": saved, "status": status}


def format_sync_result(result):
    bot = _bot()
    saved = int(result.get("saved") or 0)
    status = result.get("status")

    if not isinstance(status, dict):
        if str(status).startswith("RATE_LIMIT"):
            return f"⏳ Лимит WB API. Повтор через {bot.rate_text(status)}."
        if str(status).startswith("SUCCESS"):
            return f"✅ Обновление завершено.\nНовых продаж: {saved}"
        return normalize_sync_error(status)

    blocks = status.get("blocks", {})
    all_limited = True
    any_success = False
    lines = []
    for name in ["sales", "orders", "stocks", "finance", "advertising"]:
        block = blocks.get(name) or {}
        block_status = str(block.get("status") or "PENDING")
        kind = bot._status_kind(block_status)
        if kind != "cooldown":
            all_limited = False
        if kind == "success":
            any_success = True
            lines.append(f"✅ {bot.block_label(name)} обновлены")
        elif kind == "cooldown":
            lines.append(f"⏳ {bot.block_label(name)}: повтор через {bot.rate_text(block_status)}")
        elif block_status.startswith("ADS_PARTIAL_MISSING_IDS"):
            lines.append("⚠ Рекламные данные обновлены частично.")
            lines.append("Часть кампаний пока не удалось связать с товарами WB.")
        else:
            lines.append(f"⚠ {bot.block_label(name)}: {bot._user_reason_text(block_status)}")

    if all_limited:
        return (
            "⏳ Обновление сейчас недоступно из-за лимитов WB API\n\n"
            "Повторить можно:\n" + "\n".join(lines) +
            "\n\nСтарые данные сохранены.\nОтчёты продолжают работать на последних успешных данных."
        )

    if any_success and any(bot._status_kind((blocks.get(name) or {}).get("status")) != "success" for name in blocks):
        return "⚠ Данные обновлены частично\n\n" + "\n".join(lines)

    return "✅ Данные обновлены\n\n" + "\n".join(lines)
