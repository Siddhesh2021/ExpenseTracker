import calendar
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_MONTHS = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): index for index, name in enumerate(calendar.month_abbr) if name})

_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DAY_MONTH_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3,9})$")


def today(timezone_name: str = "Asia/Kolkata", now: datetime | None = None) -> date:
    if now is not None:
        return now.date()
    return datetime.now(ZoneInfo(timezone_name)).date()


def parse_relative_date(
    text: str,
    timezone_name: str = "Asia/Kolkata",
    *,
    now: date | None = None,
) -> date | None:
    cleaned = " ".join(text.strip().lower().split())
    if not cleaned:
        return None

    iso = _ISO_RE.match(cleaned)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None

    reference = now or today(timezone_name)

    if cleaned == "today":
        return reference
    if cleaned == "yesterday":
        return reference - timedelta(days=1)
    if cleaned == "tomorrow":
        return reference + timedelta(days=1)

    day_month = _DAY_MONTH_RE.match(text.strip())
    if day_month:
        month = _MONTHS.get(day_month.group(2).lower())
        if month is None:
            return None
        try:
            return date(reference.year, month, int(day_month.group(1)))
        except ValueError:
            return None

    last_weekday = re.match(r"^last\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$", cleaned)
    if last_weekday:
        target = _WEEKDAYS[last_weekday.group(1)]
        delta = (reference.weekday() - target) % 7
        if delta == 0:
            delta = 7
        return reference - timedelta(days=delta)

    return None
