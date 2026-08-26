from decimal import Decimal

from app.utils.money import detect_currency, parse_amount


def test_parse_rupee_amount() -> None:
    assert parse_amount("₹450") == Decimal("450")


def test_parse_comma_amount() -> None:
    assert parse_amount("₹1,200") == Decimal("1200")


def test_parse_decimal_amount() -> None:
    assert parse_amount("450.50") == Decimal("450.50")


def test_invalid_amount() -> None:
    assert parse_amount("abc") is None
    assert parse_amount("₹0") is None


def test_detect_currency_defaults_to_inr() -> None:
    assert detect_currency("₹450 Uber") == "INR"
    assert detect_currency("$20 Uber") == "USD"
