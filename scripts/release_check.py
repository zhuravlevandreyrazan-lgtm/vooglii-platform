from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

COMMANDS = [
    [
        sys.executable,
        "-m",
        "py_compile",
        "config.py",
        "db_manager.py",
        "user_manager.py",
        "background_jobs.py",
        "telegram_bot.py",
        "vooglii_telegram/legacy_bot.py",
        "vooglii_telegram/app.py",
        "vooglii_telegram/registry.py",
        "vooglii_telegram/runtime/__init__.py",
        "vooglii_telegram/runtime/error_handler.py",
        "vooglii_telegram/runtime/heartbeat.py",
        "vooglii_telegram/runtime/jobs.py",
        "vooglii_telegram/runtime/permissions.py",
        "vooglii_telegram/runtime/logging.py",
        "vooglii_telegram/handlers/__init__.py",
        "vooglii_telegram/handlers/_bot.py",
        "vooglii_telegram/handlers/start.py",
        "vooglii_telegram/handlers/navigation.py",
        "vooglii_telegram/handlers/profile.py",
        "vooglii_telegram/handlers/business.py",
        "vooglii_telegram/handlers/finance.py",
        "vooglii_telegram/handlers/products.py",
        "vooglii_telegram/handlers/admin.py",
        "vooglii_telegram/handlers/developer.py",
        "vooglii_telegram/handlers/legacy.py",
        "vooglii_telegram/handlers/system.py",
        "vooglii_telegram/handlers/advisor.py",
        "vooglii_telegram/handlers/analytics.py",
        "vooglii_telegram/handlers/advertising.py",
        "vooglii_telegram/handlers/reports.py",
        "vooglii_telegram/handlers/sales.py",
        "vooglii_telegram/handlers/profit.py",
        "vooglii_telegram/handlers/stocks.py",
        "vooglii_telegram/handlers/connect.py",
        "vooglii_telegram/handlers/update.py",
        "vooglii_telegram/services/__init__.py",
        "vooglii_telegram/services/account_service.py",
        "vooglii_telegram/services/sync_service.py",
        "vooglii_telegram/ux/__init__.py",
        "vooglii_telegram/ux/design.py",
        "vooglii_telegram/ux/navigation.py",
        "vooglii_telegram/ux/screens.py",
        "vooglii_telegram/ux/empty_states.py",
        "vooglii_telegram/ux/paywall.py",
        "vooglii_telegram/ux/periods.py",
    ],
    [sys.executable, "tests/test_token_crypto.py"],
    [sys.executable, "tests/test_wb_token_storage.py"],
    [sys.executable, "tests/test_secure_logging.py"],
    [sys.executable, "tests/test_permissions.py"],
    [sys.executable, "tests/test_command_registry.py"],
    [sys.executable, "tests/test_connect_flow.py"],
    [sys.executable, "tests/test_disconnect_flow.py"],
    [sys.executable, "tests/test_sqlite_settings.py"],
    [sys.executable, "tests/test_telegram_healthcheck.py"],
    [sys.executable, "tests/test_update_sync_service.py"],
    [sys.executable, "tests/test_telegram_customer_ux_v2.py"],
    [sys.executable, "tests/test_telegram_rc_final_polish.py"],
    [sys.executable, "tests/test_telegram_start_runtime_smoke.py"],
    [sys.executable, "tests/test_telegram_runtime_handler_audit.py"],
    [sys.executable, "tests/test_advertising_loader.py"],
    [sys.executable, "tests/test_ads_health.py"],
    [sys.executable, "tests/test_ads_sku_linking.py"],
    [sys.executable, "tests/test_advertising_customer_text.py"],
    [sys.executable, "tests/test_advertising_customer_ux_v2.py"],
    [sys.executable, "tests/test_advertising_business_finance_integration.py"],
    [sys.executable, "tests/test_adsaudit_customer_vs_debug.py"],
    [sys.executable, "tests/test_error_handler.py"],
]


def main() -> int:
    for command in COMMANDS:
        print(f"RUN {' '.join(command)}", flush=True)
        completed = subprocess.run(command, cwd=PROJECT_ROOT)
        if completed.returncode != 0:
            print(f"FAILED {' '.join(command)}", flush=True)
            return completed.returncode
    print("RELEASE CHECK OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
