"""Quick readonly routing checks for product-mode navigation."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

TEST_USER_ID = 658486226


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _run_handler(handler, command_text, args):
    outputs = []
    replies = []
    original_send_long = telegram_bot.send_long
    original_access = telegram_bot.access
    original_user_has_access = telegram_bot.user_has_access

    class _Message:
        def __init__(self, text):
            self.text = text

        async def reply_text(self, text, **kwargs):
            replies.append(str(text))

    class _User:
        id = TEST_USER_ID
        username = "readonly_user"

    class _Update:
        def __init__(self, text):
            self.message = _Message(text)
            self.effective_user = _User()

    class _Context:
        def __init__(self, args):
            self.args = list(args)
            self.application = None

    async def _fake_send_long(update, text):
        outputs.append(str(text))

    async def _fake_access(update, permission):
        return True

    async def _invoke():
        telegram_bot.send_long = _fake_send_long
        telegram_bot.access = _fake_access
        telegram_bot.user_has_access = lambda user_id, permission=None: True
        try:
            await handler(_Update(command_text), _Context(args))
        finally:
            telegram_bot.send_long = original_send_long
            telegram_bot.access = original_access
            telegram_bot.user_has_access = original_user_has_access

    telegram_bot.asyncio.run(_invoke())
    return outputs, replies


def run_all():
    help_outputs, help_replies = _run_handler(telegram_bot.menu_command, "/help", [])
    _assert(not help_outputs, "help should use reply_text")
    _assert(len(help_replies) == 1, "help should render one reply")
    help_text = help_replies[0]
    _assert("/help developer" in help_text, "help should contain /help developer")
    _assert("общая сводка бизнеса" in help_text, "help should explain /home")
    _assert("состояние бизнеса и рекомендации" in help_text, "help should explain /business")
    _assert("прибыль, деньги и выплаты" in help_text, "help should explain /finance")
    _assert("/udl" not in help_text, "help should not expose /udl")
    _assert("/command audit" not in help_text, "help should not expose /command audit")

    developer_outputs, developer_replies = _run_handler(telegram_bot.menu_command, "/help developer", ["developer"])
    _assert(not developer_outputs, "help developer should use reply_text")
    _assert(len(developer_replies) == 1, "help developer should render one reply")
    developer_text = developer_replies[0]
    _assert("/ui spec" in developer_text, "help developer should contain /ui spec")
    _assert("/dashboard prototype" in developer_text, "help developer should contain /dashboard prototype")
    _assert("/telegram identity" in developer_text, "help developer should contain /telegram identity")
    _assert("/udl" in developer_text, "help developer should contain /udl")
    _assert("/command audit" in developer_text, "help developer should contain /command audit")

    route_cases = [
        (telegram_bot.ui_command, "/ui spec", ["spec"], "VOOGLII UI SPECIFICATION v1.0"),
        (telegram_bot.telegram_command, "/telegram identity", ["identity"], "TELEGRAM IDENTITY"),
        (telegram_bot.business_command, "/business", [], "Общий статус"),
        (telegram_bot.business_command, "/business metrics current_month", ["metrics", "current_month"], "BUSINESS METRICS"),
        (telegram_bot.finance_command, "/finance", [], "Технически"),
        (telegram_bot.finance_command, "/finance api status", ["api", "status"], "FINANCE API STATUS"),
        (telegram_bot.products_command, "/products", [], "Справочник себестоимости"),
        (telegram_bot.analytics_command, "/analytics", [], "Основные отчёты готовы"),
        (telegram_bot.system_command, "/system", [], "VOOGLII SYSTEM"),
        (telegram_bot.system_command, "/system audit", ["audit"], "SYSTEM"),
    ]
    for handler, command_text, args, marker in route_cases:
        outputs, replies = _run_handler(handler, command_text, args)
        _assert(not replies, f"{command_text} should not fall back to reply_text help")
        _assert(len(outputs) == 1, f"{command_text} should produce exactly one output")
        _assert(marker in outputs[0], f"{command_text} should contain {marker}")
    system_outputs, _ = _run_handler(telegram_bot.system_command, "/system", [])
    _assert("SEE_RC_STATUS" not in system_outputs[0], "/system should not contain SEE_RC_STATUS")
    _assert("SEE_PERFORMANCE" not in system_outputs[0], "/system should not contain SEE_PERFORMANCE")


if __name__ == "__main__":
    run_all()
    print("PRODUCT NAVIGATION QUICK OK", flush=True)
