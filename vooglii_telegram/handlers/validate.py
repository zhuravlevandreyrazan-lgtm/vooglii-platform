from __future__ import annotations

from vooglii_telegram.ux.financial_modes import automatic_validation_message
from vooglii_validation.validator import get_latest_validation_result, list_validation_history

from ._bot import get_bot


def _build_validation_history_text(user_id: int) -> str:
    rows = list_validation_history(int(user_id), limit=10)
    lines = ["История финансовой сертификации", ""]
    if not rows:
        lines.append("Проверок пока нет.")
        return "\n".join(lines)
    for row in rows:
        lines.append(f"{row.get('period_from')}-{row.get('period_to')}")
        lines.append(f"Parity Score: {float(row.get('parity_score') or 0):.1f}%")
        lines.append(f"Status: {row.get('status')}")
        lines.append("")
    return "\n".join(lines).strip()


async def validate_command(update, context):
    bot = get_bot()
    if not await bot.access(update, "report"):
        return
    user_id = bot.uid(update)
    if getattr(bot, "_is_engineering_role", None) and bot._is_engineering_role(user_id):
        mode = str((context.args or ["report"])[0]).strip().lower() if getattr(context, "args", None) else "report"
        if mode == "history":
            await update.message.reply_text(_build_validation_history_text(user_id))
            return
        if mode == "details":
            latest = get_latest_validation_result(user_id)
            text = (latest or {}).get("report_text") or "Детализированный отчёт пока не сохранён."
            await update.message.reply_text(text)
            return
    await update.message.reply_text(automatic_validation_message())
