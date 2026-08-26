from difflib import SequenceMatcher
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Expense

_MERCHANT_RATIO = 0.85


def normalize_merchant(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def merchants_similar(left: str | None, right: str | None) -> bool:
    a = normalize_merchant(left)
    b = normalize_merchant(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= _MERCHANT_RATIO


def amounts_similar(left: Decimal, right: Decimal) -> bool:
    return left.quantize(Decimal("0.01")) == right.quantize(Decimal("0.01"))


def find_likely_duplicate(
    session: Session,
    *,
    user_id: int,
    amount: Decimal,
    merchant: str | None,
    expense_date,
) -> Expense | None:
    """Return a recent matching expense for the same user/date/amount/merchant, or None."""
    rows = session.scalars(
        select(Expense).where(
            Expense.user_id == user_id,
            Expense.expense_date == expense_date,
        )
    ).all()
    for expense in rows:
        if not amounts_similar(expense.amount, amount):
            continue
        if merchants_similar(expense.merchant, merchant):
            return expense
    return None
