"""Idempotent local seed data for ExpenseTracker."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.db.database import get_session_factory
from app.db.models import ConversationState, Expense, User

SEED_WHATSAPP_NUMBER = "919999999999"


def seed() -> None:
    session = get_session_factory()()
    try:
        user = session.scalar(select(User).where(User.whatsapp_number == SEED_WHATSAPP_NUMBER))
        if user is None:
            user = User(
                whatsapp_number=SEED_WHATSAPP_NUMBER,
                name="Sid",
                currency="INR",
                timezone="Asia/Kolkata",
            )
            session.add(user)
            session.flush()

        if not session.scalar(select(Expense.id).where(Expense.user_id == user.id).limit(1)):
            session.add_all(
                [
                    Expense(
                        user_id=user.id,
                        amount=Decimal("450.00"),
                        currency="INR",
                        merchant="Uber",
                        category="Travel",
                        expense_date=date(2026, 8, 26),
                        source="deterministic",
                    ),
                    Expense(
                        user_id=user.id,
                        amount=Decimal("1200.00"),
                        currency="INR",
                        merchant="Hostinger",
                        category="Software",
                        expense_date=date(2026, 8, 25),
                        client="Acme",
                        description="Hosting",
                        source="gemini",
                    ),
                    Expense(
                        user_id=user.id,
                        amount=Decimal("850.00"),
                        currency="INR",
                        merchant="Lunch",
                        category="Food",
                        expense_date=date(2026, 8, 24),
                        source="deterministic",
                    ),
                ]
            )

        state = session.scalar(select(ConversationState).where(ConversationState.user_id == user.id))
        if state is None:
            session.add(ConversationState(user_id=user.id, state="IDLE", payload=None))

        session.commit()
        print(f"Seeded user {SEED_WHATSAPP_NUMBER} (id={user.id})")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
