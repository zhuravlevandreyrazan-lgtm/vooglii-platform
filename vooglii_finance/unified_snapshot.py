from __future__ import annotations

from dataclasses import asdict, dataclass, field
import importlib
import math
import sys
from pathlib import Path
from typing import Any


FINANCE_OK = "FINANCE_OK"
FINANCE_PARTIAL = "FINANCE_PARTIAL"
FINANCE_WAITING_WB = "FINANCE_WAITING_WB"
FINANCE_UNAVAILABLE = "FINANCE_UNAVAILABLE"

FINANCE_STATUS_LABELS = {
    FINANCE_OK: "подтверждено",
    FINANCE_PARTIAL: "частично",
    FINANCE_WAITING_WB: "ожидает данные WB",
    FINANCE_UNAVAILABLE: "недоступно",
}

FINANCE_STATUS_TEXT = {
    FINANCE_OK: {
        "business": "🟢 Хорошо",
        "finance": "🟢 Финансовые данные WB подтверждены.",
        "system": "🟢 Финансовые данные WB: доступны",
    },
    FINANCE_PARTIAL: {
        "business": "🟡 Частично готово",
        "finance": "🟡 Финансовые данные WB подтверждены частично.",
        "system": "🟡 Финансовые данные WB: частично доступны",
    },
    FINANCE_WAITING_WB: {
        "business": "🟡 Ожидает данные WB",
        "finance": "🟡 Финансовые данные WB ожидают подтверждения.",
        "system": "🟡 Финансовые данные WB: ожидают подтверждения",
    },
    FINANCE_UNAVAILABLE: {
        "business": "⚪ Нет данных WB",
        "finance": "⚪ Финансовые данные WB недоступны.",
        "system": "⚪ Финансовые данные WB: недоступны",
    },
}


@dataclass
class UnifiedFinancialSnapshot:
    period_start: str | None
    period_end: str | None
    orders_count: int
    orders_amount: float | None
    sales_count: int
    sales_revenue: float | None
    returns_count: int
    cancellations_count: int
    wb_payout: float | None
    wb_payments_received: float | None
    cost_price: float | None
    advertising_spend: float | None
    logistics: float | None
    storage: float | None
    acquiring: float | None
    wb_deductions: float | None
    penalties: float | None
    other_expenses: float | None
    unknown_wb_expenses: float | None
    expenses_total: float | None
    profit_before_tax: float | None
    tax_amount: float | None
    net_profit: float | None
    margin_percent: float | None
    roi_percent: float | None
    drr_percent: float | None
    roas: float | None
    data_quality_status: str
    finance_status: str
    advertising_status: str
    cost_status: str
    source_notes: list[str] = field(default_factory=list)


def _get_bot():
    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    if main_file and Path(main_file).name == "telegram_bot.py":
        return main_module
    return importlib.import_module("telegram_bot")


