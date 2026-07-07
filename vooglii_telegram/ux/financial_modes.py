from __future__ import annotations

from vooglii_validation.validator import get_latest_validation_result


class FinancialMode:
    MANAGEMENT_PNL = "management_pnl"
    WB_WEEKLY_PARITY = "wb_weekly_parity"


def financial_mode_label(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    mapping = {
        FinancialMode.MANAGEMENT_PNL: "Управленческий P&L",
        FinancialMode.WB_WEEKLY_PARITY: "Сверка с официальным отчётом WB",
        "wb_weekly_parity": "Сверка с официальным отчётом WB",
        "wb_weekly_parity".upper(): "Сверка с официальным отчётом WB",
        "management_pnl".upper(): "Управленческий P&L",
    }
    return mapping.get(normalized, "Управленческий P&L")


def financial_mode_hint(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized == FinancialMode.WB_WEEKLY_PARITY:
        return "Это контроль качества данных, а не управленческий P&L."
    return (
        "Этот отчёт показывает операционную картину бизнеса. "
        "Для сверки с официальным недельным отчётом WB используйте /finance validate."
    )


def validation_summary_text(user_id: int, *, compact: bool = False) -> str:
    latest = get_latest_validation_result(int(user_id))
    if not latest:
        if compact:
            return "Сверка WB: ещё не выполнялась"
        return (
            "Сверка с WB:\n"
            "ещё не выполнялась.\n"
            "Для проверки загрузите недельный отчёт WB и запустите /finance validate."
        )

    period_from = str(latest.get("period_from") or "-")
    period_to = str(latest.get("period_to") or "-")
    status = str(latest.get("status") or "UNKNOWN")
    parity = float(latest.get("parity_score") or 0.0)
    if compact:
        return f"Сверка WB: {status} {parity:.1f}%"
    return (
        "Сверка с WB:\n"
        f"Последняя неделя: {period_from} - {period_to}\n"
        f"Статус: {status}\n"
        f"Совпадение: {parity:.1f}%\n"
        "Детали: /finance validate"
    )


def finance_validate_summary_text(user_id: int) -> str:
    latest = get_latest_validation_result(int(user_id))
    title = "Сверка с официальным отчётом WB"
    mode_block = f"Режим:\n{financial_mode_label(FinancialMode.WB_WEEKLY_PARITY)}"
    if not latest:
        return (
            f"{title} ещё не выполнялась.\n\n"
            "Загрузите официальный недельный отчёт WB и выполните проверку через CLI или /validate report."
        )
    failed_metrics = list(latest.get("failed_metrics") or [])
    metric_lines = []
    if failed_metrics:
        for metric_name in failed_metrics[:6]:
            metric_lines.append(f"{metric_name}: FAIL")
    else:
        metric_lines.extend(
            [
                "Выручка WB: PASS",
                "К перечислению WB: PASS",
                "Логистика: PASS",
                "Хранение: PASS",
                "Эквайринг: PASS",
                "Удержания: PASS",
            ]
        )
    return (
        f"{title}\n\n"
        f"{mode_block}\n\n"
        "Последняя проверка:\n"
        f"{latest.get('period_from')} - {latest.get('period_to')}\n\n"
        "Parity Score:\n"
        f"{float(latest.get('parity_score') or 0):.1f}%\n\n"
        "Статус:\n"
        f"{latest.get('status')}\n\n"
        "Показатели:\n"
        + "\n".join(metric_lines)
        + "\n\nВажно:\n"
        "Этот режим сверяет VOOGLII с официальным недельным отчётом WB.\n"
        "Он не заменяет управленческий P&L."
    )
