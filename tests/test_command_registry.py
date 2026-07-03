from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_telegram.commands.registry import get_command_spec, get_customer_help_commands, get_customer_menu_commands


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    customer_menu = get_customer_menu_commands()
    customer_help = get_customer_help_commands()
    _assert(any(spec.name == "dashboard" for spec in customer_menu), "dashboard should be in customer menu")
    _assert(all(spec.category == "customer" for spec in customer_help), "help should expose only customer commands")
    admin_spec = get_command_spec("admin")
    _assert(admin_spec is not None and admin_spec.category == "admin", "admin command should be classified as admin")
    dev_spec = get_command_spec("telegram")
    _assert(dev_spec is not None and dev_spec.category == "developer", "telegram command should be classified as developer")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("COMMAND REGISTRY OK", flush=True)
