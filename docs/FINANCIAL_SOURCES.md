# Financial Sources

## Single Source Of Truth

Customer-facing financial screens must use `vooglii_finance/unified_snapshot.py`.

Primary entry points:

- `build_unified_financial_snapshot(user_id, days, ...)`
- `build_unified_financial_snapshot_dict(user_id, days, ...)`

No renderer may calculate profit, expenses, margin, ROI, DRR, or ROAS independently.

## RC4 Contract

The unified snapshot must provide:

- `period_start`, `period_end`, `period_label`
- `orders_count`, `orders_amount`, `sales_count`, `sales_revenue`, `returns_count`, `buyouts_count`, `buyout_percent`
- `wb_payout`, `wb_payments_received`
- `cost_price`, `advertising_spend`, `logistics`, `storage`, `acquiring`, `wb_deductions`, `penalties`, `other_expenses`, `unknown_wb_expenses`, `reconciliation_delta`
- `confirmed_expenses_total`, `pending_expenses_total`, `expenses_total`
- `gross_profit`, `operating_profit`, `profit_before_tax`, `tax_amount`, `net_profit`
- `margin_percent`, `roi_percent`, `drr_percent`, `roas`
- `finance_status`, `finance_confidence`, `finance_confidence_score`, `finance_confidence_reason`, `profit_display_mode`
- `sales_status`, `ads_status`, `cost_status`, `expenses_status`, `data_quality_status`
- `source_map`, `warnings`

## Source Priority

- `sales_revenue` -> `_report_mgmt_snapshot().revenue` -> `get_profit_stats(...)[0]` -> `_payment_reconciliation_snapshot().sales_revenue_total`
- `orders_count`, `orders_amount`, `cancellations_count` -> `get_orders_stats(...)`
- `sales_count` -> `get_period_stats(...)`
- `returns_count` -> `get_profit_stats(...)[12]`
- `buyouts_count` -> `sales_count`
- `buyout_percent` -> `buyouts_count / orders_count`
- `wb_payout` -> `_report_mgmt_snapshot().payout` -> `get_profit_stats(...)[2]` -> payment reconciliation totals
- `wb_payments_received` -> `_payment_reconciliation_snapshot().weekly_payout_total_all`
- `cost_price` -> `_report_mgmt_snapshot().cost_price` -> `get_profit_stats(...)[3]` -> `_financial_engine_snapshot().cost_total`
- `advertising_spend` -> `_advertising_customer_snapshot().total_spend` -> `_report_mgmt_snapshot().advertising` -> `get_profit_stats(...)[5]`
- `logistics` -> management snapshot -> profit stats -> financial engine -> finance difference
- `storage` -> management snapshot -> profit stats -> financial engine -> finance difference
- `acquiring` -> management snapshot -> financial engine -> finance difference
- `wb_deductions` -> management snapshot -> financial engine -> finance difference
- `other_expenses` -> management snapshot -> finance difference
- `unknown_wb_expenses` -> positive residual only
- `reconciliation_delta` -> negative residual only
- `tax_amount` -> `get_profit_stats_after_tax(...)` -> `_financial_engine_snapshot().tax_amount`

## Core Formulas

- `gross_profit = sales_revenue - cost_price`
- `expenses_total = cost_price + advertising_spend + logistics + storage + acquiring + wb_deductions + penalties + other_expenses + positive_unknown_wb_expenses`
- `confirmed_expenses_total` includes only confirmed/operationally safe components
- `pending_expenses_total` includes WB-side components still awaiting confirmation
- `reconciliation_delta` is not added into `expenses_total`
- `operating_profit = sales_revenue - expenses_total`
- `profit_before_tax = operating_profit`
- `net_profit` uses official WB net profit only when `finance_status == FINANCE_OK`

## Confidence Rules

- `HIGH` -> final profit, margin, and ROI may be shown
- `MEDIUM` -> only preliminary operating estimate may be shown
- `LOW` or `UNKNOWN` -> final profit, margin, and ROI must be hidden

Profit display modes:

- `FINAL`
- `PRELIMINARY`
- `HIDDEN`

## False Zero Policy

If a field is not confirmed, customer screens must not invent `0.00 ₽`.

Use business-safe states such as:

- `данные обновляются`
- `не рассчитано`
- `нет данных`
- `будет рассчитана после подтверждения финансов WB`

## Explainability

`source_map` must explain every key field with:

- selected source
- selected value
- candidate sources or formula components

`warnings` must expose confidence, reconciliation, or cost-matching caveats without mutating totals.
