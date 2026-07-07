from __future__ import annotations


def automatic_validation_message() -> str:
    return "Финансовая проверка выполняется автоматически.\nОткройте /finance или /report."


def wb_data_status_text(period_status: str, validation_status: str | None = None) -> str:
    normalized_period = str(period_status or "").upper()
    normalized_validation = str(validation_status or "").upper()
    if normalized_validation in {"FAIL", "WARN"}:
        return "Данные WB: 🔴 есть расхождения"
    if normalized_period == "CLOSED":
        return "Данные WB: 🟢 период закрыт"
    if normalized_period == "PARTIAL":
        return "Данные WB: 🟡 часть финансов ещё обновляется"
    return "Данные WB: 🟡 данные обновляются"
