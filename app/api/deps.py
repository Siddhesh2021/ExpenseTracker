from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.db.database import get_db
from app.services.message_router import MessageRouter, build_message_router
from app.services.whatsapp_service import WhatsAppService


def get_whatsapp_service() -> WhatsAppService:
    return WhatsAppService()


def get_ai_provider_optional() -> AIProvider | None:
    from app.ai import get_ai_provider

    try:
        return get_ai_provider()
    except Exception:
        return None


def get_message_router(
    session: Session = Depends(get_db),
    whatsapp: WhatsAppService = Depends(get_whatsapp_service),
    ai: AIProvider | None = Depends(get_ai_provider_optional),
) -> Generator[MessageRouter, None, None]:
    yield build_message_router(session, whatsapp, ai)