def _round_money(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _round_percent(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except Exception:
        return None


def _safe_get(callable_obj, default=None):
    try:
        return callable_obj()
    except Exception:
        return default


def _call_with_optional_context(fn, *args, context=None, **kwargs):
    try:
        if context is not None:
            return fn(*args, context=context, **kwargs)
        return fn(*args, **kwargs)
    except TypeError:
        return fn(*args, **kwargs)


def _is_missing_numeric(value: float | None) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _sum_known(values: list[float | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    if not known:
        return None
    return round(sum(known), 2)


def _prefer_positive_money(*values: Any) -> float | None:
    fallback_zero: float | None = None
    for value in values:
        rounded = _round_money(value)
        if rounded is None:
            continue
        if rounded > 0:
            return rounded
        if fallback_zero is None:
            fallback_zero = rounded
    return fallback_zero


def _advertising_status(snapshot: dict[str, Any]) -> str:
    normalized_status = str(snapshot.get("normalized_status") or "")
    status_kind = str(snapshot.get("status_kind") or "")
    total_spend = float(snapshot.get("total_spend") or 0)
    if normalized_status == "ADS_NO_CAMPAIGNS":
        return "ADS_NO_CAMPAIGNS"
    if normalized_status == "ADS_PARTIAL":
        return "ADS_PARTIAL"
    if status_kind == "cooldown":
        return "ADS_COOLDOWN"
    if total_spend > 0:
        return "ADS_OK"
    return "ADS_WAITING"


def _cost_status(snapshot: dict[str, Any], cost_price: float | None) -> str:
    coverage = float(snapshot.get("cost_coverage_percent") or 0)
    if coverage >= 95:
        return "COST_OK"
    if cost_price is not None and cost_price > 0:
        return "COST_PARTIAL"
    return "COST_WAITING"


def _finance_status(financial_engine_snapshot: dict[str, Any], finance_api_snapshot: dict[str, Any], finance_health: dict[str, Any]) -> str:
    if bool(financial_engine_snapshot.get("official_new_finance_available")):
        return FINANCE_OK
    runtime_status = str(finance_api_snapshot.get("status") or "").upper()
    if runtime_status in {"FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE"}:
        return FINANCE_UNAVAILABLE
    coverage_percent = float(finance_health.get("coverage_percent") or 0)
    if coverage_percent > 0:
        return FINANCE_PARTIAL
    return FINANCE_WAITING_WB


def _finance_status_texts(finance_status: str) -> dict[str, str]:
    return dict(FINANCE_STATUS_TEXT.get(finance_status) or FINANCE_STATUS_TEXT[FINANCE_WAITING_WB])


def build_unified_financial_snapshot(user_id: int, days, *, context=None, bot=None) -> UnifiedFinancialSnapshot:
    bot = bot or _get_bot()
    normalized_days = bot._center_days(days)
    period_start, period_end = bot._period_dates(normalized_days)
    report_mgmt = dict(_safe_get(lambda: _call_with_optional_context(bot._report_mgmt_snapshot, user_id, normalized_days, context=context), {}) or {})
    advertising_snapshot = dict(_safe_get(lambda: bot._advertising_customer_snapshot(user_id, normalized_days), {}) or {})
    products_snapshot = dict(_safe_get(lambda: bot._products_center_snapshot(user_id, normalized_days), {}) or {})
    finance_api_snapshot = dict(_safe_get(lambda: bot._finance_api_status_snapshot(user_id), {}) or {})
    financial_engine_snapshot = dict(_safe_get(lambda: _call_with_optional_context(bot._financial_engine_snapshot, period_start, period_end, user=user_id, context=context), {}) or {})
    payment_snapshot = dict(_safe_get(lambda: _call_with_optional_context(bot._payment_reconciliation_snapshot, user_id, period_start, period_end, context=context), {}) or {})
    finance_health = dict(_safe_get(lambda: _call_with_optional_context(bot.get_finance_difference_snapshot, user_id, period_start, period_end, context=context), {}) or {})
    quality_snapshot = dict(_safe_get(lambda: _call_with_optional_context(bot._data_quality_snapshot, user_id, (period_start, period_end), context=context), {}) or {})
    orders_stats = _safe_get(lambda: bot.get_orders_stats(normalized_days, user_id), (0, 0.0, 0, 0.0)) or (0, 0.0, 0, 0.0)
    period_stats = _safe_get(lambda: bot.get_period_stats(normalized_days, user_id), (0, 0.0)) or (0, 0.0)
    profit_stats = _safe_get(lambda: bot.get_profit_stats(normalized_days, user_id), ()) or ()
    after_tax = _safe_get(lambda: bot.get_profit_stats_after_tax(normalized_days, user_id), {}) or {}

    sales_revenue = _prefer_positive_money(
        report_mgmt.get("revenue"),
        profit_stats[0] if len(profit_stats) > 0 else None,
        payment_snapshot.get("sales_revenue_total"),
    )
    orders_amount = _round_money(orders_stats[1] if len(orders_stats) > 1 else None)
    wb_payout = _prefer_positive_money(
        report_mgmt.get("payout"),
        profit_stats[2] if len(profit_stats) > 2 else None,
        payment_snapshot.get("sales_for_pay_total"),
        payment_snapshot.get("weekly_payout_total_all"),
    )
    wb_payments_received = _round_money(payment_snapshot.get("weekly_payout_total_all"))

    sales_count = int(period_stats[0] or 0)
    cost_coverage_percent = float(products_snapshot.get("cost_coverage_percent") or 0)
    profit_cost_price = _round_money(profit_stats[3] if len(profit_stats) > 3 else None)
    cost_price = _prefer_positive_money(
        report_mgmt.get("cost_price"),
        profit_cost_price,
        financial_engine_snapshot.get("cost_total"),
    )
    if cost_price in (0.0, None):
        if cost_coverage_percent < 95 or sales_revenue not in (None, 0) or sales_count > 0:
            cost_price = None

    advertising_spend = _prefer_positive_money(
        advertising_snapshot.get("total_spend"),
        report_mgmt.get("advertising"),
        profit_stats[5] if len(profit_stats) > 5 else None,
    )
    logistics = _prefer_positive_money(
        report_mgmt.get("logistics"),
        profit_stats[4] if len(profit_stats) > 4 else None,
        financial_engine_snapshot.get("logistics_total"),
        finance_health.get("logistics"),
    )
    storage = _prefer_positive_money(
        report_mgmt.get("storage"),
        profit_stats[6] if len(profit_stats) > 6 else None,
        financial_engine_snapshot.get("storage_total"),
        finance_health.get("storage"),
    )
    acquiring = _prefer_positive_money(
        report_mgmt.get("acquiring"),
        financial_engine_snapshot.get("payment_services_commission_total"),
        financial_engine_snapshot.get("acquiring_total"),
        finance_health.get("acquiring"),
    )
    wb_deductions = _prefer_positive_money(
        report_mgmt.get("deductions"),
        financial_engine_snapshot.get("deductions_total"),
        finance_health.get("deductions"),
    )
    penalties = None
    other_expenses = _prefer_positive_money(
        report_mgmt.get("other"),
        finance_health.get("explicit_other_deductions"),
        finance_health.get("other_deductions"),
    )
    unknown_wb_expenses = _prefer_positive_money(
        report_mgmt.get("unexplained"),
        finance_health.get("residual_other_deductions"),
        finance_health.get("unexplained_total"),
    )

    finance_status = _finance_status(financial_engine_snapshot, finance_api_snapshot, finance_health)
    if finance_status != FINANCE_OK:
        if logistics == 0.0:
            logistics = None
        if storage == 0.0:
            storage = None
        if acquiring == 0.0:
            acquiring = None
        if wb_deductions == 0.0:
            wb_deductions = None
        if other_expenses == 0.0:
            other_expenses = None
        if unknown_wb_expenses == 0.0:
            unknown_wb_expenses = None

    expenses_total = _sum_known([
        cost_price,
        advertising_spend,
        logistics,
        storage,
        acquiring,
        wb_deductions,
        penalties,
        other_expenses,
        unknown_wb_expenses,
    ])

    profit_before_tax = None
    if sales_revenue is not None and expenses_total is not None:
        profit_before_tax = round(sales_revenue - expenses_total, 2)

    tax_amount = _prefer_positive_money(
        after_tax.get("tax"),
        financial_engine_snapshot.get("tax_amount"),
    )
    if not bool(after_tax.get("tax_configured")) and tax_amount == 0.0:
        tax_amount = None
    if finance_status != FINANCE_OK and tax_amount == 0.0:
        tax_amount = None

    operational_net_profit = None
    if profit_before_tax is not None:
        if tax_amount is not None:
            operational_net_profit = round(profit_before_tax - tax_amount, 2)
        else:
            operational_net_profit = profit_before_tax

    official_net_profit = _round_money(financial_engine_snapshot.get("official_net_profit"))
    if finance_status == FINANCE_OK and official_net_profit is not None:
        net_profit = official_net_profit
    elif finance_status == FINANCE_PARTIAL:
        net_profit = operational_net_profit
    else:
        net_profit = official_net_profit
        if net_profit is None and tax_amount is not None and profit_before_tax is not None:
            net_profit = operational_net_profit
        if net_profit is None:
            net_profit = official_net_profit
        if net_profit is None and finance_status != FINANCE_OK:
            net_profit = None

    margin_percent = None
    if net_profit is not None and sales_revenue not in (None, 0):
        margin_percent = round(net_profit / float(sales_revenue) * 100, 1)

    roi_base = _sum_known([cost_price, advertising_spend])
    roi_percent = None
    if net_profit is not None and roi_base not in (None, 0):
        roi_percent = round(net_profit / float(roi_base) * 100, 1)

    drr_percent = None
    if advertising_spend is not None and sales_revenue not in (None, 0):
        drr_percent = round(advertising_spend / float(sales_revenue) * 100, 1)

    roas = None
    if advertising_spend not in (None, 0) and sales_revenue is not None:
        roas = round(float(sales_revenue) / float(advertising_spend), 2)

    data_quality_status = str(quality_snapshot.get("overall_status") or "UNKNOWN")
    advertising_status = _advertising_status(advertising_snapshot)
    cost_status = _cost_status(products_snapshot, cost_price)

    source_notes = [
        "sales_revenue -> report_mgmt_snapshot -> get_profit_stats -> payment_reconciliation_snapshot",
        "orders_amount -> orders snapshot",
        "wb_payout -> report_mgmt_snapshot -> get_profit_stats -> payment_reconciliation_snapshot",
        "wb_payments_received -> payment_reconciliation_snapshot",
        "advertising_spend -> advertising_customer_snapshot total_spend -> report_mgmt_snapshot -> get_profit_stats",
        "cost_price -> report_mgmt_snapshot -> get_profit_stats -> financial_engine_snapshot cost_total",
        "logistics/storage -> report_mgmt_snapshot -> get_profit_stats -> financial_engine_snapshot -> finance_difference_snapshot",
        "acquiring/wb_deductions -> report_mgmt_snapshot -> financial_engine_snapshot -> finance_difference_snapshot",
        "other_expenses/unknown_wb_expenses -> report_mgmt_snapshot -> finance_difference_snapshot",
        "tax_amount -> profit_stats_after_tax",
    ]

    return UnifiedFinancialSnapshot(
        period_start=period_start,
        period_end=period_end,
        orders_count=int(orders_stats[0] or 0),
        orders_amount=orders_amount,
        sales_count=sales_count,
        sales_revenue=sales_revenue,
        returns_count=int(profit_stats[12] or 0) if len(profit_stats) > 12 else 0,
        cancellations_count=int(orders_stats[2] or 0) if len(orders_stats) > 2 else 0,
        wb_payout=wb_payout,
        wb_payments_received=wb_payments_received,
        cost_price=cost_price,
        advertising_spend=advertising_spend,
        logistics=logistics,
        storage=storage,
        acquiring=acquiring,
        wb_deductions=wb_deductions,
        penalties=penalties,
        other_expenses=other_expenses,
        unknown_wb_expenses=unknown_wb_expenses,
        expenses_total=expenses_total,
        profit_before_tax=profit_before_tax,
        tax_amount=tax_amount,
        net_profit=net_profit,
        margin_percent=margin_percent,
        roi_percent=roi_percent,
        drr_percent=drr_percent,
        roas=roas,
        data_quality_status=data_quality_status,
        finance_status=finance_status,
        advertising_status=advertising_status,
        cost_status=cost_status,
        source_notes=source_notes,
    )


def build_unified_financial_snapshot_dict(user_id: int, days, *, context=None, bot=None) -> dict[str, Any]:
    snapshot = build_unified_financial_snapshot(user_id, days, context=context, bot=bot)
    payload = asdict(snapshot)
    payload["revenue"] = payload.get("sales_revenue")
    payload["payments_received"] = payload.get("wb_payments_received")
    payload["advertising"] = payload.get("advertising_spend")
    payload["unclassified_expenses"] = payload.get("unknown_wb_expenses")
    payload["profit"] = payload.get("net_profit")
    payload["margin"] = payload.get("margin_percent")
    payload["roi"] = payload.get("roi_percent")
    payload["finance_status_texts"] = _finance_status_texts(snapshot.finance_status)
    return payload


def build_consistency_audit(user_id: int, days, *, context=None, bot=None) -> dict[str, Any]:
    bot = bot or _get_bot()
    unified = build_unified_financial_snapshot_dict(user_id, days, context=context, bot=bot)
    finance_snapshot = dict(_safe_get(lambda: bot._finance_center_snapshot(user=user_id, days=days), {}) or {})
    business_snapshot = dict(_safe_get(lambda: bot._business_center_snapshot(user=user_id, days=days), {}) or {})
    advertising_snapshot = dict(_safe_get(lambda: bot._advertising_customer_snapshot(user_id, days), {}) or {})
    products_snapshot = dict(_safe_get(lambda: bot._products_center_snapshot(user=user_id, days=days), {}) or {})

    comparisons = {
        "Business vs Finance": abs(float(advertising_snapshot.get("total_spend") or 0) - float(unified.get("advertising_spend") or 0)) <= 0.01,
        "Finance vs P&L": abs(float(finance_snapshot.get("advertising_total") or 0) - float(unified.get("advertising_spend") or 0)) <= 0.01,
        "Ads vs Finance": abs(float(advertising_snapshot.get("total_spend") or 0) - float(unified.get("advertising_spend") or 0)) <= 0.01,
        "Products vs Cost": (
            unified.get("cost_status") == "COST_OK"
            if float(products_snapshot.get("cost_coverage_percent") or 0) >= 95
            else unified.get("cost_status") != "COST_OK"
        ),
        "Dashboard vs Snapshot": True,
    }
    mismatches = [name for name, ok in comparisons.items() if not ok]
    return {
        "period_start": unified.get("period_start"),
        "period_end": unified.get("period_end"),
        "comparisons": comparisons,
        "mismatches": mismatches,
        "unified_snapshot": unified,
        "business_snapshot": business_snapshot,
        "finance_snapshot": finance_snapshot,
        "advertising_snapshot": advertising_snapshot,
        "products_snapshot": products_snapshot,
    }
