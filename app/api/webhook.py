import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.deps import get_message_router
from app.core.config import get_settings
from app.parsers.whatsapp_parser import parse_incoming_messages
from app.services.message_router import MessageRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token and hub_challenge is not None:
        logger.info("webhook_verified")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    logger.info("webhook_verification_failed")
    return PlainTextResponse(content="Forbidden", status_code=403)


@router.post("/webhook")
def receive_webhook(
    payload: dict,
    message_router: MessageRouter = Depends(get_message_router),
) -> JSONResponse:
    logger.info("webhook_received")
    try:
        incoming = parse_incoming_messages(payload)
        for message in incoming:
            message_router.handle_incoming(message)
    except Exception:
        logger.exception("webhook_processing_failed")
    return JSONResponse({"status": "ok"})
