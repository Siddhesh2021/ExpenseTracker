from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import func, select

from app.ai.base import AIProvider
from app.ai.exceptions import ExpenseExtractionError
from app.ai.gemini import GeminiProvider
from app.db.models import Expense, User
from app.schemas.expense import ExpenseExtraction, ExtractionContext
from app.services.expense_service import SOURCE_DETERMINISTIC, SOURCE_GEMINI, ExpenseService


class FakeAI(AIProvider):
    def __init__(self, extraction: ExpenseExtraction | None = None, error: Exception | None = None) -> None:
        self.extraction = extraction
        self.error = error
        self.calls: list[tuple[str, ExtractionContext]] = []

    def extract_expense(self, message: str, context: ExtractionContext) -> ExpenseExtraction:
        self.calls.append((message, context))
        if self.error is not None:
            raise self.error
        assert self.extraction is not None
        return self.extraction


def _user(session) -> User:
    user = User(whatsapp_number="919999999999", name="Sid", currency="INR", timezone="Asia/Kolkata")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _expense_count(session) -> int:
    return int(session.scalar(select(func.count()).select_from(Expense)) or 0)


def test_deterministic_path_skips_gemini(db_session) -> None:
    ai = FakeAI(error=AssertionError("Gemini should not be called"))
    service = ExpenseService(db_session, ai=ai)
    user = _user(db_session)

    result = service.ingest_text(user, "₹450 Uber")

    assert result.success is True
    assert result.source == SOURCE_DETERMINISTIC
    assert result.expense is not None
    assert result.expense.amount == Decimal("450.00")
    assert result.expense.merchant == "Uber"
    assert result.expense.category == "Travel"
    assert result.expense.source == SOURCE_DETERMINISTIC
    assert ai.calls == []
    assert _expense_count(db_session) == 1


def test_gemini_path_saves_validated_expense(db_session) -> None:
    extraction = ExpenseExtraction(
        amount=Decimal("1200"),
        currency="INR",
        merchant="hosting",
        category="Software",
        expense_date=date(2026, 8, 26),
        client="Acme",
        needs_confirmation=True,
    )
    ai = FakeAI(extraction=extraction)
    service = ExpenseService(db_session, ai=ai)
    user = _user(db_session)

    result = service.ingest_text(user, "Spent ₹1200 on hosting for Acme yesterday")

    assert result.success is True
    assert result.source == SOURCE_GEMINI
    assert len(ai.calls) == 1
    assert result.expense is not None
    assert result.expense.amount == Decimal("1200.00")
    assert result.expense.client == "Acme"
    assert result.expense.category == "Software"
    assert result.expense.source == SOURCE_GEMINI
    assert _expense_count(db_session) == 1


def test_gemini_failure_does_not_save(db_session) -> None:
    ai = FakeAI(error=ExpenseExtractionError("invalid Gemini JSON"))
    service = ExpenseService(db_session, ai=ai)
    user = _user(db_session)

    result = service.ingest_text(user, "Spent money on something yesterday")

    assert result.success is False
    assert result.error_code == "gemini_failed"
    assert _expense_count(db_session) == 0


def test_extraction_without_amount_is_not_saved(db_session) -> None:
    service = ExpenseService(db_session, ai=FakeAI())
    user = _user(db_session)
    result = service.save_extraction(user, ExpenseExtraction(amount=None, merchant=None))
    assert result.success is False
    assert result.error_code == "invalid_extraction"
    assert _expense_count(db_session) == 0


def test_gemini_provider_uses_mocked_sdk() -> None:
    raw = (
        '{"amount": 850, "currency": "INR", "merchant": "lunch", "category": "Food",'
        ' "expense_date": "2026-08-26", "client": "Acme", "project": null,'
        ' "description": null, "needs_confirmation": true}'
    )
    fake_models = SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text=raw))
    fake_client = SimpleNamespace(models=fake_models)
    provider = GeminiProvider(client=fake_client, model="gemini-2.5-flash")
    context = ExtractionContext(today=date(2026, 8, 27), timezone="Asia/Kolkata", currency="INR")

    extraction = provider.extract_expense("Paid 850 for lunch with Acme yesterday", context)

    assert extraction.amount == Decimal("850")
    assert extraction.category == "Food"
    assert extraction.client == "Acme"
