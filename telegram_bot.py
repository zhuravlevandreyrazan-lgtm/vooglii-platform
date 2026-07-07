from __future__ import annotations

from pathlib import Path

exec(
    Path(__file__).with_name("vooglii_telegram").joinpath("legacy_bot.py").read_text(encoding="utf-8-sig"),
    globals(),
)

from vooglii_telegram.handlers.admin import admin_command, apistatus_command, health_command, syncstatus_command
from vooglii_telegram.handlers.advertising import ads_command, adsaudit_command, adsupdate_command, advert_command
from vooglii_telegram.handlers.advisor import advisor_command
from vooglii_telegram.handlers.analytics import analytics_command
from vooglii_telegram.handlers.business import business_command
from vooglii_telegram.handlers.connect import connect_command, disconnect_command
from vooglii_telegram.handlers.developer import (
    control_command,
    data_command,
    migration_command,
    performance_command,
    rc_command,
    structure_command,
    telegram_command,
    ui_command,
)
from vooglii_telegram.handlers.finance import finance_command
from vooglii_telegram.handlers.legacy import adsfullstatsprobe_command
from vooglii_telegram.handlers.navigation import home_command, menu_command
from vooglii_telegram.handlers.products import products_command
from vooglii_telegram.handlers.profile import account_command, profile_command
from vooglii_telegram.handlers.profit import (
    abc_command,
    cashflow_command,
    categories_command,
    expense_command,
    losers_command,
    profit_command,
    topprofit_command,
)
from vooglii_telegram.handlers.reports import dashboard_command, report_command
from vooglii_telegram.handlers.sales import orders_command, sales_command
from vooglii_telegram.handlers.start import start_command
from vooglii_telegram.handlers.stocks import forecast_command, replenishment_command, stock_command, stocks_command
from vooglii_telegram.handlers.system import system_command
from vooglii_telegram.handlers.sync import sync_command
from vooglii_telegram.handlers.update import update_command

from vooglii_telegram.app import main
from vooglii_telegram.registry import _command_handlers


if __name__ == "__main__":
    main()
