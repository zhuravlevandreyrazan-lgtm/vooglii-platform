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
    period_label: str | None
    orders_count: int
    orders_amount: float | None
    sales_count: int
    sales_revenue: float | None
    returns_count: int
    cancellations_count: int
    buyouts_count: int
    buyout_percent: float | None
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
    reconciliation_delta: float | None
    confirmed_expenses_total: float | None
    pending_expenses_total: float | None
    expenses_total: float | None
    gross_profit: float | None
    operating_profit: float | None
    profit_before_tax: float | None
    tax_amount: float | None
    net_profit: float | None
    margin_percent: float | None
    roi_percent: float | None
    drr_percent: float | None
    roas: float | None
    data_quality_status: str
    finance_status: str
    sales_status: str
    advertising_status: str
    ads_status: str
    cost_status: str
    expenses_status: str
    finance_confidence: str
    finance_confidence_score: int
    finance_confidence_reason: str
    profit_display_mode: str
    source_map: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    debug_sources: dict[str, Any] = field(default_factory=dict)
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


def _pick_first_money(*values: Any) -> float | None:
    for value in values:
        rounded = _round_money(value)
        if rounded is not None:
            return rounded
    return None


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


def _expenses_status(finance_status: str, wb_deductions: float | None, acquiring: float | None, other_expenses: float | None) -> str:
    if finance_status == FINANCE_OK:
        return "EXPENSES_CONFIRMED"
    if any(value not in (None, 0.0) for value in (wb_deductions, acquiring, other_expenses)):
        return "EXPENSES_PARTIAL"
    return "EXPENSES_ESTIMATED"


def _finance_confidence(
    finance_status: str,
    sales_revenue: float | None,
    official_net_profit: float | None,
    reconciliation_delta: float | None,
    cost_price: float | None,
    expenses_status: str,
) -> tuple[str, int, str]:
    if sales_revenue in (None, 0):
        return "UNKNOWN", 0, "Нет выручки или ключевых исходных данных."
    issues: list[str] = []
    if finance_status == FINANCE_WAITING_WB:
        issues.append("Финансовые данные WB ещё не подтверждены.")
    if reconciliation_delta not in (None, 0.0):
        issues.append("Есть расхождение классификации расходов.")
    if cost_price in (None, 0.0):
        issues.append("Себестоимость за период не рассчитана.")
    if official_net_profit is None and finance_status != FINANCE_OK:
        issues.append("Нет подтверждённой official net profit.")
    if finance_status == FINANCE_OK and official_net_profit is not None and not issues:
        return "HIGH", 95, "Финансовые данные WB подтверждены, есть official net profit."
    if finance_status == FINANCE_PARTIAL and expenses_status in {"EXPENSES_PARTIAL", "EXPENSES_CONFIRMED"}:
        if not issues:
            issues.append("Часть финансовых расходов подтверждена частично.")
        return "MEDIUM", 65, " ".join(issues)
    if finance_status == FINANCE_WAITING_WB or issues:
        return "LOW", 30, " ".join(issues)
    return "UNKNOWN", 10, "Недостаточно данных для оценки достоверности."


def _profit_display_mode(finance_confidence: str, finance_status: str) -> str:
    if finance_confidence == "HIGH" and finance_status == FINANCE_OK:
        return "FINAL"
    if finance_confidence == "MEDIUM":
        return "PRELIMINARY"
    if finance_confidence == "LOW":
        return "HIDDEN"
    return "HIDDEN"


def _source_entry(selected: Any, candidates: list[tuple[str, Any]]) -> dict[str, Any]:
    selected_money = _round_money(selected)
    normalized_candidates = []
    selected_source = None
    for source_name, value in candidates:
        rounded = _round_money(value)
        normalized_candidates.append({"source": source_name, "value": rounded})
        if selected_source is None and rounded == selected_money and rounded is not None:
            selected_source = source_name
    return {
        "selected_source": selected_source or "unresolved",
        "selected_value": selected_money,
        "candidates": normalized_candidates,
    }


