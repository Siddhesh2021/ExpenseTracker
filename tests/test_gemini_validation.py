from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.ai.exceptions import ExpenseExtractionError
from app.ai.validation import parse_gemini_json, validate_extraction_payload
from app.schemas.expense import ExpenseExtraction, ExtractionContext

CONTEXT = ExtractionContext(today=date(2026, 8, 27), timezone="Asia/Kolkata", currency="INR")


def test_valid_gemini_payload() -> None:
    payload = parse_gemini_json(
        """
        {
          "amount": 1200,
          "currency": "INR",
          "merchant": "hosting",
          "category": "Software",
          "expense_date": "2026-08-26",
          "client": "Acme",
          "project": null,
          "description": "Hosting for Acme",
          "needs_confirmation": true
        }
        """
    )
    extraction = validate_extraction_payload(
        payload,
        "Spent ₹1200 on hosting for Acme yesterday",
        CONTEXT,
    )
    assert extraction.amount == Decimal("1200")
    assert extraction.merchant == "hosting"
    assert extraction.category == "Software"
    assert extraction.expense_date == date(2026, 8, 26)
    assert extraction.client == "Acme"
    assert extraction.needs_confirmation is True


def test_fenced_json_is_accepted() -> None:
    payload = parse_gemini_json('```json\n{"amount": 850, "merchant": "lunch", "category": "Food"}\n```')
    extraction = validate_extraction_payload(payload, "Paid 850 for lunch with Acme yesterday", CONTEXT)
    assert extraction.amount == Decimal("850")
    assert extraction.category == "Food"


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(ExpenseExtractionError):
        parse_gemini_json("not json")


def test_invented_amount_is_rejected() -> None:
    payload = {"amount": 99999, "merchant": "Uber", "category": "Travel"}
    with pytest.raises(ExpenseExtractionError, match="invented"):
        validate_extraction_payload(payload, "Spent ₹450 on Uber yesterday", CONTEXT)


def test_unknown_category_becomes_other() -> None:
    payload = {"amount": 450, "merchant": "Uber", "category": "Entertainment"}
    extraction = validate_extraction_payload(payload, "Spent ₹450 on Uber yesterday", CONTEXT)
    assert extraction.category == "Other"


def test_pydantic_rejects_non_numeric_amount() -> None:
    with pytest.raises(ValidationError):
        ExpenseExtraction.model_validate({"amount": "twelve hundred", "category": "Software"})


def test_invented_merchant_is_dropped() -> None:
    payload = {"amount": 850, "merchant": "MadeUpCafe", "category": "Food"}
    extraction = validate_extraction_payload(payload, "Paid 850 for lunch yesterday", CONTEXT)
    assert extraction.merchant is None
    assert extraction.amount == Decimal("850")


def test_missing_amount_stays_null() -> None:
    extraction = ExpenseExtraction.model_validate({"amount": None, "merchant": None, "category": "Other"})
    assert extraction.amount is None
