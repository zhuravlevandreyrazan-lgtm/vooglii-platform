from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from load_sales import normalize_advertising_status
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict
from vooglii_wb_sync.sync_orchestrator import (
    run_backfill_sync,
    run_post_sync_rebuild,
    run_single_block_sync,
    run_sync,
)
from vooglii_wb_sync.sync_queue import (
    QUEUE_DONE,
    QUEUE_FAILED,
    QUEUE_WAIT_LIMIT,
    claim_ready_tasks,
    get_next_sync_task,
    list_sync_history,
)
from vooglii_wb_sync.sync_state import list_sync_state

from .token_resolver import resolve_wb_token


def _bot():
    import telegram_bot

    return telegram_bot


def _parse_dt(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass
    return None


def format_user_time(dt_value, timezone: str = "Europe/Moscow") -> str:
    dt = dt_value if isinstance(dt_value, datetime) else _parse_dt(dt_value)
    if not dt:
        return "-"
    tz = ZoneInfo(timezone)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.astimezone(tz)
    suffix = "МСК" if timezone == "Europe/Moscow" else timezone
    return f"{dt.strftime('%H:%M')} {suffix}"


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


def _retry_source(payload: dict | None) -> str:
    meta = dict((payload or {}).get("meta") or {})
    return str(meta.get("retry_source") or "")


def _history_retry_source(message: str | None) -> str:
    text = str(message or "")
    marker = "retry_source="
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip().split()[0]


def _retry_text(next_at, retry_source: str) -> str:
    if not next_at:
        return "скоро"
    formatted = format_user_time(next_at)
    if retry_source == "default_policy":
        return f"примерно в {formatted}"
    return formatted


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
        suffix = "обновлён" if name == "products" else "обновлена" if name == "cost" else "обновлены"
        if name == "cost" and str(raw_status).upper().startswith("MISSING_COST_VALUES"):
            suffix = "заполнена частично"
        return f"✅ {bot.block_label(name)} {suffix}"
    if status == "API_LIMIT":
        retry_source = _retry_source(block)
        if next_at:
            if retry_source == "default_policy":
                retry_text = f"\nАвтоматически повторю примерно в {format_user_time(next_at)}"
            else:
                retry_text = f"\nАвтоматически повторю после {format_user_time(next_at)}"
        else:
            retry_text = ""
        if name == "advertising":
            return f"⏳ {bot.block_label(name)} временно ограничена WB{retry_text}"
        return f"⏳ {bot.block_label(name)} временно ограничены WB{retry_text}"
    if status == "PARTIAL":
        if name == "cost":
            return "⚠ Себестоимость заполнена частично"
        if name == "advertising":
            return f"⚠ {bot.block_label(name)} обновлена частично"
        return f"⚠ {bot.block_label(name)} обновлены частично"
    if status == "UNAVAILABLE":
        return f"⚠ {bot.block_label(name)} недоступны для периода"
    if status == "NO_TOKEN":
        return f"⚠ {bot.block_label(name)}: нет WB токена"
    normalized_ads_status = normalize_advertising_status(raw_status) if name == "advertising" else ""
    if normalized_ads_status == "ADS_NO_CAMPAIGNS":
        return "ℹ Реклама WB: активные кампании не найдены"
    return f"⚠ {bot.block_label(name)}: {raw_status or status or 'ERROR'}"


def format_sync_result(result):
    saved = int(result.get("saved") or 0)
    blocks = result.get("blocks")
    overall_status = str(result.get("overall_status") or "")

    if isinstance(blocks, dict) and any(isinstance(item, dict) and "raw_status" in item for item in blocks.values()):
        lines = [
            _format_block_line(name, blocks.get(name) or {})
            for name in ["sales", "orders", "finance", "advertising", "stocks", "products", "cost"]
            if blocks.get(name)
        ]
        if overall_status == "API_LIMIT":
            return "Часть WB-блоков временно ограничена.\n\n" + "\n".join(lines)
        if overall_status == "PARTIAL":
            return "Данные обновлены частично.\n\n" + "\n".join(lines)
        if overall_status == "NO_TOKEN":
            return "Не найден WB токен."
        return "Данные обновлены.\n\n" + "\n".join(lines)

    status = result.get("status")
    if not isinstance(status, dict):
        return normalize_sync_error(status)
    legacy_blocks = dict(status.get("blocks") or {})
    if legacy_blocks:
        bot = _bot()
        all_limited = True
        any_success = False
        lines = []
        for name in ["sales", "orders", "stocks", "finance", "advertising", "products", "cost"]:
            block = legacy_blocks.get(name) or {}
            block_status = str(block.get("status") or "PENDING")
            kind = bot._status_kind(block_status)
            normalized_ads_status = normalize_advertising_status(block_status) if name == "advertising" else ""
            if kind != "cooldown":
                all_limited = False
            if kind == "success":
                any_success = True
                suffix = "обновлена" if name == "advertising" else "обновлён" if name == "products" else "обновлена" if name == "cost" else "обновлены"
                lines.append(f"✅ {bot.block_label(name)} {suffix}")
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
            return "⏳ Обновление сейчас недоступно из-за лимитов WB API\n\n" + "\n".join(lines)
        if any_success and any(bot._status_kind((legacy_blocks.get(name) or {}).get("status")) != "success" for name in legacy_blocks):
            return "⚠ Данные обновлены частично\n\n" + "\n".join(lines)
    return f"✅ Обновление завершено.\nНовых продаж: {saved}"


def _sync_status_line(block_name: str, state: dict, queue_task: dict | None) -> str:
    bot = _bot()
    status = str((state or {}).get("status") or "MISSING")
    if status == "OK":
        if block_name == "cost":
            return "Себестоимость: заполнена"
        if block_name == "products":
            return "Каталог товаров: обновлён"
        if block_name == "advertising":
            return "Реклама: обновлена"
        return f"{bot.block_label(block_name)}: обновлены"
    if status == "PARTIAL":
        if block_name == "cost":
            return "Себестоимость: заполнена частично"
        if block_name == "advertising":
            return "Реклама: обновлена частично"
        return f"{bot.block_label(block_name)}: частично"
    if status == "API_LIMIT":
        next_at = (queue_task or {}).get("run_after") or (state or {}).get("next_allowed_at")
        retry_source = _retry_source(state)
        label = _retry_text(next_at, retry_source)
        return f"{bot.block_label(block_name)}: ожидает лимит WB\nСледующая попытка: {label}"
    if status == "UNAVAILABLE":
        return f"{bot.block_label(block_name)}: недоступны"
    if status == "NO_TOKEN":
        return f"{bot.block_label(block_name)}: нет токена"
    return f"{bot.block_label(block_name)}: ожидает обновления"


def build_sync_status_text(user_id: int) -> str:
    state_map = list_sync_state(int(user_id))
    lines = ["Синхронизация WB", ""]
    for block_name in ["sales", "orders", "finance", "advertising", "stocks", "products", "cost"]:
        lines.append(_sync_status_line(block_name, state_map.get(block_name) or {}, get_next_sync_task(int(user_id), block_name)))
    return "\n".join(lines)


def build_sync_history_text(user_id: int, limit: int = 10) -> str:
    bot = _bot()
    rows = list_sync_history(int(user_id), limit=int(limit))
    lines = ["История синхронизации WB", ""]
    if not rows:
        lines.append("Событий пока нет.")
        return "\n".join(lines)
    for row in rows:
        created_at = format_user_time(row.get("created_at"))
        block_label = bot.block_label(row.get("block"))
        status = str(row.get("status") or "")
        source_rows = int(row.get("source_rows") or 0)
        retry_at = row.get("retry_at")
        if status == "OK":
            lines.append(f"{created_at} {block_label} - OK, {source_rows} rows")
        elif status == "API_LIMIT":
            retry_source = _history_retry_source(row.get("message"))
            lines.append(f"{created_at} {block_label} - WAIT_LIMIT, retry {_retry_text(retry_at, retry_source)}")
        elif status == "PARTIAL":
            lines.append(f"{created_at} {block_label} - PARTIAL, {source_rows} rows")
        else:
            lines.append(f"{created_at} {block_label} - {status}")
    return "\n".join(lines)


def run_sync_queue_worker(*, now: str | None = None, bot=None, limit: int = 10) -> dict[str, object]:
    claimed = claim_ready_tasks(now=now, limit=limit)
    processed: list[dict[str, object]] = []
    for task in claimed:
        period = (str(task["period_from"]), str(task["period_to"]))
        result = run_single_block_sync(int(task["user_id"]), str(task["block"]), period)
        status = str(result.get("status") or "")
        if status == "OK":
            rebuild = run_post_sync_rebuild(int(task["user_id"]), period)
            from vooglii_wb_sync.sync_queue import update_sync_task

            update_sync_task(int(task["id"]), QUEUE_DONE, last_error=None)
            processed.append({"task": task, "result": result, "rebuild": rebuild})
            continue
        if status == "API_LIMIT":
            from vooglii_wb_sync.sync_queue import update_sync_task

            update_sync_task(
                int(task["id"]),
                QUEUE_WAIT_LIMIT,
                run_after=result.get("next_allowed_at"),
                last_error=str(result.get("raw_status") or ""),
            )
            processed.append({"task": task, "result": result})
            continue
        from vooglii_wb_sync.sync_queue import update_sync_task

        update_sync_task(int(task["id"]), QUEUE_FAILED, last_error=str(result.get("raw_status") or status))
        processed.append({"task": task, "result": result})
    return {"claimed": len(claimed), "processed": processed}