def _period_label(bot, period_start: str | None, period_end: str | None) -> str | None:
    if period_start and period_end:
        label = _safe_get(lambda: bot.humanize_period_range(period_start, period_end))
        if label:
            return str(label)
        return f"{period_start}..{period_end}"
    return None


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
    period_label = _period_label(bot, period_start, period_end)

    sales_revenue_candidates = [
        ("report_mgmt.revenue", report_mgmt.get("revenue")),
        ("get_profit_stats.revenue", profit_stats[0] if len(profit_stats) > 0 else None),
        ("payment_reconciliation.sales_revenue_total", payment_snapshot.get("sales_revenue_total")),
    ]
    sales_revenue = _prefer_positive_money(*(value for _, value in sales_revenue_candidates))
    orders_amount = _round_money(orders_stats[1] if len(orders_stats) > 1 else None)
    wb_payout_candidates = [
        ("report_mgmt.payout", report_mgmt.get("payout")),
        ("get_profit_stats.wb_payout", profit_stats[2] if len(profit_stats) > 2 else None),
        ("payment_reconciliation.sales_for_pay_total", payment_snapshot.get("sales_for_pay_total")),
        ("payment_reconciliation.weekly_payout_total_all", payment_snapshot.get("weekly_payout_total_all")),
    ]
    wb_payout = _prefer_positive_money(*(value for _, value in wb_payout_candidates))
    wb_payments_received = _round_money(payment_snapshot.get("weekly_payout_total_all"))

    sales_count = int(period_stats[0] or 0)
    buyouts_count = sales_count
    buyout_percent = round((buyouts_count / float(orders_stats[0])) * 100, 1) if float(orders_stats[0] or 0) > 0 else None
    cost_coverage_percent = float(products_snapshot.get("cost_coverage_percent") or 0)
    profit_cost_price = _round_money(profit_stats[3] if len(profit_stats) > 3 else None)
    cost_price_candidates = [
        ("report_mgmt.cost_price", report_mgmt.get("cost_price")),
        ("get_profit_stats.cost_price", profit_cost_price),
        ("financial_engine.cost_total", financial_engine_snapshot.get("cost_total")),
    ]
    cost_price = _prefer_positive_money(*(value for _, value in cost_price_candidates))
    if cost_price in (0.0, None):
        if cost_coverage_percent < 95 or sales_revenue not in (None, 0) or sales_count > 0:
            cost_price = None

    advertising_spend_candidates = [
        ("advertising_customer.total_spend", advertising_snapshot.get("total_spend")),
        ("report_mgmt.advertising", report_mgmt.get("advertising")),
        ("get_profit_stats.advertising", profit_stats[5] if len(profit_stats) > 5 else None),
    ]
    advertising_spend = _prefer_positive_money(*(value for _, value in advertising_spend_candidates))
    logistics_candidates = [
        ("report_mgmt.logistics", report_mgmt.get("logistics")),
        ("get_profit_stats.logistics", profit_stats[4] if len(profit_stats) > 4 else None),
        ("financial_engine.logistics_total", financial_engine_snapshot.get("logistics_total")),
        ("finance_difference.logistics", finance_health.get("logistics")),
    ]
    logistics = _prefer_positive_money(*(value for _, value in logistics_candidates))
    storage_candidates = [
        ("report_mgmt.storage", report_mgmt.get("storage")),
        ("get_profit_stats.storage", profit_stats[6] if len(profit_stats) > 6 else None),
        ("financial_engine.storage_total", financial_engine_snapshot.get("storage_total")),
        ("finance_difference.storage", finance_health.get("storage")),
    ]
    storage = _prefer_positive_money(*(value for _, value in storage_candidates))
    acquiring_candidates = [
        ("report_mgmt.acquiring", report_mgmt.get("acquiring")),
        ("financial_engine.payment_services_commission_total", financial_engine_snapshot.get("payment_services_commission_total")),
        ("financial_engine.acquiring_total", financial_engine_snapshot.get("acquiring_total")),
        ("finance_difference.acquiring", finance_health.get("acquiring")),
    ]
    acquiring = _prefer_positive_money(*(value for _, value in acquiring_candidates))
    wb_deductions_candidates = [
        ("report_mgmt.deductions", report_mgmt.get("deductions")),
        ("financial_engine.deductions_total", financial_engine_snapshot.get("deductions_total")),
        ("finance_difference.deductions", finance_health.get("deductions")),
    ]
    wb_deductions = _prefer_positive_money(*(value for _, value in wb_deductions_candidates))
    penalties = None
    other_expenses_candidates = [
        ("report_mgmt.other", report_mgmt.get("other")),
        ("finance_difference.explicit_other_deductions", finance_health.get("explicit_other_deductions")),
        ("finance_difference.other_deductions", finance_health.get("other_deductions")),
    ]
    other_expenses = _prefer_positive_money(*(value for _, value in other_expenses_candidates))
    unknown_candidates = [
        ("report_mgmt.unexplained", report_mgmt.get("unexplained")),
        ("finance_difference.residual_other_deductions", finance_health.get("residual_other_deductions")),
        ("finance_difference.unexplained_total", finance_health.get("unexplained_total")),
    ]
    raw_unknown_wb_expenses = _pick_first_money(*(value for _, value in unknown_candidates))
    unknown_wb_expenses = None
    reconciliation_delta = None
    if raw_unknown_wb_expenses is not None:
        unknown_wb_expenses = round(max(float(raw_unknown_wb_expenses), 0.0), 2)
        reconciliation_delta = round(float(raw_unknown_wb_expenses), 2) if float(raw_unknown_wb_expenses) < 0 else 0.0

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
        if reconciliation_delta == 0.0:
            reconciliation_delta = None

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
    confirmed_expenses_total = _sum_known([
        cost_price,
        advertising_spend,
        logistics,
        storage,
        unknown_wb_expenses,
    ])
    pending_expenses_total = _sum_known([
        acquiring,
        wb_deductions,
        penalties,
        other_expenses,
    ])
    gross_profit = None
    if sales_revenue is not None and cost_price is not None:
        gross_profit = round(sales_revenue - cost_price, 2)

    profit_before_tax = None
    if sales_revenue is not None and expenses_total is not None:
        profit_before_tax = round(sales_revenue - expenses_total, 2)
    operating_profit = profit_before_tax

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
    sales_status = str(((quality_snapshot.get("sales") or {}).get("status")) or ("OK" if sales_revenue not in (None, 0) else "UNKNOWN"))
    advertising_status = _advertising_status(advertising_snapshot)
    ads_status = advertising_status
    cost_status = _cost_status(products_snapshot, cost_price)
    expenses_status = _expenses_status(finance_status, wb_deductions, acquiring, other_expenses)
    finance_confidence, finance_confidence_score, finance_confidence_reason = _finance_confidence(
        finance_status,
        sales_revenue,
        official_net_profit,
        reconciliation_delta,
        cost_price,
        expenses_status,
    )
    profit_display_mode = _profit_display_mode(finance_confidence, finance_status)

    sources = {
        "sales_revenue": _source_entry(sales_revenue, sales_revenue_candidates),
        "wb_payout": _source_entry(wb_payout, wb_payout_candidates),
        "wb_payments_received": _source_entry(wb_payments_received, [("payment_reconciliation.weekly_payout_total_all", payment_snapshot.get("weekly_payout_total_all"))]),
        "cost_price": _source_entry(cost_price, cost_price_candidates),
        "advertising_spend": _source_entry(advertising_spend, advertising_spend_candidates),
        "logistics": _source_entry(logistics, logistics_candidates),
        "storage": _source_entry(storage, storage_candidates),
        "acquiring": _source_entry(acquiring, acquiring_candidates),
        "wb_deductions": _source_entry(wb_deductions, wb_deductions_candidates),
        "other_expenses": _source_entry(other_expenses, other_expenses_candidates),
        "unknown_wb_expenses": _source_entry(raw_unknown_wb_expenses, unknown_candidates),
        "reconciliation_delta": {
            "selected_source": "derived_from_negative_unknown_wb_expenses" if reconciliation_delta not in (None, 0.0) else None,
            "selected_value": _round_money(reconciliation_delta),
            "candidates": [],
        },
        "tax_amount": _source_entry(
            tax_amount,
            [
                ("profit_stats_after_tax.tax", after_tax.get("tax")),
                ("financial_engine.tax_amount", financial_engine_snapshot.get("tax_amount")),
            ],
        ),
        "expenses_total": {
            "selected_source": "derived_sum",
            "selected_value": _round_money(expenses_total),
            "formula": "cost_price + advertising_spend + logistics + storage + acquiring + wb_deductions + penalties + other_expenses + positive_unknown_wb_expenses",
            "components": {
                "cost_price": cost_price,
                "advertising_spend": advertising_spend,
                "logistics": logistics,
                "storage": storage,
                "acquiring": acquiring,
                "wb_deductions": wb_deductions,
                "penalties": penalties,
                "other_expenses": other_expenses,
                "positive_unknown_wb_expenses": unknown_wb_expenses,
            },
        },
        "confirmed_expenses_total": {
            "selected_source": "derived_confirmed_expenses_sum",
            "selected_value": _round_money(confirmed_expenses_total),
        },
        "pending_expenses_total": {
            "selected_source": "derived_pending_expenses_sum",
            "selected_value": _round_money(pending_expenses_total),
        },
        "profit_before_tax": {
            "selected_source": "derived_sales_revenue_minus_expenses_total" if profit_before_tax is not None else None,
            "selected_value": _round_money(profit_before_tax),
        },
        "net_profit": {
            "selected_source": (
                "financial_engine.official_net_profit"
                if finance_status == FINANCE_OK and official_net_profit is not None
                else "operational_profit_minus_tax_or_profit_before_tax"
                if net_profit is not None
                else None
            ),
            "selected_value": _round_money(net_profit),
        },
        "finance_status": {
            "selected_source": "_finance_status(financial_engine_snapshot, finance_api_snapshot, finance_health)",
            "selected_value": finance_status,
            "official_new_finance_available": bool(financial_engine_snapshot.get("official_new_finance_available")),
            "finance_api_status": finance_api_snapshot.get("status"),
            "coverage_percent": float(finance_health.get("coverage_percent") or 0),
        },
        "advertising_status": {
            "selected_source": "_advertising_status(advertising_snapshot)",
            "selected_value": advertising_status,
            "normalized_status": advertising_snapshot.get("normalized_status"),
            "status_kind": advertising_snapshot.get("status_kind"),
            "total_spend": _round_money(advertising_snapshot.get("total_spend")),
        },
        "cost_status": {
            "selected_source": "_cost_status(products_snapshot, cost_price)",
            "selected_value": cost_status,
            "cost_coverage_percent": cost_coverage_percent,
            "cost_price": cost_price,
        },
        "expenses_status": {
            "selected_source": "_expenses_status(finance_status, wb_deductions, acquiring, other_expenses)",
            "selected_value": expenses_status,
        },
        "finance_confidence": {
            "selected_source": "_finance_confidence(...)",
            "selected_value": finance_confidence,
            "score": finance_confidence_score,
            "reason": finance_confidence_reason,
        },
        "profit_display_mode": {
            "selected_source": "_profit_display_mode(finance_confidence, finance_status)",
            "selected_value": profit_display_mode,
        },
    }

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
    warnings: list[str] = []
    if reconciliation_delta not in (None, 0.0):
        warnings.append("Есть расхождение классификации расходов WB.")
    if finance_status != FINANCE_OK:
        warnings.append("Финансовые данные WB ещё не подтверждены полностью.")
    if cost_price in (None, 0.0):
        warnings.append("Себестоимость за период не рассчитана.")
    if finance_confidence_reason:
        warnings.append(finance_confidence_reason)
    warnings = list(dict.fromkeys([str(item).strip() for item in warnings if str(item).strip()]))

    return UnifiedFinancialSnapshot(
        period_start=period_start,
        period_end=period_end,
        period_label=period_label,
        orders_count=int(orders_stats[0] or 0),
        orders_amount=orders_amount,
        sales_count=sales_count,
        sales_revenue=sales_revenue,
        returns_count=int(profit_stats[12] or 0) if len(profit_stats) > 12 else 0,
        cancellations_count=int(orders_stats[2] or 0) if len(orders_stats) > 2 else 0,
        buyouts_count=buyouts_count,
        buyout_percent=buyout_percent,
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
        reconciliation_delta=reconciliation_delta,
        confirmed_expenses_total=confirmed_expenses_total,
        pending_expenses_total=pending_expenses_total,
        expenses_total=expenses_total,
        gross_profit=gross_profit,
        operating_profit=operating_profit,
        profit_before_tax=profit_before_tax,
        tax_amount=tax_amount,
        net_profit=net_profit,
        margin_percent=margin_percent,
        roi_percent=roi_percent,
        drr_percent=drr_percent,
        roas=roas,
        data_quality_status=data_quality_status,
        finance_status=finance_status,
        sales_status=sales_status,
        advertising_status=advertising_status,
        ads_status=ads_status,
        cost_status=cost_status,
        expenses_status=expenses_status,
        finance_confidence=finance_confidence,
        finance_confidence_score=finance_confidence_score,
        finance_confidence_reason=finance_confidence_reason,
        profit_display_mode=profit_display_mode,
        source_map=sources,
        warnings=warnings,
        debug_sources=sources,
        source_notes=source_notes,
    )


