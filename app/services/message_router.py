import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.core.config import get_settings
from app.db.idempotency import claim_message_id
from app.db.models import User
from app.parsers.command_parser import parse_command
from app.parsers.whatsapp_parser import UNSUPPORTED_MEDIA_TYPES
from app.schemas.whatsapp import IncomingWhatsAppMessage
from app.services.conversation_service import ConversationReply, ConversationService
from app.services.whatsapp_service import UNSUPPORTED_MEDIA_REPLY, WhatsAppAPIError, WhatsAppService

logger = logging.getLogger(__name__)

GREETINGS = frozenset({"hi", "hello", "hey", "start", "hi!", "hello!", "hey!"})

HELP_TEXT = (
    "👋 Welcome to ExpenseTracker.\n\n"
    "Track expenses directly through WhatsApp.\n\n"
    "Examples:\n\n"
    "₹450 Uber\n\n"
    "₹1200 hosting for Acme\n\n"
    "Commands:\n\n"
    "/summary\n"
    "/expenses\n"
    "/export\n"
    "/help"
)

PLACEHOLDER_SUMMARY = "Monthly summaries are coming soon. For now, send expenses like ₹450 Uber."
PLACEHOLDER_EXPENSES = "Expense history is coming soon. For now, send expenses like ₹450 Uber."
PLACEHOLDER_EXPORT = "Excel export is coming soon. For now, send expenses like ₹450 Uber."

_CONFIRM_BUTTONS = (("save", "Save"), ("edit", "Edit"), ("cancel", "Cancel"))
_DUPLICATE_BUTTONS = (("add_anyway", "Add anyway"), ("cancel", "Cancel"))


class MessageRouter:
    def __init__(
        self,
        session: Session,
        whatsapp: WhatsAppService,
        ai: AIProvider | None = None,
    ) -> None:
        self._session = session
        self._whatsapp = whatsapp
        self._ai = ai
        self._conversation = ConversationService(session, ai=ai)

    def handle_incoming(self, incoming: IncomingWhatsAppMessage) -> None:
        logger.info("webhook_message type=%s", incoming.message_type)
        if not claim_message_id(self._session, incoming.message_id):
            logger.info("webhook_duplicate_skipped")
            return

        user = self._get_or_create_user(incoming)
        logger.info("user_lookup")

        if incoming.message_type in UNSUPPORTED_MEDIA_TYPES:
            self._send_text(incoming.sender, UNSUPPORTED_MEDIA_REPLY)
            return

        text = (incoming.text or "").strip()
        if not text:
            return

        command = parse_command(text)
        if command is not None:
            self._send_text(incoming.sender, self._command_reply(command.name))
            return

        if text.lower() in GREETINGS:
            self._send_text(incoming.sender, HELP_TEXT)
            return

        reply = self._conversation.handle_message(user, text)
        self._deliver(incoming.sender, reply)

    def _command_reply(self, name: str) -> str:
        if name == "help":
            return HELP_TEXT
        if name == "summary":
            return PLACEHOLDER_SUMMARY
        if name == "expenses":
            return PLACEHOLDER_EXPENSES
        if name == "export":
            return PLACEHOLDER_EXPORT
        return HELP_TEXT

    def _deliver(self, to: str, reply: ConversationReply) -> None:
        if reply.kind == "confirm":
            self._send_interactive_or_text(to, reply.text, _CONFIRM_BUTTONS)
            return
        if reply.kind == "duplicate":
            self._send_interactive_or_text(to, reply.text, _DUPLICATE_BUTTONS)
            return
        self._send_text(to, reply.text)

    def _send_interactive_or_text(self, to: str, body: str, buttons: tuple[tuple[str, str], ...]) -> None:
        try:
            self._whatsapp.send_interactive_message(to, body, list(buttons))
        except WhatsAppAPIError:
            fallback = f"{body}\n\nReply save, edit, or cancel."
            if buttons == _DUPLICATE_BUTTONS:
                fallback = f"{body}\n\nReply add anyway or cancel."
            self._send_text(to, fallback)

    def _send_text(self, to: str, body: str) -> None:
        try:
            self._whatsapp.send_text_message(to, body)
        except WhatsAppAPIError:
            logger.exception("whatsapp_send_failed")

    def _get_or_create_user(self, incoming: IncomingWhatsAppMessage) -> User:
        user = self._session.scalar(select(User).where(User.whatsapp_number == incoming.sender))
        if user is not None:
            if incoming.contact_name and not user.name:
                user.name = incoming.contact_name
                self._session.commit()
            return user
        settings = get_settings()
        user = User(
            whatsapp_number=incoming.sender,
            name=incoming.contact_name,
            currency=settings.default_currency,
            timezone=settings.default_timezone,
        )
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user


def build_message_router(session: Session, whatsapp: WhatsAppService, ai: AIProvider | None = None) -> MessageRouter:
    return MessageRouter(session, whatsapp, ai=ai)
