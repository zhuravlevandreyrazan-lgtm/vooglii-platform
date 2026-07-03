from __future__ import annotations

import logging
import re
from typing import Any


_TOKEN_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?([^\s,;]+)"),
    re.compile(r"(?i)(bot_token\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(wb_token\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(token\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(cookie\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(api[-_ ]?key\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\b"),
]


def sanitize_log_value(value: Any) -> str:
    text = str(value or "")
    sanitized = text
    for pattern in _TOKEN_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1) if match.lastindex and match.lastindex > 1 else ''}[redacted]", sanitized)
    return sanitized


def sanitize_mapping(values: dict[str, Any] | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in dict(values or {}).items():
        result[key] = sanitize_log_value(value) if isinstance(value, str) else value
    return result


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize_log_value(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = sanitize_mapping(record.args)
            else:
                record.args = tuple(sanitize_log_value(arg) for arg in record.args)
        return True

