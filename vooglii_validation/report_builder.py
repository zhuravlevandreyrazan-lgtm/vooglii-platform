from __future__ import annotations

from .models import ValidationResult


def _money(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f} ₽".replace(",", " ")


def _int_text(value) -> str:
    return "-" if value is None else str(int(value))


def build_validation_report_text(result: ValidationResult) -> str:
    lines = [
        "Финансовая сертификация WB",
        "",
        "Период:",
        f"{result.period_from.strftime('%d.%m.%Y')} — {result.period_to.strftime('%d.%m.%Y')}",
        "",
        "Parity Score:",
        f"{result.parity_score:.1f}%",
        "",
    ]
    for metric in result.metrics:
        lines.append(f"{metric.metric}:")
        if isinstance(metric.wb_value, int) and not isinstance(metric.wb_value, bool):
            lines.append(f"WB: {_int_text(metric.wb_value)}")
            lines.append(f"VOOGLII: {_int_text(metric.vooglii_value)}")
            lines.append(f"Δ: {_int_text(metric.delta)}" if metric.delta is not None else "Δ: -")
        else:
            lines.append(f"WB: {_money(metric.wb_value)}")
            lines.append(f"VOOGLII: {_money(metric.vooglii_value)}")
            lines.append(f"Δ: {_money(metric.delta)}" if metric.delta is not None else "Δ: -")
        lines.append(metric.status)
        if metric.root_cause:
            lines.append(f"Причина: {metric.root_cause}")
        lines.append("")
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
