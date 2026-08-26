from decimal import Decimal

from app.parsers.expense_parser import parse_simple_expense


def test_parse_uber_expense() -> None:
    parsed = parse_simple_expense("₹450 Uber")
    assert parsed is not None
    assert parsed.amount == Decimal("450")
    assert parsed.merchant == "Uber"
    assert parsed.category == "Travel"
    assert parsed.currency == "INR"
    assert parsed.confident is True


def test_parse_hostinger_expense() -> None:
    parsed = parse_simple_expense("₹1200 Hostinger")
    assert parsed is not None
    assert parsed.amount == Decimal("1200")
    assert parsed.merchant == "Hostinger"
    assert parsed.category == "Software"


def test_parse_swiggy_expense() -> None:
    parsed = parse_simple_expense("₹500 Swiggy")
    assert parsed is not None
    assert parsed.amount == Decimal("500")
    assert parsed.merchant == "Swiggy"
    assert parsed.category == "Food"


def test_parse_amount_without_symbol() -> None:
    parsed = parse_simple_expense("450 Uber")
    assert parsed is not None
    assert parsed.amount == Decimal("450")
    assert parsed.category == "Travel"


def test_parse_lunch_keyword() -> None:
    parsed = parse_simple_expense("₹850 lunch")
    assert parsed is not None
    assert parsed.merchant == "Lunch"
    assert parsed.category == "Food"


def test_invalid_expense_without_amount() -> None:
    assert parse_simple_expense("Uber") is None


def test_invalid_expense_without_merchant() -> None:
    assert parse_simple_expense("₹450") is None


def test_invalid_greeting_is_not_an_expense() -> None:
    assert parse_simple_expense("Hello") is None


def test_complex_natural_language_is_not_parsed_deterministically() -> None:
    assert parse_simple_expense("Spent ₹1200 on hosting for Acme yesterday") is None
    assert parse_simple_expense("₹1200 hosting for Acme") is None
