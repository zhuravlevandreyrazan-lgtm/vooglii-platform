from __future__ import annotations


FINANCE_OK = "🟢 Финансовые данные WB подтверждены"
FINANCE_PARTIAL = "🟡 Финансовые данные WB подтверждены частично"
FINANCE_WAITING = "🟡 Финансовые данные WB ожидают подтверждения"
FINANCE_UNAVAILABLE = "🔴 Финансовые данные WB временно недоступны"

ADS_OK = "🟢 Рекламные данные актуальны"
ADS_PARTIAL = "🟡 Рекламные данные обновлены частично"
ADS_WAITING = "🟡 Рекламные данные обновляются"

SALES_OK = "🟢 Продажи актуальны"
SALES_WAITING = "🟡 Продажи ожидают обновления"

COST_READY_PENDING_CALC = "🟢 Себестоимость заполнена, расчёт по продажам ожидает обновления"
COST_READY = "🟢 Себестоимость заполнена"
COST_MISSING = "🟡 Себестоимость требует заполнения"


def finance_status_label(status: str) -> str:
    value = str(status or "").strip().upper()
    if value == "FINANCE_OK":
        return FINANCE_OK
    if value == "FINANCE_PARTIAL":
        return FINANCE_PARTIAL
    if value == "FINANCE_UNAVAILABLE":
        return FINANCE_UNAVAILABLE
    return FINANCE_WAITING


def ads_status_label(status: str) -> str:
    value = str(status or "").strip().upper()
    if value in {"ADS_OK", "OK", "HIGH", "SUCCESS", "AVAILABLE"}:
        return ADS_OK
    if value in {"ADS_PARTIAL", "ADS_COOLDOWN", "PARTIAL", "MEDIUM", "LIMITED"}:
        return ADS_PARTIAL
    return ADS_WAITING


def sales_status_label(status: str) -> str:
    value = str(status or "").strip().upper()
    if value in {"GOOD", "OK", "HIGH", "SUCCESS", "AVAILABLE", "READY"}:
        return SALES_OK
    return SALES_WAITING


def cost_status_label(status: str, *, coverage_percent: float | None = None, has_period_cost: bool = False) -> str:
    value = str(status or "").strip().upper()
    coverage = float(coverage_percent or 0)
    if has_period_cost:
        return COST_READY
    if value == "COST_OK" or coverage >= 95:
        return COST_READY_PENDING_CALC
    return COST_MISSING
