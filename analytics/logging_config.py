from __future__ import annotations

import logging
import os
from typing import Any

from security.logging import SensitiveDataFilter, sanitize_log_value


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
        sanitized[key] = sanitize_log_value(value) if isinstance(value, str) else value
    return sanitized
