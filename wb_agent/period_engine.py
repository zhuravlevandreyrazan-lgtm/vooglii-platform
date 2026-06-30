from datetime import date, datetime, timedelta
import calendar


PERIOD_ENGINE_ALLOWED_TYPES = ("DAY", "WEEK", "MONTH", "RANGE", "ALL", "UNKNOWN")
PERIOD_ENGINE_ALLOWED_PRESETS = (
    "today",
    "yesterday",
    "current_month",
    "previous_month",
    "last_7_days",
    "last_30_days",
    "all",
)


def _coerce_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    return datetime.strptime(text, "%Y-%m-%d").date()


def _date_text(value):
    return value.strftime("%Y-%m-%d") if isinstance(value, date) else None


def _month_start(value):
    return value.replace(day=1)


def _month_end(value):
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _shift_year_safe(value, years=-1):
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def _iso_week_text(value):
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _is_full_calendar_month(start_dt, end_dt):
    return bool(
        start_dt
        and end_dt
        and start_dt.day == 1
        and end_dt == _month_end(start_dt)
        and start_dt.year == end_dt.year
        and start_dt.month == end_dt.month
    )


def _is_calendar_week(start_dt, end_dt):
    return bool(
        start_dt
        and end_dt
        and (end_dt - start_dt).days == 6
        and start_dt.weekday() == 0
        and end_dt.weekday() == 6
    )


def _build_weeks(start_dt, end_dt):
    if not start_dt or not end_dt:
        return []
    weeks = []
    cursor = start_dt
    while cursor <= end_dt:
        week_end = min(cursor + timedelta(days=(6 - cursor.weekday())), end_dt)
        weeks.append({
            "start_date": _date_text(cursor),
            "end_date": _date_text(week_end),
            "iso_week": _iso_week_text(cursor),
        })
        cursor = week_end + timedelta(days=1)
    return weeks


def _display_name(period_type, start_dt, end_dt, preset=None):
    if period_type == "ALL":
        return "All time"
    if not start_dt or not end_dt:
        return str(preset or "Unknown")
    if period_type == "DAY":
        return _date_text(start_dt)
    if period_type == "MONTH":
        return start_dt.strftime("%Y-%m")
    return f"{_date_text(start_dt)}..{_date_text(end_dt)}"


def _previous_period(period_type, start_dt, end_dt):
    if not start_dt or not end_dt or period_type == "ALL":
        return None
    if period_type == "DAY":
        prev_day = start_dt - timedelta(days=1)
        return {"start_date": _date_text(prev_day), "end_date": _date_text(prev_day)}
    if period_type == "MONTH":
        prev_month_end = start_dt - timedelta(days=1)
        prev_month_start = _month_start(prev_month_end)
        return {"start_date": _date_text(prev_month_start), "end_date": _date_text(_month_end(prev_month_end))}
    span_days = (end_dt - start_dt).days + 1
    prev_end = start_dt - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span_days - 1)
    return {"start_date": _date_text(prev_start), "end_date": _date_text(prev_end)}


def _same_period_last_year(start_dt, end_dt):
    if not start_dt or not end_dt:
        return None
    return {
        "start_date": _date_text(_shift_year_safe(start_dt, years=-1)),
        "end_date": _date_text(_shift_year_safe(end_dt, years=-1)),
    }


def _resolve_dates(start_dt, end_dt, preset, today_dt):
    normalized_preset = str(preset or "").strip().lower() or None
    if start_dt or end_dt:
        return start_dt, end_dt, normalized_preset
    if normalized_preset is None:
        normalized_preset = "current_month"
    if normalized_preset == "today":
        return today_dt, today_dt, normalized_preset
    if normalized_preset == "yesterday":
        yesterday = today_dt - timedelta(days=1)
        return yesterday, yesterday, normalized_preset
    if normalized_preset == "current_month":
        return _month_start(today_dt), today_dt, normalized_preset
    if normalized_preset == "previous_month":
        prev_month_anchor = _month_start(today_dt) - timedelta(days=1)
        return _month_start(prev_month_anchor), _month_end(prev_month_anchor), normalized_preset
    if normalized_preset == "last_7_days":
        return today_dt - timedelta(days=6), today_dt, normalized_preset
    if normalized_preset == "last_30_days":
        return today_dt - timedelta(days=29), today_dt, normalized_preset
    if normalized_preset == "all":
        return None, None, normalized_preset
    raise ValueError("INVALID_PERIOD_PRESET")


