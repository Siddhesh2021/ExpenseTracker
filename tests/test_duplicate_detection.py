from datetime import date
from decimal import Decimal

from app.db.models import Expense, User
from app.utils.duplicate_detection import amounts_similar, find_likely_duplicate, merchants_similar


def test_merchants_similar() -> None:
    assert merchants_similar("Uber", "uber")
    assert merchants_similar("Hostinger", "hostinger")
    assert not merchants_similar("Uber", "Swiggy")
    assert not merchants_similar("Uber", None)


def test_amounts_similar() -> None:
    assert amounts_similar(Decimal("450"), Decimal("450.00"))
    assert not amounts_similar(Decimal("450"), Decimal("451"))


def test_find_likely_duplicate(db_session) -> None:
    user = User(whatsapp_number="919777777777", currency="INR", timezone="Asia/Kolkata")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    existing = Expense(
        user_id=user.id,
        amount=Decimal("450.00"),
        currency="INR",
        merchant="Uber",
        category="Travel",
        expense_date=date(2026, 8, 26),
        source="deterministic",
    )
    db_session.add(existing)
    db_session.commit()

    match = find_likely_duplicate(
        db_session,
        user_id=user.id,
        amount=Decimal("450"),
        merchant="uber",
        expense_date=date(2026, 8, 26),
    )
    assert match is not None
    assert match.id == existing.id

    missing = find_likely_duplicate(
        db_session,
        user_id=user.id,
        amount=Decimal("450"),
        merchant="Swiggy",
        expense_date=date(2026, 8, 26),
    )
    assert missing is None
