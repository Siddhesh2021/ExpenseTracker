"""Try expense ingest locally without WhatsApp.

Examples:
  python -m scripts.try_ingest "₹450 Uber"
  python -m scripts.try_ingest "Spent ₹1200 on hosting for Acme yesterday"
  python -m scripts.try_ingest save
"""

import sys

from sqlalchemy import select

from app.ai import get_ai_provider
from app.db.database import get_session_factory
from app.db.models import User
from app.services.conversation_service import ConversationService
from scripts.seed import SEED_WHATSAPP_NUMBER, seed


def main() -> None:
    message = " ".join(sys.argv[1:]).strip() or "Spent ₹1200 on hosting for Acme yesterday"
    seed()
    session = get_session_factory()()
    try:
        user = session.scalar(select(User).where(User.whatsapp_number == SEED_WHATSAPP_NUMBER))
        if user is None:
            raise SystemExit("Seed user not found. Run: python -m scripts.seed")
        reply = ConversationService(session, ai=get_ai_provider()).handle_message(user, message)
        print(f"kind={reply.kind} state={reply.state}")
        print(reply.text)
        if reply.expense is not None:
            print(
                f"saved id={reply.expense.id} {reply.expense.currency} {reply.expense.amount} "
                f"{reply.expense.merchant} {reply.expense.category} {reply.expense.expense_date}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
