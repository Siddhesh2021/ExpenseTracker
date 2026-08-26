from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.ai.base import AIProvider
from app.ai.exceptions import ExpenseExtractionError
from app.core.states import IDLE, WAITING_FOR_CONFIRMATION, WAITING_FOR_EDIT
from app.db.models import ConversationState, Expense, User
from app.schemas.expense import ExpenseExtraction, ExtractionContext
from app.services.conversation_service import ConversationService
from app.utils.dates import today as today_in_timezone


class FakeAI(AIProvider):
    def __init__(self, extraction: ExpenseExtraction | None = None, error: Exception | None = None) -> None:
        self.extraction = extraction
        self.error = error
        self.calls: list[str] = []

    def extract_expense(self, message: str, context: ExtractionContext) -> ExpenseExtraction:
        self.calls.append(message)
        if self.error is not None:
            raise self.error
        assert self.extraction is not None
        return self.extraction


def _user(session) -> User:
    user = User(whatsapp_number="919888888888", name="Sid", currency="INR", timezone="Asia/Kolkata")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _count(session) -> int:
    return int(session.scalar(select(func.count()).select_from(Expense)) or 0)


def _state(session, user: User) -> ConversationState | None:
    return session.scalar(select(ConversationState).where(ConversationState.user_id == user.id))


def _hosting_extraction() -> ExpenseExtraction:
    return ExpenseExtraction(
        amount=Decimal("1200"),
        currency="INR",
        merchant="Hosting",
        category="Software",
        expense_date=date(2026, 8, 26),
        client="Acme",
        needs_confirmation=True,
    )


def test_confident_expense_is_saved(db_session) -> None:
    ai = FakeAI(error=AssertionError("Gemini should not be called"))
    service = ConversationService(db_session, ai=ai)
    user = _user(db_session)

    reply = service.handle_message(user, "₹450 Uber")

    assert reply.kind == "saved"
    assert reply.state == IDLE
    assert "Expense added" in reply.text
    assert _count(db_session) == 1
    assert ai.calls == []
    record = _state(db_session, user)
    assert record is None or record.state == IDLE


def test_uncertain_expense_enters_confirmation_state(db_session) -> None:
    ai = FakeAI(extraction=_hosting_extraction())
    service = ConversationService(db_session, ai=ai)
    user = _user(db_session)

    reply = service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")

    assert reply.kind == "confirm"
    assert reply.state == WAITING_FOR_CONFIRMATION
    assert "Save this expense?" in reply.text
    assert _count(db_session) == 0
    record = _state(db_session, user)
    assert record is not None
    assert record.state == WAITING_FOR_CONFIRMATION
    assert record.payload["pending"]["merchant"] == "Hosting"


def test_confirmation_saves_pending_expense(db_session) -> None:
    ai = FakeAI(extraction=_hosting_extraction())
    service = ConversationService(db_session, ai=ai)
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")

    reply = service.handle_message(user, "save")

    assert reply.kind == "saved"
    assert reply.state == IDLE
    assert _count(db_session) == 1
    expense = db_session.scalar(select(Expense))
    assert expense.merchant == "Hosting"
    assert expense.amount == Decimal("1200.00")
    record = _state(db_session, user)
    assert record is not None
    assert record.state == IDLE
    assert record.payload is None


