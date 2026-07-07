from __future__ import annotations

from .models import FinancialMode, ValidationResult


ROOT_CAUSE_TEXT = {
    "rounding_difference": "Небольшая разница округления.",
    "field_unavailable": "Нужное поле пока недоступно в weekly источниках.",
    "missing_sales_rows": "За выбранный период не хватает строк продаж/возвратов.",
    "missing_finance_raw_rows": "В weekly-периоде нет строк finance_raw_audit.",
    "wrong_reason_mapping": "Нужно уточнить mapping WB reason/category.",
    "period_mismatch": "Период начисления WB не совпадает с management-моделью.",
    "model_mismatch_management_vs_wb_weekly": (
        "Официальный недельный отчёт WB и управленческий P&L используют разные модели дат и начислений. "
        "Для проверки WB используйте режим WB Weekly Parity."
    ),
}


def _money(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f} ₽".replace(",", " ")


def _int_text(value) -> str:
    if value is None:
        return "-"
    try:
        return str(int(value))
    except Exception:
        return str(value)


def _mode_label(mode: str) -> str:
    if str(mode or "").strip().lower() == FinancialMode.WB_WEEKLY_PARITY:
        return "Сверка с официальным отчётом WB"
    return "Управленческий P&L"


def _root_cause_text(code: str | None) -> str | None:
    if not code:
        return None
    return ROOT_CAUSE_TEXT.get(code, code)


def build_validation_report_text(result: ValidationResult) -> str:
    lines = [
        "Финансовая сертификация WB",
        "",
        f"Режим: {_mode_label(result.mode)}",
        f"Период: {result.period_from.strftime('%d.%m.%Y')} - {result.period_to.strftime('%d.%m.%Y')}",
        f"Parity Score: {result.parity_score:.1f}%",
        f"Status: {result.status}",
        "",
        "WB Parity",
        "Сравнение идёт между официальным weekly report WB и WB-aligned weekly snapshot.",
        "",
    ]
    for metric in result.metrics:
        lines.append(f"{metric.metric}:")
        if isinstance(metric.wb_value, int) and not isinstance(metric.wb_value, bool):
            lines.append(f"WB: {_int_text(metric.wb_value)}")
            lines.append(f"Snapshot: {_int_text(metric.vooglii_value)}")
            lines.append(f"Δ: {_int_text(metric.delta) if metric.delta is not None else '-'}")
        else:
            lines.append(f"WB: {_money(metric.wb_value)}")
            lines.append(f"Snapshot: {_money(metric.vooglii_value)}")
            lines.append(f"Δ: {_money(metric.delta) if metric.delta is not None else '-'}")
        lines.append(f"Status: {metric.status}")
        root_cause_text = _root_cause_text(metric.root_cause)
        if root_cause_text:
            lines.append(f"Причина: {root_cause_text}")
        lines.append("")

    management = dict(result.management_context or {})
    lines.extend(
        [
            "Management Context",
            "Этот блок справочный и не влияет на parity score.",
            f"Management revenue: {_money(management.get('sales_revenue'))}",
            f"Management payout: {_money(management.get('wb_payout'))}",
            f"Management net profit: {_money(management.get('net_profit'))}",
            f"Finance confidence: {management.get('finance_confidence') or '-'}",
            "",
        ]
    )
    if result.failed_metrics:
        lines.append("Failed metrics:")
        for metric in result.failed_metrics:
            lines.append(f"- {metric}")
        lines.append("")
    if result.warnings:
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines).strip()
