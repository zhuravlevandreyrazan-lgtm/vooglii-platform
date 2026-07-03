from datetime import datetime


PERIOD_LABELS = {
    "today": "Сегодня",
    "week": "Неделя",
    "month": "Месяц",
    "current_month": "Текущий месяц",
    "previous_month": "Прошлый месяц",
    "last_7_days": "7 дней",
    "last_30_days": "30 дней",
    "all": "Всё время",
}


_MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def humanize_period_key(period_key: str) -> str:
    return PERIOD_LABELS.get(str(period_key or "").strip().lower(), str(period_key or "").strip())


def humanize_period_range(start_date: str | None, end_date: str | None) -> str:
    start_text = str(start_date or "").strip()
    end_text = str(end_date or "").strip()
    if not start_text or not end_text:
        return "Текущий месяц"
    try:
        start_dt = datetime.strptime(start_text, "%Y-%m-%d")
        end_dt = datetime.strptime(end_text, "%Y-%m-%d")
        if start_dt.year == end_dt.year and start_dt.month == end_dt.month and start_dt.day == 1:
            return f"{_MONTH_NAMES.get(start_dt.month, start_dt.strftime('%B'))} {start_dt.year}"
    except Exception:
        pass
    if start_text == end_text:
        return start_text
    return f"{start_text} - {end_text}"
