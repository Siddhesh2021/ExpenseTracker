from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ProcessedWhatsAppMessage


def claim_message_id(session: Session, message_id: str) -> bool:
    """Return True if this message ID is new and claimed; False if already processed."""
    session.add(ProcessedWhatsAppMessage(message_id=message_id))
    try:
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False
