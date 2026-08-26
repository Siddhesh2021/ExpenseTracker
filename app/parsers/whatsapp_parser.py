from app.schemas.whatsapp import IncomingWhatsAppMessage

UNSUPPORTED_MEDIA_TYPES = frozenset(
    {"image", "audio", "video", "document", "sticker", "location", "contacts"}
)
_BUTTON_ID_TO_TEXT = {
    "save": "save",
    "edit": "edit",
    "cancel": "cancel",
    "add_anyway": "add anyway",
    "add": "add anyway",
}


def parse_incoming_messages(payload: dict) -> list[IncomingWhatsAppMessage]:
    messages: list[IncomingWhatsAppMessage] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            contacts = value.get("contacts") or []
            contact_name = None
            if contacts:
                contact_name = ((contacts[0].get("profile") or {}).get("name"))
            for item in value.get("messages") or []:
                parsed = _parse_one(item, contact_name)
                if parsed is not None:
                    messages.append(parsed)
    return messages


def _parse_one(item: dict, contact_name: str | None) -> IncomingWhatsAppMessage | None:
    message_id = item.get("id")
    sender = item.get("from")
    message_type = item.get("type") or "unknown"
    if not message_id or not sender:
        return None

    text = None
    if message_type == "text":
        text = ((item.get("text") or {}).get("body") or "").strip() or None
    elif message_type == "interactive":
        text = _interactive_text(item.get("interactive") or {})
    elif message_type == "button":
        text = ((item.get("button") or {}).get("text") or "").strip() or None

    return IncomingWhatsAppMessage(
        message_id=str(message_id),
        sender=str(sender),
        message_type=message_type,
        text=text,
        contact_name=contact_name,
    )


def _interactive_text(interactive: dict) -> str | None:
    button = interactive.get("button_reply") or {}
    button_id = (button.get("id") or "").strip().lower()
    if button_id in _BUTTON_ID_TO_TEXT:
        return _BUTTON_ID_TO_TEXT[button_id]
    title = (button.get("title") or "").strip()
    if title:
        return title
    list_reply = interactive.get("list_reply") or {}
    list_id = (list_reply.get("id") or "").strip().lower()
    if list_id in _BUTTON_ID_TO_TEXT:
        return _BUTTON_ID_TO_TEXT[list_id]
    return (list_reply.get("title") or "").strip() or None
