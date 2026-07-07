from __future__ import annotations

from vooglii_telegram.ux.financial_modes import FinancialMode, financial_mode_hint, financial_mode_label
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
    mode = str((context.args or ["report"])[0]).strip().lower() if getattr(context, "args", None) else "report"
    user_id = bot.uid(update)
    if mode == "history":
        await update.message.reply_text(_build_validation_history_text(user_id))
        return
    if mode == "details":
        latest = get_latest_validation_result(user_id)
        text = (latest or {}).get("report_text") or "Детализированный отчёт пока не сохранён."
        if latest:
            text = (
                f"Режим:\n{financial_mode_label(FinancialMode.WB_WEEKLY_PARITY)}\n"
                f"{financial_mode_hint(FinancialMode.WB_WEEKLY_PARITY)}\n\n{text}"
            )
        await update.message.reply_text(text)
        return
    await update.message.reply_text(
        "Сверка с официальным отчётом WB ещё не выполнялась.\n\n"
        "Загрузите официальный недельный отчёт WB в чат, затем запустите /validate report."
    )