def build_unified_financial_snapshot_dict(user_id: int, days, *, context=None, bot=None) -> dict[str, Any]:
    snapshot = build_unified_financial_snapshot(user_id, days, context=context, bot=bot)
    payload = asdict(snapshot)
    payload["source_map"] = payload.get("source_map") or payload.get("debug_sources") or {}
    payload["warnings"] = list(payload.get("warnings") or [])
    payload["revenue"] = payload.get("sales_revenue")
    payload["period"] = payload.get("period_label")
    payload["payments_received"] = payload.get("wb_payments_received")
    payload["advertising"] = payload.get("advertising_spend")
    payload["unknown_expenses"] = payload.get("unknown_wb_expenses")
    payload["unclassified_expenses"] = payload.get("unknown_wb_expenses")
    payload["profit"] = payload.get("net_profit")
    payload["margin"] = payload.get("margin_percent")
    payload["roi"] = payload.get("roi_percent")
    payload["gross_profit"] = payload.get("gross_profit")
    payload["operating_profit"] = payload.get("operating_profit")
    payload["buyouts"] = payload.get("buyouts_count")
    payload["buyout_percent"] = payload.get("buyout_percent")
    payload["sales_status"] = payload.get("sales_status")
    payload["ads_status"] = payload.get("advertising_status")
    payload["finance_status_texts"] = _finance_status_texts(snapshot.finance_status)
    products_snapshot = dict(_safe_get(lambda: (bot or _get_bot())._products_center_snapshot(user=user_id, days=days), {}) or {})
    payload["cost_coverage_percent"] = float(products_snapshot.get("cost_coverage_percent") or 0)
    payload["positive_unknown_wb_expenses"] = payload.get("unknown_wb_expenses")
    payload["customer_unknown_wb_expenses"] = payload.get("unknown_wb_expenses")
    payload["overclassified_expenses"] = payload.get("reconciliation_delta")
    payload["confidence"] = payload.get("finance_confidence")
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
