from datetime import date

from app.utils.dates import parse_relative_date, today


def test_today_and_yesterday() -> None:
    reference = date(2026, 8, 27)
    assert parse_relative_date("today", now=reference) == reference
    assert parse_relative_date("yesterday", now=reference) == date(2026, 8, 26)


def test_last_friday() -> None:
    # 27 Aug 2026 is a Thursday; last Friday is 21 Aug 2026.
    assert parse_relative_date("last Friday", now=date(2026, 8, 27)) == date(2026, 8, 21)


def test_iso_date() -> None:
    assert parse_relative_date("2026-08-26") == date(2026, 8, 26)


def test_day_month() -> None:
    assert parse_relative_date("26 Aug", now=date(2026, 8, 27)) == date(2026, 8, 26)


def test_invalid_date() -> None:
    assert parse_relative_date("next quarter") is None
    assert parse_relative_date("2026-13-40") is None


def test_today_helper_uses_provided_datetime() -> None:
    from datetime import datetime

    assert today(now=datetime(2026, 8, 27, 9, 0, 0)) == date(2026, 8, 27)
