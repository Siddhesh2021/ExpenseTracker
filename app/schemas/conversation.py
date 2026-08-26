from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.expense import ExpenseExtraction


class DuplicateSnapshot(BaseModel):
    id: int
    merchant: str | None = None
    amount: Decimal
    expense_date: date


class ConversationPayload(BaseModel):
    intent: str
    source: str
    pending: ExpenseExtraction
    duplicate: DuplicateSnapshot | None = None