def test_cancellation_does_not_save(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")

    reply = service.handle_message(user, "cancel")

    assert reply.kind == "cancelled"
    assert _count(db_session) == 0
    record = _state(db_session, user)
    assert record is not None
    assert record.state == IDLE
    assert record.payload is None


def test_expired_confirmation_cannot_save(db_session) -> None:
    now = datetime(2026, 8, 27, 12, 0, 0)
    service = ConversationService(
        db_session,
        ai=FakeAI(extraction=_hosting_extraction()),
        now=now,
    )
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    record = _state(db_session, user)
    assert record is not None
    record.expires_at = now - timedelta(minutes=1)
    db_session.commit()

    later = ConversationService(
        db_session,
        ai=FakeAI(extraction=_hosting_extraction()),
        now=now,
    )
    reply = later.handle_message(user, "save")

    assert reply.kind in {"expired", "idle"}
    assert _count(db_session) == 0


def test_edit_amount(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change amount to 500")
    assert reply.kind == "confirm"
    assert reply.extraction is not None
    assert reply.extraction.amount == Decimal("500")
    assert reply.state == WAITING_FOR_CONFIRMATION


def test_edit_merchant(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change merchant to Hostinger")
    assert reply.extraction is not None
    assert reply.extraction.merchant == "Hostinger"


def test_edit_category(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change category to Client Expense")
    assert reply.extraction is not None
    assert reply.extraction.category == "Client Expense"


def test_edit_date(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change date to yesterday")
    assert reply.extraction is not None
    assert reply.extraction.expense_date == today_in_timezone("Asia/Kolkata") - timedelta(days=1)


def test_edit_client(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change client to Globex")
    assert reply.extraction is not None
    assert reply.extraction.client == "Globex"


def test_edit_project(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change project to Website")
    assert reply.extraction is not None
    assert reply.extraction.project == "Website"


def test_edit_description(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change description to Annual hosting")
    assert reply.extraction is not None
    assert reply.extraction.description == "Annual hosting"


def test_invalid_edit_is_rejected(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    prompt = service.handle_message(user, "edit")
    assert prompt.state == WAITING_FOR_EDIT
    reply = service.handle_message(user, "change amount to abc")
    assert reply.kind == "invalid_edit"
    assert reply.state == WAITING_FOR_EDIT
    assert _count(db_session) == 0
    record = _state(db_session, user)
    assert record is not None
    assert record.state == WAITING_FOR_EDIT
    assert Decimal(str(record.payload["pending"]["amount"])) == Decimal("1200")


def test_edited_expense_requires_confirmation(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    service.handle_message(user, "edit")
    reply = service.handle_message(user, "change amount to 900")
    assert reply.kind == "confirm"
    assert "Save this expense?" in reply.text
    assert _count(db_session) == 0
    assert reply.extraction is not None
    assert reply.extraction.needs_confirmation is True


def test_duplicate_expense_is_detected(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(error=ExpenseExtractionError("unused")))
    user = _user(db_session)
    service.handle_message(user, "₹450 Uber")
    reply = service.handle_message(user, "₹450 Uber")
    assert reply.kind == "duplicate"
    assert "looks similar" in reply.text
    assert _count(db_session) == 1
    assert reply.state == WAITING_FOR_CONFIRMATION


def test_duplicate_can_be_cancelled(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(error=ExpenseExtractionError("unused")))
    user = _user(db_session)
    service.handle_message(user, "₹450 Uber")
    service.handle_message(user, "₹450 Uber")
    reply = service.handle_message(user, "cancel")
    assert reply.kind == "cancelled"
    assert _count(db_session) == 1
    record = _state(db_session, user)
    assert record is not None
    assert record.state == IDLE


def test_duplicate_can_be_explicitly_added(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(error=ExpenseExtractionError("unused")))
    user = _user(db_session)
    service.handle_message(user, "₹450 Uber")
    service.handle_message(user, "₹450 Uber")
    reply = service.handle_message(user, "add anyway")
    assert reply.kind == "saved"
    assert _count(db_session) == 2


def test_unknown_confirmation_command_is_safe(db_session) -> None:
    service = ConversationService(db_session, ai=FakeAI(extraction=_hosting_extraction()))
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    reply = service.handle_message(user, "maybe later")
    assert reply.kind == "unknown"
    assert reply.state == WAITING_FOR_CONFIRMATION
    assert _count(db_session) == 0
    assert _state(db_session, user).state == WAITING_FOR_CONFIRMATION


def test_confirmation_commands_are_not_sent_to_gemini(db_session) -> None:
    ai = FakeAI(extraction=_hosting_extraction())
    service = ConversationService(db_session, ai=ai)
    user = _user(db_session)
    service.handle_message(user, "Spent ₹1200 on hosting for Acme yesterday")
    ai.calls.clear()
    service.handle_message(user, "edit")
    service.handle_message(user, "save")
    assert ai.calls == []
