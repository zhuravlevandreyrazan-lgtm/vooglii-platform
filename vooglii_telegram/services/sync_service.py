from __future__ import annotations

from load_sales import normalize_advertising_status
from vooglii_wb_sync.sync_orchestrator import run_backfill_sync, run_sync
from .token_resolver import resolve_wb_token


def _bot():
    import telegram_bot

    return telegram_bot


def normalize_sync_error(error_code):
    status = str(error_code or "")
    bot = _bot()
    ads_status = normalize_advertising_status(status)
    if ads_status == "ADS_PARTIAL":
        return (
            "⚠ Рекламные данные обновлены частично.\n"
            "Часть кампаний пока не удалось связать с товарами WB."
        )
    if ads_status == "ADS_NO_CAMPAIGNS":
        return "ℹ Активные рекламные кампании WB не найдены."
    if ads_status == "ADS_API_LIMIT" or status.startswith("RATE_LIMIT"):
        return f"⏳ Лимит WB API. Повтор через {bot.rate_text(status)}."
    return f"⚠ Ошибка обновления: {status}"


def run_user_sync(user_id, token=None, days=30):
    if not token:
        resolution = resolve_wb_token(int(user_id))
        token = resolution.token
        if not token:
            return {"saved": 0, "status": "NO_TOKEN", "overall_status": "NO_TOKEN", "blocks": {}}
    result = run_sync(int(user_id), token=token, days=int(days))
    saved = int(((result.get("blocks") or {}).get("sales") or {}).get("rows_inserted") or 0)
    result["saved"] = saved
    result["status"] = result.get("blocks")
    return result


def run_user_backfill(user_id, date_from, date_to, token=None):
    return run_backfill_sync(int(user_id), str(date_from), str(date_to), token=token)


def _format_block_line(name, block):
    bot = _bot()
    status = str(block.get("status") or "")
    raw_status = str(block.get("raw_status") or "")
    next_at = block.get("next_allowed_at")
    if status == "OK":
        return f"OK {bot.block_label(name)}"
    if status == "API_LIMIT":
        suffix = f", повтор после {next_at}" if next_at else ""
        return f"{bot.block_label(name)}: ожидает лимит WB{suffix}"
    if status == "PARTIAL":
        return f"{bot.block_label(name)}: частично"
    if status == "UNAVAILABLE":
        return f"{bot.block_label(name)}: недоступно для периода"
    if status == "NO_TOKEN":
        return f"{bot.block_label(name)}: нет WB токена"
    normalized_ads_status = normalize_advertising_status(raw_status) if name == "advertising" else ""
    if normalized_ads_status == "ADS_NO_CAMPAIGNS":
        return "Реклама WB: активные кампании не найдены"
    return f"{bot.block_label(name)}: {raw_status or status or 'ERROR'}"


def format_sync_result(result):
    bot = _bot()
    saved = int(result.get("saved") or 0)
    blocks = result.get("blocks")
    overall_status = str(result.get("overall_status") or "")

    if isinstance(blocks, dict) and any(isinstance(item, dict) and "raw_status" in item for item in blocks.values()):
        lines = []
        for name in ["sales", "orders", "finance", "advertising", "stocks", "products", "cost"]:
            block = blocks.get(name) or {}
            if not block:
                continue
            lines.append(_format_block_line(name, block))
        if overall_status == "API_LIMIT":
            return "WB API временно ограничил часть блоков.\n\n" + "\n".join(lines)
        if overall_status == "PARTIAL":
            return "Данные обновлены частично.\n\n" + "\n".join(lines)
        if overall_status == "NO_TOKEN":
            return "Не найден WB токен."
        return "Данные обновлены.\n\n" + "\n".join(lines)

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
    for name in ["sales", "orders", "stocks", "finance", "advertising", "products", "cost"]:
        block = blocks.get(name) or {}
        block_status = str(block.get("status") or "PENDING")
        kind = bot._status_kind(block_status)
        normalized_ads_status = normalize_advertising_status(block_status) if name == "advertising" else ""
        if kind != "cooldown":
            all_limited = False
        if kind == "success":
            any_success = True
            lines.append(f"✅ {bot.block_label(name)} обновлены")
        elif kind == "cooldown":
            lines.append(f"⏳ {bot.block_label(name)}: повтор через {bot.rate_text(block_status)}")
        elif normalized_ads_status == "ADS_PARTIAL":
            lines.append("⚠ Рекламные данные обновлены частично.")
            lines.append("Часть кампаний пока не удалось связать с товарами WB.")
        elif normalized_ads_status == "ADS_NO_CAMPAIGNS":
            any_success = True
            lines.append("ℹ Реклама WB: активные кампании не найдены")
        else:
            lines.append(f"⚠ {bot.block_label(name)}: {bot._user_reason_text(block_status)}")

    if all_limited:
        return (
            "⏳ Обновление сейчас недоступно из-за лимитов WB API\n\n"
            "Повторить можно:\n" + "\n".join(lines) +
            "\n\nСтарые данные сохранены.\nОтчеты продолжают работать на последних успешных данных."
        )

    if any_success and any(bot._status_kind((blocks.get(name) or {}).get("status")) != "success" for name in blocks):
        return "⚠ Данные обновлены частично\n\n" + "\n".join(lines)

    return "✅ Данные обновлены\n\n" + "\n".join(lines)
