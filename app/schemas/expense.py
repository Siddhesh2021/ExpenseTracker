from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.categories import Category, DEFAULT_CATEGORY, normalize_category


def _blank_to_none(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ParsedExpense(BaseModel):
    amount: Decimal
    currency: str = "INR"
    merchant: str
    category: Category = DEFAULT_CATEGORY
    expense_date: date | None = None
    client: str | None = None
    project: str | None = None
    description: str | None = None
    confident: bool = True

    model_config = ConfigDict(frozen=True)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("amount must be greater than zero")
        return value

    @field_validator("category", mode="before")
    @classmethod
    def category_must_be_allowed(cls, value: object) -> Category:
        if not isinstance(value, str):
            return DEFAULT_CATEGORY
        return normalize_category(value)


class ExtractionContext(BaseModel):
    today: date
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"


class ExpenseExtraction(BaseModel):
    amount: Decimal | None = None
    currency: str | None = None
    merchant: str | None = None
    category: Category = DEFAULT_CATEGORY
    expense_date: date | None = None
    client: str | None = None
    project: str | None = None
    description: str | None = None
    needs_confirmation: bool = True

    model_config = ConfigDict(extra="ignore")

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, value: object) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            if isinstance(value, Decimal):
                amount = value
            elif isinstance(value, int):
                amount = Decimal(value)
            elif isinstance(value, float):
                amount = Decimal(str(value))
            elif isinstance(value, str):
                amount = Decimal(value.replace(",", "").strip())
            else:
                raise ValueError("amount must be numeric")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("amount must be numeric") from exc
        if amount <= 0:
            raise ValueError("amount must be greater than zero")
        return amount

    @field_validator("category", mode="before")
    @classmethod
    def category_must_be_allowed(cls, value: object) -> Category:
        if value is None or value == "":
            return DEFAULT_CATEGORY
        if not isinstance(value, str):
            return DEFAULT_CATEGORY
        return normalize_category(value)

    @field_validator("currency", "merchant", "client", "project", "description", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("currency", mode="after")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()
