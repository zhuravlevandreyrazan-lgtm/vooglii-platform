# TELEGRAM BOT COMMANDS

## Customer Commands

- `/start` - launch VOOGLII Terminal
- `/menu` - main navigation
- `/home` - main business summary
- `/business` - business status
- `/finance` - money, profit, payouts
- `/products` - products, SKU, stock risks
- `/analytics` - reports and dashboards
- `/advisor` - VOOGLII Advisor V2
- `/system` - customer-safe platform health
- `/profile` - profile and subscription
- `/account` - alias to customer profile
- `/connect` - connect WB cabinet
- `/disconnect` - disconnect WB token
- `/update` - refresh data
- `/stocks` - stock screen
- `/forecast` - replenishment forecast

## Developer/Admin Commands

- `/system audit`
- `/performance`
- `/product readiness`
- `/structure readiness`
- `/command audit`
- `/migration readiness`

## Access Model

- Customer commands appear in `/menu` and customer help.
- Developer/admin diagnostics must stay hidden from customer roles.
- `/help developer` is developer/admin only.
- `/system` must stay customer-safe unless the user explicitly has developer access.

## VOOGLII Terminal v1.0 RC Notes

- `/start` must begin with `🏢 VOOGLII Terminal`.
- `/advisor` opens V2 by default.
- Customer outputs must not expose internal period tokens like `current_month`, `last_7_days`, `last_30_days`.
