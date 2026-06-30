"""Shared pure formatting helpers for VOOGLII.

This module intentionally contains only safe, side-effect-free helpers that
format values or safely normalize simple display inputs.
"""

__all__ = [
    "money",
    "format_seconds",
    "_ads_percent_text",
    "_ads_number_text",
]


def money(v):
    return f"{float(v or 0):,.2f}".replace(",", " ") + " ₽"


def format_seconds(seconds):
    try:
        seconds = max(0, int(float(seconds or 0)))
    except Exception:
        return "неизвестно"
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days} дн {hours} ч"
    if hours:
        return f"{hours} ч {minutes} мин"
    if minutes:
        return f"{minutes} мин"
    return f"{sec} сек"


def _ads_percent_text(value):
    if value is None:
        return "n/a"
    return f"{float(value):.1f}%"


def _ads_number_text(value, digits=2):
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"
