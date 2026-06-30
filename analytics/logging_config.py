from __future__ import annotations

import logging
import os
from typing import Any


SENSITIVE_MARKERS = [
    "token",
    "authorization",
    "secret",
    "cookie",
]


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.getMessage())
        lowered = message.lower()
        if any(marker in lowered for marker in SENSITIVE_MARKERS):
            record.msg = "[redacted sensitive log payload]"
            record.args = ()
        return True


def configure_logging() -> None:
    level_name = str(os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        has_filter = any(isinstance(existing, SensitiveDataFilter) for existing in handler.filters)
        if not has_filter:
            handler.addFilter(SensitiveDataFilter())


def get_logger(category: str) -> logging.Logger:
    return logging.getLogger(f"vooglii.{category}")


def safe_log_extra(**kwargs: Any) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in kwargs.items():
        lowered = key.lower()
        sanitized[key] = "[redacted]" if any(marker in lowered for marker in SENSITIVE_MARKERS) else value
    return sanitized
