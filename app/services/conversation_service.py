import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.exceptions import ExpenseExtractionError
from app.core.config import get_settings
from app.core.states import (
    IDLE,
    INTENT_DUPLICATE,
    INTENT_NEW,
    WAITING_FOR_CONFIRMATION,
    WAITING_FOR_EDIT,
)
from app.db.models import ConversationState, Expense, User
from app.parsers.confirmation_parser import parse_confirmation_intent
from app.parsers.edit_parser import apply_edit, parse_edit, require_complete_extraction
from app.parsers.expense_parser import parse_simple_expense
from app.schemas.conversation import ConversationPayload, DuplicateSnapshot
from app.schemas.expense import ExpenseExtraction, ExtractionContext, ParsedExpense
from app.services.expense_service import SOURCE_DETERMINISTIC, SOURCE_GEMINI, ExpenseService
from app.utils.dates import today as today_in_timezone
from app.utils.duplicate_detection import find_likely_duplicate
from app.utils.formatting import format_expense_date, format_money

logger = logging.getLogger(__name__)

UNPARSEABLE = (
    "I couldn't understand that expense.\n\nTry:\n\n₹450 Uber"
)
UNKNOWN_CONFIRMATION = "I didn't get that. Reply save, edit, or cancel."
INVALID_EDIT = (
    "I couldn't apply that edit.\n\nTry:\n\nchange amount to 900\n"
    "change merchant to Hostinger\nchange category to Software"
)
EXPIRED = "That confirmation expired. Please send the expense again."
CANCELLED = "Cancelled. That expense was not saved."
EDIT_PROMPT = "What would you like to change?"


@dataclass
class ConversationReply:
    text: str
    kind: str
    expense: Expense | None = None
    extraction: ExpenseExtraction | None = None
    state: str = IDLE


