"""Readonly checks for the VOOGLII UI specification and dashboard prototype."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wb_agent.ui_spec import (
    build_dashboard_prototype_snapshot,
    build_ui_spec_snapshot,
    dashboard_prototype_text,
    ui_spec_text,
)


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    ui_snapshot = build_ui_spec_snapshot()
    _assert(isinstance(ui_snapshot, dict), "build_ui_spec_snapshot should return dict")
    _assert(str(ui_snapshot.get("status") or "") == "READY", "ui spec status should be READY")
    _assert(str(ui_snapshot.get("product") or "") == "VOOGLII", "ui spec product should be VOOGLII")
    workspaces = list(ui_snapshot.get("workspaces") or [])
    for name in ("Dashboard", "Business", "Finance", "Products", "Advertising", "Analytics", "AI", "System"):
        _assert(name in workspaces, f"ui spec workspaces missing {name}")

    ui_text = ui_spec_text(ui_snapshot)
    _assert("VOOGLII UI SPECIFICATION v1.0" in ui_text, "ui spec text title mismatch")
    _assert("Что происходит?" in ui_text, "ui spec text should contain first core question")
    _assert("Что делать дальше?" in ui_text, "ui spec text should contain third core question")

    dashboard_snapshot = build_dashboard_prototype_snapshot()
    _assert(isinstance(dashboard_snapshot, dict), "build_dashboard_prototype_snapshot should return dict")
    _assert(str(dashboard_snapshot.get("screen") or "") == "dashboard_prototype", "dashboard prototype screen mismatch")
    _assert(str(dashboard_snapshot.get("product") or "") == "VOOGLII", "dashboard prototype product should be VOOGLII")

    dashboard_text = dashboard_prototype_text(dashboard_snapshot)
    _assert("VOOGLII DASHBOARD PROTOTYPE" in dashboard_text, "dashboard prototype title mismatch")
    _assert("Workspace" in dashboard_text, "dashboard prototype should contain Workspace block")
    _assert("Это прототип будущего интерфейса" in dashboard_text, "dashboard prototype should explain prototype status")


if __name__ == "__main__":
    main()
    print("PRODUCT UI SPEC OK", flush=True)
