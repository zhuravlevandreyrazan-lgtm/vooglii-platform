from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from security.logging import sanitize_log_value


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    cases = [
        "Authorization=Bearer abcdefghijklmnopqrstuvwxyz",
        "BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "wb_token=abcdefghijklmnopqrstuvwxyz123456",
        "cookie=sessionid=very-secret-cookie",
    ]
    for case in cases:
        sanitized = sanitize_log_value(case)
        _assert("[redacted]" in sanitized, f"expected redaction for: {case}")
        _assert("abcdefghijklmnopqrstuvwxyz123456" not in sanitized, "WB token should be hidden")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("SECURE LOGGING OK", flush=True)
