from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PY_COMPILE_FILES = [
    "config.py",
    "db_manager.py",
    "user_manager.py",
    "background_jobs.py",
    "telegram_bot.py",
    "product_catalog.py",
    "product_manager.py",
    "report.py",
    "vooglii_telegram/legacy_bot.py",
    "vooglii_telegram/registry.py",
    "vooglii_telegram/commands/registry.py",
    "vooglii_telegram/services/sync_service.py",
    "vooglii_wb_sync/products_loader.py",
    "vooglii_wb_sync/rate_limiter.py",
    "vooglii_wb_sync/sync_orchestrator.py",
    "vooglii_finance/unified_snapshot.py",
    "scripts/audit_db_schema_v2.py",
    "scripts/audit_finance_sources.py",
    "scripts/audit_product_catalog.py",
    "scripts/check_wb_token_scopes.py",
    "scripts/audit_wb_data_loading.py",
    "scripts/diagnose_financial_period.py",
    "scripts/backfill_financial_period.py",
]

REQUIRED_PYTEST_TESTS = [
    "tests/test_product_catalog_v2.py",
    "tests/test_cost_matching_v2.py",
    "tests/test_product_catalog_migration.py",
    "tests/test_product_catalog_integration.py",
    "tests/test_cost_commands.py",
    "tests/test_wb_data_loading_audit.py",
    "tests/test_financial_core_integrity.py",
    "tests/test_financial_core_periods.py",
]

COMMANDS: list[tuple[str, list[str]]] = [
    (
        "py_compile",
        [sys.executable, "-m", "py_compile", *PY_COMPILE_FILES],
    ),
    (
        "command_registry",
        [sys.executable, "tests/test_command_registry.py"],
    ),
    (
        "update_sync_service",
        [sys.executable, "tests/test_update_sync_service.py"],
    ),
    (
        "db_schema_v2",
        [sys.executable, "scripts/audit_db_schema_v2.py"],
    ),
    (
        "required_pytest_suite",
        [sys.executable, "-m", "pytest", "-q", *REQUIRED_PYTEST_TESTS],
    ),
]


def _format_seconds(value: float) -> str:
    return f"{value:.2f}s"


def main() -> int:
    phase_durations: list[tuple[str, float]] = []
    total_start = time.perf_counter()
    for label, command in COMMANDS:
        print(f"RUN[{label}] {' '.join(command)}", flush=True)
        started = time.perf_counter()
        completed = subprocess.run(command, cwd=PROJECT_ROOT)
        elapsed = time.perf_counter() - started
        phase_durations.append((label, elapsed))
        print(f"DONE[{label}] {_format_seconds(elapsed)}", flush=True)
        if completed.returncode != 0:
            print(f"FAILED[{label}] {' '.join(command)}", flush=True)
            return completed.returncode
    total_elapsed = time.perf_counter() - total_start
    print("RELEASE CHECK SUMMARY", flush=True)
    for label, elapsed in phase_durations:
        print(f"- {label}: {_format_seconds(elapsed)}", flush=True)
    print(f"TOTAL {_format_seconds(total_elapsed)}", flush=True)
    print("RELEASE CHECK OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
