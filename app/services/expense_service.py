import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.exceptions import ExpenseExtractionError
from app.db.models import Expense, User
from app.parsers.expense_parser import parse_simple_expense
from app.schemas.expense import ExpenseExtraction, ExtractionContext, ParsedExpense
from app.utils.dates import today as today_in_timezone

SOURCE_DETERMINISTIC = "deterministic"
SOURCE_GEMINI = "gemini"

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    success: bool
    expense: Expense | None = None
    extraction: ExpenseExtraction | None = None
    source: str | None = None
    error_code: str | None = None


class ExpenseService:
    def __init__(self, session: Session, ai: AIProvider | None = None) -> None:
        self._session = session
        self._ai = ai

    def ingest_text(self, user: User, message: str) -> IngestResult:
        parsed = parse_simple_expense(message)
        if parsed is not None and parsed.confident:
            expense = self.save_parsed_expense(user, parsed, source=SOURCE_DETERMINISTIC)
            return IngestResult(
                success=True,
                expense=expense,
                extraction=self._from_parsed(parsed, user),
                source=SOURCE_DETERMINISTIC,
            )

        if self._ai is None:
            return IngestResult(success=False, error_code="unparseable")

        context = self._context_for(user)
        try:
            extraction = self._ai.extract_expense(message, context)
        except ExpenseExtractionError:
            return IngestResult(success=False, error_code="gemini_failed")

        return self.save_extraction(user, extraction, source=SOURCE_GEMINI)

    def save_parsed_expense(self, user: User, parsed: ParsedExpense, source: str = SOURCE_DETERMINISTIC) -> Expense:
        expense_date = parsed.expense_date or today_in_timezone(user.timezone)
        expense = self._build_expense(
            user=user,
            amount=parsed.amount,
            currency=parsed.currency or user.currency,
            merchant=parsed.merchant,
            category=parsed.category,
            expense_date=expense_date,
            client=parsed.client,
            project=parsed.project,
            description=parsed.description,
            source=source,
        )
        return self._persist(expense)

    def save_extraction(self, user: User, extraction: ExpenseExtraction, source: str = SOURCE_GEMINI) -> IngestResult:
        if extraction.amount is None:
            return IngestResult(success=False, extraction=extraction, source=source, error_code="invalid_extraction")

        expense_date = extraction.expense_date or today_in_timezone(user.timezone)
        expense = self._build_expense(
            user=user,
            amount=extraction.amount,
            currency=extraction.currency or user.currency or "INR",
            merchant=extraction.merchant,
            category=extraction.category,
            expense_date=expense_date,
            client=extraction.client,
            project=extraction.project,
            description=extraction.description,
            source=source,
        )
        saved = self._persist(expense)
        return IngestResult(success=True, expense=saved, extraction=extraction, source=source)

    def _persist(self, expense: Expense) -> Expense:
        self._session.add(expense)
        self._session.commit()
        self._session.refresh(expense)
        logger.info("expense_created source=%s category=%s", expense.source, expense.category)
        return expense

    def _build_expense(
        self,
        *,
        user: User,
        amount: Decimal,
        currency: str,
        merchant: str | None,
        category: str,
        expense_date: date,
        client: str | None,
        project: str | None,
        description: str | None,
        source: str,
    ) -> Expense:
        return Expense(
            user_id=user.id,
            amount=amount,
            currency=currency,
            merchant=merchant,
            category=category,
            expense_date=expense_date,
            client=client,
            project=project,
            description=description,
            source=source,
        )

    def _context_for(self, user: User) -> ExtractionContext:
        return ExtractionContext(
            today=today_in_timezone(user.timezone),
            timezone=user.timezone,
            currency=user.currency or "INR",
        )

    def _from_parsed(self, parsed: ParsedExpense, user: User) -> ExpenseExtraction:
        return ExpenseExtraction(
            amount=parsed.amount,
            currency=parsed.currency or user.currency,
            merchant=parsed.merchant,
            category=parsed.category,
            expense_date=parsed.expense_date,
            client=parsed.client,
            project=parsed.project,
            description=parsed.description,
            needs_confirmation=False,
        )
