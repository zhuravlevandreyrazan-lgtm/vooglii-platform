# Financial Sources

## Unified Snapshot

Customer-facing financial screens in Telegram should read key numbers from `vooglii_finance/unified_snapshot.py`.

Primary sources:

- `sales_revenue` -> `_report_mgmt_snapshot().revenue`
- `orders_count`, `orders_amount`, `cancellations_count` -> `get_orders_stats(...)`
- `sales_count` -> `get_period_stats(...)`
- `returns_count` -> `get_profit_stats(...)[12]`
- `wb_payout` -> `_report_mgmt_snapshot().payout`
- `wb_payments_received` -> `_payment_reconciliation_snapshot().weekly_payout_total_all`
- `advertising_spend` -> `_advertising_customer_snapshot().total_spend`
- `cost_price` -> `_report_mgmt_snapshot().cost_price`
- `logistics` -> `_report_mgmt_snapshot().logistics`
- `storage` -> `_report_mgmt_snapshot().storage`
- `acquiring` -> `_report_mgmt_snapshot().acquiring`
- `wb_deductions` -> `_report_mgmt_snapshot().deductions`
- `other_expenses` -> `_report_mgmt_snapshot().other`
- `unknown_wb_expenses` -> `_report_mgmt_snapshot().unexplained`
- `tax_amount` -> `get_profit_stats_after_tax(...)`

## Profit Formula

`profit_before_tax` is calculated in one place:

`sales_revenue - cost_price - advertising_spend - logistics - storage - acquiring - wb_deductions - penalties - other_expenses - unknown_wb_expenses`

`net_profit` is:

- `profit_before_tax - tax_amount`, if tax is available
- otherwise official WB net profit, when the financial engine confirms it

## Status Rules

Finance status values:

- `FINANCE_OK`
- `FINANCE_PARTIAL`
- `FINANCE_WAITING_WB`
- `FINANCE_UNAVAILABLE`

Cost status values:

- `COST_OK`
- `COST_PARTIAL`
- `COST_WAITING`

Advertising status values:

- `ADS_OK`
- `ADS_PARTIAL`
- `ADS_COOLDOWN`
- `ADS_WAITING`
- `ADS_NO_CAMPAIGNS`

## False Zero Policy

If a value is not confirmed, customer screens should not invent `0 ₽`.

Use business-safe states instead:

- `ожидает данные WB`
- `не рассчитано`
- `нет данных`
