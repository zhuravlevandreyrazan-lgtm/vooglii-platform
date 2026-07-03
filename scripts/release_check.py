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
    [sys.executable, "tests/test_telegram_customer_ux_v2.py"],
    [sys.executable, "tests/test_telegram_start_runtime_smoke.py"],
    [sys.executable, "tests/test_telegram_runtime_handler_audit.py"],
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