class ConversationService:
    def __init__(
        self,
        session: Session,
        ai: AIProvider | None = None,
        expense_service: ExpenseService | None = None,
        now: datetime | None = None,
    ) -> None:
        self._session = session
        self._ai = ai
        self._expenses = expense_service or ExpenseService(session, ai=ai)
        self._now_override = now
        self._ttl_minutes = get_settings().conversation_state_ttl_minutes

    def handle_message(self, user: User, message: str) -> ConversationReply:
        record = self._record_for(user)
        if record is not None and record.state != IDLE:
            if record.expires_at is not None and record.expires_at <= self._now():
                logger.info("conversation_state_expired")
                self._clear(user)
                if parse_confirmation_intent(message) is not None:
                    return ConversationReply(text=EXPIRED, kind="expired", state=IDLE)
            elif record.state == WAITING_FOR_CONFIRMATION:
                return self._handle_confirmation(user, record, message)
            elif record.state == WAITING_FOR_EDIT:
                return self._handle_edit(user, record, message)

        intent = parse_confirmation_intent(message)
        if intent is not None:
            return ConversationReply(text="There's nothing waiting to confirm.", kind="idle", state=IDLE)

        parsed = parse_simple_expense(message)
        if parsed is not None and parsed.confident:
            return self._handle_confident(user, parsed)

        return self._handle_uncertain(user, message)

    def _handle_confident(self, user: User, parsed: ParsedExpense) -> ConversationReply:
        extraction = self._from_parsed(parsed, user)
        duplicate = self._duplicate_for(user, extraction)
        if duplicate is not None:
            self._store(
                user,
                WAITING_FOR_CONFIRMATION,
                ConversationPayload(
                    intent=INTENT_DUPLICATE,
                    source=SOURCE_DETERMINISTIC,
                    pending=extraction,
                    duplicate=self._snapshot(duplicate),
                ),
            )
            return ConversationReply(
                text=self._duplicate_text(duplicate, user),
                kind="duplicate",
                extraction=extraction,
                state=WAITING_FOR_CONFIRMATION,
            )
        expense = self._expenses.save_parsed_expense(user, parsed, source=SOURCE_DETERMINISTIC)
        self._clear(user)
        return ConversationReply(
            text=self._saved_text(expense, user),
            kind="saved",
            expense=expense,
            extraction=extraction,
            state=IDLE,
        )

    def _handle_uncertain(self, user: User, message: str) -> ConversationReply:
        if self._ai is None:
            return ConversationReply(text=UNPARSEABLE, kind="error", state=IDLE)
        context = self._context_for(user)
        try:
            extraction = self._ai.extract_expense(message, context)
        except ExpenseExtractionError:
            logger.info("gemini_failed")
            return ConversationReply(text=UNPARSEABLE, kind="error", state=IDLE)

        validated = require_complete_extraction(extraction)
        if validated is None:
            return ConversationReply(text=UNPARSEABLE, kind="error", state=IDLE)

        validated = validated.model_copy(update={"needs_confirmation": True})
        if validated.expense_date is None:
            validated = validated.model_copy(update={"expense_date": context.today})
        if validated.currency is None:
            validated = validated.model_copy(update={"currency": user.currency or "INR"})

        self._store(
            user,
            WAITING_FOR_CONFIRMATION,
            ConversationPayload(intent=INTENT_NEW, source=SOURCE_GEMINI, pending=validated),
        )
        return ConversationReply(
            text=self._confirm_text(validated, user),
            kind="confirm",
            extraction=validated,
            state=WAITING_FOR_CONFIRMATION,
        )

    def _handle_confirmation(self, user: User, record: ConversationState, message: str) -> ConversationReply:
        intent = parse_confirmation_intent(message)
        payload = self._load_payload(record)
        if payload is None:
            self._clear(user)
            return ConversationReply(text=EXPIRED, kind="expired", state=IDLE)
        if intent is None:
            return ConversationReply(
                text=UNKNOWN_CONFIRMATION,
                kind="unknown",
                extraction=payload.pending,
                state=WAITING_FOR_CONFIRMATION,
            )
        if intent.name == "cancel":
            return self._cancel(user)
        if intent.name == "edit":
            self._store(user, WAITING_FOR_EDIT, payload)
            return ConversationReply(
                text=EDIT_PROMPT,
                kind="edit_prompt",
                extraction=payload.pending,
                state=WAITING_FOR_EDIT,
            )
        return self._confirm_save(user, payload)

    def _handle_edit(self, user: User, record: ConversationState, message: str) -> ConversationReply:
        intent = parse_confirmation_intent(message)
        payload = self._load_payload(record)
        if payload is None:
            self._clear(user)
            return ConversationReply(text=EXPIRED, kind="expired", state=IDLE)
        if intent is not None and intent.name == "cancel":
            return self._cancel(user)
        if intent is not None and intent.name == "save":
            return self._confirm_save(user, payload)

        parsed_edit = parse_edit(message)
        if parsed_edit is None:
            return ConversationReply(
                text=INVALID_EDIT,
                kind="invalid_edit",
                extraction=payload.pending,
                state=WAITING_FOR_EDIT,
            )
        updated = apply_edit(payload.pending, parsed_edit, self._context_for(user))
        validated = require_complete_extraction(updated) if updated is not None else None
        if validated is None:
            return ConversationReply(
                text=INVALID_EDIT,
                kind="invalid_edit",
                extraction=payload.pending,
                state=WAITING_FOR_EDIT,
            )
        next_payload = ConversationPayload(intent=INTENT_NEW, source=payload.source, pending=validated)
        self._store(user, WAITING_FOR_CONFIRMATION, next_payload)
        return ConversationReply(
            text=self._confirm_text(validated, user),
            kind="confirm",
            extraction=validated,
            state=WAITING_FOR_CONFIRMATION,
        )

    def _confirm_save(self, user: User, payload: ConversationPayload) -> ConversationReply:
        validated = require_complete_extraction(payload.pending)
        if validated is None:
            self._clear(user)
            return ConversationReply(text=UNPARSEABLE, kind="error", state=IDLE)

        if payload.intent != INTENT_DUPLICATE:
            duplicate = self._duplicate_for(user, validated)
            if duplicate is not None:
                dup_payload = ConversationPayload(
                    intent=INTENT_DUPLICATE,
                    source=payload.source,
                    pending=validated,
                    duplicate=self._snapshot(duplicate),
                )
                self._store(user, WAITING_FOR_CONFIRMATION, dup_payload)
                return ConversationReply(
                    text=self._duplicate_text(duplicate, user),
                    kind="duplicate",
                    extraction=validated,
                    state=WAITING_FOR_CONFIRMATION,
                )

        result = self._expenses.save_extraction(user, validated, source=payload.source)
        if not result.success or result.expense is None:
            return ConversationReply(text=UNPARSEABLE, kind="error", extraction=validated, state=WAITING_FOR_CONFIRMATION)
        self._clear(user)
        return ConversationReply(
            text=self._saved_text(result.expense, user),
            kind="saved",
            expense=result.expense,
            extraction=validated,
            state=IDLE,
        )

    def _cancel(self, user: User) -> ConversationReply:
        self._clear(user)
        return ConversationReply(text=CANCELLED, kind="cancelled", state=IDLE)

    def _duplicate_for(self, user: User, extraction: ExpenseExtraction) -> Expense | None:
        if extraction.amount is None:
            return None
        expense_date = extraction.expense_date or today_in_timezone(user.timezone)
        return find_likely_duplicate(
            self._session,
            user_id=user.id,
            amount=extraction.amount,
            merchant=extraction.merchant,
            expense_date=expense_date,
        )

    def _store(self, user: User, state: str, payload: ConversationPayload) -> None:
        now = self._now()
        expires_at = now + timedelta(minutes=self._ttl_minutes)
        record = self._record_for(user)
        body = payload.model_dump(mode="json")
        if record is None:
            record = ConversationState(user_id=user.id, state=state, payload=body, expires_at=expires_at)
            self._session.add(record)
        else:
            record.state = state
            record.payload = body
            record.expires_at = expires_at
            record.updated_at = now
        self._session.commit()
        logger.info("conversation_state state=%s", state)

    def _clear(self, user: User) -> None:
        record = self._record_for(user)
        if record is None:
            return
        record.state = IDLE
        record.payload = None
        record.expires_at = None
        record.updated_at = self._now()
        self._session.commit()
        logger.info("conversation_state state=%s", IDLE)

    def _record_for(self, user: User) -> ConversationState | None:
        return self._session.scalar(select(ConversationState).where(ConversationState.user_id == user.id))

    def _load_payload(self, record: ConversationState) -> ConversationPayload | None:
        if not record.payload:
            return None
        try:
            return ConversationPayload.model_validate(record.payload)
        except Exception:
            logger.info("conversation_payload_invalid")
            return None

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
            expense_date=parsed.expense_date or today_in_timezone(user.timezone),
            client=parsed.client,
            project=parsed.project,
            description=parsed.description,
            needs_confirmation=False,
        )

    def _snapshot(self, expense: Expense) -> DuplicateSnapshot:
        return DuplicateSnapshot(
            id=expense.id,
            merchant=expense.merchant,
            amount=expense.amount,
            expense_date=expense.expense_date,
        )

    def _now(self) -> datetime:
        if self._now_override is not None:
            return self._now_override
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _saved_text(self, expense: Expense, user: User) -> str:
        lines = [
            "✅ Expense added",
            "",
            format_money(expense.amount, expense.currency),
            expense.merchant or "",
            expense.category,
            format_expense_date(expense.expense_date, user.timezone),
        ]
        return "\n".join(lines)

    def _confirm_text(self, extraction: ExpenseExtraction, user: User) -> str:
        amount = extraction.amount or Decimal("0")
        lines = [
            "I found:",
            "",
            format_money(amount, extraction.currency or user.currency or "INR"),
            extraction.merchant or "",
            extraction.category,
            format_expense_date(extraction.expense_date, user.timezone),
        ]
        if extraction.client:
            lines.append(extraction.client)
        lines.extend(["", "Save this expense?"])
        return "\n".join(lines)

    def _duplicate_text(self, expense: Expense, user: User) -> str:
        merchant = expense.merchant or "Expense"
        amount = format_money(expense.amount, expense.currency)
        when = format_expense_date(expense.expense_date, user.timezone)
        return (
            "⚠️ This looks similar to an existing expense:\n\n"
            f"{merchant} — {amount} — {when}\n\n"
            "Add anyway?"
        )