def build_period_snapshot(start_date=None, end_date=None, preset=None, today=None):
    warnings = []
    today_dt = _coerce_date(today) or datetime.now().date()
    start_dt = _coerce_date(start_date)
    end_dt = _coerce_date(end_date)

    if (start_dt is None) ^ (end_dt is None):
        raise ValueError("INVALID_PERIOD_RANGE")
    start_dt, end_dt, normalized_preset = _resolve_dates(start_dt, end_dt, preset, today_dt)

    if normalized_preset == "all":
        return {
            "start_date": None,
            "end_date": None,
            "days_count": None,
            "display_name": "All time",
            "period_type": "ALL",
            "is_full_month": False,
            "is_current_month": False,
            "is_closed_period": False,
            "month_key": None,
            "previous_period": None,
            "same_period_last_year": None,
            "weeks": [],
            "warnings": warnings,
        }

    if start_dt is None or end_dt is None or start_dt > end_dt:
        raise ValueError("INVALID_PERIOD_RANGE")

    days_count = (end_dt - start_dt).days + 1
    if start_dt == end_dt:
        period_type = "DAY"
    elif _is_full_calendar_month(start_dt, end_dt):
        period_type = "MONTH"
    elif _is_calendar_week(start_dt, end_dt):
        period_type = "WEEK"
    else:
        period_type = "RANGE"

    is_full_month = _is_full_calendar_month(start_dt, end_dt)
    is_current_month = (
        start_dt.year == today_dt.year
        and start_dt.month == today_dt.month
        and end_dt.year == today_dt.year
        and end_dt.month == today_dt.month
    )
    is_closed_period = end_dt < today_dt
    month_key = start_dt.strftime("%Y-%m") if start_dt.year == end_dt.year and start_dt.month == end_dt.month else None

    if end_dt > today_dt:
        warnings.append("Period includes a future date.")
    if start_dt > today_dt:
        warnings.append("Period starts in the future.")

    return {
        "start_date": _date_text(start_dt),
        "end_date": _date_text(end_dt),
        "days_count": days_count,
        "display_name": _display_name(period_type, start_dt, end_dt, preset=normalized_preset),
        "period_type": period_type,
        "is_full_month": is_full_month,
        "is_current_month": is_current_month,
        "is_closed_period": is_closed_period,
        "month_key": month_key,
        "previous_period": _previous_period(period_type, start_dt, end_dt),
        "same_period_last_year": _same_period_last_year(start_dt, end_dt),
        "weeks": _build_weeks(start_dt, end_dt),
        "warnings": warnings,
    }


def period_engine_text(snapshot):
    snapshot = dict(snapshot or {})
    previous_period = snapshot.get("previous_period") or {}
    same_period_last_year = snapshot.get("same_period_last_year") or {}
    weeks = list(snapshot.get("weeks") or [])
    warnings = list(snapshot.get("warnings") or [])

    lines = [
        "PERIOD ENGINE",
        "",
        f'Period: {snapshot.get("display_name") or "Unknown"}',
        f'Type: {snapshot.get("period_type") or "UNKNOWN"}',
        f'Days: {snapshot.get("days_count") if snapshot.get("days_count") is not None else "all"}',
        f'Closed: {"yes" if snapshot.get("is_closed_period") else "no"}',
        f'Full month: {"yes" if snapshot.get("is_full_month") else "no"}',
        f'Current month: {"yes" if snapshot.get("is_current_month") else "no"}',
        f'Previous period: {previous_period.get("start_date") or "-"}..{previous_period.get("end_date") or "-"}',
        f'Same period last year: {same_period_last_year.get("start_date") or "-"}..{same_period_last_year.get("end_date") or "-"}',
        "Weeks:",
    ]
    if weeks:
        for item in weeks:
            lines.append(f'{item.get("start_date")}..{item.get("end_date")} ({item.get("iso_week")})')
    else:
        lines.append("none")
    lines.extend(["", "Warnings:"])
    if warnings:
        lines.extend(str(item) for item in warnings)
    else:
        lines.append("none")
    return "\n".join(lines)
